"""Contract tests for the TSFM benchmark harness.

These run in the CORE Python env with NO heavy model dependencies: they exercise
the harness plumbing through the dependency-free StubAdapter, plus the registry,
aggregation and admission-test logic. They do NOT validate the three real
foundation-model adapters — those require the isolated benchmark env and a human
run (CLAUDE.md rule 4).
"""

import numpy as np
import pandas as pd
import pytest


from hormuz_throughput import config
from hormuz_throughput.tsfm import (
    FOUNDATION_MODELS,
    MODEL_REGISTRY,
    QuantileForecast,
    StubAdapter,
    TSFMAdapter,
    admission_test,
    aggregate_benchmark,
    configure_deterministic_execution,
    counterfactual_shortfall,
    run_benchmark,
)
from hormuz_throughput.validation import rolling_origin_splits


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


def test_deterministic_configuration_reseeds_numpy():
    configure_deterministic_execution(123)
    first = np.random.random(4)
    configure_deterministic_execution(123)
    second = np.random.random(4)
    np.testing.assert_array_equal(first, second)


def test_stub_adapter_honors_requested_levels_and_horizon():
    adapter = StubAdapter(season_length=7)
    train = pd.Series(np.arange(30.0))
    fc = adapter.predict(train, horizon=7, lower_q=0.025, upper_q=0.975)
    assert len(fc.point) == 7
    assert fc.level_lower == 0.025 and fc.level_upper == 0.975
    assert np.all(fc.lower <= fc.point) and np.all(fc.point <= fc.upper)


def test_adapter_preserves_calendar_steps_with_past_only_fill():
    class CapturingAdapter(TSFMAdapter):
        name = "capture"

        def _predict(self, context, horizon, lower_q, upper_q):
            self.context = context.copy()
            point = np.zeros(horizon)
            return QuantileForecast(point, point, point, lower_q, upper_q)

    adapter = CapturingAdapter()
    index = pd.to_datetime(["2024-01-01", "2024-01-03", "2024-01-04"])
    train = pd.Series([1.0, np.nan, 4.0], index=index)
    adapter.predict(train, horizon=2)

    expected_index = pd.date_range("2024-01-01", "2024-01-04", freq="D")
    pd.testing.assert_index_equal(adapter.context.index, expected_index)
    assert adapter.context.tolist() == [1.0, 1.0, 1.0, 4.0]


def test_adapter_rejects_leading_or_noncalendar_missing_context():
    adapter = StubAdapter(season_length=7)
    dated = pd.Series(
        [np.nan, 2.0],
        index=pd.date_range("2024-01-01", periods=2, freq="D"),
    )
    with pytest.raises(ValueError, match="leading missing"):
        adapter.predict(dated, horizon=1)
    with pytest.raises(ValueError, match="Non-datetime"):
        adapter.predict(pd.Series([1.0, np.nan, 3.0]), horizon=1)


def test_run_benchmark_emits_expected_columns_and_rows():
    panel = _panel()
    folds = rolling_origin_splits(panel.index, _settings())
    scores, forecasts = run_benchmark(panel, "target", StubAdapter(7), folds=folds)

    assert len(scores) == 2
    assert len(forecasts) == 14
    for col in ["mase", "rmse", "empirical_coverage", "nominal_coverage",
                "coverage_error", "interval_width"]:
        assert col in scores.columns
    assert "runtime_s" not in scores.columns
    assert np.allclose(scores["nominal_coverage"], 0.95)
    assert scores["empirical_coverage"].between(0, 1).all()
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


