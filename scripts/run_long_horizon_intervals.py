"""Phase 4, step 8: honest horizon-matched counterfactual intervals.

The block-bootstrap intervals in ``run_interval_calibration.py`` are calibrated
on rolling-origin residuals from <=30-day folds, so they understate uncertainty
for a counterfactual that runs far beyond those validation folds. This script
recalibrates the interval at the current post-window horizon by reusing the
placebo-in-time windows, which are full-horizon pre-treatment recursive
forecasts. Each placebo window's cumulative gap is a realised horizon-matched
cumulative forecast error; their spread is the honest forecast-error band.

It does not refit anything post-treatment and adds no new model. It compares the
old (<=30-day-fold) interval with the horizon-matched interval so the magnitude
of the previous understatement is explicit.

Run from the repo root:
    python scripts/run_placebo_inference.py        # produces full-horizon errors
    python scripts/run_interval_calibration.py     # produces the 30-day interval
    python scripts/run_long_horizon_intervals.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lngfreight import config  # noqa: E402
from lngfreight.inference import (  # noqa: E402
    circular_block_bootstrap_loss_interval,
    long_horizon_loss_interval,
)

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


def _horizon_calendar_days(windows: pd.DataFrame, model: str, target: str) -> int:
    spans = windows[["test_start", "test_end"]].copy()
    spans["test_start"] = pd.to_datetime(spans["test_start"])
    spans["test_end"] = pd.to_datetime(spans["test_end"])
    lengths = (spans["test_end"] - spans["test_start"]).dt.days + 1
    unique = sorted(int(value) for value in lengths.dropna().unique())
    if len(unique) != 1:
        raise ValueError(
            "Placebo windows for "
            f"{model}/{target} do not share one calendar horizon: {unique}"
        )
    return unique[0]


def main() -> None:
    intervals_30d = _read_processed("counterfactual_intervals_summary.csv")
    placebo = _read_processed("placebo_time_effects.csv")
    placebo = placebo[~placebo["is_actual"]].copy()
    validation_forecasts = _read_processed("baseline_forecasts.csv")
    crosscheck = config.settings()["long_horizon_crosscheck"]
    seed = int(config.settings()["reproducibility"]["random_seed"])

    rows = []
    for row_number, (_, base) in enumerate(intervals_30d.iterrows()):
        model, target = base["model"], base["target"]
        windows = placebo[(placebo["model"] == model) & (placebo["target"] == target)]
        if windows.empty:
            continue
        horizon_calendar_days = _horizon_calendar_days(windows, model, target)

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
        residual_path = validation_forecasts.loc[
            validation_forecasts["model"].eq(model)
            & validation_forecasts["target"].eq(target)
        ].sort_values("date")
        if residual_path["date"].duplicated().any():
            raise ValueError(f"Duplicate OOF residual dates for {model}/{target}.")
        circular = circular_block_bootstrap_loss_interval(
            base["point_cumulative_throughput_loss"],
            residual_path["error"],
            horizon=int(base["n_post_days"]),
            block_length=int(crosscheck["circular_block_length_days"]),
            n_draws=int(crosscheck["bootstrap_draws"]),
            seed=seed + row_number,
            alpha=ALPHA,
        )

        width_30d = base["loss_interval_upper"] - base["loss_interval_lower"]
        rows.append({
            "model": model,
            "target": target,
            "alpha": ALPHA,
            "horizon_calendar_days": horizon_calendar_days,
            "n_post_days": int(base["n_post_days"]),
            "n_horizon_windows": cum["n_horizon_windows"],
            "effective_non_overlapping_windows": _effective_non_overlapping(windows),
            "point_cumulative_throughput_loss": cum["point_loss"],
            # Old short-fold block-bootstrap interval (for comparison).
            "interval_30dfold_lower": float(base["loss_interval_lower"]),
            "interval_30dfold_upper": float(base["loss_interval_upper"]),
            "interval_30dfold_width": float(width_30d),
            # Honest horizon-matched interval.
            "interval_horizon_matched_lower": cum["interval_lower"],
            "interval_horizon_matched_upper": cum["interval_upper"],
            "interval_horizon_matched_width": cum["interval_width"],
            "widening_factor_vs_30dfold": (
                cum["interval_width"] / width_30d if width_30d else float("nan")
            ),
            "excludes_zero_horizon_matched": cum["excludes_zero"],
            "pre_period_bias_centered_out": cum["pre_period_mean_error_centered_out"],
            # Independent cross-check from the ordered OOF residual path.
            "interval_circular_bootstrap_lower": circular["interval_lower"],
            "interval_circular_bootstrap_upper": circular["interval_upper"],
            "interval_circular_bootstrap_width": circular["interval_width"],
            "circular_bootstrap_block_length": circular["block_length"],
            "circular_bootstrap_draws": circular["n_bootstrap_draws"],
            "circular_bootstrap_n_oof_residuals": circular["n_residuals"],
            # Mean-daily band (robust to differing valid-day counts, esp. capacity).
            "mean_daily_loss": daily["point_loss"],
            "mean_daily_horizon_matched_lower": daily["interval_lower"],
            "mean_daily_horizon_matched_upper": daily["interval_upper"],
            "mean_daily_excludes_zero": daily["excludes_zero"],
        })

    summary = pd.DataFrame(rows).sort_values(["target", "model"]).reset_index(drop=True)
    out = config.path("data_processed") / "long_horizon_intervals_summary.csv"
    summary.to_csv(out, index=False)

    show = [
        "model", "target", "point_cumulative_throughput_loss",
        "interval_30dfold_lower", "interval_30dfold_upper",
        "interval_horizon_matched_lower", "interval_horizon_matched_upper",
        "interval_circular_bootstrap_lower", "interval_circular_bootstrap_upper",
        "widening_factor_vs_30dfold", "excludes_zero_horizon_matched",
        "horizon_calendar_days", "n_horizon_windows",
        "effective_non_overlapping_windows",
    ]
    horizons = sorted(summary["horizon_calendar_days"].unique())
    horizon_text = (
        f"{int(horizons[0])} calendar days"
        if len(horizons) == 1
        else ", ".join(f"{int(value)} calendar days" for value in horizons)
    )
    print(
        "Horizon-matched vs short-fold (<=30-day) counterfactual intervals "
        f"({horizon_text}):"
    )
    print(summary[show].to_string(index=False))
    print(f"\nwrote {out}")
    print("\nInterpretation guard:")
    print(" - The horizon-matched interval reuses placebo-in-time windows = realised full-horizon forecast errors.")
    print(" - It is wider than the 30-day-fold interval; that gap is the previous understatement.")
    print(" - Placebo windows overlap and use expanding training, so the band is")
    print("   coarse and conservative (wider), not a precise tail.")
    print(" - The circular-block band independently resamples the chronological OOF residual path.")
    print(" - It does not fix AIS measurement bias, donor contamination, or energy mediation.")


if __name__ == "__main__":
    main()
