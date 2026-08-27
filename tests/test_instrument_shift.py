"""B1 instrument revision audit: synthetic mapping, guard, and regime tests.

Every test here is synthetic. None of them touches the frozen PortWatch states
or asserts a real-data value. Real-data invariants are verified by
`scripts/run_hormuz_measurement_audit.py --check`, which Mher runs.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from lngfreight.instrument_shift import (
    InvariantMismatch,
    annual_summary,
    assert_not_averaged,
    assert_states_separate,
    changed_rows_by_unit,
    daily_revision_frame,
    fit_declared_mappings,
    fit_mapping,
    monthly_revision_distribution,
    overlap_panel,
    residual_summary,
    split_residuals_by_onset,
    squared_error_decomposition,
    tidy_state,
    verify_invariants,
    wto_state_audit,
)

QUANTILES = [0.05, 0.5, 0.95]


def _state_frame(values: dict[str, np.ndarray], dates: pd.DatetimeIndex) -> pd.DataFrame:
    blocks = []
    for unit, series in values.items():
        blocks.append(
            pd.DataFrame(
                {
                    "portname": unit,
                    "date": dates.strftime("%Y/%m/%d"),
                    "n_tanker": series,
                }
            )
        )
    return pd.concat(blocks, ignore_index=True)


def _two_states(july_values, august_values, start="2020-01-01"):
    dates = pd.date_range(start, periods=len(next(iter(july_values.values()))), freq="D")
    july = tidy_state(_state_frame(july_values, dates), "july", "july.csv", "a" * 64)
    august = tidy_state(_state_frame(august_values, dates), "august", "august.csv", "b" * 64)
    return july, august


# ---------------------------------------------------------------------------
# Mapping forms recover their own generating parameters
# ---------------------------------------------------------------------------


def test_proportional_mapping_recovers_exact_scale():
    x = np.arange(1.0, 501.0)
    fit = fit_mapping(x, 0.8319 * x, form="proportional")
    assert fit.intercept == 0.0
    assert fit.scale == pytest.approx(0.8319, abs=1e-12)
    assert fit.n_sample == 500


def test_affine_mapping_recovers_intercept_and_slope():
    x = np.arange(1.0, 501.0)
    fit = fit_mapping(x, 1.75 + 0.83 * x, form="affine")
    assert fit.intercept == pytest.approx(1.75, abs=1e-9)
    assert fit.scale == pytest.approx(0.83, abs=1e-12)


def test_additive_mapping_recovers_constant_shift_with_unit_slope():
    x = np.arange(1.0, 501.0)
    fit = fit_mapping(x, x - 8.5, form="additive")
    assert fit.scale == 1.0
    assert fit.intercept == pytest.approx(-8.5, abs=1e-12)


def test_unknown_mapping_form_is_rejected():
    with pytest.raises(ValueError, match="form must be one of"):
        fit_mapping(np.ones(5), np.ones(5), form="quadratic")


def test_empty_estimation_sample_raises():
    with pytest.raises(ValueError, match="empty estimation sample"):
        fit_mapping(np.array([np.nan]), np.array([np.nan]), form="proportional")


# ---------------------------------------------------------------------------
# The proportional / non-proportional decomposition
# ---------------------------------------------------------------------------


def test_purely_proportional_revision_leaves_no_residual():
    """A pure rescaling is fully absorbed: this is arithmetic, not evidence."""
    rng = np.random.default_rng(11)
    x = rng.uniform(20, 80, size=1000)
    y = 0.75 * x
    fit = fit_mapping(x, y, form="proportional")
    decomp = squared_error_decomposition(x, y, fit)
    assert decomp["fraction_squared_error_remaining"] == pytest.approx(0.0, abs=1e-20)
    assert decomp["share_absorbed_by_mapping"] == pytest.approx(1.0, abs=1e-20)
    assert decomp["rmse_after_mapping"] == pytest.approx(0.0, abs=1e-12)


def test_non_proportional_revision_leaves_a_detectable_residual():
    rng = np.random.default_rng(12)
    x = rng.uniform(20, 80, size=1000)
    y = 0.75 * x + rng.normal(0, 3.0, size=1000)
    fit = fit_mapping(x, y, form="proportional")
    decomp = squared_error_decomposition(x, y, fit)
    assert decomp["fraction_squared_error_remaining"] > 0.0
    assert decomp["rmse_after_mapping"] > 1.0


def test_fraction_remaining_is_relative_to_the_raw_revision():
    """Fraction remaining = SSE after mapping / SSE of the raw revision."""
    x = np.array([10.0, 20.0, 30.0, 40.0])
    y = np.array([5.0, 10.0, 15.0, 21.0])
    fit = fit_mapping(x, y, form="proportional")
    decomp = squared_error_decomposition(x, y, fit)
    expected = float(((y - fit.apply(x)) ** 2).sum() / ((y - x) ** 2).sum())
    assert decomp["fraction_squared_error_remaining"] == pytest.approx(expected, rel=1e-12)


def test_scaling_a_whole_series_is_absorbed_but_a_level_shift_is_not():
    x = np.linspace(10, 90, 400)
    scaled = squared_error_decomposition(x, 0.6 * x, fit_mapping(x, 0.6 * x, "proportional"))
    shifted = squared_error_decomposition(x, x - 5.0, fit_mapping(x, x - 5.0, "proportional"))
    assert scaled["fraction_squared_error_remaining"] == pytest.approx(0.0, abs=1e-20)
    assert shifted["fraction_squared_error_remaining"] > 0.0


# ---------------------------------------------------------------------------
# Frozen sample selection
# ---------------------------------------------------------------------------


def test_declared_mappings_use_only_their_configured_sample():
    dates = pd.date_range("2019-01-01", "2026-07-12", freq="D")
    x = np.linspace(40, 60, len(dates))
    y = 0.80 * x
    # Contaminate the window that the default sample must exclude.
    y = np.where(dates > pd.Timestamp("2025-12-31"), 999.0, y)
    series = pd.DataFrame({"date": dates, "july": x, "august": y})
    forms = {
        "default": {
            "form": "proportional",
            "sample_start": "2019-01-01",
            "sample_end": "2025-12-31",
            "role": "default",
        },
        "extended": {
            "form": "proportional",
            "sample_start": "2019-01-01",
            "sample_end": "2026-07-12",
            "role": "declared_sensitivity",
        },
    }
    fits = fit_declared_mappings(series, forms)
    assert fits["default"].scale == pytest.approx(0.80, abs=1e-12)
    assert fits["extended"].scale > 0.80  # contamination only reaches the extended sample
    assert fits["default"].n_sample < fits["extended"].n_sample
    assert fits["default"].sample_end == "2025-12-31"


def test_mapping_fit_is_deterministic():
    rng = np.random.default_rng(3)
    x = rng.uniform(10, 90, 500)
    y = 0.7 * x + rng.normal(0, 2, 500)
    first = fit_mapping(x, y, form="proportional")
    second = fit_mapping(x, y, form="proportional")
    assert first.scale == second.scale


# ---------------------------------------------------------------------------
# Residual reporting
# ---------------------------------------------------------------------------


def test_residuals_are_split_at_the_onset_without_reselecting_the_sample():
    dates = pd.date_range("2025-11-01", periods=200, freq="D")
    x = np.full(len(dates), 50.0)
    y = np.where(dates >= pd.Timestamp("2026-02-28"), 30.0, 40.0)
    series = pd.DataFrame({"date": dates, "july": x, "august": y})
    fit = fit_mapping(x, y, form="proportional")
    split = split_residuals_by_onset(series, fit, "2026-02-28", QUANTILES)
    assert split["pre_onset"]["n"] + split["post_onset"]["n"] == len(dates)
    assert split["full_overlap"]["n"] == len(dates)
    assert split["pre_onset"]["mean"] > split["post_onset"]["mean"]
    assert split["onset"] == "2026-02-28"


def test_residual_summary_reports_requested_quantiles():
    summary = residual_summary(np.arange(-50.0, 51.0), [0.05, 0.5, 0.95])
    assert summary["n"] == 101
    assert summary["q0.5"] == pytest.approx(0.0)
    assert summary["mean"] == pytest.approx(0.0)
    assert summary["rmse"] > 0


def test_residual_summary_handles_an_empty_vector():
    assert residual_summary(np.array([]), QUANTILES) == {"n": 0}


# ---------------------------------------------------------------------------
# Changed-row accounting and temporal distribution
# ---------------------------------------------------------------------------


def test_changed_row_percentage_counts_only_differing_rows():
    july_values = {"unit_a": np.array([1.0, 2.0, 3.0, 4.0]), "unit_b": np.array([9.0] * 4)}
    august_values = {"unit_a": np.array([1.0, 5.0, 3.0, 7.0]), "unit_b": np.array([9.0] * 4)}
    july, august = _two_states(july_values, august_values)
    panel = overlap_panel(july, august, ["n_tanker"])
    changed = changed_rows_by_unit(panel).set_index("portname")
    assert changed.loc["unit_a", "n_changed_rows"] == 2
    assert changed.loc["unit_a", "pct_changed_rows"] == pytest.approx(50.0)
    assert changed.loc["unit_b", "n_changed_rows"] == 0
    assert changed.loc["unit_b", "pct_changed_rows"] == pytest.approx(0.0)


def test_both_missing_is_not_counted_as_a_revision():
    july_values = {"u": np.array([1.0, np.nan, 3.0])}
    august_values = {"u": np.array([1.0, np.nan, 4.0])}
    july, august = _two_states(july_values, august_values)
    panel = overlap_panel(july, august, ["n_tanker"])
    changed = changed_rows_by_unit(panel)
    assert int(changed.loc[0, "n_changed_rows"]) == 1


def test_overlap_panel_keeps_only_shared_dates_and_labels_both_states():
    dates_j = pd.date_range("2020-01-01", periods=10, freq="D")
    dates_a = pd.date_range("2020-01-01", periods=14, freq="D")
    july = tidy_state(_state_frame({"u": np.arange(10.0)}, dates_j), "july", "j.csv", "a" * 64)
    august = tidy_state(_state_frame({"u": np.arange(14.0)}, dates_a), "august", "a.csv", "b" * 64)
    panel = overlap_panel(july, august, ["n_tanker"])
    assert len(panel) == 10
    assert {"july", "august"}.issubset(panel.columns)


def test_annual_summary_reports_ratio_and_revision_share():
    dates = pd.date_range("2020-01-01", "2021-12-31", freq="D")
    x = np.full(len(dates), 100.0)
    y = np.where(dates.year == 2020, 80.0, 100.0)
    july = tidy_state(_state_frame({"u": x}, dates), "july", "j.csv", "a" * 64)
    august = tidy_state(_state_frame({"u": y}, dates), "august", "a.csv", "b" * 64)
    panel = overlap_panel(july, august, ["n_tanker"])
    annual = annual_summary(panel, "u", "n_tanker").set_index("year")
    assert annual.loc[2020, "ratio_august_over_july"] == pytest.approx(0.8)
    assert annual.loc[2021, "ratio_august_over_july"] == pytest.approx(1.0)
    assert annual.loc[2020, "share_of_all_revisions_pct"] == pytest.approx(100.0)
    assert annual.loc[2021, "n_changed_rows"] == 0


def test_monthly_distribution_shares_sum_to_one_hundred():
    dates = pd.date_range("2020-01-01", "2020-06-30", freq="D")
    x = np.full(len(dates), 50.0)
    y = np.where(dates.month <= 3, 40.0, 50.0)
    series = pd.DataFrame({"date": dates, "july": x, "august": y})
    fit = fit_mapping(x, y, form="proportional")
    daily = daily_revision_frame(series, {"m": fit}, "m", "2020-04-01")
    monthly = monthly_revision_distribution(daily)
    assert monthly["share_of_all_revisions_pct"].sum() == pytest.approx(100.0)
    assert set(daily["period"]) == {"pre_onset", "post_onset"}


# ---------------------------------------------------------------------------
# Measurement-state separation guards
# ---------------------------------------------------------------------------


def test_identical_states_are_rejected():
    july, _ = _two_states({"u": np.ones(5)}, {"u": np.ones(5)})
    twin = tidy_state(july.frame.assign(date=july.frame["date"].dt.strftime("%Y/%m/%d")),
                      "august", "other.csv", july.sha256)
    with pytest.raises(ValueError, match="hash identically"):
        assert_states_separate(july, twin)


def test_states_sharing_one_file_are_rejected():
    july, august = _two_states({"u": np.ones(5)}, {"u": np.zeros(5)})
    same_path = tidy_state(
        august.frame.assign(date=august.frame["date"].dt.strftime("%Y/%m/%d")),
        "august",
        july.path,
        "b" * 64,
    )
    with pytest.raises(ValueError, match="same file"):
        assert_states_separate(july, same_path)


def test_separate_states_produce_a_separation_record():
    july, august = _two_states({"u": np.ones(5)}, {"u": np.full(5, 0.8)})
    record = assert_states_separate(july, august)
    assert record["states_separate"] is True
    assert record["never_averaged"] is True
    assert record["july"]["sha256"] != record["august"]["sha256"]


def test_an_averaged_column_is_refused():
    frame = pd.DataFrame({"july": [10.0, 20.0, 30.0], "august": [8.0, 16.0, 24.0]})
    frame["blended"] = (frame["july"] + frame["august"]) / 2.0
    with pytest.raises(ValueError, match="equals the July/August average"):
        assert_not_averaged(frame, "july", "august")


def test_legitimate_derived_columns_pass_the_average_guard():
    frame = pd.DataFrame({"july": [10.0, 20.0, 30.0], "august": [8.0, 16.0, 24.0]})
    frame["revision"] = frame["august"] - frame["july"]
    frame["ratio"] = frame["august"] / frame["july"]
    assert_not_averaged(frame, "july", "august")


def test_duplicate_unit_days_within_one_state_are_rejected():
    dates = pd.date_range("2020-01-01", periods=3, freq="D")
    frame = _state_frame({"u": np.ones(3)}, dates)
    doubled = pd.concat([frame, frame.iloc[[0]]], ignore_index=True)
    with pytest.raises(ValueError, match="duplicate"):
        tidy_state(doubled, "july", "j.csv", "a" * 64)


# ---------------------------------------------------------------------------
# Invariant verification
# ---------------------------------------------------------------------------


_SPEC = {
    "enforce": True,
    "checks": {
        "pct": {"expected": 97.4545, "tolerance": 0.001, "description": ""},
        "ratios": {"expected": {2019: 0.843, 2020: 0.848}, "tolerance": 0.0005, "description": ""},
    },
}


def test_invariants_pass_inside_tolerance():
    table = verify_invariants(
        {"pct": 97.454545, "ratios": {2019: 0.842825, 2020: 0.848370}}, _SPEC
    )
    assert bool(table["passed"].all())
    assert len(table) == 3


def test_invariant_mismatch_stops_the_phase():
    with pytest.raises(InvariantMismatch, match="STOP"):
        verify_invariants({"pct": 90.0, "ratios": {2019: 0.843, 2020: 0.848}}, _SPEC)


def test_a_missing_computed_invariant_fails_rather_than_passing_silently():
    with pytest.raises(InvariantMismatch):
        verify_invariants({"ratios": {2019: 0.843, 2020: 0.848}}, _SPEC)


def test_expected_unit_label_is_checked():
    spec = {
        "enforce": True,
        "checks": {
            "next": {
                "expected": 0.1091,
                "tolerance": 0.001,
                "expected_unit": "Malacca Strait",
                "description": "",
            }
        },
    }
    table = verify_invariants(
        {"next": 0.109091, "next__unit": "Malacca Strait"}, spec
    )
    assert bool(table["passed"].all())
    with pytest.raises(InvariantMismatch):
        verify_invariants({"next": 0.109091, "next__unit": "Suez Canal"}, spec)


# ---------------------------------------------------------------------------
# WTO regime detection
# ---------------------------------------------------------------------------


def _write_wto(tmp_path: Path, name: str, dates, values, cols=("date", "value")):
    frame = pd.DataFrame({cols[0]: [d.strftime("%Y-%m-%d") for d in dates], cols[1]: values})
    frame.to_csv(tmp_path / name, index=False)


def test_wto_regimes_separate_files_whose_history_differs(tmp_path):
    dates = pd.date_range("2025-01-01", periods=40, freq="D")
    base = np.linspace(100, 140, 40)
    _write_wto(tmp_path, "a_regime1.csv", dates, base)
    _write_wto(tmp_path, "b_regime1.csv", dates[:30], base[:30])
    _write_wto(tmp_path, "c_regime2.csv", dates, base + 0.5)
    audit, pairwise = wto_state_audit(
        tmp_path, "*.csv", tmp_path / "missing.jsonl", "v", ["date"], ["value"], 0.0
    )
    regimes = audit.set_index("file")["regime_id"]
    assert regimes["a_regime1.csv"] == regimes["b_regime1.csv"]
    assert regimes["c_regime2.csv"] != regimes["a_regime1.csv"]
    assert audit["regime_id"].nunique() == 2
    assert len(pairwise) == 3


def test_a_single_differing_date_creates_its_own_regime(tmp_path):
    """Strict equality: near-identical is not identical, and is not merged."""
    dates = pd.date_range("2025-01-01", periods=30, freq="D")
    base = np.linspace(100, 130, 30)
    nudged = base.copy()
    nudged[7] += 0.25
    _write_wto(tmp_path, "a.csv", dates, base)
    _write_wto(tmp_path, "b.csv", dates, base)
    _write_wto(tmp_path, "c.csv", dates, nudged)
    audit, pairwise = wto_state_audit(
        tmp_path, "*.csv", tmp_path / "missing.jsonl", "v", ["date"], ["value"], 0.0
    )
    assert audit.set_index("file").loc["c.csv", "regime_id"] != audit.set_index("file").loc["a.csv", "regime_id"]
    conflict = next(r for r in pairwise if {r["file_a"], r["file_b"]} == {"a.csv", "c.csv"})
    assert conflict["n_differing_dates"] == 1
    assert conflict["identical_on_overlap"] is False


def test_wto_column_aliases_resolve_provider_named_columns(tmp_path):
    dates = pd.date_range("2025-01-01", periods=10, freq="D")
    _write_wto(tmp_path, "aliased.csv", dates, np.arange(10.0),
               cols=("voy_load_date", "voy_intake_index"))
    audit, _ = wto_state_audit(
        tmp_path, "*.csv", tmp_path / "missing.jsonl", "v",
        ["date", "voy_load_date"], ["value", "voy_intake_index"], 0.0,
    )
    assert len(audit) == 1
    assert audit.loc[0, "n_rows"] == 10
    assert audit.loc[0, "data_start"] == "2025-01-01"


def test_unresolvable_wto_columns_raise(tmp_path):
    pd.DataFrame({"when": ["2025-01-01"], "x": [1.0]}).to_csv(tmp_path / "bad.csv", index=False)
    with pytest.raises(ValueError, match="could not resolve date/value columns"):
        wto_state_audit(tmp_path, "*.csv", tmp_path / "m.jsonl", "v", ["date"], ["value"], 0.0)


def test_wto_audit_reads_retrieval_horizons_from_provenance(tmp_path):
    dates = pd.date_range("2025-01-01", periods=10, freq="D")
    _write_wto(tmp_path, "snap.csv", dates, np.arange(10.0))
    provenance = tmp_path / "provenance.jsonl"
    provenance.write_text(
        '{"retrieved_utc": "2026-06-19T22:21:21+00:00", "variable": "v", '
        '"query": {"start": "2025-01-01", "end": "2026-06-01"}, '
        '"file": "some/dir/snap.csv"}\n',
        encoding="utf-8",
    )
    audit, _ = wto_state_audit(tmp_path, "*.csv", provenance, "v", ["date"], ["value"], 0.0)
    assert audit.loc[0, "n_provenance_records"] == 1
    assert audit.loc[0, "query_start"] == "2025-01-01"
    assert audit.loc[0, "query_end"] == "2026-06-01"
    assert audit.loc[0, "retrieved_utc_first"].startswith("2026-06-19")


def test_empty_wto_directory_raises(tmp_path):
    with pytest.raises(ValueError, match="No WTO files matched"):
        wto_state_audit(tmp_path, "*.csv", tmp_path / "m.jsonl", "v", ["date"], ["value"], 0.0)


# ---------------------------------------------------------------------------
# End-to-end synthetic pipeline: the composition the audit script performs
# ---------------------------------------------------------------------------


def test_synthetic_end_to_end_pipeline_matches_the_script_composition():
    """Exercise the whole B1 chain on a synthetic two-state panel.

    A known scale is applied to one unit plus a small non-proportional wobble,
    every other unit is revised on a handful of days, and the pipeline must
    recover the scale, separate the components, and produce a manifest-shaped
    dict that serialises.
    """
    rng = np.random.default_rng(2026)
    dates = pd.date_range("2019-01-01", "2026-07-12", freq="D")
    units = [f"unit_{i:02d}" for i in range(28)]
    focus, true_scale = "unit_00", 0.83

    july_values, august_values = {}, {}
    for i, unit in enumerate(units):
        base = rng.uniform(30, 70, size=len(dates)).round(0)
        july_values[unit] = base
        if unit == focus:
            revised = true_scale * base + rng.normal(0, 2.0, size=len(dates))
            august_values[unit] = revised.round(3)
        else:
            revised = base.copy()
            revised[i] = revised[i] + 1.0  # i revised days for unit i
            august_values[unit] = revised

    july = tidy_state(_state_frame(july_values, dates), "july", "j.csv", "a" * 64)
    august = tidy_state(_state_frame(august_values, dates), "august", "a.csv", "b" * 64)
    separation = assert_states_separate(july, august)
    assert separation["states_separate"] is True

    panel = overlap_panel(july, august, ["n_tanker"])
    assert panel["date"].nunique() == len(dates)
    assert panel["portname"].nunique() == 28

    by_unit = changed_rows_by_unit(panel)
    assert_not_averaged(
        by_unit.rename(columns={"mean_july": "july", "mean_august": "august"}),
        "july",
        "august",
    )
    ranked = by_unit.sort_values("pct_changed_rows", ascending=False)
    assert ranked.iloc[0]["portname"] == focus  # the rescaled unit dominates

    series = (
        panel[(panel["portname"] == focus)].sort_values("date").reset_index(drop=True)
    )
    forms = {
        "proportional_default": {
            "form": "proportional",
            "sample_start": "2019-01-01",
            "sample_end": "2025-12-31",
            "role": "default",
        },
        "affine_sensitivity": {
            "form": "affine",
            "sample_start": "2019-01-01",
            "sample_end": "2025-12-31",
            "role": "declared_sensitivity",
        },
        "additive_sensitivity": {
            "form": "additive",
            "sample_start": "2019-01-01",
            "sample_end": "2025-12-31",
            "role": "declared_sensitivity",
        },
    }
    fits = fit_declared_mappings(series, forms)
    default_name = "proportional_default"
    assert fits[default_name].scale == pytest.approx(true_scale, abs=0.01)

    x = series["july"].to_numpy(float)
    y = series["august"].to_numpy(float)
    decompositions = {
        name: squared_error_decomposition(x, y, fit) for name, fit in fits.items()
    }
    default_decomp = decompositions[default_name]
    # Most of the revision is the rescaling; a real remainder survives it.
    assert default_decomp["share_absorbed_by_mapping"] > 0.8
    assert default_decomp["fraction_squared_error_remaining"] > 0.0

    residual_split = split_residuals_by_onset(
        series, fits[default_name], "2026-02-28", QUANTILES
    )
    assert residual_split["pre_onset"]["n"] > residual_split["post_onset"]["n"] > 0

    daily = daily_revision_frame(series, fits, default_name, "2026-02-28", measure="n_tanker")
    assert_not_averaged(daily, "n_tanker_july", "n_tanker_august")
    assert "residual__affine_sensitivity" in daily.columns
    assert daily["residual_default"].equals(daily[f"residual__{default_name}"])

    monthly = monthly_revision_distribution(daily)
    assert monthly["share_of_all_revisions_pct"].sum() == pytest.approx(100.0)

    annual = annual_summary(panel, focus, "n_tanker")
    assert bool(annual.loc[annual["year"] == 2026, "partial_year"].iloc[0])
    assert not bool(annual.loc[annual["year"] == 2019, "partial_year"].iloc[0])

    computed = {
        "hormuz_pct_changed_n_tanker": float(
            by_unit.loc[by_unit["portname"] == focus, "pct_changed_rows"].iloc[0]
        )
    }
    table = verify_invariants(
        computed,
        {
            "enforce": True,
            "checks": {
                "hormuz_pct_changed_n_tanker": {
                    "expected": computed["hormuz_pct_changed_n_tanker"],
                    "tolerance": 1e-9,
                    "description": "",
                }
            },
        },
    )
    assert bool(table["passed"].all())

    manifest = {
        "estimators": {name: fit.to_dict() for name, fit in fits.items()},
        "revision_decomposition": decompositions,
        "residual_distribution": residual_split,
        "measurement_states": separation,
        "temporal_distribution_monthly": monthly.to_dict(orient="records"),
        "invariant_verification": table.to_dict(orient="records"),
    }
    import json

    restored = json.loads(json.dumps(manifest))
    assert restored["estimators"][default_name]["form"] == "proportional"
    assert restored["measurement_states"]["never_averaged"] is True
