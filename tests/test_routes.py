import math

import pandas as pd
import pytest

from hormuz_throughput.routes import (
    build_route_distance_matrix,
    great_circle_nm,
    route_distance_summary,
)


def _voyages() -> pd.DataFrame:
    return pd.DataFrame({
        "project_id": ["export", "export", "export"],
        "terminal_name": ["Export"] * 3,
        "terminal_lat": [0.0] * 3,
        "terminal_lon": [0.0] * 3,
        "destination_project_id": ["import", "import", None],
        "destination_terminal_name": ["Import", "Import", None],
        "destination_terminal_lat": [0.0, 0.0, math.nan],
        "destination_terminal_lon": [10.0, 10.0, math.nan],
        "endpoint_status": [
            "resolved_liquefaction_to_regasification",
            "resolved_liquefaction_to_regasification",
            "right_censored",
        ],
    })


def test_great_circle_nm_matches_one_degree_at_equator():
    assert great_circle_nm(0, 0, 0, 1) == pytest.approx(60.04, rel=0.001)


def test_route_matrix_deduplicates_resolved_pairs_and_accepts_valid_route():
    def router(origin, destination, **kwargs):
        return {
            "distance_nm": 650.0,
            "route_start_lon": origin[0],
            "route_start_lat": origin[1],
            "route_end_lon": destination[0],
            "route_end_lat": destination[1],
            "passages": ["test_passage"],
        }

    routes = build_route_distance_matrix(
        _voyages(), router=router, engine_version="test"
    )
    assert len(routes) == 1
    assert bool(routes.loc[0, "distance_accepted"]) is True
    assert routes.loc[0, "route_status"] == "accepted_modeled_shortest_sea_route"
    assert routes.loc[0, "route_passages"] == '["test_passage"]'
    assert routes.loc[0, "modeled_terminal_to_terminal_nm"] == 650.0


def test_route_matrix_flags_large_network_snap_without_losing_distance():
    def router(origin, destination, **kwargs):
        return {
            "distance_nm": 600.0,
            "route_start_lon": 1.0,
            "route_start_lat": 0.0,
            "route_end_lon": destination[0],
            "route_end_lat": destination[1],
            "passages": [],
        }

    routes = build_route_distance_matrix(
        _voyages(), router=router, max_endpoint_snap_nm=30.0
    )
    assert bool(routes.loc[0, "distance_accepted"]) is False
    assert routes.loc[0, "route_status"] == (
        "endpoint_snap_exceeds_expanded_threshold"
    )
    assert routes.loc[0, "modeled_route_nm"] == 600.0


def test_route_matrix_retains_expanded_snap_as_sensitivity_only():
    def router(origin, destination, **kwargs):
        return {
            "distance_nm": 600.0,
            "route_start_lon": 0.75,
            "route_start_lat": 0.0,
            "route_end_lon": destination[0],
            "route_end_lat": destination[1],
            "passages": [],
        }

    routes = build_route_distance_matrix(_voyages(), router=router)
    assert bool(routes.loc[0, "distance_accepted"]) is False
    assert bool(routes.loc[0, "distance_accepted_expanded"]) is True
    assert routes.loc[0, "route_status"] == "accepted_expanded_endpoint_snap"


def test_route_summary_states_capacity_miles_are_not_yet_calculated():
    routes = pd.DataFrame({
        "distance_accepted": [True, False],
        "distance_accepted_expanded": [True, True],
        "route_status": ["accepted", "review"],
        "route_to_geodesic_ratio": [1.2, 4.0],
        "origin_snap_nm": [1.0, 2.0],
        "destination_snap_nm": [2.0, 3.0],
    })
    summary = route_distance_summary(routes)
    assert summary["accepted_route_pair_rate"] == 0.5
    assert summary["expanded_accepted_route_pair_rate"] == 1.0
    assert summary["capacity_nautical_miles_calculated"] is False
