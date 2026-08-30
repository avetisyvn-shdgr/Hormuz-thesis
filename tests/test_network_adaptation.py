"""Contract tests for the restricted network-adaptation experiment."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from experiments.network_adaptation.inference import (
    global_mean_test,
    scale_columns,
    synchronized_circular_mbb,
)
from experiments.network_adaptation.protocol import load_protocol


def test_protocol_retains_restricted_exploratory_geometry():
    protocol = load_protocol()
    assert protocol.status == "exploratory_retrospective_restriction"
    assert protocol.horizon == 130
    assert protocol.event_end == pd.Timestamp("2026-07-07")
    assert protocol.primary_model == "chronos2_univariate"
    assert protocol.robustness_model == "ar_lag1_7"
    assert len(protocol.primary_keys) == 5
    assert len(protocol.control_keys) == 10
    assert not set(protocol.primary_corridors) & set(protocol.context_corridors)


def test_synchronized_mbb_is_deterministic_and_preserves_joint_columns():
    base = np.arange(60, dtype="float64")
    residuals = pd.DataFrame({"a": base, "b": 2.0 * base})
    first = synchronized_circular_mbb(
        residuals, horizon=20, block_length=7, n_draws=100, seed=42
    )
    second = synchronized_circular_mbb(
        residuals, horizon=20, block_length=7, n_draws=100, seed=42
    )
    pd.testing.assert_frame_equal(first, second)
    assert np.allclose(first["b"], 2.0 * first["a"])


def test_synchronized_mbb_rejects_missing_values():
    residuals = pd.DataFrame({"a": [1.0, np.nan, 2.0]})
    with pytest.raises(ValueError, match="finite and complete"):
        synchronized_circular_mbb(
            residuals, horizon=2, block_length=2, n_draws=10, seed=1
        )


def test_scale_columns_requires_positive_matching_denominators():
    draws = pd.DataFrame({"a": [2.0, 4.0], "b": [3.0, 6.0]})
    scaled = scale_columns(draws, pd.Series({"a": 2.0, "b": 3.0}))
    assert scaled.iloc[0].to_dict() == {"a": 1.0, "b": 1.0}
    with pytest.raises(ValueError, match="finite, positive"):
        scale_columns(draws, pd.Series({"a": 2.0, "b": 0.0}))


def test_global_mean_test_uses_joint_draws_and_plus_one_correction():
    observed = pd.Series({"a": 2.0, "b": 2.0})
    draws = pd.DataFrame({"a": [0.0, 1.0, 3.0], "b": [0.0, 1.0, 3.0]})
    result = global_mean_test(observed, draws)
    assert result["observed_global_statistic"] == 2.0
    assert result["one_sided_bootstrap_p_value"] == pytest.approx(0.5)
    assert result["n_joint_resamples"] == 3


def test_executed_event_forecast_artifact_has_frozen_geometry():
    protocol = load_protocol()
    frame = pd.read_csv(
        protocol.outputs["event_forecasts"], parse_dates=["origin", "date"]
    )
    assert len(frame) == 2 * 28 * 5 * 130
    assert frame["origin"].eq(protocol.cutoff).all()
    assert frame["date"].min() == protocol.cutoff
    assert frame["date"].max() == protocol.event_end
    assert not frame.duplicated(
        ["model", "portname", "vessel_class", "date"]
    ).any()
    truth = frame.pivot(
        index=["portname", "vessel_class", "date"], columns="model", values="y_true"
    )
    assert np.allclose(
        truth[protocol.primary_model], truth[protocol.robustness_model]
    )


def test_executed_inference_artifact_separates_families_and_context():
    protocol = load_protocol()
    frame = pd.read_csv(protocol.outputs["inference"])
    assert len(frame) == 2 * 3 * (5 + 10 + 3)
    assert set(frame["block_length_days"]) == {7, 14, 28}
    tested = frame["family"].ne("context_descriptive_not_tested")
    assert frame.loc[tested, "romano_wolf_p_value"].between(0, 1).all()
    assert frame.loc[~tested, "romano_wolf_p_value"].isna().all()
    primary = frame.loc[
        frame["family"].eq("restricted_tanker_adaptation")
        & frame["block_length_days"].eq(protocol.block_length)
    ]
    assert primary.groupby("model").size().eq(5).all()


def test_protocol_carries_the_declared_chronos_context_length():
    protocol = load_protocol()
    assert protocol.primary_context_length == 2048


def test_specification_sensitivity_artifact_pairs_two_training_windows():
    protocol = load_protocol()
    frame = pd.read_csv(protocol.outputs["specification_sensitivity"])
    assert list(frame.columns) == [
        "spec", "train_start", "context_length", "model", "observed_sum",
        "counterfactual_sum", "cumulative_gap", "pct_below_counterfactual",
    ]
    assert len(frame) == 4
    assert not frame.duplicated(["spec", "model"]).any()
    assert set(frame["model"]) == {protocol.primary_model, protocol.robustness_model}
    assert frame.groupby("spec").size().eq(2).all()

    # The two specifications must score the same event, or the comparison is
    # not a specification sensitivity but a different question.
    assert frame["observed_sum"].nunique() == 1
    assert frame["observed_sum"].iloc[0] == 529.0

    # Chronos never sees more than its declared context; AR sees everything.
    chronos = frame.loc[frame["model"].eq(protocol.primary_model)]
    assert chronos["context_length"].le(protocol.primary_context_length).all()

    # The claim the write-up rests on: the shortfall is stable even though the
    # model-versus-model difference is not.
    assert frame["pct_below_counterfactual"].between(92.0, 93.5).all()
    gaps = frame.set_index(["spec", "model"])["cumulative_gap"]
    legacy = gaps["legacy_admission_protocol"]
    expanded = gaps["expanded_history_event_panel"]
    assert legacy[protocol.primary_model] < legacy[protocol.robustness_model]
    assert expanded[protocol.primary_model] > expanded[protocol.robustness_model]


def test_cape_drift_artifact_covers_every_corridor_and_origin():
    protocol = load_protocol()
    frame = pd.read_csv(protocol.outputs["cape_drift"])
    assert len(frame) == 2 * len(protocol.primary_corridors) * 8
    assert set(frame["portname"]) == set(protocol.primary_corridors)
    assert set(frame["model"]) == {protocol.primary_model, protocol.robustness_model}
    assert frame["n_days"].eq(protocol.horizon).all()
    # Residual calibration must stay strictly pre-event.
    assert pd.to_datetime(frame["scored_end"]).max() < protocol.cutoff


def test_cape_regime_break_is_the_reason_cape_is_demoted():
    """If this stops holding, the chapter's demotion has to be revisited."""
    import json

    protocol = load_protocol()
    summary = json.loads(
        protocol.outputs["cape_drift_manifest"].read_text(encoding="utf-8")
    )
    assert summary["verdict"] == "demoted_to_context"
    assert summary["cape_is_the_largest_onset_shift"]
    shifts = summary["cape_onset_shift"]
    assert min(abs(value) for value in shifts.values()) > 4 * summary[
        "largest_non_cape_onset_shift"
    ]
    # The two models move in opposite directions at the onset; that is the
    # disagreement the chapter attributes to the regime break, not to model
    # quality.
    assert shifts[protocol.primary_model] * shifts[protocol.robustness_model] < 0


