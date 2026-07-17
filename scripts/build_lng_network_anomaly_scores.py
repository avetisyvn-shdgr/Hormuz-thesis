"""Build exploratory LNG origin-portfolio anomaly scores.

Scores monthly importer-origin portfolios against pre-shock portfolio variation
using Jensen-Shannon distance. This is a descriptive graph anomaly diagnostic,
not causal identification and not a primary inference-family result.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lngfreight import config  # noqa: E402
from lngfreight.network_rewiring import (  # noqa: E402
    build_rewiring_network,
    graph_anomaly_scores,
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
    monthly, summary = graph_anomaly_scores(network)

    monthly_path = config.ROOT / paths["lng_network_anomaly_monthly_csv"]
    summary_path = config.ROOT / paths["lng_network_anomaly_summary_csv"]
    monthly_path.parent.mkdir(parents=True, exist_ok=True)
    monthly.to_csv(monthly_path, index=False)
    summary.to_csv(summary_path, index=False)

    print(f"wrote {monthly_path}")
    print(f"wrote {summary_path}")
    print(summary[[
        "destination_unit",
        "pre_calibration_months",
        "post_months",
        "post_max_js_distance",
        "post_max_zscore",
        "post_max_empirical_percentile",
        "anomaly_flag",
        "coverage_note",
    ]].to_string(index=False))


if __name__ == "__main__":
    main()
