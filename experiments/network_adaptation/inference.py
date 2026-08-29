"""Dependence-preserving inference utilities for network-adaptation residuals."""
from __future__ import annotations

import numpy as np
import pandas as pd


def synchronized_circular_mbb(
    residuals: pd.DataFrame,
    *,
    horizon: int,
    block_length: int,
    n_draws: int,
    seed: int,
) -> pd.DataFrame:
    """Bootstrap horizon means using common circular blocks across columns.

    Each row of ``residuals`` is a synchronized historical date and each column
    is a model/series forecast residual. Sampling identical time indices for all
    columns preserves contemporaneous cross-corridor dependence; contiguous
    blocks preserve short-run serial dependence.
    """
    frame = pd.DataFrame(residuals, dtype="float64")
    if frame.empty or frame.shape[1] == 0:
        raise ValueError("residual matrix must be non-empty.")
    if frame.isna().any().any() or not np.isfinite(frame.to_numpy()).all():
        raise ValueError("residual matrix must be finite and complete.")
    if horizon <= 0 or block_length <= 0 or n_draws <= 0:
        raise ValueError("horizon, block_length, and n_draws must be positive.")
    if block_length > len(frame):
        raise ValueError("block_length cannot exceed the historical residual length.")

    values = frame.to_numpy(dtype="float64")
    rng = np.random.default_rng(seed)
    blocks_per_draw = int(np.ceil(horizon / block_length))
    starts = rng.integers(0, len(frame), size=(n_draws, blocks_per_draw))
    offsets = np.arange(block_length)
    indices = (starts[..., None] + offsets) % len(frame)
    indices = indices.reshape(n_draws, -1)[:, :horizon]
    draws = values[indices].mean(axis=1)
    return pd.DataFrame(draws, columns=frame.columns)


def scale_columns(frame: pd.DataFrame, denominators: pd.Series) -> pd.DataFrame:
    """Scale each residual-mean column by its positive pre-event mean."""
    data = pd.DataFrame(frame, dtype="float64")
    scale = pd.Series(denominators, dtype="float64").reindex(data.columns)
    if scale.isna().any() or not np.isfinite(scale.to_numpy()).all() or scale.le(0).any():
        raise ValueError("all series require a finite, positive pre-event mean.")
    return data.divide(scale, axis="columns")


def global_mean_test(
    observed: pd.Series,
    joint_draws: pd.DataFrame,
) -> dict[str, float | int]:
    """One-sided global mean test over an explicitly fixed hypothesis family."""
    obs = pd.Series(observed, dtype="float64")
    draws = pd.DataFrame(joint_draws, dtype="float64").reindex(columns=obs.index)
    if obs.empty or draws.empty or draws.isna().any().any():
        raise ValueError("global test requires a complete observed vector and joint draws.")
    observed_global = float(obs.mean())
    draw_global = draws.mean(axis=1)
    p_value = (1.0 + float((draw_global >= observed_global).sum())) / (len(draw_global) + 1.0)
    return {
        "observed_global_statistic": observed_global,
        "historical_reference_mean": float(draw_global.mean()),
        "historical_reference_sd": float(draw_global.std(ddof=1)),
        "reference_q025": float(draw_global.quantile(0.025)),
        "reference_q975": float(draw_global.quantile(0.975)),
        "one_sided_bootstrap_p_value": p_value,
        "n_joint_resamples": int(len(draw_global)),
    }
