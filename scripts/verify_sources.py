"""Phase-2, step 1: source confirmation.

For EVERY variable in config/sources.yaml, attempt a fetch over the full
study window via registry.get_variable() and report:

  - rows, actual vs requested date range (start/end shortfall in days)
  - NaN count after numeric coercion
  - longest calendar gap between consecutive observations, and where it is
  - weekday coverage (business-day vs 7-day series)
  - value min / median / max (units sanity check)

Variables whose backend is not implemented (Spark targets, TTF/JKM
settlement scrapers, AIS ton-miles, PortWatch stub) are EXPECTED to fail;
they are reported as known gaps, not papered over.

NOTE on the FRED cross-check planned for step 4: FRED's DHHNGSP and
DCOILBRENTEU are republished EIA series, not independent measurements.
The EIA-vs-FRED comparison therefore validates ingestion fidelity
(parsing, alignment, revision lag), NOT independent measurement agreement.

Run from the repo root with EIA_API_KEY in .env:
    python scripts/verify_sources.py
Paste the full output back before we move to step 2.
"""
from __future__ import annotations

import sys
import traceback
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lngfreight import config            # noqa: E402
from lngfreight.registry import get_variable  # noqa: E402

# Gaps longer than this (calendar days) are flagged. Business-day series
# legitimately gap 2-3 days over weekends and ~4 over long holidays.
GAP_FLAG_DAYS = 4

# Rough plausibility bands for units sanity. A value outside its band does
# not prove an error - it prompts a manual look. Bands are deliberately wide
# (2022 energy crisis included).
UNIT_BANDS = {
    # Upper bound raised 2026-06-14 after manual review. The frozen EIA series
    # records $30.72 on 2026-01-23, followed by $25.01 on 2026-01-26, $17.19 on
    # 2026-01-27, and $9.34 on 2026-01-28. Do not winsorise the 23 January peak:
    # it is a real pre-treatment observation, and contemporaneous EIA reporting
    # identifies severe winter weather as the late-January market context. See
    # docs/EVENT_CHRONOLOGY.md.
    "henry_hub_spot": (1.0, 60.0),     # USD/MMBtu
    "brent_spot": (40.0, 150.0),       # USD/bbl
}


def diagnose(name: str, df: pd.DataFrame, start: str, end: str) -> list[str]:
    lines: list[str] = []
    df = df.sort_values("date").reset_index(drop=True)
    dates = pd.to_datetime(df["date"])

    lines.append(f"rows={len(df)}  range {dates.min().date()} -> {dates.max().date()}")

    start_short = (dates.min() - pd.Timestamp(start)).days
    end_short = (pd.Timestamp(end) - dates.max()).days
    if start_short > 0:
        lines.append(f"START SHORTFALL: first obs {start_short} d after requested {start}")
    if end_short > 0:
        lines.append(f"END SHORTFALL: last obs {end_short} d before requested {end}")

    n_nan = int(df["value"].isna().sum())
    if n_nan:
        lines.append(f"NaN values after coercion: {n_nan}")

    if len(dates) > 1:
        diffs = dates.diff().dt.days.iloc[1:]
        gmax = int(diffs.max())
        gwhere = dates.iloc[int(diffs.idxmax())].date()
        flag = "  <-- FLAG" if gmax > GAP_FLAG_DAYS else ""
        lines.append(f"longest gap: {gmax} d (ending {gwhere}){flag}")
        n_big = int((diffs > GAP_FLAG_DAYS).sum())
        if n_big > 1:
            lines.append(f"gaps > {GAP_FLAG_DAYS} d: {n_big} occurrences")

    wd = dates.dt.dayofweek
    weekend_share = float((wd >= 5).mean())
    kind = "7-day series" if weekend_share > 0.05 else "business-day series"
    lines.append(f"weekday profile: {kind} (weekend share {weekend_share:.1%})")

    v = df["value"].dropna()
    if len(v):
        lines.append(f"values: min={v.min():.3f} med={v.median():.3f} max={v.max():.3f}")
        if name in UNIT_BANDS:
            lo, hi = UNIT_BANDS[name]
            n_out = int(((v < lo) | (v > hi)).sum())
            if n_out:
                lines.append(f"UNITS CHECK: {n_out} obs outside plausibility band [{lo}, {hi}]  <-- FLAG")
            else:
                lines.append(f"units check: all obs within [{lo}, {hi}] OK")
    return lines


def main() -> None:
    win = config.settings()["study_window"]
    start, end = win["full_start"], win["full_end"]
    reg = config.registry()

    print(f"Study window: {start} -> {end}")
    print(f"Variables in registry: {len(reg)}\n")

    ok, gaps, errors = [], [], []
    for name, spec in reg.items():
        status, role = spec.get("status"), spec.get("role")
        print(f"--- {name}  (role={role}, status={status})")
        try:
            df = get_variable(name, start, end)
            # Make proxy resolution VISIBLE: a status unavailable/proxy variable
            # that fetches via its proxy entry is NOT the real series.
            from lngfreight.registry import _resolve_entry
            backend, channel = _resolve_entry(spec)
            if channel == "proxy":
                print(f"    !! PROXY DATA: resolved via proxy -> {backend['provider']}:{backend['code']}")
                print(f"    !! note: {backend.get('note', 'none')}")
            for line in diagnose(name, df, start, end):
                print(f"    {line}")
            ok.append(name if channel == "primary" else f"{name} (PROXY)")
        except NotImplementedError as exc:
            print(f"    KNOWN GAP (no backend): {exc}")
            gaps.append(name)
        except Exception as exc:  # noqa: BLE001 - verification wants the message
            print(f"    ERROR {type(exc).__name__}: {exc}")
            traceback.print_exc(limit=2)
            errors.append(name)
        print()

    print("=" * 60)
    print(f"fetched OK     : {ok}")
    print(f"known gaps     : {gaps}")
    print(f"unexpected err : {errors}")
    print("\nKnown gaps are honest registry state, not bugs. Unexpected")
    print("errors must be resolved before panel assembly (step 3).")


if __name__ == "__main__":
    main()
