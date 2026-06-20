"""Reproducible local audit for the LNG vessel-data feasibility gate."""
from __future__ import annotations

from pathlib import Path
import json
import re
from typing import Mapping

import pandas as pd


INPUT_SCHEMAS = {
    "gfw_lng_vessel_benchmark_csv": {
        "imo", "vessel_name", "lng_capacity_m3", "source"
    },
    "gfw_vessel_identity_csv": {"imo", "vessel_id"},
    "gfw_port_visits_csv": {
        "vessel_id", "start", "end", "port_id", "lat", "lon"
    },
    "gfw_lng_terminals_csv": {
        "port_id", "terminal_name", "terminal_role", "country", "source"
    },
}


def _normalize_imo(value: object) -> str:
    if pd.isna(value):
        return ""
    text = str(value).strip()
    return text[:-2] if text.endswith(".0") else text


def _valid_imo(value: object) -> bool:
    """Return whether a value satisfies the seven-digit IMO checksum."""
    imo = _normalize_imo(value)
    if not re.fullmatch(r"\d{7}", imo):
        return False
    checksum = sum(
        int(digit) * weight
        for digit, weight in zip(imo[:6], range(7, 1, -1))
    )
    return checksum % 10 == int(imo[-1])


def _profile_csv(
    path: Path,
    required: set[str] | None = None,
    root: Path | None = None,
) -> dict:
    display_path = (
        path.relative_to(root).as_posix()
        if root is not None and path.is_relative_to(root)
        else path.as_posix()
    )
    if not path.exists():
        return {"present": False, "path": display_path}
    frame = pd.read_csv(path)
    columns = list(frame.columns)
    missing = sorted((required or set()) - set(columns))
    result = {
        "present": True,
        "path": display_path,
        "rows": int(len(frame)),
        "columns": columns,
        "schema_valid": not missing,
        "missing_columns": missing,
    }
    if "voy_load_date" in frame.columns and len(frame):
        dates = pd.to_datetime(frame["voy_load_date"], errors="coerce").dropna()
        if len(dates):
            result["start"] = dates.min().date().isoformat()
            result["end"] = dates.max().date().isoformat()
    return result


def _profile_benchmark_roster(
    path: Path,
    required: set[str],
    minimum_vessels: int,
    root: Path,
) -> dict:
    result = _profile_csv(path, required, root=root)
    if not result.get("present") or not result.get("schema_valid"):
        return result

    frame = pd.read_csv(path)
    imos = frame["imo"].map(_normalize_imo)
    capacities = pd.to_numeric(frame["lng_capacity_m3"], errors="coerce")
    blank_names = frame["vessel_name"].isna() | (
        frame["vessel_name"].astype(str).str.strip().eq("")
    )
    blank_sources = frame["source"].isna() | (
        frame["source"].astype(str).str.strip().eq("")
    )
    valid_imos = imos.map(_valid_imo)
    unique_imos = int(imos[imos.ne("")].nunique())
    diagnostics = {
        "minimum_vessels_required": int(minimum_vessels),
        "unique_imo_count": unique_imos,
        "duplicate_imo_rows": int(imos[imos.ne("")].duplicated().sum()),
        "invalid_imo_rows": int((~valid_imos).sum()),
        "blank_vessel_name_rows": int(blank_names.sum()),
        "invalid_capacity_rows": int((capacities.isna() | capacities.le(0)).sum()),
        "blank_source_rows": int(blank_sources.sum()),
    }
    result["roster_diagnostics"] = diagnostics
    result["quality_valid"] = (
        unique_imos >= minimum_vessels
        and all(
            diagnostics[key] == 0
            for key in (
                "duplicate_imo_rows",
                "invalid_imo_rows",
                "blank_vessel_name_rows",
                "invalid_capacity_rows",
                "blank_source_rows",
            )
        )
    )
    return result


def _gfw_coverage_diagnostics(
    roster_path: Path,
    identity_path: Path,
    visits_path: Path,
    minimum_visit_rate: float,
) -> dict | None:
    if not all(path.exists() for path in (roster_path, identity_path, visits_path)):
        return None
    roster = pd.read_csv(roster_path, dtype={"imo": str})
    identities = pd.read_csv(identity_path, dtype={"imo": str})
    visits = pd.read_csv(visits_path)
    if not {"imo", "vessel_id"}.issubset(identities.columns) or not {
        "vessel_id", "sample_period"
    }.issubset(visits.columns):
        return None

    roster_imos = set(roster["imo"].dropna().astype(str))
    matched_imos = set(identities["imo"].dropna().astype(str)) & roster_imos
    merged = visits.merge(identities[["imo", "vessel_id"]], on="vessel_id", how="left")
    period_coverage = {}
    for period, group in merged.groupby("sample_period"):
        covered = set(group["imo"].dropna().astype(str)) & matched_imos
        rate = len(covered) / len(matched_imos) if matched_imos else 0.0
        period_coverage[str(period)] = {
            "covered_imos": len(covered),
            "matched_imo_denominator": len(matched_imos),
            "coverage_rate": rate,
            "passes_threshold": rate >= minimum_visit_rate,
        }
    return {
        "roster_imos": len(roster_imos),
        "matched_imos": len(matched_imos),
        "identity_match_rate": (
            len(matched_imos) / len(roster_imos) if roster_imos else 0.0
        ),
        "periods": period_coverage,
        "all_periods_pass": (
            {"pre", "post"}.issubset(period_coverage)
            and all(item["passes_threshold"] for item in period_coverage.values())
        ),
    }


