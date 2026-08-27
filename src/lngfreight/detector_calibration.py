"""Phase A3 detector calibration.

A2 produced a forecast.  A3 turns forecast error into an alarm rule and fixes
the one number that rule needs: the threshold.  Everything here is calibrated
on the 27 non-Hormuz development units, exactly as `detector_contract` requires,
and the frozen `detector:` block in `config/hormuz_detection.yaml` supplies every
rule.  Nothing in this module chooses a rule; it only executes frozen ones and
reports what they achieved.

Three things in the design are easy to get wrong and are handled explicitly.

*Thresholds are transferable.*  One threshold per model, horizon and detector
form, calibrated across units.  Hormuz never enters calibration, so a per-unit
threshold would have no Hormuz counterpart at scoring time.

*Masked gaps are segment boundaries.*  A unit-day with no admissible residual
carries no observation, so an episode can neither continue nor be counted
across it.  Both counters reset, an episode running into a gap is right-censored
and terminated on its last eligible day, and a new episode after the gap needs a
fresh pair of consecutive exceedances.

*The frozen object is the scaling algorithm, not a constant.*  Context scales
are refitted per fold and horizon on history through that fold's `fit_end`, so a
2021 residual is normalised on 2021 information.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Mapping, Sequence

import numpy as np
import pandas as pd

from .disruption_detector import (
    EventMask,
    apply_event_mask,
    fit_context_scale,
    load_event_mask,
    validate_detector_calibration_tasks,
)
from .global_forecaster import (
    LeakageError,
    RidgeGlobalModel,
    RollingOriginFold,
    TrainingOnlyStandardizer,
    apply_context_normalisation,
    assert_task_access,
    build_task_geometry,
    classify_feature_transforms,
    denormalise,
    development_units,
    feature_columns,
    fit_unit_context_scales,
    materialize_task_features,
    rolling_origin_folds,
    seasonal_naive_predictions,
    task_geometry_hash,
    validate_task_table,
    _minimum_supported_target,
)

RAW_LEVEL = "raw_level"
SCALE_INVARIANT = "scale_invariant"
DETECTOR_FORMS = (RAW_LEVEL, SCALE_INVARIANT)

DAYS_PER_YEAR = 365.25

# Seasonal naive is a lookup rather than a fit, so withholding a unit from
# "model fitting" withholds nothing from it.  Its end-to-end LOCO is its
# threshold LOCO by construction, and claiming two distinct tests for it would
# be a fiction.
MODELS_WITHOUT_END_TO_END_LOCO = frozenset({"seasonal_naive"})


class DetectorSpecError(ValueError):
    """Raised when the frozen A3 detector block has drifted."""


def validate_detector_spec(spec: Mapping) -> None:
    """Reject drift in the frozen A3 detector contract before anything runs."""
    detector = spec.get("detector")
    if not isinstance(detector, Mapping):
        raise DetectorSpecError("phase A3 requires a frozen `detector` specification block")
    if detector.get("status") != "frozen" or detector.get("frozen") is not True:
        raise DetectorSpecError("the detector design must be frozen before calibration runs")
    outstanding = detector.get("outstanding_unratified_items")
    if outstanding is None or list(outstanding):
        raise DetectorSpecError(
            "the detector design still carries unratified items; calibration is blocked"
        )

    scope = detector["threshold_scope"]
    if scope.get("rule") != "one_transferable_threshold_per_model_horizon_and_form":
        raise DetectorSpecError("threshold scope drifted from the frozen transferable rule")
    if scope.get("per_unit_thresholds_prohibited") is not True:
        raise DetectorSpecError("per-unit thresholds must remain prohibited")
    if scope.get("operational_threshold_fitted_on") != "all_27_development_units":
        raise DetectorSpecError("the operational threshold population drifted")
    if scope.get("loco_thresholds_are_evaluation_only") is not True:
        raise DetectorSpecError("LOCO thresholds must stay evaluation-only")

    nonconformity = detector["nonconformity"]
    if nonconformity.get("comparison") != "strict_greater_than":
        raise DetectorSpecError("exceedance comparison drifted from strict greater-than")
    if nonconformity[RAW_LEVEL].get("standardised") is not False:
        raise DetectorSpecError("the raw-level score must remain unstandardised")
    if nonconformity[SCALE_INVARIANT].get("scale_invariant_by_construction") is not True:
        raise DetectorSpecError("the scale-invariant score lost its invariance claim")
    if nonconformity[SCALE_INVARIANT].get("invariance_test_required") is not True:
        raise DetectorSpecError("the frozen design requires an executed invariance test")

    episodes = detector["episodes"]
    if int(episodes["alarm_begins_after_consecutive_exceedances"]) < 1:
        raise DetectorSpecError("an alarm needs at least one exceedance")
    if int(episodes["quiet_days_required_for_new_episode"]) < 1:
        raise DetectorSpecError("episode separation needs at least one quiet day")
    if episodes.get("masked_days_are_observations") is not False:
        raise DetectorSpecError("masked days must not count as observations")
    if episodes.get("masked_gap_rule") != "segment_boundary":
        raise DetectorSpecError("the masked-gap rule drifted from segment boundaries")
    gap = episodes["masked_gap_state_machine"]
    for flag in ("reset_exceedance_counter", "reset_quiet_counter", "censored_episodes_reported_separately"):
        if gap.get(flag) is not True:
            raise DetectorSpecError(f"masked-gap rule {flag} drifted")
    if gap.get("bridge_episodes_across_gap") is not False:
        raise DetectorSpecError("episodes must never bridge a masked gap")
    if int(gap["after_gap_requires_fresh_consecutive_exceedances"]) != int(
        episodes["alarm_begins_after_consecutive_exceedances"]
    ):
        raise DetectorSpecError("post-gap alarm onset must match the frozen onset rule")

    target = detector["calibration_target"]
    if target.get("statistic") != "macro_average_episode_rate_across_units":
        raise DetectorSpecError("the calibration target drifted from the macro-average rate")
    if target.get("pooled_row_quantile_as_primary") is not False:
        raise DetectorSpecError("a pooled row quantile cannot become the primary target")
    if float(target["max_episodes_per_chokepoint_year"]) <= 0.0:
        raise DetectorSpecError("the target episode rate must be positive")
    if target["exposure_denominator"].get("masked_days_excluded") is not True:
        raise DetectorSpecError("exposure must exclude masked days")

    ties = detector["discrete_ties"]
    if ties.get("rule") != "smallest_threshold_whose_achieved_rate_is_at_or_below_target":
        raise DetectorSpecError("the discrete-tie rule drifted")
    if ties.get("report_achieved_rate") is not True or ties.get("report_requested_rate") is not True:
        raise DetectorSpecError("both requested and achieved rates must be reported")

    timing = detector["evaluation"]["context_scale_timing"]
    if timing.get("rule") != "refit_per_fold_and_horizon_on_history_through_that_fold_fit_end":
        raise DetectorSpecError("context-scale timing drifted from the frozen refit rule")
    if timing["drift_diagnostic"].get("required") is not True:
        raise DetectorSpecError("the context-scale drift diagnostic is required")

    for name in ("threshold_loco", "end_to_end_loco"):
        if detector["evaluation"][name].get("enabled") is not True:
            raise DetectorSpecError(f"{name} must remain enabled")

    eligibility = detector["eligibility"]
    if eligibility.get("hormuz_excluded") is not True:
        raise DetectorSpecError("Hormuz must stay out of calibration")
    if eligibility.get("hyperparameter_validation_excluded") is not True:
        raise DetectorSpecError("the 2024 selection year must stay out of calibration")
    if eligibility.get("event_masked_unit_days_excluded") is not True:
        raise DetectorSpecError("event-masked unit-days must stay out of calibration")
    declared = tuple(eligibility["residual_roles"])
    frozen_eligible = tuple(
        role
        for role, cfg in spec["rolling_origin"]["residual_roles"].items()
        if bool(cfg["detector_calibration_eligible"])
    )
    if set(declared) != set(frozen_eligible):
        raise DetectorSpecError(
            "the detector's eligible residual roles disagree with the frozen rolling-origin roles: "
            f"{sorted(declared)} against {sorted(frozen_eligible)}"
        )
    if pd.Timestamp(eligibility["calibration_end"]) != pd.Timestamp(
        spec["dates"]["detector_calibration_end"]
    ):
        raise DetectorSpecError("the detector calibration end drifted from the frozen date")

    forms = tuple(spec["detector_contract"]["forms"])
    if forms != DETECTOR_FORMS:
        raise DetectorSpecError(f"detector forms drifted from {DETECTOR_FORMS}, got {forms}")


# ---------------------------------------------------------------------------
# Nonconformity scores
# ---------------------------------------------------------------------------


def raw_level_score(prediction: np.ndarray, actual: np.ndarray) -> np.ndarray:
    """`s_raw = yhat - y`; positive means the outcome fell below the forecast."""
    return np.asarray(prediction, dtype="float64") - np.asarray(actual, dtype="float64")


def scale_invariant_score(
    prediction: np.ndarray,
    actual: np.ndarray,
    context_scale: np.ndarray,
) -> np.ndarray:
    """`s_scaled = (yhat - y) / context_scale`, dimensionless by construction."""
    scale = np.asarray(context_scale, dtype="float64")
    if not np.isfinite(scale).all() or (scale <= 0.0).any():
        raise ValueError("scale-invariant scoring requires strictly positive context scales")
    return raw_level_score(prediction, actual) / scale


# ---------------------------------------------------------------------------
# Episode state machine
# ---------------------------------------------------------------------------


def segment_boundaries(dates: pd.DatetimeIndex) -> np.ndarray:
    """Split an eligible-day sequence wherever the calendar is not contiguous.

    Masked unit-days and role-ineligible days are absent from the eligible
    sequence, so every gap of any origin appears here as a calendar break.  The
    frozen rule makes each such break a segment boundary, which is what stops an
    episode bridging Panama's masked year, the open-ended Red Sea and Kerch
    masks, or the withheld 2024 selection year.
    """
    values = pd.DatetimeIndex(dates)
    if not values.is_monotonic_increasing or values.has_duplicates:
        raise ValueError("episode dates must be unique and chronological")
    if len(values) == 0:
        return np.zeros(0, dtype="int64")
    steps = np.diff(values.to_numpy(dtype="datetime64[D]")).astype("int64")
    starts = np.concatenate(([0], np.nonzero(steps != 1)[0] + 1))
    return starts.astype("int64")


@dataclass(frozen=True)
class EpisodeCurve:
    """Episode counts for one unit as a step function of the threshold.

    `breakpoints` ascends and starts at -inf, which is the regime where every
    eligible day exceeds.  Because exceedance is strict (`score > threshold`),
    the exceedance set is constant on `[breakpoints[k], breakpoints[k+1])`, so
    evaluating at the breakpoints characterises the whole real line.
    """

    unit: str
    breakpoints: np.ndarray
    episodes: np.ndarray
    censored: np.ndarray
    total_duration: np.ndarray
    eligible_days: int
    exposure_years: float

    def episodes_at(self, thresholds: np.ndarray) -> np.ndarray:
        index = np.searchsorted(self.breakpoints, np.asarray(thresholds, dtype="float64"), side="right") - 1
        return self.episodes[np.clip(index, 0, len(self.breakpoints) - 1)]

    def censored_at(self, thresholds: np.ndarray) -> np.ndarray:
        index = np.searchsorted(self.breakpoints, np.asarray(thresholds, dtype="float64"), side="right") - 1
        return self.censored[np.clip(index, 0, len(self.breakpoints) - 1)]

    def duration_at(self, thresholds: np.ndarray) -> np.ndarray:
        index = np.searchsorted(self.breakpoints, np.asarray(thresholds, dtype="float64"), side="right") - 1
        return self.total_duration[np.clip(index, 0, len(self.breakpoints) - 1)]

    def rate_at(self, thresholds: np.ndarray) -> np.ndarray:
        return self.episodes_at(thresholds) / self.exposure_years


def count_episodes(
    scores: np.ndarray,
    thresholds: np.ndarray,
    segment_starts: np.ndarray,
    *,
    onset: int,
    quiet_days: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Run the frozen episode machine over every candidate threshold at once.

    The recursion is sequential in time and independent across thresholds, so
    the loop runs over days and the state is a vector over candidates.  Returns
    (episodes, censored, total_episode_days), each indexed by candidate.
    """
    scores = np.asarray(scores, dtype="float64")
    candidates = np.asarray(thresholds, dtype="float64")
    n_candidates = len(candidates)
    episodes = np.zeros(n_candidates, dtype="int64")
    censored = np.zeros(n_candidates, dtype="int64")
    duration = np.zeros(n_candidates, dtype="int64")
    if len(scores) == 0 or n_candidates == 0:
        return episodes, censored, duration

    bounds = list(segment_starts) + [len(scores)]
    for lo, hi in zip(bounds[:-1], bounds[1:]):
        run = np.zeros(n_candidates, dtype="int64")
        quiet = np.zeros(n_candidates, dtype="int64")
        open_episode = np.zeros(n_candidates, dtype=bool)
        # Days since the open episode's last exceedance are provisional: they
        # only become part of the episode if another exceedance follows, so
        # they are held here and either committed or discarded at closure.
        pending = np.zeros(n_candidates, dtype="int64")
        for value in scores[lo:hi]:
            exceeds = value > candidates
            run = np.where(exceeds, run + 1, 0)
            quiet = np.where(exceeds, 0, quiet + 1)

            opening = exceeds & ~open_episode & (run >= onset)
            episodes += opening
            # The episode is dated from the first of its consecutive
            # exceedances, so opening commits that whole opening run.
            duration += np.where(opening, onset, 0)
            open_episode |= opening

            continuing = exceeds & open_episode & ~opening
            duration += np.where(continuing, pending + 1, 0)
            pending = np.where(exceeds, 0, pending + 1)

            closing = ~exceeds & open_episode & (quiet >= quiet_days)
            open_episode &= ~closing
            pending = np.where(closing, 0, pending)
        censored += open_episode
        # A censored episode is terminated on the last eligible day of the
        # segment, so its provisional tail is part of it.
        duration += np.where(open_episode, pending, 0)
    return episodes, censored, duration


