"""Phase 4, step 5: residual-calibrated intervals for counterfactual gaps.

Uses pre-treatment rolling-origin residuals from `baseline_forecasts.csv` to
calibrate post-treatment counterfactual bands from
`counterfactual_post_treatment.csv`.

Outputs:
  - pointwise counterfactual / loss bands
  - aggregate cumulative-loss intervals via block-resampled residual sums

Run from the repo root:
    python scripts/run_baseline.py
    python scripts/run_counterfactual.py
    python scripts/run_interval_calibration.py
"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from hormuz_throughput import config  # noqa: E402
from hormuz_throughput.inference import block_residual_sums, residual_quantiles  # noqa: E402


ALPHA = 0.05
BLOCK_LENGTH = 7
N_DRAWS = 5000


def _read_processed(name: str) -> pd.DataFrame:
    path = config.path("data_processed") / name
    if not path.exists():
        raise FileNotFoundError(f"{path} not found. Run the upstream scripts first.")
    return pd.read_csv(path, parse_dates=["date"] if "forecasts" in name or "counterfactual" in name else None)


def _calibration_residuals(baseline: pd.DataFrame, model: str, target: str) -> pd.Series:
    rows = baseline[(baseline["model"] == model) & (baseline["target"] == target)].copy()
    if rows.empty:
        raise ValueError(f"No calibration residuals for model={model!r}, target={target!r}.")
    residuals = rows["y_true"] - rows["y_pred"]
    residuals = residuals.replace([np.inf, -np.inf], np.nan).dropna()
    if residuals.empty:
        raise ValueError(f"No finite calibration residuals for model={model!r}, target={target!r}.")
    return residuals


def _stable_seed(base_seed: int, model: str, target: str) -> int:
    digest = hashlib.sha256(f"{model}:{target}".encode("utf-8")).hexdigest()
    return base_seed + int(digest[:8], 16) % 100000


def main() -> None:
    baseline = _read_processed("baseline_forecasts.csv")
    post = _read_processed("counterfactual_post_treatment.csv")

    daily_rows = []
    summary_rows = []
    rng_seed = int(config.settings()["reproducibility"]["random_seed"])

    for (model, target), group in post.groupby(["model", "target"]):
        valid = group.dropna(subset=["y_true", "y_pred"]).copy()
        if valid.empty:
            continue

        residuals = _calibration_residuals(baseline, model, target)
        q_lo, q_hi = residual_quantiles(residuals, alpha=ALPHA)
        point_loss = float((valid["y_pred"] - valid["y_true"]).sum())
        horizon = len(valid)
        residual_sums = block_residual_sums(
            residuals,
            horizon=horizon,
            block_length=BLOCK_LENGTH,
            n_draws=N_DRAWS,
            seed=_stable_seed(rng_seed, model, target),
        )
        residual_sum_mean = float(residual_sums.mean())
        loss_draws = point_loss + (residual_sums - residual_sum_mean)
        ci_lo, ci_hi = np.quantile(loss_draws, [ALPHA / 2, 1 - ALPHA / 2])

        valid["counterfactual_lower"] = valid["y_pred"] + q_lo
        valid["counterfactual_upper"] = valid["y_pred"] + q_hi
        valid["loss_lower"] = valid["counterfactual_lower"] - valid["y_true"]
        valid["loss_upper"] = valid["counterfactual_upper"] - valid["y_true"]
        valid["alpha"] = ALPHA
        valid["calibration_residual_q_low"] = q_lo
        valid["calibration_residual_q_high"] = q_hi
        daily_rows.append(valid)

        summary_rows.append({
            "model": model,
            "target": target,
            "alpha": ALPHA,
            "block_length": BLOCK_LENGTH,
            "n_bootstrap_draws": N_DRAWS,
            "n_calibration_residuals": int(len(residuals)),
            "n_post_days": int(horizon),
            "point_cumulative_throughput_loss": point_loss,
            "bootstrap_residual_sum_mean_centered_out": residual_sum_mean,
            "loss_interval_lower": float(ci_lo),
            "loss_interval_upper": float(ci_hi),
            "mean_daily_loss": point_loss / horizon,
            "mean_daily_loss_interval_lower": float(ci_lo / horizon),
            "mean_daily_loss_interval_upper": float(ci_hi / horizon),
            "residual_q_low": q_lo,
            "residual_q_high": q_hi,
        })

    daily = pd.concat(daily_rows, ignore_index=True)
    summary = pd.DataFrame(summary_rows).sort_values(["target", "model"])

    out_dir = config.path("data_processed")
    daily_out = out_dir / "counterfactual_intervals_daily.csv"
    summary_out = out_dir / "counterfactual_intervals_summary.csv"
    daily.to_csv(daily_out, index=False)
    summary.to_csv(summary_out, index=False)

    print("Residual-calibrated aggregate intervals:")
    print(summary.to_string(index=False))
    print(f"\nwrote {daily_out}")
    print(f"wrote {summary_out}")
    print("\nInterpretation guard:")
    print(" - Intervals use pre-treatment rolling-origin residuals, not post-treatment fit.")
    print(" - Aggregate intervals are block-resampled residual-sum bands, not structural causal intervals.")
    print(" - If AIS dark activity is treatment-correlated, these intervals do not fix that measurement bias.")


if __name__ == "__main__":
    main()
