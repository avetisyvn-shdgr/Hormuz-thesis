"""Generate leakage-safe 130-day event forecasts for the complete 28 x 5 panel.

Run with the pinned Chronos environment:

    .venv-bench/bin/python -m experiments.network_adaptation.run_event_forecasts
"""
from __future__ import annotations

import json
import platform
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import torch
from chronos import Chronos2Pipeline

from experiments.network_adaptation.protocol import load_protocol
from experiments.panel_bakeoff.models import recursive_ar17
from experiments.panel_bakeoff.protocol import composition_wide, file_sha256, load_raw_panel
from experiments.panel_bakeoff.run_chronos import (
    BATCH_SIZE,
    CONTEXT_LENGTH,
    MODEL_PATH,
    MODEL_REVISION,
    configure_determinism,
    forecast_univariate,
)


def main() -> None:
    protocol = load_protocol()
    configure_determinism()
    if MODEL_REVISION != protocol.primary_revision or not MODEL_PATH.exists():
        raise RuntimeError("the pinned Chronos revision is unavailable or changed.")
    if CONTEXT_LENGTH != protocol.primary_context_length:
        raise RuntimeError("the Chronos context length differs from the frozen protocol.")
    if file_sha256(protocol.raw_path) != protocol.expected_raw_sha256:
        raise RuntimeError("the PortWatch snapshot hash changed.")

    panel = composition_wide(load_raw_panel(protocol.raw_path))
    train = panel.loc[panel.index < protocol.cutoff]
    dates = pd.date_range(protocol.cutoff, periods=protocol.horizon, freq="D")
    if not dates.isin(panel.index).all() or dates[-1] != protocol.event_end:
        raise RuntimeError("the complete 130-day event window is not available.")
    future = panel.loc[dates]

    pipeline = Chronos2Pipeline.from_pretrained(str(MODEL_PATH), device_map="cpu")
    chronos = forecast_univariate(pipeline, train, protocol.horizon)
    rows: list[pd.DataFrame] = []
    for port, vessel_class in panel.columns:
        actual = future[(port, vessel_class)].to_numpy(dtype="float64")
        forecast = chronos[(str(port), str(vessel_class))]
        chronos_point = np.maximum(0.0, forecast["point"])
        lower = np.maximum(0.0, forecast["lower"])
        upper = np.maximum(lower, forecast["upper"])
        ar_point = np.maximum(
            0.0,
            recursive_ar17(train[(port, vessel_class)].to_numpy(dtype="float64"), protocol.horizon),
        )
        common = {
            "portname": str(port),
            "vessel_class": str(vessel_class),
            "origin": protocol.cutoff,
            "date": dates,
            "lead": np.arange(1, protocol.horizon + 1),
            "y_true": actual,
        }
        rows.append(pd.DataFrame({
            "model": protocol.primary_model,
            **common,
            "y_pred": chronos_point,
            "native_lower": lower,
            "native_upper": upper,
        }))
        rows.append(pd.DataFrame({
            "model": protocol.robustness_model,
            **common,
            "y_pred": ar_point,
            "native_lower": np.nan,
            "native_upper": np.nan,
        }))

    output = pd.concat(rows, ignore_index=True).sort_values(
        ["model", "vessel_class", "portname", "date"], kind="stable"
    )
    expected_rows = 2 * 28 * 5 * protocol.horizon
    if len(output) != expected_rows or output.duplicated(
        ["model", "portname", "vessel_class", "date"]
    ).any():
        raise AssertionError("event forecast panel is incomplete or duplicated.")
    if output["date"].min() != protocol.cutoff or output["date"].max() != protocol.event_end:
        raise AssertionError("event forecast dates violate the frozen geometry.")

    output_path = protocol.outputs["event_forecasts"]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output.to_csv(output_path, index=False, compression="gzip")
    manifest = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": protocol.status,
        "raw_sha256": file_sha256(protocol.raw_path),
        "cutoff_exclusive": str(protocol.cutoff.date()),
        "event_end_inclusive": str(protocol.event_end.date()),
        "horizon_days": protocol.horizon,
        "training_end_inclusive": str(train.index.max().date()),
        "models": [protocol.primary_model, protocol.robustness_model],
        "chronos_revision": MODEL_REVISION,
        "chronos_context_length": CONTEXT_LENGTH,
        "chronos_batch_size": BATCH_SIZE,
        "chronos_cross_learning": False,
        "python": platform.python_version(),
        "numpy": np.__version__,
        "pandas": pd.__version__,
        "torch": torch.__version__,
        "n_rows": len(output),
        "n_unit_series": int(output.groupby(["portname", "vessel_class"]).ngroups),
        "interpretation_guard": protocol.claim,
    }
    protocol.outputs["event_manifest"].write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"wrote {len(output):,} event forecast rows to {output_path}")


if __name__ == "__main__":
    main()
