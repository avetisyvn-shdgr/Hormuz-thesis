from __future__ import annotations

import hashlib
import json

from lngfreight import config


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_pre_run_checkpoint_matches_current_bytes_and_has_no_matrix_outputs():
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
    for relative, expected in checkpoint["checkpoint_input_sha256"].items():
        assert _sha256(config.ROOT / relative) == expected
    for relative, expected in checkpoint["raw_vintage_sha256"].items():
        assert _sha256(config.ROOT / relative) == expected

    digest, relative = sidecar.read_text(encoding="utf-8").strip().split()
    assert relative == path.relative_to(config.ROOT).as_posix()
    assert digest == _sha256(path)
