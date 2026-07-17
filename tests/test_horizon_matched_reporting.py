from pathlib import Path

import pandas as pd

from lngfreight import config


def test_long_horizon_interval_schema_uses_neutral_horizon_names():
    frame = pd.read_csv(
        config.path("data_processed") / "long_horizon_intervals_summary.csv"
    )
    expected = {
        "horizon_calendar_days",
        "n_post_days",
        "interval_horizon_matched_lower",
        "interval_horizon_matched_upper",
        "interval_horizon_matched_width",
        "excludes_zero_horizon_matched",
        "mean_daily_horizon_matched_lower",
        "mean_daily_horizon_matched_upper",
    }
    forbidden = {
        "interval_94dhorizon_lower",
        "interval_94dhorizon_upper",
        "interval_94dhorizon_width",
        "excludes_zero_94dhorizon",
        "mean_daily_94dhorizon_lower",
        "mean_daily_94dhorizon_upper",
    }

    assert expected <= set(frame.columns)
    assert forbidden.isdisjoint(frame.columns)
    assert frame["horizon_calendar_days"].ge(frame["n_post_days"]).all()
    assert (
        frame.groupby(["model", "target"])["horizon_calendar_days"].nunique() == 1
    ).all()


def test_run_spec_comparison_uses_neutral_interval_columns():
    frame = pd.read_csv(config.path("data_processed") / "run_spec_comparison.csv")

    assert "interval_horizon_matched_lower" in frame.columns
    assert "interval_horizon_matched_upper" in frame.columns
    assert "interval_94d_lower" not in frame.columns
    assert "interval_94d_upper" not in frame.columns


def test_active_primary_reports_do_not_reintroduce_stale_94_day_labels():
    active_reports = [
        config.ROOT / "reports" / "run_output.md",
        config.ROOT / "reports" / "current_results_summary.md",
    ]
    stale_phrases = (
        "94-day",
        "94d lower",
        "94d upper",
        "AR 94-day",
        "36 overlapping",
        "about 9 non-overlapping",
    )

    for path in active_reports:
        text = Path(path).read_text(encoding="utf-8")
        for phrase in stale_phrases:
            assert phrase not in text
