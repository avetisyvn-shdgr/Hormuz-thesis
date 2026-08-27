"""Phase A3 detector-calibration tests.

Two kinds of test live here and they are kept apart deliberately.

*Synthetic tests* build sequences whose episode structure is known by
construction and check the frozen rules reproduce it.  They are behaviour
checks, not results: no synthetic number here says anything about a chokepoint.

*Leakage tests* try to push forbidden rows and forbidden windows through the
calibration entry points and require them to be refused.  A phase that fits
nothing can still leak, so these run against the real frozen specification.
"""
from __future__ import annotations

from copy import deepcopy

import numpy as np
import pandas as pd
import pytest

from lngfreight.detector_calibration import (
    DETECTOR_FORMS,
    RAW_LEVEL,
    SCALE_INVARIANT,
    DetectorSpecError,
    build_episode_curve,
    build_rolling_fit_geometry,
    calibrate_threshold,
    candidate_thresholds,
    count_episodes,
    curves_by_unit,
    eligible_residuals,
    fold_context_scales,
    macro_average_rate,
    raw_level_score,
    ridge_from_moments,
    scale_invariant_score,
    score_frame,
    segment_boundaries,
    unit_moments,
    validate_detector_spec,
)
from lngfreight.disruption_detector import fit_context_scale, load_event_mask
from lngfreight.global_forecaster import (
    LeakageError,
    RidgeGlobalModel,
    TrainingOnlyStandardizer,
    apply_context_normalisation,
    assert_task_access,
    build_task_geometry,
    development_units,
    feature_columns,
    fit_unit_context_scales,
    load_detection_spec,
    materialize_task_features,
    rolling_origin_folds,
)


@pytest.fixture(scope="module")
def spec() -> dict:
    loaded, _ = load_detection_spec()
    return loaded


ONSET = 2
QUIET = 7


def _episode_spec() -> dict:
    return {
        "detector": {
            "episodes": {
                "alarm_begins_after_consecutive_exceedances": ONSET,
                "quiet_days_required_for_new_episode": QUIET,
            },
            "calibration_target": {"max_episodes_per_chokepoint_year": 2},
        }
    }


def _pattern(pattern: str, dates: pd.DatetimeIndex | None = None):
    """Run the frozen machine over an X/. pattern at threshold 0.5."""
    scores = np.array([1.0 if char == "X" else 0.0 for char in pattern], dtype="float64")
    if dates is None:
        dates = pd.date_range("2021-01-01", periods=len(pattern), freq="D")
    episodes, censored, duration = count_episodes(
        scores,
        np.array([0.5]),
        segment_boundaries(dates),
        onset=ONSET,
        quiet_days=QUIET,
    )
    return int(episodes[0]), int(censored[0]), int(duration[0])


# ---------------------------------------------------------------------------
# Synthetic: the episode state machine
# ---------------------------------------------------------------------------


def test_one_exceedance_is_not_an_alarm_and_two_consecutive_are():
    assert _pattern("X")[0] == 0
    assert _pattern("X.X")[0] == 0
    assert _pattern("XX")[0] == 1


def test_quiet_days_separate_episodes_exactly_at_the_frozen_boundary():
    # Six quiet days leave the episode open, so the later pair extends it.
    assert _pattern("XX" + "." * (QUIET - 1) + "XX")[0] == 1
    # Seven close it, so the later pair opens a second.
    assert _pattern("XX" + "." * QUIET + "XX")[0] == 2


def test_a_long_run_is_one_episode_whose_duration_counts_its_days():
    episodes, _, duration = _pattern("XXXXX")
    assert episodes == 1
    assert duration == 5


def test_trailing_quiet_days_close_an_episode_without_censoring_it():
    episodes, censored, duration = _pattern(".." + "XX" + "." * QUIET)
    assert (episodes, censored, duration) == (1, 0, 2)


def test_an_episode_still_open_at_the_end_is_right_censored():
    episodes, censored, _ = _pattern("..XX..")
    assert (episodes, censored) == (1, 1)


