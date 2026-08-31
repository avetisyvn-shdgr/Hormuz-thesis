"""Tests for the AR-only corridor-transmission outputs."""

import numpy as np
import pandas as pd
import pytest


from hormuz_throughput.corridor_transmission import (
    ar_window_statistic,
    basin_point_summary,
)


def _series(values, start="2022-01-01"):
    idx = pd.date_range(start, periods=len(values), freq="D")
    return pd.Series(values, index=idx, dtype="float64")


def test_window_geometry_is_leakage_safe():
    s = _series(np.r_[np.full(500, 50.0), np.full(60, 50.0)])
    origin = s.index[0] + pd.Timedelta(days=500)
    out = ar_window_statistic(s, history_start=s.index[0], origin=origin, horizon_days=30)
    assert out["train_start"] == s.index[0]
    assert out["train_end"] == origin - pd.Timedelta(days=1)
    assert out["window_end"] == origin + pd.Timedelta(days=29)
    assert 0 < out["n_scored"] <= 30


def test_deviation_sign_matches_a_known_collapse():
    pre = np.full(500, 100.0)
    post = np.zeros(40)
    s = _series(np.r_[pre, post])
    origin = s.index[0] + pd.Timedelta(days=500)
    out = ar_window_statistic(s, history_start=s.index[0], origin=origin, horizon_days=30)
    assert out["statistic_value"] == pytest.approx(-1.0, abs=0.05)


def test_statistic_depends_only_on_its_own_series():
    s = _series(np.r_[np.full(500, 30.0), np.full(40, 12.0)])
    origin = s.index[0] + pd.Timedelta(days=500)
    base = ar_window_statistic(s, history_start=s.index[0], origin=origin, horizon_days=30)
    other = _series(np.r_[np.full(500, 30.0), np.full(40, 1.0)])
    again = ar_window_statistic(s, history_start=s.index[0], origin=origin, horizon_days=30)
    other_stat = ar_window_statistic(other, history_start=other.index[0], origin=origin, horizon_days=30)
    assert base["statistic_value"] == again["statistic_value"]
    assert other_stat["statistic_value"] != base["statistic_value"]


def test_masked_values_do_not_collapse_the_forecast():
    values = np.full(540, 80.0)
    values[499] = np.nan
    values[505:510] = np.nan
    s = _series(values)
    origin = s.index[0] + pd.Timedelta(days=500)
    out = ar_window_statistic(s, history_start=s.index[0], origin=origin, horizon_days=30)
    assert np.isfinite(out["statistic_value"])
    assert out["n_scored"] == 25


def test_basin_summary_is_point_only_and_never_additive():
    observed = pd.DataFrame({
        "target": ["n_tanker"] * 3,
        "corridor": ["a", "b", "c"],
        "statistic_value": [-0.5, -0.1, 0.2],
    })
    metadata = pd.DataFrame({
        "slug": ["a", "b", "c"],
        "basin_group": ["g1", "g1", "g2"],
    })
    summary = basin_point_summary(observed, metadata)
    g1 = summary.loc[summary["basin_group"].eq("g1")].iloc[0]
    assert g1["n_corridors"] == 2
    assert g1["mean_signed_deviation_point"] == pytest.approx(-0.3)
    assert (summary["interval_policy"] == "point_only_not_additive").all()
    assert "sum" not in [c for c in summary.columns if "signed" in c and "sum" in c]


def test_basin_summary_rejects_unmapped_corridor():
    observed = pd.DataFrame({
        "target": ["n_tanker"], "corridor": ["z"], "statistic_value": [0.1],
    })
    metadata = pd.DataFrame({"slug": ["a"], "basin_group": ["g1"]})
    with pytest.raises(ValueError, match="missing a basin mapping"):
        basin_point_summary(observed, metadata)