def build_vessel_feasibility_report(
    root: Path,
    settings: Mapping,
    credential_presence: Mapping[str, bool],
) -> dict:
    """Inspect local evidence without calling or exposing credentialed APIs."""
    paths = settings["paths"]
    criteria = dict(settings["vessel_data_feasibility"])
    wto = _profile_csv(root / paths["wto_hormuz_lng_csv"], root=root)
    portwatch = _profile_csv(root / paths["portwatch_csv"], root=root)
    inputs = {
        key: _profile_csv(root / paths[key], required, root=root)
        for key, required in INPUT_SCHEMAS.items()
    }
    roster_key = "gfw_lng_vessel_benchmark_csv"
    inputs[roster_key] = _profile_benchmark_roster(
        root / paths[roster_key],
        INPUT_SCHEMAS[roster_key],
        int(criteria["benchmark_vessels"]),
        root,
    )
    coverage = _gfw_coverage_diagnostics(
        root / paths[roster_key],
        root / paths["gfw_vessel_identity_csv"],
        root / paths["gfw_port_visits_csv"],
        float(criteria["min_port_visit_coverage_rate"]),
    )
    summary_path = paths.get("voyage_feasibility_summary_json")
    voyage_summary = None
    if summary_path and (root / summary_path).exists():
        voyage_summary = json.loads((root / summary_path).read_text())

    gfw_token = bool(credential_presence.get("GFW_API_TOKEN"))
    inputs_ready = gfw_token and all(
        item.get("present")
        and item.get("schema_valid")
        and (key != roster_key or item.get("quality_valid"))
        for key, item in inputs.items()
    )
    coverage_ready = bool(
        coverage
        and coverage["identity_match_rate"] >= criteria["min_identity_match_rate"]
        and coverage["all_periods_pass"]
    )
    endpoint_ready = bool(voyage_summary and voyage_summary.get("passes_threshold"))
    blockers = []
    if not gfw_token:
        blockers.append("GFW_API_TOKEN is not configured")
    for key, item in inputs.items():
        if not item.get("present"):
            blockers.append(f"missing {key}")
        elif not item.get("schema_valid"):
            blockers.append(f"invalid schema for {key}")
        elif key == roster_key and not item.get("quality_valid"):
            blockers.append("benchmark roster does not meet quality criteria")

    spark_ready = bool(credential_presence.get("SPARK_CLIENT_ID")) and bool(
        credential_presence.get("SPARK_CLIENT_SECRET")
    )
    if not inputs_ready:
        empirical_status = "blocked_pending_access_and_sample"
    elif not coverage_ready:
        empirical_status = "sample_scored_below_coverage_threshold"
    elif not endpoint_ready:
        empirical_status = "sample_ready_for_endpoint_scoring"
    else:
        empirical_status = "qflex_port_sequence_feasibility_passed_scope_limited"

    return {
        "audit_date": "2026-06-19",
        "local_evidence": {
            "wto_lng_outbound_index": wto,
            "portwatch_chokepoints": portwatch,
        },
        "gfw": {
            "token_configured": gfw_token,
            "documented_capabilities": [
                "all-vessel identity search",
                "all-vessel port-visit events",
                "gridded hourly vessel presence",
            ],
            "documented_limitations": [
                "presence product is not an individual raw vessel track",
                "no observed LNG cargo quantity",
                "no authoritative laden/ballast state",
            ],
            "required_local_inputs": inputs,
            "coverage_diagnostics": coverage,
            "voyage_feasibility": voyage_summary,
        },
        "acceptance_criteria": criteria,
        "empirical_vessel_branch": {
            "status": empirical_status,
            "blockers": blockers,
            "maximum_defensible_measure_if_passed": criteria["accepted_measure"],
            "prohibited_label": criteria["prohibited_measure_label"],
        },
        "simulation_fallback": {
            "status": "partially_ready",
            "available_input": "daily aggregate LNG outbound-volume index",
            "still_needed": [
                "bilateral LNG origin-destination flows",
                "liquefaction and regasification capacities",
                "route-distance matrix",
                "documented vessel-capacity assumptions",
            ],
        },
        "spark_extension": {
            "status": (
                "credentials_available_for_probe"
                if spark_ready
                else "dormant_access_unverified"
            ),
            "preserved": True,
        },
    }