def test_a_gap_is_a_segment_boundary_and_no_episode_bridges_it():
    dates = pd.DatetimeIndex(
        list(pd.date_range("2021-01-01", periods=2, freq="D"))
        + list(pd.date_range("2021-03-01", periods=2, freq="D"))
    )
    assert segment_boundaries(dates).tolist() == [0, 2]

    # One exceedance either side of the gap is not a pair: the counter resets.
    scores = np.array([1.0, 0.0, 0.0, 1.0])
    episodes, _, _ = count_episodes(
        scores, np.array([0.5]), segment_boundaries(dates), onset=ONSET, quiet_days=QUIET
    )
    assert int(episodes[0]) == 0

    # A pair either side is two separate episodes, both censored by the boundary.
    scores = np.ones(4)
    episodes, censored, _ = count_episodes(
        scores, np.array([0.5]), segment_boundaries(dates), onset=ONSET, quiet_days=QUIET
    )
    assert (int(episodes[0]), int(censored[0])) == (2, 2)


def test_the_withheld_2024_year_is_itself_a_segment_boundary(spec: dict):
    """2024 carries no admissible residual, so an episode cannot span it."""
    dates = pd.DatetimeIndex(
        list(pd.date_range("2023-12-30", "2023-12-31", freq="D"))
        + list(pd.date_range("2025-01-01", "2025-01-02", freq="D"))
    )
    scores = np.ones(4)
    episodes, censored, _ = count_episodes(
        scores, np.array([0.5]), segment_boundaries(dates), onset=ONSET, quiet_days=QUIET
    )
    assert (int(episodes[0]), int(censored[0])) == (2, 2)


def test_masked_unit_days_leave_the_eligible_sequence_and_so_break_the_run():
    """Removing a masked day mid-run must not silently join its neighbours."""
    full = pd.date_range("2021-01-01", periods=5, freq="D")
    scores = np.ones(5)
    joined, _, _ = count_episodes(
        scores, np.array([0.5]), segment_boundaries(full), onset=ONSET, quiet_days=QUIET
    )
    assert int(joined[0]) == 1

    masked = full.delete(2)
    split, censored, _ = count_episodes(
        np.ones(4), np.array([0.5]), segment_boundaries(masked), onset=ONSET, quiet_days=QUIET
    )
    assert int(split[0]) == 2
    assert int(censored[0]) == 2


# ---------------------------------------------------------------------------
# Synthetic: the episode curve and threshold calibration
# ---------------------------------------------------------------------------


def test_curve_reproduces_a_direct_evaluation_at_every_breakpoint():
    rng = np.random.default_rng(11)
    dates = pd.date_range("2021-01-01", periods=400, freq="D")
    scores = rng.normal(size=400)
    curve = build_episode_curve("synthetic", dates, scores, _episode_spec())

    for threshold in rng.choice(curve.breakpoints[1:], size=25, replace=False):
        direct, _, _ = count_episodes(
            scores,
            np.array([threshold]),
            segment_boundaries(dates),
            onset=ONSET,
            quiet_days=QUIET,
        )
        assert curve.episodes_at(np.array([threshold]))[0] == direct[0]


def test_a_threshold_above_every_score_never_fires():
    dates = pd.date_range("2021-01-01", periods=100, freq="D")
    scores = np.linspace(-1.0, 1.0, 100)
    curve = build_episode_curve("synthetic", dates, scores, _episode_spec())
    assert curve.episodes[-1] == 0
    assert curve.episodes_at(np.array([10.0]))[0] == 0


def test_exceedance_is_strict_so_a_tied_score_does_not_fire():
    dates = pd.date_range("2021-01-01", periods=4, freq="D")
    scores = np.array([5.0, 5.0, 5.0, 5.0])
    curve = build_episode_curve("synthetic", dates, scores, _episode_spec())
    # At threshold exactly 5.0 nothing exceeds; only below it does the pair fire.
    assert curve.episodes_at(np.array([5.0]))[0] == 0
    assert curve.episodes_at(np.array([4.999]))[0] == 1


