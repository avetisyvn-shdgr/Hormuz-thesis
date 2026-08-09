"""Transparent forecasting baselines for the modeling phase.

These baselines are target-agnostic: callers choose the dependent-variable
column, while this module only handles leakage-safe prediction and scoring over
the rolling-origin folds produced by ``validation.py``.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .metrics import score_forecast
from .validation import Fold, require_chronological_index, rolling_origin_splits


def seasonal_naive_forecast(
    series: pd.Series,
    fold: Fold,
    season_length: int = 7,
) -> pd.Series:
    """Forecast a fold by copying the value from ``season_length`` days earlier.

    The lookup is date-based rather than positional, so it remains correct if a
    future panel has calendar gaps. Any test date whose lagged value is not
    available before the fold origin receives NaN and is excluded from metrics.
    """
    if season_length <= 0:
        raise ValueError(f"season_length must be > 0, got {season_length}.")

    require_chronological_index(series.index, name="series index")
    y = series.astype("float64")
    history = y.iloc[fold.train_idx].copy()
    test_index = y.iloc[fold.test_idx].index

    preds = []
    for ts in test_index:
        lag_ts = ts - pd.Timedelta(days=season_length)
        if lag_ts in history.index:
            pred = history.loc[lag_ts]
        else:
            pred = np.nan
        preds.append(pred)
        history.loc[ts] = pred
    return pd.Series(preds, index=test_index, name="y_pred")


def evaluate_seasonal_naive(
    panel: pd.DataFrame,
    target: str,
    season_length: int = 7,
    folds: list[Fold] | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Score a seasonal-naive baseline over rolling-origin folds.

    Returns
    -------
    scores, forecasts
        ``scores`` has one row per fold. ``forecasts`` has one row per test-day
        forecast and is useful for plotting residuals or auditing fold geometry.
    """
    if target not in panel.columns:
        raise KeyError(f"target {target!r} not found in panel columns.")
    if not isinstance(panel.index, pd.DatetimeIndex):
        raise TypeError("panel must be indexed by a DatetimeIndex.")
    require_chronological_index(panel.index, name="panel index")

    folds = folds or rolling_origin_splits(panel.index)
    y = panel[target].astype("float64")

    score_rows = []
    forecast_rows = []
    for fold in folds:
        y_train = y.iloc[fold.train_idx]
        y_test = y.iloc[fold.test_idx]
        y_pred = seasonal_naive_forecast(y, fold, season_length=season_length)
        metrics = score_forecast(y_test, y_pred, y_train, season_length=season_length)

        score_rows.append({
            "model": f"seasonal_naive_{season_length}d",
            "target": target,
            "fold": fold.name,
            "train_start": fold.train_start.date(),
            "train_end": fold.train_end.date(),
            "test_start": fold.test_start.date(),
            "test_end": fold.test_end.date(),
            "n_train": len(fold.train_idx),
            "n_test": len(fold.test_idx),
            "n_scored": int((y_test.notna() & y_pred.notna()).sum()),
            **metrics,
        })

        fold_forecasts = pd.DataFrame({
            "date": y_test.index,
            "model": f"seasonal_naive_{season_length}d",
            "target": target,
            "fold": fold.name,
            "y_true": y_test.to_numpy(),
            "y_pred": y_pred.to_numpy(),
        })
        fold_forecasts["error"] = fold_forecasts["y_true"] - fold_forecasts["y_pred"]
        forecast_rows.append(fold_forecasts)

    scores = pd.DataFrame(score_rows)
    forecasts = pd.concat(forecast_rows, ignore_index=True)
    return scores, forecasts


def _design_row(
    panel: pd.DataFrame,
    target: str,
    ts: pd.Timestamp,
    history: pd.Series,
    exog_cols: list[str],
    y_lags: tuple[int, ...],
) -> dict[str, float]:
    """Build one ARX design row from lagged target values and current exog."""
    row: dict[str, float] = {}
    for lag in y_lags:
        row[f"{target}_lag_{lag}d"] = history.get(ts - pd.Timedelta(days=lag), np.nan)
    for col in exog_cols:
        row[col] = panel.at[ts, col] if ts in panel.index else np.nan

    # Simple deterministic seasonality; no future information involved.
    dow = ts.dayofweek
    row["dow_sin"] = np.sin(2 * np.pi * dow / 7)
    row["dow_cos"] = np.cos(2 * np.pi * dow / 7)
    return row


def _standardized_ridge_fit(
    x: pd.DataFrame,
    y: pd.Series,
    ridge_alpha: float,
) -> tuple[np.ndarray, pd.Series, pd.Series, list[str]]:
    """Fit a small ridge/OLS model on standardized columns.

    Uses an augmented least-squares system instead of normal equations. This is
    more stable for the capacity target, where values are in the millions.
    """
    cols = list(x.columns)
    x_mean = x.mean()
    x_std = x.std(ddof=0).replace(0, 1.0)
    xz = (x - x_mean) / x_std
    mat = np.column_stack([np.ones(len(xz)), xz.to_numpy(dtype="float64")])
    target = y.to_numpy(dtype="float64")

    if ridge_alpha > 0:
        penalty = np.eye(mat.shape[1]) * np.sqrt(ridge_alpha)
        penalty[0, 0] = 0.0  # never penalize intercept
        mat = np.vstack([mat, penalty])
        target = np.concatenate([target, np.zeros(mat.shape[1])])

    beta, *_ = np.linalg.lstsq(mat, target, rcond=None)
    return beta, x_mean, x_std, cols


