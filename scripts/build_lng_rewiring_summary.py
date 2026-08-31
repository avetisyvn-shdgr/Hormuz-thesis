"""Build monthly and pre/post LNG network-rewiring metrics.

Inputs are the frozen by-origin network edge list from
scripts/build_lng_rewiring_network.py. If the edge list is absent, it is rebuilt
from frozen snapshots first. Outputs are descriptive mechanism artifacts, not
causal estimates.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from hormuz_throughput import config  # noqa: E402
from hormuz_throughput.network_rewiring import (  # noqa: E402
    build_rewiring_network,
    monthly_rewiring_metrics,
    registered_rewiring_input_paths,
    rewiring_prepost_summary,
)


def _load_or_build_network() -> pd.DataFrame:
    network_path = config.ROOT / config.settings()["paths"]["lng_rewiring_network_csv"]
    if network_path.exists():
        return pd.read_csv(network_path)
    return build_rewiring_network(
        *registered_rewiring_input_paths("build_lng_rewiring_summary")
    )


def main() -> None:
    paths = config.settings()["paths"]
    network = _load_or_build_network()
    monthly = monthly_rewiring_metrics(network)
    summary = rewiring_prepost_summary(monthly)

    monthly_path = config.ROOT / paths["lng_rewiring_monthly_metrics_csv"]
    summary_path = config.ROOT / paths["lng_rewiring_summary_csv"]
    monthly_path.parent.mkdir(parents=True, exist_ok=True)
    monthly.to_csv(monthly_path, index=False)
    summary.to_csv(summary_path, index=False)

    print(f"wrote {monthly_path}")
    print(f"wrote {summary_path}")
    print(summary[[
        "destination_unit",
        "pre_months",
        "post_months",
        "edge_total_pct_change",
        "same_calendar_edge_total_pct_change",
        "gulf_share_change_pp",
        "same_calendar_gulf_share_change_pp",
        "source_hhi_change",
        "coverage_note",
    ]].to_string(index=False))


if __name__ == "__main__":
    main()
