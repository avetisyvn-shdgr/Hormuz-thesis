"""EIA Open Data API v2 provider.

Free, public-domain US government data. Covers Henry Hub spot and Brent spot,
which are the two energy confounders the proposal needs that have a genuine
free equivalent (status: free in the registry).

Register a key (instant, free): https://www.eia.gov/opendata/register.php
Then put it in .env as EIA_API_KEY=...
"""
from __future__ import annotations

import requests
import pandas as pd

from .base import BaseSource
from .. import config

_BASE = "https://api.eia.gov/v2/seriesid/{series_id}"


class EIASource(BaseSource):
    name = "eia"

    def fetch(self, code: str, start: str, end: str) -> pd.DataFrame:
        key = config.api_key("EIA_API_KEY")
        url = _BASE.format(series_id=code)
        params = {
            "api_key": key,
            "start": start,
            "end": end,
            "sort[0][column]": "period",
            "sort[0][direction]": "asc",
            "length": 5000,
        }
        resp = requests.get(url, params=params, timeout=60)
        resp.raise_for_status()
        payload = resp.json()

        rows = payload.get("response", {}).get("data", [])
        if not rows:
            raise ValueError(f"EIA returned no data for {code} in [{start}, {end}]")

        df = pd.DataFrame(rows)
        # EIA v2 returns 'period' (date) and 'value'; value can arrive as str.
        out = df[["period", "value"]].rename(columns={"period": "date"})
        out["value"] = pd.to_numeric(out["value"], errors="coerce")
        out["date"] = pd.to_datetime(out["date"])

        # OBSERVED 2026-06 (verify_sources.py run): the /v2/seriesid/ alias
        # IGNORED start/end and returned the most recent `length` rows
        # (requested 2022-01-01..2026-06-01, received 2006-08..2026-06-08,
        # row count == cap). Two consequences handled here:
        #   1. Window must be enforced client-side.
        #   2. If the capped payload does not reach back to the requested
        #      start, the pre-period is silently truncated -> fail loudly.
        capped = len(rows) >= params["length"]
        if capped and out["date"].min() > pd.Timestamp(start):
            raise ValueError(
                f"EIA row cap ({params['length']}) truncated {code}: earliest "
                f"returned obs {out['date'].min().date()} is after requested "
                f"start {start}. Paginate with `offset` before trusting this series."
            )
        mask = (out["date"] >= pd.Timestamp(start)) & (out["date"] <= pd.Timestamp(end))
        out = out.loc[mask]
        if out.empty:
            raise ValueError(f"EIA returned no data for {code} inside [{start}, {end}]")
        return self._validate(out)
