"""Fetch equal seasonal port-visit windows for the global carrier census."""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from hormuz_throughput import config, provenance  # noqa: E402
from hormuz_throughput.registry import get_gfw_port_visits  # noqa: E402
from hormuz_throughput.sources.gfw import GFWClient, PORT_VISIT_DATASET  # noqa: E402


WINDOWS = {
    "pre": ("2025-02-28", "2025-06-02"),
    "post": ("2026-02-28", "2026-06-02"),
}


def main() -> None:
    settings = config.settings()
    identities = pd.read_csv(
        config.ROOT / settings["paths"]["global_gfw_vessel_identity_csv"],
        dtype={"imo": str},
    )
    client = GFWClient()
    visits = get_gfw_port_visits(
        identities["vessel_id"].tolist(), WINDOWS, client=client
    )
    out = provenance.save_raw(
        visits,
        provider="gfw",
        variable="gfw_global_port_visits",
        code=PORT_VISIT_DATASET,
        query={
            "windows": WINDOWS,
            "end_date_semantics": "exclusive",
            "eligible_fleet_census": int(identities["imo"].nunique()),
        },
        license_note="Global Fishing Watch API terms and attribution apply",
        filename="global_port_visits.csv",
        source_payloads=client.source_payloads,
    )
    print(f"wrote {out}")
    print(f"rows={len(visits)}")
    for period in WINDOWS:
        subset = visits.loc[visits["sample_period"] == period]
        print(
            f"{period}: visits={len(subset)} "
            f"vessel_ids={subset['vessel_id'].nunique()}"
        )


if __name__ == "__main__":
    main()
