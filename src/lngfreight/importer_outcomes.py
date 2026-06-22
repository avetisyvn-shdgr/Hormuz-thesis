"""Importer LNG outcome module (task V2).

Builds the pre-registered outcomes from the *frozen, hash-verified* coverage-probe
snapshots only. No network access: provenance is the snapshot SHA-256 recorded per
series. A live `registry.get_variable()` path is intentionally NOT used here because
no Comtrade/Eurostat/PPAC provider exists yet (`src/lngfreight/sources/`); wiring
those providers is a separate V-layer task. Building on the frozen snapshot keeps
this deterministic and consistent with the `--frozen-raw` pipeline.

Scope honesty (mirrors the V1 NO_GO finding):
- Only by-source units carry the Gulf outcome: Japan (Comtrade) and EU27 (Eurostat).
- India (PPAC) is total-volume only and is added in a later increment (Y2 only).
- Y4 (composite vulnerability) is DEFERRED: its storage-drawdown and delay
  components are unsourced ([VERIFY]); they are not fabricated here.

Outcome tags follow `docs/CAPTIVITY_EVENT_STUDY_DESIGN.md` 6.3. The primary outcome
is Y1 because the estimand names it, not because of any fitted result.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from .importer_coverage import _jsonstat_frame, verify_probe_manifest

TREATMENT_MONTH = "2026-03"

# Hormuz-dependent LNG exporters (design doc 6.3). Oman is deliberately EXCLUDED:
# Omani LNG ships from Sur on the Gulf of Oman, outside the Strait of Hormuz, so it
# is not Hormuz-dependent. Codes below are the *source-native* partner codes.
COMTRADE_GULF_CODES = {
    634: "Qatar",
    784: "United Arab Emirates",
    414: "Kuwait",
    368: "Iraq",
    682: "Saudi Arabia",
    48: "Bahrain",
    364: "Iran",
}
EUROSTAT_GULF_CODES = {"QA", "AE", "KW", "IQ", "SA", "BH", "IR"}

OUTCOME_TAGS = (
    "y1_gulf_volume",
    "y1_gulf_share",
    "y2_total_volume",
    "y3_non_gulf_volume",
)

DEFERRED_OUTCOMES = ("y4_composite_vulnerability",)

FRAME_COLUMNS = [
    "unit",
    "unit_type",
    "month",
    "outcome",
    "value",
    "unit_of_measure",
    "source",
    "snapshot_sha256",
    "post_treatment",
]


def _outcome_rows(
    *,
    unit: str,
    unit_type: str,
    source: str,
    unit_of_measure: str,
    snapshot_sha256: str,
    monthly_total: dict[str, float],
    monthly_gulf: dict[str, float],
) -> list[dict]:
    """Long-format rows for one unit. A month enters only if its official TOTAL is
    present; an absent Gulf-partner-month means no recorded trade (contributes 0)."""
    rows: list[dict] = []
    for month in sorted(monthly_total):
        total = monthly_total[month]
        gulf = monthly_gulf.get(month, 0.0)
        non_gulf = total - gulf
        share = gulf / total if total else None
        values = {
            "y1_gulf_volume": gulf,
            "y1_gulf_share": share,
            "y2_total_volume": total,
            "y3_non_gulf_volume": non_gulf,
        }
        for outcome, value in values.items():
            rows.append(
                {
                    "unit": unit,
                    "unit_type": unit_type,
                    "month": month,
                    "outcome": outcome,
                    "value": value,
                    "unit_of_measure": (
                        "ratio" if outcome == "y1_gulf_share" else unit_of_measure
                    ),
                    "source": source,
                    "snapshot_sha256": snapshot_sha256,
                    "post_treatment": month >= TREATMENT_MONTH,
                }
            )
    return rows


def japan_outcomes(path: Path, snapshot_sha256: str) -> list[dict]:
    """Y1-Y3 for Japan from the Comtrade HS 271111 by-partner snapshot (kg)."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    monthly_total: dict[str, float] = {}
    monthly_gulf: dict[str, float] = {}
    for record in payload["data"]:
        if record.get("flowCode") != "M":
            continue
        weight = record.get("netWgt")
        if weight is None:
            continue
        period = record["period"]
        month = f"{period[:4]}-{period[4:]}"
        code = record.get("partnerCode")
        if code == 0:  # World aggregate = total imports
            monthly_total[month] = float(weight)
        elif code in COMTRADE_GULF_CODES:
            monthly_gulf[month] = monthly_gulf.get(month, 0.0) + float(weight)
    monthly_gulf = {m: v for m, v in monthly_gulf.items() if m in monthly_total}
    return _outcome_rows(
        unit="Japan",
        unit_type="importer",
        source="UN Comtrade HS 271111",
        unit_of_measure="kg",
        snapshot_sha256=snapshot_sha256,
        monthly_total=monthly_total,
        monthly_gulf=monthly_gulf,
    )


