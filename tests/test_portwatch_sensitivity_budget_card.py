from __future__ import annotations

import json
import struct

import numpy as np
import pandas as pd
import pytest

from lngfreight import config
from freeze_portwatch_sensitivity_budget_card import (
    build_manifest,
    manifest_path,
)
from freeze_portwatch_sensitivity_complete import build_complete_manifest
from make_portwatch_sensitivity_budget_card import (
    DESIGN_PATH,
    build_card_payload,
    build_cell_table,
    load_design,
    load_verified_inputs,
    output_path,
    sha256_file,
    validate_matrix_summary,
)


PHASE4_MANIFEST = (
    config.path("data_processed") / "portwatch_sensitivity_complete_manifest.json"
)
PHASE4_SHA256 = "2d6daf153d4fe73224533cbd39c64631a1156c44f4907959283c2550ca651fa7"
MATRIX_SUMMARY_SHA256 = "79043329359bb6194260ff4461fef9a2da679a0e120136b3bfdec93531c8be89"
MATRIX_MANIFEST_SHA256 = "65cb3352877f2cdd3042360ecdb25a4ee7ca77bd30a54a683dbebb1c14ca711b"
ADMISSION_RESULTS_SHA256 = "d191a2329b5471c9bd718fd22f7c92c9c608db147485ef6d08c4970bcdfa643e"

EXPECTED_COMMON = {
    "seasonal_naive_7d": (54.8, 43.7),
    "ar_lag1_7": (52.83843081600861, 43.81350622973898),
    "chronos2": (50.88375704838679, 42.17672494741586),
    "bsts_local_level_weekly": (49.62516478850947, 40.16745715691507),
}
EXPECTED_SHARES = {
    "seasonal_naive_7d": (93.08767803475762, 93.40677408747122),
    "ar_lag1_7": (92.84941490147921, 93.42273149022826),
    "chronos2": (92.59506911118999, 93.18487839293523),
    "bsts_local_level_weekly": (92.42149813409311, 92.86828305937583),
}


def _required_paths() -> list:
    design, _ = load_design()
    return [
        PHASE4_MANIFEST,
        *(config.ROOT / spec["path"] for spec in design["parent_artifacts"].values()),
        *(output_path(design, key) for key in (
            "card_csv",
            "card_json",
            "card_markdown",
            "card_png",
            "card_pdf",
        )),
    ]


pytestmark = pytest.mark.skipif(
    not all(path.is_file() for path in _required_paths()),
    reason="optional PortWatch sensitivity-budget reporting layer is not deposited",
)


def _live() -> tuple[dict, str, pd.DataFrame, pd.DataFrame, pd.DataFrame, dict]:
    design, design_sha = load_design()
    summary, admission = load_verified_inputs(design)
    cells = build_cell_table(summary, design)
    payload = build_card_payload(cells, admission, design, design_sha)
    return design, design_sha, summary, admission, cells, payload


def test_parent_hashes_and_phase4_lifecycle_are_unchanged():
    design, _, _, _, _, _ = _live()
    parents = design["parent_artifacts"]
    assert parents["complete_branch_manifest"]["sha256"] == PHASE4_SHA256
    assert parents["matrix_summary"]["sha256"] == MATRIX_SUMMARY_SHA256
    assert parents["matrix_manifest"]["sha256"] == MATRIX_MANIFEST_SHA256
    assert parents["admission_known_results"]["sha256"] == ADMISSION_RESULTS_SHA256
    for spec in parents.values():
        assert sha256_file(config.ROOT / spec["path"]) == spec["sha256"]

    assert sha256_file(PHASE4_MANIFEST) == PHASE4_SHA256
    written = json.loads(PHASE4_MANIFEST.read_text(encoding="utf-8"))
    assert written == build_complete_manifest()
    assert len(written["artifact_sha256"]) == 13