def arx_forecast(
    panel: pd.DataFrame,
    target: str,
    fold: Fold,
    exog_cols: list[str],
    y_lags: tuple[int, ...] = (1, 7),
    ridge_alpha: float = 1e-6,
) -> pd.Series:
    """Recursive autoregressive forecast, optionally with exogenous controls.

    Target lags inside the test window use prior predictions, not held-out
    observed values. That keeps the 30-day validation horizon honest. Exogenous
    variables are treated as observed controls for conditional forecasting; the
    causal interpretation of post-treatment exog remains a later design choice.
    """
    missing = [c for c in [target, *exog_cols] if c not in panel.columns]
    if missing:
        raise KeyError(f"columns not found in panel: {missing}")
    if any(lag <= 0 for lag in y_lags):
        raise ValueError(f"all y_lags must be > 0, got {y_lags}.")
    if ridge_alpha < 0:
        raise ValueError(f"ridge_alpha must be >= 0, got {ridge_alpha}.")

    if not isinstance(panel.index, pd.DatetimeIndex):
        raise TypeError("panel must be indexed by a DatetimeIndex.")
    require_chronological_index(panel.index, name="panel index")
    y = panel[target].astype("float64")
    train_index = y.iloc[fold.train_idx].index
    test_index = y.iloc[fold.test_idx].index

    train_rows = []
    train_y = []
    train_history = y.loc[:fold.train_end]
    for ts in train_index:
        row = _design_row(panel, target, ts, train_history, exog_cols, y_lags)
        if np.isfinite(list(row.values())).all() and np.isfinite(y.at[ts]):
            train_rows.append(row)
            train_y.append(y.at[ts])

    min_train = len(y_lags) + len(exog_cols) + 4
    if len(train_rows) < min_train:
        raise ValueError(
            f"Not enough complete training rows for ARX: have {len(train_rows)}, "
            f"need at least {min_train}."
        )

    x_train = pd.DataFrame(train_rows, index=range(len(train_rows)))
    y_train = pd.Series(train_y, dtype="float64")
    beta, x_mean, x_std, cols = _standardized_ridge_fit(x_train, y_train, ridge_alpha)

    history = train_history.copy()
    preds = []
    for ts in test_index:
        row = _design_row(panel, target, ts, history, exog_cols, y_lags)
        values = pd.Series(row, dtype="float64").reindex(cols)
        if values.isna().any():
            pred = np.nan
        else:
            xz = ((values - x_mean) / x_std).to_numpy(dtype="float64")
            pred = float(np.r_[1.0, xz] @ beta)
        preds.append(pred)
        history.loc[ts] = pred

    return pd.Series(preds, index=test_index, name="y_pred")


def evaluate_arx(
    panel: pd.DataFrame,
    target: str,
    exog_cols: list[str],
    y_lags: tuple[int, ...] = (1, 7),
    season_length: int = 7,
    ridge_alpha: float = 1e-6,
    folds: list[Fold] | None = None,
    model_name: str | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Score an AR or ARX baseline over rolling-origin folds."""
    if target not in panel.columns:
        raise KeyError(f"target {target!r} not found in panel columns.")
    if not isinstance(panel.index, pd.DatetimeIndex):
        raise TypeError("panel must be indexed by a DatetimeIndex.")
    require_chronological_index(panel.index, name="panel index")

    folds = folds or rolling_origin_splits(panel.index)
    y = panel[target].astype("float64")
    model_name = model_name or "arx_lag" + "_".join(str(l) for l in y_lags)

    score_rows = []
    forecast_rows = []
    for fold in folds:
        y_train = y.iloc[fold.train_idx]
        y_test = y.iloc[fold.test_idx]
        y_pred = arx_forecast(
            panel,
            target=target,
            fold=fold,
            exog_cols=exog_cols,
            y_lags=y_lags,
            ridge_alpha=ridge_alpha,
        )
        metrics = score_forecast(y_test, y_pred, y_train, season_length=season_length)

        score_rows.append({
            "model": model_name,
            "target": target,
            "fold": fold.name,
            "train_start": fold.train_start.date(),
            "train_end": fold.train_end.date(),
            "test_start": fold.test_start.date(),
            "test_end": fold.test_end.date(),
            "n_train": len(fold.train_idx),
            "n_test": len(fold.test_idx),
            "n_scored": int((y_test.notna() & y_pred.notna()).sum()),
            "exog_cols": ",".join(exog_cols),
            **metrics,
        })

        fold_forecasts = pd.DataFrame({
            "date": y_test.index,
            "model": model_name,
            "target": target,
            "fold": fold.name,
            "y_true": y_test.to_numpy(),
            "y_pred": y_pred.to_numpy(),
        })
        fold_forecasts["error"] = fold_forecasts["y_true"] - fold_forecasts["y_pred"]
        forecast_rows.append(fold_forecasts)

    scores = pd.DataFrame(score_rows)
    forecasts = pd.concat(forecast_rows, ignore_index=True)
    return scores, forecasts


def aggregate_scores(scores: pd.DataFrame) -> pd.DataFrame:
    """Summarize fold-level scores for reporting."""
    metric_cols = ["mae", "rmse", "mase", "smape"]
    group_cols = ["model", "target"]
    out = (
        scores.groupby(group_cols, dropna=False)[metric_cols]
        .agg(["mean", "median", "std"])
        .reset_index()
    )
    out.columns = [
        "_".join(str(part) for part in col if part)
        if isinstance(col, tuple) else str(col)
        for col in out.columns
    ]
    return out
