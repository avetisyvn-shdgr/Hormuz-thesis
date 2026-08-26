"""Write or verify the post-matrix PortWatch sensitivity manifest.

The prepared manifest is a pre-run checkpoint input and must remain byte-stable.
This post-run wrapper therefore writes the complete manifest to a distinct path
instead of overwriting that historical evidence.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from lngfreight import config  # noqa: E402
from freeze_portwatch_sensitivity import build_manifest, sha256_file  # noqa: E402


PREPARED_MANIFEST = "data/processed/portwatch_sensitivity_manifest.json"
COMPLETE_MANIFEST = "data/processed/portwatch_sensitivity_complete_manifest.json"
PRE_RUN_CHECKPOINT = "data/processed/model_admission_pre_run_checkpoint.json"


def build_complete_manifest() -> dict:
    checkpoint_path = config.ROOT / PRE_RUN_CHECKPOINT
    checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
    frozen_prepared_sha = checkpoint["checkpoint_input_sha256"][PREPARED_MANIFEST]
    current_prepared_sha = sha256_file(config.ROOT / PREPARED_MANIFEST)
    if current_prepared_sha != frozen_prepared_sha:
        raise ValueError(
            "prepared sensitivity manifest drifted from the pre-run checkpoint"
        )

    manifest = build_manifest(mode="complete")
    manifest.update({
        "lifecycle_role": "post_matrix_complete_manifest",
        "prepared_manifest_path": PREPARED_MANIFEST,
        "prepared_manifest_sha256": frozen_prepared_sha,
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
        f"{len(actual['artifact_sha256'])} artifacts match"
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
