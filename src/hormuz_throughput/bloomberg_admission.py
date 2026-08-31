"""Read-only admission audit for user-supplied Bloomberg export workbooks.

This module evaluates source integrity, metadata, licence, schema, and temporal
coverage. It deliberately does not expose a provider or return analysis-ready
series: a failed Phase 0 gate must not become an implicit Phase 1 admission.
"""
from __future__ import annotations

from datetime import date, datetime
import hashlib
from pathlib import Path
import re
from typing import Any

import numpy as np
import pandas as pd
import yaml


MANIFEST_REQUIRED_FIELDS = {
    "filename",
    "displayed_series_name",
    "analysis_use",
    "bloomberg_identifier",
    "original_provider",
    "candidate_role",
    "frequency",
    "assessment_calendar_verified",
    "unit",
    "currency",
    "price_field",
    "publication_time",
    "timezone",
    "extraction_date",
    "export_procedure",
    "raw_sheet",
    "date_column",
    "value_column",
    "missing_value_convention",
    "zero_is_genuine",
    "assessment_methodology",
    "definition_stable",
    "expected_sha256",
    "source_artifact_status",
    "rights",
}
RIGHTS_FIELDS = {
    "historical_export",
    "raw_retention",
    "thesis_modelling",
    "raw_publication",
    "derived_results_publication",
}
MISSING_MARKERS = {"", "-", "--", "n/a", "na", "null", "none", "#n/a"}


def load_manifest(path: Path) -> dict[str, Any]:
    """Load and minimally validate the versioned YAML admission manifest."""
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("schema_version") != 1:
        raise ValueError("Bloomberg manifest must declare schema_version: 1")
    series = payload.get("series")
    if not isinstance(series, dict) or not series:
        raise ValueError("Bloomberg manifest must define at least one series")
    for name, spec in series.items():
        if not isinstance(spec, dict):
            raise ValueError(f"manifest series {name!r} must be a mapping")
        missing = MANIFEST_REQUIRED_FIELDS - set(spec)
        if missing:
            raise ValueError(
                f"manifest series {name!r} is missing fields: {sorted(missing)}"
            )
        rights = spec.get("rights")
        if not isinstance(rights, dict) or RIGHTS_FIELDS - set(rights):
            raise ValueError(
                f"manifest series {name!r} must declare all rights fields"
            )
    governance = payload.get("governance")
    if not isinstance(governance, dict):
        raise ValueError("Bloomberg manifest must declare governance metadata")
    if governance.get("designation") != "provenance_limited_secondary":
        raise ValueError("Bloomberg manifest governance designation is invalid")
    return payload


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _is_blank(value: object) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip().lower() in MISSING_MARKERS
    try:
        return bool(pd.isna(value))
    except (TypeError, ValueError):
        return False


def parse_decimal(value: object) -> float:
    """Parse numeric cells and common decimal-comma exports without imputing."""
    if _is_blank(value):
        return float("nan")
    if isinstance(value, (int, float, np.integer, np.floating)):
        return float(value)

    text = str(value).strip().replace("\u00a0", "").replace(" ", "")
    text = re.sub(r"(?:USD|EUR|US\$|€|\$)", "", text, flags=re.IGNORECASE)
    if "," in text and "." in text:
        if text.rfind(",") > text.rfind("."):
            text = text.replace(".", "").replace(",", ".")
        else:
            text = text.replace(",", "")
    elif "," in text:
        head, tail = text.rsplit(",", 1)
        if tail.isdigit() and len(tail) <= 3:
            text = f"{head.replace(',', '')}.{tail}"
        else:
            text = text.replace(",", "")
    text = re.sub(r"[^0-9eE+\-.]", "", text)
    try:
        return float(text)
    except ValueError:
        return float("nan")


def parse_date(value: object) -> pd.Timestamp:
    """Parse an Excel date serial, timestamp, or unambiguous date string."""
    if _is_blank(value):
        return pd.NaT
    if isinstance(value, pd.Timestamp):
        return value.tz_localize(None) if value.tzinfo else value
    if isinstance(value, (datetime, date)):
        return pd.Timestamp(value).tz_localize(None)
    if isinstance(value, (int, float, np.integer, np.floating)):
        numeric = float(value)
        if 1 <= numeric <= 100_000:
            return pd.Timestamp("1899-12-30") + pd.to_timedelta(numeric, unit="D")
        return pd.NaT
    parsed = pd.to_datetime(str(value).strip(), errors="coerce", format="mixed")
    if pd.isna(parsed):
        return pd.NaT
    stamp = pd.Timestamp(parsed)
    return stamp.tz_localize(None) if stamp.tzinfo else stamp


