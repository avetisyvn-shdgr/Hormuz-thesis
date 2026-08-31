from __future__ import annotations

import hashlib
import json

import numpy as np
import pandas as pd
import pytest

from hormuz_throughput import config
from hormuz_throughput.vintage_matrix import (
    load_design,
    pinned_self_checks,
    sha256_file,
    validate_complete_matrix,
)
from freeze_portwatch_sensitivity_complete import (
    COMPLETE_MANIFEST,
    build_complete_manifest,
)


DAILY_PATH = config.path("model_vintage_matrix_daily_csv")
SUMMARY_PATH = config.path("model_vintage_matrix_summary_csv")
MATRIX_MANIFEST_PATH = config.path("model_vintage_matrix_manifest_json")
SENSITIVITY_RAW = (
    config.ROOT
    / "data/raw/portwatch/vintages/"
    "Daily_Chokepoints_Data__vintage_2026-08-09.csv"
)
REQUIRED_OPTIONAL_ARTIFACTS = (
    DAILY_PATH,
    SUMMARY_PATH,
    MATRIX_MANIFEST_PATH,
    config.ROOT / COMPLETE_MANIFEST,
)
pytestmark = pytest.mark.skipif(
    not SENSITIVITY_RAW.is_file()
    or not all(path.is_file() for path in REQUIRED_OPTIONAL_ARTIFACTS),
    reason="optional completed PortWatch matrix branch is not deposited",
)


EXPECTED_COMMON = {
    ("pinned_primary", "seasonal_naive_7d"): 54.8,
    ("pinned_primary", "ar_lag1_7"): 52.838430816008604,
    ("pinned_primary", "chronos2"): 50.88375704838679,
    ("pinned_primary", "bsts_local_level_weekly"): 49.62516478850947,
    ("vintage_20260809", "seasonal_naive_7d"): 43.7,
    ("vintage_20260809", "ar_lag1_7"): 43.81350622973898,
    ("vintage_20260809", "chronos2"): 42.17672494741586,
    ("vintage_20260809", "bsts_local_level_weekly"): 40.16745715691507,
}
EXPECTED_OBSERVED_SUM = {"pinned_primary": 529.0, "vintage_20260809": 401.0}
EXPECTED_VECTOR_SHA256 = {
    "pinned_primary": "0994ce039c929c66cc065cb15ed9f7bb12ade4b2774517f0b17f9c85db077446",
    "vintage_20260809": "cbeded4dc1c9446c73e1991ba9dd8fd969f0030e94e551506138a1d70c552be5",
}


def _daily() -> pd.DataFrame:
    return pd.read_csv(DAILY_PATH, parse_dates=["date"])


def _summary() -> pd.DataFrame:
    return pd.read_csv(SUMMARY_PATH)


def test_matrix_has_exact_frozen_cells_dates_and_observed_support():
    daily = _daily()
    summary = _summary()
    expected_dates = pd.date_range("2026-02-28", "2026-07-07", freq="D")
    assert len(daily) == 1040
    assert len(summary) == 8
    assert not daily.duplicated(["vintage", "model", "date"]).any()
    assert not summary.duplicated(["vintage", "model"]).any()
    assert set(zip(summary["vintage"], summary["model"])) == set(EXPECTED_COMMON)

    for vintage, expected_sum in EXPECTED_OBSERVED_SUM.items():
        reference = daily.loc[
            daily["vintage"].eq(vintage)
            & daily["model"].eq("seasonal_naive_7d")
        ].sort_values("date")
        assert pd.DatetimeIndex(reference["date"]).equals(expected_dates)
        observed = reference["y_true"].to_numpy(dtype="float64")
        assert observed.sum() == expected_sum
        assert hashlib.sha256(observed.tobytes()).hexdigest() == (
            EXPECTED_VECTOR_SHA256[vintage]
        )
        for model in summary.loc[summary["vintage"].eq(vintage), "model"]:
            cell = daily.loc[
                daily["vintage"].eq(vintage) & daily["model"].eq(model)
            ].sort_values("date")
            assert pd.DatetimeIndex(cell["date"]).equals(expected_dates)
            np.testing.assert_array_equal(cell["y_true"].to_numpy(), observed)
            assert np.isfinite(cell[["y_true", "y_pred", "common_point_shortfall"]]).all().all()


