"""Bayesian structural time-series counterfactuals.

The implementation is deliberately small and auditable: a Gaussian local-level
state-space model with deterministic weekly seasonality, estimated by Gibbs
sampling with forward-filtering backward-sampling (FFBS).  It produces joint
posterior predictive paths, so cumulative shortfall intervals retain temporal
dependence instead of summing independent pointwise intervals.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class BSTSResult:
    dates: pd.DatetimeIndex
    predictive_draws: np.ndarray
    beta_draws: np.ndarray
    observation_variance_draws: np.ndarray
    level_variance_draws: np.ndarray

    def forecast_frame(self) -> pd.DataFrame:
        return pd.DataFrame({
            "date": self.dates,
            "y_pred": np.median(self.predictive_draws, axis=0),
            "lower_95": np.quantile(self.predictive_draws, 0.025, axis=0),
            "upper_95": np.quantile(self.predictive_draws, 0.975, axis=0),
        })


def _weekly_design(index: pd.DatetimeIndex) -> np.ndarray:
    day = np.asarray(index.dayofweek, dtype="float64")
    angle = 2.0 * np.pi * day / 7.0
    return np.column_stack([np.sin(angle), np.cos(angle)])


def _linear_component(x: np.ndarray, beta: np.ndarray) -> np.ndarray:
    """Rowwise dot product without platform-specific BLAS warning noise."""
    return np.sum(x * beta[None, :], axis=1)


def _ffbs_local_level(
    z: np.ndarray,
    observation_variance: float,
    level_variance: float,
    rng: np.random.Generator,
) -> np.ndarray:
    """Sample a random-walk level conditional on observations and variances."""
    n = len(z)
    predicted_mean = np.empty(n)
    predicted_var = np.empty(n)
    filtered_mean = np.empty(n)
    filtered_var = np.empty(n)

    mean = float(z[0])
    variance = max(observation_variance * 10.0, 1.0)
    for t in range(n):
        if t:
            variance += level_variance
        predicted_mean[t] = mean
        predicted_var[t] = variance
        gain = variance / (variance + observation_variance)
        mean = mean + gain * (z[t] - mean)
        variance = max((1.0 - gain) * variance, 1e-10)
        filtered_mean[t] = mean
        filtered_var[t] = variance

    level = np.empty(n)
    level[-1] = rng.normal(filtered_mean[-1], np.sqrt(filtered_var[-1]))
    for t in range(n - 2, -1, -1):
        denom = filtered_var[t] + level_variance
        gain = filtered_var[t] / denom
        mean = filtered_mean[t] + gain * (level[t + 1] - filtered_mean[t])
        variance = max(filtered_var[t] - gain * filtered_var[t], 1e-10)
        level[t] = rng.normal(mean, np.sqrt(variance))
    return level


def fit_bsts_forecast(
    y: pd.Series,
    forecast_index: pd.DatetimeIndex,
    *,
    n_draws: int = 1000,
    burn: int = 500,
    thin: int = 2,
    seed: int = 20260612,
) -> BSTSResult:
    """Fit the local-level BSTS and sample posterior predictive paths.

    Missing training values are rejected rather than silently imputed.  The
    caller is responsible for passing the frozen, aligned pre-treatment series.
    """
    y = y.astype("float64").dropna().sort_index()
    forecast_index = pd.DatetimeIndex(forecast_index).sort_values()
    if len(y) < 30:
        raise ValueError("BSTS requires at least 30 finite training observations.")
    if len(forecast_index) == 0:
        raise ValueError("forecast_index must contain at least one date.")
    if not isinstance(y.index, pd.DatetimeIndex):
        raise TypeError("y must use a DatetimeIndex.")
    if forecast_index.min() <= y.index.max():
        raise ValueError("All forecast dates must be after the training series.")
    if n_draws <= 0 or burn < 0 or thin <= 0:
        raise ValueError("n_draws and thin must be positive; burn cannot be negative.")

    values = y.to_numpy()
    x = _weekly_design(y.index)
    x_future = _weekly_design(forecast_index)
    n, p = x.shape
    rng = np.random.default_rng(seed)

    beta = np.linalg.lstsq(np.column_stack([np.ones(n), x]), values, rcond=None)[0][1:]
    level = np.full(n, float(np.mean(values)))
    observation_variance = max(
        float(np.var(values - level - _linear_component(x, beta))), 1.0
    )
    level_variance = max(observation_variance * 0.05, 1e-3)
    prior_variance = max(float(np.var(values)) * 100.0, 100.0)
    prior_precision = np.eye(p) / prior_variance
    a0 = 2.5
    b0 = max(float(np.var(values)) * 0.5, 1e-3)

    prediction_draws = np.empty((n_draws, len(forecast_index)))
    beta_draws = np.empty((n_draws, p))
    obs_var_draws = np.empty(n_draws)
    level_var_draws = np.empty(n_draws)
    total_iterations = burn + n_draws * thin
    kept = 0
    for iteration in range(total_iterations):
        level = _ffbs_local_level(
            values - _linear_component(x, beta),
            observation_variance,
            level_variance,
            rng,
        )

        precision = np.einsum("ni,nj->ij", x, x) / observation_variance + prior_precision
        covariance = np.linalg.inv(precision)
        score = np.einsum("ni,n->i", x, values - level) / observation_variance
        mean = np.sum(covariance * score[None, :], axis=1)
        beta = rng.multivariate_normal(mean, covariance)

        residual = values - level - _linear_component(x, beta)
        obs_shape = a0 + n / 2.0
        obs_scale = b0 + float(np.sum(residual**2)) / 2.0
        observation_variance = 1.0 / rng.gamma(obs_shape, 1.0 / obs_scale)

        differences = np.diff(level)
        level_shape = a0 + (n - 1) / 2.0
        level_scale = b0 + float(np.sum(differences**2)) / 2.0
        level_variance = 1.0 / rng.gamma(level_shape, 1.0 / level_scale)

        if iteration < burn or (iteration - burn) % thin:
            continue
        future_level = float(level[-1])
        path = np.empty(len(forecast_index))
        for h in range(len(forecast_index)):
            future_level += rng.normal(0.0, np.sqrt(level_variance))
            path[h] = (
                future_level
                + float(np.sum(x_future[h] * beta))
                + rng.normal(0.0, np.sqrt(observation_variance))
            )
        prediction_draws[kept] = np.maximum(path, 0.0)
        beta_draws[kept] = beta
        obs_var_draws[kept] = observation_variance
        level_var_draws[kept] = level_variance
        kept += 1

    return BSTSResult(
        dates=forecast_index,
        predictive_draws=prediction_draws,
        beta_draws=beta_draws,
        observation_variance_draws=obs_var_draws,
        level_variance_draws=level_var_draws,
    )


def posterior_shortfall(
    predictive_draws: np.ndarray,
    observed,
    alpha: float = 0.05,
) -> dict[str, float]:
    """Summarize the joint posterior for cumulative counterfactual shortfall."""
    if not 0 < alpha < 1:
        raise ValueError("alpha must lie strictly between zero and one.")
    observed_values = pd.Series(observed, dtype="float64").to_numpy()
    draws = np.asarray(predictive_draws, dtype="float64")
    if draws.ndim != 2 or draws.shape[1] != len(observed_values):
        raise ValueError("predictive_draws must have one column per observed day.")
    if not np.isfinite(observed_values).all():
        raise ValueError("observed must contain only finite values.")
    losses = np.sum(draws - observed_values[None, :], axis=1)
    lower, upper = np.quantile(losses, [alpha / 2.0, 1.0 - alpha / 2.0])
    return {
        "posterior_median_shortfall": float(np.median(losses)),
        "posterior_mean_shortfall": float(np.mean(losses)),
        "lower_95": float(lower),
        "upper_95": float(upper),
        "posterior_probability_shortfall_positive": float(np.mean(losses > 0)),
        "n_posterior_draws": int(len(losses)),
    }
