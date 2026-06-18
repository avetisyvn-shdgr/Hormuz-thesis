"""Phase-1 smoke test: pull the FREE energy confounders and prove the pipeline
(registry -> provider -> provenance) works end to end.

Run from the repo root, with your EIA key in .env:
    python scripts/fetch_baseline.py

Deliberately limited to the variables that have a genuine free backend today
(status: free). Everything else is gated behind data-access decisions and is
intentionally NOT fetched here.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Make `src/` importable without installing the package.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lngfreight import config
from lngfreight.registry import get_variable

# Only variables whose status is "free" right now.
FREE_VARS = [
    name for name, spec in config.registry().items() if spec.get("status") == "free"
]


def main() -> None:
    print(f"Free variables available today: {FREE_VARS}\n")
    for name in FREE_VARS:
        try:
            df = get_variable(name)
            print(f"  OK  {name:24s} rows={len(df):5d}  "
                  f"{df['date'].min().date()} -> {df['date'].max().date()}")
        except Exception as exc:  # noqa: BLE001 - smoke test wants the message
            print(f"  XX  {name:24s} {type(exc).__name__}: {exc}")
    print(f"\nProvenance log: {config.settings()['paths']['provenance_log']}")


if __name__ == "__main__":
    main()
