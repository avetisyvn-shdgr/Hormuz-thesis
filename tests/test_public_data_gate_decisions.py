"""Structural and corruption tests for the task-9 public-data gate decisions.

These tests police a governance boundary rather than a numeric result. They
assert that no candidate can be marked GO, that every candidate carries a
permitted use, a prohibited use, rights, coverage, lag, estimand relevance and
kill criteria, that the phase performs no network access, and that it adds no
registered variable and mutates no G4-verified manifest.
"""
from __future__ import annotations

import ast
import json

import pandas as pd
import pytest
import yaml

from lngfreight import config

from freeze_public_data_gate_decisions import (
    BUILDER_PATH,
    FREEZER_PATH,
    build_manifest,
    manifest_path,
)
from run_public_data_gate_decisions import (
    DESIGN_PATH,
    build_table,
    guard_table,
    load_design,
    output_path,
    sha256_file,
    verify_integrity_pins,
)


REQUIRED_CANDIDATES = {
    "era5_reanalysis",
    "sentinel1_sar",
    "gfw_hourly_presence",
    "jodi_gas",
    "marad_advisories",
}
NETWORK_MODULES = {
    "requests",
    "urllib",
    "urllib3",
    "http",
    "httpx",
    "aiohttp",
    "socket",
    "ftplib",
    "cdsapi",
    "sentinelsat",
}


def _design():
    return load_design()


def _outputs_present() -> bool:
    design, _ = _design()
    return all(
        output_path(design, key).is_file()
        for key in (
            "decision_table_csv",
            "diagnostics_json",
            "documentation_markdown",
            "manifest_json",
        )
    )


needs_outputs = pytest.mark.skipif(
    not _outputs_present(), reason="public-data gate artifacts are not generated"
)


# --------------------------------------------------------------------------
# Governance boundary
# --------------------------------------------------------------------------


def test_every_required_candidate_is_covered():
    design, _ = _design()
    assert set(design["candidates"]) == REQUIRED_CANDIDATES


def test_no_candidate_may_be_marked_go():
    design, _ = _design()
    assert design["go_status_permitted"] is False
    assert "GO" not in design["permitted_statuses"]
    table = build_table(design)
    assert not table["status"].str.upper().eq("GO").any()
    assert table["reopening_required"].all()


def test_scope_authorizes_nothing():
    design, _ = _design()
    scope = design["scope"]
    assert scope["authorizes_download"] is False
    assert scope["authorizes_analysis"] is False
    assert scope["authorizes_registry_entry"] is False
    assert scope["authorizes_third_empirical_layer"] is False
    assert scope["preserves_accepted_no_third_layer_plan"] is True


def test_each_candidate_states_the_required_governance_fields():
    design, _ = _design()
    for name, spec in design["candidates"].items():
        for field in (
            "status",
            "permitted_use",
            "prohibited_use",
            "required_rights",
            "coverage",
            "reporting_lag",
            "estimand_relevance",
        ):
            assert str(spec[field]).strip(), f"{name} has a blank {field}"
        assert len(spec["kill_criteria"]) >= 1
        assert spec["reopening_required"] is True


def test_candidate_permitted_uses_match_the_stated_gate_policy():
    """Each candidate's single permitted use must be the narrow one agreed."""
    design, _ = _design()
    candidates = design["candidates"]

    assert candidates["era5_reanalysis"]["status"] == (
        "DEFER_PENDING_SCOPE_REOPENING"
    )
    assert "falsification" in candidates["era5_reanalysis"]["permitted_use"]

    assert candidates["sentinel1_sar"]["status"] == "DEFER_POST_SUBMISSION"
    sar = candidates["sentinel1_sar"]
    assert "scene-level" in sar["permitted_use"]
    assert "throughput multiplier" in sar["prohibited_use"]

    gfw = candidates["gfw_hourly_presence"]
    assert "loitering" in gfw["permitted_use"] or "dwell" in gfw["permitted_use"]
    assert "track reconstruction" in gfw["prohibited_use"]

    jodi = candidates["jodi_gas"]
    assert jodi["status"] == "NO_GO"
    assert "macro context" in jodi["permitted_use"]
    assert str(jodi.get("blocking_reason", "")).strip()

    marad = candidates["marad_advisories"]
    assert "chronology" in marad["permitted_use"]
    assert "identification" in marad["prohibited_use"]


def test_jodi_is_blocked_on_already_triggered_criteria():
    design, _ = _design()
    jodi = design["candidates"]["jodi_gas"]
    triggered = [c for c in jodi["kill_criteria"] if "already triggered" in c]
    assert len(triggered) >= 2, "JODI must be NO_GO on facts, not preference"


# --------------------------------------------------------------------------
# No acquisition actually happens
# --------------------------------------------------------------------------


@pytest.mark.parametrize("script", [BUILDER_PATH, FREEZER_PATH])
def test_phase_scripts_import_no_network_client(script):
    """A governance phase must not even be able to fetch anything."""
    tree = ast.parse(script.read_text(encoding="utf-8"))
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    assert not imported & NETWORK_MODULES, sorted(imported & NETWORK_MODULES)


def test_integrity_pins_hold():
    design, _ = _design()
    pins = verify_integrity_pins(design)
    assert set(pins) == set(design["integrity_pins"])


def test_registry_variable_count_is_pinned_and_unchanged():
    design, _ = _design()
    spec = design["integrity_pins"]["sources_registry"]
    registry = yaml.safe_load(
        (config.ROOT / spec["path"]).read_text(encoding="utf-8")
    )["variables"]
    assert len(registry) == int(spec["registered_variable_count"])
    assert sha256_file(config.ROOT / spec["path"]) == spec["sha256"]


