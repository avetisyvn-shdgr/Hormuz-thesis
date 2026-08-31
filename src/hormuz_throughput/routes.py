"""Reproducible modeled maritime distances for resolved terminal pairs."""
from __future__ import annotations

import json
import math
from importlib import metadata
from typing import Any, Callable

import pandas as pd


EARTH_RADIUS_NM = 3440.065
RESOLVED_STATUS = "resolved_liquefaction_to_regasification"
PAIR_COLUMNS = [
    "project_id",
    "terminal_name",
    "terminal_lat",
    "terminal_lon",
    "destination_project_id",
    "destination_terminal_name",
    "destination_terminal_lat",
    "destination_terminal_lon",
]


def great_circle_nm(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Return the spherical great-circle distance in nautical miles."""
    lat1_r, lon1_r, lat2_r, lon2_r = map(
        math.radians, (lat1, lon1, lat2, lon2)
    )
    dlat = lat2_r - lat1_r
    dlon = lon2_r - lon1_r
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1_r) * math.cos(lat2_r) * math.sin(dlon / 2) ** 2
    )
    return 2 * EARTH_RADIUS_NM * math.asin(math.sqrt(a))


def _valid_coordinates(lat: Any, lon: Any) -> bool:
    try:
        return math.isfinite(float(lat)) and math.isfinite(float(lon)) and (
            -90 <= float(lat) <= 90 and -180 <= float(lon) <= 180
        )
    except (TypeError, ValueError):
        return False


def _feature_value(feature: Any, key: str) -> Any:
    if isinstance(feature, dict):
        return feature[key]
    return getattr(feature, key)


def searoute_router(
    origin: tuple[float, float],
    destination: tuple[float, float],
    *,
    units: str,
    restrictions: list[str],
) -> dict[str, Any]:
    """Run the pinned searoute graph and return a plain route record."""
    import searoute as sr

    feature = sr.searoute(
        origin,
        destination,
        units=units,
        append_orig_dest=False,
        restrictions=restrictions,
        return_passages=True,
        backend="networkx",
        algorithm="dijkstra",
    )
    properties = _feature_value(feature, "properties")
    geometry = _feature_value(feature, "geometry")
    coordinates = _feature_value(geometry, "coordinates")
    if not coordinates:
        raise ValueError("Route engine returned no coordinates.")
    return {
        "distance_nm": float(properties["length"]),
        "route_start_lon": float(coordinates[0][0]),
        "route_start_lat": float(coordinates[0][1]),
        "route_end_lon": float(coordinates[-1][0]),
        "route_end_lat": float(coordinates[-1][1]),
        "coordinates": [
            [float(longitude), float(latitude)]
            for longitude, latitude in coordinates
        ],
        "passages": sorted(
            properties.get(
                "traversed_passages", properties.get("passages", [])
            )
            or []
        ),
    }


def build_route_distance_matrix(
    voyages: pd.DataFrame,
    *,
    router: Callable[..., dict[str, Any]] = searoute_router,
    units: str = "naut",
    restrictions: list[str] | None = None,
    max_endpoint_snap_nm: float = 30.0,
    expanded_max_endpoint_snap_nm: float = 60.0,
    min_route_to_geodesic_ratio: float = 0.95,
    review_route_to_geodesic_ratio: float = 3.0,
    engine: str = "searoute",
    engine_version: str | None = None,
) -> pd.DataFrame:
    """Route each unique resolved terminal pair and attach auditable QA fields."""
    restrictions = list(restrictions or ["northwest"])
    required = set(PAIR_COLUMNS + ["endpoint_status"])
    missing = required.difference(voyages.columns)
    if missing:
        raise ValueError(f"Voyage endpoints missing columns: {sorted(missing)}")

    pairs = (
        voyages.loc[voyages["endpoint_status"].eq(RESOLVED_STATUS), PAIR_COLUMNS]
        .drop_duplicates()
        .sort_values(["project_id", "destination_project_id"])
    )
    rows: list[dict[str, Any]] = []
    for pair in pairs.to_dict("records"):
        row = dict(pair)
        row.update({
            "route_engine": engine,
            "route_engine_version": engine_version,
            "route_units": units,
            "route_restrictions": json.dumps(restrictions, separators=(",", ":")),
            "modeled_route_nm": math.nan,
            "modeled_terminal_to_terminal_nm": math.nan,
            "great_circle_nm": math.nan,
            "route_to_geodesic_ratio": math.nan,
            "origin_snap_nm": math.nan,
            "destination_snap_nm": math.nan,
            "route_passages": "[]",
            "route_status": "routing_error",
            "distance_accepted": False,
            "distance_accepted_expanded": False,
            "route_error": "",
        })
        coords = (
            pair["terminal_lat"], pair["terminal_lon"],
            pair["destination_terminal_lat"], pair["destination_terminal_lon"],
        )
        if not (
            _valid_coordinates(coords[0], coords[1])
            and _valid_coordinates(coords[2], coords[3])
        ):
            row["route_status"] = "invalid_coordinates"
            rows.append(row)
            continue

        lat1, lon1, lat2, lon2 = map(float, coords)
        geodesic = great_circle_nm(lat1, lon1, lat2, lon2)
        row["great_circle_nm"] = geodesic
        try:
            route = router(
                (lon1, lat1),
                (lon2, lat2),
                units=units,
                restrictions=restrictions,
            )
            distance = float(route["distance_nm"])
            origin_snap = great_circle_nm(
                lat1, lon1, route["route_start_lat"], route["route_start_lon"]
            )
            destination_snap = great_circle_nm(
                lat2, lon2, route["route_end_lat"], route["route_end_lon"]
            )
            terminal_distance = distance + origin_snap + destination_snap
            ratio = terminal_distance / geodesic if geodesic > 0 else math.nan
            row.update({
                "modeled_route_nm": distance,
                "modeled_terminal_to_terminal_nm": terminal_distance,
                "route_to_geodesic_ratio": ratio,
                "origin_snap_nm": origin_snap,
                "destination_snap_nm": destination_snap,
                "route_passages": json.dumps(
                    route.get("passages", []), separators=(",", ":")
                ),
            })
            if not math.isfinite(distance) or distance <= 0:
                row["route_status"] = "nonpositive_route"
            elif not math.isfinite(ratio) or ratio < min_route_to_geodesic_ratio:
                row["route_status"] = "route_below_geodesic_tolerance"
            elif ratio > review_route_to_geodesic_ratio:
                row["route_status"] = "high_detour_requires_review"
            elif (
                origin_snap <= max_endpoint_snap_nm
                and destination_snap <= max_endpoint_snap_nm
            ):
                row["route_status"] = "accepted_modeled_shortest_sea_route"
                row["distance_accepted"] = True
                row["distance_accepted_expanded"] = True
            elif (
                origin_snap <= expanded_max_endpoint_snap_nm
                and destination_snap <= expanded_max_endpoint_snap_nm
            ):
                row["route_status"] = "accepted_expanded_endpoint_snap"
                row["distance_accepted_expanded"] = True
            else:
                row["route_status"] = "endpoint_snap_exceeds_expanded_threshold"
        except Exception as exc:
            row["route_error"] = f"{type(exc).__name__}: {exc}"
        rows.append(row)
    return pd.DataFrame(rows)


def installed_searoute_version() -> str:
    """Return the installed engine version for output provenance."""
    return metadata.version("searoute")


def route_distance_summary(routes: pd.DataFrame) -> dict[str, Any]:
    accepted = routes["distance_accepted"].astype(bool) if len(routes) else pd.Series(dtype=bool)
    expanded = (
        routes["distance_accepted_expanded"].astype(bool)
        if len(routes) else pd.Series(dtype=bool)
    )
    return {
        "unique_resolved_terminal_pairs": int(len(routes)),
        "accepted_route_pairs": int(accepted.sum()),
        "accepted_route_pair_rate": float(accepted.mean()) if len(routes) else 0.0,
        "expanded_accepted_route_pairs": int(expanded.sum()),
        "expanded_accepted_route_pair_rate": (
            float(expanded.mean()) if len(routes) else 0.0
        ),
        "route_status_counts": routes["route_status"].value_counts().to_dict(),
        "median_route_to_geodesic_ratio": (
            float(routes.loc[accepted, "route_to_geodesic_ratio"].median())
            if accepted.any() else None
        ),
        "max_origin_snap_nm": (
            float(routes["origin_snap_nm"].max()) if routes["origin_snap_nm"].notna().any()
            else None
        ),
        "max_destination_snap_nm": (
            float(routes["destination_snap_nm"].max())
            if routes["destination_snap_nm"].notna().any() else None
        ),
        "distance_interpretation": "modeled_shortest_navigable_sea_route",
        "observed_ais_track_distance": False,
        "capacity_nautical_miles_calculated": False,
    }
