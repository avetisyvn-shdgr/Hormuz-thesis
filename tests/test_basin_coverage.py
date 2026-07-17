"""Tests for the basin-interval coverage simulation backing the point-only decision."""

import pandas as pd
import pytest


from lngfreight.basin_coverage import (
    BASIN_INTERVAL_METHODS,
    BasinCoverageScenario,
    default_scenarios,
    run_coverage_grid,
    simulate_scenario,
)


def _scenario(**overrides) -> BasinCoverageScenario:
    base = dict(
        name="t",
        n_corridors=5,
        corridor_correlation=0.5,
        true_corridor_effect=0.10,
        estimator_noise_sd=0.05,
        n_placebo_draws=2000,
        double_count_overlap=0.0,
    )
    base.update(overrides)
    return BasinCoverageScenario(**base)


def test_simulation_is_deterministic_for_a_fixed_seed():
    first = simulate_scenario(_scenario(), n_replications=1500, seed=7)
    second = simulate_scenario(_scenario(), n_replications=1500, seed=7)
    pd.testing.assert_frame_equal(first, second)


def test_scenario_rejects_invalid_configuration():
    with pytest.raises(ValueError, match="at least two corridors"):
        _scenario(n_corridors=1)
    with pytest.raises(ValueError, match="positive definite"):
        _scenario(corridor_correlation=-0.30, n_corridors=5)
    with pytest.raises(ValueError, match="double_count_overlap"):
        _scenario(double_count_overlap=1.0)
    with pytest.raises(ValueError, match="two placebo draws"):
        _scenario(n_placebo_draws=1)


def test_placebo_reference_distribution_is_not_an_interval():
    # The null-centred reference never covers a clearly non-zero basin effect.
    df = simulate_scenario(_scenario(), n_replications=2000, seed=1)
    row = df.loc[df["method"].eq("placebo_reference_as_interval")].iloc[0]
    assert row["empirical_coverage"] < 0.05


def test_joint_method_is_calibrated_only_under_ideal_conditions():
    ideal = simulate_scenario(
        _scenario(corridor_correlation=0.0, n_placebo_draws=2000),
        n_replications=4000,
        seed=20260621,
    )
    joint_ideal = ideal.loc[ideal["method"].eq("joint_centered_resample")].iloc[0]
    assert joint_ideal["empirical_coverage"] == pytest.approx(0.80, abs=0.03)

    # Independent-normal summation ignores positive dependence and undercovers.
    correlated = simulate_scenario(
        _scenario(corridor_correlation=0.5, n_placebo_draws=2000),
        n_replications=4000,
        seed=20260621,
    )
    indep = correlated.loc[correlated["method"].eq("independent_normal_sum")].iloc[0]
    assert indep["empirical_coverage"] < 0.65


def test_realistic_design_has_no_method_reaching_nominal_coverage():
    grid = run_coverage_grid(default_scenarios(), n_replications=4000, seed=20260621)
    realistic = grid.loc[grid["scenario"].eq("realistic_design_nine_draws")]
    assert len(realistic) == len(BASIN_INTERVAL_METHODS)
    assert not realistic["meets_nominal_coverage"].any()
    # The closest method still falls short of the 0.80 nominal target.
    assert realistic["empirical_coverage"].max() < 0.77


def test_coverage_is_measured_against_the_topology_aware_estimand():
    no_overlap = _scenario(double_count_overlap=0.0)
    with_overlap = _scenario(double_count_overlap=0.25)
    assert with_overlap.meaningful_basin_effect < with_overlap.naive_basin_effect
    assert no_overlap.meaningful_basin_effect == pytest.approx(no_overlap.naive_basin_effect)
