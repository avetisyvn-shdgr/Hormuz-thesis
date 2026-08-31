"""Write or verify the task-9 public-data gate decision manifest.

Verification recomputes the decision table from the frozen design and compares
it byte-for-byte with what is on disk. It also re-asserts the integrity pins:
the source registry and the three G4-verified upstream manifests must be
unchanged, which is what makes "this phase acquired nothing" a checked fact
rather than a claim.
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
from run_public_data_gate_decisions import (  # noqa: E402
    DESIGN_PATH,
    build_diagnostics,
    build_table,
    load_design,
    output_path,
    render_markdown,
    sha256_file,
    verify_integrity_pins,
)


BUILDER_PATH = config.ROOT / "scripts/run_public_data_gate_decisions.py"
FREEZER_PATH = Path(__file__)

OUTPUT_KEYS = (
    "decision_table_csv",
    "diagnostics_json",
    "documentation_markdown",
)


def _relative(path: Path) -> str:
    return path.relative_to(config.ROOT).as_posix()


def rebuild(design: dict, design_sha256: str) -> tuple:
    pins = verify_integrity_pins(design)
    table = build_table(design)
    diagnostics = build_diagnostics(design, design_sha256, table, pins)
    markdown = render_markdown(design, diagnostics, table)
    return table, diagnostics, markdown


def validate_written_outputs(design: dict, design_sha256: str) -> None:
    table, diagnostics, markdown = rebuild(design, design_sha256)
    written_table = pd.read_csv(
        output_path(design, "decision_table_csv"), keep_default_na=False
    )
    pd.testing.assert_frame_equal(
        written_table, table, check_dtype=False, check_exact=True
    )
    written_diagnostics = json.loads(
        output_path(design, "diagnostics_json").read_text(encoding="utf-8")
    )
    if written_diagnostics != diagnostics:
        raise ValueError("written gate diagnostics differ from the live rebuild")
    written_markdown = output_path(design, "documentation_markdown").read_text(
        encoding="utf-8"
    )
    if written_markdown != markdown:
        raise ValueError("written gate documentation differs from live inputs")


def build_manifest() -> dict:
    design, design_sha256 = load_design()
    validate_written_outputs(design, design_sha256)
    for key in OUTPUT_KEYS:
        if not output_path(design, key).is_file():
            raise FileNotFoundError(f"gate-decision output missing: {key}")

    table, diagnostics, _ = rebuild(design, design_sha256)
    input_paths = {
        "design": DESIGN_PATH,
        "builder": BUILDER_PATH,
        "freezer": FREEZER_PATH,
    }
    for label, spec in design["integrity_pins"].items():
        input_paths[f"pin_{label}"] = config.ROOT / spec["path"]

    return {
        "manifest_schema": 1,
        "design_id": design["design_id"],
        "analysis_role": design["analysis_role"],
        "status": "governance_decision_artifact_no_acquisition",
        "verification_state": "NEEDS-VERIFY",
        "verification_record": "reports/reproducibility_run_transcript.txt",
        "design_sha256": design_sha256,
        "freeze_status": design["freeze_status"]["timing"],
        "core_run_all_dependency": "required_for_final_integration",
        "core_reproducibility_manifest_dependency": "none",
        "input_sha256": {
            _relative(path): sha256_file(path) for path in input_paths.values()
        },
        "output_sha256": {
            _relative(output_path(design, key)): sha256_file(output_path(design, key))
            for key in OUTPUT_KEYS
        },
        "n_candidates": diagnostics["n_candidates"],
        "status_counts": diagnostics["status_counts"],
        "any_go_status": False,
        "all_require_scope_reopening": diagnostics["all_require_scope_reopening"],
        "no_go_candidates": diagnostics["no_go_candidates"],
        "deferred_candidates": diagnostics["deferred_candidates"],
        "datasets_downloaded": 0,
        "registry_variables_added": 0,
        "registered_variable_count": int(
            design["integrity_pins"]["sources_registry"][
                "registered_variable_count"
            ]
        ),
        "third_layer_admitted": False,
        "no_third_layer_plan_preserved": True,
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
        print(f"PUBLIC DATA GATE MANIFEST FAILED: missing {path}")
        return 1
    written = json.loads(path.read_text(encoding="utf-8"))
    live = build_manifest()
    if written != live:
        print("PUBLIC DATA GATE MANIFEST FAILED: live bytes differ")
        return 1
    print(
        "PUBLIC DATA GATE MANIFEST PASSED: "
        f"{len(live['output_sha256'])} outputs match; "
        f"{live['n_candidates']} candidates, no GO status, "
        f"{live['datasets_downloaded']} datasets downloaded, "
        f"registry unchanged at {live['registered_variable_count']} variables; "
        "no-third-layer plan preserved"
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
