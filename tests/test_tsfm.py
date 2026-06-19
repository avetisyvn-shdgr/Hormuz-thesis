"""Contract tests for the TSFM benchmark harness.

These run in the CORE Python env with NO heavy model dependencies: they exercise
the harness plumbing through the dependency-free StubAdapter, plus the registry,
aggregation and admission-test logic. They do NOT validate the three real
foundation-model adapters — those require the isolated benchmark env and a human
run (CLAUDE.md rule 4).
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lngfreight.tsfm import (
    FOUNDATION_MODELS,
    MODEL_REGISTRY,
    QuantileForecast,
    StubAdapter,
    admission_test,
    aggregate_benchmark,
    run_benchmark,
)
from lngfreight.validation import rolling_origin_splits


def _settings():
    return {
        "study_window": {"treatment_candidates": {"a": "2022-02-20"}},
        "modeling": {"validation": {
            "scheme": "expanding",
            "initial_train_days": 21,
            "horizon_days": 7,
            "step_days": 7,
            "sliding_train_days": 21,
            "max_folds": 2,
            "cutoff": "2022-02-20",
        }},
    }


def _panel():
    idx = pd.date_range("2022-01-01", periods=60, freq="D", name="date")
    rng = np.random.default_rng(0)
    base = 100 + 10 * np.sin(2 * np.pi * np.arange(60) / 7)
    return pd.DataFrame({"target": base + rng.normal(0, 1, 60)}, index=idx)


def test_quantile_forecast_validates_shapes_and_levels():
    with pytest.raises(ValueError):
        QuantileForecast(np.zeros(3), np.zeros(2), np.zeros(3), 0.025, 0.975)
    with pytest.raises(ValueError):
        QuantileForecast(np.zeros(3), np.zeros(3), np.zeros(3), 0.9, 0.1)
    fc = QuantileForecast(np.zeros(3), -np.ones(3), np.ones(3), 0.025, 0.975)
    assert fc.nominal_coverage == pytest.approx(0.95)


def test_registry_lists_three_foundation_models_plus_stub():
    assert set(FOUNDATION_MODELS) == {"chronos2", "timesfm", "moirai"}
    assert set(MODEL_REGISTRY) == {"stub", *FOUNDATION_MODELS}


def test_stub_adapter_honors_requested_levels_and_horizon():
    adapter = StubAdapter(season_length=7)
    train = pd.Series(np.arange(30.0))
    fc = adapter.predict(train, horizon=7, lower_q=0.025, upper_q=0.975)
    assert len(fc.point) == 7
    assert fc.level_lower == 0.025 and fc.level_upper == 0.975
    assert np.all(fc.lower <= fc.point) and np.all(fc.point <= fc.upper)


def test_run_benchmark_emits_expected_columns_and_rows():
    panel = _panel()
    folds = rolling_origin_splits(panel.index, _settings())
    scores, forecasts = run_benchmark(panel, "target", StubAdapter(7), folds=folds)

    assert len(scores) == 2
    assert len(forecasts) == 14
    for col in ["mase", "rmse", "empirical_coverage", "nominal_coverage",
                "coverage_error", "interval_width", "runtime_s"]:
        assert col in scores.columns
    assert np.allclose(scores["nominal_coverage"], 0.95)
    assert scores["empirical_coverage"].between(0, 1).all()
    # coverage_error is empirical minus nominal, by construction.
    assert np.allclose(
        scores["coverage_error"],
        scores["empirical_coverage"] - scores["nominal_coverage"],
    )


def test_harness_is_leakage_safe_test_values_do_not_change_forecasts():
    """Per-fold anti-leakage guarantee: only a fold's own pre-origin training
    context reaches the model, so altering THAT fold's held-out test values must
    not change its forecast. Uses a single fold to avoid the expanding-window
    coupling where a later fold legitimately trains on an earlier fold's
    (still pre-treatment) test window."""
    panel = _panel()
    settings = _settings()
    settings["modeling"]["validation"]["max_folds"] = 1
    folds = rolling_origin_splits(panel.index, settings)
    assert len(folds) == 1
    _, base = run_benchmark(panel, "target", StubAdapter(7), folds=folds)

    altered = panel.copy()
    altered.iloc[folds[0].test_idx, altered.columns.get_loc("target")] = 99999.0
    _, alt = run_benchmark(altered, "target", StubAdapter(7), folds=folds)

    pd.testing.assert_series_equal(base["y_pred"], alt["y_pred"])
    pd.testing.assert_series_equal(base["lower"], alt["lower"])
    pd.testing.assert_series_equal(base["upper"], alt["upper"])


def test_aggregate_benchmark_one_row_per_model_target():
    panel = _panel()
    folds = rolling_origin_splits(panel.index, _settings())
    scores, _ = run_benchmark(panel, "target", StubAdapter(7), folds=folds)
    agg = aggregate_benchmark(scores)
    assert len(agg) == 1
    assert {"mase_mean", "coverage_error_mean", "interval_width_mean"}.issubset(agg.columns)


def test_admission_test_requires_both_mase_and_calibration():
    # Candidate beats AR on MASE and has better calibration -> admitted.
    tsfm = pd.DataFrame([{
        "model": "chronos2", "target": "y",
        "mase_mean": 0.8, "coverage_error_mean": 0.01,
    }])
    ar = pd.DataFrame([{
        "model": "ar_lag1_7", "target": "y",
        "mase_mean": 1.0, "coverage_error_mean": 0.05,
    }])
    v = admission_test(tsfm, ar)
    assert bool(v.loc[0, "admitted"]) is True

    # Beats MASE but worse calibration -> rejected.
    tsfm2 = tsfm.copy()
    tsfm2.loc[0, "coverage_error_mean"] = 0.20
    v2 = admission_test(tsfm2, ar)
    assert bool(v2.loc[0, "admitted"]) is False
    assert "calibration" in v2.loc[0, "verdict"]


def test_admission_test_calibration_unavailable_when_ar_has_no_interval():
    tsfm = pd.DataFrame([{
        "model": "chronos2", "target": "y",
        "mase_mean": 0.8, "coverage_error_mean": 0.01,
    }])
    ar = pd.DataFrame([{"model": "ar_lag1_7", "target": "y", "mase_mean": 1.0}])
    v = admission_test(tsfm, ar)
    assert bool(v.loc[0, "admitted"]) is False
    assert bool(v.loc[0, "calibration_assessed"]) is False
    assert bool(v.loc[0, "beats_ar_mase"]) is True
    assert "NOT assessed" in v.loc[0, "verdict"]


def test_admission_test_raises_on_missing_ar_model():
    tsfm = pd.DataFrame([{"model": "m", "target": "y", "mase_mean": 1.0,
                          "coverage_error_mean": 0.0}])
    ar = pd.DataFrame([{"model": "other", "target": "y", "mase_mean": 1.0}])
    with pytest.raises(ValueError, match="not found"):
        admission_test(tsfm, ar)