def test_the_one_losing_origin_is_a_cape_artifact():
    import json

    protocol = load_protocol()
    losing = json.loads(
        protocol.outputs["cape_drift_manifest"].read_text(encoding="utf-8")
    )["losing_origin_decomposition"]
    assert losing["reduction_all_series"] < 0
    assert losing["reduction_excluding_cape"] > 0.10
    assert losing["worst_series"].startswith("Cape of Good Hope")


def test_validation_record_carries_the_cape_demotion():
    import json

    protocol = load_protocol()
    validation = json.loads(
        protocol.outputs["validation"].read_text(encoding="utf-8")
    )
    assert any(
        "Cape of Good Hope is context, not corroboration" in caveat
        for caveat in validation["required_caveats"]
    )


def test_weighted_global_test_reduces_to_the_equal_weighted_one():
    observed = pd.Series({"a": 2.0, "b": 4.0})
    draws = pd.DataFrame({"a": [0.0, 1.0, 3.0], "b": [1.0, 2.0, 5.0]})
    equal = global_mean_test(observed, draws)
    explicit = global_mean_test(observed, draws, pd.Series({"a": 7.0, "b": 7.0}))
    assert equal["observed_global_statistic"] == pytest.approx(
        explicit["observed_global_statistic"]
    )
    assert equal["one_sided_bootstrap_p_value"] == pytest.approx(
        explicit["one_sided_bootstrap_p_value"]
    )
    # A weight that concentrates on one series must reproduce that series alone.
    single = global_mean_test(observed, draws, pd.Series({"a": 1.0, "b": 1e-12}))
    assert single["observed_global_statistic"] == pytest.approx(2.0, abs=1e-6)


def test_global_test_rejects_non_positive_or_missing_weights():
    observed = pd.Series({"a": 1.0, "b": 1.0})
    draws = pd.DataFrame({"a": [0.0, 1.0], "b": [0.0, 1.0]})
    for bad in (pd.Series({"a": 1.0, "b": 0.0}), pd.Series({"a": 1.0})):
        with pytest.raises(ValueError, match="finite and positive"):
            global_mean_test(observed, draws, bad)


