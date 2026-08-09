"""Append truthful v2 provenance metadata for existing active snapshots.

This migration never rewrites historical ledger lines or snapshot bytes. It
links originals that are already preserved and labels historical originals that
were not retained. Re-running is idempotent.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lngfreight import config, provenance  # noqa: E402
from lngfreight.registry import RegisteredArtifact, get_variable  # noqa: E402
from lngfreight.sources.base import SourcePayload  # noqa: E402


IMPORTER_REGISTRY_VARIABLES = {
    unit: [f"{country}_lng_import_total", f"{country}_lng_import_gulf"]
    for unit, country in {
        "kr": "korea",
        "tw": "taiwan",
        "cn": "china",
        "in": "india",
        "jp": "japan",
    }.items()
}


def _payload(path: Path, role: str = "original_source_payload") -> SourcePayload:
    media = {
        ".csv": "text/csv",
        ".geojson": "application/geo+json",
        ".html": "text/html",
    }.get(path.suffix.lower(), "application/octet-stream")
    return SourcePayload(
        filename=path.name,
        media_type=media,
        role=role,
        path=path,
    )


def _source_links(variable: str) -> tuple[list[SourcePayload], str]:
    raw = config.path("data_raw")
    if variable in {
        "hormuz_tanker_transits",
        "hormuz_tanker_capacity",
        "panama_tanker_transits",
        "panama_tanker_capacity",
        "ais_laden_tonmiles_usgc",
    }:
        return [_payload(raw / "portwatch" / "Daily_Chokepoints_Data.csv")], "preserved"
    if variable == "wto_hormuz_lng_outbound_index":
        return [
            _payload(raw / "wto_hormuz" / "voy_intake_index_lng_export.csv")
        ], "preserved"
    if variable.endswith("_lng_imports_by_origin"):
        unit = variable[:2]
        originals = raw / "importer_customs" / "originals"
        paths = {
            "kr": [],
            "tw": [originals / "tw_original_big5.csv"],
            "cn": [
                originals / "cn_original_2024.csv",
                originals / "cn_original_2025.csv",
                originals / "cn_original_2026.csv",
            ],
            "in": [originals / "in_original_long.csv"],
            "jp": [
                originals / "jp_estat_2024_raw.csv",
                originals / "jp_estat_2025_raw.csv",
                originals / "jp_estat_2026_raw.csv",
                originals / "jp_country_code_list.html",
                originals / "jp_estat_search_page1.html",
                originals / "jp_estat_search_page2.html",
                originals / "jp_original_lng271111_with_jpy.csv",
            ],
        }[unit]
        if unit == "cn":
            return [
                _payload(path, role="portal_export_without_query_receipt")
                for path in paths
            ], "portal_exports_preserved_no_html_query_receipt_or_terms_capture"
        if unit == "in":
            return [
                _payload(path, role="parsed_table_capture_not_http_response")
                for path in paths
            ], "parsed_capture_preserved_original_http_responses_not_retained"
        if paths:
            return [_payload(path) for path in paths], "preserved"
        return [], "normalized_capture_only_no_original_response_or_query_receipt"
    if variable in {"gfw_lng_terminal_crosswalk", "gfw_global_lng_terminal_crosswalk"}:
        return [
            _payload(
                raw / "gem" / "GEM-GGIT-LNG-Terminals-2025-09.geojson",
                role="upstream_source_snapshot",
            )
        ], "upstream_source_preserved"
    if variable == "natural_earth_110m_land":
        return [], "artifact_is_original_source_payload"
    return [], "historical_original_not_preserved"


def _registry_variables(variable: str, configured: set[str]) -> list[str]:
    if variable in configured:
        return [variable]
    if variable.endswith("_lng_imports_by_origin"):
        return IMPORTER_REGISTRY_VARIABLES[variable[:2]]
    return []


def main() -> int:
    ledger = config.ROOT / config.settings()["paths"]["provenance_log"]
    records = [
        json.loads(line)
        for line in ledger.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    configured = set(config.registry())
    current: dict[str, dict] = {}
    for record in records:
        if record.get("schema_version") == 2:
            continue
        path = config.ROOT / record["file"]
        if not path.exists():
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest == record["sha256"]:
            current[record["file"]] = record

    for relative, record in sorted(current.items()):
        links, status = _source_links(record["variable"])
        provenance.register_existing_snapshot(
            config.ROOT / relative,
            provider=record["provider"],
            variable=record["variable"],
            code=record["code"],
            query={
                **record.get("query", {}),
                "metadata_backfill": "provenance_v2_2026-07-26",
            },
            license_note=record.get("license", "unspecified"),
            registry_variables=_registry_variables(record["variable"], configured),
            source_payloads=links,
            source_payload_status=status,
            artifact_role=(
                "original_source_snapshot"
                if record["variable"] == "natural_earth_110m_land"
                else "normalized_analysis_snapshot"
            ),
        )
    renamed_duplicate = (
        config.path("data_raw")
        / "portwatch"
        / "quarantined_panama_tanker_capacity_duplicate__"
        "chokepoint_panama_canal_capacity_tanker.csv"
    )
    if renamed_duplicate.exists():
        provenance.register_existing_snapshot(
            renamed_duplicate,
            provider="portwatch",
            variable="panama_tanker_capacity_historical_duplicate",
            code="chokepoint:panama_canal:capacity_tanker",
            query={
                "metadata_backfill": "data_02_truthful_rename_2026-07-26",
                "active_input": False,
                "duplicate_of": (
                    "data/raw/portwatch/panama_tanker_capacity__"
                    "chokepoint_panama_canal_capacity_tanker.csv"
                ),
            },
            license_note="IMF PortWatch public snapshot",
            registry_variables=[],
            source_payloads=[
                _payload(
                    config.path("data_raw")
                    / "portwatch"
                    / "Daily_Chokepoints_Data.csv"
                )
            ],
            source_payload_status="upstream_source_preserved",
            artifact_role="quarantined_duplicate_snapshot",
        )
    artifact_variables = sorted(
        name
        for name, spec in config.registry().items()
        if spec.get("kind") == "artifact"
    )
    for name in artifact_variables:
        artifact = get_variable(
            name,
            query={"consumer": "provenance_v2_artifact_backfill"},
        )
        if not isinstance(artifact, RegisteredArtifact):
            raise TypeError(f"artifact registry entry did not resolve as artifact: {name}")
    print(f"v2 provenance records current={len(current)}")
    print(f"registered artifact variables={len(artifact_variables)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
