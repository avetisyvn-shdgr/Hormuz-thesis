from __future__ import annotations

import json
import hashlib

import pytest

from lngfreight import config
from freeze_portwatch_sensitivity import build_manifest as build_branch_manifest
from freeze_portwatch_sensitivity import MATRIX_ARTIFACTS
from verify_sensitivity_inputs import (
    DERIVED_SENSITIVITY_CONSUMERS,
    PINNED_VARIABLE,
    SENSITIVITY_ENTRYPOINTS,
    SENSITIVITY_VARIABLE,
    build_sensitivity_manifest,
)


SENSITIVITY_RAW = (
    config.ROOT
    / "data/raw/portwatch/vintages/"
    "Daily_Chokepoints_Data__vintage_2026-08-09.csv"
)
pytestmark = pytest.mark.skipif(
    not SENSITIVITY_RAW.is_file(),
    reason="optional August PortWatch sensitivity bytes are not deposited",
)


def test_sensitivity_manifest_enforces_non_promotion_guards():
    manifest = build_sensitivity_manifest()
    assert manifest["analysis_scope"] == "sensitivity_only"
    assert manifest["variable"] == SENSITIVITY_VARIABLE
    assert manifest["pinned_primary_variable"] == PINNED_VARIABLE
    assert manifest["path"] != manifest["pinned_primary_path"]
    assert manifest["pinned_primary_window_end"] == "2026-07-07"
    assert manifest["sha256"] == (
        "0bc806a4c384723debff08053d6fcbb915a03ee9fdf7b23c73d76d9bcb885bcb"
    )
    assert manifest["date_max"] == "2026-08-02"
    assert manifest["local_fixity_status"] == "verified"
    assert manifest["registry_opt_in_enforced"] is True
    assert set(manifest["direct_registry_call_sites"]) == {
        "scripts/verify_sensitivity_inputs.py",
        "scripts/run_portwatch_vintage_sensitivity.py",
        "scripts/run_rebound_relapse_profile.py",
        "scripts/run_revision_and_basin_exploration.py",
        "src/lngfreight/vintage_matrix.py",
    }
    # A4 and B1 opt in through a hash-pinned config rather than by naming the
    # variable in code, so they are recorded separately -- they are declared and
    # runtime-enforced consumers, but not direct call sites.
    assert set(manifest["config_mediated_call_sites"]) == {
        "scripts/run_hormuz_detection.py",
        "scripts/run_hormuz_measurement_audit.py",
    }
    assert not (
        set(manifest["direct_registry_call_sites"])
        & set(manifest["config_mediated_call_sites"])
    )
    assert tuple(manifest["sensitivity_entrypoints"]) == SENSITIVITY_ENTRYPOINTS
    assert tuple(manifest["derived_artifact_consumers"]) == (
        DERIVED_SENSITIVITY_CONSUMERS
    )
    assert manifest["replication_archive_status"].startswith("pending_deposit")


def test_written_sensitivity_manifest_matches_live_gate():
    written = json.loads(
        config.path("portwatch_sensitivity_input_manifest_json").read_text()
    )
    live = build_sensitivity_manifest()
    assert written == live


def test_prepared_branch_manifest_is_separate_and_matrix_free():
    path = config.path("portwatch_sensitivity_manifest_json")
    written = json.loads(path.read_text())
    assert written["core_run_all_dependency"] == "none"
    assert written["core_reproducibility_manifest_dependency"] == "none"
    assert not any(written["matrix_artifact_presence"].values())
    assert "data/processed/portwatch_vintage_sensitivity.csv" in written[
        "artifact_sha256"
    ]

    matrix_present = any((config.ROOT / relative).is_file() for relative in MATRIX_ARTIFACTS)
    if not matrix_present:
        assert written == build_branch_manifest(mode="prepared")
        return

    checkpoint = json.loads(
        config.path("model_admission_pre_run_checkpoint_json").read_text()
    )
    expected = checkpoint["checkpoint_input_sha256"][
        "data/processed/portwatch_sensitivity_manifest.json"
    ]
    assert hashlib.sha256(path.read_bytes()).hexdigest() == expected
    with pytest.raises(ValueError, match="prepared manifest refuses"):
        build_branch_manifest(mode="prepared")
