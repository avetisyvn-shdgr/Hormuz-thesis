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

from .validation import require_chronological_index


@dataclass(frozen=True)
class BSTSResult:
    dates: pd.DatetimeIndex
    predictive_draws: np.ndarray
    beta_draws: np.ndarray
    observation_variance_draws: np.ndarray
    level_variance_draws: np.ndarray
    training_dates: pd.DatetimeIndex | None = None
    training_predictive_draws: np.ndarray | None = None

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
    observation_prior_scale_multiplier: float = 0.5,
    level_prior_scale_multiplier: float = 0.5,
    variance_prior_shape: float = 2.5,
    retain_training_predictive_draws: bool = False,
) -> BSTSResult:
    """Fit the local-level BSTS and sample posterior predictive paths.

    Training must be a complete, finite daily calendar. Missing dates or values
    are rejected rather than dropped or silently imputed because compressing
    them would change the meaning of each local-level transition and weekday
    seasonal term. Forecast dates must be the immediately following complete
    daily horizon.
    """
    if not isinstance(y.index, pd.DatetimeIndex):
        raise TypeError("y must use a DatetimeIndex.")
    y = y.astype("float64")
    train_index = require_chronological_index(y.index, name="BSTS training index")
    forecast_index = require_chronological_index(
        forecast_index,
        name="BSTS forecast index",
    )
    if len(y) < 30:
        raise ValueError("BSTS requires at least 30 finite training observations.")
    if not train_index.is_unique or not forecast_index.is_unique:
        raise ValueError("BSTS training and forecast dates must be unique.")
    expected_train = pd.date_range(
        train_index.min(),
        train_index.max(),
        freq="D",
        name=train_index.name,
    )
    if not train_index.equals(expected_train):
        raise ValueError("BSTS training index must be a complete daily calendar.")
    if not np.isfinite(y.to_numpy()).all():
        raise ValueError(
            "BSTS training values must be finite on every calendar day; "
            "impute explicitly upstream or choose a missing-aware model."
        )
    if len(forecast_index) == 0:
        raise ValueError("forecast_index must contain at least one date.")
    expected_forecast = pd.date_range(
        train_index.max() + pd.Timedelta(days=1),
        periods=len(forecast_index),
        freq="D",
        name=forecast_index.name,
    )
    if not forecast_index.equals(expected_forecast):
        raise ValueError(
            "BSTS forecast index must be the complete daily horizon immediately "
            "after the training series."
        )
    if n_draws <= 0 or burn < 0 or thin <= 0:
        raise ValueError("n_draws and thin must be positive; burn cannot be negative.")
    if observation_prior_scale_multiplier <= 0 or level_prior_scale_multiplier <= 0:
        raise ValueError("Variance-prior scale multipliers must be positive.")
    if variance_prior_shape <= 1:
        raise ValueError("variance_prior_shape must exceed one.")

    values = y.to_numpy()
    x = _weekly_design(y.index)
    x_future = _weekly_design(forecast_index)
    n, p = x.shape
    rng = np.random.default_rng(seed)
    ppc_rng = np.random.default_rng(seed + 10_000_019)

    beta = np.linalg.lstsq(np.column_stack([np.ones(n), x]), values, rcond=None)[0][1:]
    level = np.full(n, float(np.mean(values)))
    observation_variance = max(
        float(np.var(values - level - _linear_component(x, beta))), 1.0
    )
    level_variance = max(observation_variance * 0.05, 1e-3)
    prior_variance = max(float(np.var(values)) * 100.0, 100.0)
    prior_precision = np.eye(p) / prior_variance
    a0 = float(variance_prior_shape)
    empirical_variance = max(float(np.var(values)), 1e-3)
    observation_b0 = empirical_variance * observation_prior_scale_multiplier
    level_b0 = empirical_variance * level_prior_scale_multiplier

    prediction_draws = np.empty((n_draws, len(forecast_index)))
    beta_draws = np.empty((n_draws, p))
    obs_var_draws = np.empty(n_draws)
    level_var_draws = np.empty(n_draws)
    training_draws = (
        np.empty((n_draws, n)) if retain_training_predictive_draws else None
    )
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
        obs_scale = observation_b0 + float(np.sum(residual**2)) / 2.0
        observation_variance = 1.0 / rng.gamma(obs_shape, 1.0 / obs_scale)

        differences = np.diff(level)
        level_shape = a0 + (n - 1) / 2.0
        level_scale = level_b0 + float(np.sum(differences**2)) / 2.0
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
        if training_draws is not None:
            fitted = level + _linear_component(x, beta)
            training_draws[kept] = np.maximum(
                fitted + ppc_rng.normal(0.0, np.sqrt(observation_variance), size=n),
                0.0,
            )
        kept += 1

    return BSTSResult(
        dates=forecast_index,
        predictive_draws=prediction_draws,
        beta_draws=beta_draws,
        observation_variance_draws=obs_var_draws,
        level_variance_draws=level_var_draws,
        training_dates=y.index if training_draws is not None else None,
        training_predictive_draws=training_draws,
    )


def posterior_predictive_check(
    result: BSTSResult,
    observed: pd.Series,
) -> tuple[pd.DataFrame, dict[str, float]]:
    """Summarize in-sample posterior replications for model-adequacy checking."""
    draws = result.training_predictive_draws
    if draws is None or result.training_dates is None:
        raise ValueError("Fit must retain training predictive draws for a PPC.")
    y = observed.astype("float64").reindex(result.training_dates)
    if y.isna().any() or draws.shape[1] != len(y):
        raise ValueError("Observed training data must align with retained PPC draws.")
    values = y.to_numpy()
    median = np.median(draws, axis=0)
    lower = np.quantile(draws, 0.025, axis=0)
    upper = np.quantile(draws, 0.975, axis=0)

    def p_value(stat_draws: np.ndarray, observed_stat: float) -> float:
        upper_tail = float(np.mean(stat_draws >= observed_stat))
        lower_tail = float(np.mean(stat_draws <= observed_stat))
        return min(1.0, 2.0 * min(upper_tail, lower_tail))

    frame = pd.DataFrame({
        "date": result.training_dates,
        "y_true": values,
        "posterior_median": median,
        "lower_95": lower,
        "upper_95": upper,
    })
    summary = {
        "n_pre_days": int(len(values)),
        "pointwise_95_coverage": float(np.mean((values >= lower) & (values <= upper))),
        "posterior_median_rmse": float(np.sqrt(np.mean((values - median) ** 2))),
        "bayesian_p_mean": p_value(draws.mean(axis=1), float(values.mean())),
        "bayesian_p_sd": p_value(draws.std(axis=1), float(values.std())),
        "bayesian_p_max": p_value(draws.max(axis=1), float(values.max())),
    }
    return frame, summary


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
