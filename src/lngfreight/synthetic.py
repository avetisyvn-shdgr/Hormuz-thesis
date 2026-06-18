"""Simple donor-weighted synthetic-control helpers.

This module is intentionally small and dependency-free. The goal is a
corroborating donor-weighted diagnostic, not a new primary estimator.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def project_to_simplex(values: np.ndarray) -> np.ndarray:
    """Project a vector onto the non-negative unit simplex."""
    v = np.asarray(values, dtype="float64")
    if v.ndim != 1:
        raise ValueError("values must be one-dimensional.")
    if len(v) == 0:
        raise ValueError("values must not be empty.")

    u = np.sort(v)[::-1]
    cssv = np.cumsum(u)
    rho_candidates = u * np.arange(1, len(u) + 1) > (cssv - 1)
    if not rho_candidates.any():
        return np.full(len(v), 1.0 / len(v))
    rho = np.flatnonzero(rho_candidates)[-1]
    theta = (cssv[rho] - 1) / (rho + 1)
    return np.maximum(v - theta, 0.0)


def fit_simplex_weights(
    y: pd.Series,
    donors: pd.DataFrame,
    max_iter: int = 10000,
    tol: float = 1e-10,
) -> pd.Series:
    """Fit convex donor weights by Frank-Wolfe optimization."""
    if donors.empty:
        raise ValueError("Need at least one donor column.")

    x = donors.to_numpy(dtype="float64")
    target = y.to_numpy(dtype="float64")
    mask = np.isfinite(target) & np.isfinite(x).all(axis=1)
    x = x[mask]
    target = target[mask]
    if len(target) == 0:
        raise ValueError("No complete pre-period rows for synthetic-control fit.")

    n = x.shape[1]
    weights = np.full(n, 1.0 / n)

    for t in range(max_iter):
        with np.errstate(over="ignore", divide="ignore", invalid="ignore"):
            residual = x @ weights - target
            grad = (2.0 / len(target)) * (x.T @ residual)
        if not np.isfinite(residual).all():
            raise ValueError("Synthetic-control optimization produced non-finite residuals.")
        if not np.isfinite(grad).all():
            raise ValueError("Synthetic-control optimization produced non-finite gradients.")
        vertex = np.zeros(n)
        vertex[int(np.argmin(grad))] = 1.0
        direction = vertex - weights
        gap = float(-grad @ direction)
        if gap < tol:
            break
        gamma = 2.0 / (t + 2.0)
        next_weights = weights + gamma * direction
        if np.linalg.norm(next_weights - weights, ord=1) < tol:
            weights = next_weights
            break
        weights = next_weights

    return pd.Series(weights, index=donors.columns, name="weight")


def scale_by_pre_period_mean(
    wide: pd.DataFrame,
    pre_mask: pd.Series | np.ndarray,
) -> tuple[pd.DataFrame, pd.Series]:
    """Scale each series by its own pre-period mean."""
    pre = wide.loc[pre_mask]
    scale = pre.mean(skipna=True)
    scale = scale.where(np.isfinite(scale) & (scale > 0))
    scaled = wide.divide(scale, axis="columns")
    return scaled, scale


def rmspe(y_true, y_pred) -> float:
    """Root mean squared prediction error over finite paired rows."""
    yt = pd.Series(y_true, dtype="float64")
    yp = pd.Series(y_pred, dtype="float64")
    mask = np.isfinite(yt.to_numpy()) & np.isfinite(yp.to_numpy())
    if not mask.any():
        return float("nan")
    err = yt.to_numpy()[mask] - yp.to_numpy()[mask]
    return float(np.sqrt(np.mean(err ** 2)))


def post_pre_ratio(post_rmspe: float, pre_rmspe: float) -> float:
    """Return Abadie-style post/pre RMSPE ratio."""
    if not np.isfinite(post_rmspe) or not np.isfinite(pre_rmspe) or pre_rmspe == 0:
        return float("nan")
    return float(post_rmspe / pre_rmspe)