def test_every_summary_is_recomputed_from_its_daily_rows():
    daily = _daily()
    summary = _summary().set_index(["vintage", "model"])
    for key, row in summary.iterrows():
        vintage, model = key
        cell = daily.loc[
            daily["vintage"].eq(vintage) & daily["model"].eq(model)
        ].sort_values("date")
        observed = cell["y_true"].sum()
        predicted = cell["y_pred"].sum()
        cumulative = (cell["y_pred"] - cell["y_true"]).sum()
        assert row["n_scored_days"] == 130
        assert row["train_start"] == "2022-01-01"
        assert row["train_end"] == "2026-02-27"
        assert row["scoring_start"] == "2026-02-28"
        assert row["scoring_end"] == "2026-07-07"
        assert row["observed_sum"] == pytest.approx(observed, abs=1e-10)
        assert row["counterfactual_point_sum"] == pytest.approx(predicted, abs=1e-10)
        assert row["cumulative_common_point_shortfall"] == pytest.approx(
            cumulative, abs=1e-10
        )
        assert row["mean_daily_common_point_shortfall"] == pytest.approx(
            cumulative / 130.0, abs=1e-10
        )
        assert cell.iloc[-1]["cumulative_common_point_shortfall"] == pytest.approx(
            cumulative, abs=1e-9
        )
        if model != "bsts_local_level_weekly":
            assert row["mean_daily_model_native_shortfall"] == pytest.approx(
                cumulative / 130.0, abs=1e-10
            )


def test_frozen_numeric_results_and_harmonized_range():
    summary = _summary().set_index(["vintage", "model"])
    for key, expected in EXPECTED_COMMON.items():
        assert summary.loc[key, "mean_daily_common_point_shortfall"] == pytest.approx(
            expected, abs=1e-10
        )
    pinned = summary.xs("pinned_primary")["mean_daily_common_point_shortfall"]
    assert pinned.max() - pinned.min() == pytest.approx(
        5.1748352114905245, abs=1e-10
    )
    assert summary.loc[
        ("pinned_primary", "bsts_local_level_weekly"),
        "mean_daily_model_native_shortfall",
    ] == pytest.approx(49.52249694980984, abs=1e-10)


def test_source_runtime_and_interval_metadata_are_scoped_correctly():
    daily = _daily()
    summary = _summary()
    expected_sources = {
        "pinned_primary": (
            "data/raw/portwatch/Daily_Chokepoints_Data.csv",
            "66f3a54afb042103f3e0afc9670568cb7be245394ec04eba55ebd158593f579d",
            "pinned_primary_reference",
        ),
        "vintage_20260809": (
            "data/raw/portwatch/vintages/Daily_Chokepoints_Data__vintage_2026-08-09.csv",
            "0bc806a4c384723debff08053d6fcbb915a03ee9fdf7b23c73d76d9bcb885bcb",
            "sensitivity_only",
        ),
    }
    for vintage, (path, source_sha, role) in expected_sources.items():
        rows = summary.loc[summary["vintage"].eq(vintage)]
        assert rows["source_path"].eq(path).all()
        assert rows["source_sha256"].eq(source_sha).all()
        assert rows["vintage_reporting_role"].eq(role).all()
        assert rows["unit"].eq("transits_per_day").all()

    chronos = summary.loc[summary["model"].eq("chronos2")]
    assert chronos["runtime_python"].eq("3.11.15").all()
    assert chronos["runtime_package_version"].eq("2.3.0").all()
    assert chronos["runtime_model_revision"].eq(
        "29ec3766d36d6f73f0696f85560a422f50e8498c"
    ).all()
    assert chronos["runtime_lockfile_sha256"].eq(
        "b4ac5fc4205fc6117409a4e99b220a05dc4afa00d54a0b31bd5740caa06a0683"
    ).all()
    assert "runtime_model_snapshot_path" not in summary.columns
    for model in ("chronos2", "bsts_local_level_weekly"):
        cell = daily.loc[daily["model"].eq(model)]
        assert np.isfinite(cell[["lower_pointwise", "upper_pointwise"]]).all().all()
        assert (cell["lower_pointwise"] <= cell["upper_pointwise"]).all()


