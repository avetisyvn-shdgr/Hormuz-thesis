"""Contract tests for the raw horizon-aware AR interval (calibration leg)."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lngfreight.ar_intervals import (
    _normal_ppf,
    aggregate_ar_interval,
    evaluate_ar_horizon_interval,
)


def _ar_forecasts(n_folds=20, horizon=10, seed=0):
    """Synthetic AR-style fold forecasts with growing step-ahead residuals."""
    rng = np.random.default_rng(seed)
    rows = []
    start = pd.Timestamp("2022-01-01")
    for k in range(n_folds):
        origin = start + pd.Timedelta(days=30 * k)
        for s in range(1, horizon + 1):
            # Residual spread grows with the step (horizon-aware by construction).
            resid = rng.normal(0, s)
            y_pred = 100.0
            rows.append({
                "date": origin + pd.Timedelta(days=s - 1),
                "fold": f"fold_{k + 1:02d}",
                "target": "y",
                "y_true": y_pred + resid,
                "y_pred": y_pred,
            })
    return pd.DataFrame(rows)


def test_normal_ppf_matches_known_quantiles():
    assert _normal_ppf(0.5) == pytest.approx(0.0, abs=1e-6)
    assert _normal_ppf(0.975) == pytest.approx(1.959964, abs=1e-4)
    assert _normal_ppf(0.025) == pytest.approx(-1.959964, abs=1e-4)
    with pytest.raises(ValueError):
        _normal_ppf(0.0)


def test_min_calib_folds_excludes_early_folds():
    fc = _ar_forecasts(n_folds=20, horizon=10)
    scores, _ = evaluate_ar_horizon_interval(fc, min_calib_folds=15)
    # Only folds with >=15 strictly-earlier folds are scored: folds 16..20.
    assert len(scores) == 5
    assert scores["n_calib_folds"].min() >= 15


def test_interval_is_horizon_aware_band_widens_with_step():
    fc = _ar_forecasts(n_folds=20, horizon=10)
    _, bands = evaluate_ar_horizon_interval(fc, min_calib_folds=15)
    width = (bands["upper"] - bands["lower"]).groupby(bands["step"]).mean()
    # Spread was built to grow with step, so the band must widen with the horizon.
    assert width.loc[10] > width.loc[1]


def test_calibration_uses_only_strictly_earlier_folds():
    """Leakage guard: altering a fold's own residuals must not change ITS band
    (the band is built from strictly-earlier folds only)."""
    fc = _ar_forecasts(n_folds=20, horizon=10)
    _, bands = evaluate_ar_horizon_interval(fc, min_calib_folds=15)
    target_fold = "fold_16"
    base = bands[bands["fold"] == target_fold].sort_values("step")["sigma"].to_numpy()

    altered = fc.copy()
    mask = altered["fold"] == target_fold
    altered.loc[mask, "y_true"] = altered.loc[mask, "y_true"] + 10000.0
    _, bands2 = evaluate_ar_horizon_interval(altered, min_calib_folds=15)
    alt = bands2[bands2["fold"] == target_fold].sort_values("step")["sigma"].to_numpy()

    np.testing.assert_allclose(base, alt)


def test_aggregate_reports_coverage_error_per_target():
    fc = _ar_forecasts(n_folds=20, horizon=10)
    scores, _ = evaluate_ar_horizon_interval(fc, min_calib_folds=15)
    agg = aggregate_ar_interval(scores)
    assert len(agg) == 1
    assert {"coverage_error_mean", "empirical_coverage_mean", "n_folds_scored"}.issubset(
        agg.columns
    )
    assert agg.loc[0, "n_folds_scored"] == 5


def test_missing_columns_raise():
    with pytest.raises(KeyError, match="missing"):
        evaluate_ar_horizon_interval(pd.DataFrame({"date": [], "fold": []}))
