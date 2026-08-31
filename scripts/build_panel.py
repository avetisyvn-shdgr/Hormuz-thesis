"""Step 3: assemble the free daily panel and print its coverage summary.

Writes the un-imputed panel to data/interim/panel_free.csv for inspection.
Persistence format (Parquet vs DB) is the step-5 decision; this CSV is a
temporary inspection artifact, not the final store.

Run from the repo root:
    python scripts/build_panel.py
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from hormuz_throughput import config           # noqa: E402
from hormuz_throughput.panel import (  # noqa: E402
    build_panel,
    build_panel_from_frozen_raw,
    coverage_summary,
)


def main(frozen_raw: bool = False) -> None:
    panel = build_panel_from_frozen_raw() if frozen_raw else build_panel()
    print(f"panel shape: {panel.shape}  "
          f"({panel.index.min().date()} -> {panel.index.max().date()}, calendar-daily)\n")
    print(coverage_summary(panel).to_string())

    out = config.path("data_interim") / "panel_free.csv"
    panel.to_csv(out)
    print(f"\nwrote {out}")

    print("\nSpot-check around the closure window (2026-02-26 .. 2026-03-04):")
    print(panel.loc["2026-02-26":"2026-03-04"].to_string())


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--frozen-raw",
        action="store_true",
        help="rebuild entirely from local provenance-pinned raw snapshots",
    )
    args = parser.parse_args()
    main(frozen_raw=args.frozen_raw)