def test_calibration_meets_the_target_and_reports_the_achieved_rate():
    """A synthetic panel with a controllable tail: the rule must hit target."""
    rng = np.random.default_rng(3)
    dates = pd.DatetimeIndex(
        list(pd.date_range("2021-01-01", "2023-12-31", freq="D"))
        + list(pd.date_range("2025-01-01", "2025-11-30", freq="D"))
    )
    curves = [
        build_episode_curve(f"unit_{index:02d}", dates, rng.normal(size=len(dates)), _episode_spec())
        for index in range(10)
    ]
    solution = calibrate_threshold(curves, _episode_spec())
    assert solution.attainable
    assert solution.achieved_rate <= solution.requested_rate
    assert solution.n_units == 10

    # No lower attainable threshold keeps every higher one at or below target.
    grid = candidate_thresholds(curves)
    rates = macro_average_rate(curves, grid)
    index = int(np.searchsorted(grid, solution.threshold))
    assert rates[index:].max() <= solution.requested_rate
    if index > 0:
        assert rates[index - 1 :].max() > solution.requested_rate


def test_the_episode_rate_is_not_monotone_and_the_literal_rule_is_degenerate():
    """The frozen tie rule, read literally, selects a fire-every-day threshold.

    This is the finding that must not be quietly smoothed over: when every day
    exceeds, a unit's record collapses into one unending episode per segment, so
    the macro rate drops back below target at the very bottom of the range.
    """
    rng = np.random.default_rng(7)
    dates = pd.DatetimeIndex(
        list(pd.date_range("2021-01-01", "2023-12-31", freq="D"))
        + list(pd.date_range("2025-01-01", "2025-11-30", freq="D"))
    )
    curves = [
        build_episode_curve(f"unit_{index:02d}", dates, rng.normal(size=len(dates)), _episode_spec())
        for index in range(12)
    ]
    solution = calibrate_threshold(curves, _episode_spec())

    assert not solution.monotone
    assert solution.monotonicity_violations > 0
    assert solution.literal_rule_degenerate
    assert solution.literal_rule_threshold < solution.threshold
    # The literal reading fires on essentially every unit-day yet still "passes".
    assert solution.literal_rule_exceedance_share > 0.9
    assert solution.literal_rule_achieved_rate <= solution.requested_rate


def test_the_largest_observed_score_always_gives_a_non_firing_threshold():
    """Strict `>` means the top candidate never fires, so a target is reachable.

    This is why `attainable` is a guard on a restricted grid rather than a
    property of the data: over the full candidate set it is always true.
    """
    dates = pd.date_range("2021-01-01", periods=60, freq="D")
    scores = np.tile([1.0, 1.0] + [0.0] * QUIET, 10)[:60]
    curves = [build_episode_curve("unit_a", dates, scores, _episode_spec())]
    spec = _episode_spec()
    spec["detector"]["calibration_target"]["max_episodes_per_chokepoint_year"] = 0.001
    solution = calibrate_threshold(curves, spec)
    assert solution.attainable is True
    assert solution.achieved_rate == 0.0
    assert curves[0].episodes_at(np.array([solution.threshold]))[0] == 0


def test_a_restricted_grid_that_cannot_meet_target_is_reported_unattainable():
    """Never invent a threshold outside the grid it was asked to search."""
    dates = pd.date_range("2021-01-01", periods=60, freq="D")
    scores = np.tile([1.0, 1.0] + [0.0] * QUIET, 10)[:60]
    curves = [build_episode_curve("unit_a", dates, scores, _episode_spec())]
    spec = _episode_spec()
    spec["detector"]["calibration_target"]["max_episodes_per_chokepoint_year"] = 0.001
    # Search only below the top score, where every candidate still fires.
    solution = calibrate_threshold(curves, spec, candidates=np.array([0.0, 0.5]))
    assert solution.attainable is False
    assert solution.achieved_rate > solution.requested_rate


# ---------------------------------------------------------------------------
# Synthetic: the two score forms
# ---------------------------------------------------------------------------


def test_raw_level_score_is_positive_when_the_outcome_falls_below_forecast():
    assert raw_level_score(np.array([10.0]), np.array([4.0]))[0] == pytest.approx(6.0)


