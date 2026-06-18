"""Step-1 follow-up: locate the two Henry Hub obs above 25 USD/MMBtu.

Prints each extreme observation (value > 25 or < 1.5) with 3 trading days
of context on each side, so we can judge: isolated bad tick (one-day spike
surrounded by normal values) vs genuine market episode (neighbors elevated
too). No data is modified; this is inspection only.

Run from the repo root:
    python scripts/inspect_hh_outliers.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lngfreight.registry import get_variable  # noqa: E402

HIGH, LOW = 25.0, 1.5
CONTEXT = 3  # trading days either side


def main() -> None:
    df = get_variable("henry_hub_spot").reset_index(drop=True)
    extreme_idx = df.index[(df["value"] > HIGH) | (df["value"] < LOW)]
    print(f"Henry Hub obs with value > {HIGH} or < {LOW}: {len(extreme_idx)}\n")

    for i in extreme_idx:
        lo, hi = max(0, i - CONTEXT), min(len(df) - 1, i + CONTEXT)
        print(f"--- extreme obs at {df.loc[i, 'date'].date()}  value={df.loc[i, 'value']}")
        for j in range(lo, hi + 1):
            marker = "  <-- " if j == i else "      "
            print(f"   {df.loc[j, 'date'].date()}  {df.loc[j, 'value']:8.3f}{marker}")
        print()


if __name__ == "__main__":
    main()
