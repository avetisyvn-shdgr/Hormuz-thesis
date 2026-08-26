"""Structural and corruption tests for the task-8 route-burden decomposition.

These tests police the decomposition algebra and the construct boundary. They
verify exact reconciliation, the independent identity for the entry/exit
residual, invariance of that residual to index-number weighting, the
percent-instability flag, and the prohibited-label guard. They do not assert
that the burden rose by any particular amount.
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from lngfreight import config
from lngfreight import route_burden as rb

from freeze_route_burden_decomposition import (
    assert_upstream_untouched,
    build_manifest,
    manifest_path,
)
from run_route_burden_decomposition import (
    PAIR_COLUMN,
    build_audit_expectation,
    both_period_carrier_restriction,
    complete_case,
    guard_decomposition,
    load_design,
    load_verified_inputs,
    output_path,
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
            "decomposition_csv",
            "weighting_sensitivity_csv",
            "pair_support_csv",
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
    not _outputs_present(), reason="route-burden artifacts are not generated"
)
needs_upstream = pytest.mark.skipif(
    not _upstream_present(), reason="vessel-branch upstream artifacts are absent"
)

OUTCOME = "burden"


def _panel(records: list[tuple]) -> pd.DataFrame:
    """(period, pair, imo, burden) tuples -> a complete-case frame."""
    return pd.DataFrame(
        [
            {
                "sample_period": period,
                PAIR_COLUMN: pair,
                "imo": imo,
                OUTCOME: float(burden),
            }
            for period, pair, imo, burden in records
        ]
    )


def _balanced_panel() -> pd.DataFrame:
    return _panel([
        ("pre", "A->X", 1, 100.0), ("pre", "A->X", 2, 120.0),
        ("pre", "B->Y", 3, 300.0),
        ("post", "A->X", 1, 110.0), ("post", "B->Y", 3, 320.0),
        ("post", "B->Y", 4, 340.0),
    ])


# --------------------------------------------------------------------------
# Decomposition algebra
# --------------------------------------------------------------------------


@pytest.mark.parametrize("scheme", rb.WEIGHTING_SCHEMES)
def test_components_reconcile_exactly(scheme):
    result = rb.decompose(
        _balanced_panel(),
        pair_column=PAIR_COLUMN,
        outcome_column=OUTCOME,
        weighting_scheme=scheme,
    )
    assert result.reconciliation_error <= 1e-9
    assert result.common_pair_share_reweighting + result.within_common_pair_capacity_mix \
        + result.entry_exit_residual == pytest.approx(result.total_change)
    assert result.total_change == pytest.approx(result.post_mean - result.pre_mean)


@pytest.mark.parametrize("scheme", rb.WEIGHTING_SCHEMES)
def test_entry_exit_residual_matches_its_conditional_mean_identity(scheme):
    """The residual must be the support term, not accumulated arithmetic slack."""
    panel = _balanced_panel()
    result = rb.decompose(
        panel,
        pair_column=PAIR_COLUMN,
        outcome_column=OUTCOME,
        weighting_scheme=scheme,
    )
    identity = rb.residual_identity_check(
        panel, pair_column=PAIR_COLUMN, outcome_column=OUTCOME
    )
    assert result.entry_exit_residual == pytest.approx(identity, abs=1e-9)


def test_entry_exit_residual_is_invariant_to_weighting():
    panel = _balanced_panel()
    residuals = {
        scheme: rb.decompose(
            panel,
            pair_column=PAIR_COLUMN,
            outcome_column=OUTCOME,
            weighting_scheme=scheme,
        ).entry_exit_residual
        for scheme in rb.WEIGHTING_SCHEMES
    }
    values = list(residuals.values())
    assert max(values) - min(values) == pytest.approx(0.0, abs=1e-9)


def test_share_and_within_terms_do_depend_on_weighting():
    """The index-number ambiguity is real and must not be hidden."""
    panel = _balanced_panel()
    shares = {
        scheme: rb.decompose(
            panel,
            pair_column=PAIR_COLUMN,
            outcome_column=OUTCOME,
            weighting_scheme=scheme,
        ).common_pair_share_reweighting
        for scheme in rb.WEIGHTING_SCHEMES
    }
    assert len(set(round(v, 9) for v in shares.values())) > 1


def test_no_pair_movement_gives_zero_share_and_entry_exit_terms():
    """Identical composition: all change must land in the within-pair term."""
    panel = _panel([
        ("pre", "A->X", 1, 100.0), ("pre", "B->Y", 2, 200.0),
        ("post", "A->X", 1, 150.0), ("post", "B->Y", 2, 250.0),
    ])
    result = rb.decompose(
        panel, pair_column=PAIR_COLUMN, outcome_column=OUTCOME
    )
    assert result.common_pair_share_reweighting == pytest.approx(0.0, abs=1e-9)
    assert result.entry_exit_residual == pytest.approx(0.0, abs=1e-9)
    assert result.within_common_pair_capacity_mix == pytest.approx(50.0, abs=1e-9)


def test_pure_share_shift_gives_zero_within_term():
    """Same pair means, different mix: nothing may land in the within term."""
    panel = _panel([
        ("pre", "A->X", 1, 100.0), ("pre", "A->X", 2, 100.0),
        ("pre", "B->Y", 3, 200.0),
        ("post", "A->X", 1, 100.0),
        ("post", "B->Y", 3, 200.0), ("post", "B->Y", 4, 200.0),
    ])
    result = rb.decompose(
        panel, pair_column=PAIR_COLUMN, outcome_column=OUTCOME
    )
    assert result.within_common_pair_capacity_mix == pytest.approx(0.0, abs=1e-9)
    assert result.entry_exit_residual == pytest.approx(0.0, abs=1e-9)
    assert result.common_pair_share_reweighting == pytest.approx(
        result.total_change, abs=1e-9
    )


def test_entering_pair_lands_in_the_entry_exit_residual():
    panel = _panel([
        ("pre", "A->X", 1, 100.0),
        ("post", "A->X", 1, 100.0), ("post", "NEW->Z", 9, 500.0),
    ])
    result = rb.decompose(
        panel, pair_column=PAIR_COLUMN, outcome_column=OUTCOME
    )
    assert result.n_post_only_pairs == 1
    assert result.n_pre_only_pairs == 0
    assert result.common_pair_share_reweighting == pytest.approx(0.0, abs=1e-9)
    assert result.within_common_pair_capacity_mix == pytest.approx(0.0, abs=1e-9)
    assert result.entry_exit_residual == pytest.approx(
        result.total_change, abs=1e-9
    )


def test_percent_stability_ratio_flags_offsetting_components():
    """A near-zero total with large offsetting parts must be detectable."""
    # Mass moves from a low-burden pair to a high-burden pair (share term up)
    # while a very-high-burden pair leaves support entirely (residual down), so
    # the two largely offset.
    records = []
    records += [("pre", "A->X", i, 100.0) for i in range(8)]
    records += [("pre", "B->Y", 10 + i, 900.0) for i in range(2)]
    records += [("pre", "C->Z", 20 + i, 3000.0) for i in range(5)]
    records += [("post", "A->X", i, 100.0) for i in range(2)]
    records += [("post", "B->Y", 10 + i, 900.0) for i in range(8)]
    result = rb.decompose(
        _panel(records), pair_column=PAIR_COLUMN, outcome_column=OUTCOME
    )

    assert result.common_pair_share_reweighting == pytest.approx(480.0)
    assert result.entry_exit_residual == pytest.approx(-913.3333, abs=1e-3)
    assert result.total_change == pytest.approx(-433.3333, abs=1e-3)
    assert np.isfinite(result.percent_stability_ratio())
    assert result.percent_stability_ratio() > 2.0

    # The percentages still sum to 100 yet are individually meaningless: one
    # exceeds 200% and another is negative while the total change is negative.
    percentages = result.component_percentages()
    assert sum(percentages.values()) == pytest.approx(100.0)
    assert max(abs(v) for v in percentages.values()) > 100.0


def test_zero_total_change_gives_infinite_ratio_and_nan_percentages():
    panel = _panel([
        ("pre", "A->X", 1, 100.0),
        ("post", "A->X", 1, 100.0),
    ])
    result = rb.decompose(
        panel, pair_column=PAIR_COLUMN, outcome_column=OUTCOME
    )
    assert result.total_change == pytest.approx(0.0)
    assert np.isinf(result.percent_stability_ratio())
    assert all(np.isnan(v) for v in result.component_percentages().values())


def test_decompose_rejects_bad_inputs():
    panel = _balanced_panel()
    with pytest.raises(ValueError, match="Unknown weighting_scheme"):
        rb.decompose(
            panel, pair_column=PAIR_COLUMN, outcome_column=OUTCOME,
            weighting_scheme="whichever_looks_best",
        )
    with pytest.raises(ValueError, match="lacks required column"):
        rb.decompose(panel, pair_column="nope", outcome_column=OUTCOME)
    nulled = panel.copy()
    nulled.loc[0, OUTCOME] = np.nan
    with pytest.raises(ValueError, match="null outcomes"):
        rb.decompose(nulled, pair_column=PAIR_COLUMN, outcome_column=OUTCOME)
    with pytest.raises(ValueError, match="non-empty pre and post"):
        rb.decompose(
            panel.loc[panel["sample_period"].eq("pre")],
            pair_column=PAIR_COLUMN, outcome_column=OUTCOME,
        )


def test_no_common_pair_is_rejected_rather_than_silently_zeroed():
    panel = _panel([
        ("pre", "A->X", 1, 100.0),
        ("post", "B->Y", 2, 200.0),
    ])
    with pytest.raises(ValueError, match="no terminal pair is supported in both"):
        rb.decompose(panel, pair_column=PAIR_COLUMN, outcome_column=OUTCOME)


def test_pair_support_table_labels_entry_and_exit():
    table = rb.pair_support_table(
        _balanced_panel(), pair_column=PAIR_COLUMN, outcome_column=OUTCOME
    ).set_index("terminal_pair")
    assert table.loc["A->X", "support_status"] == "common"
    assert table.loc["B->Y", "support_status"] == "common"
    assert set(table["support_status"]).issubset(
        {"common", "pre_only_exit", "post_only_entry"}
    )


def test_both_period_carrier_restriction_keeps_only_shared_imos():
    panel = _balanced_panel()
    restricted = both_period_carrier_restriction(panel)
    assert set(restricted["imo"]) == {1, 3}
    assert len(restricted) < len(panel)


# --------------------------------------------------------------------------
# Corruption tests
# --------------------------------------------------------------------------


def _valid_decomposition() -> pd.DataFrame:
    design, _ = _design()
    return pd.DataFrame([{
        "cohort": "all_retained",
        "terminal_radius_km": 30,
        "weighting_scheme": rb.SYMMETRIC,
        "construct_label": design["construct"]["label"],
        "total_change": 100.0,
        "common_pair_share_reweighting": 55.0,
        "within_common_pair_capacity_mix": 1.0,
        "entry_exit_residual": 44.0,
        "common_pair_share_reweighting_percent": 55.0,
        "within_common_pair_capacity_mix_percent": 1.0,
        "entry_exit_residual_percent": 44.0,
        "percent_stability_ratio": 0.55,
        "percent_decomposition_is_unstable": False,
        "reconciliation_error": 0.0,
        "residual_identity_error": 0.0,
        "n_common_pairs": 12,
    }])


def test_guard_accepts_a_well_formed_decomposition():
    design, _ = _design()
    guard_decomposition(design, _valid_decomposition())


def test_guard_rejects_a_failed_reconciliation():
    design, _ = _design()
    corrupted = _valid_decomposition()
    corrupted.loc[0, "reconciliation_error"] = 1.0
    with pytest.raises(AssertionError, match="exact reconciliation"):
        guard_decomposition(design, corrupted)


def test_guard_rejects_components_not_summing_to_the_total():
    design, _ = _design()
    corrupted = _valid_decomposition()
    corrupted.loc[0, "entry_exit_residual"] = 1.0
    with pytest.raises(AssertionError, match="does not equal the total change"):
        guard_decomposition(design, corrupted)


def test_guard_rejects_a_residual_that_breaks_its_identity():
    design, _ = _design()
    corrupted = _valid_decomposition()
    corrupted.loc[0, "residual_identity_error"] = 5.0
    with pytest.raises(AssertionError, match="conditional-mean"):
        guard_decomposition(design, corrupted)


def test_guard_rejects_percentages_not_summing_to_100():
    design, _ = _design()
    corrupted = _valid_decomposition()
    corrupted.loc[0, "entry_exit_residual_percent"] = 10.0
    with pytest.raises(AssertionError, match="percentages do not sum to 100"):
        guard_decomposition(design, corrupted)


def test_guard_rejects_a_drifted_construct_label():
    design, _ = _design()
    corrupted = _valid_decomposition()
    corrupted.loc[0, "construct_label"] = "observed cargo ton-miles"
    with pytest.raises(AssertionError, match="construct label drifted"):
        guard_decomposition(design, corrupted)


def test_guard_rejects_a_mismatched_instability_flag():
    design, _ = _design()
    corrupted = _valid_decomposition()
    corrupted.loc[0, "percent_stability_ratio"] = 99.0
    with pytest.raises(AssertionError, match="instability flag disagrees"):
        guard_decomposition(design, corrupted)


def test_guard_rejects_a_weighting_dependent_residual():
    design, _ = _design()
    corrupted = pd.concat([_valid_decomposition(), _valid_decomposition()])
    corrupted = corrupted.reset_index(drop=True)
    corrupted.loc[1, "weighting_scheme"] = rb.LASPEYRES_SHARE
    corrupted.loc[1, "entry_exit_residual"] = 40.0
    corrupted.loc[1, "common_pair_share_reweighting"] = 59.0
    with pytest.raises(AssertionError, match="varies with weighting scheme"):
        guard_decomposition(design, corrupted)


def test_upstream_hash_drift_stops_the_phase():
    design, _ = _design()
    corrupted = json.loads(json.dumps(design["upstream_registered_artifacts"]))
    corrupted["capacity_voyages"]["sha256"] = "0" * 64
    with pytest.raises(ValueError, match="hash drift"):
        load_verified_inputs({
            **design, "upstream_registered_artifacts": corrupted,
        })


def test_missing_radius_is_rejected():
    design, _ = _design()
    voyages = pd.DataFrame({
        "inferred_nominal_m3_nm_expanded": [1.0],
        "endpoint_status": ["x"], "sample_period": ["pre"],
        "terminal_match_radius_km": [30], "project_id": ["a"],
        "destination_project_id": ["b"], "imo": [1],
    })
    with pytest.raises(ValueError, match="lacks frozen radii"):
        validate_inputs(design, voyages)


# --------------------------------------------------------------------------
# Frozen design contract
# --------------------------------------------------------------------------


def test_design_fixes_the_construct_label_and_prohibited_labels():
    design, _ = _design()
    assert design["construct"]["label"] == (
        "modeled distance per nominal vessel-capacity m3 among retained "
        "inferred voyages"
    )
    prohibited = design["construct"]["prohibited_labels"]
    assert "observed cargo ton-miles" in prohibited
    assert "physical rerouting" in prohibited
    assert "evidence that individual ships sailed farther" in prohibited


def test_design_forbids_causal_and_throughput_claims():
    design, _ = _design()
    guards = design["reporting_guards"]
    assert guards["is_ATT"] is False
    assert guards["is_causal_identification"] is False
    assert guards["is_observed_cargo_ton_miles"] is False
    assert guards["is_physical_rerouting_evidence"] is False
    assert guards["implies_individual_ships_sailed_farther"] is False
    assert guards["ais_dark_throughput_inference_permitted"] is False


def test_design_declares_the_symmetric_scheme_primary():
    design, _ = _design()
    roles = {
        name: spec["role"] for name, spec in design["weighting_schemes"].items()
    }
    assert roles[rb.SYMMETRIC] == "primary"
    assert set(roles) == set(rb.WEIGHTING_SCHEMES)
    assert list(roles.values()).count("primary") == 1


def test_audit_expectation_detects_a_refutation():
    design, _ = _design()
    wrong = _valid_decomposition()
    wrong.loc[0, "total_change"] = 1.0
    audit = build_audit_expectation(design, wrong)
    assert audit["fully_reproduced"] is False
    assert audit["checks"][
        "total_change_m3_nm_per_retained_sequence"
    ]["reproduced"] is False


# --------------------------------------------------------------------------
# Generated artifacts
# --------------------------------------------------------------------------


@needs_upstream
def test_registered_upstream_artifacts_were_not_rewritten():
    design, _ = _design()
    assert_upstream_untouched(design)


@needs_upstream
def test_complete_case_excludes_nothing_silently():
    design, _ = _design()
    voyages, _ = load_verified_inputs(design)
    outcome = design["construct"]["outcome_column"]
    for radius in design["terminal_radius_km_grid"]:
        retained, exclusions = complete_case(design, voyages, int(radius))
        assert retained[outcome].notna().all()
        assert all(value >= 0 for value in exclusions.values())
        resolved = voyages.loc[
            voyages["terminal_match_radius_km"].astype(int).eq(int(radius))
            & voyages["endpoint_status"].eq(
                design["complete_case_rule"]["endpoint_status"]
            )
        ]
        for period in rb.PERIODS:
            kept = int(retained["sample_period"].eq(period).sum())
            total = int(resolved["sample_period"].eq(period).sum())
            assert kept + exclusions[f"excluded_{period}_sequences"] == total


@needs_outputs
def test_audit_benchmark_is_reproduced_and_recorded():
    design, _ = _design()
    audit = json.loads(
        output_path(design, "audit_expectation_json").read_text(encoding="utf-8")
    )
    assert audit["terminal_radius_km"] == 30
    assert audit["weighting_scheme"] == rb.SYMMETRIC
    checks = audit["checks"]
    assert checks["total_change_m3_nm_per_retained_sequence"]["observed"] == (
        pytest.approx(67585181.55, abs=1000.0)
    )
    assert checks["common_pair_share_reweighting_percent"]["observed"] == (
        pytest.approx(54.9, abs=0.1)
    )
    assert checks["entry_exit_residual_percent"]["observed"] == (
        pytest.approx(43.8, abs=0.1)
    )
    assert checks["within_common_pair_capacity_mix_percent"]["observed"] == (
        pytest.approx(1.3, abs=0.1)
    )
    assert audit["fully_reproduced"] is True


@needs_outputs
def test_written_decomposition_satisfies_every_structural_guard():
    design, _ = _design()
    decomposition = pd.read_csv(output_path(design, "decomposition_csv"))
    guard_decomposition(design, decomposition)
    expected = {
        (cohort, int(radius), scheme)
        for cohort in ("all_retained", "both_period_carriers")
        for radius in design["terminal_radius_km_grid"]
        for scheme in rb.WEIGHTING_SCHEMES
    }
    actual = set(zip(
        decomposition["cohort"],
        decomposition["terminal_radius_km"],
        decomposition["weighting_scheme"],
    ))
    assert actual == expected


@needs_outputs
def test_documentation_states_that_the_split_does_not_generalise():
    design, _ = _design()
    text = output_path(design, "documentation_markdown").read_text(encoding="utf-8")
    assert "NEEDS-VERIFY" in text
    assert "does not generalise" in text
    assert design["construct"]["label"] in text
    for banned in design["construct"]["prohibited_labels"]:
        # The prohibited label may appear only inside an explicit negation.
        for line in text.splitlines():
            if banned in line:
                assert "not " in line.lower(), line


@needs_outputs
def test_documentation_does_not_claim_a_universal_rise():
    """The headline direction must not be asserted where the grid disagrees."""
    design, _ = _design()
    diagnostics = json.loads(
        output_path(design, "diagnostics_json").read_text(encoding="utf-8")
    )
    text = output_path(design, "documentation_markdown").read_text(encoding="utf-8")
    cells = (
        diagnostics["radius_sensitivity"]
        + diagnostics["balanced_radius_sensitivity"]
    )
    signs = {bool(item["total_change_is_positive"]) for item in cells}
    assert diagnostics["total_change_sign_consistent_across_grid"] is (
        len(signs) == 1
    )
    if len(signs) > 1:
        assert "not** universal" in text or "not universal" in text
        assert any(
            not item["total_change_is_positive"] for item in cells
        )


@needs_outputs
def test_manifest_matches_its_live_rebuild():
    written = json.loads(manifest_path().read_text(encoding="utf-8"))
    assert written == build_manifest()
    assert written["upstream_artifacts_mutated"] is False
    assert written["audit_expectation_fully_reproduced"] is True
    assert written["component_split_generalises_across_grid"] is False
    assert written["is_observed_cargo_ton_miles"] is False
    assert written["is_physical_rerouting_evidence"] is False
    assert written["verification_state"] == "NEEDS-VERIFY"
    assert written["core_run_all_dependency"] == "none"


@needs_outputs
def test_manifest_output_hashes_match_the_files_on_disk():
    written = json.loads(manifest_path().read_text(encoding="utf-8"))
    for relative, expected in written["output_sha256"].items():
        assert sha256_file(config.ROOT / relative) == expected
