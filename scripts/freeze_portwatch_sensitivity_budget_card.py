"""Write or verify the separate phase-5 sensitivity-budget card manifest."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from lngfreight import config  # noqa: E402
from freeze_portwatch_sensitivity_complete import (  # noqa: E402
    build_complete_manifest,
)
from make_portwatch_sensitivity_budget_card import (  # noqa: E402
    DESIGN_PATH,
    build_card_payload,
    build_cell_table,
    load_design,
    load_verified_inputs,
    output_path,
    render_markdown,
    sha256_file,
)


BUILDER_PATH = config.ROOT / "scripts/make_portwatch_sensitivity_budget_card.py"
FREEZER_PATH = Path(__file__)
FIGURE_STYLE_PATH = config.ROOT / "scripts/figure_style.py"
PHASE4_COMPLETE_PATH = (
    config.path("data_processed") / "portwatch_sensitivity_complete_manifest.json"
)


def _relative(path: Path) -> str:
    return path.relative_to(config.ROOT).as_posix()


def validate_written_outputs(design: dict, design_sha256: str) -> None:
    """Recompute every tabular/text value from the immutable parent."""
    summary, admission = load_verified_inputs(design)
    expected_cells = build_cell_table(summary, design)
    expected_payload = build_card_payload(
        expected_cells, admission, design, design_sha256
    )

    written_cells = pd.read_csv(output_path(design, "card_csv"))
    pd.testing.assert_frame_equal(
        written_cells,
        expected_cells,
        check_dtype=False,
        check_exact=False,
        rtol=0.0,
        atol=1e-12,
    )
    written_payload = json.loads(
        output_path(design, "card_json").read_text(encoding="utf-8")
    )
    if written_payload != expected_payload:
        raise ValueError("written sensitivity-card JSON differs from live inputs")
    written_markdown = output_path(design, "card_markdown").read_text(
        encoding="utf-8"
    )
    if written_markdown != render_markdown(expected_payload):
        raise ValueError("written sensitivity-card prose differs from live inputs")


def build_manifest() -> dict:
    design, design_sha256 = load_design()
    phase4_expected = design["parent_artifacts"]["complete_branch_manifest"][
        "sha256"
    ]
    if sha256_file(PHASE4_COMPLETE_PATH) != phase4_expected:
        raise ValueError("G4-verified phase-4 complete manifest drifted")
    written_phase4 = json.loads(PHASE4_COMPLETE_PATH.read_text(encoding="utf-8"))
    if written_phase4 != build_complete_manifest():
        raise ValueError("phase-4 complete manifest differs from its live build")
    if len(written_phase4["artifact_sha256"]) != 13:
        raise ValueError("phase-4 parent must retain exactly 13 artifacts")

    validate_written_outputs(design, design_sha256)
    output_keys = ("card_csv", "card_json", "card_markdown", "card_png", "card_pdf")
    for key in output_keys:
        if not output_path(design, key).is_file():
            raise FileNotFoundError(f"sensitivity-card output missing: {key}")

    input_paths = {
        "design": DESIGN_PATH,
        "builder": BUILDER_PATH,
        "freezer": FREEZER_PATH,
        "figure_style": FIGURE_STYLE_PATH,
    }
    for label, spec in design["parent_artifacts"].items():
        input_paths[f"parent_{label}"] = config.ROOT / spec["path"]
    return {
        "manifest_schema": 1,
        "card_id": design["card_id"],
        "analysis_role": design["analysis_role"],
        "status": "assistant_generated_reporting_artifact",
        "human_verification_record": "docs/DECISION_LOG.md",
        "design_sha256": design_sha256,
        "phase4_complete_manifest_sha256": phase4_expected,
        "phase4_artifact_count": 13,
        "phase4_manifest_mutated": False,
        "core_run_all_dependency": "none",
        "core_reproducibility_manifest_dependency": "none",
        "input_sha256": {
            _relative(path): sha256_file(path) for path in input_paths.values()
        },
        "output_sha256": {
            _relative(output_path(design, key)): sha256_file(output_path(design, key))
            for key in output_keys
        },
        "axes_are_additive": False,
        "combined_budget_total": None,
        "secondary_normalization_role": (
            "descriptive_scale_context_only_not_budget_axis"
        ),
        "vintage_averaging": "prohibited_and_not_performed",
        "all_preperiod_admitted_model_range": "not_estimated",
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
        print(f"SENSITIVITY-BUDGET CARD MANIFEST FAILED: missing {path}")
        return 1
    written = json.loads(path.read_text(encoding="utf-8"))
    live = build_manifest()
    if written != live:
        print("SENSITIVITY-BUDGET CARD MANIFEST FAILED: live bytes differ")
        return 1
    print(
        "SENSITIVITY-BUDGET CARD MANIFEST PASSED: "
        f"{len(live['output_sha256'])} outputs match; phase-4 parent unchanged"
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