def _calendar_coverage(
    dates: pd.Series,
    *,
    frequency: str,
    start: pd.Timestamp,
    end: pd.Timestamp,
) -> dict[str, int | float]:
    if frequency == "weekly":
        expected = pd.date_range(start=start, end=end, freq="W-FRI")
        observed = pd.DatetimeIndex(
            dates.dt.to_period("W-FRI").dt.end_time.dt.normalize().unique()
        )
    elif frequency == "daily":
        expected = pd.bdate_range(start=start, end=end)
        observed = pd.DatetimeIndex(dates.dt.normalize().unique())
    else:
        raise ValueError(f"unsupported frequency {frequency!r}")
    observed_in_calendar = expected.intersection(observed)
    expected_count = int(len(expected))
    observed_count = int(len(observed_in_calendar))
    missing_count = expected_count - observed_count
    return {
        "expected_periods": expected_count,
        "observed_periods": observed_count,
        "missing_periods": missing_count,
        "missing_ratio": (
            float(missing_count / expected_count) if expected_count else 1.0
        ),
    }


def audit_frame(
    frame: pd.DataFrame,
    spec: dict[str, Any],
    *,
    study_start: str,
    study_end: str,
    treatment_cutoff: str,
) -> dict[str, Any]:
    """Audit the configured raw sheet without correcting or deduplicating it."""
    date_column = spec["date_column"]
    value_column = spec["value_column"]
    missing_columns = [
        column for column in (date_column, value_column) if column not in frame
    ]
    if missing_columns:
        return {
            "schema_valid": False,
            "missing_columns": missing_columns,
            "row_count": int(len(frame)),
        }

    data = frame.dropna(how="all").copy()
    raw_dates = data[date_column]
    raw_values = data[value_column]
    dates = raw_dates.map(parse_date)
    values = raw_values.map(parse_decimal)
    nonblank_dates = ~raw_dates.map(_is_blank)
    nonblank_values = ~raw_values.map(_is_blank)
    invalid_date_count = int((nonblank_dates & dates.isna()).sum())
    invalid_value_count = int((nonblank_values & values.isna()).sum())
    duplicate_date_count = int(dates.dropna().duplicated(keep=False).sum())

    start = pd.Timestamp(study_start)
    end = pd.Timestamp(study_end)
    cutoff = pd.Timestamp(treatment_cutoff)
    valid = dates.notna() & values.notna()
    in_window = valid & dates.between(start, end, inclusive="both")
    window_dates = dates.loc[in_window]
    window_values = values.loc[in_window]
    coverage = _calendar_coverage(
        window_dates,
        frequency=spec["frequency"],
        start=start,
        end=end,
    )

    sorted_dates = dates.loc[valid].sort_values()
    gaps = sorted_dates.diff().dt.days.dropna()
    first_post_week = pd.date_range(
        start=cutoff + pd.Timedelta(days=1), periods=1, freq="W-FRI"
    )[0]
    return {
        "schema_valid": True,
        "missing_columns": [],
        "row_count": int(len(data)),
        "dated_observations": int(dates.notna().sum()),
        "priced_observations": int(valid.sum()),
        "invalid_date_count": invalid_date_count,
        "invalid_value_count": invalid_value_count,
        "missing_value_count": int((dates.notna() & values.isna()).sum()),
        "duplicate_date_count": duplicate_date_count,
        "zero_value_count": int((values.loc[valid] == 0).sum()),
        "study_window_observations": int(in_window.sum()),
        "pre_treatment_observations": int(
            (in_window & dates.lt(cutoff)).sum()
        ),
        "post_treatment_observations": int(
            (in_window & dates.ge(cutoff)).sum()
        ),
        "first_expected_post_week": first_post_week.date().isoformat(),
        "earliest_date": (
            sorted_dates.min().date().isoformat() if len(sorted_dates) else None
        ),
        "latest_date": (
            sorted_dates.max().date().isoformat() if len(sorted_dates) else None
        ),
        "minimum_value": float(values.loc[valid].min()) if valid.any() else None,
        "maximum_value": float(values.loc[valid].max()) if valid.any() else None,
        "longest_calendar_gap_days": int(gaps.max()) if len(gaps) else None,
        **coverage,
    }


def _all_rights_confirmed(spec: dict[str, Any]) -> bool:
    rights = spec.get("rights", {})
    required_permissions = {
        "historical_export",
        "raw_retention",
        "thesis_modelling",
        "derived_results_publication",
    }
    return (
        all(rights.get(field) is True for field in required_permissions)
        and rights.get("raw_publication") in {True, False}
    )