def test_scale_invariant_score_is_unchanged_under_a_rescaled_series():
    """The frozen design requires this test to be executed, not asserted."""
    rng = np.random.default_rng(5)
    actual = rng.normal(loc=50.0, scale=5.0, size=200)
    prediction = actual + rng.normal(scale=2.0, size=200)
    scale = np.full(200, 7.4130)

    for factor in (0.5, 2.0, 13.7):
        rescaled = scale_invariant_score(prediction * factor, actual * factor, scale * factor)
        assert np.allclose(rescaled, scale_invariant_score(prediction, actual, scale))


def test_raw_level_score_is_not_scale_invariant():
    """The contrast between the two forms is the point; assert it exists."""
    actual = np.array([40.0, 60.0])
    prediction = np.array([44.0, 66.0])
    assert not np.allclose(
        raw_level_score(prediction * 2.0, actual * 2.0), raw_level_score(prediction, actual)
    )


def test_scale_invariant_scoring_refuses_a_non_positive_context_scale():
    with pytest.raises(ValueError):
        scale_invariant_score(np.array([1.0]), np.array([0.0]), np.array([0.0]))


# ---------------------------------------------------------------------------
# Synthetic: the moment path used for leave-one-chokepoint-out
# ---------------------------------------------------------------------------


def _synthetic_fit_frame(spec: dict) -> tuple[pd.DataFrame, tuple[str, ...]]:
    """A small, real-shaped training table built from a synthetic panel."""
    units = ["dover_strait", "suez_canal", "korea_strait"]
    index = pd.date_range("2019-01-01", "2023-12-31", freq="D")
    trend = np.arange(len(index), dtype="float64")
    rng = np.random.default_rng(19)
    panel = pd.DataFrame(
        {
            "dover_strait": 20.0 + 0.01 * trend + np.sin(trend / 7.0) + rng.normal(scale=0.5, size=len(index)),
            "suez_canal": 15.0 + 0.02 * trend + np.cos(trend / 11.0) + rng.normal(scale=0.5, size=len(index)),
            "korea_strait": 30.0 + 0.005 * trend + np.sin(trend / 13.0) + rng.normal(scale=0.5, size=len(index)),
        },
        index=index,
    )
    geometry = build_task_geometry(
        pd.date_range("2023-01-01", "2023-12-31", freq="D"),
        units,
        [7],
        measurement_state="july",
        task_role="development_fit",
        seed=spec["tasks"]["seed"],
    )
    materialised = materialize_task_features(panel, geometry, spec)
    scales = {
        unit: fit_context_scale(
            panel[unit],
            spec,
            measurement_state="july",
            context_start="2019-01-01",
            context_end="2023-12-31",
        )
        for unit in units
    }
    return apply_context_normalisation(materialised, scales, spec), feature_columns(spec)


def test_moment_ridge_reproduces_the_sealed_estimator(spec: dict):
    """The fast LOCO path must be the same estimator as the accepted A2 one."""
    frame, columns = _synthetic_fit_frame(spec)
    alpha = 100.0

    standardiser = TrainingOnlyStandardizer.fit(frame, columns, spec)
    sealed = RidgeGlobalModel.fit(
        standardiser.transform(frame, spec), columns, spec, horizon_days=7, alpha=alpha
    )
    sealed_prediction = sealed.predict(standardiser.transform(frame, spec))

    moments = unit_moments(
        frame.loc[:, list(columns)].to_numpy(dtype="float64"),
        frame["z_target"].to_numpy(dtype="float64"),
        frame["unit"].to_numpy(),
        sorted(set(frame["unit"])),
    )
    coefficients, intercept, _, _ = ridge_from_moments(
        list(moments.values()), alpha, float(spec["scaling"]["zero_variance_scale"])
    )
    moment_prediction = (
        frame.loc[:, list(columns)].to_numpy(dtype="float64") @ coefficients + intercept
    )
    assert np.allclose(moment_prediction, sealed_prediction, rtol=1e-8, atol=1e-8)


