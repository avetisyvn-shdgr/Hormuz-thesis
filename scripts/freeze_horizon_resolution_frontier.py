"""Write or verify the task-6 horizon/resolution frontier manifest.

Verification recomputes every frontier artifact from the design file and the
hash-pinned panel and compares it byte-for-byte with what is on disk. It also
re-asserts that the locked primary block artifacts are untouched, so this phase
cannot quietly become the reporting basis for the locked inference row.
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
from run_horizon_resolution_frontier import (  # noqa: E402
    DESIGN_PATH,
    build_audit_expectation,
    build_blocks,
    build_diagnostics,
    build_geometry,
    build_summary,
    load_design,
    load_verified_inputs,
    output_path,
    render_markdown,
    sha256_file,
)


MODULE_PATH = config.ROOT / "src/hormuz_throughput/horizon_frontier.py"
BUILDER_PATH = config.ROOT / "scripts/run_horizon_resolution_frontier.py"
FREEZER_PATH = Path(__file__)

OUTPUT_KEYS = (
    "geometry_csv",
    "blocks_csv",
    "summary_csv",
    "diagnostics_json",
    "audit_expectation_json",
    "documentation_markdown",
)


def _relative(path: Path) -> str:
    return path.relative_to(config.ROOT).as_posix()


def rebuild(design: dict, design_sha256: str) -> tuple:
    panel = load_verified_inputs(design)
    geometry = build_geometry(design, panel)
    blocks = build_blocks(design, panel, geometry)
    summary = build_summary(design, panel, blocks)
    audit = build_audit_expectation(design, summary)
    diagnostics = build_diagnostics(
        design, design_sha256, panel, geometry, blocks, summary
    )
    markdown = render_markdown(design, diagnostics, summary, audit)
    return geometry, blocks, summary, audit, diagnostics, markdown


def validate_written_outputs(design: dict, design_sha256: str) -> None:
    """Recompute every written value from the hash-pinned inputs."""
    geometry, blocks, summary, audit, diagnostics, markdown = rebuild(
        design, design_sha256
    )
    for key, expected in (
        ("geometry_csv", geometry),
        ("blocks_csv", blocks),
        ("summary_csv", summary),
    ):
        written = pd.read_csv(output_path(design, key))
        pd.testing.assert_frame_equal(
            written,
            expected,
            check_dtype=False,
            check_exact=False,
            rtol=1e-9,
            atol=1e-9,
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
        raise ValueError("written frontier documentation differs from live inputs")


def assert_locked_primary_untouched(design: dict) -> None:
    """The locked block artifacts must still carry their pinned hashes."""
    for label, spec in design["upstream_locked_artifacts"].items():
        if not spec["role"].startswith("locked_primary"):
            continue
        path = config.ROOT / spec["path"]
        if sha256_file(path) != spec["sha256"]:
            raise ValueError(
                f"locked primary inference artifact was modified: {label}"
            )


def build_manifest() -> dict:
    design, design_sha256 = load_design()
    assert_locked_primary_untouched(design)
    validate_written_outputs(design, design_sha256)
    for key in OUTPUT_KEYS:
        if not output_path(design, key).is_file():
            raise FileNotFoundError(f"frontier output missing: {key}")

    _, _, summary, audit, diagnostics, _ = rebuild(design, design_sha256)
    primary = diagnostics["primary_cell"]
    input_paths = {
        "design": DESIGN_PATH,
        "module": MODULE_PATH,
        "builder": BUILDER_PATH,
        "freezer": FREEZER_PATH,
    }
    for label, spec in design["upstream_locked_artifacts"].items():
        input_paths[f"upstream_{label}"] = config.ROOT / spec["path"]

    return {
        "manifest_schema": 1,
        "design_id": design["design_id"],
        "analysis_role": design["analysis_role"],
        "status": "generated_inference_design_artifact",
        "verification_state": "NEEDS-VERIFY",
        "verification_record": "reports/reproducibility_run_transcript.txt",
        "design_sha256": design_sha256,
        "freeze_status": design["freeze_status"]["timing"],
        "locked_primary_artifacts_mutated": False,
        "core_run_all_dependency": "required_for_final_integration",
        "core_reproducibility_manifest_dependency": "none",
        "input_sha256": {
            _relative(path): sha256_file(path) for path in input_paths.values()
        },
        "output_sha256": {
            _relative(output_path(design, key)): sha256_file(output_path(design, key))
            for key in OUTPUT_KEYS
        },
        "origin_rules": {
            rule: spec["role"] for rule, spec in design["origin_rules"].items()
        },
        "horizon_grid_days": list(design["horizon_grid_days"]),
        "primary_horizon_days": int(design["primary_horizon_days"]),
        "primary_cell": {
            "origin_rule": primary["origin_rule"],
            "horizon_days": primary["horizon_days"],
            "n_reference_blocks": primary["n_reference_blocks"],
            "packing_upper_bound": primary["packing_upper_bound"],
            "rank_p_value_greater": primary["rank_p_value_greater"],
            "rank_p_value_floor": primary["rank_p_value_floor"],
            "maximum_attainable_coverage": primary["maximum_attainable_coverage"],
            "finite_interval_levels": primary["finite_interval_levels"],
            "unbounded_interval_levels": primary["unbounded_interval_levels"],
        },
        "audit_expectation_fully_reproduced": bool(audit["fully_reproduced"]),
        "five_percent_significance_claimed": bool(
            summary["five_percent_significance_claimed"].any()
        ),
        "resolutions_with_sub_five_percent_floor": sorted({
            int(item["horizon_days"])
            for item in diagnostics["cells"]
            if item["five_percent_floor_attainable"]
        }),
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
        print(f"HORIZON FRONTIER MANIFEST FAILED: missing {path}")
        return 1
    written = json.loads(path.read_text(encoding="utf-8"))
    live = build_manifest()
    if written != live:
        print("HORIZON FRONTIER MANIFEST FAILED: live bytes differ")
        return 1
    print(
        "HORIZON FRONTIER MANIFEST PASSED: "
        f"{len(live['output_sha256'])} outputs match; "
        f"K={live['primary_cell']['n_reference_blocks']} at "
        f"{live['primary_horizon_days']}d; "
        f"audit expectation reproduced="
        f"{live['audit_expectation_fully_reproduced']}; "
        "locked primary block artifacts unchanged"
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
