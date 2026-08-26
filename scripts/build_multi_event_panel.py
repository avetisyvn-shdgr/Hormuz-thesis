"""Phase 1 — build the multi-event chokepoint panel and audit its coverage.

Reads `config/multi_event_propagation.yaml` and materialises the extended
chokepoint-day panel used by the SECONDARY propagation estimator.

This script does not touch `study_window` in settings.yaml, the locked
2026-02-28 cutoff, or the frozen corridor specification. It reads the PortWatch
snapshot only through `spatial.wide_chokepoint_panel`, which resolves via
`registry.get_variable` and logs provenance (CLAUDE.md rule 7).

Nothing here fits a model. It builds the panel and answers the Phase 1 gate
question: is the pre-2022 history usable, or does its definition differ?

Usage:
    python scripts/build_multi_event_panel.py
    python scripts/build_multi_event_panel.py --value-col n_container
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lngfreight import config                                 # noqa: E402
from lngfreight.spatial import wide_chokepoint_panel          # noqa: E402

SPEC_PATH = config.CONFIG_DIR / "multi_event_propagation.yaml"
JUMP_THRESHOLD = 0.60  # flag year-over-year moves beyond +/-60%
MIN_LEVEL_FOR_JUMP = 2.0  # ignore ratio noise on near-empty chokepoints


def load_spec(path: Path = SPEC_PATH) -> dict:
    spec = yaml.safe_load(path.read_text(encoding="utf-8"))
    if spec.get("version") != 1:
        raise ValueError(f"Unexpected spec version: {spec.get('version')!r}")
    held = [k for k, v in spec["events"].items() if v.get("role") == "HELD_OUT"]
    if held != ["hormuz"]:
        raise ValueError(f"Expected hormuz to be the only held-out event, got {held}")
    return spec


def build_panel(spec: dict, value_col: str) -> pd.DataFrame:
    win = spec["training_window"]
    panel = wide_chokepoint_panel(
        value_col=value_col, start=win["start"], end=win["end"]
    )
    expected = spec["panel"]["n_units"]
    if panel.shape[1] != expected:
        raise ValueError(f"Expected {expected} chokepoints, got {panel.shape[1]}.")
    return panel


def audit_coverage(panel: pd.DataFrame, spec: dict, value_col: str) -> dict:
    """Completeness, per-year density, and year-boundary level-shift screen."""
    years = panel.index.year
    per_year = {int(y): int((years == y).sum()) for y in sorted(set(years))}

    annual = panel.groupby(years).mean()
    jumps = []
    for cp in annual.columns:
        s = annual[cp]
        for a, b in zip(s.index[:-1], s.index[1:]):
            if b == int(panel.index[-1].year):
                continue  # final year is partial; ratio is not comparable
            prev, cur = float(s.loc[a]), float(s.loc[b])
            if prev < MIN_LEVEL_FOR_JUMP or prev == 0:
                continue
            change = cur / prev - 1.0
            if abs(change) > JUMP_THRESHOLD:
                jumps.append(
                    {
                        "chokepoint": cp,
                        "from_year": int(a),
                        "to_year": int(b),
                        "from_mean": round(prev, 2),
                        "to_mean": round(cur, 2),
                        "pct_change": round(change, 4),
                    }
                )

    return {
        "value_col": value_col,
        "window": {
            "start": str(panel.index[0].date()),
            "end": str(panel.index[-1].date()),
        },
        "n_chokepoints": int(panel.shape[1]),
        "n_days": int(panel.shape[0]),
        "days_per_year": per_year,
        "missing_cells": int(panel.isna().sum().sum()),
        "missing_by_chokepoint": {
            c: int(n) for c, n in panel.isna().sum().items() if n > 0
        },
        "year_over_year_jumps": jumps,
        "jump_threshold": JUMP_THRESHOLD,
        "annual_means": {
            str(y): {c: round(float(v), 3) for c, v in row.items()}
            for y, row in annual.iterrows()
        },
        "note": (
            "Flagged jumps are candidates for a definition change OR a real "
            "event. They must be adjudicated by hand against EVENT_CHRONOLOGY.md "
            "before the spec is frozen. A jump is not by itself a reason to "
            "discard a year."
        ),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--value-col", default=None, help="override the primary value column")
    args = ap.parse_args()

    spec = load_spec()
    value_col = args.value_col or spec["panel"]["primary_value_column"]
    if value_col not in spec["panel"]["value_columns"]:
        raise SystemExit(
            f"{value_col!r} is not in the spec's value_columns "
            f"{spec['panel']['value_columns']}."
        )

    panel = build_panel(spec, value_col)
    audit = audit_coverage(panel, spec, value_col)

    panel_path = Path(spec["panel"]["outputs"]["panel"])
    audit_path = Path(spec["panel"]["outputs"]["audit"])
    if value_col != spec["panel"]["primary_value_column"]:
        panel_path = panel_path.with_name(f"{panel_path.stem}__{value_col}.csv")
        audit_path = audit_path.with_name(f"{audit_path.stem}__{value_col}.json")

    panel_path.parent.mkdir(parents=True, exist_ok=True)
    panel.to_csv(panel_path)
    audit_path.write_text(json.dumps(audit, indent=2), encoding="utf-8")

    print(f"panel  -> {panel_path}  ({panel.shape[0]} days x {panel.shape[1]} chokepoints)")
    print(f"audit  -> {audit_path}")
    print(f"window : {audit['window']['start']} .. {audit['window']['end']}")
    print(f"missing cells: {audit['missing_cells']}")
    print(f"days per year: {audit['days_per_year']}")
    print(f"\nyear-over-year jumps beyond +/-{JUMP_THRESHOLD:.0%} "
          f"({len(audit['year_over_year_jumps'])}):")
    for j in audit["year_over_year_jumps"]:
        print(f"  {j['chokepoint']:<26} {j['from_year']}->{j['to_year']}: "
              f"{j['from_mean']:>6.1f} -> {j['to_mean']:>6.1f}  ({j['pct_change']:+.0%})")
    print("\nSTOP AND REPORT. Adjudicate each flagged jump against "
          "EVENT_CHRONOLOGY.md before freezing the spec or starting Phase 2.")


if __name__ == "__main__":
    main()
