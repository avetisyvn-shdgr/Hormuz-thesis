"""Lightweight inference helpers for counterfactual gaps.

This module does not claim full causal identification. It supplies the first
uncertainty layer for the free-data fallback: placebo-in-time windows that use
the same forecast machinery as the real post-treatment window.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .validation import Fold, require_chronological_index, resolve_cutoff


def post_treatment_fold(
    index: pd.DatetimeIndex,
    cutoff: pd.Timestamp | str | None = None,
) -> Fold:
    """Return one fold: train before cutoff, forecast on/after cutoff."""
    index = require_chronological_index(index)
    cut = pd.Timestamp(cutoff) if cutoff is not None else resolve_cutoff()
    train_idx = np.flatnonzero(index < cut)
    test_idx = np.flatnonzero(index >= cut)
    if len(train_idx) == 0 or len(test_idx) == 0:
        raise ValueError(
            f"Need rows before and after cutoff {cut.date()} to build a "
            "post-treatment fold."
        )
    return Fold(
        name="actual",
        train_idx=train_idx,
        test_idx=test_idx,
        train_start=index[train_idx[0]],
        train_end=index[train_idx[-1]],
        test_start=index[test_idx[0]],
        test_end=index[test_idx[-1]],
    )


def fixed_train_post_fold(
    index: pd.DatetimeIndex,
    train_cutoff: pd.Timestamp | str,
    post_start: pd.Timestamp | str,
    name: str = "fixed_train_post",
) -> Fold:
    """Return one fold with fixed pre-cutoff training and a chosen post window.

    This supports treatment-date robustness without moving disrupted days into
    training. ``train_cutoff`` is exclusive; ``post_start`` is inclusive.
    """
    index = require_chronological_index(index)
    train_cut = pd.Timestamp(train_cutoff)
    post = pd.Timestamp(post_start)
    if post < train_cut:
        raise ValueError(
            f"post_start {post.date()} must be on/after train_cutoff "
            f"{train_cut.date()}."
        )

    train_idx = np.flatnonzero(index < train_cut)
    test_idx = np.flatnonzero(index >= post)
    if len(train_idx) == 0 or len(test_idx) == 0:
        raise ValueError(
            f"Need rows before train_cutoff {train_cut.date()} and on/after "
            f"post_start {post.date()}."
        )
    train_end = index[train_idx[-1]]
    test_start = index[test_idx[0]]
    if train_end >= train_cut or test_start < post or test_start <= train_end:
        raise AssertionError(
            "Invalid fixed-train fold geometry; check cutoff/post dates."
        )
    return Fold(
        name=name,
        train_idx=train_idx,
        test_idx=test_idx,
        train_start=index[train_idx[0]],
        train_end=train_end,
        test_start=test_start,
        test_end=index[test_idx[-1]],
    )


def placebo_time_folds(
    index: pd.DatetimeIndex,
    cutoff: pd.Timestamp | str | None = None,
    horizon_days: int | None = None,
    initial_train_days: int = 365,
    step_days: int = 30,
) -> list[Fold]:
    """Build pre-treatment placebo windows with the same horizon length.

    Each placebo fold trains only before its placebo start and tests on a window
    that lies strictly before the real treatment cutoff.
    """
    if initial_train_days <= 0:
        raise ValueError("initial_train_days must be > 0.")
    if step_days <= 0:
        raise ValueError("step_days must be > 0.")

    index = require_chronological_index(index)
    cut = pd.Timestamp(cutoff) if cutoff is not None else resolve_cutoff()
    usable = index[index < cut]
    if len(usable) == 0:
        raise ValueError(f"No pre-treatment rows before cutoff {cut.date()}.")

    if horizon_days is None:
        horizon_days = len(index[index >= cut])
    if horizon_days <= 0:
        raise ValueError("horizon_days must be > 0.")

    t0 = usable.min()
    tN = usable.max()
    origin = t0 + pd.Timedelta(days=initial_train_days)
    folds: list[Fold] = []
    while True:
        test_start = origin
        test_end_excl = origin + pd.Timedelta(days=horizon_days)
        if test_end_excl > cut or test_end_excl - pd.Timedelta(days=1) > tN:
            break

        train_mask = (index >= t0) & (index < test_start)
        test_mask = (index >= test_start) & (index < test_end_excl)
        train_pos = np.flatnonzero(train_mask)
        test_pos = np.flatnonzero(test_mask)

        if len(train_pos) and len(test_pos):
            folds.append(Fold(
                name=f"placebo_{len(folds) + 1:02d}",
                train_idx=train_pos,
                test_idx=test_pos,
                train_start=index[train_pos[0]],
                train_end=index[train_pos[-1]],
                test_start=index[test_pos[0]],
                test_end=index[test_pos[-1]],
            ))
        origin = origin + pd.Timedelta(days=step_days)

    if not folds:
        raise ValueError(
            "No placebo folds fit before the treatment cutoff. Shorten the "
            "horizon, reduce initial_train_days, or lengthen the pre-period."
        )
    return folds


def non_overlapping_fold_count(folds: list[Fold]) -> int:
    """Greedy count of non-overlapping placebo test windows.

    The placebo set may deliberately use overlapping windows to increase
    temporal coverage, but this helper reports the rough number of independent
    horizon-length windows available in the same pre-period.
    """
    count = 0
    last_end: pd.Timestamp | None = None
    for fold in sorted(folds, key=lambda f: f.test_start):
        if last_end is None or fold.test_start > last_end:
            count += 1
            last_end = fold.test_end
    return count


def select_non_overlapping_folds(folds: list[Fold]) -> list[Fold]:
    """Greedily retain disjoint test windows in chronological order."""
    selected: list[Fold] = []
    last_end: pd.Timestamp | None = None
    for fold in sorted(folds, key=lambda item: item.test_start):
        if last_end is None or fold.test_start > last_end:
            selected.append(fold)
            last_end = fold.test_end
    return selected


def finite_sample_conformal_radius(
    calibration_errors,
    alpha: float = 0.1,
) -> dict[str, float | int | bool]:
    """Finite-sample split-conformal radius from absolute block errors.

    The order statistic is ``ceil((n + 1) * (1 - alpha))``.  If that rank is
    larger than the number of independent calibration blocks, the requested
    coverage cannot be supported and the radius is infinite.  Returning an
    honest unbounded interval is preferable to silently clipping the rank.
    """
    if not 0 < alpha < 1:
        raise ValueError(f"alpha must be between 0 and 1, got {alpha}.")
    errors = pd.Series(calibration_errors, dtype="float64").dropna().to_numpy()
    if len(errors) == 0:
        raise ValueError("Need at least one finite calibration error.")
    scores = np.sort(np.abs(errors))
    rank = int(np.ceil((len(scores) + 1) * (1 - alpha)))
    supported = rank <= len(scores)
    radius = float(scores[rank - 1]) if supported else float("inf")
    return {
        "radius": radius,
        "n_calibration_blocks": int(len(scores)),
        "order_statistic_rank": rank,
        "finite_interval_supported": supported,
        "maximum_finite_coverage": float(len(scores) / (len(scores) + 1)),
    }


def conformal_effect_interval(
    point_effect: float,
    calibration_errors,
    alpha: float = 0.1,
) -> dict[str, float | int | bool]:
    """Symmetric block-conformal interval around an estimated cumulative effect."""
    result = finite_sample_conformal_radius(calibration_errors, alpha=alpha)
    radius = float(result["radius"])
    return {
        "point_effect": float(point_effect),
        "interval_lower": float(point_effect - radius),
        "interval_upper": float(point_effect + radius),
        "nominal_coverage": float(1 - alpha),
        **result,
    }


def separation_ratio(actual: float, reference: float) -> float:
    """Return actual/reference, preserving undefined cases as NaN."""
    if not np.isfinite(actual) or not np.isfinite(reference) or reference == 0:
        return float("nan")
    return float(actual / reference)


def residual_quantiles(residuals, alpha: float = 0.05) -> tuple[float, float]:
    """Two-sided empirical residual quantiles for pointwise bands."""
    if not 0 < alpha < 1:
        raise ValueError(f"alpha must be between 0 and 1, got {alpha}.")
    vals = pd.Series(residuals, dtype="float64").dropna().to_numpy()
    if len(vals) == 0:
        raise ValueError("Need at least one finite residual.")
    return (
        float(np.quantile(vals, alpha / 2)),
        float(np.quantile(vals, 1 - alpha / 2)),
    )


def block_residual_sums(
    residuals,
    horizon: int,
    block_length: int = 7,
    n_draws: int = 5000,
    seed: int = 20260612,
) -> np.ndarray:
    """Bootstrap sums of residuals over a forecast horizon.

    Residuals are sampled in contiguous blocks to preserve short-run serial
    dependence. The result is a distribution for aggregate forecast error over
    the horizon.
    """
    if horizon <= 0:
        raise ValueError("horizon must be > 0.")
    if block_length <= 0:
        raise ValueError("block_length must be > 0.")
    if n_draws <= 0:
        raise ValueError("n_draws must be > 0.")

    vals = pd.Series(residuals, dtype="float64").dropna().to_numpy()
    if len(vals) == 0:
        raise ValueError("Need at least one finite residual.")
    rng = np.random.default_rng(seed)
    starts = np.arange(len(vals))
    out = np.empty(n_draws, dtype="float64")
    for i in range(n_draws):
        pieces = []
        while sum(len(p) for p in pieces) < horizon:
            start = int(rng.choice(starts))
            idx = (start + np.arange(block_length)) % len(vals)
            pieces.append(vals[idx])
        sample = np.concatenate(pieces)[:horizon]
        out[i] = float(sample.sum())
    return out


def circular_block_bootstrap_loss_interval(
    point_loss: float,
    residuals,
    *,
    horizon: int,
    block_length: int = 14,
    n_draws: int = 10000,
    seed: int = 20260612,
    alpha: float = 0.05,
) -> dict[str, float | int | bool]:
    """Circular-block bootstrap interval from an ordered OOF residual path."""
    if not 0 < alpha < 1:
        raise ValueError("alpha must lie strictly between zero and one.")
    values = pd.Series(residuals, dtype="float64").dropna().to_numpy()
    if len(values) < block_length:
        raise ValueError("Residual path must contain at least one full block.")
    mean_residual = float(values.mean())
    sums = block_residual_sums(
        values - mean_residual,
        horizon=horizon,
        block_length=block_length,
        n_draws=n_draws,
        seed=seed,
    )
    lower_error, upper_error = np.quantile(sums, [alpha / 2, 1 - alpha / 2])
    lower = float(point_loss + lower_error)
    upper = float(point_loss + upper_error)
    return {
        "point_loss": float(point_loss),
        "interval_lower": lower,
        "interval_upper": upper,
        "interval_width": float(upper - lower),
        "excludes_zero": bool(lower > 0 or upper < 0),
        "n_residuals": int(len(values)),
        "block_length": int(block_length),
        "n_bootstrap_draws": int(n_draws),
        "pre_period_mean_residual_centered_out": mean_residual,
    }


def overlapping_placebo_quantile_band(
    point_loss: float,
    horizon_cumulative_errors,
    lower_quantile: float = 0.025,
    upper_quantile: float = 0.975,
) -> dict[str, float]:
    """Descriptive loss band from overlapping full-horizon placebo errors.

    ``horizon_cumulative_errors`` are realised cumulative forecast errors,
    each summed over a full horizon-length window in the *pre-treatment* period
    (e.g. the placebo-in-time windows). Unlike block-bootstrapping short-fold
    residuals, this uses errors that already include long-horizon recursive
    compounding, so it does not understate uncertainty for a long counterfactual.

    The windows may overlap and therefore are not independent calibration units.
    The returned empirical quantile band has *no nominal coverage guarantee* and
    must not be labeled a confidence, prediction, or conformal interval.

    Errors are mean-centered (any pre-period forecast bias is removed and
    reported separately), then the requested empirical quantiles are added to
    ``point_loss``. This preserves asymmetry/skew without assuming normality.
    """
    if not 0 <= lower_quantile < upper_quantile <= 1:
        raise ValueError(
            "quantiles must satisfy 0 <= lower < upper <= 1, got "
            f"{lower_quantile}, {upper_quantile}."
        )
    err = pd.Series(horizon_cumulative_errors, dtype="float64").dropna().to_numpy()
    if len(err) == 0:
        raise ValueError("Need at least one finite horizon cumulative error.")

    mean_err = float(err.mean())
    centered = err - mean_err
    q_lo, q_hi = np.quantile(centered, [lower_quantile, upper_quantile])
    lower = float(point_loss + q_lo)
    upper = float(point_loss + q_hi)
    return {
        "point_loss": float(point_loss),
        "band_lower": lower,
        "band_upper": upper,
        "band_width": float(upper - lower),
        "band_excludes_zero_descriptively": bool(lower > 0 or upper < 0),
        "lower_quantile": float(lower_quantile),
        "upper_quantile": float(upper_quantile),
        "nominal_coverage_supported": False,
        "n_horizon_windows": int(len(err)),
        "pre_period_mean_error_centered_out": mean_err,
        "error_sd": float(err.std(ddof=1)) if len(err) > 1 else float("nan"),
    }


def counterfactual_effect(y_true, y_pred) -> dict[str, float]:
    """Summarize observed-minus-counterfactual and loss gaps."""
    yt = pd.Series(y_true, dtype="float64")
    yp = pd.Series(y_pred, dtype="float64")
    if len(yt) != len(yp):
        raise ValueError("y_true and y_pred must have the same length.")
    mask = np.isfinite(yt.to_numpy()) & np.isfinite(yp.to_numpy())
    if not mask.any():
        raise ValueError("No finite paired observations for effect summary.")

    obs = yt.to_numpy()[mask]
    pred = yp.to_numpy()[mask]
    gap = obs - pred
    loss = pred - obs
    return {
        "n_days": int(mask.sum()),
        "observed_sum": float(obs.sum()),
        "counterfactual_sum": float(pred.sum()),
        "cumulative_gap_observed_minus_predicted": float(gap.sum()),
        "cumulative_throughput_loss": float(loss.sum()),
        "mean_daily_throughput_loss": float(loss.mean()),
    }


def empirical_p_value(
    actual: float,
    placebo_values,
    alternative: str = "greater",
) -> float:
    """Finite-sample placebo p-value with +1 correction."""
    vals = pd.Series(placebo_values, dtype="float64").dropna().to_numpy()
    if len(vals) == 0:
        raise ValueError("Need at least one finite placebo value.")
    if alternative == "greater":
        extreme = np.sum(vals >= actual)
    elif alternative == "less":
        extreme = np.sum(vals <= actual)
    elif alternative == "two-sided":
        extreme = np.sum(np.abs(vals) >= abs(actual))
    else:
        raise ValueError(
            "alternative must be 'greater', 'less', or 'two-sided', "
            f"got {alternative!r}."
        )
    return float((extreme + 1) / (len(vals) + 1))


def romano_wolf_stepdown(
    observed,
    resampled,
    *,
    alternative: str = "greater",
    studentize: bool = True,
) -> pd.DataFrame:
    """Dependence-aware Romano-Wolf max-statistic step-down p-values.

    Rows of ``resampled`` must be aligned joint null draws across hypotheses.
    This requirement is substantive: independently shuffled placebo columns do
    not preserve dependence and must not be passed to this function.  The +1
    correction keeps finite-resample p-values away from zero.
    """
    obs = pd.Series(observed, dtype="float64")
    draws = pd.DataFrame(resampled, columns=obs.index, dtype="float64")
    if obs.empty:
        raise ValueError("Need at least one observed statistic.")
    if draws.empty:
        raise ValueError("Need at least one joint resampling draw.")
    if obs.isna().any() or not np.isfinite(obs.to_numpy()).all():
        raise ValueError("Observed statistics must all be finite.")
    if draws.isna().any().any() or not np.isfinite(draws.to_numpy()).all():
        raise ValueError("Joint resampling matrix must be finite and complete.")
    if alternative not in {"greater", "less", "two-sided"}:
        raise ValueError("alternative must be 'greater', 'less', or 'two-sided'.")

    if alternative == "less":
        obs = -obs
        draws = -draws

    if studentize:
        scale = draws.std(axis=0, ddof=1)
        invalid = ~np.isfinite(scale) | scale.le(0)
        if invalid.any():
            bad = list(scale.index[invalid])
            raise ValueError(f"Cannot studentize zero-variance hypotheses: {bad}")
        center = draws.mean(axis=0)
        test_obs = (obs - center) / scale
        test_draws = (draws - center) / scale
        if alternative == "two-sided":
            test_obs = test_obs.abs()
            test_draws = test_draws.abs()
    else:
        test_obs = obs.abs() if alternative == "two-sided" else obs
        test_draws = draws.abs() if alternative == "two-sided" else draws

    order = list(test_obs.sort_values(ascending=False, kind="stable").index)
    raw = {
        name: (1.0 + float((test_draws[name] >= test_obs[name]).sum()))
        / (len(test_draws) + 1.0)
        for name in order
    }
    adjusted: dict[object, float] = {}
    running = 0.0
    for position, name in enumerate(order):
        remaining = order[position:]
        maxima = test_draws[remaining].max(axis=1)
        step_p = (1.0 + float((maxima >= test_obs[name]).sum())) / (
            len(test_draws) + 1.0
        )
        running = max(running, step_p)
        adjusted[name] = min(running, 1.0)

    return pd.DataFrame({
        "hypothesis": order,
        "observed_statistic": [float(observed[name]) for name in order],
        "studentized_statistic": [float(test_obs[name]) for name in order],
        "raw_resampling_p_value": [raw[name] for name in order],
        "romano_wolf_p_value": [adjusted[name] for name in order],
        "stepdown_rank": range(1, len(order) + 1),
        "family_size": len(order),
        "n_joint_resamples": len(test_draws),
    })
