"""FRED (St. Louis Fed) provider.

Used as a redundancy / cross-check source for Henry Hub (DHHNGSP) and Brent
(DCOILBRENTEU). Running the same economic series from two independent
providers is a cheap, strong data-quality check: if EIA and FRED disagree on
Henry Hub for a date, something is wrong and you want to know before modelling.

Register a key (free): https://fred.stlouisfed.org/docs/api/api_key.html
Then put it in .env as FRED_API_KEY=...
"""
from __future__ import annotations

import requests
import pandas as pd

from .base import BaseSource
from .. import config

_URL = "https://api.stlouisfed.org/fred/series/observations"


class FREDSource(BaseSource):
    name = "fred"

    def fetch(self, code: str, start: str, end: str) -> pd.DataFrame:
        key = config.api_key("FRED_API_KEY")
        params = {
            "series_id": code,
            "api_key": key,
            "file_type": "json",
            "observation_start": start,
            "observation_end": end,
        }
        resp = requests.get(_URL, params=params, timeout=60)
        resp.raise_for_status()
        obs = resp.json().get("observations", [])
        if not obs:
            raise ValueError(f"FRED returned no data for {code} in [{start}, {end}]")

        df = pd.DataFrame(obs)[["date", "value"]]
        df["value"] = pd.to_numeric(df["value"], errors="coerce")  # FRED uses '.' for missing
        return self._validate(df)
