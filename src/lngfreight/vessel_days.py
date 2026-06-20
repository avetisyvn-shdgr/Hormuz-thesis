"""Assumption-driven LNG sailing-day estimates and elapsed-time diagnostics."""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from .routes import RESOLVED_STATUS


def add_elapsed_time_diagnostics(
    voyages: pd.DataFrame,
    *,
    min_implied_speed_knots: float,
    max_implied_speed_knots: float,
) -> pd.DataFrame:
    """Diagnose endpoint elapsed time without treating it as sailing duration."""
    required = {
        "endpoint_status", "end", "destination_start",
        "modeled_terminal_to_terminal_nm",
    }
    missing = required.difference(voyages.columns)
    if missing:
        raise ValueError(f"Voyages missing columns: {sorted(missing)}")
    output = voyages.copy()
    departure = pd.to_datetime(output["end"], utc=True)
    arrival = pd.to_datetime(output["destination_start"], utc=True)
    output["endpoint_elapsed_days"] = (
        arrival - departure
    ).dt.total_seconds() / 86_400
    output["elapsed_implied_speed_knots"] = (
        output["modeled_terminal_to_terminal_nm"]
        / (output["endpoint_elapsed_days"] * 24)
    )
    resolved = output["endpoint_status"].eq(RESOLVED_STATUS)
    has_route = output["modeled_terminal_to_terminal_nm"].notna()
    elapsed = output["endpoint_elapsed_days"]
    speed = output["elapsed_implied_speed_knots"]
    output["elapsed_time_status"] = np.select(
        [
            ~resolved,
            ~has_route,
            elapsed.isna(),
            elapsed.le(0),
            speed.gt(max_implied_speed_knots),
            speed.lt(min_implied_speed_knots),
        ],
        [
            "endpoint_not_resolved",
            "modeled_route_unavailable",
            "elapsed_time_missing",
            "nonpositive_elapsed_time",
            "implied_speed_too_high",
            "extended_elapsed_time",
        ],
        default="plausible_elapsed_transit",
    )
    return output


def modeled_vessel_day_summary(
    voyages: pd.DataFrame,
    *,
    speeds_knots: list[float],
) -> pd.DataFrame:
    """Summarize modeled sailing and capacity-days by route QA specification."""
    if any(speed <= 0 for speed in speeds_knots):
        raise ValueError("All speed assumptions must be positive.")
    rows: list[dict[str, Any]] = []
    specifications = {
        "strict_30nm_snap": "distance_accepted",
        "expanded_60nm_snap": "distance_accepted_expanded",
    }
    resolved = voyages["endpoint_status"].eq(RESOLVED_STATUS)
    for (radius, period), group in voyages.groupby(
        ["terminal_match_radius_km", "sample_period"], sort=True
    ):
        for specification, accepted_column in specifications.items():
            accepted = resolved.loc[group.index] & group[accepted_column].eq(True)
            routed = group.loc[accepted].copy()
            for speed in speeds_knots:
                sailing_days = routed["modeled_terminal_to_terminal_nm"] / (speed * 24)
                capacity_days = routed["capacity_m3"] * sailing_days
                rows.append({
                    "terminal_match_radius_km": int(radius),
                    "sample_period": str(period),
                    "route_specification": specification,
                    "speed_knots": float(speed),
                    "resolved_voyages": int(resolved.loc[group.index].sum()),
                    "routed_voyages": int(len(routed)),
                    "route_coverage_rate": (
                        float(len(routed) / resolved.loc[group.index].sum())
                        if resolved.loc[group.index].any() else 0.0
                    ),
                    "total_modeled_sailing_vessel_days": float(sailing_days.sum()),
                    "mean_modeled_sailing_days_per_voyage": float(sailing_days.mean()),
                    "total_nominal_capacity_m3_days": float(capacity_days.sum()),
                    "mean_nominal_capacity_m3_days_per_voyage": float(
                        capacity_days.mean()
                    ),
                })
    return pd.DataFrame(rows)


def vessel_day_pre_post_comparison(summary: pd.DataFrame) -> pd.DataFrame:
    """Compare equal-window modeled totals and means without causal language."""
    keys = ["terminal_match_radius_km", "route_specification", "speed_knots"]
    rows: list[dict[str, Any]] = []
    for values, group in summary.groupby(keys, sort=True):
        indexed = group.set_index("sample_period")
        if not {"pre", "post"}.issubset(indexed.index):
            raise ValueError(f"Missing pre/post period for vessel-day cell {values}.")
        row = dict(zip(keys, values))
        for metric in (
            "routed_voyages",
            "total_modeled_sailing_vessel_days",
            "mean_modeled_sailing_days_per_voyage",
            "total_nominal_capacity_m3_days",
            "mean_nominal_capacity_m3_days_per_voyage",
        ):
            pre = float(indexed.loc["pre", metric])
            post = float(indexed.loc["post", metric])
            row[f"pre_{metric}"] = pre
            row[f"post_{metric}"] = post
            row[f"{metric}_percent_change"] = (
                (post / pre - 1.0) * 100 if pre else np.nan
            )
        post_voyages = row["post_routed_voyages"]
        row["descriptive_post_excess_sailing_days_vs_pre_mean"] = (
            row["post_total_modeled_sailing_vessel_days"]
            - post_voyages * row["pre_mean_modeled_sailing_days_per_voyage"]
        )
        row["descriptive_post_excess_capacity_m3_days_vs_pre_mean"] = (
            row["post_total_nominal_capacity_m3_days"]
            - post_voyages * row["pre_mean_nominal_capacity_m3_days_per_voyage"]
        )
        rows.append(row)
    return pd.DataFrame(rows)


def elapsed_time_diagnostics(
    voyages: pd.DataFrame,
    *,
    primary_radius_km: int,
) -> dict[str, Any]:
    """Summarize endpoint-time quality once at the primary terminal radius."""
    primary = voyages.loc[
        voyages["terminal_match_radius_km"].eq(primary_radius_km)
        & voyages["endpoint_status"].eq(RESOLVED_STATUS)
    ]
    by_period = {}
    for period, group in primary.groupby("sample_period"):
        by_period[str(period)] = {
            "resolved_voyages": int(len(group)),
            "median_endpoint_elapsed_days": float(group["endpoint_elapsed_days"].median()),
            "elapsed_time_status_counts": group["elapsed_time_status"].value_counts().to_dict(),
        }
    return {
        "by_period": by_period,
        "endpoint_elapsed_time_is_sailing_time": False,
        "modeled_sailing_days_include_waiting_or_port_time": False,
        "warning": (
            "Endpoint elapsed time can include waiting, storage, reloads, and missed "
            "calls. Speed-based vessel-days are assumptions, not observed AIS duration."
        ),
    }
