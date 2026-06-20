"""Nominal LNG capacity-nautical miles from inferred terminal sequences."""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from .routes import PAIR_COLUMNS, RESOLVED_STATUS


def validate_carrier_capacity_frame(carriers: pd.DataFrame) -> dict[str, Any]:
    """Fail on ambiguous IMO joins or unusable nominal capacity values."""
    required = {"imo", "capacity_m3"}
    missing = required.difference(carriers.columns)
    if missing:
        raise ValueError(f"Carrier frame missing columns: {sorted(missing)}")
    if carriers["imo"].isna().any():
        raise ValueError("Carrier frame contains missing IMO values.")
    duplicates = carriers["imo"].astype(str).duplicated(keep=False)
    if duplicates.any():
        duplicate_imos = sorted(carriers.loc[duplicates, "imo"].astype(str).unique())
        raise ValueError(f"Carrier frame contains duplicate IMOs: {duplicate_imos[:10]}")
    capacity = pd.to_numeric(carriers["capacity_m3"], errors="coerce")
    invalid = capacity.isna() | capacity.le(0)
    if invalid.any():
        raise ValueError(f"Carrier frame contains {int(invalid.sum())} invalid capacities.")
    return {
        "carrier_rows": int(len(carriers)),
        "unique_imos": int(carriers["imo"].astype(str).nunique()),
        "invalid_capacity_rows": 0,
        "duplicate_imos": 0,
    }


def attach_capacity_nautical_miles(
    voyages: pd.DataFrame,
    routes: pd.DataFrame,
    carriers: pd.DataFrame,
) -> pd.DataFrame:
    """Join audited route and capacity data without dropping excluded voyages."""
    required_voyage = set(PAIR_COLUMNS + [
        "imo", "sample_period", "event_id", "endpoint_status",
        "terminal_match_radius_km",
    ])
    missing = required_voyage.difference(voyages.columns)
    if missing:
        raise ValueError(f"Voyages missing columns: {sorted(missing)}")
    required_route = set(PAIR_COLUMNS + [
        "modeled_terminal_to_terminal_nm", "route_status",
        "distance_accepted", "distance_accepted_expanded",
    ])
    missing_routes = required_route.difference(routes.columns)
    if missing_routes:
        raise ValueError(f"Routes missing columns: {sorted(missing_routes)}")

    validate_carrier_capacity_frame(carriers)
    output = voyages.copy()
    output["imo"] = output["imo"].astype(str)
    carrier_subset = carriers.copy()
    carrier_subset["imo"] = carrier_subset["imo"].astype(str)
    output = output.merge(
        carrier_subset[["imo", "capacity_m3", "capacity_reference_missing"]],
        on="imo",
        how="left",
        validate="many_to_one",
    )
    output = output.merge(
        routes[PAIR_COLUMNS + [
            "modeled_route_nm", "modeled_terminal_to_terminal_nm",
            "great_circle_nm", "origin_snap_nm", "destination_snap_nm",
            "route_to_geodesic_ratio", "route_passages", "route_status",
            "distance_accepted", "distance_accepted_expanded",
        ]],
        on=PAIR_COLUMNS,
        how="left",
        validate="many_to_one",
    )
    resolved = output["endpoint_status"].eq(RESOLVED_STATUS)
    strict_route = output["distance_accepted"].eq(True)
    expanded_route = output["distance_accepted_expanded"].eq(True)
    output["capacity_join_status"] = np.select(
        [
            output["capacity_m3"].isna(),
            ~resolved,
            output["route_status"].isna(),
            strict_route,
            expanded_route,
        ],
        [
            "missing_carrier_capacity",
            "endpoint_not_resolved",
            "missing_route_pair",
            "strict_route_accepted",
            "expanded_route_accepted",
        ],
        default="route_excluded",
    )
    strict = (
        resolved
        & output["capacity_m3"].notna()
        & strict_route
    )
    expanded = (
        resolved
        & output["capacity_m3"].notna()
        & expanded_route
    )
    product = output["capacity_m3"] * output["modeled_terminal_to_terminal_nm"]
    output["inferred_nominal_m3_nm_strict"] = product.where(strict)
    output["inferred_nominal_m3_nm_expanded"] = product.where(expanded)
    return output