def test_counterfactual_shortfall_is_leakage_safe_and_signed():
    """Counterfactual trains only on pre-cutoff data, and post-cutoff observed
    values must not change the forecast; throughput_loss = counterfactual - obs."""
    idx = pd.date_range("2022-01-01", periods=120, freq="D", name="date")
    panel = pd.DataFrame({"target": 100.0 + np.arange(120) % 7}, index=idx)
    cutoff = pd.Timestamp("2022-04-01")

    daily, summary = counterfactual_shortfall(
        panel, "target", StubAdapter(7), cutoff=cutoff
    )
    assert summary["n_days"] == int((panel.index >= cutoff).sum())
    np.testing.assert_allclose(
        daily["throughput_loss_vs_counterfactual"],
        daily["y_pred"] - daily["y_true"],
    )

    altered = panel.copy()
    altered.loc[altered.index >= cutoff, "target"] = 0.0
    daily2, _ = counterfactual_shortfall(altered, "target", StubAdapter(7), cutoff=cutoff)
    np.testing.assert_allclose(daily["y_pred"], daily2["y_pred"])


def test_frozen_tsfm_counterfactual_matches_active_ar_dates_and_observations():
    out_dir = config.path("data_processed")
    tsfm_summary = pd.read_csv(out_dir / "tsfm_counterfactual_summary.csv")
    tsfm_daily = pd.read_csv(
        out_dir / "tsfm_counterfactual_daily.csv", parse_dates=["date"]
    )
    ar_summary = pd.read_csv(out_dir / "counterfactual_post_treatment_summary.csv")
    ar_daily = pd.read_csv(
        out_dir / "counterfactual_post_treatment.csv", parse_dates=["date"]
    )

    for target in tsfm_summary["target"]:
        tsfm_row = tsfm_summary.loc[tsfm_summary["target"].eq(target)].iloc[0]
        ar_row = ar_summary.loc[
            ar_summary["model"].eq("ar_lag1_7")
            & ar_summary["target"].eq(target)
        ].iloc[0]
        assert tsfm_row["start"] == ar_row["start"]
        assert tsfm_row["end"] == ar_row["end"]
        assert tsfm_row["n_days"] == ar_row["n_days"]
        assert tsfm_row["observed_sum"] == pytest.approx(ar_row["observed_sum"])
        assert bool(tsfm_row["matched_ar_dates"])
        assert bool(tsfm_row["matched_ar_observed"])

        tsfm_valid = (
            tsfm_daily.loc[tsfm_daily["target"].eq(target)]
            .dropna(subset=["y_true", "y_pred"])
            .sort_values("date")
            .reset_index(drop=True)
        )
        ar_valid = (
            ar_daily.loc[
                ar_daily["model"].eq("ar_lag1_7")
                & ar_daily["target"].eq(target)
            ]
            .dropna(subset=["y_true", "y_pred"])
            .sort_values("date")
            .reset_index(drop=True)
        )
        pd.testing.assert_series_equal(tsfm_valid["date"], ar_valid["date"])
        np.testing.assert_allclose(tsfm_valid["y_true"], ar_valid["y_true"])


def test_current_results_report_uses_matched_horizon_tsfm_values():
    text = (
        config.ROOT / "reports" / "current_results_summary.md"
    ).read_text(encoding="utf-8")
    assert "Matched-horizon TSFM sensitivity" in text
    assert "130 transit days" in text
    assert "118 valid capacity days" in text
    assert "**-3.7%**" in text
    assert "**-10.6%**" in text
    assert "+2.4%" not in text
    assert "196.1M" not in text
    assert "206.9M" not in text


def test_counterfactual_requires_pre_and_post_rows():
    idx = pd.date_range("2022-01-01", periods=10, freq="D", name="date")
    panel = pd.DataFrame({"target": np.arange(10.0)}, index=idx)
    with pytest.raises(ValueError, match="pre- and post-cutoff"):
        counterfactual_shortfall(panel, "target", StubAdapter(7),
                                 cutoff=pd.Timestamp("2021-01-01"))


def test_admission_test_raises_on_missing_ar_model():
    tsfm = pd.DataFrame([{"model": "m", "target": "y", "mase_mean": 1.0,
                          "coverage_error_mean": 0.0}])
    ar = pd.DataFrame([{"model": "other", "target": "y", "mase_mean": 1.0}])
    with pytest.raises(ValueError, match="not found"):
        admission_test(tsfm, ar)
