from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd
import pytest

from hormuz_throughput.registry import _resolve_entry
from hormuz_throughput.sources.bloomberg_transcription import BloombergTranscriptionSource


def _manifest(tmp_path: Path, digest: str = "0" * 64) -> dict:
    return {
        "schema_version": 1,
        "export_directory_env": "BLOOMBERG_EXPORT_DIR",
        "governance": {
            "designation": "provenance_limited_secondary",
            "authorized_by": "thesis_author",
            "authorized_date": "2026-08-08",
            "permitted_uses": ["descriptive_market_evidence"],
            "prohibited_claims": ["ATT"],
        },
        "series": {
            "test_series": {
                "filename": "test.xlsx",
                "displayed_series_name": "Test",
                "analysis_use": "provenance_limited_secondary",
                "bloomberg_identifier": None,
                "original_provider": "Test Provider",
                "candidate_role": "secondary_freight_outcome",
                "frequency": "weekly",
                "assessment_calendar_verified": None,
                "unit": "USD/day",
                "currency": "USD",
                "price_field": None,
                "publication_time": None,
                "timezone": None,
                "extraction_date": None,
                "export_procedure": "structured transcription",
                "raw_sheet": "Raw Data",
                "date_column": "Date",
                "value_column": "Rate",
                "missing_value_convention": "blank is missing",
                "zero_is_genuine": None,
                "assessment_methodology": None,
                "definition_stable": None,
                "expected_sha256": digest,
                "source_artifact_status": (
                    "structured_transcription_not_original_export"
                ),
                "rights": {
                    "historical_export": None,
                    "raw_retention": None,
                    "thesis_modelling": None,
                    "raw_publication": None,
                    "derived_results_publication": None,
                },
            }
        },
    }


def _patch_source(monkeypatch, tmp_path, frame: pd.DataFrame):
    source = tmp_path / "test.xlsx"
    source.write_bytes(b"workbook-bytes")
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    monkeypatch.setenv("BLOOMBERG_EXPORT_DIR", str(tmp_path))
    monkeypatch.setattr(
        BloombergTranscriptionSource,
        "_manifest",
        staticmethod(lambda: _manifest(tmp_path, digest)),
    )
    monkeypatch.setattr(pd, "read_excel", lambda *args, **kwargs: frame.copy())
    return source


def test_restricted_registry_status_resolves_primary_without_becoming_free():
    backend, channel = _resolve_entry(
        {"status": "restricted", "primary": {"provider": "local", "code": "x"}}
    )
    assert backend["code"] == "x"
    assert channel == "primary"
    assert "fearnleys_lng_spot_east_suez" not in __import__(
        "hormuz_throughput.panel", fromlist=["free_variables"]
    ).free_variables()


def test_missing_export_directory_fails_loudly(monkeypatch):
    monkeypatch.delenv("BLOOMBERG_EXPORT_DIR", raising=False)
    monkeypatch.setattr(
        BloombergTranscriptionSource,
        "_manifest",
        staticmethod(lambda: _manifest(Path("."))),
    )
    with pytest.raises(RuntimeError, match="BLOOMBERG_EXPORT_DIR"):
        BloombergTranscriptionSource().fetch(
            "test_series", "2026-01-01", "2026-03-31"
        )


def test_fetch_returns_tidy_filtered_values_and_preserves_zero(monkeypatch, tmp_path):
    source = _patch_source(
        monkeypatch,
        tmp_path,
        pd.DataFrame(
            {
                "Date": ["2025-12-26", "2026-01-02", "2026-01-09", "2026-01-16"],
                "Rate": ["10.000,00", "", "0,00", "12,500.00"],
            }
        ),
    )
    result = BloombergTranscriptionSource().fetch(
        "test_series", "2026-01-01", "2026-01-31"
    )
    assert result.to_dict(orient="list") == {
        "date": [pd.Timestamp("2026-01-09"), pd.Timestamp("2026-01-16")],
        "value": [0.0, 12500.0],
    }
    payload = BloombergTranscriptionSource()
    _patch_source(
        monkeypatch,
        tmp_path,
        pd.DataFrame({"Date": ["2026-01-09"], "Rate": [1]}),
    )
    payload.fetch("test_series", "2026-01-01", "2026-01-31")
    assert payload.source_payload.path == source
    assert payload.source_payload.role == "provenance_limited_structured_transcription"


def test_checksum_mismatch_is_rejected_before_parsing(monkeypatch, tmp_path):
    source = tmp_path / "test.xlsx"
    source.write_bytes(b"changed")
    monkeypatch.setenv("BLOOMBERG_EXPORT_DIR", str(tmp_path))
    monkeypatch.setattr(
        BloombergTranscriptionSource,
        "_manifest",
        staticmethod(lambda: _manifest(tmp_path)),
    )
    with pytest.raises(ValueError, match="checksum mismatch"):
        BloombergTranscriptionSource().fetch(
            "test_series", "2026-01-01", "2026-03-31"
        )


def test_duplicate_dates_are_rejected(monkeypatch, tmp_path):
    _patch_source(
        monkeypatch,
        tmp_path,
        pd.DataFrame({"Date": ["2026-01-02", "2026-01-02"], "Rate": [1, 2]}),
    )
    with pytest.raises(ValueError, match="Duplicate Bloomberg dates"):
        BloombergTranscriptionSource().fetch(
            "test_series", "2026-01-01", "2026-03-31"
        )
