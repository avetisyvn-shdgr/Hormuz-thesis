"""Refresh the public WTO/AXSMarine LNG index snapshot and print its hash."""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lngfreight import config  # noqa: E402
from lngfreight.sources.wto_hormuz import EXPECTED_COLUMNS  # noqa: E402


URL = (
    "https://wtomais.blob.core.windows.net/strait-of-hormuz-tracker/"
    "voy_intake_index_lng_export.csv"
)


def main() -> None:
    response = requests.get(URL, timeout=60)
    response.raise_for_status()
    content = response.content
    frame = pd.read_csv(pd.io.common.BytesIO(content))
    if list(frame.columns) != EXPECTED_COLUMNS:
        raise ValueError(
            f"WTO LNG schema drift: expected {EXPECTED_COLUMNS}, got {list(frame.columns)}"
        )
    if frame.empty or frame.isna().any().any():
        raise ValueError("WTO LNG download is empty or contains missing values.")
    out = config.ROOT / config.settings()["paths"]["wto_hormuz_lng_csv"]
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(content)
    print(f"wrote {out}")
    print(f"rows={len(frame)} start={frame.iloc[0, 0]} end={frame.iloc[-1, 0]}")
    print(f"sha256={hashlib.sha256(content).hexdigest()}")


if __name__ == "__main__":
    main()