def test_moment_subsetting_equals_refitting_without_the_held_out_unit(spec: dict):
    """Dropping a unit's moment block must equal refitting on the other units."""
    frame, columns = _synthetic_fit_frame(spec)
    alpha = 100.0
    units = sorted(set(frame["unit"]))
    held_out = units[0]

    retained_frame = frame.loc[frame["unit"].ne(held_out)].reset_index(drop=True)
    standardiser = TrainingOnlyStandardizer.fit(retained_frame, columns, spec)
    sealed = RidgeGlobalModel.fit(
        standardiser.transform(retained_frame, spec), columns, spec, horizon_days=7, alpha=alpha
    )

    moments = unit_moments(
        frame.loc[:, list(columns)].to_numpy(dtype="float64"),
        frame["z_target"].to_numpy(dtype="float64"),
        frame["unit"].to_numpy(),
        units,
    )
    coefficients, intercept, _, _ = ridge_from_moments(
        [moments[unit] for unit in units if unit != held_out],
        alpha,
        float(spec["scaling"]["zero_variance_scale"]),
    )

    design = frame.loc[:, list(columns)].to_numpy(dtype="float64")
    sealed_prediction = sealed.predict(standardiser.transform(frame, spec))
    assert np.allclose(design @ coefficients + intercept, sealed_prediction, rtol=1e-8, atol=1e-8)


# ---------------------------------------------------------------------------
# Leakage: the frozen calibration seals
# ---------------------------------------------------------------------------


def test_detector_spec_validates_against_the_frozen_configuration(spec: dict):
    validate_detector_spec(spec)
    assert tuple(spec["detector_contract"]["forms"]) == DETECTOR_FORMS


def test_calibration_is_blocked_while_the_design_is_unfrozen(spec: dict):
    unfrozen = deepcopy(spec)
    unfrozen["detector"]["status"] = "proposed"
    with pytest.raises(DetectorSpecError):
        validate_detector_spec(unfrozen)

    unratified = deepcopy(spec)
    unratified["detector"]["outstanding_unratified_items"] = ["exposure denominator"]
    with pytest.raises(DetectorSpecError):
        validate_detector_spec(unratified)


def test_per_unit_thresholds_cannot_be_re_enabled(spec: dict):
    drifted = deepcopy(spec)
    drifted["detector"]["threshold_scope"]["per_unit_thresholds_prohibited"] = False
    with pytest.raises(DetectorSpecError):
        validate_detector_spec(drifted)


def test_a_pooled_row_quantile_cannot_replace_the_macro_average(spec: dict):
    drifted = deepcopy(spec)
    drifted["detector"]["calibration_target"]["statistic"] = "pooled_row_quantile"
    with pytest.raises(DetectorSpecError):
        validate_detector_spec(drifted)


def test_episodes_cannot_be_allowed_to_bridge_a_masked_gap(spec: dict):
    drifted = deepcopy(spec)
    drifted["detector"]["episodes"]["masked_gap_state_machine"]["bridge_episodes_across_gap"] = True
    with pytest.raises(DetectorSpecError):
        validate_detector_spec(drifted)


def test_eligible_roles_must_agree_with_the_frozen_rolling_origin_roles(spec: dict):
    drifted = deepcopy(spec)
    drifted["detector"]["eligibility"]["residual_roles"] = [
        "development_oof",
        "hyperparameter_validation_oof",
    ]
    with pytest.raises(DetectorSpecError):
        validate_detector_spec(drifted)


def _residual_frame(units, dates, role="development_oof") -> pd.DataFrame:
    rows = []
    for unit in units:
        for date in dates:
            rows.append(
                {
                    "unit": unit,
                    "horizon_days": 7,
                    "target_timestamp": date,
                    "fold_id": "fold_001",
                    "residual_role": role,
                    "y_target": 10.0,
                    "prediction": 11.0,
                    "context_scale": 2.0,
                }
            )
    return pd.DataFrame.from_records(rows)


def test_a_hormuz_row_cannot_reach_detector_calibration(spec: dict):
    mask = load_event_mask(spec)
    dates = pd.date_range("2021-02-01", periods=5, freq="D")
    contaminated = _residual_frame([spec["population"]["hormuz_unit"]], dates)
    with pytest.raises(LeakageError):
        eligible_residuals(contaminated, spec, mask)


