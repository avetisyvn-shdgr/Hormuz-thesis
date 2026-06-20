"""Freeze the active ocean-going LNG carrier census from the GEM tracker."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lngfreight import config  # noqa: E402
from lngfreight.carrier_frame import build_global_carrier_frame  # noqa: E402


def main() -> None:
    settings = config.settings()
    policy = settings["vessel_data_feasibility"]["global_carrier_frame"]
    tracker = pd.read_json(config.ROOT / settings["paths"]["gem_carrier_json"])
    frame, diagnostics = build_global_carrier_frame(
        tracker,
        minimum_capacity_m3=float(policy["minimum_capacity_m3"]),
    )
    out = config.ROOT / settings["paths"]["global_carrier_frame_csv"]
    out.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(out, index=False)
    diagnostics_path = (
        config.path("data_processed") / "global_carrier_frame_diagnostics.json"
    )
    diagnostics_path.write_text(
        json.dumps(diagnostics, indent=2, sort_keys=True) + "\n"
    )
    print(f"wrote {out}")
    print(f"wrote {diagnostics_path}")
    print(json.dumps(diagnostics, sort_keys=True))


if __name__ == "__main__":
    main()
