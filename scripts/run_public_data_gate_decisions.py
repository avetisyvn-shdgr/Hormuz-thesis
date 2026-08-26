"""Task 9: optional public-data gate decision table.

This is a governance phase, not an empirical one. It downloads nothing,
registers nothing, and analyses nothing. It renders a frozen decision table
recording, for each candidate public dataset, the single narrow use it could
ever be admitted for, the rights and coverage it would need, and the criteria
that would kill it.

The table cannot itself admit anything. Every candidate carries a non-GO status,
and a GO requires Mher's explicit written scope reopening recorded in the
decision log before any acquisition.

Deliberately imports no HTTP client. The integrity pins verify that the source
registry is byte-identical to its pre-phase state, so this phase provably added
no registered variable.

Run from the repo root:
    python scripts/run_public_data_gate_decisions.py
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pandas as pd
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lngfreight import config  # noqa: E402


DESIGN_PATH = config.CONFIG_DIR / "public_data_gate_decisions.yaml"
NOT_APPLICABLE = "not_applicable"

TABLE_COLUMNS = [
    "candidate",
    "display_name",
    "status",
    "reopening_required",
    "permitted_use",
    "prohibited_use",
    "required_rights",
    "coverage",
    "reporting_lag",
    "estimand_relevance",
    "kill_criteria_count",
    "kill_criteria",
    "blocking_reason",
]


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_design() -> tuple[dict, str]:
    raw = DESIGN_PATH.read_bytes()
    return yaml.safe_load(raw), hashlib.sha256(raw).hexdigest()


def output_path(design: dict, key: str) -> Path:
    return config.ROOT / design["outputs"][key]


def verify_integrity_pins(design: dict) -> dict:
    """Prove this phase changed no registry entry and no verified manifest."""
    results = {}
    for label, spec in design["integrity_pins"].items():
        path = config.ROOT / spec["path"]
        if not path.is_file():
            raise FileNotFoundError(f"integrity pin missing: {label}")
        actual = sha256_file(path)
        if actual != spec["sha256"]:
            raise ValueError(
                f"integrity pin drift for {label}: {actual}. This phase must "
                "not modify the registry or any G4-verified manifest."
            )
        results[label] = actual

    registry = yaml.safe_load(
        (config.ROOT / design["integrity_pins"]["sources_registry"]["path"])
        .read_text(encoding="utf-8")
    )["variables"]
    expected_count = int(
        design["integrity_pins"]["sources_registry"]["registered_variable_count"]
    )
    if len(registry) != expected_count:
        raise ValueError(
            f"registered variable count changed: {len(registry)} != "
            f"{expected_count}; this phase adds no data source"
        )
    return results


def build_table(design: dict) -> pd.DataFrame:
    rows = []
    for key, spec in design["candidates"].items():
        kill = list(spec["kill_criteria"])
        rows.append({
            "candidate": key,
            "display_name": spec["display_name"],
            "status": spec["status"],
            "reopening_required": bool(spec["reopening_required"]),
            "permitted_use": " ".join(spec["permitted_use"].split()),
            "prohibited_use": " ".join(spec["prohibited_use"].split()),
            "required_rights": spec["required_rights"],
            "coverage": spec["coverage"],
            "reporting_lag": spec["reporting_lag"],
            "estimand_relevance": " ".join(spec["estimand_relevance"].split()),
            "kill_criteria_count": len(kill),
            "kill_criteria": " | ".join(kill),
            # Explicit sentinel rather than an empty string: "" round-trips
            # through CSV as NaN and would silently weaken the NO_GO check.
            "blocking_reason": " ".join(
                spec.get("blocking_reason", "").split()
            ) or NOT_APPLICABLE,
        })
    table = pd.DataFrame(rows, columns=TABLE_COLUMNS)
    guard_table(design, table)
    return table.sort_values("candidate", kind="stable").reset_index(drop=True)


def guard_table(design: dict, table: pd.DataFrame) -> None:
    """Structural invariants for the decision table."""
    if table.empty:
        raise AssertionError("public-data gate table is empty")
    expected = set(design["candidates"])
    if set(table["candidate"]) != expected:
        raise AssertionError("decision table does not cover every candidate")

    permitted = set(design["permitted_statuses"])
    unknown = set(table["status"]).difference(permitted)
    if unknown:
        raise AssertionError(f"unpermitted gate status: {sorted(unknown)}")
    if design["go_status_permitted"]:
        raise AssertionError(
            "the design must not permit a GO status; admission requires an "
            "explicit scope reopening recorded outside this table"
        )
    if table["status"].str.upper().eq("GO").any():
        raise AssertionError("a candidate was marked GO; this phase cannot admit")
    if not table["reopening_required"].all():
        raise AssertionError(
            "every candidate must require an explicit scope reopening"
        )
    if table["kill_criteria_count"].lt(1).any():
        raise AssertionError("every candidate needs at least one kill criterion")
    for column in (
        "permitted_use",
        "prohibited_use",
        "required_rights",
        "coverage",
        "reporting_lag",
        "estimand_relevance",
    ):
        if table[column].astype(str).str.strip().eq("").any():
            raise AssertionError(f"decision table has a blank {column}")

    blocked = table.loc[table["status"].eq("NO_GO")]
    reasons = blocked["blocking_reason"].astype(str).str.strip()
    if reasons.eq("").any() or reasons.eq(NOT_APPLICABLE).any():
        raise AssertionError("a NO_GO candidate lacks a stated blocking reason")


def build_diagnostics(
    design: dict, design_sha256: str, table: pd.DataFrame, pins: dict
) -> dict:
    counts = table["status"].value_counts().to_dict()
    return {
        "design_id": design["design_id"],
        "design_sha256": design_sha256,
        "analysis_role": design["analysis_role"],
        "freeze_status": design["freeze_status"]["timing"],
        "n_candidates": int(len(table)),
        "status_counts": {str(k): int(v) for k, v in sorted(counts.items())},
        "any_go_status": False,
        "all_require_scope_reopening": bool(table["reopening_required"].all()),
        "no_go_candidates": sorted(
            table.loc[table["status"].eq("NO_GO"), "candidate"]
        ),
        "deferred_candidates": sorted(
            table.loc[~table["status"].eq("NO_GO"), "candidate"]
        ),
        "scope": design["scope"],
        "integrity_pins_verified": {
            label: pins[label] for label in sorted(pins)
        },
        "registered_variable_count_unchanged": True,
        "reporting_guards": design["reporting_guards"],
    }


def render_markdown(design: dict, diagnostics: dict, table: pd.DataFrame) -> str:
    lines: list[str] = []
    add = lines.append

    add("# Optional public-data gate decisions")
    add("")
    add(f"**Design id:** `{design['design_id']}`  ")
    add(f"**Design SHA-256:** `{diagnostics['design_sha256']}`  ")
    add(f"**Frozen (UTC):** {design['frozen_utc']}  ")
    add("**Verification status:** `NEEDS-VERIFY` until Mher runs the G4 commands.")
    add("")
    add(
        "This is a **governance decision table**, not an empirical phase. "
        "Nothing here was downloaded, registered, or analysed. The accepted "
        "no-third-layer plan is preserved: no candidate below is admitted, and "
        "no candidate can be admitted by this document."
    )
    add("")
    add(
        f"All {diagnostics['n_candidates']} candidates carry a non-GO status and "
        "all require an explicit written scope reopening by Mher, recorded in "
        "`DECISION_LOG.md` **before** any acquisition."
    )
    add("")

    add("## Decision summary")
    add("")
    add("| Candidate | Status | Single permitted use | Reopening required |")
    add("|---|---|---|---|")
    for record in table.to_dict("records"):
        add(
            f"| {record['display_name']} | `{record['status']}` | "
            f"{record['permitted_use']} | "
            f"{'yes' if record['reopening_required'] else 'no'} |"
        )
    add("")

    add("## Rights, coverage, lag, and estimand relevance")
    add("")
    add("| Candidate | Required rights | Coverage | Reporting lag | Estimand relevance |")
    add("|---|---|---|---|---|")
    for record in table.to_dict("records"):
        add(
            f"| {record['display_name']} | {record['required_rights']} | "
            f"{record['coverage']} | {record['reporting_lag']} | "
            f"{record['estimand_relevance']} |"
        )
    add("")

    add("## What each candidate may never be used for")
    add("")
    for record in table.to_dict("records"):
        add(f"- **{record['display_name']}** — {record['prohibited_use']}")
    add("")

    add("## Kill criteria")
    add("")
    for record in table.to_dict("records"):
        add(f"### {record['display_name']}")
        add("")
        for criterion in record["kill_criteria"].split(" | "):
            add(f"- {criterion}")
        if record["blocking_reason"] != NOT_APPLICABLE:
            add("")
            add(f"**Blocking reason:** {record['blocking_reason']}")
        add("")

    add("## Governance boundary")
    add("")
    add(
        f"- Authority to reopen scope rests with "
        f"{design['scope']['reopening_authority']}."
    )
    add(
        "- This phase performed no network access and added no registered "
        "variable. The source registry is hash-pinned at "
        f"{design['integrity_pins']['sources_registry']['registered_variable_count']} "
        "variables and verified byte-identical on every run."
    )
    add(
        "- The G4-verified horizon-frontier, network-support, and route-burden "
        "manifests are hash-pinned and unchanged."
    )
    add(
        "- The locked specification, the 2026-02-28 operational-onset cutoff, "
        "and the formal proposal are untouched."
    )
    add("")
    return "\n".join(lines) + "\n"


def main() -> int:
    design, design_sha256 = load_design()
    pins = verify_integrity_pins(design)
    table = build_table(design)
    diagnostics = build_diagnostics(design, design_sha256, table, pins)
    markdown = render_markdown(design, diagnostics, table)

    path = output_path(design, "decision_table_csv")
    path.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(path, index=False)
    print(f"wrote {path}")

    path = output_path(design, "diagnostics_json")
    path.write_text(
        json.dumps(diagnostics, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"wrote {path}")

    doc_path = output_path(design, "documentation_markdown")
    doc_path.parent.mkdir(parents=True, exist_ok=True)
    doc_path.write_text(markdown, encoding="utf-8")
    print(f"wrote {doc_path}")

    print("\nOptional public-data gate decisions:")
    print(
        table.loc[:, ["candidate", "status", "kill_criteria_count"]].to_string(
            index=False
        )
    )
    print(f"\n  status counts: {diagnostics['status_counts']}")
    print(f"  any GO status: {diagnostics['any_go_status']}")
    print(
        f"  all require scope reopening: "
        f"{diagnostics['all_require_scope_reopening']}"
    )
    print("\nGovernance guard:")
    print(" - No dataset was downloaded, registered, or analysed.")
    print(" - The source registry is hash-verified unchanged at 53 variables.")
    print(" - The accepted no-third-layer plan is preserved.")
    print(" - Admission requires Mher's explicit written scope reopening.")
    print(" - This is NEEDS-VERIFY until Mher records the G4 output.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
