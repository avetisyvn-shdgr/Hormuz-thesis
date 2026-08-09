from fetch_india_tradestat_lng import UA
from ingest_importer_customs_snapshots import (
    ORIGINALS_README,
    SOURCE_PAYLOAD_STATUSES,
    source_payloads,
)

from lngfreight import config


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
    assert "TUM-LNG-Freight-Thesis" in user_agent
    assert "Mozilla" not in user_agent


def test_central_limitations_cover_all_four_unverifiable_capture_classes():
    text = (config.ROOT / "docs/DATA_SOURCES.md").read_text(encoding="utf-8")
    for label in (
        "Korea KCS importer table",
        "China GACC importer table",
        "India DGCI&S Tradestat table",
        "Q-Flex 31-vessel benchmark",
    ):
        assert label in text
    assert "does not affect the independently frozen PortWatch primary outcome" in text
