"""Contract tests for shared-placebo corridor inference."""
from dataclasses import replace

import numpy as np
import pandas as pd
import pytest


from hormuz_throughput.corridor_inference import (
    CorridorInferenceProtocol,
    build_shared_placebo_matrix,
    corridor_romano_wolf,
    load_corridor_inference_protocol,
    mean_scaled_signed_deviation,
)
from hormuz_throughput.inference import romano_wolf_stepdown
from hormuz_throughput.spatial import wide_chokepoint_panel
from hormuz_throughput.inference import placebo_time_folds, select_non_overlapping_folds


def _protocol() -> CorridorInferenceProtocol:
    return CorridorInferenceProtocol(
        status="test",
        history_start=pd.Timestamp("2021-01-01"),
        cutoff=pd.Timestamp("2022-02-01"),
        family_name="test_family",
        model="ar_lag1_7",
        statistic="mean_scaled_signed_deviation",
        sign="observed_minus_counterfactual",
        alternative="two-sided",
        studentize=True,
        post_horizon_days=10,
        minimum_scored_days_per_window=8,
        primary_placebo_design="non_overlapping_shared_origins",
        expected_joint_draws=3,
        shared_placebo_origins=(
            pd.Timestamp("2022-01-01"),
            pd.Timestamp("2022-01-11"),
            pd.Timestamp("2022-01-21"),
        ),
        overlapping_placebo_policy="sensitivity_only",
        basin_interval_policy="point_only",
        basin_reference_distribution_label="placebo_reference_not_interval",
        eligible_corridors={"count": ("a", "b"), "capacity": ("a",)},
    )


def _statistics(protocol, *, placebo):
    rows = []
    origins = protocol.shared_placebo_origins if placebo else (None,)
    for target, corridors in protocol.eligible_corridors.items():
        for corridor in corridors:
            for i, origin in enumerate(origins):
                row = {
                    "model": protocol.model,
                    "target": target,
                    "corridor": corridor,
                    "statistic_value": float(i + 1 + len(corridor)),
                    "n_scored": protocol.post_horizon_days,
                    "train_start": protocol.history_start,
                }
                if placebo:
                    row["train_end"] = origin - pd.Timedelta(days=1)
                    row["placebo_start"] = origin
                    row["placebo_end"] = origin + pd.Timedelta(
                        days=protocol.post_horizon_days - 1
                    )
                else:
                    row["train_end"] = protocol.cutoff - pd.Timedelta(days=1)
                    row["window_start"] = protocol.cutoff
                    row["window_end"] = protocol.cutoff + pd.Timedelta(
                        days=protocol.post_horizon_days - 1
                    )
                rows.append(row)
    return pd.DataFrame(rows)


def test_repository_protocol_uses_nine_disjoint_shared_windows():
    protocol = load_corridor_inference_protocol()
    assert len(protocol.hypotheses) == 48
    assert protocol.expected_joint_draws == 9
    assert protocol.minimum_scored_days_per_window == 76
    assert protocol.finite_sample_p_value_floor == pytest.approx(0.10)
    assert protocol.basin_interval_policy == "point_only"

    index = wide_chokepoint_panel("n_tanker").index
    folds = placebo_time_folds(
        index,
        cutoff="2026-02-28",
        horizon_days=94,
        initial_train_days=365,
        step_days=30,
    )
    selected = select_non_overlapping_folds(folds)
    assert tuple(fold.test_start for fold in selected) == protocol.shared_placebo_origins
    for target, corridors in protocol.eligible_corridors.items():
        panel = wide_chokepoint_panel(target)
        for corridor in corridors:
            for origin in protocol.shared_placebo_origins:
                assert (
                    panel.loc[
                        origin:origin + pd.Timedelta(days=protocol.post_horizon_days - 1),
                        corridor,
                    ].notna().sum()
                    >= protocol.minimum_scored_days_per_window
                )


def test_mean_scaled_signed_deviation_has_declared_sign():
    value = mean_scaled_signed_deviation(
        [8.0, 12.0], [10.0, 10.0], pre_period_mean=10.0
    )
    assert value == pytest.approx(0.0)
    below = mean_scaled_signed_deviation(
        [5.0, 5.0], [10.0, 10.0], pre_period_mean=10.0
    )
    assert below == pytest.approx(-0.5)


