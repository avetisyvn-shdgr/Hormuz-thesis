from __future__ import annotations

import hashlib
import json
import subprocess

from lngfreight import config


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


ANCHOR_COMMIT = "ca925a86a2098b07653f635505ca785100f29b54"


def test_pre_run_checkpoint_remains_self_consistent_and_git_anchored():
    path = config.path("model_admission_pre_run_checkpoint_json")
    sidecar = config.path("model_admission_pre_run_checkpoint_sha256")
    checkpoint = json.loads(path.read_text(encoding="utf-8"))

    assert checkpoint["checkpoint_role"] == (
        "pre_persisted_matrix_and_pre_august_chronos_run"
    )
    assert checkpoint["human_verification_status"] == "pending_g4"
    assert checkpoint["known_artifact_result_rows"] == 14
    assert len(checkpoint["known_result_ids"]) == 14
    assert not any(checkpoint["matrix_output_presence"].values())

    assert checkpoint["protocol_sha256"] == _sha256(
        config.ROOT / "config/model_admission_protocol.yaml"
    )
    assert checkpoint["matrix_design_sha256"] == _sha256(
        config.ROOT / "config/model_vintage_matrix.yaml"
    )
    assert all(
        len(expected) == 64
        for expected in checkpoint["checkpoint_input_sha256"].values()
    )
    for relative, expected in checkpoint["raw_vintage_sha256"].items():
        assert _sha256(config.ROOT / relative) == expected

    digest, relative = sidecar.read_text(encoding="utf-8").strip().split()
    assert relative == path.relative_to(config.ROOT).as_posix()
    assert digest == _sha256(path)

    anchored = subprocess.run(
        ["git", "show", f"{ANCHOR_COMMIT}:{relative}"],
        cwd=config.ROOT,
        check=True,
        capture_output=True,
    ).stdout
    assert hashlib.sha256(anchored).hexdigest() == digest
