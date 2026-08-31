"""Write or verify the task-7 selective network-support frontier manifest.

Verification recomputes every output from the design file and the hash-pinned
registered upstream artifacts, then compares byte-for-byte with what is on disk.
It also re-asserts that the upstream capacity and radius-comparison artifacts
still carry their pinned hashes, so this phase cannot become a silent rewrite of
the vessel branch.
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
from run_network_support_frontier import (  # noqa: E402
    DESIGN_PATH,
    build_audit_expectation,
    build_balanced_table,
    build_denominators,
    build_diagnostics,
    build_radius_sensitivity,
    load_design,
    load_verified_inputs,
    output_path,
    render_markdown,
    sha256_file,
)


MODULE_PATH = config.ROOT / "src/hormuz_throughput/network_support.py"
BUILDER_PATH = config.ROOT / "scripts/run_network_support_frontier.py"
FREEZER_PATH = Path(__file__)
EXPOSURE_PATH = config.ROOT / "src/hormuz_throughput/exposure.py"

OUTPUT_KEYS = (
    "denominators_csv",
    "radius_sensitivity_csv",
    "balanced_cohort_csv",
    "diagnostics_json",
    "audit_expectation_json",
    "documentation_markdown",
)


def _relative(path: Path) -> str:
    return path.relative_to(config.ROOT).as_posix()


def rebuild(design: dict, design_sha256: str) -> tuple:
    voyages, terminals, carriers = load_verified_inputs(design)
    denominators, full = build_denominators(design, voyages, terminals, carriers)
    sensitivity = build_radius_sensitivity(design, full)
    balanced = build_balanced_table(design, denominators)
    audit = build_audit_expectation(design, sensitivity)
    diagnostics = build_diagnostics(
        design, design_sha256, denominators, sensitivity, balanced, carriers
    )
    markdown = render_markdown(
        design, diagnostics, denominators, sensitivity, balanced, audit
    )
    return denominators, sensitivity, balanced, audit, diagnostics, markdown


def validate_written_outputs(design: dict, design_sha256: str) -> None:
    denominators, sensitivity, balanced, audit, diagnostics, markdown = rebuild(
        design, design_sha256
    )
    for key, expected in (
        ("denominators_csv", denominators),
        ("radius_sensitivity_csv", sensitivity),
        ("balanced_cohort_csv", balanced),
    ):
        written = pd.read_csv(output_path(design, key))
        pd.testing.assert_frame_equal(
            written,
            expected,
            check_dtype=False,
            check_exact=False,
            rtol=0.0,
            atol=1e-12,
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
        raise ValueError("written support documentation differs from live inputs")


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
            raise FileNotFoundError(f"network-support output missing: {key}")

    _, _, _, audit, diagnostics, _ = rebuild(design, design_sha256)
    input_paths = {
        "design": DESIGN_PATH,
        "module": MODULE_PATH,
        "builder": BUILDER_PATH,
        "freezer": FREEZER_PATH,
        "exposure_module": EXPOSURE_PATH,
    }
    for label, spec in design["upstream_registered_artifacts"].items():
        input_paths[f"upstream_{label}"] = config.ROOT / spec["path"]

    return {
        "manifest_schema": 1,
        "design_id": design["design_id"],
        "analysis_role": design["analysis_role"],
        "status": "generated_support_denominator_artifact",
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
        "terminal_radius_km_grid": list(design["terminal_radius_km_grid"]),
        "primary_terminal_radius_km": int(design["primary_terminal_radius_km"]),
        "census": diagnostics["census"],
        "primary_cell": diagnostics["primary_cell"],
        "balanced_primary_cell": diagnostics["balanced_primary_cell"],
        "selectivity_direction_consistent_across_radii": diagnostics[
            "selectivity_direction_consistent_across_radii"
        ],
        "audit_expectation_fully_reproduced": bool(audit["fully_reproduced"]),
        "ais_dark_throughput_inferred": False,
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
        print(f"NETWORK SUPPORT MANIFEST FAILED: missing {path}")
        return 1
    written = json.loads(path.read_text(encoding="utf-8"))
    live = build_manifest()
    if written != live:
        print("NETWORK SUPPORT MANIFEST FAILED: live bytes differ")
        return 1
    cell = live["primary_cell"]
    print(
        "NETWORK SUPPORT MANIFEST PASSED: "
        f"{len(live['output_sha256'])} outputs match; at "
        f"{live['primary_terminal_radius_km']}km all-resolved "
        f"{cell['all_resolved_pre']}->{cell['all_resolved_post']} and "
        f"Hormuz-crossing {cell['hormuz_crossing_pre']}->"
        f"{cell['hormuz_crossing_post']}; audit expectation reproduced="
        f"{live['audit_expectation_fully_reproduced']}; "
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
