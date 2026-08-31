import hashlib
import json

import pandas as pd

from hormuz_throughput import config, provenance
from hormuz_throughput.sources.base import SourcePayload


def test_identical_raw_save_does_not_duplicate_provenance(tmp_path, monkeypatch):
    settings = {
        "paths": {
            "data_raw": "data/raw",
            "provenance_log": "data/raw/provenance.jsonl",
        }
    }
    monkeypatch.setattr(config, "ROOT", tmp_path)
    monkeypatch.setattr(config, "settings", lambda: settings)
    frame = pd.DataFrame({"value": [1, 2]})
    kwargs = {
        "provider": "example",
        "variable": "series",
        "code": "v1",
        "query": {"window": "fixed"},
        "license_note": "test",
    }

    provenance.save_raw(frame, **kwargs)
    provenance.save_raw(frame, **kwargs)

    lines = (tmp_path / "data/raw/provenance.jsonl").read_text().splitlines()
    assert len(lines) == 1


def test_different_raw_payloads_get_immutable_paths(tmp_path, monkeypatch):
    settings = {
        "paths": {
            "data_raw": "data/raw",
            "provenance_log": "data/raw/provenance.jsonl",
        }
    }
    monkeypatch.setattr(config, "ROOT", tmp_path)
    monkeypatch.setattr(config, "settings", lambda: settings)
    kwargs = {
        "provider": "example",
        "variable": "series",
        "code": "v1",
        "license_note": "test",
    }

    first = provenance.save_raw(
        pd.DataFrame({"value": [1]}), query={"window": "first"}, **kwargs
    )
    second = provenance.save_raw(
        pd.DataFrame({"value": [2]}), query={"window": "second"}, **kwargs
    )

    assert first != second
    assert pd.read_csv(first)["value"].tolist() == [1]
    assert pd.read_csv(second)["value"].tolist() == [2]


def test_v2_record_links_original_source_bytes(tmp_path, monkeypatch):
    settings = {
        "paths": {
            "data_raw": "data/raw",
            "provenance_log": "data/raw/provenance.jsonl",
        }
    }
    monkeypatch.setattr(config, "ROOT", tmp_path)
    monkeypatch.setattr(config, "settings", lambda: settings)
    content = b'{"source_rows":[{"period":"2026-01-01","value":"1"}]}'

    provenance.save_raw(
        pd.DataFrame({"date": ["2026-01-01"], "value": [1.0]}),
        provider="example",
        variable="logical_series",
        code="source-code",
        query={"start": "2026-01-01", "end": "2026-01-01"},
        license_note="test",
        source_payload=SourcePayload(
            filename="response.json",
            media_type="application/json",
            source_url="https://example.test/data",
            content=content,
        ),
        registry_variables=["logical_series"],
    )

    record = json.loads(
        (tmp_path / "data/raw/provenance.jsonl").read_text().strip()
    )
    assert record["schema_version"] == 2
    assert record["artifact_role"] == "normalized_analysis_snapshot"
    assert record["registry_variables"] == ["logical_series"]
    assert record["source_payload_status"] == "preserved"
    source = record["source_payloads"][0]
    assert source["role"] == "original_source_payload"
    assert source["sha256"] == hashlib.sha256(content).hexdigest()
    assert (tmp_path / source["file"]).read_bytes() == content


def test_register_existing_snapshot_does_not_rewrite_bytes(tmp_path, monkeypatch):
    settings = {
        "paths": {
            "data_raw": "data/raw",
            "provenance_log": "data/raw/provenance.jsonl",
        }
    }
    monkeypatch.setattr(config, "ROOT", tmp_path)
    monkeypatch.setattr(config, "settings", lambda: settings)
    path = tmp_path / "data/raw/example/existing.csv"
    path.parent.mkdir(parents=True)
    original = b"value\n1.00\n"
    path.write_bytes(original)

    provenance.register_existing_snapshot(
        path,
        provider="example",
        variable="series",
        code="v1",
        query={"metadata_backfill": "test"},
        license_note="test",
        source_payload_status="historical_original_not_preserved",
        registry_variables=["series"],
    )

    assert path.read_bytes() == original
    record = json.loads(
        (tmp_path / "data/raw/provenance.jsonl").read_text().strip()
    )
    assert record["sha256"] == hashlib.sha256(original).hexdigest()
    assert record["source_payload_status"] == "historical_original_not_preserved"