def build_episode_curve(
    unit: str,
    dates: pd.DatetimeIndex,
    scores: np.ndarray,
    spec: Mapping,
) -> EpisodeCurve:
    """Characterise one unit's episode behaviour across every attainable threshold."""
    episodes_cfg = spec["detector"]["episodes"]
    onset = int(episodes_cfg["alarm_begins_after_consecutive_exceedances"])
    quiet_days = int(episodes_cfg["quiet_days_required_for_new_episode"])
    scores = np.asarray(scores, dtype="float64")
    if len(scores) != len(dates):
        raise ValueError("episode scores and dates must align")
    if not np.isfinite(scores).all():
        raise ValueError(f"unit {unit!r} carries a non-finite residual score")

    starts = segment_boundaries(dates)
    breakpoints = np.concatenate(([-np.inf], np.unique(scores)))
    episodes, censored, duration = count_episodes(
        scores, breakpoints, starts, onset=onset, quiet_days=quiet_days
    )
    eligible_days = int(len(scores))
    return EpisodeCurve(
        unit=unit,
        breakpoints=breakpoints,
        episodes=episodes,
        censored=censored,
        total_duration=duration,
        eligible_days=eligible_days,
        exposure_years=eligible_days / DAYS_PER_YEAR,
    )


# ---------------------------------------------------------------------------
# Threshold calibration
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ThresholdSolution:
    """The calibrated threshold and the evidence needed to judge it.

    `threshold` is the operational answer.  `literal_rule_threshold` is what a
    word-by-word reading of `discrete_ties.rule` returns; the two differ
    whenever the episode-rate curve is non-monotone, and `literal_rule_degenerate`
    says so explicitly.  See `calibrate_threshold` for why the operational
    answer is the one it is.
    """

    threshold: float
    requested_rate: float
    achieved_rate: float
    attainable: bool
    n_units: int
    n_candidates: int
    monotone: bool
    monotonicity_violations: int
    max_upward_step: float
    literal_rule_threshold: float
    literal_rule_achieved_rate: float
    literal_rule_exceedance_share: float
    literal_rule_degenerate: bool


