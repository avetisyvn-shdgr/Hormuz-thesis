"""Structural tests for the joint observability / counterfactual breakdown frontier.

These tests police the arithmetic and the sign structure, not the answer. They
assert that the identity is exact, that the two-sided direction is what the
write-up claims, that the binding scenario is the least favourable admissible one
rather than the point estimate, that unbounded interval endpoints are dropped
instead of clipped, and that the new layer reproduces the existing AIS-dark bound
at their shared corner. They deliberately do not assert that any particular
reduction is large or that any claim survives.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from lngfreight import observability_frontier as of


MODEL = "ar_lag1_7"
TARGET = "hormuz_tanker_transits"
OBSERVED = 529.0
COUNTERFACTUAL = 7397.996006081118
N_POST_DAYS = 130
DAILY_MEAN = 40.0


def _scenarios() -> list[of.CounterfactualScenario]:
    return [
        of.CounterfactualScenario(of.POINT_SCENARIO, COUNTERFACTUAL, "point", None),
        of.CounterfactualScenario(
            "bootstrap_block_lower", 6834.209, "block_bootstrap_residual", 0.95
        ),
        of.CounterfactualScenario(
            "bootstrap_block_upper", 7939.246, "block_bootstrap_residual", 0.95
        ),
        of.CounterfactualScenario(
            "conformal_0.80_lower", 5727.825, "split_conformal_block_rank", 0.80
        ),
    ]


def _frontier() -> pd.DataFrame:
    return of.build_frontier(
        observed=OBSERVED,
        scenarios=_scenarios(),
        model=MODEL,
        target=TARGET,
        n_post_days=N_POST_DAYS,
        pretreatment_daily_mean=DAILY_MEAN,
    )


def test_true_reduction_recovers_the_naive_estimate_at_zero_error():
    naive = 1.0 - OBSERVED / COUNTERFACTUAL
    assert of.true_reduction(OBSERVED, COUNTERFACTUAL, 0.0, 0.0) == pytest.approx(naive)


def test_breakdown_rate_inverts_the_true_reduction_identity():
    """d*(R̄) must be the exact d at which R_true(d) equals R̄."""
    for threshold in of.CLAIM_THRESHOLDS:
        rate = of.breakdown_dark_rate(OBSERVED, COUNTERFACTUAL, threshold)
        if not 0.0 <= rate < 1.0:
            continue
        assert of.true_reduction(OBSERVED, COUNTERFACTUAL, rate) == pytest.approx(
            threshold, abs=1e-12
        )


def test_breakdown_rate_inverts_the_identity_with_false_positives():
    for spurious in (0.0, 0.05, 0.2):
        rate = of.breakdown_dark_rate(OBSERVED, COUNTERFACTUAL, 0.90, spurious)
        assert of.true_reduction(
            OBSERVED, COUNTERFACTUAL, rate, spurious
        ) == pytest.approx(0.90, abs=1e-12)


def test_implied_true_total_at_breakdown_do_not_depend_on_false_positives():
    """T at d* is C(1 - R̄) by construction; the reporting column must match."""
    frontier = of.build_frontier(
        observed=OBSERVED,
        scenarios=_scenarios()[:1],
        model=MODEL,
        target=TARGET,
        n_post_days=N_POST_DAYS,
        pretreatment_daily_mean=DAILY_MEAN,
        false_positive_rate=0.15,
    )
    for _, row in frontier.iterrows():
        assert row["implied_true_total_at_breakdown"] == pytest.approx(
            COUNTERFACTUAL * (1.0 - row["claim_threshold"])
        )


def test_dark_rate_lowers_and_false_positives_raise_the_true_reduction():
    grid = of.build_two_sided_grid(
        observed=OBSERVED, scenarios=_scenarios(), model=MODEL, target=TARGET
    )
    of.assert_false_positive_direction(grid)  # must not raise


def test_direction_guard_catches_a_corrupted_sign():
    grid = of.build_two_sided_grid(
        observed=OBSERVED, scenarios=_scenarios()[:1], model=MODEL, target=TARGET
    )
    corrupted = grid.copy()
    mask = (corrupted["dark_rate"] == 0.0) & (corrupted["false_positive_rate"] == 0.20)
    corrupted.loc[mask, "true_reduction"] = -1.0
    with pytest.raises(AssertionError):
        of.assert_false_positive_direction(corrupted)


def test_binding_scenario_is_the_smallest_breakdown_rate_not_the_point_estimate():
    frontier = _frontier()
    binding = of.binding_breakdown(frontier)
    for _, row in binding.iterrows():
        cell = frontier[frontier["claim_threshold"] == row["claim_threshold"]]
        assert row["breakdown_dark_rate"] == pytest.approx(
            cell["breakdown_dark_rate"].min()
        )
        assert row["interval_robustness_discount"] >= -1e-12


def test_binding_requires_the_point_scenario_to_be_present():
    frontier = _frontier()
    without_point = frontier[frontier["counterfactual_scenario"] != of.POINT_SCENARIO]
    with pytest.raises(ValueError, match="point_estimate"):
        of.binding_breakdown(without_point)


def test_lower_counterfactual_never_makes_a_claim_look_more_robust():
    """Monotonicity in C: a smaller admissible counterfactual can only shrink d*."""
    low = of.breakdown_dark_rate(OBSERVED, 5727.825, 0.90)
    point = of.breakdown_dark_rate(OBSERVED, COUNTERFACTUAL, 0.90)
    high = of.breakdown_dark_rate(OBSERVED, 7939.246, 0.90)
    assert low < point < high


def test_strongest_surviving_claim_respects_the_conceded_rate():
    binding = of.binding_breakdown(_frontier())
    strongest = of.strongest_surviving_claim(binding, 0.05)
    for _, row in strongest.iterrows():
        assert row["breakdown_dark_rate"] > 0.05
    tighter = of.strongest_surviving_claim(binding, 0.95)
    assert tighter.empty or bool(
        (tighter["breakdown_dark_rate"] > 0.95).all()
    )


def test_strongest_surviving_claim_is_monotone_in_the_conceded_rate():
    binding = of.binding_breakdown(_frontier())
    previous = np.inf
    for tolerated in (0.01, 0.05, 0.10, 0.30, 0.60):
        strongest = of.strongest_surviving_claim(binding, tolerated)
        current = (
            float(strongest["claim_threshold"].max()) if not strongest.empty else -np.inf
        )
        assert current <= previous + 1e-12
        previous = current


def test_status_vocabulary_covers_the_three_regimes():
    assert of.breakdown_status(0.3) == of.STATUS_INTERIOR
    assert of.breakdown_status(-0.4) == of.STATUS_ALREADY_BROKEN
    assert of.breakdown_status(1.4) == of.STATUS_UNREACHABLE
    assert of.breakdown_status(float("nan")) == of.STATUS_UNREACHABLE


def test_non_finite_counterfactual_endpoint_is_refused_not_clipped():
    with pytest.raises(ValueError, match="unbounded"):
        of.CounterfactualScenario("bad", float("inf"), "family", 0.9)
    with pytest.raises(ValueError, match="unbounded"):
        of.CounterfactualScenario("bad", -np.inf, "family", 0.9)


def test_rates_outside_the_unit_interval_are_refused():
    for bad in (-0.01, 1.0, 1.5, float("nan")):
        with pytest.raises(ValueError):
            of.true_reduction(OBSERVED, COUNTERFACTUAL, bad)
        with pytest.raises(ValueError):
            of.true_reduction(OBSERVED, COUNTERFACTUAL, 0.1, bad)


def test_claim_threshold_of_one_is_refused():
    with pytest.raises(ValueError, match="claim_threshold"):
        of.breakdown_dark_rate(OBSERVED, COUNTERFACTUAL, 1.0)


def test_legacy_cross_check_passes_on_agreement_and_fails_on_divergence():
    frontier = _frontier()
    legacy = pd.DataFrame([
        {
            "model": MODEL,
            "target": TARGET,
            "reference_reduction": threshold,
            "critical_dark_rate": min(max(of.breakdown_dark_rate(
                OBSERVED, COUNTERFACTUAL, threshold
            ), 0.0), 1.0),
        }
        for threshold in of.CLAIM_THRESHOLDS
    ])
    of.assert_point_scenario_matches_legacy_bound(frontier, legacy)

    diverged = legacy.copy()
    diverged.loc[0, "critical_dark_rate"] += 0.01
    with pytest.raises(AssertionError, match="disagrees"):
        of.assert_point_scenario_matches_legacy_bound(frontier, diverged)


def test_legacy_cross_check_refuses_an_empty_join():
    frontier = _frontier()
    unrelated = pd.DataFrame([{
        "model": "other_model",
        "target": "hormuz_tanker_transits",
        "reference_reduction": 0.90,
        "critical_dark_rate": 0.28,
    }])
    with pytest.raises(AssertionError, match="did not actually run"):
        of.assert_point_scenario_matches_legacy_bound(frontier, unrelated)


def test_frontier_column_contract_is_stable():
    assert list(_frontier().columns) == of.FRONTIER_COLUMNS
    grid = of.build_two_sided_grid(
        observed=OBSERVED, scenarios=_scenarios(), model=MODEL, target=TARGET
    )
    assert list(grid.columns) == of.GRID_COLUMNS


def test_frontier_covers_every_scenario_threshold_pair():
    frontier = _frontier()
    assert len(frontier) == len(_scenarios()) * len(of.CLAIM_THRESHOLDS)
    assert frontier["breakdown_dark_rate"].notna().all()


def test_implied_unobserved_per_day_is_consistent_with_the_totals():
    frontier = _frontier()
    per_day = (
        frontier["implied_unobserved_total_at_breakdown"] / frontier["n_post_days"]
    )
    assert np.allclose(per_day, frontier["implied_unobserved_per_post_day"])
    share = frontier["implied_unobserved_per_post_day"] / DAILY_MEAN
    assert np.allclose(
        share, frontier["implied_unobserved_share_of_pretreatment_daily_mean"]
    )


def test_unit_label_is_looked_up_strictly():
    """An unregistered outcome must fail loudly rather than ship an unlabelled column."""
    assert of.target_unit("hormuz_tanker_transits") == "transits"
    assert of.target_unit("hormuz_tanker_capacity") == "deadweight_tonnes"
    with pytest.raises(KeyError, match="no unit registered"):
        of.target_unit("panama_tanker_transits")


def test_unit_column_matches_the_target_on_both_frames():
    frontier = _frontier()
    assert (frontier["unit"] == of.target_unit(TARGET)).all()
    grid = of.build_two_sided_grid(
        observed=OBSERVED, scenarios=_scenarios(), model=MODEL, target=TARGET
    )
    assert (grid["unit"] == of.target_unit(TARGET)).all()


def test_cross_check_cell_count_distinguishes_skip_from_agreement():
    """The robustness outcome has no legacy rows; that must read as 0, not as a pass."""
    frontier = _frontier()
    matching = pd.DataFrame([{
        "model": MODEL,
        "target": TARGET,
        "reference_reduction": 0.90,
        "critical_dark_rate": 0.28,
    }])
    assert of.legacy_cross_check_cells(frontier, matching) == 1
    other_target = matching.assign(target="hormuz_tanker_capacity")
    assert of.legacy_cross_check_cells(frontier, other_target) == 0


def test_script_runs_both_registered_outcomes_and_refuses_others():
    """The default run must cover the robustness twin, and must not accept a
    target outside the working specification."""
    import run_observability_breakdown_frontier as script
    from lngfreight.specification import working_specification

    spec = working_specification()
    frontier = pd.read_csv(
        script.config.path("data_processed") / script.FRONTIER_OUT
    )
    assert set(frontier["target"]) == {
        spec.primary_outcome, spec.robustness_outcome
    }
    with pytest.raises(KeyError, match="does not run on unregistered outcomes"):
        script.main(target_override="panama_tanker_transits")


def test_degenerate_inputs_are_refused():
    with pytest.raises(ValueError, match="counterfactual"):
        of.true_reduction(OBSERVED, 0.0, 0.1)
    with pytest.raises(ValueError, match="at least one"):
        of.build_frontier(
            observed=OBSERVED,
            scenarios=[],
            model=MODEL,
            target=TARGET,
            n_post_days=N_POST_DAYS,
            pretreatment_daily_mean=DAILY_MEAN,
        )
    with pytest.raises(ValueError, match="pretreatment_daily_mean"):
        of.build_frontier(
            observed=OBSERVED,
            scenarios=_scenarios(),
            model=MODEL,
            target=TARGET,
            n_post_days=N_POST_DAYS,
            pretreatment_daily_mean=0.0,
        )