def test_card_is_exact_selected_two_vintage_four_model_population():
    design, _, _, _, cells, payload = _live()
    assert list(cells["model"]) == design["selected_representative_models"]
    assert len(cells) == 4
    assert payload["selected_representative_models"] == list(EXPECTED_COMMON)
    excluded = {
        "timesfm",
        "moirai",
        "arx_lag1_7_route_energy",
        "arx_lag1_7_route",
        "synthetic_control",
    }
    assert excluded.isdisjoint(set(cells["model"]))
    assert cells["is_locked_primary_model"].sum() == 1
    assert cells.loc[cells["is_locked_primary_model"], "model"].item() == "ar_lag1_7"


def test_absolute_card_values_use_the_harmonized_common_statistic():
    _, _, summary, _, cells, payload = _live()
    indexed = cells.set_index("model")
    for model, (pinned, august) in EXPECTED_COMMON.items():
        assert indexed.loc[model, "pinned_shortfall_per_day"] == pytest.approx(
            pinned, abs=1e-12
        )
        assert indexed.loc[model, "august_shortfall_per_day"] == pytest.approx(
            august, abs=1e-12
        )
        assert indexed.loc[model, "pinned_minus_august_per_day"] == pytest.approx(
            pinned - august, abs=1e-12
        )

    bsts = summary.loc[summary["model"].eq("bsts_local_level_weekly")].set_index(
        "vintage"
    )
    assert indexed.loc[
        "bsts_local_level_weekly", "pinned_shortfall_per_day"
    ] == pytest.approx(49.62516478850947, abs=1e-12)
    assert indexed.loc[
        "bsts_local_level_weekly", "pinned_shortfall_per_day"
    ] != pytest.approx(
        bsts.loc["pinned_primary", "mean_daily_model_native_shortfall"], abs=1e-6
    )
    assert indexed.loc[
        "bsts_local_level_weekly", "august_shortfall_per_day"
    ] != pytest.approx(
        bsts.loc["vintage_20260809", "mean_daily_model_native_shortfall"], abs=1e-6
    )

    ranges = payload["primary_absolute_axes"]["selected_model_range_within_vintage"]
    assert ranges[0]["range"] == pytest.approx(5.1748352114905245, abs=1e-12)
    assert ranges[1]["range"] == pytest.approx(3.6460490728239066, abs=1e-12)
    cross = payload["primary_absolute_axes"]["cross_axis_reading"]
    assert cross["smallest_same_model_vintage_difference"] == pytest.approx(
        8.707032100970928, abs=1e-12
    )
    assert cross["smallest_vintage_difference_exceeds_largest_model_range"] is True
    assert cross["ar_primary_difference_to_pinned_model_range_ratio"] == pytest.approx(
        1.7440023145529606, abs=1e-12
    )


def test_normalized_context_recomputes_cell_specific_denominators_in_percentage_points():
    design, _, summary, _, cells, payload = _live()
    summary = summary.set_index(["vintage", "model"])
    indexed = cells.set_index("model")
    for model, (pinned_share, august_share) in EXPECTED_SHARES.items():
        for vintage, output_column, expected in (
            ("pinned_primary", "pinned_shortfall_share_of_counterfactual_pct", pinned_share),
            ("vintage_20260809", "august_shortfall_share_of_counterfactual_pct", august_share),
        ):
            row = summary.loc[(vintage, model)]
            assert row["counterfactual_point_sum"] > 0
            assert row["counterfactual_point_sum"] == pytest.approx(
                row["observed_sum"] + row["cumulative_common_point_shortfall"],
                abs=1e-9,
            )
            recomputed = (
                100.0
                * row["cumulative_common_point_shortfall"]
                / row["counterfactual_point_sum"]
            )
            assert recomputed == pytest.approx(expected, abs=1e-12)
            assert indexed.loc[model, output_column] == pytest.approx(
                recomputed, abs=1e-12
            )

    normalized = payload["secondary_normalized_context"]
    assert normalized["all_cells_minimum_pct"] == pytest.approx(
        92.42149813409311, abs=1e-12
    )
    assert normalized["all_cells_maximum_pct"] == pytest.approx(
        93.42273149022826, abs=1e-12
    )
    assert normalized["within_vintage_model_ranges"][0]["range"] == pytest.approx(
        0.6661799006645026, abs=1e-12
    )
    assert normalized["within_vintage_model_ranges"][1]["range"] == pytest.approx(
        0.5544484308524318, abs=1e-12
    )
    assert normalized["minimum_same_model_change_percentage_points"] == pytest.approx(
        0.3190960527136042, abs=1e-12
    )
    assert normalized["maximum_same_model_change_percentage_points"] == pytest.approx(
        0.5898092817452465, abs=1e-12
    )
    secondary = design["comparison_basis"]["secondary_denominator_check"]
    assert secondary["between_cell_difference_unit"] == "percentage_points"
    assert secondary["role"] == "descriptive_scale_context_only_not_budget_axis"
    assert secondary["not_equivalent_to"] == "raw_observed_pre_post_decline"