def candidate_thresholds(curves: Sequence[EpisodeCurve]) -> np.ndarray:
    """Every attainable threshold: the union of the units' observed scores."""
    values = np.unique(
        np.concatenate([curve.breakpoints[1:] for curve in curves])
        if curves
        else np.zeros(0, dtype="float64")
    )
    return values


def macro_average_rate(
    curves: Sequence[EpisodeCurve],
    candidates: np.ndarray,
) -> np.ndarray:
    """Mean over units of that unit's episodes per exposure-year, per candidate.

    Each chokepoint gets equal weight in the quantity being controlled.  A
    pooled row-level quantile would instead let the long or high-volume series
    set the threshold, which the frozen design rejects.
    """
    if not curves:
        raise ValueError("the macro average needs at least one unit")
    stacked = np.vstack([curve.rate_at(candidates) for curve in curves])
    return stacked.mean(axis=0)


def calibrate_threshold(
    curves: Sequence[EpisodeCurve],
    spec: Mapping,
    *,
    candidates: np.ndarray | None = None,
) -> ThresholdSolution:
    """Calibrate one transferable threshold against the macro-average episode rate.

    Scores tie, so the requested rate is usually unattainable exactly.  The
    frozen rule takes the attainable threshold on the conservative side and
    reports the achieved rate next to the requested one.

    The episode rate is **not** monotone in the threshold, which the frozen rule
    was written without.  Raising a threshold can split one long episode in two
    by opening a quiet gap wide enough to close the first, so the curve rises
    before it falls.  At the bottom of the range the effect is extreme: when
    every day exceeds, a unit's whole record collapses into one unending episode
    per segment, so the rate falls back *below* target for a detector that fires
    every single day.

    A word-by-word reading of `discrete_ties.rule` -- "smallest threshold whose
    achieved rate is at or below target" -- therefore selects that degenerate
    floor.  The block's own stated reason says to "take the attainable threshold
    on the conservative side", which the floor plainly is not, so the operational
    answer is the smallest threshold from which the rate stays at or below target
    for every higher threshold too.  Both are returned, and the literal reading's
    exceedance share is reported so the difference is visible rather than
    asserted.  This discrepancy is flagged for Mher's ratification; it is not a
    silent rewrite of a frozen rule.
    """
    target = float(spec["detector"]["calibration_target"]["max_episodes_per_chokepoint_year"])
    grid = candidate_thresholds(curves) if candidates is None else np.asarray(candidates, dtype="float64")
    if len(grid) == 0:
        raise ValueError("threshold calibration needs at least one attainable candidate")
    rates = macro_average_rate(curves, grid)

    steps = np.diff(rates)
    violations = int(np.count_nonzero(steps > 0.0))
    max_upward = float(steps.max()) if len(steps) else 0.0

    # The literal reading, computed so the degeneracy can be reported.
    literal_idx = np.nonzero(rates <= target)[0]
    literal_index = int(literal_idx[0]) if len(literal_idx) else int(np.argmin(rates))

    # The operational reading: no higher threshold may breach the target either.
    suffix_max = np.maximum.accumulate(rates[::-1])[::-1]
    operational_idx = np.nonzero(suffix_max <= target)[0]
    if len(operational_idx) == 0:
        # Every attainable threshold, including the largest, fires too often.
        index = int(len(grid) - 1)
        attainable = False
    else:
        index = int(operational_idx[0])
        attainable = True

    observed = np.concatenate([curve.breakpoints[1:] for curve in curves])
    literal_share = float(np.mean(observed > grid[literal_index])) if len(observed) else 0.0

    return ThresholdSolution(
        threshold=float(grid[index]),
        requested_rate=target,
        achieved_rate=float(rates[index]),
        attainable=attainable,
        n_units=len(curves),
        n_candidates=int(len(grid)),
        monotone=violations == 0,
        monotonicity_violations=violations,
        max_upward_step=max_upward,
        literal_rule_threshold=float(grid[literal_index]),
        literal_rule_achieved_rate=float(rates[literal_index]),
        literal_rule_exceedance_share=literal_share,
        literal_rule_degenerate=bool(literal_index != index),
    )