def test_the_2024_selection_year_is_dropped_from_calibration(spec: dict):
    mask = load_event_mask(spec)
    frame = pd.concat(
        [
            _residual_frame(["dover_strait"], pd.date_range("2021-02-01", periods=3, freq="D")),
            _residual_frame(
                ["dover_strait"],
                pd.date_range("2024-06-01", periods=3, freq="D"),
                role="hyperparameter_validation_oof",
            ),
        ],
        ignore_index=True,
    )
    admitted, _ = eligible_residuals(frame, spec, mask)
    assert set(admitted["residual_role"]) == {"development_oof"}
    assert pd.to_datetime(admitted["target_timestamp"]).dt.year.eq(2024).sum() == 0


def test_residuals_after_the_calibration_end_are_refused(spec: dict):
    mask = load_event_mask(spec)
    late = _residual_frame(
        ["dover_strait"],
        pd.date_range("2025-12-01", periods=3, freq="D"),
        role="post_selection_prequential",
    )
    with pytest.raises(LeakageError):
        eligible_residuals(late, spec, mask)


def test_event_masked_unit_days_are_removed_and_only_for_their_own_unit(spec: dict):
    mask = load_event_mask(spec)
    # The Ever Given closure masks Suez, and nothing else, on those days.
    dates = pd.date_range("2021-03-23", "2021-03-29", freq="D")
    frame = _residual_frame(["suez_canal", "dover_strait"], dates)
    admitted, excluded = eligible_residuals(frame, spec, mask)
    assert set(excluded["unit"]) == {"suez_canal"}
    assert set(admitted["unit"]) == {"dover_strait"}
    assert len(admitted) == len(dates)


def test_calibration_task_access_refuses_masked_or_ineligible_rows(spec: dict):
    """The A1 seal itself, exercised through the A3 entry point."""
    folds = rolling_origin_folds(spec)
    geometry = build_task_geometry(
        pd.date_range(folds[0].score_start, folds[0].score_start + pd.Timedelta(days=2), freq="D"),
        ["dover_strait"],
        [1],
        measurement_state="july",
        task_role="rolling_residual",
        seed=spec["tasks"]["seed"],
        fold_id=folds[0].fold_id,
        extra_columns={
            "fit_start": folds[0].fit_start,
            "fit_end": folds[0].score_start - pd.Timedelta(days=1),
            "score_start": folds[0].score_start,
            "score_end": folds[0].score_end,
            "residual_role": "development_oof",
            "calibration_eligible": True,
        },
    )
    with pytest.raises(LeakageError):
        # No event-mask column at all: calibration must not accept it.
        assert_task_access(geometry, "detector_calibration", spec)

    masked = geometry.assign(event_masked=True)
    with pytest.raises(LeakageError):
        assert_task_access(masked, "detector_calibration", spec)

    ineligible = geometry.assign(event_masked=False, calibration_eligible=False)
    with pytest.raises(LeakageError):
        assert_task_access(ineligible, "detector_calibration", spec)


def test_rolling_fit_targets_never_reach_past_their_horizon_specific_fit_end(spec: dict):
    folds = rolling_origin_folds(spec)
    for fold in (folds[0], folds[30], folds[-1]):
        for horizon in spec["tasks"]["horizons_days"]:
            geometry = build_rolling_fit_geometry(spec, fold, int(horizon), "july")
            fit_end = fold.score_start - pd.Timedelta(days=int(horizon))
            assert pd.to_datetime(geometry["target_timestamp"]).max() <= fit_end
            assert pd.to_datetime(geometry["feature_timestamp"]).max() < fit_end
            assert spec["population"]["hormuz_unit"] not in set(geometry["unit"])


