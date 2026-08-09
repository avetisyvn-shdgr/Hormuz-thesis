import json


import freeze_reproducibility as freeze
import freeze_tsfm_run
import run_all
from freeze_reproducibility import (
    CORE_RAW_INPUTS,
    ORCHESTRATED_ARTIFACTS,
    QUARANTINED_RAW_INPUTS,
    core_raw_hashes,
    raw_hashes,
    sha256_file,
    vessel_raw_hashes,
)


from lngfreight import config


def test_sha256_file_is_stable(tmp_path):
    path = tmp_path / "x.txt"
    path.write_text("abc", encoding="utf-8")
    assert sha256_file(path) == (
        "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    )


def test_raw_hashes_excludes_manifests(tmp_path):
    raw = tmp_path / "data" / "raw"
    raw.mkdir(parents=True)
    (raw / "source.csv").write_text("x\n1\n", encoding="utf-8")
    (raw / ".gitkeep").write_text("", encoding="utf-8")
    (raw / "SHA256SUMS").write_text("old", encoding="utf-8")
    (raw / "SHA256SUMS.vessel").write_text("old", encoding="utf-8")
    (raw / "provenance.jsonl").write_text("{}\n", encoding="utf-8")
    assert list(raw_hashes(tmp_path)) == ["data/raw/source.csv"]


def test_core_raw_hashes_cover_exactly_declared_inputs():
    """The core scope is the PortWatch inputs run_all.py consumes; if one is
    renamed or removed the freeze must fail loudly, not silently shrink."""
    hashes = core_raw_hashes(config.ROOT)
    assert set(hashes) == set(CORE_RAW_INPUTS)
    assert len(hashes) == 8
    assert not any("ais_laden_tonmiles_usgc" in path for path in hashes)


def test_vessel_scope_excludes_core_and_archives():
    """Vessel-branch raw set must not overlap the core set or canonicalize
    transient .zip downloads."""
    core = set(CORE_RAW_INPUTS)
    vessel = vessel_raw_hashes(config.ROOT)
    assert core.isdisjoint(vessel)
    assert set(QUARANTINED_RAW_INPUTS).isdisjoint(vessel)
    assert not any(rel.endswith(".zip") for rel in vessel)
    assert "data/raw/natural_earth/ne_110m_land.geojson" in vessel


def test_mislabeled_panama_duplicate_is_truthfully_quarantined():
    renamed = (
        config.ROOT
        / "data/raw/portwatch/"
        "quarantined_panama_tanker_capacity_duplicate__"
        "chokepoint_panama_canal_capacity_tanker.csv"
    )
    active = (
        config.ROOT
        / "data/raw/portwatch/"
        "panama_tanker_capacity__chokepoint_panama_canal_capacity_tanker.csv"
    )
    assert renamed.relative_to(config.ROOT).as_posix() in QUARANTINED_RAW_INPUTS
    assert sha256_file(renamed) == sha256_file(active)


def test_orchestrated_artifact_scope_includes_reported_tsfm_crosscheck():
    assert len(ORCHESTRATED_ARTIFACTS) == len(set(ORCHESTRATED_ARTIFACTS))
    assert {
        "data/processed/tsfm_counterfactual_daily.csv",
        "data/processed/tsfm_counterfactual_summary.csv",
        "data/processed/tsfm_run_manifest.json",
    }.issubset(ORCHESTRATED_ARTIFACTS)
    assert not any("tsfm_benchmark_" in rel for rel in ORCHESTRATED_ARTIFACTS)
    assert "data/processed/tsfm_admission_test.csv" not in ORCHESTRATED_ARTIFACTS
    assert not any("/presentation/" in rel for rel in ORCHESTRATED_ARTIFACTS)
    assert "reports/Hormuz_Thesis_Supervisor_Review.pptx" not in ORCHESTRATED_ARTIFACTS
    assert {
        "data/processed/provenance_audit_summary.json",
        "data/processed/raw_provenance_inventory.csv",
    }.issubset(ORCHESTRATED_ARTIFACTS)


def test_report_consumed_tsfm_summary_is_in_manifest_scope():
    report_builder = (
        config.ROOT / "scripts" / "make_results_summary.py"
    ).read_text(encoding="utf-8")
    assert '_read_processed("tsfm_counterfactual_summary.csv")' in report_builder
    assert (
        "data/processed/tsfm_counterfactual_summary.csv"
        in ORCHESTRATED_ARTIFACTS
    )


def test_run_all_regenerates_reported_tsfm_comparison_in_isolated_env():
    matching = [
        args
        for label, args in run_all.STEPS
        if label == "Run matched-horizon admitted Chronos-2 counterfactual"
    ]
    assert len(matching) == 1
    command = run_all._step_command(matching[0])
    assert command[0].endswith(".venv-bench/bin/python")
    assert command[1:] == [
        "scripts/run_tsfm_counterfactual.py",
        "--model",
        "chronos2",
        "--acknowledge-benchmark-only",
    ]
    assert any(
        label == "Refresh deterministic TSFM provenance"
        and args == ["scripts/freeze_tsfm_run.py"]
        for label, args in run_all.STEPS
    )
    assert run_all.RUN_TRANSCRIPT.name == "reproducibility_run_transcript.txt"
    assert any(
        label == "Audit provenance coverage"
        and args == ["scripts/audit_provenance.py"]
        for label, args in run_all.STEPS
    )


def test_current_provenance_audit_has_no_structural_failures():
    summary = json.loads(
        (config.path("data_processed") / "provenance_audit_summary.json").read_text()
    )
    assert summary["missing_ledger_paths"] == []
    assert summary["resolved_renamed_ledger_paths"]
    assert summary["current_paths_without_v2"] == []
    assert summary["source_payload_hash_failures"] == []
    assert summary["unmapped_free_registry_variables"] == []
    assert summary["frozen_hash_failures"] == []
    assert summary["historical_stale_record_count"] == 4


def test_tsfm_output_hash_ignores_only_wall_clock_runtime(tmp_path):
    path = tmp_path / "scores.csv"
    path.write_text("model,mase,runtime_s\nm,0.8,1.2\n", encoding="utf-8")
    first = freeze_tsfm_run._output_sha256(path)
    path.write_text("model,mase,runtime_s\nm,0.8,9.9\n", encoding="utf-8")
    assert freeze_tsfm_run._output_sha256(path) == first
    path.write_text("model,mase,runtime_s\nm,0.9,9.9\n", encoding="utf-8")
    assert freeze_tsfm_run._output_sha256(path) != first


def test_verify_manifest_compares_without_overwriting(tmp_path, monkeypatch):
    manifest_path = tmp_path / freeze.RUN_MANIFEST
    manifest_path.parent.mkdir(parents=True)
    expected = {
        "artifact_sha256": {"data/processed/result.csv": "abc"},
        "manifest_schema": 2,
    }
    original = json.dumps(expected, indent=2, sort_keys=True) + "\n"
    manifest_path.write_text(original, encoding="utf-8")
    monkeypatch.setattr(freeze, "build_manifest", lambda root: expected)

    assert freeze.verify_manifest(tmp_path) == 0
    assert manifest_path.read_text(encoding="utf-8") == original

    drifted = {
        "artifact_sha256": {"data/processed/result.csv": "changed"},
        "manifest_schema": 2,
    }
    monkeypatch.setattr(freeze, "build_manifest", lambda root: drifted)
    assert freeze.verify_manifest(tmp_path) == 1
    assert manifest_path.read_text(encoding="utf-8") == original


def test_workspace_candidate_manifest_is_stable_without_mutation():
    first = freeze.build_manifest(config.ROOT)
    second = freeze.build_manifest(config.ROOT)
    assert first == second


def test_manifest_rebuilds_from_clean_room_declared_scope(tmp_path, monkeypatch):
    """An isolated rebuild must depend only on explicitly declared files.

    Synthetic fixture bytes keep this test fast while exercising every declared
    core input, interim input, and orchestrated artifact. A stale prior manifest
    and an undeclared processed file must not alter the rebuilt identity.
    """
    declared = (
        *freeze.CORE_RAW_INPUTS,
        *freeze.INTERIM_INPUTS,
        *freeze.ORCHESTRATED_ARTIFACTS,
        "config/settings.yaml",
        "config/sources.yaml",
    )
    for relative_path in declared:
        path = tmp_path / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(f"clean-room fixture: {relative_path}\n".encode())

    vessel_path = tmp_path / "data/raw/vessel_branch/source.csv"
    vessel_path.parent.mkdir(parents=True, exist_ok=True)
    vessel_path.write_text("vessel_id\nfixture\n", encoding="utf-8")

    monkeypatch.setattr(freeze, "_package_versions", lambda: {"fixture": "1.0"})
    monkeypatch.setattr(
        freeze,
        "_working_specification",
        lambda: {"status": "clean-room-test"},
    )
    monkeypatch.setattr(freeze.platform, "python_version", lambda: "test-python")
    monkeypatch.setattr(freeze.platform, "platform", lambda: "test-platform")

    rebuilt = freeze.build_manifest(tmp_path)
    assert set(rebuilt["raw_sha256"]) == set(freeze.CORE_RAW_INPUTS)
    assert set(rebuilt["interim_input_sha256"]) == set(freeze.INTERIM_INPUTS)
    assert set(rebuilt["artifact_sha256"]) == set(freeze.ORCHESTRATED_ARTIFACTS)
    assert rebuilt["vessel_raw_sha256"] == {
        "data/raw/vessel_branch/source.csv": freeze.sha256_file(vessel_path)
    }
    assert not (tmp_path / freeze.RUN_MANIFEST).exists()

    stale_manifest = tmp_path / freeze.RUN_MANIFEST
    stale_manifest.parent.mkdir(parents=True, exist_ok=True)
    stale_manifest.write_text('{"stale": true}\n', encoding="utf-8")
    undeclared = tmp_path / "data/processed/undeclared_output.csv"
    undeclared.write_text("value\n999\n", encoding="utf-8")

    assert freeze.build_manifest(tmp_path) == rebuilt


def test_tsfm_lockfiles_use_exact_versions():
    for name in (
        "requirements-benchmark.lock.txt",
        "requirements-timesfm.lock.txt",
    ):
        lines = (config.ROOT / name).read_text().splitlines()
        requirements = [line for line in lines if line and not line.startswith("#")]
        assert requirements
        assert all("==" in requirement for requirement in requirements)


def test_tsfm_manifest_records_clean_environment_checks():
    path = config.ROOT / "data/processed/tsfm_run_manifest.json"
    manifest = json.loads(path.read_text())
    assert "captured_at" not in manifest
    assert manifest["determinism_policy"] == {
        "numpy_seeded": True,
        "python_random_seeded": True,
        "seed": 20260612,
        "torch_deterministic_algorithms": True,
        "torch_seeded": True,
        "wall_clock_runtime_columns_excluded_from_output_hashes": True,
    }
    for environment in manifest["benchmark_environments"].values():
        assert environment["status"] == "captured"
        assert environment["metadata_consistent"] is True
        assert environment["pip_check"] == "passed"
        assert environment["lock_matches_installed"] is True
        assert environment["locked_distribution_count"] == environment[
            "installed_distribution_count"
        ]
        assert len(environment["lockfile_sha256"]) == 64