# ---------------------------------------------------------------------------
# Rolling residual production
# ---------------------------------------------------------------------------


def fold_context_scales(
    panel: pd.DataFrame,
    spec: Mapping,
    *,
    measurement_state: str,
    context_end: pd.Timestamp,
) -> dict[str, object]:
    """Refit every unit's context scale on its own history through `context_end`.

    The frozen object is this transformation, not one numerical scale, so each
    fold and horizon normalises on the information that would actually have been
    available at its own `fit_end`.
    """
    context_start = spec["model"]["context_normalisation"]["context_start"]
    scales: dict[str, object] = {}
    for unit in development_units(spec):
        scales[unit] = fit_context_scale(
            panel[unit],
            spec,
            measurement_state=measurement_state,
            context_start=context_start,
            context_end=context_end,
        )
    return scales


def build_rolling_fit_geometry(
    spec: Mapping,
    fold: RollingOriginFold,
    horizon: int,
    measurement_state: str,
) -> pd.DataFrame:
    """Training tasks for one fold and horizon, ending at its own `fit_end`."""
    fit_end = fold.score_start - pd.Timedelta(days=int(horizon))
    dates = pd.date_range(_minimum_supported_target(spec), fit_end, freq="D")
    if len(dates) == 0:
        raise ValueError(f"{fold.fold_id} h={horizon} has no supported training targets")
    geometry = build_task_geometry(
        dates,
        development_units(spec),
        [int(horizon)],
        measurement_state=measurement_state,
        task_role="rolling_fit",
        seed=int(spec["tasks"]["seed"]),
        fold_id=fold.fold_id,
        extra_columns={
            "fit_start": fold.fit_start,
            "fit_end": fit_end,
            "score_start": fold.score_start,
            "score_end": fold.score_end,
        },
    )
    validate_task_table(geometry, spec)
    return geometry


