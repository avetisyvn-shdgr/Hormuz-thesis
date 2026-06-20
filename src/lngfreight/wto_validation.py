"""Unscaled validation of inferred Gulf LNG departures against the WTO index."""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


def _safe_correlation(left: pd.Series, right: pd.Series, method: str) -> float:
    frame = pd.concat([left, right], axis=1).dropna()
    if len(frame) < 3 or frame.iloc[:, 0].nunique() < 2 or frame.iloc[:, 1].nunique() < 2:
        return np.nan
    if method == "pearson":
        return float(frame.iloc[:, 0].corr(frame.iloc[:, 1]))
    if method == "spearman":
        return float(frame.iloc[:, 0].rank().corr(frame.iloc[:, 1].rank()))
    raise ValueError(f"Unknown correlation method: {method}")


def build_gulf_departure_daily(
    voyages: pd.DataFrame,
    wto_index: pd.DataFrame,
    *,
    gulf_export_project_ids: list[str],
    terminal_match_radius_km: int,
    comparison_windows: dict[str, list[str]],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Create daily unscaled departure/count series and a terminal audit."""
    required = {
        "event_id", "sample_period", "project_id", "terminal_name", "end",
        "capacity_m3", "terminal_match_radius_km", "endpoint_status",
        "distance_accepted_expanded",
    }
    missing = required.difference(voyages.columns)
    if missing:
        raise ValueError(f"Capacity voyages missing columns: {sorted(missing)}")
    if set(wto_index.columns) != {"date", "value"}:
        raise ValueError("WTO index must contain exactly date and value columns.")

    selected = voyages.loc[
        voyages["terminal_match_radius_km"].eq(terminal_match_radius_km)
        & voyages["project_id"].isin(gulf_export_project_ids)
    ].copy()
    if selected.empty:
        raise ValueError("No Gulf export-origin calls match the configured projects.")
    if selected["event_id"].duplicated().any():
        raise ValueError("Duplicate Gulf departure event IDs at the selected radius.")
    selected["date"] = (
        pd.to_datetime(selected["end"], utc=True).dt.tz_localize(None).dt.floor("D")
    )
    unknown_periods = set(selected["sample_period"]) - set(comparison_windows)
    if unknown_periods:
        raise ValueError(f"No comparison window for periods: {sorted(unknown_periods)}")
    starts = selected["sample_period"].map(
        {period: pd.Timestamp(bounds[0]) for period, bounds in comparison_windows.items()}
    )
    ends = selected["sample_period"].map(
        {period: pd.Timestamp(bounds[1]) for period, bounds in comparison_windows.items()}
    )
    selected = selected.loc[selected["date"].between(starts, ends)].copy()
    selected["expanded_resolved_capacity_m3"] = selected["capacity_m3"].where(
        selected["distance_accepted_expanded"].eq(True)
    )

    wto = wto_index.copy()
    wto["date"] = pd.to_datetime(wto["date"]).dt.tz_localize(None)
    wto = wto.set_index("date")["value"]
    daily_frames = []
    for period, bounds in comparison_windows.items():
        start, end = map(pd.Timestamp, bounds)
        dates = pd.date_range(start, end, freq="D")
        period_calls = selected.loc[selected["sample_period"].eq(period)]
        aggregate = period_calls.groupby("date").agg(
            gfw_departure_calls=("event_id", "size"),
            gfw_nominal_departure_capacity_m3=("capacity_m3", "sum"),
            gfw_expanded_resolved_capacity_m3=(
                "expanded_resolved_capacity_m3", "sum"
            ),
        ).reindex(dates, fill_value=0.0)
        aggregate.index.name = "date"
        aggregate["wto_outbound_volume_index"] = wto.reindex(dates)
        if aggregate["wto_outbound_volume_index"].isna().any():
            raise ValueError(f"WTO index does not fully cover the {period} window.")
        aggregate["sample_period"] = period
        aggregate["day_of_window"] = np.arange(len(aggregate))
        daily_frames.append(aggregate.reset_index())

    terminal = selected.groupby(
        ["sample_period", "project_id", "terminal_name"], as_index=False
    ).agg(
        departure_calls=("event_id", "size"),
        nominal_departure_capacity_m3=("capacity_m3", "sum"),
        first_departure_date=("date", "min"),
        last_departure_date=("date", "max"),
    )
    return pd.concat(daily_frames, ignore_index=True), terminal


def complete_weekly_totals(daily: pd.DataFrame) -> pd.DataFrame:
    """Aggregate 13 complete seven-day bins from each 94-day window."""
    complete = daily.loc[daily["day_of_window"] < 91].copy()
    complete["week_of_window"] = complete["day_of_window"] // 7
    value_columns = [
        "gfw_departure_calls", "gfw_nominal_departure_capacity_m3",
        "gfw_expanded_resolved_capacity_m3", "wto_outbound_volume_index",
    ]
    return complete.groupby(
        ["sample_period", "week_of_window"], as_index=False
    )[value_columns].sum()


def validation_correlations(
    daily: pd.DataFrame,
    weekly: pd.DataFrame,
    *,
    lags: list[int],
) -> pd.DataFrame:
    """Report all pre-specified lags; zero lag is the primary timing test."""
    rows: list[dict[str, Any]] = []
    gfw_columns = ["gfw_departure_calls", "gfw_nominal_departure_capacity_m3"]
    for period, group in daily.groupby("sample_period"):
        ordered = group.sort_values("date")
        for gfw_column in gfw_columns:
            for lag in lags:
                shifted = ordered[gfw_column].shift(lag)
                for method in ("pearson", "spearman"):
                    rows.append({
                        "sample_period": period,
                        "frequency": "daily",
                        "gfw_measure": gfw_column,
                        "gfw_lag_days": int(lag),
                        "method": method,
                        "correlation": _safe_correlation(
                            shifted, ordered["wto_outbound_volume_index"], method
                        ),
                        "n_observations": int(
                            pd.concat([
                                shifted, ordered["wto_outbound_volume_index"]
                            ], axis=1).dropna().shape[0]
                        ),
                    })
    for period, group in weekly.groupby("sample_period"):
        for gfw_column in gfw_columns:
            for method in ("pearson", "spearman"):
                rows.append({
                    "sample_period": period,
                    "frequency": "complete_7d_bins",
                    "gfw_measure": gfw_column,
                    "gfw_lag_days": 0,
                    "method": method,
                    "correlation": _safe_correlation(
                        group[gfw_column], group["wto_outbound_volume_index"], method
                    ),
                    "n_observations": int(len(group)),
                })
    return pd.DataFrame(rows)


def validation_summary(
    daily: pd.DataFrame,
    correlations: pd.DataFrame,
) -> dict[str, Any]:
    """Summarize scale-free pre/post agreement and zero-lag timing evidence."""
    period_rows: dict[str, dict[str, Any]] = {}
    for period, group in daily.groupby("sample_period"):
        period_rows[str(period)] = {
            "days": int(len(group)),
            "gfw_departure_calls": int(group["gfw_departure_calls"].sum()),
            "gfw_nominal_departure_capacity_m3": float(
                group["gfw_nominal_departure_capacity_m3"].sum()
            ),
            "gfw_nonzero_departure_days": int(group["gfw_departure_calls"].gt(0).sum()),
            "wto_mean_outbound_volume_index": float(
                group["wto_outbound_volume_index"].mean()
            ),
            "wto_nonzero_days": int(group["wto_outbound_volume_index"].gt(0).sum()),
        }
    if not {"pre", "post"}.issubset(period_rows):
        raise ValueError("Validation requires pre and post periods.")

    def percent_change(field: str) -> float:
        pre = float(period_rows["pre"][field])
        post = float(period_rows["post"][field])
        return (post / pre - 1.0) * 100 if pre else np.nan

    zero_lag = correlations.loc[
        correlations["gfw_lag_days"].eq(0)
        & correlations["frequency"].isin(["daily", "complete_7d_bins"])
    ].to_dict("records")
    changes = {
        "gfw_departure_calls_percent_change": percent_change("gfw_departure_calls"),
        "gfw_nominal_capacity_percent_change": percent_change(
            "gfw_nominal_departure_capacity_m3"
        ),
        "wto_mean_index_percent_change": percent_change(
            "wto_mean_outbound_volume_index"
        ),
    }
    return {
        "periods": period_rows,
        "pre_post_changes": changes,
        "directional_agreement": all(value < 0 for value in changes.values()),
        "zero_lag_correlations": zero_lag,
        "scaling_or_calibration_applied": False,
        "interpretation": (
            "Independent directional and timing validation of inferred Gulf LNG "
            "departures; not equality of units, observed cargo, or causal identification."
        ),
    }
