"""Fetch India monthly LNG imports by origin from DGCI&S Tradestat (meidb).

Source: https://tradestat.commerce.gov.in/meidb/commodity_wise_all_countries_import
(Ministry of Commerce & Industry Export Import Data Bank, monthly edition).

Design notes:
- HS 271111, calendar-year basis, one POST per (year, month, measure).
- A query for (year=Y, month=M) returns that month for BOTH Y-1 and Y, so
  querying all of 2025 plus 2026 H1 covers 2024-01 .. latest-2026 in one pass.
- Measures pulled: Quantity (ReportVal=2) and US $ Million (ReportVal=1).
- Output: one long CSV snapshot (period, country, measure, value) written to
  --outdir (default data/raw_staging/india_tradestat). Normalization into the
  frozen data/raw/importer_customs snapshot happens in a separate, documented
  step -- this script only captures the source payload faithfully.

This is a capture script in the spirit of scripts/fetch_wto_hormuz_lng.py:
run rarely, snapshot the result, freeze the hash. Not part of run_all.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

import pandas as pd
import requests


class _TableParser(HTMLParser):
    """Minimal stdlib parser: extracts every <table> as a list of text rows.

    Avoids an lxml/bs4 dependency; the Tradestat tables are plain
    <table><tr><td> markup with no nesting."""

    def __init__(self) -> None:
        super().__init__()
        self.tables: list[list[list[str]]] = []
        self._row: list[str] | None = None
        self._cell: list[str] | None = None

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag == "table":
            self.tables.append([])
        elif tag == "tr" and self.tables:
            self._row = []
        elif tag in ("td", "th") and self._row is not None:
            self._cell = []

    def handle_endtag(self, tag: str) -> None:
        if tag in ("td", "th") and self._cell is not None:
            assert self._row is not None
            self._row.append(" ".join("".join(self._cell).split()))
            self._cell = None
        elif tag == "tr" and self._row is not None:
            if self._row:
                self.tables[-1].append(self._row)
            self._row = None

    def handle_data(self, data: str) -> None:
        if self._cell is not None:
            self._cell.append(data)


def _tables_from_html(text: str) -> list[pd.DataFrame]:
    parser = _TableParser()
    parser.feed(text)
    frames = []
    for rows in parser.tables:
        if len(rows) < 2:
            continue
        header, *body = rows
        width = len(header)
        body = [r for r in body if len(r) == width]
        if body:
            frames.append(pd.DataFrame(body, columns=header))
    return frames

BASE_URL = "https://tradestat.commerce.gov.in/meidb/commodity_wise_all_countries_import"
HS_CODE = "271111"
MEASURES = {"quantity": "2", "usd_million": "1"}
CALENDAR_YEAR = "2"
UA = {
    "User-Agent": (
        "TUM-Hormuz-Throughput-Thesis/1.0 "
        "(non-commercial academic research; mher.avetisyan@tum.de)"
    )
}
MONTH_NAMES = {
    1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr", 5: "May", 6: "Jun",
    7: "Jul", 8: "Aug", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec",
}


def _fresh_token(session: requests.Session) -> str:
    page = session.get(BASE_URL, headers=UA, timeout=60)
    page.raise_for_status()
    match = re.search(r'name="_token" value="([^"]+)"', page.text)
    if not match:
        raise RuntimeError("CSRF token not found on Tradestat form page.")
    return match.group(1)


def _month_columns(frame: pd.DataFrame, month: int) -> dict[int, str]:
    """Map calendar year -> column name for the single-month columns.

    Tradestat headers look like 'May-2025' / 'May-2026' (single month) next to
    cumulative 'Jan-May2025' columns; only the single-month ones are wanted."""
    out: dict[int, str] = {}
    pattern = re.compile(rf"^{MONTH_NAMES[month]}\s*-\s*(\d{{4}})\s*(?:\([A-Z]\))?$")
    for col in map(str, frame.columns):
        m = pattern.match(col.strip())
        if m:
            out[int(m.group(1))] = col
    return out


def fetch_month(
    session: requests.Session, year: int, month: int, measure_code: str
) -> pd.DataFrame:
    token = _fresh_token(session)
    resp = session.post(
        BASE_URL,
        headers=UA,
        timeout=90,
        data={
            "_token": token,
            "cwacimHSCODE": HS_CODE,
            "cwacimMonth": str(month),
            "cwacimYear": str(year),
            "cwacimReportVal": measure_code,
            "cwacimReportYear": CALENDAR_YEAR,
        },
    )
    resp.raise_for_status()
    tables = _tables_from_html(resp.text)
    candidates = [t for t in tables if "Country" in map(str, t.columns)]
    if not candidates:
        raise RuntimeError(f"No country table for {year}-{month:02d}.")
    return candidates[0]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--outdir", default="data/raw_staging/india_tradestat", type=Path
    )
    parser.add_argument("--sleep", default=2.0, type=float)
    args = parser.parse_args()

    session = requests.Session()
    rows: list[dict] = []
    passes = [(2025, range(1, 13)), (2026, range(1, 7))]
    for measure_name, measure_code in MEASURES.items():
        for query_year, months in passes:
            for month in months:
                frame = fetch_month(session, query_year, month, measure_code)
                by_year = _month_columns(frame, month)
                for cal_year, col in by_year.items():
                    if query_year == 2026 and cal_year == 2025:
                        continue
                    for _, rec in frame.iterrows():
                        country = str(rec["Country"]).strip()
                        if not country or country.lower().startswith(("total", "nan")):
                            continue
                        value = pd.to_numeric(rec[col], errors="coerce")
                        if pd.isna(value):
                            continue
                        rows.append(
                            {
                                "period": f"{cal_year}.{month:02d}",
                                "country": country,
                                "measure": measure_name,
                                "value": float(value),
                            }
                        )
                print(
                    f"fetched {measure_name} {query_year}-{month:02d} "
                    f"(years in table: {sorted(by_year)})",
                    flush=True,
                )
                time.sleep(args.sleep)

    out = pd.DataFrame(rows).drop_duplicates(
        subset=["period", "country", "measure"], keep="last"
    )
    out = out.sort_values(["measure", "period", "country"]).reset_index(drop=True)
    args.outdir.mkdir(parents=True, exist_ok=True)
    out_path = args.outdir / "india_tradestat_lng271111_by_origin.csv"
    out.to_csv(out_path, index=False)
    digest = hashlib.sha256(out_path.read_bytes()).hexdigest()
    meta = {
        "retrieved_utc": datetime.now(timezone.utc).isoformat(),
        "source": "DGCI&S Tradestat meidb commodity_wise_all_countries_import",
        "hs_code": HS_CODE,
        "measures": list(MEASURES),
        "rows": int(len(out)),
        "period_range": [out["period"].min(), out["period"].max()],
        "n_countries": int(out["country"].nunique()),
        "sha256": digest,
    }
    (args.outdir / "india_tradestat_lng271111_by_origin.meta.json").write_text(
        json.dumps(meta, indent=2)
    )
    print(json.dumps(meta, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
