"""Structural and corruption tests for the task-6 horizon/resolution frontier.

These tests police the design, not the answer. They assert that the origin
rules cannot see an outcome, that the enumeration is complete, that the
finite-sample arithmetic is exact, that unbounded levels are never clipped, and
that the locked primary block artifacts are not rewritten. They deliberately do
not assert that any particular loss is large.
"""
from __future__ import annotations

import json
import math

import numpy as np
import pandas as pd
import pytest

from hormuz_throughput import config
from hormuz_throughput import horizon_frontier as hf
from hormuz_throughput.inference import conformal_effect_interval

from freeze_horizon_resolution_frontier import (
    assert_locked_primary_untouched,
    build_manifest,
    manifest_path,
)
from run_horizon_resolution_frontier import (
    build_audit_expectation,
    build_geometry,
    build_summary,
    guard_summary,
    load_design,
    load_verified_inputs,
    output_path,
    sha256_file,
    treated_block,
    validate_panel,
)


CUTOFF = pd.Timestamp("2026-02-28")
MIN_TRAIN = 365


def _synthetic_index(start: str = "2022-01-01", days: int = 1519) -> pd.DatetimeIndex:
    return pd.date_range(start, periods=days, freq="D")


def _design():
    design, sha = load_design()
    return design, sha


def _outputs_present() -> bool:
    design, _ = _design()
    return all(output_path(design, key).is_file() for key in (
        "geometry_csv",
        "blocks_csv",
        "summary_csv",
        "diagnostics_json",
        "audit_expectation_json",
        "documentation_markdown",
        "manifest_json",
    ))


needs_outputs = pytest.mark.skipif(
    not _outputs_present(),
    reason="horizon/resolution frontier artifacts are not generated",
)




def test_packing_bound_is_floor_of_span_over_horizon():
    index = _synthetic_index()
    span = hf.available_reference_days(index, CUTOFF, MIN_TRAIN)
    assert span == 1519 - MIN_TRAIN
    for horizon in (30, 65, 91, 130):
        assert hf.packing_upper_bound(index, CUTOFF, horizon, MIN_TRAIN) == (
            span // horizon
        )


def test_direct_tiling_attains_the_packing_bound():
    index = _synthetic_index()
    for horizon in (30, 65, 91, 130):
        bound = hf.packing_upper_bound(index, CUTOFF, horizon, MIN_TRAIN)
        blocks = hf.reference_blocks(
            index, CUTOFF, horizon, MIN_TRAIN, origin_rule=hf.PRIMARY_RULE
        )
        assert len(blocks) == bound


def test_complete_enumeration_beats_the_coarsened_greedy_selection():
    """The locked construction is a restricted subsample, and it can cost blocks."""
    index = _synthetic_index()
    for horizon in (65, 91, 130):
        optimal = hf.maximum_disjoint_packing(
            hf.enumerate_candidate_blocks(index, CUTOFF, horizon, MIN_TRAIN)
        )
        legacy = hf.reference_blocks(
            index, CUTOFF, horizon, MIN_TRAIN, origin_rule=hf.LEGACY_RULE
        )
        assert len(legacy) <= len(optimal)
    assert len(hf.reference_blocks(
        index, CUTOFF, 130, MIN_TRAIN, origin_rule=hf.LEGACY_RULE
    )) == 7
    assert len(hf.reference_blocks(
        index, CUTOFF, 130, MIN_TRAIN, origin_rule=hf.PRIMARY_RULE
    )) == 8


def _dp_optimum(candidates: list[hf.Block]) -> int:
    """Independent reference optimum via interval-scheduling DP.

    Deliberately a different algorithm from the earliest-end greedy under test,
    so agreement is evidence rather than a restatement.
    """
    ordered = sorted(candidates, key=lambda b: (b.end, b.start))
    best = [0] * (len(ordered) + 1)
    for i, block in enumerate(ordered, start=1):
        skip = best[i - 1]
        prior = 0
        for j in range(i - 1, 0, -1):
            if ordered[j - 1].end < block.start:
                prior = best[j]
                break
        best[i] = max(skip, 1 + prior)
    return best[-1]