def test_control_robustness_covers_every_declared_variant():
    protocol = load_protocol()
    frame = pd.read_csv(protocol.outputs["control_robustness"])
    blocks = (protocol.block_length, *protocol.sensitivity_block_lengths)
    assert set(frame["block_length_days"]) == set(blocks)
    assert set(frame["weighting"]) == set(protocol.control_weighting_schemes)

    controls = frame.loc[frame["family"].eq("non_tanker_negative_controls")]
    # Three weightings + one eligibility variant + ten leave-one-outs, per model
    # and block length.
    assert len(controls) == 2 * len(blocks) * (3 + 1 + 10)
    loo = controls.loc[controls["variant"].eq("leave_one_control_out")]
    assert loo["n_series"].eq(9).all()
    assert loo.groupby(["model", "block_length_days"])["dropped_control"].nunique().eq(10).all()

    # The full family is retained and reported regardless of what the other
    # variants say; the plan requires that explicitly.
    full = controls.loc[
        controls["variant"].eq("full_ten_control_family") & controls["weighting"].eq("equal")
    ]
    assert full["n_series"].eq(10).all()

    # The eligibility rule is volume-based and pre-event, never post-event.
    eligible = controls.loc[controls["variant"].eq("volume_eligible_controls")]
    assert eligible["n_series"].eq(7).all()
    assert eligible["minimum_pre_event_daily_transits"].ge(
        protocol.control_minimum_daily_transits
    ).all()


def test_control_family_has_power_and_chronos_specificity_holds():
    import json

    protocol = load_protocol()
    summary = json.loads(
        protocol.outputs["control_robustness_manifest"].read_text(encoding="utf-8")
    )
    assert summary["declared_before_running"]["minimum_pre_event_daily_transits"] == 5.0
    assert summary["declared_before_running"]["no_post_event_removal"]
    # If the control family could not flag a tanker-sized movement it would not
    # be a falsification test, and section 5.3 would have to be rewritten.
    assert summary["control_family_can_falsify"]
    above, total = summary["chronos_control_cells_above_0_05"]
    assert total == 42 and above >= 41


def test_the_model_specificity_contrast_is_an_equal_weighting_artifact():
    """The chapter withdraws a methodological claim on the strength of this."""
    import json

    protocol = load_protocol()
    summary = json.loads(
        protocol.outputs["control_robustness_manifest"].read_text(encoding="utf-8")
    )
    assert summary["ar_control_failure_is_equal_weighting_only"]
    assert summary["tanker_family_global_is_weighting_sensitive"]
    assert set(summary["controls_excluded_by_volume_rule"]) == {
        "n_roro::Cape of Good Hope",
        "n_roro::Panama Canal",
        "n_roro::Yucatan Channel",
    }


def test_all_corridor_ranking_covers_every_chokepoint_and_stays_labelled():
    protocol = load_protocol()
    frame = pd.read_csv(protocol.outputs["all_corridor_ranking"])
    blocks = (protocol.block_length, *protocol.sensitivity_block_lengths)
    assert len(frame) == 2 * len(blocks) * 28
    assert frame.groupby(["model", "block_length_days"])["portname"].nunique().eq(28).all()
    assert frame["vessel_class"].eq(protocol.primary_class).all()
    assert frame["family_size"].eq(28).all()
    # The label is the point: this run must never read as confirmatory.
    assert frame["status"].eq("retrospective_disclosure_not_confirmatory").all()
    assert frame.loc[frame["in_restricted_five"]].groupby(
        ["model", "block_length_days"]
    ).size().eq(5).all()
    assert frame.loc[frame["is_treated_anchor"], "portname"].eq("Strait of Hormuz").all()


def test_widening_the_family_keeps_panama_and_yucatan_and_drops_the_rest():
    """The chapter rests on this pair surviving the harshest available correction."""
    import json

    protocol = load_protocol()
    frame = pd.read_csv(protocol.outputs["all_corridor_ranking"])
    cells = frame.groupby(["model", "block_length_days"]).ngroups
    flagged = frame.loc[frame["romano_wolf_p_value"].lt(0.05)]
    survivors = flagged.groupby("portname").size()
    always = set(survivors[survivors.eq(cells)].index)
    assert {"Panama Canal", "Yucatan Channel"} <= always

    # Gibraltar and Malacca are in the restricted five and clear nothing.
    assert not flagged["portname"].isin({"Gibraltar Strait", "Malacca Strait"}).any()

    summary = json.loads(
        protocol.outputs["all_corridor_manifest"].read_text(encoding="utf-8")
    )
    assert summary["status"] == "retrospective_disclosure_not_confirmatory"
    assert summary["family_size"] == 28
    # The treated anchor must sit at the bottom of a one-sided positive ranking.
    assert summary["treated_anchor_rank_from_bottom"] == 1
    # Corridors outside the restricted five do clear the threshold; concealing
    # that is exactly what this run exists to prevent.
    assert summary["corridors_flagged_outside_the_restricted_five"]


def test_the_network_as_a_whole_does_not_move():
    protocol = load_protocol()
    frame = pd.read_csv(protocol.outputs["all_corridor_global_tests"])
    assert set(frame["variant"]) == {"all_28_corridors", "volume_eligible_corridors"}
    assert frame["one_sided_bootstrap_p_value"].gt(0.05).all()
