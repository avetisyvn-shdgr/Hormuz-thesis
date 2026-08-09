"""WTO/AXSMarine Strait of Hormuz LNG shipment index.

The public series is LNG-only and excludes LPG, but measures an indexed daily
outbound shipment volume (2025 average = 100), not carrier counts, tonnes, or
freight rates. The underlying voyage intelligence is produced by AXSMarine.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from .base import BaseSource, SourcePayload
from .. import config


EXPECTED_COLUMNS = ["voy_load_date", "voy_intake_index"]


class WTOHormuzLNGSource(BaseSource):
    name = "wto_hormuz_lng"

    def fetch(self, code: str, start: str, end: str) -> pd.DataFrame:
        if code != "lng_outbound_volume_index":
            raise ValueError("Only 'lng_outbound_volume_index' is supported.")
        path = config.ROOT / config.settings()["paths"]["wto_hormuz_lng_csv"]
        if not Path(path).exists():
            raise FileNotFoundError(
                f"WTO Hormuz LNG snapshot not found at {path}. "
                "Run scripts/fetch_wto_hormuz_lng.py."
            )
        self._capture_source_payload(SourcePayload(
            filename=path.name,
            media_type="text/csv",
            path=path,
        ))
        raw = pd.read_csv(path)
        if list(raw.columns) != EXPECTED_COLUMNS:
            raise ValueError(
                f"WTO Hormuz LNG schema drift: expected {EXPECTED_COLUMNS}, "
                f"got {list(raw.columns)}."
            )
        out = raw.rename(columns={
            "voy_load_date": "date",
            "voy_intake_index": "value",
        })
        out["date"] = pd.to_datetime(out["date"], format="%Y-%m-%d")
        mask = (out["date"] >= pd.Timestamp(start)) & (out["date"] <= pd.Timestamp(end))
        out = out.loc[mask]
        if out.empty:
            raise ValueError(f"No WTO Hormuz LNG rows inside [{start}, {end}].")
        if out["date"].duplicated().any():
            raise ValueError("Duplicate dates in WTO Hormuz LNG snapshot.")
        return self._validate(out)
