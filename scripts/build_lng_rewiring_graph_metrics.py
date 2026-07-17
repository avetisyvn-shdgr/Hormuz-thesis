"""Build pre/post dynamic LNG network-rewiring graph metrics.

This compares each destination unit's average pre-period origin-share vector
with its available post-period vector. The output is descriptive mechanism
evidence: origin-portfolio movement, edge turnover, and non-Gulf offset, not
observed cargo matching or causal identification.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lngfreight import config  # noqa: E402
from lngfreight.network_rewiring import (  # noqa: E402
    build_rewiring_network,
    dynamic_network_graph_metrics,
)


def _load_or_build_network() -> pd.DataFrame:
    network_path = config.ROOT / config.settings()["paths"]["lng_rewiring_network_csv"]
    if network_path.exists():
        return pd.read_csv(network_path)
    probe_dir = config.path("data_raw") / "backup_pathway_probe_20260621"
    eurostat_path = config.ROOT / config.settings()["paths"]["eurostat_lng_eu27_by_partner_json"]
    return build_rewiring_network(probe_dir, config.path("importer_customs_dir"), eurostat_path)


def main() -> None:
    paths = config.settings()["paths"]
    network = _load_or_build_network()
    graph_metrics = dynamic_network_graph_metrics(network)

    out = config.ROOT / paths["lng_rewiring_graph_metrics_csv"]
    out.parent.mkdir(parents=True, exist_ok=True)
    graph_metrics.to_csv(out, index=False)

    print(f"wrote {out}")
    print(graph_metrics[[
        "destination_unit",
        "edge_turnover_rate",
        "jensen_shannon_distance",
        "new_origin_count",
        "dropped_origin_count",
        "non_gulf_offset_ratio",
        "coverage_note",
    ]].to_string(index=False))


if __name__ == "__main__":
    main()
