"""Structural and corruption tests for the task-10 final integration audit.

The scanner has two ways to fail and both are tested. It can be too permissive,
missing a genuinely asserted stale claim -- so planted violations must still be
flagged. It can be too aggressive, flagging the negations and prohibitions that
this repository is full of by design -- so hedged text must still be cleared.
"""
from __future__ import annotations

import json

import pandas as pd
import pytest

from lngfreight import config
from lngfreight.claim_audit import (
    StalePattern,
    clearing_marker,
    context_window,
    flagged,
    inline_negation,
    scan_documents,
    scan_text,
    source_confusion_hits,
    uncited_numeric_lines,
)

from freeze_final_integration_audit import (
    assert_no_asserted_stale_claims,
    assert_upstream_manifests_present,
    build_manifest,
    manifest_path,
)
from run_final_integration_audit import (
    build_claim_ledger,
    build_defence_answers,
    collect_documents,
    guard_ledger,
    load_design,
    output_path,
    sha256_file,
    stale_patterns,
)


ASSERTED = {
    "planted.md": (
        "The estimated ATT is 52.8 transits per day.\n"
        "There was no rebound in tanker traffic after the MoU.\n"
        "Our results demonstrate physical rerouting of Qatari cargoes.\n"
        "The effect is statistically significant.\n"
        "This is a variance decomposition of the shortfall.\n"
    )
}
HEDGED = {
    "hedged.md": (
        "This is not an ATT and never claims causal identification.\n"
        "The phrase “no rebound” was replaced by rebound then relapse.\n"
        "These are sensitivity ranges, not\n"
        "variance decompositions.\n"
        "It is not evidence of physical rerouting.\n"
    )
}


def _design():
    return load_design()


def _patterns():
    design, _ = _design()
    return stale_patterns(design)


def _outputs_present() -> bool:
    design, _ = _design()
    return all(
        output_path(design, key).is_file()
        for key in (
            "stale_claim_scan_csv",
            "claim_ledger_csv",
            "diagnostics_json",
            "audit_markdown",
            "defence_markdown",
            "manifest_json",
        )
    )


needs_outputs = pytest.mark.skipif(
    not _outputs_present(), reason="final integration artifacts are not generated"
)


# --------------------------------------------------------------------------
# The scanner must still bite
# --------------------------------------------------------------------------


def test_planted_stale_claims_are_all_flagged():
    """Guards against a classifier so permissive it can never fail."""
    scan = scan_documents(ASSERTED, _patterns())
    assert not scan.empty
    assert scan["verdict"].eq("flagged").all(), scan.to_dict("records")
    assert len(flagged(scan)) >= 5


@pytest.mark.parametrize(
    "sentence",
    [
        "The estimated ATT is 52.8 transits per day.",
        "There was no rebound in tanker traffic.",
        "Our results demonstrate physical rerouting.",
        "The effect is statistically significant.",
    ],
)
def test_each_asserted_sentence_is_flagged_individually(sentence):
    rows = scan_text("x.md", sentence, _patterns())
    assert rows, f"no pattern matched: {sentence}"
    assert any(row["verdict"] == "flagged" for row in rows)


# --------------------------------------------------------------------------
# The scanner must not cry wolf
# --------------------------------------------------------------------------


def test_hedged_text_is_cleared():
    scan = scan_documents(HEDGED, _patterns())
    assert not scan.empty
    assert scan["verdict"].eq("cleared").all(), scan.loc[
        scan["verdict"].eq("flagged")
    ].to_dict("records")


def test_negation_on_an_adjacent_line_clears_the_hit():
    """Prose negation often lands on the neighbouring line."""
    text = "These are sensitivity ranges, not\nvariance decompositions.\n"
    rows = scan_text("x.md", text, [StalePattern("s", "variance decomposition")])
    assert rows and all(row["verdict"] == "cleared" for row in rows)

    lone = scan_text(
        "x.md",
        "This is a variance decomposition.\n",
        [StalePattern("s", "variance decomposition")],
    )
    assert lone and all(row["verdict"] == "flagged" for row in lone)


@pytest.mark.parametrize(
    "line", ["no ATT language here", "the non-ATT estimand", "a non ATT design"]
)
def test_inline_negation_clears_fused_negations(line):
    rows = scan_text("x.md", line, [StalePattern("c", r"\bATT\b", regex=True)])
    assert rows and all(row["verdict"] == "cleared" for row in rows)