@dataclass(frozen=True)
class UnitMoments:
    """Per-unit cross-moments of one fold's standardised-space design.

    Holding moments per unit makes every leave-one-chokepoint-out refit a sum
    over the retained units rather than a fresh pass over the rows, which is
    what makes the end-to-end LOCO tractable.  The arithmetic is exact: sums
    are additive, and the pooled standardiser and the ridge normal equations
    are both functions of these sums alone.
    """

    unit: str
    n: int
    sum_x: np.ndarray
    sum_xx: np.ndarray
    sum_y: float
    sum_xy: np.ndarray


def unit_moments(
    design: np.ndarray,
    target: np.ndarray,
    units: np.ndarray,
    ordered_units: Sequence[str],
) -> dict[str, UnitMoments]:
    moments: dict[str, UnitMoments] = {}
    for unit in ordered_units:
        mask = units == unit
        block = design[mask]
        response = target[mask]
        moments[unit] = UnitMoments(
            unit=unit,
            n=int(block.shape[0]),
            sum_x=block.sum(axis=0),
            sum_xx=block.T @ block,
            sum_y=float(response.sum()),
            sum_xy=block.T @ response,
        )
    return moments


def ridge_from_moments(
    moments: Sequence[UnitMoments],
    alpha: float,
    zero_variance_scale: float,
) -> tuple[np.ndarray, float, np.ndarray, np.ndarray]:
    """Fit the pooled standardiser and ridge from summed per-unit moments.

    Returns (coefficients, intercept, means, scales) in the *unstandardised*
    context-normalised space, so a caller predicts with `x @ coef + intercept`
    without restandardising.  This is the same estimator as
    `TrainingOnlyStandardizer` followed by `RidgeGlobalModel`; the equivalence
    is asserted in the tests rather than assumed.
    """
    n = sum(moment.n for moment in moments)
    if n == 0:
        raise ValueError("a ridge fit needs at least one training row")
    sum_x = sum(moment.sum_x for moment in moments)
    sum_xx = sum(moment.sum_xx for moment in moments)
    sum_y = sum(moment.sum_y for moment in moments)
    sum_xy = sum(moment.sum_xy for moment in moments)

    means = sum_x / n
    variance = np.maximum(np.diag(sum_xx) / n - means**2, 0.0)
    scales = np.sqrt(variance)
    scales = np.where(scales == 0.0, float(zero_variance_scale), scales)

    # Standardised, then centred. The standardiser already removes the mean over
    # exactly these rows, so the centred design is the standardised design and
    # the ridge intercept is the target mean.
    inv = 1.0 / scales
    centred_xx = (sum_xx - np.outer(sum_x, sum_x) / n) * np.outer(inv, inv)
    centred_xy = (sum_xy - sum_x * (sum_y / n)) * inv

    gram = centred_xx.copy()
    gram[np.diag_indices_from(gram)] += float(alpha)
    factor = np.linalg.cholesky(gram)
    beta = np.linalg.solve(factor.T, np.linalg.solve(factor, centred_xy))
    if not np.isfinite(beta).all():
        raise ValueError("ridge solution from moments is not finite")

    # Fold the standardisation back into the coefficients so the caller works in
    # context-normalised units.
    coefficients = beta * inv
    intercept = float(sum_y / n - means @ coefficients)
    return coefficients, intercept, means, scales


