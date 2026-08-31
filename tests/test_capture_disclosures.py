from fetch_india_tradestat_lng import UA
from ingest_importer_customs_snapshots import (
    ORIGINALS_README,
    SOURCE_PAYLOAD_STATUSES,
    source_payloads,
)

from hormuz_throughput import config


def test_importer_capture_disclosures_are_machine_readable_and_in_sync():
    originals = config.path("importer_customs_dir") / "originals"
    assert (originals / "README.md").read_text(encoding="utf-8") == ORIGINALS_README
    assert SOURCE_PAYLOAD_STATUSES == {
        "kr": "normalized_capture_only_no_original_response_or_query_receipt",
        "cn": "portal_exports_preserved_no_html_query_receipt_or_terms_capture",
        "in": "parsed_capture_preserved_original_http_responses_not_retained",
    }
    assert {
        payload.role for payload in source_payloads("cn", config.path("importer_customs_dir"))
    } == {"portal_export_without_query_receipt"}
    assert {
        payload.role for payload in source_payloads("in", config.path("importer_customs_dir"))
    } == {"parsed_table_capture_not_http_response"}


def test_future_india_capture_identifies_the_research_script():
    user_agent = UA["User-Agent"]
    assert "TUM-Hormuz-Throughput-Thesis" in user_agent
    assert "Mozilla" not in user_agent


def test_registry_covers_all_four_unverifiable_capture_classes():
    expected = {
        "korea_lng_by_origin_snapshot": {
            "original_rendered_response",
            "query_receipt",
            "contemporaneous_terms_capture",
        },
        "china_lng_by_origin_snapshot": {
            "surrounding_html",
            "query_receipts",
            "contemporaneous_terms_capture",
        },
        "india_lng_by_origin_snapshot": {
            "original_response_html",
            "response_headers",
            "contemporaneous_terms_capture",
        },
        "qflex_vessel_benchmark_snapshot": {
            "source_documents",
            "page_extracts",
            "transcription_log",
        },
    }
    registry = config.registry()
    for variable, missing_evidence in expected.items():
        audit = registry[variable]["auditability"]
        assert audit["frozen_artifact_hash_verifiable"] is True
        assert audit["original_source_response_reconstructible"] is False
        assert set(audit["missing_evidence"]) == missing_evidence
        assert audit["evidence_role"] == "extension_only"
        assert audit["affects_portwatch_primary"] is False