def test_inline_negation_helper_is_position_sensitive():
    line = "the non-ATT estimand"
    assert inline_negation(line, line.index("ATT")) is not None
    other = "the ATT estimand"
    assert inline_negation(other, other.index("ATT")) is None


def test_context_window_spans_neighbouring_lines():
    lines = ["alpha", "beta", "gamma", "delta", "epsilon"]
    window = context_window(lines, 2, radius=1)
    assert "beta" in window and "gamma" in window and "delta" in window
    assert "alpha" not in window


def test_clearing_marker_reports_why_it_cleared():
    assert clearing_marker("this is not an att", "this is not an att").startswith(
        "negated:"
    )
    assert clearing_marker("is_att: false", "is_att: false").startswith(
        "structural:"
    )
    assert clearing_marker("the att value", "the att value") is None


# --------------------------------------------------------------------------
# Layer separation
# --------------------------------------------------------------------------


def test_conflating_portwatch_with_lng_specific_is_flagged():
    documents = {
        "bad.md": "The PortWatch tanker transit series is our LNG-specific measure.\n"
    }
    hits = source_confusion_hits(documents)
    assert len(hits) == 1
    assert hits.iloc[0]["verdict"] == "flagged"


@pytest.mark.parametrize(
    "line",
    [
        "PortWatch is all-tanker while the WTO index is LNG-specific.",
        "PortWatch (primary) -> GIE ALSI (LNG-specific, daily) -> Eurostat",
        "The tanker transit count is not an LNG-specific quantity.",
    ],
)
def test_contrasted_or_listed_layers_are_cleared(line):
    hits = source_confusion_hits({"ok.md": line + "\n"})
    if len(hits):
        assert hits.iloc[0]["verdict"] == "cleared"


# --------------------------------------------------------------------------
# Citation checking
# --------------------------------------------------------------------------


def test_uncited_number_is_reported_and_cited_number_is_not():
    uncited = uncited_numeric_lines(
        "The shortfall was 6868.996 transits over the window.\n"
    )
    assert len(uncited) == 1

    cited = uncited_numeric_lines(
        "The shortfall was 6868.996 transits.\n"
        "Source: data/processed/model_vintage_matrix_summary.csv\n"
    )
    assert cited == []


# --------------------------------------------------------------------------
# Claim ledger and defence answers
# --------------------------------------------------------------------------


def test_every_claim_cites_an_existing_artifact_and_a_limitation():
    design, _ = _design()
    ledger = build_claim_ledger(design)
    assert ledger["artifact_exists"].all()
    assert ledger["artifact_sha256"].str.len().eq(64).all()
    assert not ledger["limitation"].str.strip().eq("").any()
    assert not ledger["claim_id"].duplicated().any()


def test_ledger_keeps_portwatch_and_wto_layers_separate():
    design, _ = _design()
    ledger = build_claim_ledger(design)
    layers = set(ledger["source_layer"])
    assert "portwatch_all_tanker" in layers
    assert "wto_lng_specific" in layers


def test_guard_rejects_a_claim_with_a_missing_artifact():
    design, _ = _design()
    ledger = build_claim_ledger(design)
    ledger.loc[0, "artifact_exists"] = False
    with pytest.raises(AssertionError, match="missing artifact"):
        guard_ledger(ledger)


def test_guard_rejects_a_claim_without_a_limitation():
    design, _ = _design()
    ledger = build_claim_ledger(design)
    ledger.loc[0, "limitation"] = "  "
    with pytest.raises(AssertionError, match="blank limitation"):
        guard_ledger(ledger)


def test_guard_rejects_dropping_the_lng_specific_layer():
    design, _ = _design()
    ledger = build_claim_ledger(design)
    ledger = ledger.loc[~ledger["source_layer"].eq("wto_lng_specific")]
    with pytest.raises(AssertionError, match="LNG-specific"):
        guard_ledger(ledger)


def test_every_defence_challenge_has_a_cited_answer():
    design, _ = _design()
    ledger = build_claim_ledger(design)
    answers = build_defence_answers(design, ledger)
    assert len(answers) == len(design["defence_challenges"])
    for answer in answers:
        assert answer["short_answer"].strip()
        assert answer["detail"].strip()
        assert answer["concession"].strip()
        assert answer["artifacts"]
        for artifact in answer["artifacts"]:
            assert (config.ROOT / artifact).is_file()