def _normalised_design(
    materialised: pd.DataFrame,
    scales: Mapping[str, object],
    spec: Mapping,
    columns: Sequence[str],
) -> tuple[pd.DataFrame, np.ndarray, np.ndarray]:
    normalised = apply_context_normalisation(materialised, scales, spec)
    design = normalised.loc[:, list(columns)].to_numpy(dtype="float64")
    target = normalised["z_target"].to_numpy(dtype="float64")
    if not np.isfinite(design).all() or not np.isfinite(target).all():
        raise ValueError("normalised fold design is not finite")
    return normalised, design, target


def select_loco_alphas(
    spec: Mapping,
    panel: pd.DataFrame,
    *,
    measurement_state: str,
) -> dict[int, dict[str, float]]:
    """Reselect the ridge penalty once per held-out unit and horizon.

    End-to-end LOCO withholds the unit from hyperparameter selection too, so the
    penalty cannot be inherited from the A2 run that saw every unit.  This
    reproduces A2's selection -- mean MASE over the frozen 2024 tasks, ties to
    the smallest penalty -- on the 26 retained units.  It is the frozen design's
    405 closed-form fits: 27 units, 3 horizons, 5 penalties.
    """
    from .global_forecaster import build_development_geometry, mase_denominators

    columns = feature_columns(spec)
    units = development_units(spec)
    alphas = [float(value) for value in spec["model"]["global_model"]["grid"]["alpha"]]
    zero_variance = float(spec["scaling"]["zero_variance_scale"])

    geometry = build_development_geometry(spec, measurement_state)
    materialised = materialize_task_features(panel, geometry, spec)
    scales = fit_unit_context_scales(panel, spec, measurement_state=measurement_state)
    normalised = apply_context_normalisation(materialised, scales, spec)
    denominators = mase_denominators(panel, spec)

    development = normalised.loc[normalised["task_role"].eq("development_fit")]
    validation = normalised.loc[normalised["task_role"].eq("hyperparameter_validation")]
    assert_task_access(development, "fitting", spec)
    assert_task_access(validation, "hyperparameter_selection", spec)

    selected: dict[int, dict[str, float]] = {}
    for horizon in (int(value) for value in spec["tasks"]["horizons_days"]):
        dev_h = development.loc[development["horizon_days"].eq(horizon)]
        val_h = validation.loc[validation["horizon_days"].eq(horizon)]
        moments = unit_moments(
            dev_h.loc[:, list(columns)].to_numpy(dtype="float64"),
            dev_h["z_target"].to_numpy(dtype="float64"),
            dev_h["unit"].to_numpy(),
            units,
        )
        val_design = val_h.loc[:, list(columns)].to_numpy(dtype="float64")
        val_units = val_h["unit"].to_numpy()
        val_actual = val_h["y_target"].to_numpy(dtype="float64")

        chosen: dict[str, float] = {}
        for held_out in units:
            retained = [moments[unit] for unit in units if unit != held_out]
            keep = val_units != held_out
            best_alpha = None
            best_score = np.inf
            for alpha in alphas:
                coefficients, intercept, _, _ = ridge_from_moments(
                    retained, alpha, zero_variance
                )
                z_prediction = val_design[keep] @ coefficients + intercept
                prediction = denormalise(
                    z_prediction, pd.Series(val_units[keep]), scales
                )
                error = np.abs(val_actual[keep] - prediction)
                per_unit = [
                    float(np.mean(error[val_units[keep] == unit])) / float(denominators[unit])
                    for unit in units
                    if unit != held_out
                ]
                score = float(np.mean(per_unit))
                # Ties go to the smallest penalty, as in A2.
                if score < best_score - 1e-12:
                    best_score = score
                    best_alpha = alpha
            if best_alpha is None:
                raise ValueError(f"penalty selection failed for held-out {held_out!r}")
            chosen[held_out] = float(best_alpha)
        selected[horizon] = chosen
    return selected


