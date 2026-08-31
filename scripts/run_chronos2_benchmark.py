"""Backward-compatible alias for the unified TSFM benchmark, Chronos-2 only.

The benchmark logic now lives in the shared, leakage-safe harness
(``src/hormuz_throughput/tsfm.py``) and the unified runner
(``scripts/run_tsfm_benchmark.py``), so all three foundation models share one
fold geometry and one scorer. This thin wrapper preserves the originally
documented command:

    python scripts/run_chronos2_benchmark.py --acknowledge-benchmark-only

Prefer ``scripts/run_tsfm_benchmark.py --model chronos2`` going forward.
"""
from __future__ import annotations

import runpy
import sys
from pathlib import Path


def main() -> None:
    argv = sys.argv[1:]
    if "--model" not in argv:
        argv = ["--model", "chronos2", *argv]
    sys.argv = [sys.argv[0], *argv]
    runpy.run_path(
        str(Path(__file__).resolve().with_name("run_tsfm_benchmark.py")),
        run_name="__main__",
    )


if __name__ == "__main__":
    main()