@pytest.mark.parametrize(
    ("days", "cutoff", "horizon", "min_train"),
    [
        (40, "2022-02-10", 7, 5),
        (60, "2022-02-25", 11, 9),
        (90, "2022-03-20", 13, 21),
        (120, "2022-04-15", 30, 30),
    ],
)
def test_maximum_packing_is_optimal_against_an_independent_dp(
    days, cutoff, horizon, min_train
):
    index = pd.date_range("2022-01-01", periods=days, freq="D")
    candidates = hf.enumerate_candidate_blocks(
        index, pd.Timestamp(cutoff), horizon, min_train
    )
    assert len(hf.maximum_disjoint_packing(candidates)) == _dp_optimum(candidates)


def test_every_rule_returns_disjoint_in_window_blocks():
    index = _synthetic_index()
    for rule in hf.ORIGIN_RULES:
        for horizon in (30, 65, 91, 130):
            blocks = hf.reference_blocks(
                index, CUTOFF, horizon, MIN_TRAIN, origin_rule=rule
            )
            hf.assert_disjoint(blocks)
            anchor = hf.anchor_origin(index, MIN_TRAIN)
            for block in blocks:
                assert block.length_days == horizon
                assert block.start >= anchor
                assert block.end < CUTOFF


def test_origin_rules_are_outcome_independent():
    """Identical calendars must give identical geometry under any outcome path."""
    index = _synthetic_index()
    rng = np.random.default_rng(0)
    baseline = {
        rule: hf.geometry_frame(
            index, CUTOFF, 130, MIN_TRAIN, origin_rule=rule
        )
        for rule in hf.ORIGIN_RULES
    }
    for _ in range(3):
        _ = pd.Series(rng.normal(size=len(index)), index=index)
        for rule in hf.ORIGIN_RULES:
            pd.testing.assert_frame_equal(
                hf.geometry_frame(
                    index, CUTOFF, 130, MIN_TRAIN, origin_rule=rule
                ),
                baseline[rule],
            )


def test_geometry_frame_carries_no_outcome_column():
    index = _synthetic_index()
    frame = hf.geometry_frame(index, CUTOFF, 130, MIN_TRAIN)
    for column in frame.columns:
        assert "loss" not in column
        assert "observed" not in column
        assert "counterfactual" not in column


def test_unknown_origin_rule_is_rejected():
    index = _synthetic_index()
    with pytest.raises(ValueError, match="Unknown origin_rule"):
        hf.reference_blocks(
            index, CUTOFF, 130, MIN_TRAIN, origin_rule="pick_the_best_one"
        )


def test_block_fold_training_never_crosses_its_block():
    index = _synthetic_index()
    for block in hf.reference_blocks(index, CUTOFF, 130, MIN_TRAIN):
        fold = hf.block_fold(index, block)
        assert fold.train_end < block.start
        assert fold.test_start == block.start
        assert fold.test_end == block.end
        assert len(fold.test_idx) == 130




def test_frontier_capacity_matches_the_closed_form():
    capacity = hf.frontier_capacity(8, [0.80, 0.90, 0.95])
    assert capacity["n_reference_blocks"] == 8
    assert capacity["rank_p_value_floor"] == pytest.approx(1 / 9)
    assert capacity["maximum_attainable_coverage"] == pytest.approx(8 / 9)
    assert capacity["finite_interval_levels"] == [0.80]
    assert capacity["unbounded_interval_levels"] == [0.90, 0.95]
    assert capacity["five_percent_floor_attainable"] is False


def test_conformal_rank_and_support_agree_with_the_inference_module():
    """The frontier and the locked interval helper must not drift apart."""
    rng = np.random.default_rng(7)
    for n_blocks in range(1, 25):
        errors = rng.normal(size=n_blocks)
        for level in (0.50, 0.80, 0.90, 0.95, 0.99):
            interval = conformal_effect_interval(0.0, errors, alpha=1 - level)
            assert interval["order_statistic_rank"] == hf.conformal_rank(
                n_blocks, level
            )
            supported = hf.conformal_rank(n_blocks, level) <= n_blocks
            assert bool(interval["finite_interval_supported"]) is supported
            assert bool(np.isfinite(interval["radius"])) is supported
            assert interval["maximum_finite_coverage"] == pytest.approx(
                n_blocks / (n_blocks + 1)
            )


