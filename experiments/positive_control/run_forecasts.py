"""Forecast the Red Sea positive control under the current forecaster pair.

For each declared onset this generates, for both models:

* eight contiguous, disjoint 130-day out-of-sample origins ending the day
  before the onset, which supply the synchronized bootstrap's historical
  reference; and
* the 130-day event window opening at the onset itself.

Every origin trains strictly on observations before it, so no forecast sees its
own scoring window and the reference contains no post-onset information.

Forecasts are computed on the complete 28 x 5 panel so the geometry is
validated the same way the bake-off validates it, and the declared families are
subset on write.

Run with the pinned Chronos environment:

    .venv-bench/bin/python -m experiments.positive_control.run_forecasts
"""
from __future__ import annotations

import json
import platform
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import torch
from chronos import Chronos2Pipeline

from experiments.panel_bakeoff.models import recursive_ar17
from experiments.panel_bakeoff.protocol import (
    EXPLICIT_CLASSES,
    composition_wide,
    file_sha256,
    load_raw_panel,
)
from experiments.panel_bakeoff.run_chronos import (
    CONTEXT_LENGTH,
    MODEL_PATH,
    MODEL_REVISION,
    configure_determinism,
    forecast_univariate,
)
from experiments.positive_control.protocol import Onset, PositiveControlProtocol, load_protocol


COLUMNS = (
    "model", "onset", "origin_role", "portname", "vessel_class", "origin",
    "date", "lead", "y_true", "y_pred", "native_lower", "native_upper",
)


def _append_origin(
    buffers: dict[str, list],
    protocol: PositiveControlProtocol,
    pipeline: Chronos2Pipeline,
    panel: pd.DataFrame,
    onset: Onset,
    origin: pd.Timestamp,
    role: str,
) -> None:
    """Append one origin's forecasts for both models to the column buffers.

    Column buffers rather than a list of frames: this pandas build fails to
    concatenate several hundred small frames of this shape, and building one
    frame from contiguous arrays is both robust and faster.
    """
    train = panel.loc[panel.index < origin]
    dates = pd.date_range(origin, periods=protocol.horizon, freq="D")
    if not dates.isin(panel.index).all():
        raise RuntimeError(f"the {protocol.horizon}-day window at {origin.date()} is incomplete.")
    if len(train) < 400:
        raise RuntimeError(f"origin {origin.date()} has too little training history.")
    future = panel.loc[dates]
    chronos = forecast_univariate(pipeline, train, protocol.horizon)
    horizon = protocol.horizon
    leads = np.arange(1, horizon + 1)
    nan = np.full(horizon, np.nan)

    for port, vessel_class in protocol.all_keys:
        actual = future[(port, vessel_class)].to_numpy(dtype="float64")
        forecast = chronos[(port, vessel_class)]
        lower = np.maximum(0.0, forecast["lower"])
        ar_point = np.maximum(
            0.0,
            recursive_ar17(
                train[(port, vessel_class)].to_numpy(dtype="float64"), horizon
            ),
        )
        for model, point, low, high in (
            (
                protocol.primary_model,
                np.maximum(0.0, forecast["point"]),
                lower,
                np.maximum(lower, forecast["upper"]),
            ),
            (protocol.robustness_model, ar_point, nan, nan),
        ):
            buffers["model"].append(np.repeat(model, horizon))
            buffers["onset"].append(np.repeat(onset.name, horizon))
            buffers["origin_role"].append(np.repeat(role, horizon))
            buffers["portname"].append(np.repeat(port, horizon))
            buffers["vessel_class"].append(np.repeat(vessel_class, horizon))
            buffers["origin"].append(np.repeat(origin.to_datetime64(), horizon))
            buffers["date"].append(dates.to_numpy())
            buffers["lead"].append(leads)
            buffers["y_true"].append(actual)
            buffers["y_pred"].append(point)
            buffers["native_lower"].append(low)
            buffers["native_upper"].append(high)


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
    if panel.shape[1] != 28 * len(EXPLICIT_CLASSES):
        raise RuntimeError("the composition panel is not 28 x 5.")
    pipeline = Chronos2Pipeline.from_pretrained(str(MODEL_PATH), device_map="cpu")

    buffers: dict[str, list] = {name: [] for name in COLUMNS}
    geometry: list[dict[str, object]] = []
    for onset in protocol.onsets:
        origins = [
            *((origin, "reference") for origin in protocol.reference_origins_for(onset)),
            (onset.date, "event"),
        ]
        for origin, role in origins:
            _append_origin(buffers, protocol, pipeline, panel, onset, origin, role)
        geometry.append({
            "onset": onset.name,
            "onset_date": str(onset.date.date()),
            "event_end": str(onset.event_end.date()),
            "reference_start": str(protocol.reference_start(onset).date()),
            "reference_end": str((onset.date - pd.Timedelta(days=1)).date()),
            "reference_origins": [str(origin.date()) for origin in protocol.reference_origins_for(onset)],
        })

    output = pd.DataFrame(
        {name: np.concatenate(values) for name, values in buffers.items()},
        columns=list(COLUMNS),
    ).sort_values(
        ["onset", "model", "origin", "vessel_class", "portname", "date"], kind="stable"
    )
    expected = (
        len(protocol.onsets) * 2 * (protocol.reference_origins + 1)
        * len(protocol.all_keys) * protocol.horizon
    )
    if len(output) != expected:
        raise AssertionError(f"expected {expected} forecast rows, built {len(output)}.")
    if output.duplicated(["onset", "model", "origin", "portname", "vessel_class", "date"]).any():
        raise AssertionError("the positive-control forecast panel is duplicated.")
    if output[["y_true", "y_pred"]].isna().any().any():
        raise AssertionError("the forecast panel contains missing actuals or points.")
    reference = output.loc[output["origin_role"].eq("reference")]
    for onset in protocol.onsets:
        part = reference.loc[reference["onset"].eq(onset.name)]
        if part["date"].max() >= onset.date:
            raise AssertionError(f"the {onset.name} reference reaches its own onset.")

    path = protocol.outputs["event_forecasts"]
    path.parent.mkdir(parents=True, exist_ok=True)
    output.to_csv(path, index=False, compression="gzip")

    manifest = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": protocol.status,
        "designation": protocol.designation,
        "anchor": {
            "receiver": protocol.anchor_receiver,
            "emitter": protocol.anchor_emitter,
            "vessel_class": protocol.anchor_class,
        },
        "raw_sha256": file_sha256(protocol.raw_path),
        "models": [protocol.primary_model, protocol.robustness_model],
        "model_revision": MODEL_REVISION,
        "context_length": CONTEXT_LENGTH,
        "horizon_days": protocol.horizon,
        "series_persisted": [
            {"portname": port, "vessel_class": vessel_class}
            for port, vessel_class in protocol.all_keys
        ],
        "geometry": geometry,
        "rows": len(output),
        "forecast_sha256": file_sha256(path),
        "environment": {
            "python": platform.python_version(),
            "torch": torch.__version__,
            "numpy": np.__version__,
            "pandas": pd.__version__,
            "platform": platform.platform(),
        },
    }
    protocol.outputs["event_manifest"].write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"wrote {path} ({len(output):,} rows)")
    for item in geometry:
        print(
            f"  {item['onset']}: reference {item['reference_start']} to "
            f"{item['reference_end']}, event {item['onset_date']} to {item['event_end']}"
        )


if __name__ == "__main__":
    main()
