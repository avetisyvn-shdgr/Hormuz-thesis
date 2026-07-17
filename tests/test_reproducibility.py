import json


import freeze_reproducibility as freeze
from freeze_reproducibility import (
    CORE_RAW_INPUTS,
    ORCHESTRATED_ARTIFACTS,
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
    assert len(hashes) == 9


def test_vessel_scope_excludes_core_and_archives():
    """Vessel-branch raw set must not overlap the core set or canonicalize
    transient .zip downloads."""
    core = set(CORE_RAW_INPUTS)
    vessel = vessel_raw_hashes(config.ROOT)
    assert core.isdisjoint(vessel)
    assert not any(rel.endswith(".zip") for rel in vessel)


def test_orchestrated_artifact_scope_excludes_optional_outputs():
    assert len(ORCHESTRATED_ARTIFACTS) == len(set(ORCHESTRATED_ARTIFACTS))
    assert not any("tsfm_" in rel for rel in ORCHESTRATED_ARTIFACTS)
    assert not any("/presentation/" in rel for rel in ORCHESTRATED_ARTIFACTS)
    assert "reports/Hormuz_Thesis_Supervisor_Review.pptx" not in ORCHESTRATED_ARTIFACTS


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
    for environment in manifest["benchmark_environments"].values():
        assert environment["status"] == "captured"
        assert environment["metadata_consistent"] is True
        assert environment["pip_check"] == "passed"
        assert environment["lock_matches_installed"] is True
        assert environment["locked_distribution_count"] == environment[
            "installed_distribution_count"
        ]
        assert len(environment["lockfile_sha256"]) == 64
