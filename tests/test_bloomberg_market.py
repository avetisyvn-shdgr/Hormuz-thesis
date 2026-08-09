from __future__ import annotations

import pandas as pd
import pytest

from lngfreight.bloomberg_market import (
    FREIGHT_SERIES,
    build_weekly_freight_panel,
    descriptive_freight_layer,
    friday_week_end,
)


def _manifest() -> dict:
    return {
        "governance": {
            "designation": "provenance_limited_secondary",
            "authorized_date": "2026-08-08",
        },
        "series": {
            name: {
                "displayed_series_name": name,
                "unit": "USD/day",
                "currency": "USD",
                "expected_sha256": str(index) * 64,
                "quality_flags": (
                    {"2025-01-31": "unverified_zero_mask_in_analysis"}
                    if slug == "west_spot"
                    else {}
                ),
            }
            for index, (name, slug) in enumerate(FREIGHT_SERIES.items(), start=1)
        },
    }


def _frames() -> dict[str, pd.DataFrame]:
    return {
        name: pd.DataFrame(
            {
                "date": pd.to_datetime(["2025-01-24", "2025-01-31", "2025-02-14"]),
                "value": [10.0, 0.0 if slug == "west_spot" else 20.0, 40.0],
            }
        )
        for name, slug in FREIGHT_SERIES.items()
    }


def test_friday_mapping_does_not_expand_to_daily_rows():
    dates = pd.Series(pd.to_datetime(["2025-01-30", "2025-01-31", "2025-02-01"]))
    assert friday_week_end(dates).dt.strftime("%Y-%m-%d").tolist() == [
        "2025-01-31",
        "2025-01-31",
        "2025-02-07",
    ]


def test_weekly_panel_preserves_raw_zero_masks_analysis_and_leaves_gap():
    panel, quality, output_manifest = build_weekly_freight_panel(
        _frames(),
        _manifest(),
        study_start="2025-01-20",
        study_end="2025-02-15",
        treatment_cutoff="2025-02-01",
    )
    zero_row = panel.loc[panel["week_end"].eq(pd.Timestamp("2025-01-31"))].iloc[0]
    assert zero_row["west_spot_usd_per_day_raw"] == 0
    assert pd.isna(zero_row["west_spot_usd_per_day_analysis"])
    gap_row = panel.loc[panel["week_end"].eq(pd.Timestamp("2025-02-07"))].iloc[0]
    assert pd.isna(gap_row["east_spot_usd_per_day_raw"])
    assert gap_row["east_spot_quality_flag"] == "missing_assessment"
    assert quality.set_index("logical_name").loc[
        "fearnleys_lng_spot_west_suez", "masked_zero_observations"
    ] == 1
    assert output_manifest["study_window"]["first_expected_post_week"] == "2025-02-07"


def test_multiple_native_observations_in_one_week_are_rejected():
    frames = _frames()
    name = next(iter(FREIGHT_SERIES))
    frames[name] = pd.DataFrame(
        {"date": pd.to_datetime(["2025-01-30", "2025-01-31"]), "value": [1, 2]}
    )
    with pytest.raises(ValueError, match="multiple observations"):
        build_weekly_freight_panel(
            frames,
            _manifest(),
            study_start="2025-01-20",
            study_end="2025-02-15",
            treatment_cutoff="2025-02-01",
        )


def test_descriptive_layer_uses_balanced_windows_and_avoids_spread_percent():
    weeks = pd.date_range("2025-01-03", periods=8, freq="W-FRI")
    panel = pd.DataFrame(
        {
            "week_end": weeks,
            "east_spot_usd_per_day_analysis": [10, 10, 10, 10, 20, 20, 20, 20],
            "west_spot_usd_per_day_analysis": [8, 8, 8, 8, 12, 12, 12, 12],
            "one_year_charter_usd_per_day_analysis": [5, 5, 5, 5, 10, 10, 10, 10],
        }
    )
    data, summary = descriptive_freight_layer(
        panel, first_post_week="2025-01-31", balanced_weeks=4
    )
    balanced = summary.loc[summary["comparison"].eq("balanced_4_week")].set_index("series")
    assert balanced.loc["east_spot", "percent_change"] == 100
    assert balanced.loc["west_spot", "absolute_change"] == 4
    assert pd.isna(balanced.loc["east_minus_west_spot", "percent_change"])
    assert data.loc[data.index[0], "east_spot_pre12_index"] == 100
