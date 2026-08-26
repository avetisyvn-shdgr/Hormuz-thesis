"""Write or verify the separate PortWatch sensitivity-branch manifest."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from lngfreight import config  # noqa: E402
from freeze_reproducibility import (  # noqa: E402
    SENSITIVITY_HASH_FILE,
    SENSITIVITY_RAW_INPUTS,
    sensitivity_raw_hashes,
)


CONFIG_INPUTS = (
    "config/settings.yaml",
    "config/sources.yaml",
    "config/model_admission_protocol.yaml",
    "config/model_vintage_matrix.yaml",
    SENSITIVITY_HASH_FILE,
)
IMPLEMENTATION_INPUTS = (
    "scripts/verify_sensitivity_inputs.py",
    "scripts/run_portwatch_vintage_sensitivity.py",
    "scripts/run_revision_and_basin_exploration.py",
    "scripts/build_model_admission_protocol.py",
    "scripts/run_rebound_relapse_profile.py",
    "scripts/run_model_vintage_matrix.py",
    "scripts/freeze_portwatch_sensitivity.py",
    "scripts/run_portwatch_sensitivity.py",
    "src/lngfreight/registry.py",
    "src/lngfreight/vintage_matrix.py",
    "src/lngfreight/baselines.py",
    "src/lngfreight/bsts.py",
    "src/lngfreight/tsfm.py",
    "requirements-benchmark.lock.txt",
)
PREPARED_ARTIFACTS = (
    "data/processed/portwatch_sensitivity_input_manifest.json",
    "data/processed/portwatch_vintage_sensitivity.csv",
    "data/processed/model_admission_protocol.csv",
    "data/processed/model_admission_known_results.csv",
    "data/processed/portwatch_regime_phase_profile.csv",
    "data/processed/portwatch_regime_contrasts.csv",
)
MATRIX_ARTIFACTS = (
    "data/processed/model_vintage_matrix_core_daily.csv",
    "data/processed/model_vintage_matrix_core_summary.csv",
    "data/processed/model_vintage_matrix_chronos_daily.csv",
    "data/processed/model_vintage_matrix_chronos_summary.csv",
    "data/processed/model_vintage_matrix_daily.csv",
    "data/processed/model_vintage_matrix_summary.csv",
    "data/processed/model_vintage_matrix_manifest.json",
)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _hashes(paths: tuple[str, ...], *, label: str) -> dict[str, str]:
    out = {}
    for relative in paths:
        path = config.ROOT / relative
        if not path.is_file():
            raise FileNotFoundError(f"{label} missing: {relative}")
        out[relative] = sha256_file(path)
    return out


def build_manifest(*, mode: str) -> dict:
    if mode not in {"prepared", "complete"}:
        raise ValueError("sensitivity manifest mode must be prepared or complete")
    sensitivity = sensitivity_raw_hashes(config.ROOT)
    if set(sensitivity) != set(SENSITIVITY_RAW_INPUTS):
        raise ValueError("sensitivity input scope differs from its declaration")
    matrix_present = {
        relative: (config.ROOT / relative).is_file()
        for relative in MATRIX_ARTIFACTS
    }
    if mode == "prepared" and any(matrix_present.values()):
        raise ValueError("prepared manifest refuses partial or pre-existing matrix outputs")
    if mode == "complete" and not all(matrix_present.values()):
        missing = [path for path, present in matrix_present.items() if not present]
        raise FileNotFoundError(f"complete sensitivity matrix missing: {missing}")
    artifact_paths = PREPARED_ARTIFACTS + (
        MATRIX_ARTIFACTS if mode == "complete" else ()
    )
    return {
        "manifest_schema": 1,
        "analysis_scope": "optional_portwatch_sensitivity_branch",
        "mode": mode,
        "core_run_all_dependency": "none",
        "core_reproducibility_manifest_dependency": "none",
        "sensitivity_raw_sha256": sensitivity,
        "config_sha256": _hashes(CONFIG_INPUTS, label="sensitivity config"),
        "implementation_sha256": _hashes(
            IMPLEMENTATION_INPUTS, label="sensitivity implementation"
        ),
        "artifact_sha256": _hashes(
            artifact_paths, label="sensitivity artifact"
        ),
        "matrix_artifact_presence": matrix_present,
        "vintage_averaging": "prohibited",
        "replication_archive_status": "pending_deposit_gitignored_august_source_bytes",
        "interpretation": (
            "Case-local measurement-vintage and selected-model sensitivity; "
            "not an ATT, variance decomposition, pooled estimate, or general AIS claim."
        ),
    }


def write_manifest(*, mode: str) -> Path:
    manifest = build_manifest(mode=mode)
    path = config.path("portwatch_sensitivity_manifest_json")
    path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"wrote {path} ({len(manifest['artifact_sha256'])} branch artifacts)")
    return path


def verify_manifest(*, mode: str) -> int:
    path = config.path("portwatch_sensitivity_manifest_json")
    if not path.is_file():
        print(f"SENSITIVITY MANIFEST FAILED: missing {path}")
        return 1
    expected = json.loads(path.read_text(encoding="utf-8"))
    actual = build_manifest(mode=mode)
    if expected != actual:
        print("SENSITIVITY MANIFEST FAILED: current branch differs from frozen manifest")
        return 1
    print(
        "SENSITIVITY MANIFEST PASSED: "
        f"{len(actual['artifact_sha256'])} artifacts match ({mode})"
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("prepared", "complete"), required=True)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    if args.verify:
        return verify_manifest(mode=args.mode)
    write_manifest(mode=args.mode)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