def test_minimum_blocks_for_level_is_the_smallest_k_with_finite_support():
    for level in (0.50, 0.75, 0.80, 0.90, 0.95, 0.975, 0.99):
        required = hf.minimum_blocks_for_level(level)
        assert hf.conformal_rank(required, level) <= required
        for smaller in range(0, required):
            assert hf.conformal_rank(smaller, level) > smaller
    assert hf.minimum_blocks_for_level(0.80) == 4
    assert hf.minimum_blocks_for_level(0.90) == 9
    assert hf.minimum_blocks_for_level(0.95) == 19


def test_capacity_rejects_degenerate_inputs():
    with pytest.raises(ValueError):
        hf.frontier_capacity(0, [0.80])
    with pytest.raises(ValueError):
        hf.conformal_rank(8, 1.0)
    with pytest.raises(ValueError):
        hf.conformal_rank(8, 0.0)
    with pytest.raises(ValueError):
        hf.packing_upper_bound(_synthetic_index(), CUTOFF, 0, MIN_TRAIN)




def test_design_holds_the_locked_basis_fixed():
    design, _ = _design()
    fixed = design["held_fixed"]
    assert fixed["outcome"] == "hormuz_tanker_transits"
    assert fixed["model_id"] == "ar_lag1_7"
    assert list(fixed["y_lags"]) == [1, 7]
    assert list(fixed["exog_cols"]) == []
    assert fixed["training_cutoff_exclusive"] == "2026-02-28"
    assert fixed["treated_window_start"] == "2026-02-28"
    assert fixed["treated_window_end"] == "2026-07-07"
    assert int(fixed["treated_window_days"]) == 130


def test_design_declares_a_primary_rule_and_complete_horizon_grid():
    design, _ = _design()
    roles = [spec["role"] for spec in design["origin_rules"].values()]
    assert roles.count("primary") == 1
    assert set(design["origin_rules"]) == set(hf.ORIGIN_RULES)
    assert int(design["primary_horizon_days"]) in design["horizon_grid_days"]
    assert max(design["horizon_grid_days"]) <= int(
        design["held_fixed"]["treated_window_days"]
    )
    assert design["freeze_status"]["timing"] == (
        "frozen_before_generation_not_preregistered"
    )


def test_design_forbids_causal_and_five_percent_claims():
    design, _ = _design()
    guards = design["reporting_guards"]
    assert guards["is_ATT"] is False
    assert guards["is_causal_identification"] is False
    assert guards["five_percent_significance_claim_permitted"] is False
    assert guards["overwrite_policy"].startswith("locked_primary")


def test_horizons_longer_than_the_treated_window_are_rejected():
    design, _ = _design()
    panel = pd.DataFrame(
        {"hormuz_tanker_transits": np.ones(1649)},
        index=pd.date_range("2022-01-01", periods=1649, freq="D"),
    )
    corrupted = json.loads(json.dumps({
        "held_fixed": design["held_fixed"],
        "horizon_grid_days": [131],
        "primary_horizon_days": 131,
    }))
    with pytest.raises(ValueError, match="longer than the treated window"):
        validate_panel(panel, corrupted)


def test_treated_block_never_moves_the_treatment_date():
    design, _ = _design()
    for horizon in design["horizon_grid_days"]:
        block = treated_block(design, int(horizon))
        assert block.start == pd.Timestamp(
            design["held_fixed"]["treated_window_start"]
        )
        assert block.length_days == int(horizon)




def _minimal_summary() -> pd.DataFrame:
    return pd.DataFrame([
        {
            "rank_p_value_greater": 0.125,
            "rank_p_value_floor": 0.125,
            "five_percent_floor_attainable": False,
            "five_percent_significance_claimed": False,
            "is_primary_reporting_resolution": True,
            "maximum_attainable_coverage": 7 / 8,
            "level": 0.80,
            "finite_interval_supported": True,
            "conformal_radius": 100.0,
            "interval_lower": -100.0,
            "interval_upper": 100.0,
        },
        {
            "rank_p_value_greater": 0.125,
            "rank_p_value_floor": 0.125,
            "five_percent_floor_attainable": False,
            "five_percent_significance_claimed": False,
            "is_primary_reporting_resolution": True,
            "maximum_attainable_coverage": 7 / 8,
            "level": 0.95,
            "finite_interval_supported": False,
            "conformal_radius": float("inf"),
            "interval_lower": -float("inf"),
            "interval_upper": float("inf"),
        },
    ])


def test_guard_accepts_a_well_formed_summary():
    guard_summary(_minimal_summary())


