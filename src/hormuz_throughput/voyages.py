"""Endpoint-sequence diagnostics for the vessel-data feasibility gate."""
from __future__ import annotations

import pandas as pd


def candidate_voyage_endpoints(
    visits: pd.DataFrame,
    identities: pd.DataFrame,
    terminals: pd.DataFrame,
) -> pd.DataFrame:
    """Pair each export call with the next distinct classified terminal call.

    This reconstructs port sequences only. It does not infer laden state, cargo
    quantity, sailed route, or causality.
    """
    events = visits.merge(identities, on="vessel_id", how="left").merge(
        terminals,
        on="port_id",
        how="left",
        suffixes=("_event", "_terminal"),
    )
    events = events.loc[events["project_id"].notna()].copy()
    events["start"] = pd.to_datetime(events["start"], utc=True)
    events["end"] = pd.to_datetime(events["end"], utc=True)
    events = events.sort_values(["imo", "sample_period", "start", "event_id"])
    events["previous_project_id"] = events.groupby(
        ["imo", "sample_period"]
    )["project_id"].shift()
    calls = events.loc[
        events["project_id"].ne(events["previous_project_id"])
    ].copy()
    grouped = calls.groupby(["imo", "sample_period"])
    for column in (
        "project_id", "terminal_name", "terminal_role", "terminal_lat",
        "terminal_lon", "start", "event_id",
    ):
        calls[f"destination_{column}"] = grouped[column].shift(-1)

    origins = calls.loc[calls["terminal_role"] == "liquefaction"].copy()
    origins["endpoint_status"] = "right_censored"
    has_destination = origins["destination_project_id"].notna()
    origins.loc[has_destination, "endpoint_status"] = "unresolved_role_sequence"
    origins.loc[
        origins["destination_terminal_role"] == "regasification", "endpoint_status"
    ] = "resolved_liquefaction_to_regasification"
    columns = [
        "imo", "sample_period", "event_id", "project_id", "terminal_name",
        "terminal_lat", "terminal_lon", "end", "destination_event_id",
        "destination_project_id", "destination_terminal_name",
        "destination_terminal_lat", "destination_terminal_lon",
        "destination_start", "destination_terminal_role", "endpoint_status",
    ]
    return origins[columns].reset_index(drop=True)


def endpoint_summary(voyages: pd.DataFrame, threshold: float) -> dict:
    scored = voyages.loc[voyages["endpoint_status"] != "right_censored"]
    resolved = scored["endpoint_status"].eq(
        "resolved_liquefaction_to_regasification"
    )
    rate = float(resolved.mean()) if len(scored) else 0.0
    by_period = {}
    for period, group in voyages.groupby("sample_period"):
        period_scored = group.loc[group["endpoint_status"] != "right_censored"]
        period_resolved = period_scored["endpoint_status"].eq(
            "resolved_liquefaction_to_regasification"
        )
        by_period[str(period)] = {
            "export_origin_calls": int(len(group)),
            "scorable_calls": int(len(period_scored)),
            "resolved_calls": int(period_resolved.sum()),
            "right_censored_calls": int(
                group["endpoint_status"].eq("right_censored").sum()
            ),
        }
    return {
        "scorable_export_origin_calls": int(len(scored)),
        "resolved_endpoint_calls": int(resolved.sum()),
        "endpoint_resolution_rate": rate,
        "passes_threshold": rate >= threshold,
        "by_period": by_period,
    }
