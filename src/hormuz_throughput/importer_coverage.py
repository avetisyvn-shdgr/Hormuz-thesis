"""Coverage audit for the proposed importer-vulnerability panel.

This module evaluates frozen source snapshots only. It does not fetch data and
does not construct modelling outcomes when the admission conditions fail.
"""
from __future__ import annotations

import hashlib
import itertools
import json
import re
from pathlib import Path

import pandas as pd


TREATMENT_MONTH = "2026-03"
PRE_END_MONTH = "2026-02"
MIN_CONTIGUOUS_PRE_MONTHS = 12
MIN_POST_MONTHS = 3
MIN_IMPORTERS = 15

CORE_IMPORTERS = (
    "Japan",
    "India",
    "South Korea",
    "China",
    "Taiwan",
    "Pakistan",
    "Bangladesh",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_probe_manifest(probe_dir: Path) -> dict[str, str]:
    manifest = json.loads((probe_dir / "MANIFEST.json").read_text(encoding="utf-8"))
    hashes: dict[str, str] = {}
    for record in manifest["files"]:
        path = probe_dir / record["file"]
        if not path.is_file():
            raise FileNotFoundError(f"coverage-probe snapshot missing: {path}")
        actual = sha256_file(path)
        if actual != record["sha256"]:
            raise ValueError(f"coverage-probe hash mismatch: {path}")
        hashes[record["file"]] = actual
    return hashes


def _contiguous_pre_months(months: set[str]) -> int:
    current = pd.Period(PRE_END_MONTH, freq="M")
    count = 0
    while str(current) in months:
        count += 1
        current -= 1
    return count


def _coverage_counts(months: set[str]) -> tuple[int, int, str | None]:
    return (
        _contiguous_pre_months(months),
        sum(month >= TREATMENT_MONTH for month in months),
        max(months) if months else None,
    )


def japan_coverage(path: Path) -> tuple[int, int, str | None]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    months = {
        f"{row['period'][:4]}-{row['period'][4:]}"
        for row in payload["data"]
        if row.get("flowCode") == "M" and row.get("partnerCode") == 0
    }
    return _coverage_counts(months)


def _jsonstat_frame(payload: dict) -> pd.DataFrame:
    dimensions = payload["id"]
    categories: list[list[str]] = []
    for dimension in dimensions:
        positions = payload["dimension"][dimension]["category"]["index"]
        ordered = [""] * len(positions)
        for value, position in positions.items():
            ordered[position] = value
        categories.append(ordered)
    values = payload["value"]
    rows = []
    for flat_index, coordinates in enumerate(itertools.product(*categories)):
        value = (
            values.get(str(flat_index))
            if isinstance(values, dict)
            else values[flat_index]
        )
        if value is not None:
            rows.append((*coordinates, value))
    return pd.DataFrame(rows, columns=[*dimensions, "value"])


def eu27_coverage(path: Path) -> tuple[int, int, str | None]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    frame = _jsonstat_frame(payload)
    months = set(frame.loc[frame["partner"] == "TOTAL", "time"].astype(str))
    return _coverage_counts(months)


def _ppac_sheet_months(path: Path) -> set[str]:
    months: set[str] = set()
    workbook = pd.ExcelFile(path)
    for sheet_name in workbook.sheet_names:
        match = re.search(r"(20\d{2})-(\d{2})", sheet_name)
        if not match and path.suffix.lower() == ".xls":
            frame = pd.read_excel(path, sheet_name=sheet_name, header=None)
            text = " ".join(str(value) for value in frame.iloc[:, 0].dropna())
            match = re.search(r"(20\d{2})-(\d{2})", text)
        else:
            frame = pd.read_excel(path, sheet_name=sheet_name, header=None)
        if not match:
            continue
        start_year = int(match.group(1))
        month_row = frame.index[
            frame.iloc[:, 0].astype(str).str.strip().eq("Month")
        ]
        value_row = frame.index[
            frame.iloc[:, 0].astype(str).str.contains(
                "Total LNG Imports .* in MMT", regex=True, na=False
            )
        ]
        if month_row.empty or value_row.empty:
            continue
        labels = frame.loc[month_row[0]].iloc[1:13]
        values = frame.loc[value_row[0]].iloc[1:13]
        for label, value in zip(labels, values, strict=True):
            if pd.isna(label) or pd.isna(value):
                continue
            month_number = pd.Timestamp(f"2000-{str(label).strip()}-01").month
            year = start_year if month_number >= 4 else start_year + 1
            months.add(f"{year:04d}-{month_number:02d}")
    return months


def india_coverage(historical: Path, current: Path) -> tuple[int, int, str | None]:
    months = _ppac_sheet_months(historical) | _ppac_sheet_months(current)
    return _coverage_counts(months)


def admission_status(
    *,
    unit_type: str,
    official_total: bool,
    official_by_source: bool,
    contiguous_pre_months: int,
    post_months: int,
) -> tuple[bool, str]:
    reasons = []
    if unit_type != "importer":
        reasons.append("aggregate comparator, not an importer unit")
    if not official_total:
        reasons.append("no frozen official total-volume series")
    if not official_by_source:
        reasons.append("no frozen official by-source series for Exposure")
    if contiguous_pre_months < MIN_CONTIGUOUS_PRE_MONTHS:
        reasons.append(
            f"{contiguous_pre_months} contiguous pre months < "
            f"{MIN_CONTIGUOUS_PRE_MONTHS}"
        )
    if post_months < MIN_POST_MONTHS:
        reasons.append(f"{post_months} post months < {MIN_POST_MONTHS}")
    return (not reasons, "admitted" if not reasons else "; ".join(reasons))


def build_coverage_matrix(
    probe_dir: Path, gfw_summary_path: Path
) -> pd.DataFrame:
    hashes = verify_probe_manifest(probe_dir)
    gfw = pd.read_csv(gfw_summary_path).set_index("destination_country")

    source_rows = {
        "Japan": {
            "unit_type": "importer",
            "official_source": "UN Comtrade HS 271111",
            "snapshot_file": "comtrade_japan_lng271111_bypartner.json",
            "official_total": True,
            "official_by_source": True,
            "coverage": japan_coverage(
                probe_dir / "comtrade_japan_lng271111_bypartner.json"
            ),
            "limitation": "Frozen series has a gap before 2025-10 and one post month.",
        },
        "India": {
            "unit_type": "importer",
            "official_source": "PPAC/DGCIS",
            "snapshot_file": "ppac_lng_import_historical.xlsx + ppac_lng_import_current.xls",
            "official_total": True,
            "official_by_source": False,
            "coverage": india_coverage(
                probe_dir / "ppac_lng_import_historical.xlsx",
                probe_dir / "ppac_lng_import_current.xls",
            ),
            "limitation": "Monthly total LNG only; no origin split.",
        },
        "EU27": {
            "unit_type": "aggregate_comparator",
            "official_source": "Eurostat nrg_ti_gasm",
            "snapshot_file": "eurostat_nrg_ti_gasm_lng_eu27_by_partner.json",
            "official_total": True,
            "official_by_source": True,
            "coverage": eu27_coverage(
                probe_dir / "eurostat_nrg_ti_gasm_lng_eu27_by_partner.json"
            ),
            "limitation": "EU27 aggregate is a descriptive comparator, not an importer unit.",
        },
    }
    for country in CORE_IMPORTERS:
        source_rows.setdefault(country, {
            "unit_type": "importer",
            "official_source": "none frozen",
            "snapshot_file": "",
            "official_total": False,
            "official_by_source": False,
            "coverage": (0, 0, None),
            "limitation": "Candidate national source not yet frozen and verified.",
        })

    rows = []
    for country in (*CORE_IMPORTERS, "EU27"):
        source = source_rows[country]
        pre_months, post_months, latest = source["coverage"]
        admitted, reason = admission_status(
            unit_type=source["unit_type"],
            official_total=source["official_total"],
            official_by_source=source["official_by_source"],
            contiguous_pre_months=pre_months,
            post_months=post_months,
        )
        if country in gfw.index:
            gfw_row = gfw.loc[country]
            gfw_pre = int(gfw_row["pre_resolved_voyages"])
            gfw_post = int(gfw_row["post_resolved_voyages"])
            gfw_admitted = bool(gfw_row["country_hormuz_exposed_estimate_estimable"])
        else:
            gfw_pre = None
            gfw_post = None
            gfw_admitted = False
        snapshot_files = [part.strip() for part in source["snapshot_file"].split("+")]
        snapshot_hashes = [hashes[name] for name in snapshot_files if name]
        rows.append({
            "unit": country,
            "unit_type": source["unit_type"],
            "official_source": source["official_source"],
            "snapshot_file": source["snapshot_file"],
            "snapshot_sha256": ";".join(snapshot_hashes),
            "official_total_available": source["official_total"],
            "official_by_source_available": source["official_by_source"],
            "frequency": "monthly" if source["official_total"] else "",
            "contiguous_pre_months": pre_months,
            "post_months": post_months,
            "latest_period": latest or "",
            "gfw_pre_resolved_voyages": gfw_pre,
            "gfw_post_resolved_voyages": gfw_post,
            "gfw_country_gulf_estimate_admissible": gfw_admitted,
            "confirmatory_panel_admissible": admitted,
            "admission_reason": reason,
            "source_limitation": source["limitation"],
        })
    return pd.DataFrame(rows)


def coverage_summary(matrix: pd.DataFrame) -> dict[str, object]:
    admitted = matrix.loc[
        (matrix["unit_type"] == "importer")
        & matrix["confirmatory_panel_admissible"],
        "unit",
    ].tolist()
    return {
        "status": "pass" if len(admitted) >= MIN_IMPORTERS else "no_go",
        "admitted_importers": admitted,
        "admitted_importer_count": len(admitted),
        "minimum_importers": MIN_IMPORTERS,
        "minimum_contiguous_pre_months": MIN_CONTIGUOUS_PRE_MONTHS,
        "minimum_post_months": MIN_POST_MONTHS,
        "treatment_month": TREATMENT_MONTH,
        "interpretation": (
            "Current frozen public data do not admit the proposed confirmatory "
            "importer panel. Do not freeze or estimate the Option D model."
            if len(admitted) < MIN_IMPORTERS
            else "Coverage admission threshold met; design review may proceed."
        ),
    }
