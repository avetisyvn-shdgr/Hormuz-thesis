"""Isolated Chronos-2 benchmark; never part of the locked primary pipeline.

Install in a separate compatible environment with ``chronos-forecasting`` and
model weights, then run with ``--acknowledge-benchmark-only``. The script uses
only pre-treatment rolling-origin folds and does not modify settings.yaml.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lngfreight import config  # noqa: E402
from lngfreight.metrics import score_forecast  # noqa: E402
from lngfreight.specification import working_specification  # noqa: E402
from lngfreight.validation import resolve_cutoff, rolling_origin_splits  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--acknowledge-benchmark-only", action="store_true")
    parser.add_argument("--model-id", default="amazon/chronos-2")
    parser.add_argument("--device-map", default="cpu")
    args = parser.parse_args()
    if not args.acknowledge_benchmark_only:
        raise SystemExit(
            "Refusing to run without --acknowledge-benchmark-only; Chronos-2 is "
            "not the thesis foundation or an enabled estimator."
        )
    try:
        from chronos import Chronos2Pipeline
    except ImportError as exc:
        raise SystemExit(
            "chronos-forecasting is not installed. Use a separate benchmark "
            "environment; do not add it to the frozen core requirements."
        ) from exc

    spec = working_specification()
    panel = pd.read_csv(
        config.path("data_processed") / "panel_aligned.csv", parse_dates=["date"]
    ).set_index("date")
    panel = panel.loc[panel.index < resolve_cutoff()]
    target = spec.primary_outcome
    y = panel[target].astype("float64")
    pipeline = Chronos2Pipeline.from_pretrained(args.model_id, device_map=args.device_map)
    rows = []
    forecasts = []
    for fold in rolling_origin_splits(panel.index):
        train = y.iloc[fold.train_idx]
        test = y.iloc[fold.test_idx]
        context = pd.DataFrame({
            "id": target,
            "timestamp": train.index,
            "target": train.to_numpy(),
        })
        pred = pipeline.predict_df(
            context,
            prediction_length=len(test),
            quantile_levels=[0.025, 0.5, 0.975],
            id_column="id",
            timestamp_column="timestamp",
            target="target",
        ).sort_values("timestamp")
        point = pd.Series(pred["predictions"].to_numpy(), index=test.index)
        metrics = score_forecast(test, point, train, season_length=7)
        coverage = float(
            ((test.to_numpy() >= pred["0.025"].to_numpy())
             & (test.to_numpy() <= pred["0.975"].to_numpy())).mean()
        )
        rows.append({
            "model": args.model_id,
            "fold": fold.name,
            "target": target,
            "interval_95_coverage": coverage,
            **metrics,
        })
        forecasts.append(pd.DataFrame({
            "date": test.index,
            "fold": fold.name,
            "target": target,
            "y_true": test.to_numpy(),
            "y_pred": point.to_numpy(),
            "lower_95": pred["0.025"].to_numpy(),
            "upper_95": pred["0.975"].to_numpy(),
        }))
    out = config.path("data_processed")
    pd.DataFrame(rows).to_csv(out / "chronos2_benchmark_scores.csv", index=False)
    pd.concat(forecasts, ignore_index=True).to_csv(
        out / "chronos2_benchmark_forecasts.csv", index=False
    )
    print(pd.DataFrame(rows)[["mase", "rmse", "interval_95_coverage"]].mean())
    print("Benchmark only: no post-treatment covariates and no estimator promotion.")


if __name__ == "__main__":
    main()
