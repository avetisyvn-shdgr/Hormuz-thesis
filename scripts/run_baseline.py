"""Phase 4, step 1: run transparent forecasting baselines.

This is the first actual modeling increment. It uses the already-processed
free-data panel and the leakage-safe rolling-origin folds, then writes fold
scores and test-window forecasts for inspection.

Run from the repo root:
    python scripts/run_baseline.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from hormuz_throughput import config  # noqa: E402
from hormuz_throughput.baselines import (  # noqa: E402
    aggregate_scores,
    evaluate_arx,
    evaluate_seasonal_naive,
)
from hormuz_throughput.validation import rolling_origin_splits, summary  # noqa: E402
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


def main() -> None:
    panel = _load_panel()
    folds = rolling_origin_splits(panel.index)

    print(f"panel shape: {panel.shape}  "
          f"({panel.index.min().date()} -> {panel.index.max().date()})")
    print(f"rolling-origin folds: {len(folds)}")
    print(summary(folds).tail(5).to_string(index=False))

    all_scores = []
    all_forecasts = []
    for target in TARGETS:
        scores, forecasts = evaluate_seasonal_naive(
            panel,
            target=target,
            season_length=7,
            folds=folds,
        )
        all_scores.append(scores)
        all_forecasts.append(forecasts)

        ar_scores, ar_forecasts = evaluate_arx(
            panel,
            target=target,
            exog_cols=[],
            y_lags=(1, 7),
            folds=folds,
            model_name="ar_lag1_7",
        )
        all_scores.append(ar_scores)
        all_forecasts.append(ar_forecasts)

        arx_route_scores, arx_route_forecasts = evaluate_arx(
            panel,
            target=target,
            exog_cols=ROUTE_EXOG,
            y_lags=(1, 7),
            folds=folds,
            model_name="arx_lag1_7_route",
        )
        all_scores.append(arx_route_scores)
        all_forecasts.append(arx_route_forecasts)

        arx_energy_scores, arx_energy_forecasts = evaluate_arx(
            panel,
            target=target,
            exog_cols=[*ROUTE_EXOG, *ENERGY_EXOG],
            y_lags=(1, 7),
            folds=folds,
            model_name="arx_lag1_7_route_energy",
        )
        all_scores.append(arx_energy_scores)
        all_forecasts.append(arx_energy_forecasts)

    scores = pd.concat(all_scores, ignore_index=True)
    forecasts = pd.concat(all_forecasts, ignore_index=True)
    aggregate = aggregate_scores(scores)

    out_dir = config.path("data_processed")
    scores_out = out_dir / "baseline_scores.csv"
    forecasts_out = out_dir / "baseline_forecasts.csv"
    aggregate_out = out_dir / "baseline_summary.csv"
    scores.to_csv(scores_out, index=False)
    forecasts.to_csv(forecasts_out, index=False)
    aggregate.to_csv(aggregate_out, index=False)

    print("\nAggregate scores:")
    print(aggregate.to_string(index=False))
    print(f"\nwrote {scores_out}")
    print(f"wrote {forecasts_out}")
    print(f"wrote {aggregate_out}")

    print("\nInterpretation guard:")
    print(" - These are pre-treatment validation scores, not causal effects.")
    print(" - Seasonal naive is the benchmark; AR tests target-only dynamics.")
    print(" - ARX tests whether observed controls improve pre-treatment prediction.")
    print(f" - Working primary estimator: {SPEC.primary_estimator}.")
    print(" - ARX uses observed exogenous controls, but held-out target values are not used as lags.")
    print(" - Spark access is not required for this layer.")


if __name__ == "__main__":
    main()
