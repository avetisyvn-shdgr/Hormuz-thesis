"""Phase 4, step 3: placebo-in-time inference for counterfactual gaps.

The script compares the real post-treatment throughput loss against losses from
pre-treatment placebo windows of the same horizon. This is an uncertainty layer,
not a final causal design; donor/placebo-in-space checks still come later.

Run from the repo root:
    python scripts/run_placebo_inference.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from hormuz_throughput import config  # noqa: E402
from hormuz_throughput.baselines import arx_forecast, seasonal_naive_forecast  # noqa: E402
from hormuz_throughput.inference import (  # noqa: E402
    counterfactual_effect,
    empirical_p_value,
    non_overlapping_fold_count,
    placebo_time_folds,
    post_treatment_fold,
    separation_ratio,
)
from hormuz_throughput.specification import working_specification  # noqa: E402


SPEC = working_specification()
TARGETS = list(SPEC.outcomes)

ROUTE_EXOG = [
    "panama_tanker_transits",
    "panama_tanker_capacity",
]

ENERGY_EXOG = [
    "henry_hub_spot",
    "brent_spot",
]


def _load_panel() -> pd.DataFrame:
    path = config.path("data_processed") / "panel_aligned.csv"
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found. Run scripts/build_panel.py and "
            "scripts/align_panel.py first."
        )
    return pd.read_csv(path, parse_dates=["date"]).set_index("date")


def _predict(panel: pd.DataFrame, target: str, fold, model: str) -> pd.Series:
    if model == "seasonal_naive_7d":
        return seasonal_naive_forecast(panel[target], fold, season_length=7)
    if model == "ar_lag1_7":
        return arx_forecast(
            panel,
            target=target,
            fold=fold,
            exog_cols=[],
            y_lags=(1, 7),
        )
    if model == "arx_lag1_7_route":
        return arx_forecast(
            panel,
            target=target,
            fold=fold,
            exog_cols=ROUTE_EXOG,
            y_lags=(1, 7),
        )
    if model == "arx_lag1_7_route_energy":
        return arx_forecast(
            panel,
            target=target,
            fold=fold,
            exog_cols=[*ROUTE_EXOG, *ENERGY_EXOG],
            y_lags=(1, 7),
        )
    raise ValueError(f"Unknown model {model!r}.")


def _effect_row(panel: pd.DataFrame, target: str, model: str, fold, is_actual: bool) -> dict:
    pred = _predict(panel, target, fold, model)
    true = panel.loc[pred.index, target]
    eff = counterfactual_effect(true, pred)
    return {
        "model": model,
        "target": target,
        "fold": fold.name,
        "is_actual": is_actual,
        "train_start": fold.train_start.date(),
        "train_end": fold.train_end.date(),
        "test_start": fold.test_start.date(),
        "test_end": fold.test_end.date(),
        "n_train": len(fold.train_idx),
        "n_test": len(fold.test_idx),
        **eff,
    }


def _summarize(effects: pd.DataFrame, effective_placebos: int) -> pd.DataFrame:
    rows = []
    for (model, target), group in effects.groupby(["model", "target"]):
        actual = group.loc[group["is_actual"]].iloc[0]
        placebo_rows = group.loc[~group["is_actual"]]
        placebos = placebo_rows["cumulative_throughput_loss"]
        placebo_daily = placebo_rows["mean_daily_throughput_loss"]
        placebo_loss_p95 = float(placebos.quantile(0.95))
        placebo_daily_p95 = float(placebo_daily.quantile(0.95))
        rows.append({
            "model": model,
            "target": target,
            "actual_cumulative_throughput_loss": float(
                actual["cumulative_throughput_loss"]
            ),
            "actual_mean_daily_throughput_loss": float(
                actual["mean_daily_throughput_loss"]
            ),
            "actual_n_days": int(actual["n_days"]),
            "actual_n_train": int(actual["n_train"]),
            "n_placebos": int(placebos.notna().sum()),
            "approx_non_overlapping_placebos": int(effective_placebos),
            "overlapping_windows": True,
            "nominal_p_value_supported": False,
            "placebo_train_min": int(placebo_rows["n_train"].min()),
            "placebo_train_median": float(placebo_rows["n_train"].median()),
            "placebo_train_max": int(placebo_rows["n_train"].max()),
            "placebo_valid_days_min": int(placebo_rows["n_days"].min()),
            "placebo_valid_days_median": float(placebo_rows["n_days"].median()),
            "placebo_valid_days_max": int(placebo_rows["n_days"].max()),
            "placebo_loss_mean": float(placebos.mean()),
            "placebo_loss_median": float(placebos.median()),
            "placebo_loss_p05": float(placebos.quantile(0.05)),
            "placebo_loss_p95": placebo_loss_p95,
            "loss_vs_placebo_p95_ratio": separation_ratio(
                actual["cumulative_throughput_loss"],
                placebo_loss_p95,
            ),
            "placebo_mean_daily_loss_mean": float(placebo_daily.mean()),
            "placebo_mean_daily_loss_median": float(placebo_daily.median()),
            "placebo_mean_daily_loss_p05": float(placebo_daily.quantile(0.05)),
            "placebo_mean_daily_loss_p95": placebo_daily_p95,
            "mean_daily_loss_vs_placebo_p95_ratio": separation_ratio(
                actual["mean_daily_throughput_loss"],
                placebo_daily_p95,
            ),
            "overlapping_reference_rank_loss_ge_actual": empirical_p_value(
                actual["cumulative_throughput_loss"],
                placebos,
                alternative="greater",
            ),
            "overlapping_reference_rank_mean_daily_loss_ge_actual": empirical_p_value(
                actual["mean_daily_throughput_loss"],
                placebo_daily,
                alternative="greater",
            ),
            "overlapping_reference_rank_abs_loss_ge_actual": empirical_p_value(
                actual["cumulative_throughput_loss"],
                placebos,
                alternative="two-sided",
            ),
        })
    return pd.DataFrame(rows)


def main() -> None:
    panel = _load_panel()
    actual = post_treatment_fold(panel.index)
    horizon_days = len(actual.test_idx)
    placebos = placebo_time_folds(
        panel.index,
        horizon_days=horizon_days,
        initial_train_days=365,
        step_days=30,
    )
    effective_placebos = non_overlapping_fold_count(placebos)

    print(f"actual window: {actual.test_start.date()} -> {actual.test_end.date()} "
          f"({horizon_days} calendar days)")
    print(f"placebo windows: {len(placebos)} overlapping; "
          f"~{effective_placebos} non-overlapping horizon-length windows")

    models = list(SPEC.estimators)

    rows = []
    for target in TARGETS:
        for model in models:
            rows.append(_effect_row(panel, target, model, actual, True))
            for fold in placebos:
                rows.append(_effect_row(panel, target, model, fold, False))

    effects = pd.DataFrame(rows)
    summary = _summarize(effects, effective_placebos)

    out_dir = config.path("data_processed")
    effects_out = out_dir / "placebo_time_effects.csv"
    summary_out = out_dir / "placebo_time_summary.csv"
    effects.to_csv(effects_out, index=False)
    summary.to_csv(summary_out, index=False)

    print("\nPlacebo-in-time summary:")
    print(summary.to_string(index=False))
    print(f"\nwrote {effects_out}")
    print(f"wrote {summary_out}")

    print("\nInterpretation guard:")
    print(" - Placebo windows overlap; their reference ranks are not p-values.")
    print(" - Report separation ratios and state when the loss exceeds all windows.")
    print(" - Use disjoint blocks for rank p-values and conformal calibration.")
    print(" - Use mean-daily loss for capacity comparisons because valid day counts differ.")
    print(" - This tests whether the observed gap is unusual vs earlier forecast errors.")
    print(" - It does not solve AIS measurement bias or donor contamination by itself.")


if __name__ == "__main__":
    main()
