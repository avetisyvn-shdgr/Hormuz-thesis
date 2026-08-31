
import pandas as pd
import pytest


from hormuz_throughput.baselines import (
    arx_forecast,
    evaluate_arx,
    evaluate_seasonal_naive,
    seasonal_naive_forecast,
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
    return pd.DataFrame({
        "target": range(60),
        "exog": [v % 5 for v in range(60)],
    }, index=idx)


def test_seasonal_naive_uses_only_lagged_training_values():
    panel = _panel()
    fold = rolling_origin_splits(panel.index, _settings())[0]
    pred = seasonal_naive_forecast(panel["target"], fold, season_length=7)
    expected = panel["target"].shift(7).loc[pred.index]
    pd.testing.assert_series_equal(pred, expected.rename("y_pred"), check_names=True)
    assert pred.index.min() > fold.train_end


def test_seasonal_naive_recursion_does_not_use_held_out_target_values():
    panel = _panel()
    fold = rolling_origin_splits(panel.index, _settings())[0]
    pred = seasonal_naive_forecast(panel["target"], fold, season_length=7)

    altered = panel.copy()
    altered.iloc[fold.test_idx, altered.columns.get_loc("target")] = 99999
    altered_pred = seasonal_naive_forecast(altered["target"], fold, season_length=7)

    pd.testing.assert_series_equal(pred, altered_pred)


def test_evaluate_seasonal_naive_returns_scores_and_forecasts():
    panel = _panel()
    folds = rolling_origin_splits(panel.index, _settings())
    scores, forecasts = evaluate_seasonal_naive(panel, "target", season_length=7, folds=folds)

    assert len(scores) == 2
    assert len(forecasts) == 14
    assert set(["mae", "rmse", "mase", "smape"]).issubset(scores.columns)
    assert scores["n_scored"].tolist() == [7, 7]
    assert (forecasts["error"] == 7).all()


def test_missing_target_column_raises():
    with pytest.raises(KeyError, match="target"):
        evaluate_seasonal_naive(_panel(), "missing")


def test_datetime_index_required():
    panel = _panel().reset_index(drop=True)
    with pytest.raises(TypeError, match="DatetimeIndex"):
        evaluate_seasonal_naive(panel, "target")


def test_positional_fold_consumers_reject_unsorted_panels():
    panel = _panel()
    folds = rolling_origin_splits(panel.index, _settings())
    unsorted = panel.sample(frac=1, random_state=7)

    with pytest.raises(ValueError, match="chronologically sorted"):
        seasonal_naive_forecast(unsorted["target"], folds[0])
    with pytest.raises(ValueError, match="chronologically sorted"):
        evaluate_seasonal_naive(unsorted, "target", folds=folds)
    with pytest.raises(ValueError, match="chronologically sorted"):
        arx_forecast(unsorted, "target", folds[0], exog_cols=["exog"])
    with pytest.raises(ValueError, match="chronologically sorted"):
        evaluate_arx(unsorted, "target", exog_cols=["exog"], folds=folds)


def test_arx_forecast_does_not_use_held_out_target_values():
    panel = _panel()
    fold = rolling_origin_splits(panel.index, _settings())[0]
    pred = arx_forecast(panel, "target", fold, exog_cols=["exog"])

    altered = panel.copy()
    altered.iloc[fold.test_idx, altered.columns.get_loc("target")] = 99999
    altered_pred = arx_forecast(altered, "target", fold, exog_cols=["exog"])

    pd.testing.assert_series_equal(pred, altered_pred)


def test_ar_forecast_supports_empty_exogenous_set():
    panel = _panel()
    fold = rolling_origin_splits(panel.index, _settings())[0]
    pred = arx_forecast(panel, "target", fold, exog_cols=[])
    assert len(pred) == len(fold.test_idx)
    assert pred.notna().all()


def test_ar_forecast_is_independent_of_held_out_exogenous_values():
    panel = _panel()
    fold = rolling_origin_splits(panel.index, _settings())[0]
    pred = arx_forecast(panel, "target", fold, exog_cols=[])
    altered = panel.copy()
    altered.iloc[fold.test_idx, altered.columns.get_loc("exog")] = 99999
    altered_pred = arx_forecast(altered, "target", fold, exog_cols=[])
    pd.testing.assert_series_equal(pred, altered_pred)


def test_evaluate_arx_returns_scores_and_forecasts():
    panel = _panel()
    folds = rolling_origin_splits(panel.index, _settings())
    scores, forecasts = evaluate_arx(panel, "target", exog_cols=["exog"], folds=folds)

    assert len(scores) == 2
    assert len(forecasts) == 14
    assert set(["mae", "rmse", "mase", "smape"]).issubset(scores.columns)
    assert scores["n_scored"].tolist() == [7, 7]
    assert scores["exog_cols"].tolist() == ["exog", "exog"]


def test_evaluate_ar_returns_empty_exog_metadata():
    panel = _panel()
    folds = rolling_origin_splits(panel.index, _settings())
    scores, _ = evaluate_arx(
        panel, "target", exog_cols=[], folds=folds, model_name="ar_lag1_7"
    )
    assert scores["model"].tolist() == ["ar_lag1_7", "ar_lag1_7"]
    assert scores["exog_cols"].tolist() == ["", ""]