def eu27_outcomes(path: Path, snapshot_sha256: str) -> list[dict]:
    """Y1-Y3 for EU27 from the Eurostat nrg_ti_gasm by-partner snapshot (MIO_M3).

    EU27 is an aggregate comparator, not a single importer unit (flagged in the
    unit_type) but it carries a usable by-source split."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    frame = _jsonstat_frame(payload)
    monthly_total: dict[str, float] = {}
    monthly_gulf: dict[str, float] = {}
    for partner, month, value in zip(
        frame["partner"], frame["time"].astype(str), frame["value"], strict=True
    ):
        if value is None or pd.isna(value):
            continue
        if partner == "TOTAL":
            monthly_total[month] = float(value)
        elif partner in EUROSTAT_GULF_CODES:
            monthly_gulf[month] = monthly_gulf.get(month, 0.0) + float(value)
    monthly_gulf = {m: v for m, v in monthly_gulf.items() if m in monthly_total}
    return _outcome_rows(
        unit="EU27",
        unit_type="aggregate_comparator",
        source="Eurostat nrg_ti_gasm",
        unit_of_measure="MIO_M3",
        snapshot_sha256=snapshot_sha256,
        monthly_total=monthly_total,
        monthly_gulf=monthly_gulf,
    )


def build_outcomes(probe_dir: Path) -> pd.DataFrame:
    """Assemble the long-format outcome frame from the verified frozen snapshots."""
    hashes = verify_probe_manifest(probe_dir)
    rows: list[dict] = []
    rows += japan_outcomes(
        probe_dir / "comtrade_japan_lng271111_bypartner.json",
        hashes["comtrade_japan_lng271111_bypartner.json"],
    )
    rows += eu27_outcomes(
        probe_dir / "eurostat_nrg_ti_gasm_lng_eu27_by_partner.json",
        hashes["eurostat_nrg_ti_gasm_lng_eu27_by_partner.json"],
    )
    frame = pd.DataFrame(rows, columns=FRAME_COLUMNS)
    return frame.sort_values(["unit", "outcome", "month"]).reset_index(drop=True)


def outcomes_summary(frame: pd.DataFrame) -> dict[str, object]:
    gulf_units = sorted(
        frame.loc[frame["outcome"] == "y1_gulf_share", "unit"].unique().tolist()
    )
    return {
        "units": sorted(frame["unit"].unique().tolist()),
        "units_with_gulf_outcome": gulf_units,
        "outcomes_built": sorted(frame["outcome"].unique().tolist()),
        "outcomes_deferred": list(DEFERRED_OUTCOMES),
        "y4_deferral_reason": (
            "Composite vulnerability needs storage-drawdown and delay components "
            "that are unsourced ([VERIFY]); not fabricated."
        ),
        "month_range": [str(frame["month"].min()), str(frame["month"].max())],
        "treatment_month": TREATMENT_MONTH,
        "row_count": int(len(frame)),
        "interpretation": (
            "Descriptive-grade outcomes for the by-source units only (Japan, EU27). "
            "Not an admissible confirmatory panel -- see the V1 NO_GO coverage report."
        ),
    }
