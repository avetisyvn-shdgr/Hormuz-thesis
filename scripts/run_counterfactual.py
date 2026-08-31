"""Phase 4, step 2: export post-treatment counterfactual gaps.

This script trains transparent baselines on the full pre-treatment period and
forecasts the observed disruption window. It does not estimate a final causal
effect yet; it creates auditable observed-minus-counterfactual series for the
next ITS / placebo-inference step.

Run from the repo root:
    python scripts/run_counterfactual.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from hormuz_throughput import config  # noqa: E402
from hormuz_throughput.baselines import arx_forecast, seasonal_naive_forecast  # noqa: E402
from hormuz_throughput.validation import Fold, resolve_cutoff  # noqa: E402
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


def _post_treatment_fold(panel: pd.DataFrame) -> Fold:
    cutoff = resolve_cutoff()
    train_idx = np.flatnonzero(panel.index < cutoff)
    test_idx = np.flatnonzero(panel.index >= cutoff)
    if len(train_idx) == 0 or len(test_idx) == 0:
        raise ValueError(
            f"Cannot build post-treatment fold at cutoff {cutoff.date()}: "
            "need both pre- and post-treatment rows."
        )
    return Fold(
        name="post_treatment",
        train_idx=train_idx,
        test_idx=test_idx,
        train_start=panel.index[train_idx[0]],
        train_end=panel.index[train_idx[-1]],
        test_start=panel.index[test_idx[0]],
        test_end=panel.index[test_idx[-1]],
    )


def _forecast_rows(
    panel: pd.DataFrame,
    target: str,
    model: str,
    y_pred: pd.Series,
) -> pd.DataFrame:
    y_true = panel.loc[y_pred.index, target].astype("float64")
    out = pd.DataFrame({
        "date": y_pred.index,
        "model": model,
        "target": target,
        "y_true": y_true.to_numpy(),
        "y_pred": y_pred.to_numpy(),
    })
    out["gap_observed_minus_predicted"] = out["y_true"] - out["y_pred"]
    out["throughput_loss_vs_counterfactual"] = out["y_pred"] - out["y_true"]
    out["cumulative_throughput_loss"] = (
        out["throughput_loss_vs_counterfactual"].fillna(0).cumsum()
    )
    return out


def _summary(counterfactuals: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (model, target), g in counterfactuals.groupby(["model", "target"]):
        valid = g.dropna(subset=["y_true", "y_pred"])
        rows.append({
            "model": model,
            "target": target,
            "start": valid["date"].min().date() if len(valid) else None,
            "end": valid["date"].max().date() if len(valid) else None,
            "n_days": int(len(valid)),
            "observed_sum": float(valid["y_true"].sum()),
            "counterfactual_sum": float(valid["y_pred"].sum()),
            "cumulative_gap_observed_minus_predicted": float(
                valid["gap_observed_minus_predicted"].sum()
            ),
            "cumulative_throughput_loss": float(
                valid["throughput_loss_vs_counterfactual"].sum()
            ),
            "mean_daily_throughput_loss": float(
                valid["throughput_loss_vs_counterfactual"].mean()
            ),
        })
    return pd.DataFrame(rows)


def main() -> None:
    panel = _load_panel()
    fold = _post_treatment_fold(panel)

    print(f"counterfactual fold: train {fold.train_start.date()} -> "
          f"{fold.train_end.date()}, forecast {fold.test_start.date()} -> "
          f"{fold.test_end.date()}")

    outputs = []
    for target in TARGETS:
        seasonal = seasonal_naive_forecast(
            panel[target],
            fold=fold,
            season_length=7,
        )
        outputs.append(_forecast_rows(panel, target, "seasonal_naive_7d", seasonal))

        ar_only = arx_forecast(
            panel,
            target=target,
            fold=fold,
            exog_cols=[],
            y_lags=(1, 7),
        )
        outputs.append(_forecast_rows(panel, target, "ar_lag1_7", ar_only))

        route_only = arx_forecast(
            panel,
            target=target,
            fold=fold,
            exog_cols=ROUTE_EXOG,
            y_lags=(1, 7),
        )
        outputs.append(_forecast_rows(panel, target, "arx_lag1_7_route", route_only))

        route_energy = arx_forecast(
            panel,
            target=target,
            fold=fold,
            exog_cols=[*ROUTE_EXOG, *ENERGY_EXOG],
            y_lags=(1, 7),
        )
        outputs.append(_forecast_rows(panel, target, "arx_lag1_7_route_energy", route_energy))

    counterfactuals = pd.concat(outputs, ignore_index=True)
    summary = _summary(counterfactuals)

    out_dir = config.path("data_processed")
    cf_out = out_dir / "counterfactual_post_treatment.csv"
    summary_out = out_dir / "counterfactual_post_treatment_summary.csv"
    counterfactuals.to_csv(cf_out, index=False)
    summary.to_csv(summary_out, index=False)

    print("\nPost-treatment counterfactual summary:")
    print(summary.to_string(index=False))
    print(f"\nwrote {cf_out}")
    print(f"wrote {summary_out}")

    print("\nInterpretation guard:")
    print(" - These are conditional counterfactual gaps, not final causal inference.")
    print(" - AR-only has no post-treatment covariate exposure and is the working primary.")
    print(" - Route+energy ARX may absorb post-treatment energy mediation; compare it to route-only ARX.")
    print(" - Route-only ARX is also conditional on observed post-treatment Panama traffic.")
    print(" - Placebo inference is still required before thesis-level effect claims.")


if __name__ == "__main__":
    main()
