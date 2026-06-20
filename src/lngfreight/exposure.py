"""Importer and destination-basin exposure from inferred LNG voyages."""
from __future__ import annotations

import json
from typing import Any

import numpy as np
import pandas as pd

from .routes import RESOLVED_STATUS


def attach_exposure_metadata(
    voyages: pd.DataFrame,
    terminal_audit: pd.DataFrame,
    *,
    terminal_match_radius_km: int,
    gulf_export_project_ids: list[str],
    destination_basin_by_country: dict[str, str],
) -> pd.DataFrame:
    """Attach destination country/basin and Gulf-origin flags to resolved legs."""
    required = {
        "event_id", "imo", "sample_period", "project_id",
        "destination_project_id", "endpoint_status", "capacity_m3",
        "terminal_match_radius_km", "inferred_nominal_m3_nm_expanded",
        "route_passages",
    }
    missing = required.difference(voyages.columns)
    if missing:
        raise ValueError(f"Capacity voyages missing columns: {sorted(missing)}")
    audit_required = {"project_id", "country", "terminal_role"}
    audit_missing = audit_required.difference(terminal_audit.columns)
    if audit_missing:
        raise ValueError(f"Terminal audit missing columns: {sorted(audit_missing)}")

    resolved = voyages.loc[
        voyages["terminal_match_radius_km"].eq(terminal_match_radius_km)
        & voyages["endpoint_status"].eq(RESOLVED_STATUS)
    ].copy()
    destination_meta = terminal_audit.loc[
        terminal_audit["terminal_role"].eq("regasification"),
        ["project_id", "country"],
    ].drop_duplicates()
    if destination_meta["project_id"].duplicated().any():
        raise ValueError("Destination project maps to multiple countries.")
    resolved = resolved.merge(
        destination_meta.rename(columns={
            "project_id": "destination_project_id",
            "country": "destination_country",
        }),
        on="destination_project_id",
        how="left",
        validate="many_to_one",
    )
    if resolved["destination_country"].isna().any():
        raise ValueError("Resolved voyages contain missing destination countries.")
    resolved["destination_basin"] = resolved["destination_country"].map(
        destination_basin_by_country
    )
    unclassified = sorted(
        resolved.loc[resolved["destination_basin"].isna(), "destination_country"].unique()
    )
    if unclassified:
        raise ValueError(f"Unclassified destination countries: {unclassified}")
    resolved["inside_hormuz_origin"] = resolved["project_id"].isin(
        gulf_export_project_ids
    )
    if resolved["route_passages"].isna().any():
        raise ValueError("Resolved voyages contain missing modeled route passages.")
    crosses_hormuz = resolved["route_passages"].map(
        lambda value: "ormuz" in json.loads(value)
    )
    resolved["hormuz_exposed_leg"] = resolved["inside_hormuz_origin"] & crosses_hormuz
    resolved["origin_group"] = np.where(
        resolved["hormuz_exposed_leg"],
        "inside_hormuz_crossing",
        np.where(resolved["inside_hormuz_origin"], "inside_hormuz_non_crossing", "non_gulf"),
    )
    resolved["expanded_route_available"] = resolved[
        "inferred_nominal_m3_nm_expanded"
    ].notna()
    return resolved


def _pct_change(pre: float, post: float) -> float:
    return (post / pre - 1.0) * 100 if pre else np.nan


