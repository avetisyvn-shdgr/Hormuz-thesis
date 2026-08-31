"""Structural and corruption tests for the task-7 network-support frontier.

These tests police the denominator discipline and the construct boundary. They
assert that a selective cohort can never be emitted without its overall
denominator, that the cohorts partition the resolved panel, that the
Hormuz-crossing definition is the one already established in the exposure layer,
and that no artifact drifts into throughput or causal language. They do not
assert that support fell by any particular amount.
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from hormuz_throughput import config
from hormuz_throughput import network_support as ns

from freeze_network_support_frontier import (
    assert_upstream_untouched,
    build_manifest,
    manifest_path,
)
from run_network_support_frontier import (
    build_audit_expectation,
    guard_denominators,
    load_design,
    load_verified_inputs,
    output_path,
    resolved_legs,
    sha256_file,
    validate_inputs,
)


def _design():
    return load_design()


def _outputs_present() -> bool:
    design, _ = _design()
    return all(
        output_path(design, key).is_file()
        for key in (
            "denominators_csv",
            "radius_sensitivity_csv",
            "balanced_cohort_csv",
            "diagnostics_json",
            "audit_expectation_json",
            "documentation_markdown",
            "manifest_json",
        )
    )


def _upstream_present() -> bool:
    design, _ = _design()
    return all(
        (config.ROOT / spec["path"]).is_file()
        for spec in design["upstream_registered_artifacts"].values()
    )


needs_outputs = pytest.mark.skipif(
    not _outputs_present(),
    reason="network-support frontier artifacts are not generated",
)
needs_upstream = pytest.mark.skipif(
    not _upstream_present(),
    reason="vessel-branch upstream artifacts are not deposited",
)


def _synthetic_legs() -> pd.DataFrame:
    """Small hand-built panel with a known cohort partition."""
    records = []

    def add(n, period, imo_base, gulf, crossing, country, dest, origin):
        for i in range(n):
            records.append({
                "event_id": f"{period}_{origin}_{dest}_{imo_base + i}",
                "imo": imo_base + i,
                "sample_period": period,
                "project_id": origin,
                "terminal_name": f"origin_{origin}",
                "destination_project_id": dest,
                "destination_terminal_name": f"dest_{dest}",
                "destination_country": country,
                "inside_hormuz_origin": gulf,
                "hormuz_exposed_leg": gulf and crossing,
                "origin_group": (
                    "inside_hormuz_crossing" if gulf and crossing
                    else "inside_hormuz_non_crossing" if gulf
                    else "non_gulf"
                ),
            })

    add(10, "pre", 100, True, True, "Japan", "D1", "GULF1")
    add(3, "pre", 200, True, False, "India", "D2", "GULF1")
    add(7, "pre", 300, False, False, "Spain", "D3", "USA1")
    add(1, "post", 100, True, True, "Japan", "D1", "GULF1")
    add(2, "post", 200, True, False, "India", "D2", "GULF1")
    add(6, "post", 300, False, False, "Spain", "D3", "USA1")
    return pd.DataFrame(records)




def test_cohorts_partition_the_resolved_panel():
    legs = _synthetic_legs()
    parts = ["hormuz_crossing", "inside_hormuz_non_crossing", "non_gulf"]
    masks = [ns.cohort_mask(legs, cohort) for cohort in parts]
    stacked = np.vstack([mask.to_numpy() for mask in masks])
    assert stacked.sum(axis=0).tolist() == [1] * len(legs)
    assert ns.cohort_mask(legs, "all_resolved").all()


def test_hormuz_cohort_uses_the_established_exposure_flag():
    legs = _synthetic_legs()
    mask = ns.cohort_mask(legs, "hormuz_crossing")
    pd.testing.assert_series_equal(
        mask, legs["hormuz_exposed_leg"].astype(bool), check_names=False
    )


def test_unknown_cohort_is_rejected():
    with pytest.raises(ValueError, match="Unknown cohort"):
        ns.cohort_mask(_synthetic_legs(), "hormuz_only_when_convenient")


def test_missing_leg_columns_are_rejected():
    legs = _synthetic_legs().drop(columns=["hormuz_exposed_leg"])
    with pytest.raises(ValueError, match="missing columns"):
        ns.cohort_mask(legs, "hormuz_crossing")




def test_overall_denominator_is_always_emitted():
    """Requesting only the selective cohort must still yield the overall one."""
    legs = _synthetic_legs()
    frame = ns.support_denominators(
        legs,
        terminal_radius_km=30,
        census_eligible_imos=100,
        cohorts=("hormuz_crossing",),
    )
    assert "all_resolved" in set(frame["cohort"])
    assert set(frame["sample_period"]) == set(ns.PERIODS)


def test_denominator_counts_match_the_synthetic_panel():
    legs = _synthetic_legs()
    frame = ns.support_denominators(
        legs, terminal_radius_km=30, census_eligible_imos=100
    ).set_index(["cohort", "sample_period"])["n_sequences"]
    assert int(frame.loc["all_resolved", "pre"]) == 20
    assert int(frame.loc["all_resolved", "post"]) == 9
    assert int(frame.loc["hormuz_crossing", "pre"]) == 10
    assert int(frame.loc["hormuz_crossing", "post"]) == 1
    assert int(frame.loc["non_gulf", "pre"]) == 7


def test_census_coverage_is_a_share_of_the_census():
    legs = _synthetic_legs()
    frame = ns.support_denominators(
        legs, terminal_radius_km=30, census_eligible_imos=50
    )
    expected = frame["n_unique_imos"] / 50
    pd.testing.assert_series_equal(
        frame["census_coverage_share"], expected, check_names=False
    )
    assert frame["census_coverage_share"].between(0, 1).all()


def test_zero_census_is_rejected():
    with pytest.raises(ValueError, match="census_eligible_imos"):
        ns.support_denominators(
            _synthetic_legs(), terminal_radius_km=30, census_eligible_imos=0
        )


def test_balanced_cohort_keeps_only_both_period_imos():
    legs = _synthetic_legs()
    balanced = ns.balanced_cohort(legs)
    both = ns.balanced_cohort_imos(legs)
    assert set(balanced["imo"]) == both
    for imo in both:
        periods = set(legs.loc[legs["imo"].eq(imo), "sample_period"])
        assert periods == {"pre", "post"}
    assert len(balanced) <= len(legs)


def test_support_change_requires_both_periods():
    legs = _synthetic_legs()
    frame = ns.support_denominators(
        legs, terminal_radius_km=30, census_eligible_imos=100
    )
    truncated = frame.loc[frame["sample_period"].eq("pre")]
    with pytest.raises(ValueError, match="pre/post pair"):
        ns.support_change(truncated)


def test_thin_pre_period_denominators_are_flagged():
    """A retention share above 1.0 off a tiny base must be marked unstable."""
    legs = _synthetic_legs()
    frame = ns.support_denominators(
        legs, terminal_radius_km=30, census_eligible_imos=100
    )
    change = ns.support_change(frame, thin_denominator_threshold=10).set_index(
        "cohort"
    )
    assert bool(change.loc["all_resolved", "pre_denominator_is_thin"]) is False
    assert bool(
        change.loc["inside_hormuz_non_crossing", "pre_denominator_is_thin"]
    ) is True
    assert bool(change.loc["hormuz_crossing", "pre_denominator_is_thin"]) is True

    strict = ns.support_change(frame, thin_denominator_threshold=0).set_index("cohort")
    assert not strict["pre_denominator_is_thin"].any()
    with pytest.raises(ValueError, match="thin_denominator_threshold"):
        ns.support_change(frame, thin_denominator_threshold=-1)


@needs_outputs
def test_documentation_marks_every_thin_retention_cell():
    design, _ = _design()
    balanced = pd.read_csv(output_path(design, "balanced_cohort_csv"))
    text = output_path(design, "documentation_markdown").read_text(encoding="utf-8")
    if balanced["pre_denominator_is_thin"].any():
        assert "†" in text
        assert "must not be read as a trend" in text
    threshold = int(design["thin_denominator_threshold_sequences"])
    expected = balanced["pre_sequences"].le(threshold)
    pd.testing.assert_series_equal(
        balanced["pre_denominator_is_thin"].astype(bool),
        expected,
        check_names=False,
    )


def test_selectivity_contrast_requires_the_overall_cohort():
    change = pd.DataFrame([
        {"terminal_radius_km": 30, "cohort": "hormuz_crossing",
         "retention_share": 0.01},
    ])
    with pytest.raises(ValueError, match="all_resolved"):
        ns.selectivity_contrast(change)


def test_retention_and_contrast_arithmetic():
    legs = _synthetic_legs()
    frame = ns.support_denominators(
        legs, terminal_radius_km=30, census_eligible_imos=100
    )
    change = ns.support_change(frame).set_index("cohort")
    assert float(change.loc["all_resolved", "retention_share"]) == pytest.approx(
        9 / 20
    )
    assert float(change.loc["hormuz_crossing", "retention_share"]) == pytest.approx(
        1 / 10
    )
    contrast = ns.selectivity_contrast(ns.support_change(frame)).iloc[0]
    assert contrast["retention_share_ratio"] == pytest.approx((1 / 10) / (9 / 20))
    assert bool(contrast["selective_support_loss_exceeds_general"]) is True




def _valid_denominators() -> pd.DataFrame:
    legs = _synthetic_legs()
    return ns.support_denominators(
        legs, terminal_radius_km=30, census_eligible_imos=100
    ).assign(panel="full_resolved_panel")


def test_guard_accepts_a_well_formed_denominator_table():
    guard_denominators(_valid_denominators())


def test_guard_rejects_a_broken_cohort_partition():
    corrupted = _valid_denominators()
    mask = corrupted["cohort"].eq("non_gulf") & corrupted["sample_period"].eq("pre")
    corrupted.loc[mask, "n_sequences"] = 999
    with pytest.raises(AssertionError, match="do not partition"):
        guard_denominators(corrupted)


def test_guard_rejects_a_cohort_exceeding_its_overall_denominator():
    corrupted = _valid_denominators()
    parts = ["hormuz_crossing", "inside_hormuz_non_crossing", "non_gulf"]
    corrupted = corrupted.loc[~corrupted["cohort"].isin(parts[1:])]
    mask = corrupted["cohort"].eq("hormuz_crossing")
    corrupted.loc[mask, "n_sequences"] = 10_000
    with pytest.raises(AssertionError, match="exceeds its overall denominator"):
        guard_denominators(corrupted)


def test_guard_rejects_a_missing_overall_denominator():
    corrupted = _valid_denominators()
    corrupted = corrupted.loc[~corrupted["cohort"].eq("all_resolved")]
    with pytest.raises(AssertionError, match="without its overall denominator"):
        guard_denominators(corrupted)


def test_guard_rejects_a_negative_count():
    corrupted = _valid_denominators()
    corrupted.loc[0, "n_sequences"] = -1
    with pytest.raises(AssertionError, match="negative support count"):
        guard_denominators(corrupted)


def test_guard_rejects_impossible_census_coverage():
    corrupted = _valid_denominators()
    corrupted.loc[0, "census_coverage_share"] = 1.5
    with pytest.raises(AssertionError, match="census coverage"):
        guard_denominators(corrupted)


def test_guard_rejects_an_empty_table():
    with pytest.raises(AssertionError, match="empty"):
        guard_denominators(_valid_denominators().iloc[0:0])


def test_upstream_hash_drift_stops_the_phase():
    design, _ = _design()
    corrupted = json.loads(json.dumps(design["upstream_registered_artifacts"]))
    corrupted["capacity_voyages"]["sha256"] = "0" * 64
    with pytest.raises(ValueError, match="hash drift"):
        load_verified_inputs({
            **design,
            "upstream_registered_artifacts": corrupted,
        })


def test_missing_frozen_radius_is_rejected():
    design, _ = _design()
    voyages = pd.DataFrame({
        "terminal_match_radius_km": [30, 30],
        "sample_period": ["pre", "post"],
    })
    carriers = pd.DataFrame({"imo": [1, 2]})
    with pytest.raises(ValueError, match="lacks frozen radii"):
        validate_inputs(design, voyages, carriers)


def test_duplicate_census_imo_is_rejected():
    design, _ = _design()
    voyages = pd.DataFrame({
        "terminal_match_radius_km": [10, 20, 30, 30],
        "sample_period": ["pre", "pre", "pre", "post"],
    })
    carriers = pd.DataFrame({"imo": [1, 1]})
    with pytest.raises(ValueError, match="one row per IMO"):
        validate_inputs(design, voyages, carriers)


def test_audit_expectation_detects_a_refutation():
    """A wrong benchmark must be reported as not reproduced, never smoothed."""
    design, _ = _design()
    sensitivity = pd.DataFrame([
        {"terminal_radius_km": 30, "cohort": "all_resolved",
         "pre_sequences": 971, "post_sequences": 746},
        {"terminal_radius_km": 30, "cohort": "hormuz_crossing",
         "pre_sequences": 999, "post_sequences": 2},
    ])
    audit = build_audit_expectation(design, sensitivity)
    assert audit["fully_reproduced"] is False
    assert audit["checks"]["hormuz_crossing_pre_sequences"]["reproduced"] is False
    assert audit["checks"]["all_resolved_pre_sequences"]["reproduced"] is True




def test_design_freezes_the_three_radii_and_a_primary():
    design, _ = _design()
    assert list(design["terminal_radius_km_grid"]) == [10, 20, 30]
    assert int(design["primary_terminal_radius_km"]) == 30
    assert set(design["cohorts"]) == set(ns.COHORTS)
    assert design["freeze_status"]["timing"] == (
        "frozen_before_generation_not_preregistered"
    )


def test_design_forbids_causal_and_ais_dark_throughput_claims():
    design, _ = _design()
    guards = design["reporting_guards"]
    assert guards["is_ATT"] is False
    assert guards["is_causal_identification"] is False
    assert guards["ais_dark_throughput_inference_permitted"] is False
    assert "not observed voyages" in guards["construct_label"]
    assert "NOT evidence that no ship sailed" in guards["missing_edge_interpretation"]




@needs_upstream
def test_registered_upstream_artifacts_were_not_rewritten():
    design, _ = _design()
    assert_upstream_untouched(design)


@needs_outputs
def test_audit_benchmark_is_reproduced_and_recorded():
    design, _ = _design()
    audit = json.loads(
        output_path(design, "audit_expectation_json").read_text(encoding="utf-8")
    )
    assert audit["terminal_radius_km"] == 30
    assert audit["checks"]["hormuz_crossing_pre_sequences"]["observed"] == 145
    assert audit["checks"]["hormuz_crossing_post_sequences"]["observed"] == 2
    assert audit["checks"]["all_resolved_pre_sequences"]["observed"] == 971
    assert audit["checks"]["all_resolved_post_sequences"]["observed"] == 746
    assert audit["fully_reproduced"] is True


@needs_outputs
def test_written_denominators_satisfy_every_structural_guard():
    design, _ = _design()
    denominators = pd.read_csv(output_path(design, "denominators_csv"))
    guard_denominators(denominators)
    assert set(denominators["panel"]) == {
        "full_resolved_panel",
        "both_period_balanced_cohort",
    }
    expected = {
        (panel, int(radius), cohort, period)
        for panel in ("full_resolved_panel", "both_period_balanced_cohort")
        for radius in design["terminal_radius_km_grid"]
        for cohort in ns.COHORTS
        for period in ns.PERIODS
    }
    actual = set(zip(
        denominators["panel"],
        denominators["terminal_radius_km"],
        denominators["cohort"],
        denominators["sample_period"],
    ))
    assert actual == expected


@needs_outputs
def test_balanced_cohort_never_exceeds_the_full_panel():
    design, _ = _design()
    denominators = pd.read_csv(output_path(design, "denominators_csv"))
    keys = ["terminal_radius_km", "cohort", "sample_period"]
    full = denominators.loc[
        denominators["panel"].eq("full_resolved_panel")
    ].set_index(keys)
    balanced = denominators.loc[
        denominators["panel"].eq("both_period_balanced_cohort")
    ].set_index(keys)
    aligned = balanced.join(full, rsuffix="_full")
    assert aligned["n_sequences"].le(aligned["n_sequences_full"]).all()
    assert aligned["n_unique_imos"].le(aligned["n_unique_imos_full"]).all()


@needs_outputs
def test_selectivity_direction_is_reported_for_every_radius():
    design, _ = _design()
    sensitivity = pd.read_csv(output_path(design, "radius_sensitivity_csv"))
    for radius in design["terminal_radius_km_grid"]:
        subset = sensitivity.loc[sensitivity["terminal_radius_km"].eq(radius)]
        assert not subset.empty
        indexed = subset.set_index("cohort")
        overall = float(indexed.loc["all_resolved", "retention_share"])
        selective = float(indexed.loc["hormuz_crossing", "retention_share"])
        assert 0.0 <= selective <= 1.0
        assert 0.0 <= overall <= 1.0
        assert bool(
            indexed.loc["hormuz_crossing", "selective_support_loss_exceeds_general"]
        ) is (selective < overall)


@needs_outputs
def test_documentation_states_the_support_boundary_and_avoids_throughput_claims():
    design, _ = _design()
    text = output_path(design, "documentation_markdown").read_text(encoding="utf-8")
    lowered = text.lower()
    assert "NEEDS-VERIFY" in text
    assert "not evidence that no ship sailed" in lowered
    assert "ais-dark physical throughput" in lowered
    assert "not an average treatment effect" in text
    for banned in (
        "proves that no ship sailed",
        "physical rerouting",
        "observed cargo ton-miles",
        "actual throughput fell",
        "causally identified",
        "statistically significant",
    ):
        assert banned not in text


@needs_outputs
def test_manifest_matches_its_live_rebuild():
    written = json.loads(manifest_path().read_text(encoding="utf-8"))
    assert written == build_manifest()
    assert written["upstream_artifacts_mutated"] is False
    assert written["ais_dark_throughput_inferred"] is False
    assert written["audit_expectation_fully_reproduced"] is True
    assert written["verification_state"] == "NEEDS-VERIFY"
    assert written["core_run_all_dependency"] == "required_for_final_integration"


@needs_outputs
def test_manifest_output_hashes_match_the_files_on_disk():
    written = json.loads(manifest_path().read_text(encoding="utf-8"))
    for relative, expected in written["output_sha256"].items():
        assert sha256_file(config.ROOT / relative) == expected


@needs_upstream
def test_resolved_legs_reuse_the_exposure_definition_at_every_radius():
    design, _ = _design()
    voyages, terminals, _ = load_verified_inputs(design)
    for radius in design["terminal_radius_km_grid"]:
        legs = resolved_legs(design, voyages, terminals, int(radius))
        assert legs["terminal_match_radius_km"].eq(int(radius)).all()
        assert legs.loc[legs["hormuz_exposed_leg"], "inside_hormuz_origin"].all()
