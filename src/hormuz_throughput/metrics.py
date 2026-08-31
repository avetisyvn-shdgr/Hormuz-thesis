"""Forecast-evaluation metrics for the first modeling layer.

The metrics are deliberately small and dependency-free. They score any
one-step or multi-step forecast against observed values after dropping paired
missing observations, and they fail loudly when no comparable observations
remain. MASE uses an explicit in-sample training series so each rolling-origin
fold is scaled only on data available before that fold's forecast window.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def _paired_arrays(y_true, y_pred) -> tuple[np.ndarray, np.ndarray]:
    """Return finite paired observations as float arrays."""
    yt = pd.Series(y_true, dtype="float64")
    yp = pd.Series(y_pred, dtype="float64")
    if len(yt) != len(yp):
        raise ValueError(
            f"y_true and y_pred must have the same length, got {len(yt)} and {len(yp)}."
        )
    mask = np.isfinite(yt.to_numpy()) & np.isfinite(yp.to_numpy())
    if not mask.any():
        raise ValueError("No finite paired observations to score.")
    return yt.to_numpy()[mask], yp.to_numpy()[mask]


def mae(y_true, y_pred) -> float:
    """Mean absolute error."""
    yt, yp = _paired_arrays(y_true, y_pred)
    return float(np.mean(np.abs(yt - yp)))


def rmse(y_true, y_pred) -> float:
    """Root mean squared error."""
    yt, yp = _paired_arrays(y_true, y_pred)
    return float(np.sqrt(np.mean((yt - yp) ** 2)))


def smape(y_true, y_pred) -> float:
    """Symmetric mean absolute percentage error, in percent.

    Pairs where both observed and predicted are zero contribute 0 rather than
    undefined error. This matters for closure days with true operational zeros.
    """
    yt, yp = _paired_arrays(y_true, y_pred)
    denom = np.abs(yt) + np.abs(yp)
    terms = np.zeros_like(denom, dtype="float64")
    nonzero = denom != 0
    terms[nonzero] = 2.0 * np.abs(yt[nonzero] - yp[nonzero]) / denom[nonzero]
    return float(np.mean(terms) * 100.0)


def mase(y_true, y_pred, y_train, season_length: int = 1) -> float:
    """Mean absolute scaled error.

    The denominator is the mean absolute seasonal-naive error inside the
    training series. If the training series is constant at the requested season
    length, the scale is undefined and the metric returns NaN instead of
    pretending the model has infinite or perfect accuracy.
    """
    if season_length <= 0:
        raise ValueError(f"season_length must be > 0, got {season_length}.")

    yt, yp = _paired_arrays(y_true, y_pred)
    train = pd.Series(y_train, dtype="float64").dropna().to_numpy()
    if len(train) <= season_length:
        raise ValueError(
            f"Need more than season_length={season_length} non-missing training "
            "observations to compute MASE."
        )

    scale = np.mean(np.abs(train[season_length:] - train[:-season_length]))
    if not np.isfinite(scale) or scale == 0:
        return float("nan")
    return float(np.mean(np.abs(yt - yp)) / scale)


def score_forecast(
    y_true,
    y_pred,
    y_train,
    season_length: int = 7,
) -> dict[str, float]:
    """Return the standard metric bundle for one forecast window."""
    return {
        "mae": mae(y_true, y_pred),
        "rmse": rmse(y_true, y_pred),
        "mase": mase(y_true, y_pred, y_train, season_length=season_length),
        "smape": smape(y_true, y_pred),
    }
