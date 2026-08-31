from __future__ import annotations

import hashlib

import numpy as np
import pandas as pd

from hormuz_throughput import config
from hormuz_throughput.bloomberg_admission import (
    admission_gates,
    audit_export,
    audit_frame,
    load_manifest,
    parse_date,
    parse_decimal,
)


def _weekly_spec() -> dict:
    return {
        "filename": "freight.xlsx",
        "displayed_series_name": "Test freight",
        "candidate_role": "secondary_freight_outcome",
        "frequency": "weekly",
        "assessment_calendar_verified": True,
        "unit": "USD/day",
        "currency": "USD",
        "raw_sheet": "Raw Data",
        "date_column": "Date",
        "value_column": "Rate",
        "expected_sha256": "0" * 64,
        "source_artifact_status": "original_terminal_export",
        "bloomberg_identifier": "TEST Index",
        "original_provider": "Test Provider",
        "assessment_methodology": "Documented method",
        "definition_stable": True,
        "price_field": "PX_LAST",
        "publication_time": "12:00",
        "timezone": "Europe/London",
        "extraction_date": "2026-08-08",
        "zero_is_genuine": False,
        "export_procedure": "Bloomberg Excel add-in export with saved parameters",
        "missing_value_convention": "Blank means no assessment",
        "rights": {
            "historical_export": True,
            "raw_retention": True,
            "thesis_modelling": True,
            "raw_publication": True,
            "derived_results_publication": True,
        },
    }


def test_repository_manifest_declares_all_five_phase_zero_candidates():
    manifest = load_manifest(config.ROOT / "config/bloomberg_exports.yaml")
    assert manifest["export_directory_env"] == "BLOOMBERG_EXPORT_DIR"
    assert set(manifest["series"]) == {
        "fearnleys_lng_spot_east_suez",
        "fearnleys_lng_spot_west_suez",
        "fearnleys_lng_one_year_time_charter",
        "netherlands_ttf_day_ahead",
        "clearlynx_vlsfo_singapore",
    }


def test_decimal_comma_parser_preserves_missing_and_zero():
    assert parse_decimal("45.000,00") == 45000.0
    assert parse_decimal("45,000.00") == 45000.0
    assert parse_decimal("801,25") == 801.25
    assert parse_decimal("0,00") == 0.0
    assert np.isnan(parse_decimal(""))
    assert np.isnan(parse_decimal(None))


def test_date_parser_handles_excel_serial_and_iso_date():
    assert parse_date(46081) == pd.Timestamp("2026-02-28")
    assert parse_date("2026-03-06") == pd.Timestamp("2026-03-06")
    assert pd.isna(parse_date("not-a-date"))


def test_weekly_audit_reports_coverage_duplicates_missing_and_zeros():
    dates = list(pd.date_range("2022-01-07", "2026-07-03", freq="W-FRI"))
    dates.remove(pd.Timestamp("2024-06-07"))
    frame = pd.DataFrame(
        {"Date": dates, "Rate": pd.Series([10_000.0] * len(dates), dtype=object)}
    )
    frame.loc[0, "Rate"] = "10.000,00"
    frame.loc[1, "Rate"] = ""
    frame.loc[2, "Rate"] = 0
    frame = pd.concat([frame, frame.iloc[[3]]], ignore_index=True)

    metrics = audit_frame(
        frame,
        _weekly_spec(),
        study_start="2022-01-01",
        study_end="2026-07-07",
        treatment_cutoff="2026-02-28",
    )

    assert metrics["schema_valid"] is True
    assert metrics["missing_value_count"] == 1
    assert metrics["duplicate_date_count"] == 2
    assert metrics["zero_value_count"] == 1
    assert metrics["missing_periods"] == 2
    assert metrics["pre_treatment_observations"] >= 52
    assert metrics["post_treatment_observations"] >= 12
    assert metrics["first_expected_post_week"] == "2026-03-06"


def test_complete_metadata_and_coverage_can_pass_all_freight_gates():
    dates = pd.date_range("2022-01-07", "2026-07-03", freq="W-FRI")
    metrics = audit_frame(
        pd.DataFrame({"Date": dates, "Rate": 50_000}),
        _weekly_spec(),
        study_start="2022-01-01",
        study_end="2026-07-07",
        treatment_cutoff="2026-02-28",
    )
    gates = admission_gates(
        _weekly_spec(), metrics, file_present=True, checksum_match=True
    )
    assert all(gates.values())


def test_raw_publication_prohibition_does_not_block_private_modelling():
    spec = _weekly_spec()
    spec["rights"] = {**spec["rights"], "raw_publication": False}
    dates = pd.date_range("2022-01-07", "2026-07-03", freq="W-FRI")
    metrics = audit_frame(
        pd.DataFrame({"Date": dates, "Rate": 50_000}),
        spec,
        study_start="2022-01-01",
        study_end="2026-07-07",
        treatment_cutoff="2026-02-28",
    )
    gates = admission_gates(spec, metrics, file_present=True, checksum_match=True)
    assert gates["licence_and_thesis_rights_confirmed"] is True


def test_missing_workbook_is_reported_without_attempting_to_read(tmp_path):
    spec = _weekly_spec()
    result = audit_export(
        "test_freight",
        spec,
        tmp_path,
        study_start="2022-01-01",
        study_end="2026-07-07",
        treatment_cutoff="2026-02-28",
    )
    assert result["admitted"] is False
    assert result["gates"]["file_present"] is False
    assert result["actual_sha256"] is None


def test_checksum_mismatch_blocks_an_otherwise_readable_export(
    tmp_path, monkeypatch
):
    source = tmp_path / "freight.xlsx"
    source.write_bytes(b"not-real-xlsx")
    spec = _weekly_spec()
    expected = hashlib.sha256(b"different").hexdigest()
    spec["expected_sha256"] = expected
    monkeypatch.setattr(
        pd,
        "read_excel",
        lambda *args, **kwargs: pd.DataFrame(
            {
                "Date": pd.date_range(
                    "2022-01-07", "2026-07-03", freq="W-FRI"
                ),
                "Rate": 50_000,
            }
        ),
    )
    result = audit_export(
        "test_freight",
        spec,
        tmp_path,
        study_start="2022-01-01",
        study_end="2026-07-07",
        treatment_cutoff="2026-02-28",
    )
    assert result["gates"]["checksum_match"] is False
    assert result["admitted"] is False
