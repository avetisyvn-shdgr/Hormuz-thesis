"""IMF PortWatch provider (chokepoint transits).

Free, AIS/satellite-derived transit estimates for 28 chokepoints, including
the Strait of Hormuz and the Panama Canal.

SCHEMA PINNED 2026-06-12 from the live CSV (md5 4728447a..., 76,020 data
rows): a BALANCED DAILY panel, 28 chokepoints x 2,715 days, 2019-01-01 ->
2026-06-07, no missing rows. The dataset is refreshed weekly but the data
frequency is DAILY (the Phase-1 stub wrongly implied weekly data).
Closure days appear as ZEROS, not gaps - zeros are data here.

Vessel classes: container, dry_bulk, general_cargo, roro, tanker, cargo,
total. There is NO LNG-carrier class: gas carriers sit inside `tanker`
together with oil/chemical tankers, so even n_tanker is a diluted measure.
Combined with the laden/ballast limitation (see registry note), PortWatch
remains a route-capacity covariate, not a ton-mile mechanism proxy.

INGESTION MODE: reads the manually downloaded snapshot at
settings paths.portwatch_csv. No public download URL is pinned yet (do not
guess one); the refresh procedure is documented in settings.yaml.

Registry `code` format (column choice is an explicit, documented decision -
there is NO default):
    chokepoint:<slug>:<column>
e.g. "chokepoint:strait_of_hormuz:n_tanker"
<slug> = portname lowercased, spaces -> underscores ("strait_of_hormuz").
<column> = one of the n_* / capacity_* columns below.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from .base import BaseSource, SourcePayload
from .. import config

# Pinned from the live file 2026-06-12. If PortWatch changes its schema the
# mismatch is detected and raised, never silently absorbed.
EXPECTED_COLUMNS = [
    "date", "year", "month", "day", "portid", "portname",
    "n_container", "n_dry_bulk", "n_general_cargo", "n_roro", "n_tanker",
    "n_cargo", "n_total",
    "capacity_container", "capacity_dry_bulk", "capacity_general_cargo",
    "capacity_roro", "capacity_tanker", "capacity_cargo", "capacity",
    "ObjectId",
]
VALUE_COLUMNS = [c for c in EXPECTED_COLUMNS
                 if c.startswith("n_") or c.startswith("capacity")]


def _slug(portname: str) -> str:
    return portname.strip().lower().replace(" ", "_").replace("-", "_")


class PortWatchSource(BaseSource):
    name = "portwatch"

    def _load(self) -> pd.DataFrame:
        csv_path = config.ROOT / config.settings()["paths"]["portwatch_csv"]
        if not Path(csv_path).exists():
            raise FileNotFoundError(
                f"PortWatch snapshot not found at {csv_path}. Download the "
                "'Daily Chokepoint Transit Calls' CSV from portwatch.imf.org "
                "and place it there (procedure in settings.yaml)."
            )
        df = pd.read_csv(csv_path, encoding="utf-8-sig")
        if list(df.columns) != EXPECTED_COLUMNS:
            raise ValueError(
                "PortWatch schema drift detected. Expected columns "
                f"{EXPECTED_COLUMNS}, got {list(df.columns)}. Re-pin the "
                "schema deliberately; do not ignore this."
            )
        return df

    def fetch(self, code: str, start: str, end: str) -> pd.DataFrame:
        parts = code.split(":")
        if len(parts) != 3 or parts[0] != "chokepoint":
            raise ValueError(
                f"PortWatch code {code!r} must be 'chokepoint:<slug>:<column>'. "
                "The column is an explicit methodological choice - no default. "
                f"Valid columns: {VALUE_COLUMNS}"
            )
        _, slug, column = parts
        if column not in VALUE_COLUMNS:
            raise ValueError(
                f"Unknown PortWatch column {column!r}. Valid: {VALUE_COLUMNS}"
            )

        df = self._load()
        source_path = config.ROOT / config.settings()["paths"]["portwatch_csv"]
        self._capture_source_payload(SourcePayload(
            filename=source_path.name,
            media_type="text/csv",
            path=source_path,
        ))
        match = df[df["portname"].map(_slug) == _slug(slug)]
        if match.empty:
            known = sorted(df["portname"].map(_slug).unique())
            raise ValueError(f"No chokepoint matching {slug!r}. Known: {known}")

        out = match[["date", column]].rename(columns={column: "value"})
        out["date"] = pd.to_datetime(out["date"], format="%Y/%m/%d")
        mask = (out["date"] >= pd.Timestamp(start)) & (out["date"] <= pd.Timestamp(end))
        out = out.loc[mask]
        if out.empty:
            raise ValueError(
                f"PortWatch snapshot has no rows for {slug!r} inside "
                f"[{start}, {end}] - snapshot may be stale (ends "
                f"{match['date'].max()}). Refresh per settings.yaml."
            )
        if out["date"].duplicated().any():
            raise ValueError(f"Duplicate dates for {slug!r} - inspect the snapshot.")
        return self._validate(out)