def exposure_summary(voyages: pd.DataFrame, group_column: str) -> pd.DataFrame:
    """Summarize total, Gulf, and non-Gulf exposure by importer or basin."""
    required = {
        group_column, "sample_period", "event_id", "imo", "capacity_m3",
        "inferred_nominal_m3_nm_expanded", "inside_hormuz_origin",
        "hormuz_exposed_leg",
    }
    missing = required.difference(voyages.columns)
    if missing:
        raise ValueError(f"Exposure voyages missing columns: {sorted(missing)}")
    rows: list[dict[str, Any]] = []
    for group_name, group in voyages.groupby(group_column, sort=True):
        row: dict[str, Any] = {group_column: group_name}
        for period in ("pre", "post"):
            period_frame = group.loc[group["sample_period"].eq(period)]
            exposed = period_frame.loc[period_frame["hormuz_exposed_leg"]]
            non_gulf = period_frame.loc[~period_frame["inside_hormuz_origin"]]
            intra_gulf = period_frame.loc[
                period_frame["inside_hormuz_origin"]
                & ~period_frame["hormuz_exposed_leg"]
            ]
            row.update({
                f"{period}_resolved_voyages": int(len(period_frame)),
                f"{period}_unique_imos": int(period_frame["imo"].nunique()),
                f"{period}_nominal_capacity_m3": float(period_frame["capacity_m3"].sum()),
                f"{period}_expanded_m3_nm": float(
                    period_frame["inferred_nominal_m3_nm_expanded"].sum(min_count=1)
                ),
                f"{period}_expanded_route_coverage_rate": float(
                    period_frame["inferred_nominal_m3_nm_expanded"].notna().mean()
                ) if len(period_frame) else np.nan,
                f"{period}_hormuz_exposed_voyages": int(len(exposed)),
                f"{period}_hormuz_exposed_nominal_capacity_m3": float(
                    exposed["capacity_m3"].sum()
                ),
                f"{period}_hormuz_exposed_expanded_m3_nm": float(
                    exposed["inferred_nominal_m3_nm_expanded"].sum(min_count=1)
                ),
                f"{period}_inside_hormuz_non_crossing_voyages": int(len(intra_gulf)),
                f"{period}_non_gulf_voyages": int(len(non_gulf)),
                f"{period}_non_gulf_nominal_capacity_m3": float(
                    non_gulf["capacity_m3"].sum()
                ),
                f"{period}_non_gulf_expanded_m3_nm": float(
                    non_gulf["inferred_nominal_m3_nm_expanded"].sum(min_count=1)
                ),
            })
        pre_total = row["pre_nominal_capacity_m3"]
        post_total = row["post_nominal_capacity_m3"]
        pre_exposed = row["pre_hormuz_exposed_nominal_capacity_m3"]
        post_exposed = row["post_hormuz_exposed_nominal_capacity_m3"]
        pre_non_gulf = row["pre_non_gulf_nominal_capacity_m3"]
        post_non_gulf = row["post_non_gulf_nominal_capacity_m3"]
        exposed_loss = max(pre_exposed - post_exposed, 0.0)
        non_gulf_gain = max(post_non_gulf - pre_non_gulf, 0.0)
        row.update({
            "pre_hormuz_exposure_capacity_share_pct": (
                pre_exposed / pre_total * 100 if pre_total else np.nan
            ),
            "total_capacity_percent_change": _pct_change(pre_total, post_total),
            "hormuz_exposed_capacity_absolute_change_m3": post_exposed - pre_exposed,
            "hormuz_exposed_capacity_percent_change": _pct_change(
                pre_exposed, post_exposed
            ),
            "non_gulf_capacity_absolute_change_m3": post_non_gulf - pre_non_gulf,
            "non_gulf_capacity_percent_change": _pct_change(pre_non_gulf, post_non_gulf),
            "descriptive_non_gulf_offset_ratio": (
                non_gulf_gain / exposed_loss if exposed_loss else np.nan
            ),
            "expanded_m3_nm_percent_change": _pct_change(
                row["pre_expanded_m3_nm"], row["post_expanded_m3_nm"]
            ),
        })
        rows.append(row)
    return pd.DataFrame(rows).sort_values(
        ["pre_hormuz_exposed_nominal_capacity_m3", group_column],
        ascending=[False, True]
    ).reset_index(drop=True)


def exposure_diagnostics(voyages: pd.DataFrame) -> dict[str, Any]:
    """Publish scope and coverage checks for the exposure tables."""
    by_period = {}
    for period, group in voyages.groupby("sample_period"):
        by_period[str(period)] = {
            "resolved_voyages": int(len(group)),
            "destination_countries": int(group["destination_country"].nunique()),
            "destination_basins": int(group["destination_basin"].nunique()),
            "inside_hormuz_origin_voyages": int(
                group["inside_hormuz_origin"].sum()
            ),
            "hormuz_exposed_voyages": int(group["hormuz_exposed_leg"].sum()),
            "expanded_route_coverage_rate": float(
                group["expanded_route_available"].mean()
            ),
        }
    return {
        "by_period": by_period,
        "missing_destination_country_rows": int(
            voyages["destination_country"].isna().sum()
        ),
        "unclassified_destination_basin_rows": int(
            voyages["destination_basin"].isna().sum()
        ),
        "measure": "inferred_nominal_capacity_exposure",
        "actual_import_volume_observed": False,
        "replacement_causality_supported": False,
        "warning": (
            "Non-Gulf post/pre changes are descriptive composition shifts, not "
            "identified replacement cargoes or importer demand effects."
        ),
    }
