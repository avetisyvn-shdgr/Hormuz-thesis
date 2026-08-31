import pandas as pd

from hormuz_throughput.wto_validation import (
    build_gulf_departure_daily,
    complete_weekly_totals,
    validation_correlations,
    validation_summary,
)


def _voyages() -> pd.DataFrame:
    return pd.DataFrame({
        "event_id": ["a", "b", "c"],
        "sample_period": ["pre", "pre", "post"],
        "project_id": ["gulf"] * 3,
        "terminal_name": ["Gulf LNG"] * 3,
        "end": ["2025-01-01T12:00:00Z", "2025-01-03T12:00:00Z", "2026-01-01T12:00:00Z"],
        "capacity_m3": [100.0, 200.0, 50.0],
        "terminal_match_radius_km": [30] * 3,
        "endpoint_status": ["resolved_liquefaction_to_regasification"] * 3,
        "distance_accepted_expanded": [True] * 3,
    })


def _wto() -> pd.DataFrame:
    dates = list(pd.date_range("2025-01-01", "2025-01-14")) + list(
        pd.date_range("2026-01-01", "2026-01-14")
    )
    return pd.DataFrame({
        "date": dates,
        "value": list(range(1, 15)) + [value / 2 for value in range(1, 15)],
    })


def test_daily_validation_preserves_unscaled_counts_and_capacity():
    daily, terminal = build_gulf_departure_daily(
        _voyages(), _wto(), gulf_export_project_ids=["gulf"],
        terminal_match_radius_km=30,
        comparison_windows={
            "pre": ["2025-01-01", "2025-01-14"],
            "post": ["2026-01-01", "2026-01-14"],
        },
    )
    pre = daily[daily.sample_period.eq("pre")]
    assert pre["gfw_departure_calls"].sum() == 2
    assert pre["gfw_nominal_departure_capacity_m3"].sum() == 300.0
    assert terminal["departure_calls"].sum() == 3


def test_weekly_correlations_and_directional_summary():
    daily, _ = build_gulf_departure_daily(
        _voyages(), _wto(), gulf_export_project_ids=["gulf"],
        terminal_match_radius_km=30,
        comparison_windows={
            "pre": ["2025-01-01", "2025-01-14"],
            "post": ["2026-01-01", "2026-01-14"],
        },
    )
    weekly = complete_weekly_totals(daily)
    correlations = validation_correlations(daily, weekly, lags=[-1, 0, 1])
    summary = validation_summary(daily, correlations)
    assert len(weekly) == 4
    assert set(correlations["gfw_lag_days"]) == {-1, 0, 1}
    assert summary["scaling_or_calibration_applied"] is False
    assert summary["directional_agreement"] is True