def test_fold_context_scales_never_read_past_their_fold(spec: dict):
    """A 2021 fold must be normalised on 2021 information, not 2025."""
    index = pd.date_range("2019-01-01", "2025-11-30", freq="D")
    rng = np.random.default_rng(23)
    panel = pd.DataFrame(
        {unit: 20.0 + rng.normal(size=len(index)) for unit in development_units(spec)},
        index=index,
    )
    early = fold_context_scales(panel, spec, measurement_state="july", context_end=pd.Timestamp("2021-06-30"))
    late = fold_context_scales(panel, spec, measurement_state="july", context_end=pd.Timestamp("2025-06-30"))
    for unit in development_units(spec):
        assert early[unit].context_end <= pd.Timestamp("2021-06-30")
        assert late[unit].context_end <= pd.Timestamp("2025-06-30")
    # The frozen object is the algorithm, so the constants must actually differ.
    assert any(early[unit].scale != late[unit].scale for unit in development_units(spec))


def test_each_fold_scale_is_fitted_through_that_folds_own_fit_end(spec: dict):
    """The seal is that the algorithm refitted, not that the number moved."""
    index = pd.date_range("2019-01-01", "2025-11-30", freq="D")
    rng = np.random.default_rng(37)
    panel = pd.DataFrame(
        {unit: 20.0 + rng.normal(size=len(index)) for unit in development_units(spec)},
        index=index,
    )
    folds = rolling_origin_folds(spec)
    for fold in (folds[0], folds[-1]):
        for horizon in spec["tasks"]["horizons_days"]:
            fit_end = fold.score_start - pd.Timedelta(days=int(horizon))
            scales = fold_context_scales(
                panel, spec, measurement_state="july", context_end=fit_end
            )
            for unit in development_units(spec):
                assert scales[unit].context_end == fit_end


def test_an_integer_count_series_gives_a_quantised_context_scale(spec: dict):
    """Why some units' scales are constant across every fold.

    `n_tanker` is a count.  A low-volume unit's median absolute deviation is
    therefore an integer, its scale is that integer times 1.4826, and a longer
    history does not move it.  The refit is still real; its estimate is coarse.
    """
    index = pd.date_range("2019-01-01", "2025-11-30", freq="D")
    rng = np.random.default_rng(41)
    counts = pd.Series(rng.integers(0, 4, size=len(index)).astype("float64"), index=index)

    early = fit_context_scale(
        counts, spec, measurement_state="july",
        context_start="2019-01-01", context_end="2021-06-30",
    )
    late = fit_context_scale(
        counts, spec, measurement_state="july",
        context_start="2019-01-01", context_end="2025-06-30",
    )
    assert early.context_end != late.context_end
    assert early.scale == pytest.approx(late.scale)
    assert early.scale / 1.4826 == pytest.approx(round(early.scale / 1.4826))


def test_a_context_scale_cannot_be_fitted_into_the_surveillance_window(spec: dict):
    index = pd.date_range("2019-01-01", "2026-07-07", freq="D")
    rng = np.random.default_rng(29)
    panel = pd.DataFrame(
        {unit: 20.0 + rng.normal(size=len(index)) for unit in development_units(spec)},
        index=index,
    )
    with pytest.raises(LeakageError):
        fold_context_scales(
            panel, spec, measurement_state="july", context_end=pd.Timestamp("2026-01-15")
        )


def test_curves_are_built_per_unit_and_never_pooled(spec: dict):
    dates = pd.date_range("2021-02-01", periods=40, freq="D")
    frame = _residual_frame(["dover_strait", "suez_canal"], dates)
    rng = np.random.default_rng(31)
    frame["prediction"] = frame["y_target"] + rng.normal(size=len(frame))
    curves = curves_by_unit(frame, spec, RAW_LEVEL)
    assert set(curves) == {"dover_strait", "suez_canal"}
    for curve in curves.values():
        assert curve.eligible_days == len(dates)
        assert curve.exposure_years == pytest.approx(len(dates) / 365.25)


def test_both_frozen_forms_produce_scores_from_the_same_rows(spec: dict):
    dates = pd.date_range("2021-02-01", periods=10, freq="D")
    frame = _residual_frame(["dover_strait"], dates)
    for form in DETECTOR_FORMS:
        scores = score_frame(frame, form)
        assert len(scores) == len(frame)
        assert np.isfinite(scores).all()
    assert np.allclose(
        score_frame(frame, SCALE_INVARIANT),
        score_frame(frame, RAW_LEVEL) / frame["context_scale"].to_numpy(),
    )
