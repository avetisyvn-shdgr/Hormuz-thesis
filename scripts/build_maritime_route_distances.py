"""Build the audited maritime-distance matrix; do not calculate capacity-miles."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lngfreight import config  # noqa: E402
from lngfreight.routes import (  # noqa: E402
    build_route_distance_matrix,
    installed_searoute_version,
    route_distance_summary,
)


def main() -> None:
    settings = config.settings()
    paths = settings["paths"]
    policy = settings["vessel_data_feasibility"]["route_distance"]
    installed_version = installed_searoute_version()
    if installed_version != str(policy["engine_version"]):
        raise RuntimeError(
            f"Configured searoute {policy['engine_version']}, installed {installed_version}."
        )

    voyages = pd.read_csv(
        config.ROOT / paths["global_candidate_voyage_endpoints_csv"],
        dtype={"imo": str},
    )
    routes = build_route_distance_matrix(
        voyages,
        units=str(policy["units"]),
        restrictions=list(policy["restrictions"]),
        max_endpoint_snap_nm=float(policy["max_endpoint_snap_nm"]),
        expanded_max_endpoint_snap_nm=float(
            policy["expanded_max_endpoint_snap_nm"]
        ),
        min_route_to_geodesic_ratio=float(policy["min_route_to_geodesic_ratio"]),
        review_route_to_geodesic_ratio=float(policy["review_route_to_geodesic_ratio"]),
        engine=str(policy["engine"]),
        engine_version=installed_version,
    )
    summary = route_distance_summary(routes)
    summary["policy"] = policy

    route_path = config.ROOT / paths["maritime_route_distances_csv"]
    summary_path = config.ROOT / paths["maritime_route_distance_summary_json"]
    route_path.parent.mkdir(parents=True, exist_ok=True)
    routes.to_csv(route_path, index=False)
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(f"wrote {route_path}")
    print(f"wrote {summary_path}")
    print(
        f"accepted={summary['accepted_route_pairs']}/"
        f"{summary['unique_resolved_terminal_pairs']} "
        f"rate={summary['accepted_route_pair_rate']:.1%}"
    )
    print(
        f"expanded_accepted={summary['expanded_accepted_route_pairs']}/"
        f"{summary['unique_resolved_terminal_pairs']} "
        f"rate={summary['expanded_accepted_route_pair_rate']:.1%}"
    )


if __name__ == "__main__":
    main()
