"""Bound the counterfactual's dependence on where the series sat at the cutoff.

Chapter 9 concedes a pre-cutoff movement in the treated series without saying
which way it pushes the headline number. This script answers that question
mechanically, with the locked design untouched: same model (`ar_lag1_7`), same
lags, same ridge penalty, same training cutoff (2026-02-28, exclusive), same
130-day scored window.

Only one thing varies. In each counterfactual world the final `k` observed
training days are replaced by the seven-day trailing mean as it stood `k` days
before the cutoff, which flattens the late-February rise without touching any
earlier observation. The model is then refitted and the 130-day recursive path
regenerated. The spread across `k` is the share of the reported shortfall that
is attributable to the terminal condition rather than to the disruption.

This is a bounding exercise, not a re-estimation. The locked run (k = 0) remains
the reported result.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lngfreight.baselines import arx_forecast  # noqa: E402
from lngfreight.validation import Fold  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
PANEL = ROOT / "data" / "processed" / "panel_aligned.csv"
OUT = ROOT / "data" / "processed" / "terminal_condition_sensitivity.csv"

TARGET = "hormuz_tanker_transits"
CUTOFF = pd.Timestamp("2026-02-28")      # exclusive training bound, locked
WINDOW_END = pd.Timestamp("2026-07-07")  # 130 scored days, locked
Y_LAGS = (1, 7)
RIDGE_ALPHA = 1e-6
K_GRID = (0, 7, 14, 21, 30)


def build_fold(index: pd.DatetimeIndex) -> Fold:
    train_idx = np.flatnonzero(index < CUTOFF)
    test_idx = np.flatnonzero((index >= CUTOFF) & (index <= WINDOW_END))
    return Fold(
        name="locked_treated_window",
        train_idx=train_idx,
        test_idx=test_idx,
        train_start=index[train_idx[0]],
        train_end=index[train_idx[-1]],
        test_start=index[test_idx[0]],
        test_end=index[test_idx[-1]],
    )


def flatten_tail(y: pd.Series, k: int) -> tuple[pd.Series, float]:
    """Replace the last k pre-cutoff days with the level k days before the cutoff."""
    if k == 0:
        return y.copy(), float("nan")
    pre = y[y.index < CUTOFF]
    anchor_end = pre.index[-k - 1]
    level = float(pre.loc[:anchor_end].tail(7).mean())
    out = y.copy()
    out.loc[pre.index[-k]:pre.index[-1]] = level
    return out, level


def main() -> None:
    panel = pd.read_csv(PANEL, parse_dates=["date"]).set_index("date").sort_index()
    y_obs = panel[TARGET].astype("float64")
    fold = build_fold(panel.index)
    scored = panel.index[fold.test_idx]
    observed_total = float(y_obs.loc[scored].sum())
    print(f"scored days {len(scored)}  {scored[0].date()} to {scored[-1].date()}")
    print(f"observed transits in window: {observed_total:,.1f}\n")

    rows = []
    baseline = None
    for k in K_GRID:
        y_k, level = flatten_tail(y_obs, k)
        p = panel.copy()
        p[TARGET] = y_k
        fc = arx_forecast(p, TARGET, fold, exog_cols=[],
                          y_lags=Y_LAGS, ridge_alpha=RIDGE_ALPHA)
        cf_total = float(fc.sum())
        shortfall = cf_total - observed_total
        if k == 0:
            baseline = shortfall
        rows.append({
            "k_days_flattened": k,
            "replacement_level": level,
            "last7_observed_mean": float(y_obs[y_obs.index < CUTOFF].tail(7).mean()),
            "counterfactual_total": cf_total,
            "observed_total": observed_total,
            "cumulative_shortfall": shortfall,
            "delta_vs_locked": shortfall - baseline,
            "pct_of_locked": 100.0 * (shortfall - baseline) / baseline,
        })
        print(f"k={k:3d}  level={level if k else float('nan'):6.2f}  "
              f"counterfactual={cf_total:9,.1f}  shortfall={shortfall:8,.1f}  "
              f"delta={shortfall - baseline:+8,.1f} ({100*(shortfall-baseline)/baseline:+5.1f}%)")

    out = pd.DataFrame(rows)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUT, index=False)
    print(f"\nwrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
