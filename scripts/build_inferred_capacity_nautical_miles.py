"""Calculate nominal capacity-nautical miles with route/radius sensitivities."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lngfreight import config  # noqa: E402
from lngfreight.capacity_miles import (  # noqa: E402
    attach_capacity_nautical_miles,
    capacity_period_summary,
    capacity_pre_post_comparison,
    cluster_bootstrap_mean_change,
    route_shift_share_decomposition,
    validate_carrier_capacity_frame,
)
from lngfreight.routes import (  # noqa: E402
    build_route_distance_matrix,
    installed_searoute_version,
    route_distance_summary,
)
from lngfreight.voyages import candidate_voyage_endpoints  # noqa: E402


TERMINAL_COLUMNS = [
    "port_id", "terminal_name", "terminal_role", "country", "source",
    "project_id", "terminal_lat", "terminal_lon", "distance_km",
    "capacity_mtpa",
]


def _terminal_subset(audit: pd.DataFrame, max_distance_km: int) -> pd.DataFrame:
    eligible = (
        audit["country_match"]
        & audit["capacity_mtpa"].ge(1.0)
        & audit["distance_km"].le(max_distance_km)
    )
    return audit.loc[eligible, TERMINAL_COLUMNS].copy()


def main() -> None:
    settings = config.settings()
    paths = settings["paths"]
    policy = settings["vessel_data_feasibility"]["route_distance"]
    engine_version = installed_searoute_version()
    if engine_version != str(policy["engine_version"]):
        raise RuntimeError(
            f"Configured searoute {policy['engine_version']}, installed {engine_version}."
        )

    visits = pd.read_csv(config.ROOT / paths["global_gfw_port_visits_csv"])
    identities = pd.read_csv(
        config.ROOT / paths["global_gfw_vessel_identity_csv"], dtype={"imo": str}
    )
    audit = pd.read_csv(config.ROOT / paths["global_terminal_matching_audit_csv"])
    carriers = pd.read_csv(
        config.ROOT / paths["global_carrier_frame_csv"], dtype={"imo": str}
    )
    carrier_diagnostics = validate_carrier_capacity_frame(carriers)

    radius_frames = []
    for radius in (10, 20, 30):
        voyages = candidate_voyage_endpoints(
            visits, identities, _terminal_subset(audit, radius)
        )
        voyages["terminal_match_radius_km"] = radius
        radius_frames.append(voyages)
    all_voyages = pd.concat(radius_frames, ignore_index=True)

    routes = build_route_distance_matrix(
        all_voyages,
        units=str(policy["units"]),
        restrictions=list(policy["restrictions"]),
        max_endpoint_snap_nm=float(policy["max_endpoint_snap_nm"]),
        expanded_max_endpoint_snap_nm=float(policy["expanded_max_endpoint_snap_nm"]),
        min_route_to_geodesic_ratio=float(policy["min_route_to_geodesic_ratio"]),
        review_route_to_geodesic_ratio=float(policy["review_route_to_geodesic_ratio"]),
        engine=str(policy["engine"]),
        engine_version=engine_version,
    )
    enriched = attach_capacity_nautical_miles(all_voyages, routes, carriers)
    period_summary = capacity_period_summary(enriched)
    comparison = capacity_pre_post_comparison(period_summary)
    primary = enriched.loc[
        enriched["terminal_match_radius_km"].eq(30)
        & enriched["inferred_nominal_m3_nm_expanded"].notna()
    ].copy()
    seed = int(settings["reproducibility"]["random_seed"])
    bootstrap = cluster_bootstrap_mean_change(
        primary,
        "inferred_nominal_m3_nm_expanded",
        n_draws=5000,
        seed=seed,
    )
    decomposition = route_shift_share_decomposition(
        primary,
        "inferred_nominal_m3_nm_expanded",
    )

    route_diagnostics = route_distance_summary(routes)
    diagnostics = {
        "carrier_frame": carrier_diagnostics,
        "route_matrix": route_diagnostics,
        "candidate_rows": int(len(enriched)),
        "missing_carrier_capacity_rows": int(enriched["capacity_m3"].isna().sum()),
        "missing_route_pair_rows": int(
            enriched["capacity_join_status"].eq("missing_route_pair").sum()
        ),
        "measure": "inferred_nominal_lng_capacity_cubic_meter_nautical_miles",
        "capacity_nautical_miles_calculated": True,
        "cargo_quantity_observed": False,
        "laden_state_observed": False,
        "sailed_route_observed": False,
        "causal_interpretation_supported": False,
        "warning": (
            "Pre/post changes combine voyage count, vessel mix, destination mix, "
            "terminal classification, and modeled distance. They are not an ATT."
        ),
    }
    outputs = {
        paths["maritime_route_distances_sensitivity_csv"]: routes,
        paths["inferred_capacity_nm_voyages_csv"]: enriched,
        paths["inferred_capacity_nm_period_summary_csv"]: period_summary,
        paths["inferred_capacity_nm_comparison_csv"]: comparison,
    }
    for relative_path, frame in outputs.items():
        output = config.ROOT / relative_path
        output.parent.mkdir(parents=True, exist_ok=True)
        frame.to_csv(output, index=False)
        print(f"wrote {output}")
    diagnostics_path = config.ROOT / paths["inferred_capacity_nm_diagnostics_json"]
    diagnostics_path.write_text(json.dumps(diagnostics, indent=2, sort_keys=True) + "\n")
    print(f"wrote {diagnostics_path}")
    for key, payload in (
        ("inferred_capacity_nm_bootstrap_json", bootstrap),
        ("inferred_capacity_nm_decomposition_json", decomposition),
    ):
        output = config.ROOT / paths[key]
        output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
        print(f"wrote {output}")
    print(comparison.to_string(index=False))


if __name__ == "__main__":
    main()
