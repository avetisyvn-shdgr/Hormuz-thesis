"""Synchronize physical, freight, and market-context evidence layers."""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


def _weekly_mean(
    frame: pd.DataFrame, date_column: str, value_columns: list[str]
) -> pd.DataFrame:
    data = frame.loc[:, [date_column, *value_columns]].copy()
    data[date_column] = pd.to_datetime(data[date_column], errors="raise")
    data["week_end"] = (
        data[date_column].dt.to_period("W-FRI").dt.end_time.dt.normalize()
    )
    return data.groupby("week_end", as_index=False)[value_columns].mean()


def build_freight_mechanism_integration(
    portwatch: pd.DataFrame,
    wto: pd.DataFrame,
    freight: pd.DataFrame,
    context: pd.DataFrame,
    *,
    first_post_week: str,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    """Create one post-event Friday-week panel with explicit evidence roles."""
    port = portwatch.loc[
        portwatch["target"].eq("hormuz_tanker_transits")
        & portwatch["model"].eq("ar_lag1_7")
    ].copy()
    if port.empty:
        raise ValueError("Missing locked PortWatch ar_lag1_7 transit rows")
    port["portwatch_throughput_shortfall"] = port["y_pred"] - port["y_true"]
    port = _weekly_mean(
        port,
        "date",
        ["y_true", "y_pred", "portwatch_throughput_shortfall"],
    ).rename(
        columns={
            "y_true": "portwatch_tanker_transits_observed_daily_mean",
            "y_pred": "portwatch_tanker_transits_counterfactual_daily_mean",
            "portwatch_throughput_shortfall": "portwatch_tanker_transits_shortfall_daily_mean",
        }
    )

    wto_weekly = _weekly_mean(
        wto,
        "date",
        ["observed_lng_volume_index", "ar_counterfactual"],
    ).rename(
        columns={
            "observed_lng_volume_index": "wto_lng_outbound_index_observed_daily_mean",
            "ar_counterfactual": "wto_lng_outbound_index_counterfactual_daily_mean",
        }
    )
    wto_weekly["wto_lng_outbound_index_shortfall_daily_mean"] = (
        wto_weekly["wto_lng_outbound_index_counterfactual_daily_mean"]
        - wto_weekly["wto_lng_outbound_index_observed_daily_mean"]
    )

    freight_wide = freight.pivot(
        index="week_end",
        columns="series",
        values=[
            "observed_usd_per_day",
            "counterfactual_usd_per_day",
            "deviation_usd_per_day",
        ],
    )
    freight_wide.columns = [f"{series}_{metric}" for metric, series in freight_wide.columns]
    freight_wide = freight_wide.reset_index()
    freight_wide["week_end"] = pd.to_datetime(freight_wide["week_end"])

    context_weekly = _weekly_mean(
        context,
        "date",
        [
            "ttf_eur_per_mwh",
            "vlsfo_singapore_usd_per_metric_tonne",
            "ttf_eur_per_mwh_pre_zscore",
            "vlsfo_singapore_usd_per_metric_tonne_pre_zscore",
        ],
    )
    panel = port.merge(wto_weekly, on="week_end", how="outer", validate="one_to_one")
    panel = panel.merge(freight_wide, on="week_end", how="outer", validate="one_to_one")
    panel = panel.merge(context_weekly, on="week_end", how="outer", validate="one_to_one")
    last_complete_freight_week = freight_wide["week_end"].max()
    panel = panel.loc[
        panel["week_end"].ge(pd.Timestamp(first_post_week))
        & panel["week_end"].le(last_complete_freight_week)
    ].sort_values("week_end")
    panel = panel.reset_index(drop=True)

    summary_specs = [
        ("physical_primary", "PortWatch tanker transits", "portwatch_tanker_transits_observed_daily_mean", "portwatch_tanker_transits_counterfactual_daily_mean", "transits/day", "counterfactual minus observed"),
        ("commodity_physical", "WTO LNG outbound volume index", "wto_lng_outbound_index_observed_daily_mean", "wto_lng_outbound_index_counterfactual_daily_mean", "index (2025 mean=100)", "counterfactual minus observed"),
        ("monetary_secondary", "East of Suez spot assessment", "east_spot_observed_usd_per_day", "east_spot_counterfactual_usd_per_day", "USD/day", "observed minus counterfactual"),
        ("monetary_secondary", "West of Suez spot assessment", "west_spot_observed_usd_per_day", "west_spot_counterfactual_usd_per_day", "USD/day", "observed minus counterfactual"),
        ("monetary_secondary", "One-year time-charter assessment", "one_year_charter_observed_usd_per_day", "one_year_charter_counterfactual_usd_per_day", "USD/day", "observed minus counterfactual"),
    ]
    rows: list[dict[str, Any]] = []
    for layer, measure, observed_col, counterfactual_col, unit, direction in summary_specs:
        valid = panel[[observed_col, counterfactual_col]].dropna()
        observed_mean = float(valid[observed_col].mean())
        counterfactual_mean = float(valid[counterfactual_col].mean())
        deviation = (
            counterfactual_mean - observed_mean
            if direction == "counterfactual minus observed"
            else observed_mean - counterfactual_mean
        )
        rows.append(
            {
                "evidence_layer": layer,
                "measure": measure,
                "observations": int(len(valid)),
                "observed_mean": observed_mean,
                "counterfactual_mean": counterfactual_mean,
                "directional_deviation": deviation,
                "deviation_definition": direction,
                "unit": unit,
                "identified_mediation": False,
            }
        )
    for measure, column, unit in [
        ("Netherlands TTF day-ahead", "ttf_eur_per_mwh", "EUR/MWh"),
        ("Singapore VLSFO", "vlsfo_singapore_usd_per_metric_tonne", "USD/metric tonne"),
    ]:
        values = panel[column].dropna()
        rows.append(
            {
                "evidence_layer": "market_context",
                "measure": measure,
                "observations": int(len(values)),
                "observed_mean": float(values.mean()),
                "counterfactual_mean": np.nan,
                "directional_deviation": np.nan,
                "deviation_definition": "context level only",
                "unit": unit,
                "identified_mediation": False,
            }
        )
    manifest = {
        "schema_version": 1,
        "first_post_week": first_post_week,
        "calendar": "Friday week-ending means; no cross-layer imputation",
        "layers": ["physical_primary", "commodity_physical", "monetary_secondary", "market_context"],
        "claim_boundary": (
            "Synchronized triangulation only. Correlated movements do not identify "
            "a mediated causal chain or a freight-rate ATT."
        ),
    }
    return panel, pd.DataFrame(rows), manifest
