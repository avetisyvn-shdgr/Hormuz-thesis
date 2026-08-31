"""Task 10: final evidence-to-claim audit and defence integration.

Three jobs. First, scan thesis-facing prose for retired claims -- classifying
each hit by whether it is asserted or merely quoted, prohibited, or corrected,
because in this repository the retired phrases legitimately appear in dozens of
guard and correction contexts. Second, bind every headline empirical claim to a
frozen artifact and its stated limitation. Third, write defence answers for the
five challenges most likely to be pressed.

It edits no manuscript, admits no data, and touches the formal proposal not at
all.

Run from the repo root:
    python scripts/run_final_integration_audit.py
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pandas as pd
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from hormuz_throughput import config  # noqa: E402
from hormuz_throughput.claim_audit import (  # noqa: E402
    StalePattern,
    flagged,
    scan_documents,
    source_confusion_hits,
    uncited_numeric_lines,
)


DESIGN_PATH = config.CONFIG_DIR / "final_integration_audit.yaml"

LEDGER_COLUMNS = [
    "claim_id",
    "statement",
    "value",
    "artifact",
    "artifact_exists",
    "artifact_sha256",
    "value_verified",
    "source_layer",
    "limitation",
]


def _single_row(frame: pd.DataFrame, mask: pd.Series, claim_id: str) -> pd.Series:
    selected = frame.loc[mask]
    if len(selected) != 1:
        raise AssertionError(
            f"claim {claim_id} expected one evidence row, found {len(selected)}"
        )
    return selected.iloc[0]


def _close(actual: float, expected: float, claim_id: str, atol: float = 1e-9) -> None:
    if abs(float(actual) - expected) > atol:
        raise AssertionError(
            f"claim {claim_id} value drift: {actual} != {expected}"
        )


def verify_claim_value(item: dict) -> bool:
    """Recompute the configured claim value from its cited artifact."""
    claim_id = item["claim_id"]
    path = config.ROOT / item["artifact"]

    if claim_id == "throughput_shortfall":
        frame = pd.read_csv(path)
        row = _single_row(
            frame,
            frame["vintage"].eq("pinned_primary")
            & frame["model"].eq("ar_lag1_7"),
            claim_id,
        )
        _close(row["mean_daily_common_point_shortfall"], 52.83843081600861, claim_id)
        _close(row["cumulative_common_point_shortfall"], 6868.996006081119, claim_id)
        if int(row["n_scored_days"]) != 130:
            raise AssertionError(f"claim {claim_id} scoring window is not 130 days")
        expected = "52.838 lost transits/day (6868.996 cumulative)"

    elif claim_id == "vintage_sensitivity":
        frame = pd.read_csv(path)
        row = _single_row(frame, frame["model"].eq("ar_lag1_7"), claim_id)
        _close(row["pinned_minus_august_per_day"], 9.024924586269634, claim_id)
        expected = "9.025 transits/day for AR(1,7)"

    elif claim_id == "rebound_relapse":
        frame = pd.read_csv(path)
        august = frame.loc[frame["vintage"].eq("vintage_20260809")]
        rebound = _single_row(
            august, august["phase"].eq("post_mou_interval_20d"), claim_id
        )
        relapse = _single_row(
            august, august["phase"].eq("post_renewed_attacks_interval"), claim_id
        )
        _close(rebound["mean_daily_transits"], 10.45, claim_id)
        _close(relapse["mean_daily_transits"], 1.56, claim_id)
        if not bool(relapse["complete_window"]) or relapse["phase_end"] != "2026-08-01":
            raise AssertionError(f"claim {claim_id} relapse window is incomplete")
        expected = (
            "10.45/day after the MoU, then 1.56/day after renewed attacks "
            "through 2026-08-01"
        )

    elif claim_id == "inference_frontier":
        frame = pd.read_csv(path)
        primary = frame.loc[
            frame["origin_rule"].eq("forward_anchored_direct")
            & frame["horizon_days"].eq(130)
        ]
        if set(primary["level"].round(2)) != {0.80, 0.90, 0.95}:
            raise AssertionError(f"claim {claim_id} confidence levels drifted")
        if not primary["n_reference_blocks"].eq(8).all():
            raise AssertionError(f"claim {claim_id} reference-block count drifted")
        if not primary["rank_p_value_greater"].sub(1 / 9).abs().le(1e-12).all():
            raise AssertionError(f"claim {claim_id} rank p-value drifted")
        finite = primary.set_index("level")["finite_interval_supported"].to_dict()
        if finite != {0.8: True, 0.9: False, 0.95: False}:
            raise AssertionError(f"claim {claim_id} finite-interval support drifted")
        expected = (
            "8 disjoint reference blocks; rank p 0.111111 at the 1/9 floor; "
            "80% radius finite, 90% and 95% unbounded"
        )

    elif claim_id == "network_support":
        frame = pd.read_csv(path)
        radius = frame.loc[frame["terminal_radius_km"].eq(30)]
        overall = _single_row(radius, radius["cohort"].eq("all_resolved"), claim_id)
        hormuz = _single_row(radius, radius["cohort"].eq("hormuz_crossing"), claim_id)
        if tuple(overall[["pre_sequences", "post_sequences"]]) != (971, 746):
            raise AssertionError(f"claim {claim_id} overall support drifted")
        if tuple(hormuz[["pre_sequences", "post_sequences"]]) != (145, 2):
            raise AssertionError(f"claim {claim_id} Hormuz support drifted")
        expected = "all resolved 971 to 746; Hormuz-crossing 145 to 2"

    elif claim_id == "route_burden":
        frame = pd.read_csv(path)
        row = _single_row(
            frame,
            frame["cohort"].eq("all_retained")
            & frame["terminal_radius_km"].eq(30)
            & frame["weighting_scheme"].eq("symmetric_marshall_edgeworth"),
            claim_id,
        )
        _close(row["total_change"], 67585181.55385447, claim_id, atol=1e-3)
        _close(row["common_pair_share_reweighting_percent"], 54.9, claim_id, atol=0.1)
        _close(row["entry_exit_residual_percent"], 43.8, claim_id, atol=0.1)
        _close(row["within_common_pair_capacity_mix_percent"], 1.3, claim_id, atol=0.1)
        expected = (
            "+67.585 million m3-nm per retained sequence; "
            "54.9 / 43.8 / 1.3 component split"
        )

    elif claim_id == "lng_specific_outbound":
        frame = pd.read_csv(path)
        frame["voy_load_date"] = pd.to_datetime(frame["voy_load_date"])
        after = frame.loc[frame["voy_load_date"].ge("2026-06-16")]
        nonzero_dates = set(
            after.loc[after["voy_intake_index"].ne(0), "voy_load_date"]
            .dt.strftime("%Y-%m-%d")
        )
        if nonzero_dates != {"2026-06-28", "2026-07-05"}:
            raise AssertionError(f"claim {claim_id} nonzero dates drifted")
        if frame["voy_load_date"].max().strftime("%Y-%m-%d") != "2026-07-15":
            raise AssertionError(f"claim {claim_id} endpoint drifted")
        expected = (
            "nonzero on 2026-06-28 and 2026-07-05, then zero through the "
            "available endpoint 2026-07-15"
        )

    elif claim_id == "public_data_gates":
        frame = pd.read_csv(path)
        if len(frame) != 5 or frame["status"].eq("GO").any():
            raise AssertionError(f"claim {claim_id} candidate count or status drifted")
        jodi = _single_row(frame, frame["candidate"].eq("jodi_gas"), claim_id)
        if jodi["status"] != "NO_GO":
            raise AssertionError(f"claim {claim_id} JODI status drifted")
        if not frame.loc[~frame["candidate"].eq("jodi_gas"), "status"].str.startswith(
            "DEFER_"
        ).all():
            raise AssertionError(f"claim {claim_id} deferred statuses drifted")
        expected = "5 candidates; JODI NO_GO; remainder deferred; no GO status permitted"

    else:
        raise AssertionError(f"claim {claim_id} has no executable value check")

    if item["value"] != expected:
        raise AssertionError(
            f"claim {claim_id} text does not match verified evidence: {item['value']!r}"
        )
    return True


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_design() -> tuple[dict, str]:
    raw = DESIGN_PATH.read_bytes()
    return yaml.safe_load(raw), hashlib.sha256(raw).hexdigest()


def output_path(design: dict, key: str) -> Path:
    return config.ROOT / design["outputs"][key]


def stale_patterns(design: dict) -> list[StalePattern]:
    return [
        StalePattern(
            category=item["category"],
            pattern=item["pattern"],
            regex=bool(item.get("regex", False)),
        )
        for item in design["stale_claim_patterns"]
    ]


def collect_documents(design: dict) -> dict[str, str]:
    """Thesis-facing prose, excluding the registers that record retired claims."""
    excluded = {
        (config.ROOT / path).resolve() for path in design["excluded_paths"]
    }
    documents: dict[str, str] = {}
    for pattern in design["scanned_globs"]:
        for path in sorted(config.ROOT.glob(pattern)):
            if path.resolve() in excluded or not path.is_file():
                continue
            relative = path.relative_to(config.ROOT).as_posix()
            documents[relative] = path.read_text(encoding="utf-8")
    if not documents:
        raise ValueError("no documents matched the scanned globs")
    return documents


def build_claim_ledger(design: dict) -> pd.DataFrame:
    rows = []
    for item in design["claim_ledger"]:
        path = config.ROOT / item["artifact"]
        exists = path.is_file()
        rows.append({
            "claim_id": item["claim_id"],
            "statement": item["statement"],
            "value": item["value"],
            "artifact": item["artifact"],
            "artifact_exists": bool(exists),
            "artifact_sha256": sha256_file(path) if exists else "",
            "value_verified": verify_claim_value(item) if exists else False,
            "source_layer": item["source_layer"],
            "limitation": item["limitation"],
        })
    ledger = pd.DataFrame(rows, columns=LEDGER_COLUMNS)
    guard_ledger(ledger)
    return ledger.sort_values("claim_id", kind="stable").reset_index(drop=True)


def guard_ledger(ledger: pd.DataFrame) -> None:
    """Every claim must cite an existing artifact and state a limitation."""
    if ledger.empty:
        raise AssertionError("claim ledger is empty")
    missing = ledger.loc[~ledger["artifact_exists"], "claim_id"].tolist()
    if missing:
        raise AssertionError(f"claims cite a missing artifact: {missing}")
    for column in ("statement", "value", "limitation", "source_layer"):
        if ledger[column].astype(str).str.strip().eq("").any():
            raise AssertionError(f"a claim has a blank {column}")
    if ledger["claim_id"].duplicated().any():
        raise AssertionError("duplicate claim_id in the ledger")
    if not ledger["value_verified"].astype(bool).all():
        failed = ledger.loc[~ledger["value_verified"].astype(bool), "claim_id"].tolist()
        raise AssertionError(f"claims failed executable value checks: {failed}")

    layers = set(ledger["source_layer"])
    if "portwatch_all_tanker" in layers and "wto_lng_specific" not in layers:
        raise AssertionError(
            "the LNG-specific WTO layer must be represented separately from "
            "the PortWatch all-tanker layer"
        )


def build_defence_answers(design: dict, ledger: pd.DataFrame) -> list[dict]:
    """Prepared answers, each bound to the artifact that supports it."""
    indexed = ledger.set_index("claim_id")
    answers = {
        "arx_admissibility": {
            "short_answer": (
                "Because it uses information the counterfactual is not allowed "
                "to have, not because it fits worse."
            ),
            "detail": (
                "The conditional route/energy ARX consumes observed "
                "post-cutoff covariates. A no-disruption counterfactual cannot "
                "condition on realised post-disruption Panama transits and "
                "energy prices, which are themselves plausibly affected by the "
                "event. Its 62.858/day result is published in the admission "
                "table with a machine-readable exclusion reason, so the choice "
                "is auditable rather than hidden. Admitting it would widen the "
                "pinned range to 13.233/day and defeat the headline, which is "
                "precisely why the rule was fixed on information grounds "
                "before the range was read."
            ),
            "concession": (
                "The admission rule was frozen ex post and unblinded. It is "
                "documented as such and never described as preregistered."
            ),
            "artifacts": [
                "data/processed/model_admission_protocol.csv",
                "data/processed/model_admission_known_results.csv",
            ],
        },
        "mutable_vintage": {
            "short_answer": (
                "No, and the size of that exposure is measured rather than "
                "asserted."
            ),
            "detail": (
                "The same AR(1,7) specification on the August vintage gives "
                "43.814/day against 52.838/day on the pinned July vintage, a "
                f"same-model difference of "
                f"{indexed.loc['vintage_sensitivity', 'value']}. That is larger "
                "than the 5.175/day spread across the four selected models on "
                "the pinned vintage. The honest statement is that vintage "
                "choice moves this number more than model choice does, so the "
                "reporting basis is pinned and disclosed, and the two axes are "
                "reported separately."
            ),
            "concession": (
                "Vintages are different measurement states and are never "
                "averaged or ranked for truth. The absolute magnitude is "
                "vintage-sensitive; only the pinned basis is reported as "
                "primary."
            ),
            "artifacts": [
                "data/processed/portwatch_sensitivity_budget_card.csv",
                "data/processed/model_vintage_matrix_summary.csv",
            ],
        },
        "missing_network_support": {
            "short_answer": (
                "It shows the panel stopped observing those sequences. That is "
                "not the same proposition as shipping stopping."
            ),
            "detail": (
                "A sequence leaves the modeled panel when AIS coverage lapses, "
                "when neither endpoint attributes to a terminal within the "
                "radius, or when no route resolves. Each failure mode is "
                "plausibly more likely during a disruption, so the bias runs in "
                "an unknown direction. The result is reported as modeled "
                "resolved terminal-sequence support: 145 to 2 Hormuz-crossing "
                "against 971 to 746 overall at 30 km, with the overall "
                "denominator always attached. The direction survives the 10, "
                "20 and 30 km grid and the both-period carrier cohort."
            ),
            "concession": (
                "This layer cannot establish physical throughput and no "
                "AIS-dark throughput is inferred from it. Independent "
                "corroboration would need scene-level SAR, which is deferred "
                "post-submission."
            ),
            "artifacts": [
                "data/processed/network_support_radius_sensitivity.csv",
                "data/processed/network_support_denominators.csv",
            ],
        },
        "finite_sample_p_floor": {
            "short_answer": (
                "0.111 is the smallest value the design can produce. It is a "
                "floor, not a failure to reject."
            ),
            "detail": (
                "The pre-period supports 8 disjoint 130-day reference blocks, "
                "so the smallest attainable rank p-value is 1/(8+1) = 0.111. "
                "The observed statistic sits exactly at that floor: it exceeds "
                "every pre-treatment reference block, under all three "
                "origin rules and all four resolutions in the frozen grid. "
                "Reading 0.111 as weak evidence confuses the value with the "
                "resolution of the instrument. For the same reason the 90% and "
                "95% conformal bands are reported as unbounded rather than "
                "clipped, since their order statistic (9) exceeds the 8 "
                "available blocks."
            ),
            "concession": (
                "No 5% claim is available at the reporting resolution, and "
                "none is made. A finer 30-day resolution does reach a 1/39 "
                "floor, but that is a partition property rather than evidence "
                "and the reporting resolution was fixed beforehand."
            ),
            "artifacts": [
                "data/processed/horizon_frontier_summary.csv",
                "data/processed/horizon_frontier_audit_expectation.json",
            ],
        },
        "construct_limitations": {
            "short_answer": "No. It is a composition statistic, not a behaviour one.",
            "detail": (
                "The quantity is modeled distance per nominal vessel-capacity "
                "m3 among retained inferred voyages. Nominal capacity is a "
                "carrier design property rather than measured cargo, and the "
                "distance is a shortest-sea-route estimate rather than an AIS "
                "track. No vessel-level distance change is measured anywhere. "
                "The +67.585 million m3-nm per retained sequence at 30 km "
                "decomposes almost entirely into terminal-pair share "
                "reweighting and pairs entering or leaving support; carrying "
                "larger vessels on an unchanged pair explains about 1.3%."
            ),
            "concession": (
                "The component split does not generalise: 10 km gives roughly "
                "22/80/-2 and the both-period carrier cohort gives 97/9/-6 at "
                "30 km, where the 10 km cell even changes sign. Only the "
                "compositional-rather-than-within-pair reading survives the "
                "whole grid."
            ),
            "artifacts": [
                "data/processed/route_burden_decomposition.csv",
                "data/processed/route_burden_diagnostics.json",
            ],
        },
    }

    prepared = []
    for item in design["defence_challenges"]:
        key = item["challenge_id"]
        if key not in answers:
            raise AssertionError(f"no prepared answer for challenge {key}")
        answer = answers[key]
        for artifact in answer["artifacts"]:
            if not (config.ROOT / artifact).is_file():
                raise AssertionError(
                    f"defence answer {key} cites a missing artifact: {artifact}"
                )
        prepared.append({
            "challenge_id": key,
            "question": item["question"],
            **answer,
        })
    return prepared


def verify_publication_assets(design: dict) -> dict:
    """Check figure pairs and optional manifests.

    Publication figures are emitted as PNG+PDF pairs. A short declared list of
    report-inline diagnostics is PNG-only by design; anything else missing a PDF
    is a real gap and is reported.
    """
    spec = design["publication_assets"]
    figure_dir = config.ROOT / spec["figure_dir"]
    png_only = set(spec["png_only_diagnostics"])
    pngs = sorted(path.stem for path in figure_dir.glob("*.png"))
    pdfs = {path.stem for path in figure_dir.glob("*.pdf")}
    undeclared = sorted(
        stem for stem in pngs if stem not in pdfs and stem not in png_only
    )

    missing_manifests = [
        path
        for path in spec["required_optional_manifests"]
        if not (config.ROOT / path).is_file()
    ]
    return {
        "figures_png": len(pngs),
        "figures_pdf": len(pdfs),
        "declared_png_only_diagnostics": sorted(png_only),
        "figures_missing_pdf_undeclared": undeclared,
        "figure_pairs_complete": not undeclared,
        "optional_manifests_present": not missing_manifests,
        "missing_optional_manifests": missing_manifests,
    }


def build_diagnostics(
    design: dict,
    design_sha256: str,
    scan: pd.DataFrame,
    ledger: pd.DataFrame,
    confusion: pd.DataFrame,
    uncited: dict,
    defence: list[dict],
) -> dict:
    assets = verify_publication_assets(design)
    if not assets["figure_pairs_complete"]:
        raise AssertionError(
            "publication figures missing a PDF counterpart: "
            f"{assets['figures_missing_pdf_undeclared']}"
        )
    if not assets["optional_manifests_present"]:
        raise AssertionError(
            f"missing optional manifests: {assets['missing_optional_manifests']}"
        )
    flagged_rows = flagged(scan)
    by_category = (
        scan.groupby(["category", "verdict"]).size().unstack(fill_value=0)
    )
    categories = {
        str(category): {
            "cleared": int(row.get("cleared", 0)),
            "flagged": int(row.get("flagged", 0)),
        }
        for category, row in by_category.iterrows()
    }
    confusion_flagged = confusion.loc[confusion["verdict"].eq("flagged")]
    return {
        "design_id": design["design_id"],
        "design_sha256": design_sha256,
        "analysis_role": design["analysis_role"],
        "freeze_status": design["freeze_status"]["timing"],
        "documents_scanned": int(scan["path"].nunique()) if not scan.empty else 0,
        "stale_claim_occurrences": int(len(scan)),
        "stale_claims_cleared": int((scan["verdict"] == "cleared").sum()),
        "stale_claims_flagged": int(len(flagged_rows)),
        "flagged_paths": sorted(set(flagged_rows["path"])),
        "by_category": categories,
        "excluded_paths": list(design["excluded_paths"]),
        "source_layer_confusion_flagged": int(len(confusion_flagged)),
        "uncited_numeric_lines": {
            path: len(rows) for path, rows in sorted(uncited.items())
        },
        "claims": int(len(ledger)),
        "claims_with_existing_artifact": int(ledger["artifact_exists"].sum()),
        "source_layers": sorted(set(ledger["source_layer"])),
        "defence_challenges_prepared": len(defence),
        "open_reproducibility_boundaries": {
            key: spec["status"]
            for key, spec in design["open_reproducibility_boundaries"].items()
        },
        "publication_assets": assets,
        "formal_proposal_edited": False,
        "restricted_material_included": False,
        "reporting_guards": design["reporting_guards"],
    }


def render_audit_markdown(
    design: dict,
    diagnostics: dict,
    scan: pd.DataFrame,
    ledger: pd.DataFrame,
) -> str:
    lines: list[str] = []
    add = lines.append

    add("# Final evidence-to-claim audit")
    add("")
    add(f"**Design id:** `{design['design_id']}`  ")
    add(f"**Design SHA-256:** `{diagnostics['design_sha256']}`  ")
    add(f"**Frozen (UTC):** {design['frozen_utc']}  ")
    add("**Verification status:** `NEEDS-VERIFY` until the complete pipeline is run.")
    add("")
    add(
        "This document binds every headline empirical claim to a frozen "
        "artifact and its stated limitation, and records the stale-claim scan "
        "over thesis-facing prose. It edits no manuscript and does not touch "
        "the formal proposal."
    )
    add("")

    add("## Claim-to-artifact ledger")
    add("")
    add("| Claim | Value | Frozen artifact | Layer | Limitation |")
    add("|---|---|---|---|---|")
    for record in ledger.to_dict("records"):
        add(
            f"| {record['statement']} | {record['value']} | "
            f"`{record['artifact']}` | `{record['source_layer']}` | "
            f"{record['limitation']} |"
        )
    add("")
    add(
        f"All {diagnostics['claims']} claims cite an artifact that exists on "
        "disk, and each artifact's SHA-256 is recorded in "
        "`final_claim_artifact_ledger.csv`."
    )
    add("")

    add("## Layer separation")
    add("")
    add(
        "PortWatch counts **all tankers** and carries no LNG class. The "
        "WTO/AXSMarine index is **LNG-specific** but aggregate. They are "
        "reported as separate layers and never merged into a single figure."
    )
    add("")
    add("| Layer | Claims | What it can support |")
    add("|---|---:|---|")
    for layer in sorted(set(ledger["source_layer"])):
        count = int((ledger["source_layer"] == layer).sum())
        meaning = {
            "portwatch_all_tanker": "All-tanker transit counts. Never an LNG-specific quantity.",
            "wto_lng_specific": "LNG-specific outbound activity. Never vessel or destination identification.",
            "modeled_vessel_branch": "Modeled sequence support and composition. Never observed cargo.",
            "governance": "Scope and admission decisions. No empirical content.",
        }.get(layer, "See the ledger.")
        add(f"| `{layer}` | {count} | {meaning} |")
    add("")
    add(
        f"The scan found {diagnostics['source_layer_confusion_flagged']} "
        "unhedged line(s) attributing an LNG-specific reading to a PortWatch "
        "figure."
    )
    add("")

    add("## Stale-claim scan")
    add("")
    add(
        f"Scanned {diagnostics['documents_scanned']} thesis-facing documents "
        f"for {len(design['stale_claim_patterns'])} retired phrases, finding "
        f"{diagnostics['stale_claim_occurrences']} occurrences."
    )
    add("")
    add(
        "Occurrences are classified by context. A retired phrase appearing "
        "inside a negation, a quotation, a prohibition list, or a correction "
        "notice is **cleared** -- those are the places such phrases are "
        "supposed to appear. Only an asserted occurrence is **flagged**."
    )
    add("")
    add("| Category | Cleared | Flagged |")
    add("|---|---:|---:|")
    for category, counts in sorted(diagnostics["by_category"].items()):
        add(f"| `{category}` | {counts['cleared']} | {counts['flagged']} |")
    add("")
    if diagnostics["stale_claims_flagged"]:
        add("### Flagged occurrences requiring correction")
        add("")
        add("| Path | Line | Pattern | Text |")
        add("|---|---:|---|---|")
        for record in flagged(scan).to_dict("records"):
            add(
                f"| `{record['path']}` | {record['line_number']} | "
                f"`{record['pattern']}` | {record['line']} |"
            )
        add("")
    else:
        add(
            "**No asserted stale claim was found.** Every occurrence sits in a "
            "negating, quoting, prohibiting, or correcting context."
        )
        add("")
    add("### Deliberately excluded from the assertion check")
    add("")
    add(
        "These documents record retired claims as their function, so scanning "
        "them for assertion yields only noise. The exclusion is explicit:"
    )
    add("")
    for path in design["excluded_paths"]:
        add(f"- `{path}`")
    add("")

    add("## Open reproducibility boundaries")
    add("")
    add(
        "These are reported rather than hidden. None blocks submission, and "
        "one requires explicit approval before it can be closed."
    )
    add("")
    add("| Boundary | Status | Description |")
    add("|---|---|---|")
    for key, spec in design["open_reproducibility_boundaries"].items():
        description = " ".join(spec["description"].split())
        add(f"| `{key}` | `{spec['status']}` | {description} |")
    add("")

    add("## Regeneration order")
    add("")
    add(
        "This scan reads the live repository and records line numbers in the "
        "scanned documents. Editing any scanned document shifts those numbers "
        "and correctly invalidates the frozen scan. **Regenerate this phase "
        "last**, after every other documentation edit, then re-freeze."
    )
    add("")

    add("## Governance boundaries preserved")
    add("")
    add(
        "- The **formal proposal is unedited**. Direct Prof. Li authorization "
        "is not on record, and Zhenyu Wang's 2026-07-23 written acceptance "
        "does not substitute for it."
    )
    add(
        "- **No restricted material** appears in any thesis-facing artifact. "
        "JODI is `NO_GO` on already-triggered criteria; the Fearnleys series "
        "remain dormant registry entries with no data."
    )
    add(
        "- **No third empirical layer** is admitted. The public-data gate table "
        "records criteria only and grants no admission."
    )
    add(
        "- The locked specification, the 2026-02-28 operational-onset cutoff, "
        "and the pinned July reporting vintage are unchanged."
    )
    add("")
    return "\n".join(lines) + "\n"


def render_defence_markdown(
    design: dict, diagnostics: dict, defence: list[dict]
) -> str:
    lines: list[str] = []
    add = lines.append

    add("# Defence preparation")
    add("")
    add(f"**Design SHA-256:** `{diagnostics['design_sha256']}`  ")
    add("**Verification status:** `NEEDS-VERIFY` until the complete pipeline is run.")
    add("")
    add(
        "Prepared answers to the five challenges most likely to be pressed. "
        "Each states the answer, the supporting detail, the concession that "
        "should be made rather than defended, and the frozen artifacts to cite. "
        "Conceding the real limitation is the strongest available position; "
        "every one of these limitations is already documented."
    )
    add("")

    for index, item in enumerate(defence, start=1):
        add(f"## {index}. {item['question']}")
        add("")
        add(f"**Short answer.** {item['short_answer']}")
        add("")
        add(item["detail"])
        add("")
        add(f"**Concede this.** {item['concession']}")
        add("")
        add("**Cite:**")
        for artifact in item["artifacts"]:
            add(f"- `{artifact}`")
        add("")

    add("## Standing boundaries under any question")
    add("")
    add(
        "- The estimand is a disruption-associated counterfactual shortfall. "
        "It is not an average treatment effect and prediction accuracy is "
        "never offered as evidence of a causal effect."
    )
    add(
        "- No claim of 5% significance is available or made at the reporting "
        "resolution."
    )
    add(
        "- PortWatch is all-tanker; the WTO index is LNG-specific. They are "
        "never merged."
    )
    add(
        "- A missing modeled edge is a missing observation, never proof that no "
        "ship sailed."
    )
    add(
        "- Modeled distance times nominal capacity is not observed cargo "
        "ton-miles and not evidence that any ship sailed farther."
    )
    add("")
    return "\n".join(lines) + "\n"


def main() -> int:
    design, design_sha256 = load_design()
    documents = collect_documents(design)
    patterns = stale_patterns(design)

    scan = scan_documents(
        documents, patterns, context_radius=int(design["context_radius_lines"])
    )
    ledger = build_claim_ledger(design)
    confusion = source_confusion_hits(documents)
    uncited = {
        path: uncited_numeric_lines(text)
        for path, text in documents.items()
        if uncited_numeric_lines(text)
    }
    defence = build_defence_answers(design, ledger)
    diagnostics = build_diagnostics(
        design, design_sha256, scan, ledger, confusion, uncited, defence
    )
    audit_markdown = render_audit_markdown(design, diagnostics, scan, ledger)
    defence_markdown = render_defence_markdown(design, diagnostics, defence)

    for key, frame in (
        ("stale_claim_scan_csv", scan),
        ("claim_ledger_csv", ledger),
    ):
        path = output_path(design, key)
        path.parent.mkdir(parents=True, exist_ok=True)
        frame.to_csv(path, index=False)
        print(f"wrote {path}")

    path = output_path(design, "diagnostics_json")
    path.write_text(
        json.dumps(diagnostics, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"wrote {path}")

    for key, text in (
        ("audit_markdown", audit_markdown),
        ("defence_markdown", defence_markdown),
    ):
        path = output_path(design, key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        print(f"wrote {path}")

    print("\nFinal evidence-to-claim audit:")
    print(
        f"  documents scanned: {diagnostics['documents_scanned']}; "
        f"occurrences: {diagnostics['stale_claim_occurrences']}"
    )
    print(
        f"  cleared: {diagnostics['stale_claims_cleared']}; "
        f"FLAGGED: {diagnostics['stale_claims_flagged']}"
    )
    if diagnostics["stale_claims_flagged"]:
        print("  flagged paths:")
        for path in diagnostics["flagged_paths"]:
            print(f"    - {path}")
    print(
        f"  layer-confusion flagged: "
        f"{diagnostics['source_layer_confusion_flagged']}"
    )
    print(
        f"  claims: {diagnostics['claims']} "
        f"(all citing an existing frozen artifact: "
        f"{diagnostics['claims'] == diagnostics['claims_with_existing_artifact']})"
    )
    print(f"  defence challenges prepared: {diagnostics['defence_challenges_prepared']}")
    assets = diagnostics["publication_assets"]
    print(
        f"  figures: {assets['figures_png']} png / {assets['figures_pdf']} pdf "
        f"(pairs complete: {assets['figure_pairs_complete']})"
    )
    print(
        f"  optional manifests present: {assets['optional_manifests_present']}"
    )
    print("\nOpen reproducibility boundaries:")
    for key, status in diagnostics["open_reproducibility_boundaries"].items():
        print(f"  - {key}: {status}")
    print("\nGovernance guard:")
    print(" - Formal proposal unedited; no Prof. Li authorization on record.")
    print(" - No restricted Fearnleys/JODI material included.")
    print(" - No third empirical layer admitted.")
    print(" - This is NEEDS-VERIFY until the complete pipeline transcript is retained.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
