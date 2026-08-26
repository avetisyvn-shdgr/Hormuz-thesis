from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from lngfreight import config
from run_rebound_relapse_profile import complete_slice


def _profile() -> pd.DataFrame:
    return pd.read_csv(
        config.path("portwatch_regime_phase_profile_csv"),
        parse_dates=["phase_start", "phase_end", "trusted_reporting_end"],
    )


def _contrasts() -> pd.DataFrame:
    return pd.read_csv(config.path("portwatch_regime_contrasts_csv"))


def test_frozen_phase_windows_have_expected_calendar_denominators():
    profile = _profile()
    expected = {
        "pre_mou_reference_20d": 20,
        "post_mou_interval_20d": 20,
        "post_mou_final_7d": 7,
        "renewed_attacks_event_day": 1,
        "post_renewed_attacks_interval": 25,
    }
    for phase, days in expected.items():
        rows = profile.loc[profile["phase"] == phase]
        assert len(rows) == 2
        assert rows["planned_calendar_days"].eq(days).all()


def test_august_vintage_reproduces_rebound_then_relapse_profile():
    profile = _profile().query("vintage == 'vintage_20260809'").set_index("phase")
    expected = {
        "pre_mou_reference_20d": (20, 17.0, 0.85, 10),
        "post_mou_interval_20d": (20, 209.0, 10.45, 19),
        "post_mou_final_7d": (7, 88.0, 88.0 / 7.0, 7),
        "renewed_attacks_event_day": (1, 10.0, 10.0, 1),
        "post_renewed_attacks_interval": (25, 39.0, 1.56, 21),
    }
    for phase, (days, total, mean, nonzero) in expected.items():
        row = profile.loc[phase]
        assert bool(row["complete_window"])
        assert row["observed_days"] == days
        assert row["transit_sum"] == total
        assert row["mean_daily_transits"] == pytest.approx(mean)
        assert row["nonzero_days"] == nonzero
    assert profile.loc[
        "post_mou_interval_20d", "mean_as_share_of_analysis_pre"
    ] == pytest.approx(10.45 / 47.00131665569454)


def test_pinned_vintage_confirms_rebound_but_excludes_source_buffer_for_relapse():
    profile = _profile().query("vintage == 'pinned_primary'").set_index("phase")
    assert profile.loc["pre_mou_reference_20d", "mean_daily_transits"] == 1.25
    assert profile.loc["post_mou_interval_20d", "mean_daily_transits"] == 12.45
    tail = profile.loc["post_renewed_attacks_interval"]
    assert not bool(tail["complete_window"])
    assert bool(tail["right_censored"])
    assert tail["planned_calendar_days"] == 25
    assert tail["observed_days"] == 0
    assert tail["buffer_excluded_source_days"] == 5
    assert tail["trusted_reporting_end"] == pd.Timestamp("2026-07-07")
    assert not bool(tail["admissible_for_phase_contrast"])


def test_august_relapse_window_uses_only_trusted_25_day_support():
    profile = _profile().query("vintage == 'vintage_20260809'").set_index("phase")
    tail = profile.loc["post_renewed_attacks_interval"]
    assert tail["trusted_reporting_end"] == pd.Timestamp("2026-08-01")
    assert tail["observed_days"] == 25
    assert tail["buffer_excluded_source_days"] == 0
    assert bool(tail["admissible_for_phase_contrast"])


def test_declared_contrasts_estimate_only_complete_windows():
    contrasts = _contrasts().set_index(["vintage", "contrast"])
    rebound = contrasts.loc[
        ("vintage_20260809", "matched_post_mou_vs_pre_mou")
    ]
    assert bool(rebound["admissible_contrast"])
    assert rebound["difference_mean_daily_transits"] == pytest.approx(9.6)
    relapse = contrasts.loc[
        ("vintage_20260809", "post_attacks_vs_post_mou")
    ]
    assert bool(relapse["admissible_contrast"])
    assert relapse["difference_mean_daily_transits"] == pytest.approx(-8.89)
    assert relapse["percent_change_from_reference"] == pytest.approx(-85.0717703349)
    pinned_relapse = contrasts.loc[
        ("pinned_primary", "post_attacks_vs_post_mou")
    ]
    assert not bool(pinned_relapse["admissible_contrast"])
    assert np.isnan(pinned_relapse["difference_mean_daily_transits"])


def test_complete_slice_rejects_internal_calendar_gaps():
    index = pd.date_range("2026-01-01", periods=5, freq="D").delete(2)
    series = pd.Series([1.0, 2.0, 4.0, 5.0], index=index)
    with pytest.raises(ValueError, match="internal missing daily observations"):
        complete_slice(series, pd.Timestamp("2026-01-01"), pd.Timestamp("2026-01-05"))
