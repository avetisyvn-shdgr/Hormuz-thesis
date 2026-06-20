"""Build a provisional, auditable GFW-to-GEM LNG terminal crosswalk."""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lngfreight import config, provenance  # noqa: E402
from lngfreight.terminal_matching import (  # noqa: E402
    build_terminal_crosswalk,
    load_operating_terminals,
)


def main() -> None:
    settings = config.settings()
    paths = settings["paths"]
    policy = settings["vessel_data_feasibility"]
    visits = pd.read_csv(config.ROOT / paths["gfw_port_visits_csv"])
    gem_path = config.ROOT / paths["gem_lng_terminals_geojson"]
    terminals = load_operating_terminals(gem_path)
    crosswalk = build_terminal_crosswalk(
        visits,
        terminals,
        max_distance_km=float(policy["terminal_match_max_km"]),
        min_capacity_mtpa=float(policy["min_terminal_capacity_mtpa"]),
    )
    audit_path = config.path("data_processed") / "lng_terminal_matching_audit.csv"
    crosswalk.to_csv(audit_path, index=False)

    accepted = crosswalk.loc[
        crosswalk["match_status"] == "provisional_spatial_match",
        [
            "port_id", "terminal_name", "terminal_role", "country", "source",
            "project_id", "terminal_lat", "terminal_lon", "distance_km",
            "capacity_mtpa", "match_status",
        ],
    ]
    out = provenance.save_raw(
        accepted,
        provider="gem",
        variable="gfw_lng_terminal_crosswalk",
        code="GGIT-LNG-Terminals-2025-09",
        query={
            "max_distance_km": policy["terminal_match_max_km"],
            "min_capacity_mtpa": policy["min_terminal_capacity_mtpa"],
            "status": "operating",
            "country_concordance": True,
        },
        license_note="Global Energy Monitor GGIT, CC BY 4.0",
        filename="lng_terminals.csv",
    )
    print(f"wrote {out}")
    print(f"wrote {audit_path}")
    print(f"observed_ports={len(crosswalk)} provisional_matches={len(accepted)}")
    for threshold in (10, 20, 30):
        visits_covered = crosswalk.loc[
            (crosswalk["distance_km"] <= threshold)
            & crosswalk["country_match"]
            & crosswalk["capacity_mtpa"].ge(policy["min_terminal_capacity_mtpa"]),
            "visit_count",
        ].sum()
        print(f"within_{threshold}km_visits={int(visits_covered)}")


if __name__ == "__main__":
    main()