def test_matrix_and_complete_branch_manifests_match_live_files():
    matrix_manifest = json.loads(MATRIX_MANIFEST_PATH.read_text(encoding="utf-8"))
    assert matrix_manifest["completed_cells"] == matrix_manifest["expected_cells"] == 8
    assert matrix_manifest["vintage_averaging"] == "prohibited_and_not_performed"
    assert all(check["passed"] for check in matrix_manifest["pinned_self_checks"].values())
    for relative, expected in matrix_manifest["output_sha256"].items():
        assert sha256_file(config.ROOT / relative) == expected

    written_complete = json.loads(
        (config.ROOT / COMPLETE_MANIFEST).read_text(encoding="utf-8")
    )
    live_complete = build_complete_manifest()
    assert written_complete == live_complete
    assert len(live_complete["artifact_sha256"]) == 13
    assert all(live_complete["matrix_artifact_presence"].values())
    assert live_complete["core_run_all_dependency"] == "required_for_final_integration"
    assert live_complete["core_reproducibility_manifest_dependency"] == "none"

    checkpoint = json.loads(
        config.path("model_admission_pre_run_checkpoint_json").read_text()
    )
    prepared_path = config.path("portwatch_sensitivity_manifest_json")
    checkpoint_sha = checkpoint["checkpoint_input_sha256"][
        "data/processed/portwatch_sensitivity_manifest.json"
    ]
    assert live_complete["prepared_manifest_sha256"] == checkpoint_sha
    assert live_complete["current_prepared_manifest_sha256"] == sha256_file(
        prepared_path
    )
    assert live_complete["prepared_manifest_matches_checkpoint"] is False
    assert live_complete["prepared_manifest_provenance_status"] == (
        "historical_pre_run_bytes_unavailable"
    )
    assert live_complete["pre_run_freeze_claim_permitted"] is False
    gap = live_complete["disclosed_provenance_gap"]
    assert gap["scope"] == "checkpointed_manifest_bytes"
    assert set(gap["affected_paths"]) == {
        "data/processed/portwatch_sensitivity_manifest.json",
        "data/processed/portwatch_sensitivity_input_manifest.json",
    }
    assert gap["scientific_anchors_verified"] is True

    anchors = live_complete["checkpoint_scientific_anchor_verification"]
    assert anchors["matrix_design"]["matches"] is True
    assert anchors["admission_protocol"]["matches"] is True
    assert all(anchor["matches"] for anchor in anchors["raw_vintages"].values())


def test_live_matrix_passes_frozen_validator_and_pinned_self_checks():
    daily = _daily()
    summary = _summary()
    design, digest = load_design()
    validate_complete_matrix(daily, summary, design, digest)
    checks = pinned_self_checks(daily, summary)
    assert set(checks) == set(design["completion_contract"]["expected_models"])
    assert all(check["passed"] for check in checks.values())


@pytest.mark.parametrize(
    ("mutation", "match"),
    [
        ("missing_daily_row", "mismatched scored dates"),
        ("wrong_unit", "mixes outcome units"),
        ("wrong_design_hash", "stale design hashes"),
    ],
)
def test_frozen_validator_rejects_corrupted_matrix(mutation: str, match: str):
    daily = _daily()
    summary = _summary()
    design, digest = load_design()
    if mutation == "missing_daily_row":
        daily = daily.iloc[1:].copy()
    elif mutation == "wrong_unit":
        summary.loc[0, "unit"] = "normalized_index"
    elif mutation == "wrong_design_hash":
        daily.loc[0, "design_sha256"] = "0" * 64
    with pytest.raises(ValueError, match=match):
        validate_complete_matrix(daily, summary, design, digest)
