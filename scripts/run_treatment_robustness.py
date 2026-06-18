"""Phase 4, step 6: treatment-date robustness with fixed pre-treatment training.

This is a DONUT design, not a cutoff sweep. The model is always trained only on
data before the earliest defensible disruption date. Later event dates can
define post-period windows, but they never move disrupted days into training.

Run from the repo root:
    python scripts/run_treatment_robustness.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lngfreight import config  # noqa: E402
from lngfreight.baselines import arx_forecast, seasonal_naive_forecast  # noqa: E402
from lngfreight.inference import counterfactual_effect, fixed_train_post_fold  # noqa: E402
from lngfreight.validation import resolve_cutoff  # noqa: E402
from lngfreight.specification import working_specification  # noqa: E402


SPEC = working_specification()
TARGETS = list(SPEC.outcomes)
MODELS = list(SPEC.estimators)

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


def _post_windows() -> list[dict[str, object]]:
    candidates = config.settings()["study_window"]["treatment_candidates"]
    train_cutoff = resolve_cutoff()
    force_majeure = pd.Timestamp(candidates["force_majeure"])
    donut_post_start = force_majeure + pd.Timedelta(days=1)
    windows = [
        {
            "window": "donut_clean_post_after_force_majeure",
            "post_start": donut_post_start,
            "is_donut": True,
            "excluded_start": train_cutoff,
            "excluded_end": force_majeure,
            "note": (
                "Primary donut design: train before the earliest disruption "
                "date and exclude the ambiguous transition window."
            ),
        },
        {
            "window": "anchored_kinetic_trigger",
            "post_start": pd.Timestamp(candidates["kinetic_trigger"]),
            "is_donut": False,
            "excluded_start": pd.NaT,
            "excluded_end": pd.NaT,
            "note": "Sensitivity window; training cutoff remains fixed before the disruption.",
        },
        {
            "window": "anchored_closure_declaration",
            "post_start": pd.Timestamp(candidates["closure_declaration"]),
            "is_donut": False,
            "excluded_start": pd.NaT,
            "excluded_end": pd.NaT,
            "note": "Sensitivity window; training cutoff remains fixed before the disruption.",
        },
        {
            "window": "anchored_force_majeure",
            "post_start": force_majeure,
            "is_donut": False,
            "excluded_start": pd.NaT,
            "excluded_end": pd.NaT,
            "note": "Sensitivity window; training cutoff remains fixed before the disruption.",
        },
    ]
    for window in windows:
        if pd.Timestamp(window["post_start"]) < train_cutoff:
            raise ValueError(
                f"Window {window['window']} starts before fixed training cutoff "
                f"{train_cutoff.date()}."
            )
    return windows


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


def _effect_rows(
    panel: pd.DataFrame,
    target: str,
    model: str,
    forecast_fold,
    window: dict[str, object],
    train_cutoff: pd.Timestamp,
) -> tuple[dict[str, object], pd.DataFrame]:
    post_start = pd.Timestamp(window["post_start"])
    pred_full = _predict(panel, target, forecast_fold, model)
    pred = pred_full.loc[pred_full.index >= post_start]
    true = panel.loc[pred.index, target]
    eff = counterfactual_effect(true, pred)
    daily = pd.DataFrame({
        "date": pred.index,
        "window": window["window"],
        "model": model,
        "target": target,
        "y_true": true.to_numpy(dtype="float64"),
        "y_pred": pred.to_numpy(dtype="float64"),
    })
    daily["gap_observed_minus_predicted"] = daily["y_true"] - daily["y_pred"]
    daily["throughput_loss_vs_counterfactual"] = daily["y_pred"] - daily["y_true"]
    daily["cumulative_throughput_loss"] = (
        daily["throughput_loss_vs_counterfactual"].fillna(0).cumsum()
    )

    summary = {
        "window": window["window"],
        "model": model,
        "target": target,
        "is_donut": bool(window["is_donut"]),
        "fixed_train_cutoff": train_cutoff.date(),
        "train_start": forecast_fold.train_start.date(),
        "train_end": forecast_fold.train_end.date(),
        "forecast_bridge_start": forecast_fold.test_start.date(),
        "post_start": pred.index.min().date(),
        "post_end": pred.index.max().date(),
        "excluded_start": (
            pd.Timestamp(window["excluded_start"]).date()
            if not pd.isna(window["excluded_start"])
            else None
        ),
        "excluded_end": (
            pd.Timestamp(window["excluded_end"]).date()
            if not pd.isna(window["excluded_end"])
            else None
        ),
        "n_train": len(forecast_fold.train_idx),
        "n_forecast_bridge_days": len(forecast_fold.test_idx),
        "n_scored_days": len(pred),
        "note": window["note"],
        **eff,
    }
    return summary, daily


def main() -> None:
    panel = _load_panel()
    train_cutoff = resolve_cutoff()
    windows = _post_windows()

    print(f"fixed training cutoff: {train_cutoff.date()} "
          "(training rows are strictly before this date)")
    print("later event dates define post windows only; they are never training cutoffs")

    summary_rows = []
    daily_rows = []
    forecast_fold = fixed_train_post_fold(
        panel.index,
        train_cutoff=train_cutoff,
        post_start=train_cutoff,
        name="fixed_pre_treatment_forecast_bridge",
    )
    print(f"forecast bridge: {forecast_fold.test_start.date()} -> "
          f"{forecast_fold.test_end.date()} (scoring depends on window)")
    for window in windows:
        print(f"{window['window']}: train {forecast_fold.train_start.date()} -> "
              f"{forecast_fold.train_end.date()}, score post >= "
              f"{pd.Timestamp(window['post_start']).date()}")
        for target in TARGETS:
            for model in MODELS:
                summary, daily = _effect_rows(
                    panel,
                    target,
                    model,
                    forecast_fold,
                    window,
                    train_cutoff,
                )
                summary_rows.append(summary)
                daily_rows.append(daily)

    summary = pd.DataFrame(summary_rows)
    daily = pd.concat(daily_rows, ignore_index=True)

    out_dir = config.path("data_processed")
    summary_out = out_dir / "treatment_robustness_summary.csv"
    daily_out = out_dir / "treatment_robustness_daily.csv"
    summary.to_csv(summary_out, index=False)
    daily.to_csv(daily_out, index=False)

    print("\nTreatment-window robustness summary:")
    print(summary.to_string(index=False))
    print(f"\nwrote {summary_out}")
    print(f"wrote {daily_out}")
    print("\nInterpretation guard:")
    print(" - This is not a cutoff sweep; the training cutoff remains 2026-02-28.")
    print(" - The donut design excludes 2026-02-28 through 2026-03-25 from effect scoring.")
    print(" - Later cutoffs would train on disrupted days and poison the baseline.")
    print(" - Route+energy ARX may absorb post-treatment energy mediation; compare route-only.")


if __name__ == "__main__":
    main()