def test_registry_drift_stops_the_phase(tmp_path):
    design, _ = _design()
    corrupted = json.loads(json.dumps(design["integrity_pins"]))
    corrupted["sources_registry"]["sha256"] = "0" * 64
    with pytest.raises(ValueError, match="integrity pin drift"):
        verify_integrity_pins({**design, "integrity_pins": corrupted})


def test_upstream_manifest_drift_stops_the_phase():
    design, _ = _design()
    corrupted = json.loads(json.dumps(design["integrity_pins"]))
    corrupted["route_burden_manifest"]["sha256"] = "0" * 64
    with pytest.raises(ValueError, match="integrity pin drift"):
        verify_integrity_pins({**design, "integrity_pins": corrupted})


# --------------------------------------------------------------------------
# Corruption tests
# --------------------------------------------------------------------------


def _valid_table() -> pd.DataFrame:
    design, _ = _design()
    return build_table(design)


def test_guard_accepts_the_frozen_table():
    design, _ = _design()
    guard_table(design, _valid_table())


def test_guard_rejects_a_go_status():
    design, _ = _design()
    corrupted = _valid_table()
    corrupted.loc[0, "status"] = "GO"
    with pytest.raises(AssertionError, match="unpermitted gate status"):
        guard_table(design, corrupted)


def test_guard_rejects_a_design_that_permits_go():
    design, _ = _design()
    permissive = {
        **design,
        "go_status_permitted": True,
        "permitted_statuses": [*design["permitted_statuses"], "GO"],
    }
    with pytest.raises(AssertionError, match="must not permit a GO status"):
        guard_table(permissive, _valid_table())


def test_guard_rejects_a_candidate_not_requiring_reopening():
    design, _ = _design()
    corrupted = _valid_table()
    corrupted.loc[0, "reopening_required"] = False
    with pytest.raises(AssertionError, match="explicit scope reopening"):
        guard_table(design, corrupted)


def test_guard_rejects_a_missing_candidate():
    design, _ = _design()
    with pytest.raises(AssertionError, match="every candidate"):
        guard_table(design, _valid_table().iloc[1:])


def test_guard_rejects_a_candidate_without_kill_criteria():
    design, _ = _design()
    corrupted = _valid_table()
    corrupted.loc[0, "kill_criteria_count"] = 0
    with pytest.raises(AssertionError, match="kill criterion"):
        guard_table(design, corrupted)


def test_guard_rejects_a_blank_governance_field():
    design, _ = _design()
    corrupted = _valid_table()
    corrupted.loc[0, "required_rights"] = "   "
    with pytest.raises(AssertionError, match="blank required_rights"):
        guard_table(design, corrupted)


def test_guard_rejects_a_no_go_without_a_blocking_reason():
    design, _ = _design()
    corrupted = _valid_table()
    mask = corrupted["status"].eq("NO_GO")
    corrupted.loc[mask, "blocking_reason"] = "not_applicable"
    with pytest.raises(AssertionError, match="blocking reason"):
        guard_table(design, corrupted)


# --------------------------------------------------------------------------
# Generated artifacts
# --------------------------------------------------------------------------


@needs_outputs
def test_written_table_covers_every_candidate_with_no_go_status():
    design, _ = _design()
    table = pd.read_csv(
        output_path(design, "decision_table_csv"), keep_default_na=False
    )
    guard_table(design, table)
    assert set(table["candidate"]) == REQUIRED_CANDIDATES
    assert not table["status"].str.upper().eq("GO").any()


@needs_outputs
def test_documentation_states_the_no_third_layer_preservation():
    design, _ = _design()
    text = output_path(design, "documentation_markdown").read_text(encoding="utf-8")
    lowered = text.lower()
    assert "NEEDS-VERIFY" in text
    assert "no-third-layer plan is preserved" in lowered
    assert "governance decision table" in lowered
    assert "explicit written scope reopening" in lowered
    for banned in (
        "we downloaded",
        "we acquired",
        "now admitted",
        "approved for use",
    ):
        assert banned not in lowered


@needs_outputs
def test_diagnostics_record_zero_acquisition():
    design, _ = _design()
    diagnostics = json.loads(
        output_path(design, "diagnostics_json").read_text(encoding="utf-8")
    )
    assert diagnostics["any_go_status"] is False
    assert diagnostics["all_require_scope_reopening"] is True
    assert diagnostics["registered_variable_count_unchanged"] is True
    assert diagnostics["n_candidates"] == len(REQUIRED_CANDIDATES)
    assert "jodi_gas" in diagnostics["no_go_candidates"]


@needs_outputs
def test_manifest_matches_its_live_rebuild():
    written = json.loads(manifest_path().read_text(encoding="utf-8"))
    assert written == build_manifest()
    assert written["datasets_downloaded"] == 0
    assert written["registry_variables_added"] == 0
    assert written["third_layer_admitted"] is False
    assert written["no_third_layer_plan_preserved"] is True
    assert written["any_go_status"] is False
    assert written["verification_state"] == "NEEDS-VERIFY"
    assert written["core_run_all_dependency"] == "none"


@needs_outputs
def test_manifest_output_hashes_match_the_files_on_disk():
    written = json.loads(manifest_path().read_text(encoding="utf-8"))
    for relative, expected in written["output_sha256"].items():
        assert sha256_file(config.ROOT / relative) == expected


def test_design_file_is_the_single_source_of_the_table():
    """The table must be derivable from the design alone, with no hidden data."""
    design, sha = _design()
    assert sha == sha256_file(DESIGN_PATH)
    table = build_table(design)
    assert len(table) == len(design["candidates"])
