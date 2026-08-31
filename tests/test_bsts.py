import numpy as np
import pandas as pd
import pytest

from hormuz_throughput.bsts import (
    fit_bsts_forecast,
    posterior_predictive_check,
    posterior_shortfall,
)


def test_bsts_is_seed_reproducible_and_has_joint_paths():
    index = pd.date_range("2024-01-01", periods=90, freq="D")
    y = pd.Series(20 + 2 * np.sin(2 * np.pi * index.dayofweek / 7), index=index)
    future = pd.date_range(index[-1] + pd.Timedelta(days=1), periods=14, freq="D")
    first = fit_bsts_forecast(y, future, n_draws=20, burn=10, thin=1, seed=7)
    second = fit_bsts_forecast(y, future, n_draws=20, burn=10, thin=1, seed=7)
    assert first.predictive_draws.shape == (20, 14)
    np.testing.assert_allclose(first.predictive_draws, second.predictive_draws)
    assert (first.predictive_draws >= 0).all()


def test_posterior_shortfall_validates_shape():
    draws = np.array([[3.0, 4.0], [4.0, 5.0]])
    result = posterior_shortfall(draws, [1.0, 2.0])
    assert result["posterior_median_shortfall"] == pytest.approx(5.0)
    assert result["posterior_probability_shortfall_positive"] == 1.0
    with pytest.raises(ValueError):
        posterior_shortfall(draws, [1.0])


def test_bsts_retains_training_draws_for_posterior_predictive_check():
    index = pd.date_range("2024-01-01", periods=60, freq="D")
    y = pd.Series(20 + np.sin(2 * np.pi * index.dayofweek / 7), index=index)
    future = pd.date_range(index[-1] + pd.Timedelta(days=1), periods=7, freq="D")
    result = fit_bsts_forecast(
        y, future, n_draws=20, burn=10, thin=1, seed=9,
        retain_training_predictive_draws=True,
    )
    frame, summary = posterior_predictive_check(result, y)
    assert result.training_predictive_draws.shape == (20, 60)
    assert len(frame) == 60
    assert 0 <= summary["pointwise_95_coverage"] <= 1


def test_bsts_rejects_invalid_variance_prior_scales():
    index = pd.date_range("2024-01-01", periods=60, freq="D")
    y = pd.Series(np.arange(60.0), index=index)
    future = pd.date_range(index[-1] + pd.Timedelta(days=1), periods=7, freq="D")
    with pytest.raises(ValueError, match="scale multipliers"):
        fit_bsts_forecast(
            y, future, n_draws=5, burn=2,
            observation_prior_scale_multiplier=0,
        )


def test_bsts_rejects_missing_days_and_values_without_compressing_time():
    index = pd.date_range("2024-01-01", periods=60, freq="D")
    y = pd.Series(np.arange(60.0), index=index)
    future = pd.date_range(index[-1] + pd.Timedelta(days=1), periods=7, freq="D")

    with pytest.raises(ValueError, match="complete daily calendar"):
        fit_bsts_forecast(
            y.drop(index[index.size // 2]),
            future,
            n_draws=5,
            burn=2,
        )

    missing_value = y.copy()
    missing_value.iloc[index.size // 2] = np.nan
    with pytest.raises(ValueError, match="finite on every calendar day"):
        fit_bsts_forecast(
            missing_value,
            future,
            n_draws=5,
            burn=2,
        )
