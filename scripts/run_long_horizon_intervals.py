"""Phase 4, step 8: full-horizon empirical placebo quantile bands.

The block-bootstrap intervals in ``run_interval_calibration.py`` are calibrated
on rolling-origin residuals from <=30-day folds, so they understate uncertainty
for a counterfactual that runs far beyond those validation folds. This script
uses the placebo-in-time windows, which are full-horizon pre-treatment recursive
forecasts, to construct a descriptive empirical quantile band. Each placebo
window's cumulative gap is a realised horizon-matched cumulative forecast error.

The placebo windows overlap, so the 2.5/97.5% quantiles do not have nominal 95%
coverage and are not a confidence, prediction, or conformal interval. Disjoint
block-rank and block-conformal inference is generated separately by
``run_block_inference.py``.

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

from hormuz_throughput import config  # noqa: E402
from hormuz_throughput.inference import (  # noqa: E402
    circular_block_bootstrap_loss_interval,
    overlapping_placebo_quantile_band,
)

LOWER_QUANTILE = 0.025
UPPER_QUANTILE = 0.975
BOOTSTRAP_ALPHA = 0.05


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

        cum_errors = -windows["cumulative_throughput_loss"]
        daily_errors = -windows["mean_daily_throughput_loss"]

        cum = overlapping_placebo_quantile_band(
            base["point_cumulative_throughput_loss"],
            cum_errors,
            lower_quantile=LOWER_QUANTILE,
            upper_quantile=UPPER_QUANTILE,
        )
        daily = overlapping_placebo_quantile_band(
            base["mean_daily_loss"],
            daily_errors,
            lower_quantile=LOWER_QUANTILE,
            upper_quantile=UPPER_QUANTILE,
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
            alpha=BOOTSTRAP_ALPHA,
        )

        width_30d = base["loss_interval_upper"] - base["loss_interval_lower"]
        rows.append({
            "model": model,
            "target": target,
            "lower_reference_quantile": LOWER_QUANTILE,
            "upper_reference_quantile": UPPER_QUANTILE,
            "nominal_coverage_supported": False,
            "horizon_calendar_days": horizon_calendar_days,
            "n_post_days": int(base["n_post_days"]),
            "n_horizon_windows": cum["n_horizon_windows"],
            "effective_non_overlapping_windows": _effective_non_overlapping(windows),
            "point_cumulative_throughput_loss": cum["point_loss"],
            "interval_30dfold_lower": float(base["loss_interval_lower"]),
            "interval_30dfold_upper": float(base["loss_interval_upper"]),
            "interval_30dfold_width": float(width_30d),
            "overlapping_placebo_quantile_band_lower": cum["band_lower"],
            "overlapping_placebo_quantile_band_upper": cum["band_upper"],
            "overlapping_placebo_quantile_band_width": cum["band_width"],
            "widening_factor_vs_30dfold": (
                cum["band_width"] / width_30d if width_30d else float("nan")
            ),
            "overlapping_placebo_band_excludes_zero_descriptively": cum[
                "band_excludes_zero_descriptively"
            ],
            "pre_period_bias_centered_out": cum["pre_period_mean_error_centered_out"],
            "interval_circular_bootstrap_lower": circular["interval_lower"],
            "interval_circular_bootstrap_upper": circular["interval_upper"],
            "interval_circular_bootstrap_width": circular["interval_width"],
            "circular_bootstrap_block_length": circular["block_length"],
            "circular_bootstrap_draws": circular["n_bootstrap_draws"],
            "circular_bootstrap_n_oof_residuals": circular["n_residuals"],
            "mean_daily_loss": daily["point_loss"],
            "mean_daily_overlapping_placebo_quantile_band_lower": daily["band_lower"],
            "mean_daily_overlapping_placebo_quantile_band_upper": daily["band_upper"],
            "mean_daily_overlapping_placebo_band_excludes_zero_descriptively": daily[
                "band_excludes_zero_descriptively"
            ],
        })

    summary = pd.DataFrame(rows).sort_values(["target", "model"]).reset_index(drop=True)
    out = config.path("data_processed") / "long_horizon_intervals_summary.csv"
    summary.to_csv(out, index=False)

    show = [
        "model", "target", "point_cumulative_throughput_loss",
        "interval_30dfold_lower", "interval_30dfold_upper",
        "overlapping_placebo_quantile_band_lower",
        "overlapping_placebo_quantile_band_upper",
        "interval_circular_bootstrap_lower", "interval_circular_bootstrap_upper",
        "widening_factor_vs_30dfold",
        "overlapping_placebo_band_excludes_zero_descriptively",
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
        "Full-horizon empirical placebo quantile bands vs short-fold intervals "
        f"({horizon_text}):"
    )
    print(summary[show].to_string(index=False))
    print(f"\nwrote {out}")
    print("\nInterpretation guard:")
    print(" - The band uses realised full-horizon placebo forecast errors.")
    print(" - The windows overlap: 2.5/97.5% are descriptive quantiles only.")
    print(" - Do not label this band a 95% confidence, prediction, or conformal interval.")
    print(" - Use the disjoint-block rank and block-conformal outputs for inference.")
    print(" - The circular-block band independently resamples the chronological OOF residual path.")
    print(" - It does not fix AIS measurement bias, donor contamination, or energy mediation.")


if __name__ == "__main__":
    main()