def test_guard_rejects_a_clipped_unbounded_interval():
    corrupted = _minimal_summary()
    corrupted.loc[1, "conformal_radius"] = 100.0
    corrupted.loc[1, "interval_lower"] = -100.0
    corrupted.loc[1, "interval_upper"] = 100.0
    with pytest.raises(AssertionError, match="finite radius"):
        guard_summary(corrupted)


def test_guard_rejects_a_p_value_below_its_floor():
    corrupted = _minimal_summary()
    corrupted.loc[:, "rank_p_value_greater"] = 0.01
    with pytest.raises(AssertionError, match="below its finite-sample floor"):
        guard_summary(corrupted)


def test_guard_rejects_a_five_percent_significance_claim():
    corrupted = _minimal_summary()
    corrupted.loc[0, "five_percent_significance_claimed"] = True
    with pytest.raises(AssertionError, match="5% significance"):
        guard_summary(corrupted)


def test_guard_rejects_a_primary_cell_claiming_five_percent_capacity():
    corrupted = _minimal_summary()
    corrupted.loc[:, "five_percent_floor_attainable"] = True
    corrupted.loc[:, "rank_p_value_floor"] = 0.02
    with pytest.raises(AssertionError, match="primary reporting resolution"):
        guard_summary(corrupted)


def test_guard_rejects_an_inconsistent_five_percent_flag():
    corrupted = _minimal_summary()
    corrupted.loc[:, "is_primary_reporting_resolution"] = False
    corrupted.loc[0, "five_percent_floor_attainable"] = True
    with pytest.raises(AssertionError, match="disagrees with"):
        guard_summary(corrupted)


def test_guard_rejects_support_disagreeing_with_max_coverage():
    corrupted = _minimal_summary()
    corrupted.loc[1, "maximum_attainable_coverage"] = 0.99
    with pytest.raises(AssertionError, match="maximum attainable coverage"):
        guard_summary(corrupted)


def test_guard_rejects_an_empty_summary():
    with pytest.raises(AssertionError, match="empty"):
        guard_summary(_minimal_summary().iloc[0:0])


def test_overlapping_blocks_are_rejected():
    blocks = [
        hf.Block("a", pd.Timestamp("2023-01-01"), pd.Timestamp("2023-05-10")),
        hf.Block("b", pd.Timestamp("2023-05-10"), pd.Timestamp("2023-09-16")),
    ]
    with pytest.raises(AssertionError, match="overlap"):
        hf.assert_disjoint(blocks)


def test_upstream_hash_drift_stops_the_phase(tmp_path):
    design, _ = _design()
    corrupted = json.loads(json.dumps(design["upstream_locked_artifacts"]))
    corrupted["panel_aligned"]["sha256"] = "0" * 64
    with pytest.raises(ValueError, match="hash drift"):
        load_verified_inputs({
            **design,
            "upstream_locked_artifacts": corrupted,
        })




@needs_outputs
def test_locked_primary_block_artifacts_were_not_rewritten():
    design, _ = _design()
    assert_locked_primary_untouched(design)


@needs_outputs
def test_audit_expectation_is_reproduced_and_recorded():
    design, _ = _design()
    audit = json.loads(
        output_path(design, "audit_expectation_json").read_text(encoding="utf-8")
    )
    assert audit["rule"] == hf.PRIMARY_RULE
    assert audit["horizon_days"] == 130
    assert audit["checks"]["n_reference_blocks"]["observed"] == 8
    assert audit["checks"]["rank_p_value_floor"]["observed"] == pytest.approx(1 / 9)
    assert audit["checks"]["finite_interval_levels"]["observed"] == [0.80]
    assert audit["checks"]["unbounded_interval_levels"]["observed"] == [0.90, 0.95]
    assert audit["fully_reproduced"] is True


