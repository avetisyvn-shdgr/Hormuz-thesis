"""Evaluate global LNG terminal-sequence feasibility and spatial sensitivity."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lngfreight import config  # noqa: E402
from lngfreight.registry import RegisteredArtifact, get_variable  # noqa: E402
from lngfreight.voyages import candidate_voyage_endpoints, endpoint_summary  # noqa: E402


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
    policy = settings["vessel_data_feasibility"]
    visits_artifact = get_variable(
        "global_gfw_port_visits_snapshot",
        query={"consumer": "run_global_voyage_feasibility"},
    )
    identities_artifact = get_variable(
        "global_gfw_identity_snapshot",
        query={"consumer": "run_global_voyage_feasibility"},
    )
    if not isinstance(visits_artifact, RegisteredArtifact) or not isinstance(
        identities_artifact, RegisteredArtifact
    ):
        raise TypeError("global voyage inputs must resolve as artifacts")
    visits = visits_artifact.read_csv()
    identities = identities_artifact.read_csv(dtype={"imo": str})
    audit = pd.read_csv(config.ROOT / paths["global_terminal_matching_audit_csv"])

    threshold = float(policy["min_terminal_endpoint_rate"])
    sensitivity = {}
    primary_voyages = None
    for distance_km in (10, 20, 30):
        terminals = _terminal_subset(audit, distance_km)
        voyages = candidate_voyage_endpoints(visits, identities, terminals)
        result = endpoint_summary(voyages, threshold)
        result["matched_ports"] = int(terminals["port_id"].nunique())
        sensitivity[str(distance_km)] = result
        if distance_km == int(policy["terminal_match_max_km"]):
            primary_voyages = voyages

    if primary_voyages is None:
        raise ValueError("Configured terminal distance must be one of 10, 20, or 30 km.")

    observed = visits[["vessel_id", "sample_period"]].drop_duplicates().merge(
        identities, on="vessel_id", how="left", validate="many_to_one"
    )
    imos_by_period = {
        str(period): int(group["imo"].nunique())
        for period, group in observed.groupby("sample_period")
    }
    observed_periods = observed.groupby("imo")["sample_period"].nunique()
    census_size = int(identities["imo"].nunique())

    summary = sensitivity[str(int(policy["terminal_match_max_km"]))].copy()
    summary.update({
        "verdict": "global_port_sequence_feasibility_passed_scope_limited",
        "eligible_fleet_census_imos": census_size,
        "observed_imos_by_period": imos_by_period,
        "imos_observed_in_both_periods": int(observed_periods.eq(2).sum()),
        "imos_observed_in_one_period": int(observed_periods.eq(1).sum()),
        "imos_observed_in_neither_period": census_size - int(len(observed_periods)),
        "terminal_distance_sensitivity_km": sensitivity,
        "measure_supported": "inferred_lng_capacity_nautical_miles_pending_route_method",
        "cargo_state_observed": False,
        "cargo_quantity_observed": False,
        "track_distance_observed": False,
        "causal_interpretation_supported": False,
        "scope_warning": (
            "Terminal calls are provisional spatial classifications. Export-to-import "
            "sequences do not prove laden state, cargo quantity, or the sailed route."
        ),
    })

    voyage_path = config.ROOT / paths["global_candidate_voyage_endpoints_csv"]
    summary_path = config.ROOT / paths["global_voyage_feasibility_summary_json"]
    voyage_path.parent.mkdir(parents=True, exist_ok=True)
    primary_voyages.to_csv(voyage_path, index=False)
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(f"wrote {voyage_path}")
    print(f"wrote {summary_path}")
    print(
        f"resolved={summary['resolved_endpoint_calls']}/"
        f"{summary['scorable_export_origin_calls']} "
        f"rate={summary['endpoint_resolution_rate']:.1%}"
    )
    print(f"fleet_coverage_pre={imos_by_period.get('pre', 0)}/{census_size}")
    print(f"fleet_coverage_post={imos_by_period.get('post', 0)}/{census_size}")


if __name__ == "__main__":
    main()
