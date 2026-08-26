"""Joint breakdown frontier for observability error and counterfactual uncertainty.

The existing AIS-dark bound (`scripts/run_ais_dark_bound.py`) varies one nuisance
parameter — the incremental treatment-period dark rate ``d`` — while holding the
counterfactual at its point estimate and assuming one-sided undercounting. That
answers "how dark would the strait have to be?" but not the question a sceptical
examiner actually asks, which is joint: *how dark would it have to be, given that
the counterfactual itself is only interval-identified?*

This module maps the two nuisance dimensions together and reports where a stated
claim breaks down, rather than reporting a single point robustness margin.

Nuisance parameters
-------------------
``d`` — incremental post-period dark rate. The fraction of TRUE post-period
transits that PortWatch does not record, *over and above* the baseline
non-detection already embedded in the counterfactual's measurement scale. The
counterfactual is fitted on observed pre-treatment PortWatch counts, so it
forecasts what PortWatch would have recorded, not physical truth; only the
treatment-correlated *increment* is unaccounted for. ``d`` raises implied true
transits and therefore lowers the true reduction.

``s`` — post-period false-positive rate. The fraction of OBSERVED post-period
transits that do not correspond to a distinct true transit: spoofed tracks,
loitering vessels re-crossing the corridor polygon, duplicate identities. ``s``
lowers implied true transits and therefore *raises* the true reduction.

``C`` — the counterfactual, taken across its admissible interval rather than at
its point estimate. Both the block-bootstrap and the split-conformal intervals
are honoured as separate scenarios, since they carry different coverage
semantics and the conformal one is materially wider.

Identity
--------
    T(d, s)      = O (1 - s) / (1 - d)                  implied true transits
    R_true       = 1 - T(d, s) / C
    d*(R̄, s, C)  = 1 - O (1 - s) / (C (1 - R̄))          breakdown dark rate
    T at d*      = C (1 - R̄)                            independent of s

Because ``s`` is claim-reinforcing, the one-sided assumption in the existing
bound is the conservative one, and the only claim-breaking directions are large
``d`` and a counterfactual at the low end of its interval. That asymmetry is
asserted by :func:`assert_false_positive_direction` rather than assumed.

What this is not
----------------
This is a partial-identification sensitivity map over stated assumptions. It is
not a causal correction, not an estimate of the realised dark rate, and not a
measurement of dark activity. No satellite, commercial-AIS, or vendor dark-fleet
product is consulted, and none is required: the frontier reports what would have
to be true, and translates it into a physically checkable vessel count so the
reader can judge plausibility without a proprietary anchor.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


# Claim strengths a reader might defend. The frontier reports the breakdown
# dark rate for each, so the thesis can report the strongest claim that survives
# the least favourable admissible counterfactual instead of the point estimate.
CLAIM_THRESHOLDS = (0.50, 0.75, 0.90, 0.95)

# Sensitivity spans. Neither grid is an estimate of the realised rate.
DARK_RATE_GRID = (0.0, 0.05, 0.10, 0.20, 0.30, 0.40, 0.50, 0.70, 0.90)
FALSE_POSITIVE_GRID = (0.0, 0.05, 0.10, 0.20)

POINT_SCENARIO = "point_estimate"

# Unit labels are looked up strictly. The frontier runs on both the transit-count
# primary and the deadweight-capacity robustness twin, and a column called
# "transits" carrying tonnes would be a reporting defect, so an unknown target
# raises rather than defaulting.
TARGET_UNITS = {
    "hormuz_tanker_transits": "transits",
    "hormuz_tanker_capacity": "deadweight_tonnes",
}

FRONTIER_COLUMNS = [
    "model",
    "target",
    "unit",
    "counterfactual_scenario",
    "interval_family",
    "nominal_coverage",
    "observed_sum",
    "counterfactual_sum",
    "reduction_at_zero_error",
    "claim_threshold",
    "breakdown_dark_rate",
    "breakdown_status",
    "implied_true_total_at_breakdown",
    "implied_unobserved_total_at_breakdown",
    "implied_unobserved_per_post_day",
    "implied_unobserved_share_of_pretreatment_daily_mean",
    "n_post_days",
]

GRID_COLUMNS = [
    "model",
    "target",
    "unit",
    "counterfactual_scenario",
    "counterfactual_sum",
    "observed_sum",
    "dark_rate",
    "false_positive_rate",
    "implied_true_total",
    "true_reduction",
    "reduction_attributable_to_observability",
]


def target_unit(target: str) -> str:
    try:
        return TARGET_UNITS[target]
    except KeyError:
        raise KeyError(
            f"no unit registered for target {target!r}; add it to TARGET_UNITS "
            "rather than letting an unlabelled column reach the write-up."
        ) from None

# Breakdown-status vocabulary. These are descriptive labels for where d* falls
# relative to the feasible [0, 1) range, not verdicts about the claim.
STATUS_INTERIOR = "breaks_within_feasible_dark_rate"
STATUS_ALREADY_BROKEN = "claim_fails_at_zero_incremental_error"
STATUS_UNREACHABLE = "survives_total_blackout"


@dataclass(frozen=True)
class CounterfactualScenario:
    """One admissible value of the counterfactual, with its provenance label."""

    name: str
    counterfactual_sum: float
    interval_family: str
    nominal_coverage: float | None

    def __post_init__(self) -> None:
        if not np.isfinite(self.counterfactual_sum) or self.counterfactual_sum <= 0.0:
            raise ValueError(
                f"scenario {self.name!r} has a non-positive or non-finite "
                f"counterfactual ({self.counterfactual_sum!r}); an unbounded "
                "interval endpoint must be dropped upstream, not clipped here."
            )


def implied_true_total(
    observed: float, dark_rate: float, false_positive_rate: float = 0.0
) -> float:
    """T(d, s) = O (1 - s) / (1 - d)."""
    _check_rate(dark_rate, "dark_rate")
    _check_rate(false_positive_rate, "false_positive_rate")
    if dark_rate >= 1.0:
        return float("nan")
    return observed * (1.0 - false_positive_rate) / (1.0 - dark_rate)


def true_reduction(
    observed: float,
    counterfactual: float,
    dark_rate: float,
    false_positive_rate: float = 0.0,
) -> float:
    """R_true = 1 - T(d, s) / C."""
    if counterfactual <= 0.0:
        raise ValueError("counterfactual must be strictly positive.")
    implied = implied_true_total(observed, dark_rate, false_positive_rate)
    if not np.isfinite(implied):
        return float("nan")
    return 1.0 - implied / counterfactual


def breakdown_dark_rate(
    observed: float,
    counterfactual: float,
    claim_threshold: float,
    false_positive_rate: float = 0.0,
) -> float:
    """d*(R̄, s, C) = 1 - O (1 - s) / (C (1 - R̄)).

    Returned unclipped and possibly outside [0, 1). A negative value means the
    claim already fails with no incremental observability error; a value above 1
    means it survives even a total post-period blackout. Both are informative,
    so clipping happens only in the reporting layer.
    """
    if not 0.0 <= claim_threshold < 1.0:
        raise ValueError("claim_threshold must lie in [0, 1).")
    if counterfactual <= 0.0:
        raise ValueError("counterfactual must be strictly positive.")
    _check_rate(false_positive_rate, "false_positive_rate")
    survivable_observed = observed * (1.0 - false_positive_rate)
    return 1.0 - survivable_observed / (counterfactual * (1.0 - claim_threshold))


def breakdown_status(rate: float) -> str:
    if not np.isfinite(rate):
        return STATUS_UNREACHABLE
    if rate <= 0.0:
        return STATUS_ALREADY_BROKEN
    if rate >= 1.0:
        return STATUS_UNREACHABLE
    return STATUS_INTERIOR


def build_frontier(
    *,
    observed: float,
    scenarios: list[CounterfactualScenario],
    model: str,
    target: str,
    n_post_days: int,
    pretreatment_daily_mean: float,
    claim_thresholds: tuple[float, ...] = CLAIM_THRESHOLDS,
    false_positive_rate: float = 0.0,
) -> pd.DataFrame:
    """One row per (counterfactual scenario, claim threshold).

    ``pretreatment_daily_mean`` converts the abstract breakdown rate into the
    quantity a reader can weigh: the implied invisible traffic expressed as a
    share of normal pre-treatment daily throughput.
    """
    if not scenarios:
        raise ValueError("at least one counterfactual scenario is required.")
    if n_post_days <= 0:
        raise ValueError("n_post_days must be positive.")
    if pretreatment_daily_mean <= 0.0:
        raise ValueError("pretreatment_daily_mean must be positive.")

    unit = target_unit(target)
    rows = []
    for scenario in scenarios:
        counterfactual = scenario.counterfactual_sum
        for threshold in claim_thresholds:
            rate = breakdown_dark_rate(
                observed, counterfactual, threshold, false_positive_rate
            )
            implied_true = counterfactual * (1.0 - threshold)
            unobserved = implied_true - observed * (1.0 - false_positive_rate)
            per_day = unobserved / n_post_days
            rows.append({
                "model": model,
                "target": target,
                "unit": unit,
                "counterfactual_scenario": scenario.name,
                "interval_family": scenario.interval_family,
                "nominal_coverage": scenario.nominal_coverage,
                "observed_sum": observed,
                "counterfactual_sum": counterfactual,
                "reduction_at_zero_error": 1.0 - observed / counterfactual,
                "claim_threshold": threshold,
                "breakdown_dark_rate": rate,
                "breakdown_status": breakdown_status(rate),
                "implied_true_total_at_breakdown": implied_true,
                "implied_unobserved_total_at_breakdown": unobserved,
                "implied_unobserved_per_post_day": per_day,
                "implied_unobserved_share_of_pretreatment_daily_mean":
                    per_day / pretreatment_daily_mean,
                "n_post_days": n_post_days,
            })
    return pd.DataFrame(rows, columns=FRONTIER_COLUMNS)


def build_two_sided_grid(
    *,
    observed: float,
    scenarios: list[CounterfactualScenario],
    model: str,
    target: str,
    dark_rate_grid: tuple[float, ...] = DARK_RATE_GRID,
    false_positive_grid: tuple[float, ...] = FALSE_POSITIVE_GRID,
) -> pd.DataFrame:
    """Full (d, s, C) cross-product of implied true reductions."""
    unit = target_unit(target)
    rows = []
    for scenario in scenarios:
        counterfactual = scenario.counterfactual_sum
        naive = 1.0 - observed / counterfactual
        for dark in dark_rate_grid:
            for spurious in false_positive_grid:
                reduction = true_reduction(
                    observed, counterfactual, dark, spurious
                )
                rows.append({
                    "model": model,
                    "target": target,
                    "unit": unit,
                    "counterfactual_scenario": scenario.name,
                    "counterfactual_sum": counterfactual,
                    "observed_sum": observed,
                    "dark_rate": dark,
                    "false_positive_rate": spurious,
                    "implied_true_total":
                        implied_true_total(observed, dark, spurious),
                    "true_reduction": reduction,
                    "reduction_attributable_to_observability": naive - reduction,
                })
    return pd.DataFrame(rows, columns=GRID_COLUMNS)


def binding_breakdown(frontier: pd.DataFrame) -> pd.DataFrame:
    """The least favourable admissible scenario per claim threshold.

    A claim is only as robust as its weakest admissible counterfactual, so the
    binding row is the one with the *smallest* breakdown dark rate. Reporting the
    point-estimate row alone overstates the robustness margin.
    """
    _require_columns(frontier, FRONTIER_COLUMNS)
    if frontier.empty:
        raise ValueError("frontier is empty; nothing to reduce.")
    ordered = frontier.sort_values(
        ["model", "target", "claim_threshold", "breakdown_dark_rate",
         "counterfactual_scenario"],
        kind="mergesort",
    )
    binding = ordered.groupby(
        ["model", "target", "claim_threshold"], as_index=False
    ).first()
    point = frontier[frontier["counterfactual_scenario"] == POINT_SCENARIO]
    if point.empty:
        raise ValueError(
            f"no {POINT_SCENARIO!r} row present; the point estimate must always "
            "be carried so the interval discount can be reported."
        )
    point = point[["model", "target", "claim_threshold", "breakdown_dark_rate"]]
    point = point.rename(
        columns={"breakdown_dark_rate": "point_estimate_breakdown_dark_rate"}
    )
    merged = binding.merge(point, on=["model", "target", "claim_threshold"])
    merged["interval_robustness_discount"] = (
        merged["point_estimate_breakdown_dark_rate"] - merged["breakdown_dark_rate"]
    )
    return merged


def strongest_surviving_claim(
    binding: pd.DataFrame, tolerated_dark_rate: float
) -> pd.DataFrame:
    """Largest claim threshold whose binding breakdown rate exceeds a tolerance.

    ``tolerated_dark_rate`` is the incremental dark rate the author is willing to
    concede as possible. It is an assumption stated by the author, not an
    estimate produced here, and the caller must record where it came from.
    """
    _check_rate(tolerated_dark_rate, "tolerated_dark_rate")
    surviving = binding[binding["breakdown_dark_rate"] > tolerated_dark_rate]
    if surviving.empty:
        return surviving.head(0)
    idx = surviving.groupby(["model", "target"])["claim_threshold"].idxmax()
    return surviving.loc[idx]


def assert_false_positive_direction(grid: pd.DataFrame) -> None:
    """False positives must raise the true reduction; dark rate must lower it.

    This polices the sign structure the write-up depends on: it is what licenses
    the statement that the existing one-sided bound is the conservative case.
    """
    _require_columns(grid, GRID_COLUMNS)
    for keys, block in grid.groupby(["counterfactual_scenario", "dark_rate"]):
        ordered = block.sort_values("false_positive_rate")["true_reduction"]
        ordered = ordered.dropna()
        if len(ordered) > 1 and not np.all(np.diff(ordered.to_numpy()) >= -1e-12):
            raise AssertionError(
                f"true reduction is not non-decreasing in the false-positive "
                f"rate at {keys!r}; the two-sided sign structure is violated."
            )
    for keys, block in grid.groupby(["counterfactual_scenario", "false_positive_rate"]):
        ordered = block.sort_values("dark_rate")["true_reduction"]
        ordered = ordered.dropna()
        if len(ordered) > 1 and not np.all(np.diff(ordered.to_numpy()) <= 1e-12):
            raise AssertionError(
                f"true reduction is not non-increasing in the dark rate at "
                f"{keys!r}; the two-sided sign structure is violated."
            )


def legacy_cross_check_cells(frontier: pd.DataFrame, legacy: pd.DataFrame) -> int:
    """Number of (model, target, threshold) cells the legacy bound shares.

    The legacy AIS-dark bound is written for the primary outcome only, so the
    robustness-outcome run has nothing to cross-check against. The caller must
    branch on this count and record the skip; the assertion itself stays strict
    so a silently empty join can never be mistaken for agreement.
    """
    point = frontier[frontier["counterfactual_scenario"] == POINT_SCENARIO]
    return len(point.merge(
        legacy[["model", "target", "reference_reduction"]],
        left_on=["model", "target", "claim_threshold"],
        right_on=["model", "target", "reference_reduction"],
        how="inner",
    ))


def assert_point_scenario_matches_legacy_bound(
    frontier: pd.DataFrame, legacy: pd.DataFrame, *, tolerance: float = 1e-9
) -> None:
    """The point-estimate rows must reproduce the existing AIS-dark bound.

    The new layer generalises `run_ais_dark_bound.py`; it must not silently
    disagree with it. Any divergence at the shared corner (s = 0, C = point) is a
    defect in one of the two, and the reader is entitled to know they agree.
    """
    point = frontier[frontier["counterfactual_scenario"] == POINT_SCENARIO]
    merged = point.merge(
        legacy[["model", "target", "reference_reduction", "critical_dark_rate"]],
        left_on=["model", "target", "claim_threshold"],
        right_on=["model", "target", "reference_reduction"],
        how="inner",
    )
    if merged.empty:
        raise AssertionError(
            "no shared (model, target, threshold) cell between the frontier and "
            "the legacy AIS-dark bound; the cross-check did not actually run."
        )
    # The legacy artifact clips to [0, 1]; compare on the same clipped scale.
    clipped = merged["breakdown_dark_rate"].clip(0.0, 1.0)
    delta = (clipped - merged["critical_dark_rate"]).abs()
    if bool((delta > tolerance).any()):
        worst = merged.loc[delta.idxmax()]
        raise AssertionError(
            "frontier point-estimate breakdown rate disagrees with the legacy "
            f"AIS-dark bound at threshold {worst['claim_threshold']}: "
            f"{worst['breakdown_dark_rate']!r} vs {worst['critical_dark_rate']!r}."
        )


def _check_rate(value: float, name: str) -> None:
    if not np.isfinite(value) or not 0.0 <= value < 1.0:
        raise ValueError(f"{name} must be a finite value in [0, 1); got {value!r}.")


def _require_columns(frame: pd.DataFrame, columns: list[str]) -> None:
    missing = [column for column in columns if column not in frame.columns]
    if missing:
        raise ValueError(f"frame is missing required columns: {missing}.")
