"""Build the descriptive LNG importer-origin rewiring network edge list.

This writes one row per destination unit, source country, and month from frozen
by-origin snapshots. It is a descriptive mechanism artifact, not a causal
estimator and not observed cargo matching.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lngfreight import config  # noqa: E402
from lngfreight.network_rewiring import build_rewiring_network  # noqa: E402


def main() -> None:
    probe_dir = config.path("data_raw") / "backup_pathway_probe_20260621"
    customs_dir = config.path("importer_customs_dir")
    eurostat_path = config.ROOT / config.settings()["paths"][
        "eurostat_lng_eu27_by_partner_json"
    ]
    network = build_rewiring_network(probe_dir, customs_dir, eurostat_path)
    out = config.ROOT / config.settings()["paths"]["lng_rewiring_network_csv"]
    out.parent.mkdir(parents=True, exist_ok=True)
    network.to_csv(out, index=False)
    print(f"wrote {out}")
    print(
        f"rows={len(network)} "
        f"units={network['destination_unit'].nunique()} "
        f"months={network['period'].min()}..{network['period'].max()}"
    )
    print(
        network.groupby(["destination_unit", "unit_of_measure"], as_index=False)
        .agg(rows=("edge_value", "size"), origins=("origin_country", "nunique"))
        .to_string(index=False)
    )


if __name__ == "__main__":
    main()
