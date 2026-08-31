"""Phase 2 propagation model: seal, shape, and invariance checks."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from hormuz_throughput.propagation import (
    EventSpec,
    fit_propagation,
    reallocation_share,
    sanity_gate,
)


def _panel(n_days: int = 1200, n_units: int = 8, seed: int = 7) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2020-01-01", periods=n_days, freq="D")
    levels = np.array([50.0, 40.0, 30.0, 25.0, 20.0, 15.0, 10.0, 5.0])[:n_units]
    data = rng.normal(levels, levels * 0.08, size=(n_days, n_units)).clip(0.1)
    cols = [f"unit_{i}" for i in range(n_units)]
    return pd.DataFrame(data, index=idx, columns=cols)


def test_held_out_event_cannot_leak_into_training():
    panel = _panel()
    specs = [
        EventSpec("a", "unit_0", pd.Timestamp("2021-01-01")),
        EventSpec("b", "unit_1", pd.Timestamp("2021-06-01")),
        EventSpec("sealed", "unit_2", pd.Timestamp("2021-06-15"), role="HELD_OUT"),
    ]
    with pytest.raises(ValueError, match="sealed onset"):
        fit_propagation(panel, specs, horizon_weeks=8)


def test_sealed_event_may_be_passed_when_windows_are_clear():
    panel = _panel()
    specs = [
        EventSpec("a", "unit_0", pd.Timestamp("2021-01-01")),
        EventSpec("b", "unit_1", pd.Timestamp("2021-03-01")),
        EventSpec("sealed", "unit_2", pd.Timestamp("2022-06-01"), role="HELD_OUT"),
    ]
    fit = fit_propagation(panel, specs, horizon_weeks=8)
    assert fit.diagnostics["sealed_events"] == ["sealed"]
    assert fit.diagnostics["n_train_events"] == 2
    assert "sealed" not in fit.receiver_loadings.index


def test_requires_two_training_events():
    panel = _panel()
    specs = [EventSpec("only", "unit_0", pd.Timestamp("2021-01-01"))]
    with pytest.raises(ValueError, match="two training events"):
        fit_propagation(panel, specs, horizon_weeks=4)


def test_loadings_are_unit_norm_and_profile_shared():
    panel = _panel()
    specs = [
        EventSpec("a", "unit_0", pd.Timestamp("2021-01-01")),
        EventSpec("b", "unit_1", pd.Timestamp("2021-07-01")),
    ]
    fit = fit_propagation(panel, specs, horizon_weeks=6)
    for _, row in fit.receiver_loadings.iterrows():
        assert np.isclose(np.linalg.norm(row.to_numpy()), 1.0, atol=1e-6)
    assert np.isclose(np.linalg.norm(fit.profile.to_numpy()), 1.0, atol=1e-6)
    assert len(fit.profile) == 7


def test_reallocation_share_uses_absolute_units():
    """A large and a small chokepoint gaining the same FRACTION must not count
    the same. The share must weight by each unit's own baseline."""
    resp = pd.DataFrame(
        {0: [-0.5, 0.25, 0.25]}, index=["big", "mid", "small"]
    )
    equal = reallocation_share(resp, "big", pd.Series({"big": 100.0, "mid": 100.0, "small": 100.0}))
    skewed = reallocation_share(resp, "big", pd.Series({"big": 100.0, "mid": 100.0, "small": 1.0}))
    assert equal["gross_gain_per_day"] > skewed["gross_gain_per_day"]
    assert np.isclose(equal["loss_per_day"], 50.0)


def test_sanity_gate_reports_rank():
    panel = _panel()
    specs = [
        EventSpec("a", "unit_0", pd.Timestamp("2021-01-01")),
        EventSpec("b", "unit_1", pd.Timestamp("2021-07-01")),
    ]
    fit = fit_propagation(panel, specs, horizon_weeks=6)
    gate = sanity_gate(fit, "a", "unit_0", "unit_3")
    assert 1 <= gate["rank_among_receivers"] <= gate["n_receivers"]
    assert set(gate) >= {"loading", "rank_among_receivers", "passed"}


def test_pair_reallocation_reports_recovered_fraction():
    from hormuz_throughput.propagation import pair_reallocation

    panel = _panel(n_days=1400)
    spec = EventSpec("a", "unit_0", pd.Timestamp("2022-01-01"))
    out = pair_reallocation(
        panel, spec, "unit_3", ["unit_0"], horizon_weeks=4, n_draws=30
    )
    assert set(out) >= {
        "observed_gain_per_day",
        "emitter_loss_per_day",
        "recovered_fraction",
        "percentile_of_observed",
    }
    assert 0.0 <= out["percentile_of_observed"] <= 100.0
    assert out["n_draws"] > 0