def capacity_period_summary(voyages: pd.DataFrame) -> pd.DataFrame:
    """Summarize coverage and capacity-distance totals by radius and period."""
    rows: list[dict[str, Any]] = []
    for (radius, period), group in voyages.groupby(
        ["terminal_match_radius_km", "sample_period"], sort=True
    ):
        resolved = group["endpoint_status"].eq(RESOLVED_STATUS)
        right_censored = group["endpoint_status"].eq("right_censored")
        unresolved = ~(resolved | right_censored)
        strict = group["inferred_nominal_m3_nm_strict"].notna()
        expanded = group["inferred_nominal_m3_nm_expanded"].notna()
        rows.append({
            "terminal_match_radius_km": int(radius),
            "sample_period": str(period),
            "export_origin_calls": int(len(group)),
            "resolved_voyages": int(resolved.sum()),
            "right_censored_export_calls": int(right_censored.sum()),
            "unresolved_role_sequences": int(unresolved.sum()),
            "right_censoring_rate": float(right_censored.mean()),
            "unique_resolved_imos": int(group.loc[resolved, "imo"].nunique()),
            "strict_routed_voyages": int(strict.sum()),
            "expanded_routed_voyages": int(expanded.sum()),
            "strict_route_coverage_rate": (
                float(strict.sum() / resolved.sum()) if resolved.any() else 0.0
            ),
            "expanded_route_coverage_rate": (
                float(expanded.sum() / resolved.sum()) if resolved.any() else 0.0
            ),
            "strict_total_nominal_m3_nm": float(
                group["inferred_nominal_m3_nm_strict"].sum(min_count=1)
            ),
            "expanded_total_nominal_m3_nm": float(
                group["inferred_nominal_m3_nm_expanded"].sum(min_count=1)
            ),
            "strict_mean_nominal_m3_nm_per_voyage": float(
                group["inferred_nominal_m3_nm_strict"].mean()
            ),
            "expanded_mean_nominal_m3_nm_per_voyage": float(
                group["inferred_nominal_m3_nm_expanded"].mean()
            ),
        })
    return pd.DataFrame(rows)


def capacity_pre_post_comparison(period_summary: pd.DataFrame) -> pd.DataFrame:
    """Compare equal-window pre/post totals without attaching a causal label."""
    rows: list[dict[str, Any]] = []
    for radius, group in period_summary.groupby("terminal_match_radius_km"):
        indexed = group.set_index("sample_period")
        if not {"pre", "post"}.issubset(indexed.index):
            raise ValueError(f"Radius {radius} does not contain pre and post periods.")
        row: dict[str, Any] = {"terminal_match_radius_km": int(radius)}
        for specification in ("strict", "expanded"):
            total = f"{specification}_total_nominal_m3_nm"
            voyages = f"{specification}_routed_voyages"
            mean = f"{specification}_mean_nominal_m3_nm_per_voyage"
            pre_total = float(indexed.loc["pre", total])
            post_total = float(indexed.loc["post", total])
            pre_voyages = int(indexed.loc["pre", voyages])
            post_voyages = int(indexed.loc["post", voyages])
            pre_mean = float(indexed.loc["pre", mean])
            post_mean = float(indexed.loc["post", mean])
            row.update({
                f"{specification}_pre_total_nominal_m3_nm": pre_total,
                f"{specification}_post_total_nominal_m3_nm": post_total,
                f"{specification}_absolute_change_nominal_m3_nm": post_total - pre_total,
                f"{specification}_percent_change": (
                    (post_total / pre_total - 1.0) * 100 if pre_total else np.nan
                ),
                f"{specification}_pre_routed_voyages": pre_voyages,
                f"{specification}_post_routed_voyages": post_voyages,
                f"{specification}_routed_voyage_percent_change": (
                    (post_voyages / pre_voyages - 1.0) * 100
                    if pre_voyages else np.nan
                ),
                f"{specification}_pre_mean_nominal_m3_nm_per_voyage": pre_mean,
                f"{specification}_post_mean_nominal_m3_nm_per_voyage": post_mean,
                f"{specification}_mean_per_voyage_percent_change": (
                    (post_mean / pre_mean - 1.0) * 100 if pre_mean else np.nan
                ),
            })
        rows.append(row)
    return pd.DataFrame(rows).sort_values("terminal_match_radius_km").reset_index(drop=True)
