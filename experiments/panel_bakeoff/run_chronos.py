"""Run cached Chronos-2 in univariate and within-chokepoint multivariate modes.

This script must be run in the isolated Python 3.11 benchmark environment:

    .venv-bench/bin/python -m experiments.panel_bakeoff.run_chronos
"""
from __future__ import annotations

import json
import platform
import random
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from chronos import Chronos2Pipeline

from .protocol import (
    EXPLICIT_CLASSES,
    HORIZONS,
    OUTPUT_DIR,
    RAW_PATH,
    composition_wide,
    file_sha256,
    folds,
    load_raw_panel,
    mase_scale,
    port_groups,
    total_wide,
)
from .run_classical import _daily_chunk, _score_chunk


MODEL_REVISION = "29ec3766d36d6f73f0696f85560a422f50e8498c"
MODEL_PATH = Path.home() / (
    ".cache/huggingface/hub/models--amazon--chronos-2/snapshots/" + MODEL_REVISION
)
LOWER_Q = 0.025
UPPER_Q = 0.975
CONTEXT_LENGTH = 2048
BATCH_SIZE = 100
SEED = 20260612


def configure_determinism() -> None:
    random.seed(SEED)
    np.random.seed(SEED)
    torch.manual_seed(SEED)
    torch.use_deterministic_algorithms(True, warn_only=True)


def _column(frame: pd.DataFrame, level: float) -> np.ndarray:
    candidates = (str(level), f"{level:g}")
    for name in candidates:
        if name in frame.columns:
            return frame[name].to_numpy(dtype="float64")
    raise KeyError(f"Chronos output lacks quantile {level}; columns={list(frame.columns)}")


def _univariate_input(train: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, tuple[str, str]]]:
    chunks = []
    identifiers: dict[str, tuple[str, str]] = {}
    for index, ((port, vessel_class), series) in enumerate(train.items()):
        item_id = f"series_{index:03d}"
        identifiers[item_id] = (str(port), str(vessel_class))
        chunks.append(
            pd.DataFrame(
                {
                    "item_id": item_id,
                    "timestamp": train.index,
                    "target": series.to_numpy(dtype="float32"),
                }
            )
        )
    return pd.concat(chunks, ignore_index=True), identifiers


def forecast_univariate(
    pipeline: Chronos2Pipeline,
    train: pd.DataFrame,
    horizon: int,
) -> dict[tuple[str, str], dict[str, np.ndarray]]:
    frame, identifiers = _univariate_input(train.tail(CONTEXT_LENGTH))
    output = pipeline.predict_df(
        frame,
        id_column="item_id",
        timestamp_column="timestamp",
        target="target",
        prediction_length=horizon,
        quantile_levels=[LOWER_Q, 0.5, UPPER_Q],
        batch_size=BATCH_SIZE,
        context_length=CONTEXT_LENGTH,
        cross_learning=False,
        freq="D",
    )
    result = {}
    for item_id, group in output.groupby("item_id", sort=False):
        group = group.sort_values("timestamp")
        result[identifiers[str(item_id)]] = {
            "point": group["predictions"].to_numpy(dtype="float64"),
            "lower": _column(group, LOWER_Q),
            "upper": _column(group, UPPER_Q),
        }
    return result


def _multivariate_input(train: pd.DataFrame) -> pd.DataFrame:
    chunks = []
    for port in sorted(train.columns.get_level_values("portname").unique()):
        values = train.xs(port, axis=1, level="portname").loc[:, list(EXPLICIT_CLASSES)]
        chunk = values.reset_index().rename(columns={"date": "timestamp"})
        chunk.insert(0, "item_id", str(port))
        chunks.append(chunk)
    return pd.concat(chunks, ignore_index=True)


def forecast_multivariate(
    pipeline: Chronos2Pipeline,
    train: pd.DataFrame,
    horizon: int,
) -> dict[tuple[str, str], dict[str, np.ndarray]]:
    frame = _multivariate_input(train.tail(CONTEXT_LENGTH))
    output = pipeline.predict_df(
        frame,
        id_column="item_id",
        timestamp_column="timestamp",
        target=list(EXPLICIT_CLASSES),
        prediction_length=horizon,
        quantile_levels=[LOWER_Q, 0.5, UPPER_Q],
        batch_size=BATCH_SIZE,
        context_length=CONTEXT_LENGTH,
        cross_learning=False,
        freq="D",
    )
    result = {}
    for (item_id, target_name), group in output.groupby(["item_id", "target_name"], sort=False):
        group = group.sort_values("timestamp")
        result[(str(item_id), str(target_name))] = {
            "point": group["predictions"].to_numpy(dtype="float64"),
            "lower": _column(group, LOWER_Q),
            "upper": _column(group, UPPER_Q),
        }
    return result


