import pandas as pd
import pytest

from lngfreight.vessel_days import (
    add_elapsed_time_diagnostics,
    modeled_vessel_day_summary,
    vessel_day_pre_post_comparison,
)


def _voyages() -> pd.DataFrame:
    return pd.DataFrame({
        "endpoint_status": [
            "resolved_liquefaction_to_regasification",
            "resolved_liquefaction_to_regasification",
        ],
        "end": ["2025-01-01T00:00:00Z", "2026-01-01T00:00:00Z"],
        "destination_start": ["2025-01-03T00:00:00Z", "2026-01-05T00:00:00Z"],
        "modeled_terminal_to_terminal_nm": [720.0, 1440.0],
        "terminal_match_radius_km": [30, 30],
        "sample_period": ["pre", "post"],
        "distance_accepted": [True, True],
        "distance_accepted_expanded": [True, True],
        "capacity_m3": [100.0, 100.0],
    })


def test_elapsed_diagnostics_do_not_label_elapsed_as_sailing_days():
    result = add_elapsed_time_diagnostics(
        _voyages(), min_implied_speed_knots=5, max_implied_speed_knots=25
    )
    assert result["endpoint_elapsed_days"].tolist() == [2.0, 4.0]
    assert result["elapsed_time_status"].eq("plausible_elapsed_transit").all()


def test_modeled_days_use_distance_over_speed_and_compare_periods():
    summary = modeled_vessel_day_summary(_voyages(), speeds_knots=[15.0])
    expanded = summary[summary.route_specification.eq("expanded_60nm_snap")]
    assert expanded.loc[expanded.sample_period.eq("pre"), "total_modeled_sailing_vessel_days"].iloc[0] == 2.0
    comparison = vessel_day_pre_post_comparison(summary)
    expanded_comparison = comparison[
        comparison.route_specification.eq("expanded_60nm_snap")
    ]
    assert expanded_comparison["total_modeled_sailing_vessel_days_percent_change"].iloc[0] == 100.0
    assert expanded_comparison[
        "descriptive_post_excess_sailing_days_vs_pre_mean"
    ].iloc[0] == 2.0


def test_speed_assumptions_must_be_positive():
    with pytest.raises(ValueError, match="positive"):
        modeled_vessel_day_summary(_voyages(), speeds_knots=[0.0])
