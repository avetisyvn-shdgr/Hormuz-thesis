import hashlib
import json

import pytest

from lngfreight import config
from lngfreight import registry as registry_module
from lngfreight.registry import RegisteredArtifact


def _artifact_registry() -> dict:
    return {
        "external_snapshot": {
            "kind": "artifact",
            "role": "artifact",
            "status": "free",
            "primary": {
                "provider": "frozen_artifact",
                "path": "data/raw/provider/source.json",
                "media_type": "application/json",
                "license": "test licence",
                "source_status": "artifact_is_preserved_source_payload",
            },
        }
    }


def _prepare_artifact_root(tmp_path, monkeypatch):
    source = tmp_path / "data/raw/provider/source.json"
    source.parent.mkdir(parents=True)
    source.write_text('{"value": 7}\n', encoding="utf-8")
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    hash_file = tmp_path / "data/raw/SHA256SUMS"
    hash_file.write_text(
        f"{digest}  data/raw/provider/source.json\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(config, "ROOT", tmp_path)
    monkeypatch.setattr(
        config,
        "settings",
        lambda: {"paths": {"provenance_log": "data/raw/provenance.jsonl"}},
    )
    monkeypatch.setattr(config, "registry", _artifact_registry)
    return source, hash_file


def test_registered_artifact_verifies_hash_and_appends_v2_access(tmp_path, monkeypatch):
    source, _ = _prepare_artifact_root(tmp_path, monkeypatch)
    artifact = registry_module.get_variable(
        "external_snapshot",
        query={"consumer": "unit_test"},
    )
    assert isinstance(artifact, RegisteredArtifact)
    assert artifact.path == source
    assert artifact.read_json() == {"value": 7}

    ledger = tmp_path / "data/raw/provenance.jsonl"
    record = json.loads(ledger.read_text(encoding="utf-8"))
    assert record["schema_version"] == 2
    assert record["artifact_role"] == "analysis_input_artifact"
    assert record["registry_variables"] == ["external_snapshot"]
    assert record["query"] == {
        "access_mode": "frozen_analysis_input",
        "channel": "primary",
        "consumer": "unit_test",
    }
    assert record["sha256"] == hashlib.sha256(source.read_bytes()).hexdigest()


def test_registered_artifact_rejects_hash_drift_before_access(tmp_path, monkeypatch):
    source, _ = _prepare_artifact_root(tmp_path, monkeypatch)
    source.write_text('{"value": 8}\n', encoding="utf-8")
    with pytest.raises(ValueError, match="hash mismatch"):
        registry_module.get_variable("external_snapshot")
    assert not (tmp_path / "data/raw/provenance.jsonl").exists()


def test_active_external_consumers_call_registry_entrypoint():
    expected = {
        "scripts/run_lng_index_analysis.py": "wto_hormuz_lng_outbound_index",
        "src/lngfreight/spatial.py": "portwatch_chokepoints_snapshot",
        "scripts/build_lng_terminal_crosswalk.py": "gem_lng_terminals_snapshot",
        "scripts/build_global_lng_terminal_crosswalk.py": (
            "global_gfw_port_visits_snapshot"
        ),
        "scripts/build_global_carrier_frame.py": "gem_lng_carrier_source_snapshot",
        "scripts/run_voyage_feasibility.py": "qflex_gfw_port_visits_snapshot",
        "scripts/run_global_voyage_feasibility.py": (
            "global_gfw_port_visits_snapshot"
        ),
        "scripts/build_inferred_capacity_nautical_miles.py": (
            "global_gfw_identity_snapshot"
        ),
        "scripts/run_vessel_data_feasibility.py": (
            "qflex_vessel_benchmark_snapshot"
        ),
        "scripts/build_importer_outcomes.py": "korea_lng_by_origin_snapshot",
        "scripts/build_lng_rewiring_network.py": "registered_rewiring_input_paths",
        "src/lngfreight/network_rewiring.py": "CUSTOMS_ARTIFACT_VARIABLES",
        "scripts/build_lng_network_anomaly_scores.py": (
            "registered_rewiring_input_paths"
        ),
        "scripts/build_lng_rewiring_graph_metrics.py": (
            "registered_rewiring_input_paths"
        ),
        "scripts/build_lng_rewiring_summary.py": "registered_rewiring_input_paths",
        "scripts/build_lng_rewiring_post_month_sensitivity.py": (
            "registered_rewiring_input_paths"
        ),
        "scripts/build_lng_reallocation_model.py": (
            "global_lng_terminal_crosswalk_snapshot"
        ),
        "scripts/build_importer_coverage_report.py": "backup_probe_manifest_snapshot",
        "scripts/make_route_map.py": "natural_earth_land_snapshot",
    }
    for relative, variable in expected.items():
        text = (config.ROOT / relative).read_text(encoding="utf-8")
        assert (
            "get_variable" in text
            or "registered_rewiring_input_paths" in text
        )
        assert variable in text
