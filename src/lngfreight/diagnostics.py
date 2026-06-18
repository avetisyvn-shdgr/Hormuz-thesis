"""Pure, machine-readable diagnostics for model inputs and information sets."""
from __future__ import annotations

import pandas as pd

from .specification import working_specification


def coverage_by_period(panel: pd.DataFrame, cutoff: str | pd.Timestamp) -> pd.DataFrame:
    """Return per-column pre/post coverage without modifying the panel."""
    cut = pd.Timestamp(cutoff)
    rows = []
    for column in panel.columns:
        series = panel[column]
        row = {"column": column}
        for label, mask in (
            ("pre", panel.index < cut),
            ("post", panel.index >= cut),
            ("all", pd.Series(True, index=panel.index)),
        ):
            part = series.loc[mask]
            n = int(len(part))
            non_null = int(part.notna().sum())
            row[f"{label}_rows"] = n
            row[f"{label}_non_null"] = non_null
            row[f"{label}_missing"] = n - non_null
            row[f"{label}_coverage"] = non_null / n if n else float("nan")
            row[f"{label}_zeros"] = int((part.dropna() == 0).sum())
        rows.append(row)
    return pd.DataFrame(rows)


def capacity_missingness(
    panel: pd.DataFrame,
    audit: pd.DataFrame,
    cutoff: str | pd.Timestamp,
) -> pd.DataFrame:
    """Attribute capacity NaNs to documented artifact masks where possible."""
    cut = pd.Timestamp(cutoff)
    audit = audit.copy()
    if not audit.empty:
        audit["date"] = pd.to_datetime(audit["date"])

    rows = []
    for capacity_col in [c for c in panel.columns if c.endswith("_capacity")]:
        transit_col = capacity_col.removesuffix("_capacity") + "_transits"
        for period, mask in (("pre", panel.index < cut), ("post", panel.index >= cut)):
            dates = panel.index[mask]
            missing_dates = panel.loc[dates, capacity_col].index[
                panel.loc[dates, capacity_col].isna()
            ]
            if audit.empty:
                masked_dates = pd.DatetimeIndex([])
            else:
                masked_dates = pd.DatetimeIndex(audit.loc[
                    (audit["column"] == capacity_col)
                    & (audit["reason"] == "artifact_masked")
                    & audit["date"].isin(dates),
                    "date",
                ])
            unexplained = missing_dates.difference(masked_dates)
            rows.append({
                "capacity_column": capacity_col,
                "transit_column": transit_col if transit_col in panel.columns else None,
                "period": period,
                "rows": int(len(dates)),
                "missing_capacity": int(len(missing_dates)),
                "audit_confirmed_artifact_masks": int(len(masked_dates)),
                "unexplained_missing_capacity": int(len(unexplained)),
                "coverage": float(panel.loc[dates, capacity_col].notna().mean()),
            })
    return pd.DataFrame(rows)


def model_information_sets() -> pd.DataFrame:
    """Declare whether post-period observed covariates enter each model."""
    spec = working_specification()
    return pd.DataFrame([
        {
            "model": "seasonal_naive_7d",
            "post_observed_covariates": "",
            "counterfactual_role": "unconditional_candidate",
        },
        {
            "model": "ar_lag1_7",
            "post_observed_covariates": "",
            "counterfactual_role": (
                "working_primary"
                if spec.primary_estimator == "ar_lag1_7"
                else "unconditional_candidate"
            ),
        },
        {
            "model": "arx_lag1_7_route",
            "post_observed_covariates": (
                "panama_tanker_transits,panama_tanker_capacity"
            ),
            "counterfactual_role": "conditional_sensitivity",
        },
        {
            "model": "arx_lag1_7_route_energy",
            "post_observed_covariates": (
                "panama_tanker_transits,panama_tanker_capacity,"
                "henry_hub_spot,brent_spot"
            ),
            "counterfactual_role": "conditional_sensitivity",
        },
    ])