def test_missing_defence_answer_is_rejected():
    design, _ = _design()
    ledger = build_claim_ledger(design)
    broken = {
        **design,
        "defence_challenges": [
            *design["defence_challenges"],
            {"challenge_id": "unprepared", "question": "What about X?"},
        ],
    }
    with pytest.raises(AssertionError, match="no prepared answer"):
        build_defence_answers(broken, ledger)


# --------------------------------------------------------------------------
# Governance and generated artifacts
# --------------------------------------------------------------------------


def test_design_preserves_the_governance_boundaries():
    design, _ = _design()
    assert design["scope"]["edits_formal_proposal"] is False
    assert design["scope"]["admits_new_data"] is False
    assert design["scope"]["admits_restricted_material"] is False
    guards = design["reporting_guards"]
    assert guards["is_ATT"] is False
    assert guards["five_percent_significance_claim_permitted"] is False
    assert guards["portwatch_and_wto_layers_must_stay_distinct"] is True
    assert guards["formal_proposal_edited"] is False


def test_open_reproducibility_boundaries_are_declared():
    design, _ = _design()
    boundaries = design["open_reproducibility_boundaries"]
    assert "august_raw_byte_archive" in boundaries
    assert "historical_source_payload_gaps" in boundaries
    assert "core_run_manifest_staleness" in boundaries
    assert boundaries["core_run_manifest_staleness"][
        "requires_explicit_approval"
    ] is True
    for spec in boundaries.values():
        assert spec["blocks_submission"] is False
        assert str(spec["description"]).strip()


def test_upstream_manifests_are_present():
    design, _ = _design()
    pins = assert_upstream_manifests_present(design)
    assert set(pins) == set(design["integrity_pins"])
    assert all(len(value) == 64 for value in pins.values())


def test_excluded_paths_are_recorded_not_silent():
    design, _ = _design()
    excluded = design["excluded_paths"]
    assert "docs/DECISION_LOG.md" in excluded
    documents = collect_documents(design)
    for path in excluded:
        assert path not in documents


@needs_outputs
def test_no_asserted_stale_claim_survives_in_the_repository():
    design, _ = _design()
    diagnostics = json.loads(
        output_path(design, "diagnostics_json").read_text(encoding="utf-8")
    )
    assert_no_asserted_stale_claims(diagnostics)
    assert diagnostics["stale_claims_flagged"] == 0
    assert diagnostics["source_layer_confusion_flagged"] == 0
    assert diagnostics["stale_claim_occurrences"] > 0, (
        "a zero-occurrence scan would mean the patterns stopped matching"
    )


@needs_outputs
def test_written_scan_matches_its_live_rebuild():
    design, _ = _design()
    written = pd.read_csv(
        output_path(design, "stale_claim_scan_csv"), keep_default_na=False
    )
    documents = collect_documents(design)
    live = scan_documents(
        documents,
        stale_patterns(design),
        context_radius=int(design["context_radius_lines"]),
    )
    pd.testing.assert_frame_equal(
        written, live, check_dtype=False, check_exact=True
    )


@needs_outputs
def test_documents_state_the_boundaries_and_open_items():
    design, _ = _design()
    audit = output_path(design, "audit_markdown").read_text(encoding="utf-8")
    defence = output_path(design, "defence_markdown").read_text(encoding="utf-8")
    assert "NEEDS-VERIFY" in audit and "NEEDS-VERIFY" in defence
    assert "formal proposal is unedited" in audit
    assert "august_raw_byte_archive" in audit
    assert "core_run_manifest_staleness" in audit
    for key in ("arx_admissibility", "mutable_vintage"):
        question = next(
            item["question"]
            for item in design["defence_challenges"]
            if item["challenge_id"] == key
        )
        assert question in defence
    assert "Concede this." in defence


@needs_outputs
def test_manifest_matches_its_live_rebuild():
    written = json.loads(manifest_path().read_text(encoding="utf-8"))
    assert written == build_manifest()
    assert written["stale_claims_flagged"] == 0
    assert written["source_layer_confusion_flagged"] == 0
    assert written["formal_proposal_edited"] is False
    assert written["restricted_material_included"] is False
    assert written["third_layer_admitted"] is False
    assert written["verification_state"] == "NEEDS-VERIFY"


@needs_outputs
def test_manifest_output_hashes_match_the_files_on_disk():
    written = json.loads(manifest_path().read_text(encoding="utf-8"))
    for relative, expected in written["output_sha256"].items():
        assert sha256_file(config.ROOT / relative) == expected
