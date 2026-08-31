"""Write or verify the post-matrix PortWatch sensitivity manifest.

The historical checkpoint is immutable. If its prepared-manifest bytes are no
longer present, the completion record discloses that gap and verifies the
checkpointed scientific design, protocol, and raw data vintages separately.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from hormuz_throughput import config  # noqa: E402
from freeze_portwatch_sensitivity import build_manifest, sha256_file  # noqa: E402


PREPARED_MANIFEST = "data/processed/portwatch_sensitivity_manifest.json"
SENSITIVITY_INPUT_MANIFEST = (
    "data/processed/portwatch_sensitivity_input_manifest.json"
)
COMPLETE_MANIFEST = "data/processed/portwatch_sensitivity_complete_manifest.json"
PRE_RUN_CHECKPOINT = "data/processed/model_admission_pre_run_checkpoint.json"
MATRIX_DESIGN = "config/model_vintage_matrix.yaml"
ADMISSION_PROTOCOL = "config/model_admission_protocol.yaml"


def _verify_checkpoint_anchor(
    *, path: str, expected_sha256: str, label: str
) -> dict[str, object]:
    actual_sha256 = sha256_file(config.ROOT / path)
    if actual_sha256 != expected_sha256:
        raise ValueError(f"checkpointed {label} drifted: {path}")
    return {
        "path": path,
        "expected_sha256": expected_sha256,
        "actual_sha256": actual_sha256,
        "matches": True,
    }


def _verify_scientific_anchors(checkpoint: dict) -> dict[str, object]:
    raw_vintages = {
        path: _verify_checkpoint_anchor(
            path=path,
            expected_sha256=expected_sha256,
            label="raw vintage",
        )
        for path, expected_sha256 in checkpoint["raw_vintage_sha256"].items()
    }
    return {
        "matrix_design": _verify_checkpoint_anchor(
            path=MATRIX_DESIGN,
            expected_sha256=checkpoint["matrix_design_sha256"],
            label="matrix design",
        ),
        "admission_protocol": _verify_checkpoint_anchor(
            path=ADMISSION_PROTOCOL,
            expected_sha256=checkpoint["protocol_sha256"],
            label="admission protocol",
        ),
        "raw_vintages": raw_vintages,
    }


def build_complete_manifest() -> dict:
    checkpoint_path = config.ROOT / PRE_RUN_CHECKPOINT
    checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
    frozen_prepared_sha = checkpoint["checkpoint_input_sha256"][PREPARED_MANIFEST]
    current_prepared_sha = sha256_file(config.ROOT / PREPARED_MANIFEST)
    prepared_manifest_matches = current_prepared_sha == frozen_prepared_sha
    checkpoint_manifest_verification = {}
    for path in (PREPARED_MANIFEST, SENSITIVITY_INPUT_MANIFEST):
        expected_sha256 = checkpoint["checkpoint_input_sha256"][path]
        actual_sha256 = sha256_file(config.ROOT / path)
        checkpoint_manifest_verification[path] = {
            "expected_sha256": expected_sha256,
            "actual_sha256": actual_sha256,
            "matches": actual_sha256 == expected_sha256,
        }
    mismatched_manifest_paths = [
        path
        for path, verification in checkpoint_manifest_verification.items()
        if not verification["matches"]
    ]
    scientific_anchors = _verify_scientific_anchors(checkpoint)

    if not mismatched_manifest_paths:
        pre_run_provenance_status = "verified_exact"
        provenance_gap = None
    else:
        pre_run_provenance_status = "historical_pre_run_manifest_bytes_unavailable"
        provenance_gap = {
            "scope": "checkpointed_manifest_bytes",
            "affected_paths": mismatched_manifest_paths,
            "description": (
                "The metadata-manifest bytes referenced by the immutable pre-run "
                "checkpoint are not present in the current repository state. The "
                "current files reflect later repository work."
            ),
            "scientific_anchors_verified": True,
            "effect": (
                "Byte-level pre-run provenance for this optional sensitivity branch "
                "cannot be claimed. The completed matrix remains independently "
                "reproducible from the checkpoint-matched design, protocol, and raw "
                "vintages."
            ),
        }

    manifest = build_manifest(mode="complete")
    manifest.update({
        "core_run_all_dependency": "required_for_final_integration",
        "lifecycle_role": "post_matrix_complete_manifest_after_repository_migration",
        "prepared_manifest_path": PREPARED_MANIFEST,
        "prepared_manifest_sha256": frozen_prepared_sha,
        "current_prepared_manifest_sha256": current_prepared_sha,
        "prepared_manifest_matches_checkpoint": prepared_manifest_matches,
        "prepared_manifest_provenance_status": (
            "verified_exact"
            if prepared_manifest_matches
            else "historical_pre_run_bytes_unavailable"
        ),
        "checkpoint_manifest_verification": checkpoint_manifest_verification,
        "pre_run_provenance_status": pre_run_provenance_status,
        "pre_run_freeze_claim_permitted": not mismatched_manifest_paths,
        "disclosed_provenance_gap": provenance_gap,
        "checkpoint_scientific_anchor_verification": scientific_anchors,
        "pre_run_checkpoint_path": PRE_RUN_CHECKPOINT,
        "pre_run_checkpoint_sha256": sha256_file(checkpoint_path),
        "completion_freezer_sha256": sha256_file(Path(__file__)),
    })
    return manifest


def manifest_path() -> Path:
    return config.ROOT / COMPLETE_MANIFEST


def write_complete_manifest() -> Path:
    path = manifest_path()
    path.write_text(
        json.dumps(build_complete_manifest(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"wrote {path}")
    return path


def verify_complete_manifest() -> int:
    path = manifest_path()
    if not path.is_file():
        print(f"COMPLETE SENSITIVITY MANIFEST FAILED: missing {path}")
        return 1
    expected = json.loads(path.read_text(encoding="utf-8"))
    actual = build_complete_manifest()
    if expected != actual:
        print("COMPLETE SENSITIVITY MANIFEST FAILED: live branch differs")
        return 1
    print(
        "COMPLETE SENSITIVITY MANIFEST PASSED: "
        f"{len(actual['artifact_sha256'])} artifacts match; "
        f"pre-run provenance={actual['pre_run_provenance_status']}"
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    if args.verify:
        return verify_complete_manifest()
    write_complete_manifest()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
