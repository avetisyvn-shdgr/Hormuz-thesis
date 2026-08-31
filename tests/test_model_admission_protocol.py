from __future__ import annotations

import copy
import hashlib
import json

import pandas as pd
import pytest

from hormuz_throughput import config
from build_model_admission_protocol import (
    EXPECTED_PRIMARY_MODELS,
    HASH_MIGRATIONS_PATH,
    _verify_known_result,
    build_tables,
    load_protocol,
    validate_protocol,
)


def _loaded() -> tuple[dict, str, pd.DataFrame, pd.DataFrame]:
    protocol, digest = load_protocol()
    validate_protocol(protocol)
    models, known = build_tables(protocol, digest)
    return protocol, digest, models, known


def test_protocol_is_an_ex_post_four_specification_governance_lock():
    protocol, _, models, _ = _loaded()
    assert protocol["design_timing"]["preregistered"] is False
    assert protocol["design_timing"]["results_blinded"] is False
    included = models.loc[models["representative_matrix_selected"]]
    assert set(included["model"]) == EXPECTED_PRIMARY_MODELS
    assert included["same_information_contract"].all()
    assert included["expected_scored_days"].eq(130).all()
    assert included["locked_cutoff"].eq("2026-02-28").all()
    assert included["scoring_end"].eq("2026-07-07").all()
    assert included["unit"].eq("transits_per_day").all()


def test_hash_migrations_are_explicit_and_fail_closed():
    migrations = json.loads(HASH_MIGRATIONS_PATH.read_text())["migrations"]
    assert len(migrations) == 5
    assert len({item["path"] for item in migrations}) == len(migrations)
    for item in migrations:
        assert len(item["historical_sha256"]) == 64
        assert len(item["current_sha256"]) == 64
        assert item["historical_sha256"] != item["current_sha256"]
        assert item["verification"].strip()
        assert item["reason"].strip()


def test_preperiod_admission_is_distinct_from_common_window_support():
    _, _, models, _ = _loaded()
    additional = models.set_index("model").loc[["timesfm", "moirai"]]
    assert additional["pre_treatment_admission_passed"].all()
    assert not additional["pinned_130_day_support_verified"].any()
    assert not additional["representative_matrix_selected"].any()
    assert additional["status_code"].str.startswith("NOT_RUN_").all()


def test_information_and_unit_exclusions_remain_visible_without_mixed_range():
    protocol, _, models, _ = _loaded()
    rows = models.set_index("model")
    assert rows.loc[
        ["arx_lag1_7_route", "arx_lag1_7_route_energy"],
        "post_covariates_ingested",
    ].all()
    assert rows.loc["synthetic_control", "status_code"] == (
        "EXCLUDE_POST_DONORS_AND_MEAN_SCALED_UNITS"
    )
    sets = protocol["comparison_sets"]
    assert sets["mixed_information_range_status"].startswith("not_computed")
    assert sets["synthetic_range_status"].startswith("not_computed")
    assert sets["all_preperiod_admitted_range_status"].startswith("not_estimated")


def test_chronos_rationale_discloses_timesfm_point_metric_win():
    protocol, _, _, _ = _loaded()
    evidence = protocol["representative_selection"]["preperiod_evidence"]
    assert evidence["timesfm_mase"] < evidence["chronos2_mase"]
    assert (
        evidence["chronos2_abs_coverage_error"]
        < evidence["timesfm_abs_coverage_error"]
    )
    assert protocol["representative_selection"]["status_code"] == (
        "INCLUDE_HISTORICALLY_IMPLEMENTED_FAMILY_REPRESENTATIVE"
    )


def test_known_results_verify_hash_support_units_and_formulas():
    _, _, _, known = _loaded()
    assert len(known) == 14
    assert known["verified_against_artifact"].all()
    assert known["verification_delta"].abs().max() <= 1e-9
    common = known.loc[
        known["result_id"].isin({
            "pinned_seasonal_common", "pinned_ar_common",
            "pinned_chronos_common", "pinned_bsts_common",
        })
    ]
    assert len(common) == 4
    assert common["verified_n_days"].eq(130).all()
    assert common["verified_observed_sum"].eq(529.0).all()
    assert common["observed_support_sha256"].nunique() == 1
    assert common["unit"].eq("transits_per_day").all()
    assert common["artifact_value"].max() - common["artifact_value"].min() == pytest.approx(
        5.1748352114905245
    )


def test_written_tables_equal_live_builder_output():
    _, _, models, known = _loaded()
    written_models = pd.read_csv(config.path("model_admission_protocol_csv"))
    written_known = pd.read_csv(config.path("model_admission_known_results_csv"))
    pd.testing.assert_frame_equal(written_models, models, check_dtype=False)
    pd.testing.assert_frame_equal(written_known, known, check_dtype=False)


def test_known_result_rejects_wrong_source_hash():
    protocol, _ = load_protocol()
    declaration = copy.deepcopy(protocol["known_artifact_results_at_lock"][0])
    declaration["source_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="hash mismatch"):
        _verify_known_result(protocol, declaration)


def _temporary_daily_declaration(tmp_path, monkeypatch, *, drop_last=False, wrong_date=False):
    protocol, _ = load_protocol()
    declaration = copy.deepcopy(protocol["known_artifact_results_at_lock"][0])
    source = config.ROOT / declaration["source"]
    frame = pd.read_csv(source)
    mask = (
        frame["model"].eq(declaration["filters"]["model"])
        & frame["target"].eq(declaration["filters"]["target"])
    )
    if drop_last:
        frame = frame.drop(frame.index[mask][-1])
    if wrong_date:
        first = frame.index[mask][0]
        frame.loc[first, "date"] = "2026-02-27"
    relative = "data/processed/daily.csv"
    target = tmp_path / relative
    target.parent.mkdir(parents=True)
    frame.to_csv(target, index=False)
    declaration["source"] = relative
    declaration["source_sha256"] = hashlib.sha256(target.read_bytes()).hexdigest()
    monkeypatch.setattr(config, "ROOT", tmp_path)
    return protocol, declaration


def test_known_result_rejects_wrong_date_support(tmp_path, monkeypatch):
    protocol, declaration = _temporary_daily_declaration(
        tmp_path, monkeypatch, wrong_date=True
    )
    with pytest.raises(ValueError, match="scoring dates drifted"):
        _verify_known_result(protocol, declaration)


def test_known_result_rejects_wrong_day_count(tmp_path, monkeypatch):
    protocol, declaration = _temporary_daily_declaration(
        tmp_path, monkeypatch, drop_last=True
    )
    with pytest.raises(ValueError, match="does not contain 130 rows"):
        _verify_known_result(protocol, declaration)


def test_known_result_rejects_wrong_unit():
    protocol, _ = load_protocol()
    declaration = copy.deepcopy(protocol["known_artifact_results_at_lock"][0])
    declaration["unit"] = "capacity_per_day"
    with pytest.raises(ValueError, match="wrong unit"):
        _verify_known_result(protocol, declaration)
