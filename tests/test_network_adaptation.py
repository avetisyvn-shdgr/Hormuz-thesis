"""Contract tests for the restricted network-adaptation experiment."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from experiments.network_adaptation.inference import (
    global_mean_test,
    scale_columns,
    synchronized_circular_mbb,
)
from experiments.network_adaptation.protocol import load_protocol


def test_protocol_retains_restricted_exploratory_geometry():
    protocol = load_protocol()
    assert protocol.status == "exploratory_retrospective_restriction"
    assert protocol.horizon == 130
    assert protocol.event_end == pd.Timestamp("2026-07-07")
    assert protocol.primary_model == "chronos2_univariate"
    assert protocol.robustness_model == "ar_lag1_7"
    assert len(protocol.primary_keys) == 5
    assert len(protocol.control_keys) == 10
    assert not set(protocol.primary_corridors) & set(protocol.context_corridors)


def test_synchronized_mbb_is_deterministic_and_preserves_joint_columns():
    base = np.arange(60, dtype="float64")
    residuals = pd.DataFrame({"a": base, "b": 2.0 * base})
    first = synchronized_circular_mbb(
        residuals, horizon=20, block_length=7, n_draws=100, seed=42
    )
    second = synchronized_circular_mbb(
        residuals, horizon=20, block_length=7, n_draws=100, seed=42
    )
    pd.testing.assert_frame_equal(first, second)
    assert np.allclose(first["b"], 2.0 * first["a"])


def test_synchronized_mbb_rejects_missing_values():
    residuals = pd.DataFrame({"a": [1.0, np.nan, 2.0]})
    with pytest.raises(ValueError, match="finite and complete"):
        synchronized_circular_mbb(
            residuals, horizon=2, block_length=2, n_draws=10, seed=1
        )


def test_scale_columns_requires_positive_matching_denominators():
    draws = pd.DataFrame({"a": [2.0, 4.0], "b": [3.0, 6.0]})
    scaled = scale_columns(draws, pd.Series({"a": 2.0, "b": 3.0}))
    assert scaled.iloc[0].to_dict() == {"a": 1.0, "b": 1.0}
    with pytest.raises(ValueError, match="finite, positive"):
        scale_columns(draws, pd.Series({"a": 2.0, "b": 0.0}))


def test_global_mean_test_uses_joint_draws_and_plus_one_correction():
    observed = pd.Series({"a": 2.0, "b": 2.0})
    draws = pd.DataFrame({"a": [0.0, 1.0, 3.0], "b": [0.0, 1.0, 3.0]})
    result = global_mean_test(observed, draws)
    assert result["observed_global_statistic"] == 2.0
    assert result["one_sided_bootstrap_p_value"] == pytest.approx(0.5)
    assert result["n_joint_resamples"] == 3


def test_executed_event_forecast_artifact_has_frozen_geometry():
    protocol = load_protocol()
    frame = pd.read_csv(
        protocol.outputs["event_forecasts"], parse_dates=["origin", "date"]
    )
    assert len(frame) == 2 * 28 * 5 * 130
    assert frame["origin"].eq(protocol.cutoff).all()
    assert frame["date"].min() == protocol.cutoff
    assert frame["date"].max() == protocol.event_end
    assert not frame.duplicated(
        ["model", "portname", "vessel_class", "date"]
    ).any()
    truth = frame.pivot(
        index=["portname", "vessel_class", "date"], columns="model", values="y_true"
    )
    assert np.allclose(
        truth[protocol.primary_model], truth[protocol.robustness_model]
    )


def test_executed_inference_artifact_separates_families_and_context():
    protocol = load_protocol()
    frame = pd.read_csv(protocol.outputs["inference"])
    assert len(frame) == 2 * 3 * (5 + 10 + 3)
    assert set(frame["block_length_days"]) == {7, 14, 28}
    tested = frame["family"].ne("context_descriptive_not_tested")
    assert frame.loc[tested, "romano_wolf_p_value"].between(0, 1).all()
    assert frame.loc[~tested, "romano_wolf_p_value"].isna().all()
    primary = frame.loc[
        frame["family"].eq("restricted_tanker_adaptation")
        & frame["block_length_days"].eq(protocol.block_length)
    ]
    assert primary.groupby("model").size().eq(5).all()