@dataclass(frozen=True)
class FoldResiduals:
    """One fold and horizon's residual rows.

    `loco_predictions` has one column per held-out unit, in
    `development_units(spec)` order, holding that model's prediction for *every*
    row.  The retained units' columns are needed because the end-to-end LOCO
    threshold is calibrated on them, not only on the held-out unit.
    """

    frame: pd.DataFrame
    context_scales: dict[str, float]
    context_ends: dict[str, pd.Timestamp]
    loco_predictions: np.ndarray | None


def residuals_for_fold(
    spec: Mapping,
    panel: pd.DataFrame,
    fold: RollingOriginFold,
    horizon: int,
    residual_geometry: pd.DataFrame,
    *,
    measurement_state: str,
    alpha: float,
    loco_alphas: Mapping[str, float] | None = None,
) -> FoldResiduals:
    """Produce operational and LOCO predictions for one fold and horizon.

    The operational path runs through the sealed A2 estimator classes, so the
    reported residuals come from the same code A2 was accepted on.  The LOCO
    variants run through the moment path, which the tests pin to the sealed
    classes.
    """
    columns = feature_columns(spec)
    units = development_units(spec)
    fit_end = fold.score_start - pd.Timedelta(days=int(horizon))

    scales = fold_context_scales(
        panel, spec, measurement_state=measurement_state, context_end=fit_end
    )

    fit_geometry = build_rolling_fit_geometry(spec, fold, int(horizon), measurement_state)
    fit_rows = materialize_task_features(panel, fit_geometry, spec)
    assert_task_access(fit_rows, "fitting", spec)
    fit_normalised, fit_design, fit_target = _normalised_design(fit_rows, scales, spec, columns)

    score_rows = residual_geometry.loc[
        residual_geometry["fold_id"].eq(fold.fold_id)
        & residual_geometry["horizon_days"].eq(int(horizon))
    ].reset_index(drop=True)
    if score_rows.empty:
        raise ValueError(f"{fold.fold_id} h={horizon} has no residual tasks")
    score_materialised = materialize_task_features(panel, score_rows, spec)
    score_normalised, score_design, _ = _normalised_design(
        score_materialised, scales, spec, columns
    )

    # Operational model: the sealed A2 estimator on every development unit.
    standardiser = TrainingOnlyStandardizer.fit(fit_normalised, columns, spec)
    model = RidgeGlobalModel.fit(
        standardiser.transform(fit_normalised, spec),
        columns,
        spec,
        horizon_days=int(horizon),
        alpha=float(alpha),
    )
    z_prediction = model.predict(standardiser.transform(score_normalised, spec))

    output = score_materialised.loc[
        :, ["unit", "horizon_days", "target_timestamp", "fold_id", "residual_role", "y_target"]
    ].copy()
    output["prediction"] = denormalise(z_prediction, output["unit"], scales)
    output["context_scale"] = output["unit"].map(lambda unit: float(scales[unit].scale))
    output["context_center"] = output["unit"].map(lambda unit: float(scales[unit].center))
    output["fit_end"] = fit_end

    loco_predictions: np.ndarray | None = None
    if loco_alphas is not None:
        zero_variance = float(spec["scaling"]["zero_variance_scale"])
        moments = unit_moments(
            fit_design, fit_target, fit_normalised["unit"].to_numpy(), units
        )
        loco_predictions = np.empty((len(output), len(units)), dtype="float64")
        for column, held_out in enumerate(units):
            retained = [moments[unit] for unit in units if unit != held_out]
            coefficients, intercept, _, _ = ridge_from_moments(
                retained, float(loco_alphas[held_out]), zero_variance
            )
            loco_predictions[:, column] = denormalise(
                score_design @ coefficients + intercept, output["unit"], scales
            )
        if not np.isfinite(loco_predictions).all():
            raise ValueError("end-to-end LOCO produced a non-finite prediction")

    return FoldResiduals(
        frame=output,
        context_scales={unit: float(scale.scale) for unit, scale in scales.items()},
        context_ends={unit: pd.Timestamp(scale.context_end) for unit, scale in scales.items()},
        loco_predictions=loco_predictions,
    )


