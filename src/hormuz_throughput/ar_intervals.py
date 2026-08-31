"""Raw, horizon-aware predictive interval for the AR-only baseline.

The transparent baselines emit point forecasts only, so the TSFM admission test
(``tsfm.admission_test``) could confirm a foundation model beats AR-only on MASE
but could NOT assess the calibration leg — there was no comparable AR interval.
This module supplies that missing interval so the gate can be fully applied.

Design (matches the verdict's request: "raw, not conformal"):
  * RAW: the band comes straight from the AR model's own rolling-origin
    residuals — no conformal/quantile-regression recalibration layer (that
    machinery lives in ``inference.py`` and is intentionally not reused here).
  * HORIZON-AWARE: the residual spread is estimated SEPARATELY for each
    step-ahead s = 1..H, so the band widens with the forecast horizon instead of
    assuming one global spread. The half-width at step s is ``z(q) * sigma_s``,
    where ``sigma_s`` is the standard deviation of the realised step-s residuals
    and ``z`` is the standard-normal quantile.
  * LEAKAGE-SAFE: ``sigma_s`` for an evaluation fold is estimated only from folds
    whose forecast origin is STRICTLY EARLIER (expanding calibration), so the
    interval uses only information available at that fold's origin — the same
    discipline under which the foundation models only see pre-origin context.
    Early folds without enough prior calibration folds are left undefined and
    excluded from scoring (never silently filled), exactly as the harness drops
    NaN intervals.

Limitation (state it, do not hide it): with only a few dozen pre-treatment folds,
each ``sigma_s`` is estimated from O(tens) of residuals, and the band assumes a
symmetric spread around the point forecast. It is an honest raw estimate, not a
guaranteed-coverage interval; the calibration comparison is reported as such.
"""
from __future__ import annotations

from math import erf, sqrt

import numpy as np
import pandas as pd


def _normal_ppf(q: float) -> float:
    """Standard-normal quantile via bisection on erf (no scipy dependency)."""
    if not 0.0 < q < 1.0:
        raise ValueError(f"q must be in (0, 1), got {q}.")
    lo, hi = -8.0, 8.0
    for _ in range(64):
        mid = 0.5 * (lo + hi)
        cdf = 0.5 * (1.0 + erf(mid / sqrt(2.0)))
        if cdf < q:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def _with_step_and_origin(forecasts: pd.DataFrame) -> pd.DataFrame:
    """Add a 1-based step-ahead index and fold origin date to AR fold forecasts."""
    df = forecasts.copy()
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values(["fold", "date"])
    df["step"] = df.groupby("fold").cumcount() + 1
    df["residual"] = df["y_true"] - df["y_pred"]
    origins = df.groupby("fold")["date"].transform("min")
    df["origin"] = origins
    return df


def evaluate_ar_horizon_interval(
    forecasts: pd.DataFrame,
    lower_q: float = 0.025,
    upper_q: float = 0.975,
    min_calib_folds: int = 15,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Score a raw horizon-aware AR interval over the rolling-origin folds.

    Parameters
    ----------
    forecasts:
        Per-day AR forecasts for ONE model and ONE target, with columns
        ``date, fold, y_true, y_pred`` (e.g. the ``ar_lag1_7`` rows of
        ``baseline_forecasts.csv``).
    lower_q, upper_q:
        Central-interval bounds (default 95%).
    min_calib_folds:
        Minimum number of strictly-earlier folds required to estimate the
        per-step spread; folds with fewer prior folds are left unscored.

    Returns
    -------
    scores, bands
        ``scores`` has one row per scored fold (empirical vs nominal coverage,
        coverage error, mean width, and the number of calibration folds used).
        ``bands`` has one row per scored test day with the point and interval.
    """
    required = {"date", "fold", "y_true", "y_pred"}
    missing = required - set(forecasts.columns)
    if missing:
        raise KeyError(f"forecasts missing columns: {sorted(missing)}.")
    if not 0.0 <= lower_q < upper_q <= 1.0:
        raise ValueError("require 0 <= lower_q < upper_q <= 1.")

    df = _with_step_and_origin(forecasts)
    nominal = float(upper_q - lower_q)
    z_lo, z_hi = _normal_ppf(lower_q), _normal_ppf(upper_q)

    fold_origin = (
        df[["fold", "origin"]].drop_duplicates().sort_values("origin")
    )
    ordered_folds = list(fold_origin["fold"])
    origin_by_fold = dict(zip(fold_origin["fold"], fold_origin["origin"]))

    score_rows: list[dict] = []
    band_rows: list[pd.DataFrame] = []
    for fold in ordered_folds:
        origin = origin_by_fold[fold]
        calib = df[df["origin"] < origin]
        n_calib = calib["fold"].nunique()
        if n_calib < min_calib_folds:
            continue

        sigma_by_step = calib.groupby("step")["residual"].std(ddof=1)

        cur = df[df["fold"] == fold].copy()
        cur["sigma"] = cur["step"].map(sigma_by_step)
        cur["lower"] = cur["y_pred"] + z_lo * cur["sigma"]
        cur["upper"] = cur["y_pred"] + z_hi * cur["sigma"]

        valid = cur["sigma"].notna() & np.isfinite(cur["sigma"])
        scored = cur[valid & cur["y_true"].notna()]
        if scored.empty:
            continue
        inside = (scored["y_true"] >= scored["lower"]) & (
            scored["y_true"] <= scored["upper"]
        )
        coverage = float(inside.mean())
        width = float((scored["upper"] - scored["lower"]).mean())

        score_rows.append({
            "model": "ar_lag1_7",
            "target": forecasts["target"].iloc[0] if "target" in forecasts else None,
            "fold": fold,
            "test_start": pd.Timestamp(origin).date(),
            "n_test": int(len(cur)),
            "n_scored": int(len(scored)),
            "n_calib_folds": int(n_calib),
            "nominal_coverage": nominal,
            "empirical_coverage": coverage,
            "coverage_error": coverage - nominal,
            "interval_width": width,
        })
        band_rows.append(cur[[
            "date", "fold", "step", "y_true", "y_pred", "sigma", "lower", "upper",
        ]].assign(model="ar_lag1_7"))

    scores = pd.DataFrame(score_rows)
    bands = (
        pd.concat(band_rows, ignore_index=True) if band_rows else pd.DataFrame()
    )
    return scores, bands


def aggregate_ar_interval(scores: pd.DataFrame) -> pd.DataFrame:
    """One row per (model, target) with mean coverage diagnostics."""
    metric_cols = [
        "empirical_coverage", "nominal_coverage", "coverage_error", "interval_width",
    ]
    out = (
        scores.groupby(["model", "target"], dropna=False)[metric_cols]
        .mean()
        .reset_index()
    )
    out.columns = [
        c if c in ("model", "target") else f"{c}_mean" for c in out.columns
    ]
    out["n_folds_scored"] = (
        scores.groupby(["model", "target"], dropna=False)["fold"]
        .nunique()
        .to_numpy()
    )
    return out
