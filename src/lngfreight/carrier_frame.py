"""Eligibility rules for the global replacement-supply carrier frame."""
from __future__ import annotations

import pandas as pd

from .feasibility import _valid_imo


ELIGIBLE_VESSEL_TYPES = {"conventional", "icebreaker"}


def build_global_carrier_frame(
    tracker: pd.DataFrame,
    *,
    minimum_capacity_m3: float,
) -> tuple[pd.DataFrame, dict]:
    frame = tracker.copy()
    frame["imo"] = frame["IMO number"].astype(str).str.replace(r"\.0$", "", regex=True)
    frame["capacity_m3"] = pd.to_numeric(frame["Capacity"], errors="coerce")
    frame["delivery_year"] = pd.to_numeric(
        frame["Delivery year"], errors="coerce"
    ).astype("Int64")
    frame["imo_valid"] = frame["imo"].map(_valid_imo)
    eligible = frame.loc[
        frame["Status"].eq("active")
        & frame["Vessel type"].isin(ELIGIBLE_VESSEL_TYPES)
        & frame["capacity_m3"].ge(minimum_capacity_m3)
        & frame["imo_valid"]
    ].copy()
    eligible["capacity_reference_missing"] = eligible["Capacity [ref]"].isna()
    eligible["source"] = eligible["IMO number [ref]"].fillna(
        "Global Energy Monitor LNG Carrier Tracker, December 2025"
    )
    output = eligible[[
        "imo", "Name", "capacity_m3", "Vessel type", "delivery_year",
        "Shipowner", "Propulsion type", "capacity_reference_missing", "source",
    ]].rename(columns={
        "Name": "vessel_name",
        "Vessel type": "vessel_type",
        "Shipowner": "shipowner",
        "Propulsion type": "propulsion_type",
    })
    output = output.sort_values("imo").reset_index(drop=True)
    diagnostics = {
        "tracker_rows": int(len(frame)),
        "active_rows": int(frame["Status"].eq("active").sum()),
        "eligible_rows": int(len(output)),
        "duplicate_imos": int(output["imo"].duplicated().sum()),
        "missing_capacity_references": int(
            output["capacity_reference_missing"].sum()
        ),
        "vessel_type_counts": output["vessel_type"].value_counts().to_dict(),
        "minimum_capacity_m3": float(minimum_capacity_m3),
    }
    return output, diagnostics