def test_joint_matrix_is_complete_aligned_and_deterministic():
    protocol = _protocol()
    stats = _statistics(protocol, placebo=True)
    first = build_shared_placebo_matrix(stats.sample(frac=1, random_state=1), protocol)
    second = build_shared_placebo_matrix(stats.sample(frac=1, random_state=2), protocol)
    pd.testing.assert_frame_equal(first, second)
    assert first.shape == (3, 3)


def test_joint_matrix_rejects_missing_duplicate_and_wrong_horizon_rows():
    protocol = _protocol()
    stats = _statistics(protocol, placebo=True)
    with pytest.raises(ValueError, match="complete frozen joint"):
        build_shared_placebo_matrix(stats.iloc[:-1], protocol)

    duplicate = pd.concat([stats, stats.iloc[[0]]], ignore_index=True)
    with pytest.raises(ValueError, match="duplicate"):
        build_shared_placebo_matrix(duplicate, protocol)

    wrong_horizon = stats.copy()
    wrong_horizon.loc[0, "placebo_end"] -= pd.Timedelta(days=1)
    with pytest.raises(ValueError, match="frozen horizon"):
        build_shared_placebo_matrix(wrong_horizon, protocol)

    too_sparse = stats.copy()
    too_sparse.loc[0, "n_scored"] = 7
    with pytest.raises(ValueError, match="completeness"):
        build_shared_placebo_matrix(too_sparse, protocol)


def test_family_rejects_foundation_model_or_changed_membership():
    protocol = _protocol()
    stats = _statistics(protocol, placebo=True)
    stats.loc[0, "model"] = "chronos2"
    with pytest.raises(ValueError, match="AR-only"):
        build_shared_placebo_matrix(stats, protocol)

    stats = _statistics(protocol, placebo=True)
    stats.loc[0, "corridor"] = "not_frozen"
    with pytest.raises(ValueError, match="multiplicity family"):
        build_shared_placebo_matrix(stats, protocol)


def test_corridor_romano_wolf_reports_design_floor_and_no_basin_interval():
    protocol = _protocol()
    observed = _statistics(protocol, placebo=False)
    placebo = _statistics(protocol, placebo=True)
    result = corridor_romano_wolf(observed, placebo, protocol)
    assert result["family_size"].eq(3).all()
    assert result["n_joint_resamples"].eq(3).all()
    assert result["finite_sample_p_value_floor"].eq(0.25).all()
    assert result["romano_wolf_p_value"].ge(0.25).all()
    assert result["basin_interval_policy"].eq("point_only").all()


def test_corridor_romano_wolf_rejects_zero_variance_hypothesis():
    protocol = _protocol()
    observed = _statistics(protocol, placebo=False)
    placebo = _statistics(protocol, placebo=True)
    mask = placebo["target"].eq("count") & placebo["corridor"].eq("a")
    placebo.loc[mask, "statistic_value"] = 1.0
    with pytest.raises(ValueError, match="zero-variance"):
        corridor_romano_wolf(observed, placebo, protocol)


def test_two_sided_studentization_centers_before_taking_absolute_value():
    observed = pd.Series({"h": -3.0})
    draws = pd.DataFrame({"h": [-2.0, -1.0, 0.0, 1.0, 2.0]})
    result = romano_wolf_stepdown(
        observed, draws, alternative="two-sided", studentize=True
    )
    expected = abs(-3.0 / np.std([-2, -1, 0, 1, 2], ddof=1))
    assert result.loc[0, "studentized_statistic"] == pytest.approx(expected)


def test_protocol_rejects_overlapping_primary_windows():
    protocol = _protocol()
    broken = replace(
        protocol,
        shared_placebo_origins=(
            pd.Timestamp("2022-01-01"),
            pd.Timestamp("2022-01-10"),
            pd.Timestamp("2022-01-21"),
        ),
    )
    stats = _statistics(protocol, placebo=True)
    with pytest.raises(ValueError, match="must not overlap"):
        build_shared_placebo_matrix(stats, broken)
