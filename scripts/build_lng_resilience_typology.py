"""Build the descriptive LNG importer resilience typology.

The typology is rule-based because the feature table is small and coverage
differs by unit. It labels descriptive adaptation patterns; it is not a causal
resilience estimator and not an ML clustering result.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lngfreight import config  # noqa: E402
from lngfreight.network_rewiring import resilience_typology  # noqa: E402


def main() -> None:
    paths = config.settings()["paths"]
    summary = pd.read_csv(config.ROOT / paths["lng_rewiring_summary_csv"])
    graph = pd.read_csv(config.ROOT / paths["lng_rewiring_graph_metrics_csv"])
    typology = resilience_typology(summary, graph)

    out = config.ROOT / paths["lng_resilience_typology_csv"]
    out.parent.mkdir(parents=True, exist_ok=True)
    typology.to_csv(out, index=False)

    print(f"wrote {out}")
    print(typology[[
        "destination_unit",
        "primary_typology",
        "caution_flags",
        "evidence_strength",
        "pre_gulf_share",
        "non_gulf_offset_ratio",
    ]].to_string(index=False))


if __name__ == "__main__":
    main()