def test_admission_challenge_is_disclosed_but_never_mixed_into_selected_cells():
    design, _, _, admission, cells, payload = _live()
    arx = admission.loc[
        admission["result_id"].eq("pinned_arx_route_energy_mixed_information")
    ].iloc[0]
    assert arx["artifact_value"] == pytest.approx(62.85785921606604, abs=1e-12)
    assert bool(arx["comparable_same_information"]) is False
    assert arx["unit"] == "transits_per_day"
    challenge = payload["mixed_information_challenge"]
    assert challenge["mixed_information_pinned_range_per_day"] == pytest.approx(
        13.232694427556567, abs=1e-12
    )
    assert challenge[
        "mixed_information_range_exceeds_maximum_selected_vintage_difference"
    ] is True
    assert "arx_lag1_7_route_energy" not in set(cells["model"])
    assert design["reporting_guards"]["admission_timing"] == (
        "ex_post_unblinded_governance_lock"
    )
    assert design["reporting_guards"]["vintage_scope"] == (
        "full_saved_series_measurement_state_affecting_training_and_scoring"
    )
    assert design["reporting_guards"]["all_preperiod_admitted_model_range"] == (
        "not_estimated"
    )


def test_card_has_no_combined_budget_or_vintage_average_and_stays_out_of_core():
    design, _, _, _, _, payload = _live()
    assert design["axes"]["axes_are_additive"] is False
    assert design["axes"]["combined_budget_total_permitted"] is False
    assert design["axes"]["vintage_averaging_permitted"] is False
    assert payload["axes_are_additive"] is False
    assert payload["combined_budget_total"] is None
    assert payload["vintage_averaging"] == "prohibited_and_not_performed"

    run_all = (config.ROOT / "scripts/run_all.py").read_text(encoding="utf-8")
    settings = (config.ROOT / "config/settings.yaml").read_text(encoding="utf-8")
    for token in (
        "make_portwatch_sensitivity_budget_card.py",
        "freeze_portwatch_sensitivity_budget_card.py",
        "portwatch_sensitivity_budget_card.csv",
        "portwatch_sensitivity_budget_card_manifest.json",
    ):
        assert token not in run_all
        assert token not in settings


def test_written_outputs_and_separate_manifest_match_live_build():
    design, design_sha, _, _, cells, payload = _live()
    written_cells = pd.read_csv(output_path(design, "card_csv"))
    pd.testing.assert_frame_equal(
        written_cells,
        cells,
        check_dtype=False,
        check_exact=False,
        rtol=0.0,
        atol=1e-12,
    )
    written_payload = json.loads(
        output_path(design, "card_json").read_text(encoding="utf-8")
    )
    assert written_payload == payload
    assert written_payload["design_sha256"] == design_sha
    assert written_payload["status"] == "assistant_generated_reporting_artifact"
    assert written_payload["human_verification_record"] == "docs/DECISION_LOG.md"

    written_manifest = json.loads(manifest_path().read_text(encoding="utf-8"))
    live_manifest = build_manifest()
    assert written_manifest == live_manifest
    assert live_manifest["phase4_complete_manifest_sha256"] == PHASE4_SHA256
    assert live_manifest["phase4_artifact_count"] == 13
    assert live_manifest["phase4_manifest_mutated"] is False
    assert live_manifest["core_run_all_dependency"] == "none"
    assert live_manifest["core_reproducibility_manifest_dependency"] == "none"
    assert live_manifest["status"] == "assistant_generated_reporting_artifact"
    assert live_manifest["human_verification_record"] == "docs/DECISION_LOG.md"
    assert len(live_manifest["output_sha256"]) == 5
    for relative, expected in live_manifest["output_sha256"].items():
        assert sha256_file(config.ROOT / relative) == expected


