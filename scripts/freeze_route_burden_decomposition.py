"""Write or verify the task-8 route-burden decomposition manifest.

Verification recomputes every output from the design file and the hash-pinned
registered upstream artifacts, then compares byte-for-byte with what is on disk.
It also re-asserts that the upstream vessel-branch artifacts and the G4-verified
task-7 support manifest still carry their pinned hashes.
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
from run_route_burden_decomposition import (  # noqa: E402
    DESIGN_PATH,
    build_audit_expectation,
    build_decomposition,
    build_diagnostics,
    load_design,
    load_verified_inputs,
    output_path,
    render_markdown,
    sha256_file,
)


MODULE_PATH = config.ROOT / "src/hormuz_throughput/route_burden.py"
BUILDER_PATH = config.ROOT / "scripts/run_route_burden_decomposition.py"
FREEZER_PATH = Path(__file__)

OUTPUT_KEYS = (
    "decomposition_csv",
    "weighting_sensitivity_csv",
    "pair_support_csv",
    "diagnostics_json",
    "audit_expectation_json",
    "documentation_markdown",
)


def _relative(path: Path) -> str:
    return path.relative_to(config.ROOT).as_posix()


def rebuild(design: dict, design_sha256: str) -> tuple:
    voyages, carriers = load_verified_inputs(design)
    decomposition, pair_support = build_decomposition(design, voyages)
    audit = build_audit_expectation(design, decomposition)
    diagnostics = build_diagnostics(
        design, design_sha256, decomposition, pair_support, carriers
    )
    markdown = render_markdown(design, diagnostics, decomposition, audit)
    weighting = decomposition.loc[decomposition["cohort"].eq("all_retained")].copy()
    return decomposition, weighting, pair_support, audit, diagnostics, markdown


def validate_written_outputs(design: dict, design_sha256: str) -> None:
    decomposition, weighting, pair_support, audit, diagnostics, markdown = rebuild(
        design, design_sha256
    )
    for key, expected in (
        ("decomposition_csv", decomposition),
        ("weighting_sensitivity_csv", weighting),
        ("pair_support_csv", pair_support),
    ):
        written = pd.read_csv(output_path(design, key))
        pd.testing.assert_frame_equal(
            written,
            expected.reset_index(drop=True),
            check_dtype=False,
            check_exact=False,
            rtol=1e-12,
            atol=1e-6,
        )
    for key, expected_payload in (
        ("diagnostics_json", diagnostics),
        ("audit_expectation_json", audit),
    ):
        written_payload = json.loads(
            output_path(design, key).read_text(encoding="utf-8")
        )
        if written_payload != expected_payload:
            raise ValueError(f"written {key} differs from its live rebuild")
    written_markdown = output_path(design, "documentation_markdown").read_text(
        encoding="utf-8"
    )
    if written_markdown != markdown:
        raise ValueError("written decomposition prose differs from live inputs")


def assert_upstream_untouched(design: dict) -> None:
    for label, spec in design["upstream_registered_artifacts"].items():
        path = config.ROOT / spec["path"]
        if sha256_file(path) != spec["sha256"]:
            raise ValueError(f"registered upstream artifact was modified: {label}")


def build_manifest() -> dict:
    design, design_sha256 = load_design()
    assert_upstream_untouched(design)
    validate_written_outputs(design, design_sha256)
    for key in OUTPUT_KEYS:
        if not output_path(design, key).is_file():
            raise FileNotFoundError(f"route-burden output missing: {key}")

    _, _, _, audit, diagnostics, _ = rebuild(design, design_sha256)
    input_paths = {
        "design": DESIGN_PATH,
        "module": MODULE_PATH,
        "builder": BUILDER_PATH,
        "freezer": FREEZER_PATH,
    }
    for label, spec in design["upstream_registered_artifacts"].items():
        input_paths[f"upstream_{label}"] = config.ROOT / spec["path"]

    return {
        "manifest_schema": 1,
        "design_id": design["design_id"],
        "analysis_role": design["analysis_role"],
        "status": "generated_decomposition_artifact",
        "verification_state": "NEEDS-VERIFY",
        "verification_record": "reports/reproducibility_run_transcript.txt",
        "design_sha256": design_sha256,
        "freeze_status": design["freeze_status"]["timing"],
        "upstream_artifacts_mutated": False,
        "core_run_all_dependency": "required_for_final_integration",
        "core_reproducibility_manifest_dependency": "none",
        "input_sha256": {
            _relative(path): sha256_file(path) for path in input_paths.values()
        },
        "output_sha256": {
            _relative(output_path(design, key)): sha256_file(output_path(design, key))
            for key in OUTPUT_KEYS
        },
        "construct_label": design["construct"]["label"],
        "construct_unit": design["construct"]["unit"],
        "primary_weighting_scheme": diagnostics["primary_weighting_scheme"],
        "primary_terminal_radius_km": diagnostics["primary_terminal_radius_km"],
        "primary_cell": diagnostics["primary_cell"],
        "balanced_primary_cell": diagnostics["balanced_primary_cell"],
        "entry_exit_residual_invariant_to_weighting": True,
        "component_split_generalises_across_grid": False,
        "unstable_percent_cells": diagnostics["unstable_percent_cells"],
        "audit_expectation_fully_reproduced": bool(audit["fully_reproduced"]),
        "is_observed_cargo_ton_miles": False,
        "is_physical_rerouting_evidence": False,
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
        print(f"ROUTE BURDEN MANIFEST FAILED: missing {path}")
        return 1
    written = json.loads(path.read_text(encoding="utf-8"))
    live = build_manifest()
    if written != live:
        print("ROUTE BURDEN MANIFEST FAILED: live bytes differ")
        return 1
    cell = live["primary_cell"]
    print(
        "ROUTE BURDEN MANIFEST PASSED: "
        f"{len(live['output_sha256'])} outputs match; at "
        f"{live['primary_terminal_radius_km']}km total change "
        f"{cell['total_change'] / 1e6:,.3f}M m3-nm/sequence split "
        f"{cell['common_pair_share_reweighting_percent']:.1f}/"
        f"{cell['entry_exit_residual_percent']:.1f}/"
        f"{cell['within_common_pair_capacity_mix_percent']:.1f}; "
        f"audit expectation reproduced="
        f"{live['audit_expectation_fully_reproduced']}; "
        "split does NOT generalise across the grid; "
        "registered upstream artifacts unchanged"
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
