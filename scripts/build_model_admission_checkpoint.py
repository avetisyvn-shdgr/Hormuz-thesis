"""Create the one-time pre-matrix admission/design checkpoint.

The checkpoint records the exact dirty-tree context and fails if any matrix
output already exists. A later path-scoped Git commit supplies the immutable
anchor; this file alone is only a local byte-level record.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pandas as pd
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from hormuz_throughput import config  # noqa: E402
from freeze_portwatch_sensitivity import MATRIX_ARTIFACTS  # noqa: E402


CHECKPOINT_INPUTS = (
    "config/settings.yaml",
    "config/sources.yaml",
    "config/model_admission_protocol.yaml",
    "config/model_vintage_matrix.yaml",
    "config/provenance_source_payload_exceptions.json",
    "data/raw/SHA256SUMS.sensitivity",
    "data/processed/portwatch_sensitivity_input_manifest.json",
    "data/processed/portwatch_sensitivity_manifest.json",
    "data/processed/model_admission_protocol.csv",
    "data/processed/model_admission_known_results.csv",
    "data/processed/portwatch_vintage_sensitivity.csv",
    "data/processed/portwatch_regime_phase_profile.csv",
    "data/processed/portwatch_regime_contrasts.csv",
    "data/processed/counterfactual_post_treatment.csv",
    "data/processed/tsfm_counterfactual_daily.csv",
    "data/processed/bsts_counterfactual_daily.csv",
    "data/processed/bsts_counterfactual_summary.csv",
    "data/processed/synthetic_control_summary.csv",
    "data/processed/synthetic_control_scales.csv",
    "data/processed/tsfm_admission_test.csv",
    "scripts/build_model_admission_protocol.py",
    "scripts/audit_provenance.py",
    "scripts/run_model_vintage_matrix.py",
    "scripts/run_portwatch_sensitivity.py",
    "scripts/run_portwatch_vintage_sensitivity.py",
    "scripts/run_rebound_relapse_profile.py",
    "scripts/verify_sensitivity_inputs.py",
    "scripts/freeze_portwatch_sensitivity.py",
    "scripts/build_model_admission_checkpoint.py",
    "src/hormuz_throughput/registry.py",
    "src/hormuz_throughput/vintage_matrix.py",
    "src/hormuz_throughput/baselines.py",
    "src/hormuz_throughput/bsts.py",
    "src/hormuz_throughput/tsfm.py",
    "tests/test_model_admission_protocol.py",
    "tests/test_model_admission_checkpoint.py",
    "tests/test_rebound_relapse_profile.py",
    "tests/test_registry_artifacts.py",
    "tests/test_reproducibility.py",
    "tests/test_sensitivity_input_gate.py",
    "requirements/locks/benchmark-py311-macos-arm64.txt",
)
RAW_INPUTS = (
    "data/raw/portwatch/Daily_Chokepoints_Data.csv",
    "data/raw/portwatch/vintages/Daily_Chokepoints_Data__vintage_2026-08-09.csv",
)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _hashes(paths: tuple[str, ...]) -> dict[str, str]:
    out = {}
    for relative in paths:
        path = config.ROOT / relative
        if not path.is_file():
            raise FileNotFoundError(f"checkpoint input missing: {relative}")
        out[relative] = sha256_file(path)
    return out


def _git(*args: str, binary: bool = False) -> str | bytes:
    completed = subprocess.run(
        ["git", *args],
        cwd=config.ROOT,
        check=True,
        capture_output=True,
        text=not binary,
    )
    return completed.stdout


def build_checkpoint() -> dict:
    present = [
        relative for relative in MATRIX_ARTIFACTS if (config.ROOT / relative).exists()
    ]
    if present:
        raise ValueError(
            "pre-run checkpoint refuses existing matrix outputs: " + ", ".join(present)
        )
    status_bytes = _git("status", "--porcelain=v1", "-z", binary=True)
    assert isinstance(status_bytes, bytes)
    status_entries = [
        entry.decode("utf-8", errors="surrogateescape")
        for entry in status_bytes.split(b"\0")
        if entry
    ]
    known = pd.read_csv(config.path("model_admission_known_results_csv"))
    protocol = yaml.safe_load(
        (config.CONFIG_DIR / "model_admission_protocol.yaml").read_text()
    )
    return {
        "checkpoint_schema": 1,
        "checkpoint_role": "pre_persisted_matrix_and_pre_august_chronos_run",
        "immutability_status": "local_byte_level_record_pending_path_scoped_git_anchor",
        "human_verification_status": "pending_g4",
        "git_head": str(_git("rev-parse", "HEAD")).strip(),
        "git_branch": str(_git("branch", "--show-current")).strip(),
        "dirty_status_capture": {
            "timing": "immediately_before_checkpoint_output_files_were_written",
            "entry_count": len(status_entries),
            "porcelain_v1_z_sha256": hashlib.sha256(status_bytes).hexdigest(),
            "entries": status_entries,
        },
        "protocol_id": protocol["protocol_id"],
        "protocol_sha256": sha256_file(
            config.CONFIG_DIR / "model_admission_protocol.yaml"
        ),
        "matrix_design_id": yaml.safe_load(
            (config.CONFIG_DIR / "model_vintage_matrix.yaml").read_text()
        )["design_id"],
        "matrix_design_sha256": sha256_file(
            config.CONFIG_DIR / "model_vintage_matrix.yaml"
        ),
        "checkpoint_input_sha256": _hashes(CHECKPOINT_INPUTS),
        "raw_vintage_sha256": _hashes(RAW_INPUTS),
        "known_artifact_result_rows": int(len(known)),
        "known_result_ids": sorted(known["result_id"].astype(str).tolist()),
        "matrix_output_presence": {
            relative: False for relative in MATRIX_ARTIFACTS
        },
        "next_gate": (
            "Anchor this record and the corrected protocol/design in a path-scoped "
            "Git commit; then obtain Mher's phase 1-3 verification before running "
            "the August Chronos cell."
        ),
    }


def main() -> None:
    checkpoint = build_checkpoint()
    path = config.path("model_admission_pre_run_checkpoint_json")
    sidecar = config.path("model_admission_pre_run_checkpoint_sha256")
    path.write_text(
        json.dumps(checkpoint, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    digest = sha256_file(path)
    relative = path.relative_to(config.ROOT).as_posix()
    sidecar.write_text(f"{digest}  {relative}\n", encoding="utf-8")
    print(f"wrote local pre-run checkpoint {path}")
    print(f"checkpoint sha256: {digest}")
    print("immutability status: pending path-scoped Git anchor")


if __name__ == "__main__":
    main()
