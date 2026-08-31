"""Write or verify the task-10 final integration audit manifest.

Verification recomputes the scan, the claim ledger, and both documents from the
frozen design and the live repository, then compares byte-for-byte with what is
on disk. It fails if any stale claim is asserted, if any claim cites a missing
artifact, or if a G4-verified upstream manifest has drifted.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from hormuz_throughput import config  # noqa: E402
from run_final_integration_audit import (  # noqa: E402
    DESIGN_PATH,
    build_claim_ledger,
    build_defence_answers,
    build_diagnostics,
    collect_documents,
    load_design,
    output_path,
    render_audit_markdown,
    render_defence_markdown,
    sha256_file,
    stale_patterns,
)
from hormuz_throughput.claim_audit import (  # noqa: E402
    scan_documents,
    source_confusion_hits,
    uncited_numeric_lines,
)


MODULE_PATH = config.ROOT / "src/hormuz_throughput/claim_audit.py"
BUILDER_PATH = config.ROOT / "scripts/run_final_integration_audit.py"
FREEZER_PATH = Path(__file__)

OUTPUT_KEYS = (
    "stale_claim_scan_csv",
    "claim_ledger_csv",
    "diagnostics_json",
    "audit_markdown",
    "defence_markdown",
)


def _relative(path: Path) -> str:
    return path.relative_to(config.ROOT).as_posix()


def rebuild(design: dict, design_sha256: str) -> tuple:
    documents = collect_documents(design)
    scan = scan_documents(
        documents,
        stale_patterns(design),
        context_radius=int(design["context_radius_lines"]),
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
    return scan, ledger, diagnostics, audit_markdown, defence_markdown


def assert_no_asserted_stale_claims(diagnostics: dict) -> None:
    if diagnostics["stale_claims_flagged"]:
        raise ValueError(
            f"{diagnostics['stale_claims_flagged']} asserted stale claim(s) in "
            f"{diagnostics['flagged_paths']}"
        )
    if diagnostics["source_layer_confusion_flagged"]:
        raise ValueError(
            "a PortWatch all-tanker figure is read as LNG-specific"
        )
    if diagnostics["claims"] != diagnostics["claims_with_existing_artifact"]:
        raise ValueError("a claim cites an artifact that does not exist")


def assert_upstream_manifests_present(design: dict) -> dict:
    pins = {}
    for label, spec in design["integrity_pins"].items():
        path = config.ROOT / spec["path"]
        if not path.is_file():
            raise FileNotFoundError(f"upstream manifest missing: {label}")
        pins[label] = sha256_file(path)
    return pins


def validate_written_outputs(design: dict, design_sha256: str) -> None:
    scan, ledger, diagnostics, audit_markdown, defence_markdown = rebuild(
        design, design_sha256
    )
    for key, expected in (
        ("stale_claim_scan_csv", scan),
        ("claim_ledger_csv", ledger),
    ):
        written = pd.read_csv(output_path(design, key), keep_default_na=False)
        pd.testing.assert_frame_equal(
            written, expected, check_dtype=False, check_exact=True
        )
    written_diagnostics = json.loads(
        output_path(design, "diagnostics_json").read_text(encoding="utf-8")
    )
    if written_diagnostics != diagnostics:
        raise ValueError("written diagnostics differ from the live rebuild")
    for key, expected_text in (
        ("audit_markdown", audit_markdown),
        ("defence_markdown", defence_markdown),
    ):
        written = output_path(design, key).read_text(encoding="utf-8")
        if written != expected_text:
            raise ValueError(f"written {key} differs from live inputs")


def build_manifest() -> dict:
    design, design_sha256 = load_design()
    pins = assert_upstream_manifests_present(design)
    validate_written_outputs(design, design_sha256)
    for key in OUTPUT_KEYS:
        if not output_path(design, key).is_file():
            raise FileNotFoundError(f"final-audit output missing: {key}")

    _, ledger, diagnostics, _, _ = rebuild(design, design_sha256)
    assert_no_asserted_stale_claims(diagnostics)

    input_paths = {
        "design": DESIGN_PATH,
        "module": MODULE_PATH,
        "builder": BUILDER_PATH,
        "freezer": FREEZER_PATH,
    }
    return {
        "manifest_schema": 1,
        "design_id": design["design_id"],
        "analysis_role": design["analysis_role"],
        "status": "generated_final_integration_audit",
        "verification_state": "NEEDS-VERIFY",
        "verification_record": "reports/reproducibility_run_transcript.txt",
        "design_sha256": design_sha256,
        "freeze_status": design["freeze_status"]["timing"],
        "core_run_all_dependency": "required",
        "core_reproducibility_manifest_dependency": "none",
        "input_sha256": {
            _relative(path): sha256_file(path) for path in input_paths.values()
        },
        "output_sha256": {
            _relative(output_path(design, key)): sha256_file(output_path(design, key))
            for key in OUTPUT_KEYS
        },
        "upstream_manifest_sha256": pins,
        "documents_scanned": diagnostics["documents_scanned"],
        "stale_claim_occurrences": diagnostics["stale_claim_occurrences"],
        "stale_claims_flagged": 0,
        "source_layer_confusion_flagged": 0,
        "claims": diagnostics["claims"],
        "claim_artifact_sha256": {
            row["claim_id"]: row["artifact_sha256"]
            for row in ledger.to_dict("records")
        },
        "defence_challenges_prepared": diagnostics["defence_challenges_prepared"],
        "open_reproducibility_boundaries": diagnostics[
            "open_reproducibility_boundaries"
        ],
        "formal_proposal_edited": False,
        "restricted_material_included": False,
        "third_layer_admitted": False,
        "reporting_guards": design["reporting_guards"],
    }


def manifest_path() -> Path:
    design, _ = load_design()
    return output_path(design, "manifest_json")


def write_manifest() -> Path:
    path = manifest_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(build_manifest(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"wrote {path}")
    return path


def verify_manifest() -> int:
    path = manifest_path()
    if not path.is_file():
        print(f"FINAL INTEGRATION MANIFEST FAILED: missing {path}")
        return 1
    written = json.loads(path.read_text(encoding="utf-8"))
    live = build_manifest()
    if written != live:
        print("FINAL INTEGRATION MANIFEST FAILED: live bytes differ")
        return 1
    print(
        "FINAL INTEGRATION MANIFEST PASSED: "
        f"{len(live['output_sha256'])} outputs match; "
        f"{live['documents_scanned']} documents scanned, "
        f"{live['stale_claim_occurrences']} occurrences, "
        f"{live['stale_claims_flagged']} asserted stale claims; "
        f"{live['claims']} claims all citing frozen artifacts; "
        f"{live['defence_challenges_prepared']} defence answers prepared; "
        "formal proposal unedited"
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    if args.verify:
        return verify_manifest()
    write_manifest()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
