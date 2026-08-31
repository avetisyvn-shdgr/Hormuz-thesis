"""Build pre-declared LNG resilience-typology threshold sensitivity.

The artifact reruns the descriptive rule-based typology across the threshold
grid declared in src/hormuz_throughput/network_rewiring.py. It reports per-unit label
agreement with the headline typology; it does not tune or select thresholds.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from hormuz_throughput import config  # noqa: E402
from hormuz_throughput.network_rewiring import typology_threshold_sensitivity  # noqa: E402


def main() -> None:
    paths = config.settings()["paths"]
    summary = pd.read_csv(config.ROOT / paths["lng_rewiring_summary_csv"])
    graph = pd.read_csv(config.ROOT / paths["lng_rewiring_graph_metrics_csv"])
    sensitivity = typology_threshold_sensitivity(summary, graph)

    out = config.ROOT / paths["lng_typology_threshold_sensitivity_csv"]
    out.parent.mkdir(parents=True, exist_ok=True)
    sensitivity.to_csv(out, index=False)

    print(f"wrote {out}")
    print(sensitivity[[
        "destination_unit",
        "unit_grid_points",
        "unit_grid_agreement_count",
        "unit_grid_agreement_share",
    ]].drop_duplicates().to_string(index=False))


if __name__ == "__main__":
    main()
