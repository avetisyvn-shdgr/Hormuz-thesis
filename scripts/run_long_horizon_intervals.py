"""Phase 4, step 8: honest long-horizon (94-day) counterfactual intervals.

The block-bootstrap intervals in ``run_interval_calibration.py`` are calibrated
on rolling-origin residuals from <=30-day folds, so they understate uncertainty
for a counterfactual that actually runs ~94 days (recursion depths 31-94 are not
represented). This script recalibrates the interval at the TRUE horizon by reusing
the placebo-in-time windows, which are full 94-day pre-treatment recursive
forecasts. Each placebo window's cumulative gap is a realised 94-day cumulative
forecast error; their spread is the honest forecast-error band.

It does not refit anything post-treatment and adds no new model. It compares the
old (<=30-day-fold) interval with the new (94-day-horizon) interval so the
magnitude of the previous understatement is explicit.

Run from the repo root:
    python scripts/run_placebo_inference.py        # produces the 94-day errors
    python scripts/run_interval_calibration.py     # produces the 30-day interval
    python scripts/run_long_horizon_intervals.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lngfreight import config  # noqa: E402
from lngfreight.inference import long_horizon_loss_interval  # noqa: E402

ALPHA = 0.05


def _read_processed(name: str) -> pd.DataFrame:
    path = config.path("data_processed") / name
    if not path.exists():
        raise FileNotFoundError(f"{path} not found. Run the upstream scripts first.")
    return pd.read_csv(path)


def _effective_non_overlapping(windows: pd.DataFrame) -> int:
    """Greedy count of non-overlapping placebo windows (effective independent N)."""
    spans = windows[["test_start", "test_end"]].copy()
    spans["test_start"] = pd.to_datetime(spans["test_start"])
    spans["test_end"] = pd.to_datetime(spans["test_end"])
    spans = spans.sort_values("test_start")
    count = 0
    last_end = None
    for _, w in spans.iterrows():
        if last_end is None or w["test_start"] > last_end:
            count += 1
            last_end = w["test_end"]
    return count


def main() -> None:
    intervals_30d = _read_processed("counterfactual_intervals_summary.csv")
    placebo = _read_processed("placebo_time_effects.csv")
    placebo = placebo[~placebo["is_actual"]].copy()

    rows = []
    for _, base in intervals_30d.iterrows():
        model, target = base["model"], base["target"]
        windows = placebo[(placebo["model"] == model) & (placebo["target"] == target)]
        if windows.empty:
            continue

        # Each placebo window cumulative_throughput_loss = sum(pred - obs);
        # the cumulative forecast error is its negative (sum(obs - pred)).
        cum_errors = -windows["cumulative_throughput_loss"]
        daily_errors = -windows["mean_daily_throughput_loss"]

        cum = long_horizon_loss_interval(
            base["point_cumulative_throughput_loss"], cum_errors, alpha=ALPHA
        )
        daily = long_horizon_loss_interval(
            base["mean_daily_loss"], daily_errors, alpha=ALPHA
        )

        width_30d = base["loss_interval_upper"] - base["loss_interval_lower"]
        rows.append({
            "model": model,
            "target": target,
            "alpha": ALPHA,
            "n_post_days": int(base["n_post_days"]),
            "n_horizon_windows": cum["n_horizon_windows"],
            "effective_non_overlapping_windows": _effective_non_overlapping(windows),
            "point_cumulative_throughput_loss": cum["point_loss"],
            # Old short-fold block-bootstrap interval (for comparison).
            "interval_30dfold_lower": float(base["loss_interval_lower"]),
            "interval_30dfold_upper": float(base["loss_interval_upper"]),
            "interval_30dfold_width": float(width_30d),
            # Honest 94-day-horizon interval.
            "interval_94dhorizon_lower": cum["interval_lower"],
            "interval_94dhorizon_upper": cum["interval_upper"],
            "interval_94dhorizon_width": cum["interval_width"],
            "widening_factor_vs_30dfold": (
                cum["interval_width"] / width_30d if width_30d else float("nan")
            ),
            "excludes_zero_94dhorizon": cum["excludes_zero"],
            "pre_period_bias_centered_out": cum["pre_period_mean_error_centered_out"],
            # Mean-daily band (robust to differing valid-day counts, esp. capacity).
            "mean_daily_loss": daily["point_loss"],
            "mean_daily_94dhorizon_lower": daily["interval_lower"],
            "mean_daily_94dhorizon_upper": daily["interval_upper"],
            "mean_daily_excludes_zero": daily["excludes_zero"],
        })

    summary = pd.DataFrame(rows).sort_values(["target", "model"]).reset_index(drop=True)
    out = config.path("data_processed") / "long_horizon_intervals_summary.csv"
    summary.to_csv(out, index=False)

    show = [
        "model", "target", "point_cumulative_throughput_loss",
        "interval_30dfold_lower", "interval_30dfold_upper",
        "interval_94dhorizon_lower", "interval_94dhorizon_upper",
        "widening_factor_vs_30dfold", "excludes_zero_94dhorizon",
        "n_horizon_windows", "effective_non_overlapping_windows",
    ]
    print("Long-horizon (94-day) vs short-fold (<=30-day) counterfactual intervals:")
    print(summary[show].to_string(index=False))
    print(f"\nwrote {out}")
    print("\nInterpretation guard:")
    print(" - The 94-day interval reuses placebo-in-time windows = realised 94-day forecast errors.")
    print(" - It is wider than the 30-day-fold interval; that gap is the previous understatement.")
    print(" - Placebo windows overlap (~9 effective) and use expanding training, so the band is")
    print("   coarse and conservative (wider), not a precise tail.")
    print(" - It does not fix AIS measurement bias, donor contamination, or energy mediation.")


if __name__ == "__main__":
    main()
