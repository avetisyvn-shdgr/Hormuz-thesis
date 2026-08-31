from pathlib import Path

import pandas as pd

from hormuz_throughput import config


def test_long_horizon_schema_labels_overlapping_band_without_nominal_coverage():
    frame = pd.read_csv(
        config.path("data_processed") / "long_horizon_intervals_summary.csv"
    )
    expected = {
        "horizon_calendar_days",
        "n_post_days",
        "overlapping_placebo_quantile_band_lower",
        "overlapping_placebo_quantile_band_upper",
        "overlapping_placebo_quantile_band_width",
        "overlapping_placebo_band_excludes_zero_descriptively",
        "mean_daily_overlapping_placebo_quantile_band_lower",
        "mean_daily_overlapping_placebo_quantile_band_upper",
        "nominal_coverage_supported",
    }
    forbidden = {
        "interval_94dhorizon_lower",
        "interval_94dhorizon_upper",
        "interval_94dhorizon_width",
        "excludes_zero_94dhorizon",
        "mean_daily_94dhorizon_lower",
        "mean_daily_94dhorizon_upper",
        "interval_horizon_matched_lower",
        "interval_horizon_matched_upper",
        "interval_horizon_matched_width",
        "excludes_zero_horizon_matched",
    }

    assert expected <= set(frame.columns)
    assert forbidden.isdisjoint(frame.columns)
    assert not frame["nominal_coverage_supported"].astype(bool).any()
    assert frame["horizon_calendar_days"].ge(frame["n_post_days"]).all()
    assert (
        frame.groupby(["model", "target"])["horizon_calendar_days"].nunique() == 1
    ).all()


def test_run_spec_comparison_distinguishes_band_and_diagnostic_labels():
    frame = pd.read_csv(config.path("data_processed") / "run_spec_comparison.csv")

    assert "reported_band_lower" in frame.columns
    assert "reported_band_upper" in frame.columns
    assert "reported_band_label" in frame.columns
    assert "placebo_diagnostic_value" in frame.columns
    assert "placebo_diagnostic_label" in frame.columns
    primary = frame.loc[frame["role"] == "working_primary"].iloc[0]
    assert primary["reported_band_label"].endswith("no_nominal_coverage")
    assert primary["placebo_diagnostic_label"].endswith("not_p_value")
    assert "interval_horizon_matched_lower" not in frame.columns
    assert "interval_horizon_matched_upper" not in frame.columns
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
        "Horizon-matched 95% interval",
        "One-sided placebo p-value",
        "| Placebo p-value |",
        "p=0.0278",
    )

    for path in active_reports:
        text = Path(path).read_text(encoding="utf-8")
        for phrase in stale_phrases:
            assert phrase not in text


def test_active_primary_reports_lead_with_disjoint_support_limits():
    for name in ("run_output.md", "current_results_summary.md"):
        text = (config.ROOT / "reports" / name).read_text(encoding="utf-8")
        assert "0.125" in text
        assert "unbounded" in text
        assert "no nominal coverage" in text
        assert "not a p-value" in text


def test_temporal_multiplicity_correction_uses_disjoint_blocks():
    frame = pd.read_csv(
        config.path("data_processed") / "romano_wolf_stepdown.csv"
    )
    temporal = frame.loc[
        frame["family"] == "disjoint_placebo_time_generators_by_outcome"
    ]
    assert not temporal.empty
    assert temporal["n_joint_resamples"].eq(7).all()
    assert temporal["romano_wolf_p_value"].ge(0.125).all()


def test_run_output_uses_disjoint_block_maxima_for_donor_time_inference():
    text = (config.ROOT / "reports" / "run_output.md").read_text(encoding="utf-8")
    assert "Donor-by-time stress" in text
    assert "7** disjoint-window maxima" in text
    assert "floor 1/8" in text
    assert "not pooled as independent draws" in text
    assert "1/155" not in text
    assert "0.006452" not in text


def test_active_reports_use_prefit_screened_synthetic_control_inference():
    run_output = (config.ROOT / "reports" / "run_output.md").read_text(
        encoding="utf-8"
    )
    results_summary = (
        config.ROOT / "reports" / "current_results_summary.md"
    ).read_text(encoding="utf-8")

    for text in (run_output, results_summary):
        assert "pre-fit screen" in text.lower()
        assert "14/22" in text or "14 / 22" in text
        assert "0.066667" in text
        assert "1/15" in text

    assert "run_synthetic_control_placebo_paths.png" in run_output
    assert "p-value: **0.043478**" not in run_output
    assert "| Abadie placebo p-value | 0.043 |" not in results_summary