def test_figure_files_have_valid_signatures_and_dimensions():
    design, _, _, _, _, _ = _live()
    png = output_path(design, "card_png").read_bytes()
    pdf = output_path(design, "card_pdf").read_bytes()
    assert png.startswith(b"\x89PNG\r\n\x1a\n")
    width, height = struct.unpack(">II", png[16:24])
    assert width >= 2000
    assert height >= 1200
    assert width > height
    assert pdf.startswith(b"%PDF-")
    assert len(pdf) > 10_000


def test_markdown_keeps_the_case_local_interpretation_guards():
    design, _, _, _, _, _ = _live()
    text = output_path(design, "card_markdown").read_text(encoding="utf-8")
    required = (
        "a third budget component",
        "descriptive scale context rather than independent robustness evidence",
        "frozen ex post and unblinded",
        "There is no combined budget total and no vintage average",
        "not an uncertainty interval, variance decomposition, ATT",
        "general statement about AIS reliability",
        "both pre-treatment training and post-treatment scoring",
        "not attributable only to revised post-treatment counts",
        "August raw source-byte archive deposit remains pending",
    )
    for phrase in required:
        assert phrase in text


@pytest.mark.parametrize(
    ("mutation", "match"),
    [
        ("missing_cell", "exact selected 2x4 matrix"),
        ("duplicate_cell", "exact selected 2x4 matrix"),
        ("wrong_unit", "mixes units"),
        ("wrong_support", "support drifted"),
        ("wrong_window", "scoring_end drifted"),
        ("unequal_observed_sum", "observed totals differ within vintage"),
        ("wrong_point_definition", "point definition drifted"),
        ("nonpositive_denominator", "denominator is non-positive"),
        ("broken_reconciliation", "does not reconcile to observed"),
        ("broken_daily_mean", "mean-daily statistic does not reconcile"),
    ],
)
def test_validator_rejects_corrupted_matrix_summary(mutation: str, match: str):
    design, _, summary, _, _, _ = _live()
    corrupted = summary.copy()
    if mutation == "missing_cell":
        corrupted = corrupted.iloc[1:].copy()
    elif mutation == "duplicate_cell":
        corrupted = pd.concat([corrupted, corrupted.iloc[[0]]], ignore_index=True)
    elif mutation == "wrong_unit":
        corrupted.loc[0, "unit"] = "normalized_index"
    elif mutation == "wrong_support":
        corrupted.loc[0, "n_scored_days"] = 129
    elif mutation == "wrong_window":
        corrupted.loc[0, "scoring_end"] = "2026-07-06"
    elif mutation == "unequal_observed_sum":
        corrupted.loc[0, "observed_sum"] += 1.0
        corrupted.loc[0, "counterfactual_point_sum"] += 1.0
    elif mutation == "wrong_point_definition":
        corrupted.loc[0, "point_definition"] = "joint_native_median"
    elif mutation == "nonpositive_denominator":
        corrupted.loc[0, "counterfactual_point_sum"] = 0.0
    elif mutation == "broken_reconciliation":
        corrupted.loc[0, "cumulative_common_point_shortfall"] += 1.0
        corrupted.loc[0, "mean_daily_common_point_shortfall"] += 1.0 / 130.0
    elif mutation == "broken_daily_mean":
        corrupted.loc[0, "mean_daily_common_point_shortfall"] += 1.0
    with pytest.raises(ValueError, match=match):
        validate_matrix_summary(corrupted, design)
