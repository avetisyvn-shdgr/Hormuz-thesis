"""Refresh the public WTO/AXSMarine LNG index snapshot and log provenance."""
from __future__ import annotations

import hashlib
from io import BytesIO
import sys
from pathlib import Path

import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lngfreight import config, provenance  # noqa: E402
from lngfreight.sources.wto_hormuz import EXPECTED_COLUMNS  # noqa: E402


URL = (
    "https://wtomais.blob.core.windows.net/strait-of-hormuz-tracker/"
    "voy_intake_index_lng_export.csv"
)
VARIABLE = "wto_hormuz_lng_outbound_index"
CODE = "lng_outbound_volume_index"


def _normalized_series(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.rename(columns={
        "voy_load_date": "date",
        "voy_intake_index": "value",
    })
    out["date"] = pd.to_datetime(out["date"], format="%Y-%m-%d")
    if out["date"].duplicated().any():
        raise ValueError("Duplicate dates in WTO LNG download.")
    return out.sort_values("date").reset_index(drop=True)


def main() -> None:
    response = requests.get(URL, timeout=60)
    response.raise_for_status()
    content = response.content
    frame = pd.read_csv(BytesIO(content))
    if list(frame.columns) != EXPECTED_COLUMNS:
        raise ValueError(
            f"WTO LNG schema drift: expected {EXPECTED_COLUMNS}, got {list(frame.columns)}"
        )
    if frame.empty or frame.isna().any().any():
        raise ValueError("WTO LNG download is empty or contains missing values.")
    series = _normalized_series(frame)

    settings = config.settings()
    out = config.ROOT / settings["paths"]["wto_hormuz_lng_csv"]
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(content)
    spec = config.registry()[VARIABLE]
    backend = spec["primary"]
    provenance_path = provenance.save_raw(
        series,
        provider=backend["provider"],
        variable=VARIABLE,
        code=CODE,
        query={
            "start": settings["study_window"]["full_start"],
            "end": settings["study_window"]["full_end"],
            "channel": "primary",
            "role": spec["role"],
            "source_url": URL,
        },
        license_note=backend.get("license", "unspecified"),
    )
    print(f"wrote {out}")
    print(f"logged provenance snapshot {provenance_path}")
    print(
        f"rows={len(series)} "
        f"start={series['date'].min().date()} end={series['date'].max().date()}"
    )
    print(f"sha256={hashlib.sha256(content).hexdigest()}")


if __name__ == "__main__":
    main()