def admission_gates(
    spec: dict[str, Any],
    metrics: dict[str, Any],
    *,
    file_present: bool,
    checksum_match: bool,
) -> dict[str, bool]:
    """Evaluate predeclared Phase 0 gates; every false value blocks admission."""
    role = spec["candidate_role"]
    weekly_freight = role == "secondary_freight_outcome"
    schema_valid = bool(metrics.get("schema_valid"))
    parse_valid = (
        schema_valid
        and metrics.get("invalid_date_count") == 0
        and metrics.get("invalid_value_count") == 0
    )
    gates = {
        "file_present": file_present,
        "checksum_match": checksum_match,
        "workbook_schema_valid": schema_valid,
        "dates_and_values_parse": parse_valid,
        "no_duplicate_dates": metrics.get("duplicate_date_count") == 0,
        "calendar_missingness_at_most_10pct": (
            metrics.get("missing_ratio", 1.0) <= 0.10
        ),
        "assessment_calendar_confirmed": (
            spec.get("assessment_calendar_verified") is True
        ),
        "exact_bloomberg_identifier_present": bool(
            spec.get("bloomberg_identifier")
        ),
        "original_provider_present": bool(spec.get("original_provider")),
        "assessment_methodology_documented": bool(
            spec.get("assessment_methodology")
        ),
        "stable_definition_confirmed": spec.get("definition_stable") is True,
        "price_field_present": bool(spec.get("price_field")),
        "publication_convention_present": bool(
            spec.get("publication_time") and spec.get("timezone")
        ),
        "extraction_date_present": bool(spec.get("extraction_date")),
        "export_procedure_present": bool(spec.get("export_procedure")),
        "missing_value_convention_present": bool(
            spec.get("missing_value_convention")
        ),
        "zero_treatment_confirmed": spec.get("zero_is_genuine") is not None,
        "original_terminal_export_preserved": (
            spec.get("source_artifact_status") == "original_terminal_export"
        ),
        "licence_and_thesis_rights_confirmed": _all_rights_confirmed(spec),
    }
    if weekly_freight:
        gates.update(
            {
                "at_least_52_pre_treatment_observations": (
                    metrics.get("pre_treatment_observations", 0) >= 52
                ),
                "at_least_12_post_treatment_observations": (
                    metrics.get("post_treatment_observations", 0) >= 12
                ),
                "usd_per_day_unit_confirmed": (
                    spec.get("currency") == "USD" and spec.get("unit") == "USD/day"
                ),
            }
        )
    return gates


def audit_export(
    logical_name: str,
    spec: dict[str, Any],
    export_dir: Path,
    *,
    study_start: str,
    study_end: str,
    treatment_cutoff: str,
) -> dict[str, Any]:
    path = export_dir / spec["filename"]
    file_present = path.is_file()
    actual_sha256 = sha256_file(path) if file_present else None
    checksum_match = actual_sha256 == spec["expected_sha256"]
    metrics: dict[str, Any] = {"schema_valid": False}
    read_error = None
    if file_present:
        try:
            frame = pd.read_excel(
                path,
                sheet_name=spec["raw_sheet"],
                dtype=object,
                engine="openpyxl",
            )
            metrics = audit_frame(
                frame,
                spec,
                study_start=study_start,
                study_end=study_end,
                treatment_cutoff=treatment_cutoff,
            )
        except Exception as exc:
            read_error = f"{type(exc).__name__}: {exc}"

    gates = admission_gates(
        spec,
        metrics,
        file_present=file_present,
        checksum_match=checksum_match,
    )
    failed_gates = [name for name, passed in gates.items() if not passed]
    return {
        "logical_name": logical_name,
        "filename": spec["filename"],
        "displayed_series_name": spec["displayed_series_name"],
        "candidate_role": spec["candidate_role"],
        "frequency": spec["frequency"],
        "unit": spec.get("unit"),
        "currency": spec.get("currency"),
        "expected_sha256": spec["expected_sha256"],
        "actual_sha256": actual_sha256,
        "source_artifact_status": spec["source_artifact_status"],
        "read_error": read_error,
        "metrics": metrics,
        "gates": gates,
        "failed_gates": failed_gates,
        "admitted": not failed_gates,
        "decision": "admitted" if not failed_gates else "blocked",
    }


def flatten_result(result: dict[str, Any]) -> dict[str, Any]:
    """Flatten one nested result into the stable CSV audit representation."""
    flat = {
        key: value
        for key, value in result.items()
        if key not in {"metrics", "gates", "failed_gates"}
    }
    flat.update(result["metrics"])
    flat["failed_gate_count"] = len(result["failed_gates"])
    flat["failed_gates"] = "|".join(result["failed_gates"])
    for name, passed in result["gates"].items():
        flat[f"gate__{name}"] = passed
    return flat