@needs_outputs
def test_legacy_rule_reproduces_the_locked_artifact_numbers():
    """The audit-reproduction rule must recover the locked row exactly."""
    design, _ = _design()
    summary = pd.read_csv(output_path(design, "summary_csv"))
    legacy = summary.loc[
        summary["origin_rule"].eq(hf.LEGACY_RULE)
        & summary["horizon_days"].eq(130)
    ]
    assert int(legacy["n_reference_blocks"].iloc[0]) == 7
    assert float(legacy["rank_p_value_floor"].iloc[0]) == pytest.approx(1 / 8)

    locked = pd.read_csv(
        config.path("data_processed") / "block_conformal_summary.csv"
    )
    locked_80 = locked.loc[locked["nominal_coverage"].eq(0.80)].iloc[0]
    legacy_80 = legacy.loc[legacy["level"].eq(0.80)].iloc[0]
    assert int(locked_80["n_independent_placebo_blocks"]) == int(
        legacy_80["n_reference_blocks"]
    )
    assert float(locked_80["radius"]) == pytest.approx(
        float(legacy_80["conformal_radius"]), rel=1e-9
    )
    assert float(locked_80["point_effect"]) == pytest.approx(
        float(legacy_80["treated_cumulative_loss"]), rel=1e-9
    )


@needs_outputs
def test_summary_covers_the_full_declared_grid():
    design, _ = _design()
    summary = pd.read_csv(output_path(design, "summary_csv"))
    expected = {
        (rule, int(horizon), float(level))
        for rule in design["origin_rules"]
        for horizon in design["horizon_grid_days"]
        for level in design["confidence_levels"]
    }
    actual = set(
        zip(summary["origin_rule"], summary["horizon_days"], summary["level"])
    )
    assert actual == expected


@needs_outputs
def test_written_summary_satisfies_every_structural_guard():
    design, _ = _design()
    summary = pd.read_csv(output_path(design, "summary_csv"))
    guard_summary(summary)
    assert not summary["five_percent_significance_claimed"].any()
    assert summary["n_reference_blocks"].le(summary["packing_upper_bound"]).all()
    for record in summary.to_dict("records"):
        k = int(record["n_reference_blocks"])
        assert record["rank_p_value_floor"] == pytest.approx(1 / (k + 1))
        assert record["maximum_attainable_coverage"] == pytest.approx(k / (k + 1))
        assert int(record["order_statistic_rank"]) == math.ceil(
            (k + 1) * record["level"]
        )


@needs_outputs
def test_blocks_table_never_crosses_the_locked_cutoff():
    design, _ = _design()
    blocks = pd.read_csv(
        output_path(design, "blocks_csv"), parse_dates=["test_start", "test_end"]
    )
    cutoff = pd.Timestamp(design["held_fixed"]["training_cutoff_exclusive"])
    reference = blocks.loc[~blocks["is_treated_window"].astype(bool)]
    assert reference["test_end"].lt(cutoff).all()
    treated = blocks.loc[blocks["is_treated_window"].astype(bool)]
    assert treated["test_start"].eq(cutoff).all()
    assert blocks["n_test_days"].eq(blocks["horizon_days"]).all()


@needs_outputs
def test_shared_windows_get_identical_statistics_across_rules():
    design, _ = _design()
    blocks = pd.read_csv(output_path(design, "blocks_csv"))
    reference = blocks.loc[~blocks["is_treated_window"].astype(bool)]
    spread = reference.groupby(["test_start", "test_end"])[
        "cumulative_throughput_loss"
    ].nunique()
    assert spread.eq(1).all()


@needs_outputs
def test_documentation_states_the_unbounded_levels_and_no_causal_claim():
    design, _ = _design()
    text = output_path(design, "documentation_markdown").read_text(encoding="utf-8")
    assert "unbounded" in text
    assert "NEEDS-VERIFY" in text
    assert "not identify a causal effect" in text
    assert "not an average treatment effect" in text
    for banned in (
        "significant at the 5% level",
        "statistically significant",
        "average treatment effect of",
        "causally identified",
    ):
        assert banned not in text


@needs_outputs
def test_manifest_matches_its_live_rebuild():
    written = json.loads(manifest_path().read_text(encoding="utf-8"))
    assert written == build_manifest()
    assert written["locked_primary_artifacts_mutated"] is False
    assert written["five_percent_significance_claimed"] is False
    assert written["audit_expectation_fully_reproduced"] is True
    assert written["verification_state"] == "NEEDS-VERIFY"
    assert written["core_run_all_dependency"] == "required_for_final_integration"


@needs_outputs
def test_manifest_output_hashes_match_the_files_on_disk():
    design, _ = _design()
    written = json.loads(manifest_path().read_text(encoding="utf-8"))
    for relative, expected in written["output_sha256"].items():
        assert sha256_file(config.ROOT / relative) == expected