def eligible_residuals(
    residuals: pd.DataFrame,
    spec: Mapping,
    mask: EventMask,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Keep only rows the frozen contract admits into calibration."""
    eligible_roles = set(spec["detector"]["eligibility"]["residual_roles"])
    kept = residuals.loc[residuals["residual_role"].isin(eligible_roles)].copy()
    applied = apply_event_mask(kept, mask)
    admitted = applied.eligible
    end = pd.Timestamp(spec["detector"]["eligibility"]["calibration_end"])
    if pd.to_datetime(admitted["target_timestamp"]).max() > end:
        raise LeakageError("calibration residuals reach beyond the frozen calibration end")
    hormuz = spec["population"]["hormuz_unit"]
    if admitted["unit"].eq(hormuz).any():
        raise LeakageError("a Hormuz row reached detector calibration")
    return admitted, applied.excluded


def score_frame(
    residuals: pd.DataFrame,
    form: str,
    *,
    prediction_column: str = "prediction",
) -> np.ndarray:
    """Nonconformity scores for one detector form."""
    prediction = residuals[prediction_column].to_numpy(dtype="float64")
    actual = residuals["y_target"].to_numpy(dtype="float64")
    if form == RAW_LEVEL:
        return raw_level_score(prediction, actual)
    if form == SCALE_INVARIANT:
        return scale_invariant_score(
            prediction, actual, residuals["context_scale"].to_numpy(dtype="float64")
        )
    raise ValueError(f"unknown detector form {form!r}")


def curves_by_unit(
    residuals: pd.DataFrame,
    spec: Mapping,
    form: str,
    *,
    prediction_column: str = "prediction",
) -> dict[str, EpisodeCurve]:
    """One episode curve per development unit, in unit order."""
    scores = score_frame(residuals, form, prediction_column=prediction_column)
    frame = residuals.loc[:, ["unit", "target_timestamp"]].copy()
    frame["score"] = scores
    frame = frame.sort_values(["unit", "target_timestamp"], kind="mergesort")
    curves: dict[str, EpisodeCurve] = {}
    for unit, rows in frame.groupby("unit", sort=True):
        curves[unit] = build_episode_curve(
            unit,
            pd.DatetimeIndex(pd.to_datetime(rows["target_timestamp"])),
            rows["score"].to_numpy(dtype="float64"),
            spec,
        )
    return curves


def digest_frame(frame: pd.DataFrame) -> str:
    payload = frame.to_csv(index=False, lineterminator="\n").encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def digest_payload(payload: object) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    ).hexdigest()


__all__ = [
    "DETECTOR_FORMS",
    "RAW_LEVEL",
    "SCALE_INVARIANT",
    "DetectorSpecError",
    "EpisodeCurve",
    "FoldResiduals",
    "ThresholdSolution",
    "UnitMoments",
    "build_episode_curve",
    "build_rolling_fit_geometry",
    "calibrate_threshold",
    "candidate_thresholds",
    "count_episodes",
    "curves_by_unit",
    "digest_frame",
    "digest_payload",
    "eligible_residuals",
    "fold_context_scales",
    "macro_average_rate",
    "raw_level_score",
    "residuals_for_fold",
    "ridge_from_moments",
    "scale_invariant_score",
    "score_frame",
    "segment_boundaries",
    "select_loco_alphas",
    "unit_moments",
    "validate_detector_spec",
]