def evaluate_specification(
    pipeline: Chronos2Pipeline,
    panel_name: str,
    wide: pd.DataFrame,
    specification: str,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    groups = port_groups(wide.columns)
    daily_chunks: list[pd.DataFrame] = []
    score_rows: list[dict] = []
    for fold in folds(wide.index):
        train = wide.loc[wide.index < fold.origin]
        future = wide.loc[fold.test_dates]
        print(
            f"Chronos specification={specification} panel={panel_name} {fold.name} "
            f"origin={fold.origin.date()} horizon={fold.horizon}",
            flush=True,
        )
        if specification == "univariate":
            forecasts = forecast_univariate(pipeline, train, fold.horizon)
            model_name = "chronos2_univariate"
        elif specification == "multivariate_5class":
            forecasts = forecast_multivariate(pipeline, train, fold.horizon)
            model_name = "chronos2_multivariate_5class"
        else:
            raise ValueError(f"Unknown Chronos specification {specification!r}.")

        for column_index, (port, vessel_class) in enumerate(wide.columns):
            forecast = forecasts[(str(port), str(vessel_class))]
            scale = mase_scale(train.iloc[:, column_index].to_numpy(dtype="float64"))
            point = np.maximum(0.0, forecast["point"])
            lower = np.maximum(0.0, forecast["lower"])
            upper = np.maximum(lower, forecast["upper"])
            chunk = _daily_chunk(
                model=model_name,
                league="past_only_forecast",
                panel_name=panel_name,
                fold_name=fold.name,
                horizon=fold.horizon,
                origin=fold.origin,
                port=str(port),
                vessel_class=str(vessel_class),
                mask_group=groups[str(port)],
                dates=fold.test_dates,
                actual=future.iloc[:, column_index].to_numpy(dtype="float64"),
                prediction=point,
                scale=scale,
                diagnostics=(
                    f"model_revision={MODEL_REVISION};context_length={min(len(train), CONTEXT_LENGTH)};"
                    f"native_interval={UPPER_Q - LOWER_Q:.3f};cross_learning=false"
                ),
            )
            chunk["native_lower"] = lower
            chunk["native_upper"] = upper
            chunk["native_covered"] = (
                (chunk["y_true"] >= chunk["native_lower"])
                & (chunk["y_true"] <= chunk["native_upper"])
            )
            # pandas 2.1.4 in the benchmark environment cannot concatenate its
            # datetime extension blocks when chunks have 30 vs 130 rows. ISO
            # strings are lossless here and parsed back by the summarizer.
            chunk["origin"] = chunk["origin"].astype(str)
            chunk["date"] = chunk["date"].astype(str)
            daily_chunks.append(chunk)
            score = _score_chunk(chunk)
            score["native_nominal_coverage"] = UPPER_Q - LOWER_Q
            score["native_empirical_coverage"] = float(chunk["native_covered"].mean())
            score_rows.append(score)
    return pd.DataFrame(score_rows), pd.concat(daily_chunks, ignore_index=True)


def main() -> None:
    configure_determinism()
    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            f"Pinned Chronos-2 snapshot is not cached at {MODEL_PATH}; no network fallback is allowed."
        )
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    raw = load_raw_panel()
    composition = composition_wide(raw)
    total = total_wide(raw)
    pipeline = Chronos2Pipeline.from_pretrained(str(MODEL_PATH), device_map="cpu")

    results = []
    for panel_name, panel, specification in (
        ("composition_28x5", composition, "univariate"),
        ("composition_28x5", composition, "multivariate_5class"),
        # A one-target panel has no distinct multivariate formulation.
        ("total_28x1", total, "univariate"),
    ):
        result = evaluate_specification(pipeline, panel_name, panel, specification)
        checkpoint_stem = f"chronos_checkpoint__{panel_name}__{specification}"
        result[0].to_csv(OUTPUT_DIR / f"{checkpoint_stem}_scores.csv", index=False)
        result[1].to_csv(
            OUTPUT_DIR / f"{checkpoint_stem}_forecasts.csv.gz", index=False, compression="gzip"
        )
        results.append(result)
    scores = pd.concat([result[0] for result in results], ignore_index=True)
    daily = pd.concat([result[1] for result in results], ignore_index=True)
    scores.to_csv(OUTPUT_DIR / "chronos_scores.csv", index=False)
    daily.to_csv(OUTPUT_DIR / "chronos_forecasts.csv.gz", index=False, compression="gzip")
    manifest = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "raw_sha256": file_sha256(RAW_PATH),
        "model_snapshot": str(MODEL_PATH),
        "model_revision": MODEL_REVISION,
        "python": platform.python_version(),
        "numpy": np.__version__,
        "pandas": pd.__version__,
        "torch": torch.__version__,
        "chronos_forecasting": "2.3.0",
        "seed": SEED,
        "context_length": CONTEXT_LENGTH,
        "batch_size": BATCH_SIZE,
        "horizons": list(HORIZONS),
        "specifications": ["univariate", "within_chokepoint_multivariate_5class"],
        "cross_learning": False,
        "n_score_rows": len(scores),
        "n_daily_rows": len(daily),
    }
    (OUTPUT_DIR / "chronos_run_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"wrote {len(scores)} score rows and {len(daily)} daily Chronos rows")


if __name__ == "__main__":
    main()
