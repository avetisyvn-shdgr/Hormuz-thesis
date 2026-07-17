"""Contract tests for the frozen corridor-panel admission gate."""
from dataclasses import replace

import pandas as pd
import pytest


from lngfreight.corridor_admission import (
    CorridorAdmissionProtocol,
    load_corridor_admission_protocol,
    panel_admission_test,
)
from lngfreight.spatial import wide_chokepoint_panel
from lngfreight.validation import rolling_origin_splits


def _protocol() -> CorridorAdmissionProtocol:
    return CorridorAdmissionProtocol(
        status="test",
        history_start=pd.Timestamp("2022-01-01"),
        cutoff=pd.Timestamp("2022-04-01"),
        horizon_days=10,
        minimum_scored_days_per_fold=8,
        expected_scored_folds=2,
        shared_test_origins=(pd.Timestamp("2022-02-01"), pd.Timestamp("2022-03-01")),
        lower_quantile=0.1,
        upper_quantile=0.9,
        nominal_coverage=0.8,
        baseline_model="ar_lag1_7",
        minimum_median_relative_mase_improvement=0.05,
        minimum_fraction_corridors_non_worse_mase=0.60,
        maximum_median_absolute_calibration_error=0.10,
        calibration_noninferiority_margin=0.02,
        minimum_corridor_empirical_coverage=0.70,
        minimum_fraction_corridors_meeting_coverage=0.80,
        require_every_target_family_to_pass=True,
        eligible_corridors={"count": ("a", "b"), "capacity": ("a", "b")},
    )


def _scores(model: str, mase: float, coverage: float) -> pd.DataFrame:
    rows = []
    protocol = _protocol()
    for target, corridors in protocol.eligible_corridors.items():
        for corridor in corridors:
            for i, origin in enumerate(protocol.shared_test_origins, start=1):
                rows.append({
                    "model": model,
                    "target": target,
                    "corridor": corridor,
                    "fold": f"fold_{i:02d}",
                    "train_start": protocol.history_start,
                    "train_end": origin - pd.Timedelta(days=1),
                    "test_start": origin,
                    "test_end": origin + pd.Timedelta(days=9),
                    "n_scored": 10,
                    "mase": mase,
                    "empirical_coverage": coverage,
                    "nominal_coverage": 0.8,
                })
    return pd.DataFrame(rows)


def test_repository_protocol_is_valid_and_exploratory():
    protocol = load_corridor_admission_protocol()
    assert protocol.status == "exploratory_no_supervisor_signoff"
    assert protocol.nominal_coverage == pytest.approx(0.8)
    assert len(protocol.shared_test_origins) == 23
    assert len(protocol.eligible_corridors["n_tanker"]) == 28
    assert len(protocol.eligible_corridors["capacity_tanker"]) == 20


def test_repository_protocol_matches_pinned_panel_and_fold_policy():
    protocol = load_corridor_admission_protocol()
    for target, configured_corridors in protocol.eligible_corridors.items():
        panel = wide_chokepoint_panel(target)
        folds = rolling_origin_splits(panel.index)
        scored_folds = folds[15:]
        assert tuple(fold.test_start for fold in scored_folds) == protocol.shared_test_origins

        eligible = tuple(
            corridor
            for corridor in panel.columns
            if min(
                int(panel[corridor].iloc[fold.test_idx].notna().sum())
                for fold in scored_folds
            )
            >= protocol.minimum_scored_days_per_fold
        )
        assert eligible == configured_corridors


def test_panel_gate_admits_only_when_both_target_families_pass():
    protocol = _protocol()
    candidate = _scores("candidate", mase=0.90, coverage=0.78)
    baseline = _scores("ar_lag1_7", mase=1.00, coverage=0.75)
    corridor, targets, overall = panel_admission_test(candidate, baseline, protocol)
    assert len(corridor) == 4
    assert targets["target_admitted"].all()
    assert overall["admitted"] is True

    candidate.loc[candidate["target"].eq("capacity"), "mase"] = 1.00
    _, targets2, overall2 = panel_admission_test(candidate, baseline, protocol)
    assert not targets2.set_index("target").at["capacity", "target_admitted"]
    assert overall2["admitted"] is False


def test_calibration_cannot_cancel_across_corridors():
    protocol = _protocol()
    candidate = _scores("candidate", mase=0.90, coverage=0.80)
    baseline = _scores("ar_lag1_7", mase=1.00, coverage=0.75)
    candidate.loc[candidate["corridor"].eq("a"), "empirical_coverage"] = 0.60
    candidate.loc[candidate["corridor"].eq("b"), "empirical_coverage"] = 1.00
    _, targets, overall = panel_admission_test(candidate, baseline, protocol)
    assert (targets["candidate_median_absolute_calibration_error"] == 0.20).all()
    assert not targets["calibration_pass"].any()
    assert overall["admitted"] is False


def test_gate_rejects_fold_mismatch_and_model_specific_dropping():
    protocol = _protocol()
    candidate = _scores("candidate", mase=0.90, coverage=0.78)
    baseline = _scores("ar_lag1_7", mase=1.00, coverage=0.75)
    with pytest.raises(ValueError, match="frozen targets"):
        panel_admission_test(candidate.iloc[:-1], baseline, protocol)

    candidate.loc[0, "n_scored"] = 9
    with pytest.raises(ValueError, match="n_scored must match"):
        panel_admission_test(candidate, baseline, protocol)


def test_gate_rejects_post_cutoff_rows_and_wrong_interval_level():
    protocol = _protocol()
    candidate = _scores("candidate", mase=0.90, coverage=0.78)
    baseline = _scores("ar_lag1_7", mase=1.00, coverage=0.75)
    candidate.loc[0, "test_end"] = protocol.cutoff
    with pytest.raises(ValueError, match="cutoff"):
        panel_admission_test(candidate, baseline, protocol)

    candidate = _scores("candidate", mase=0.90, coverage=0.78)
    candidate["nominal_coverage"] = 0.95
    with pytest.raises(ValueError, match="common nominal"):
        panel_admission_test(candidate, baseline, protocol)


def test_gate_rejects_wrong_history_or_horizon_geometry():
    protocol = _protocol()
    candidate = _scores("candidate", mase=0.90, coverage=0.78)
    baseline = _scores("ar_lag1_7", mase=1.00, coverage=0.75)
    candidate.loc[0, "train_start"] = pd.Timestamp("2022-01-02")
    with pytest.raises(ValueError, match="history start"):
        panel_admission_test(candidate, baseline, protocol)

    candidate = _scores("candidate", mase=0.90, coverage=0.78)
    candidate.loc[0, "test_end"] -= pd.Timedelta(days=1)
    with pytest.raises(ValueError, match="test horizon"):
        panel_admission_test(candidate, baseline, protocol)


def test_threshold_boundary_is_inclusive_and_output_is_deterministic():
    protocol = _protocol()
    candidate = _scores("candidate", mase=0.95, coverage=0.70)
    # Candidate sits exactly at the 5% MASE, 70% coverage, 10-point absolute
    # calibration and 2-point calibration-noninferiority boundaries.
    baseline = _scores("ar_lag1_7", mase=1.00, coverage=0.72)
    first = panel_admission_test(candidate.sample(frac=1, random_state=1), baseline, protocol)
    second = panel_admission_test(candidate.sample(frac=1, random_state=2), baseline, protocol)
    pd.testing.assert_frame_equal(first[0], second[0])
    pd.testing.assert_frame_equal(first[1], second[1])
    assert first[2] == second[2]
    assert first[2]["admitted"] is True


def test_protocol_rejects_duplicate_origins():
    protocol = _protocol()
    broken = replace(
        protocol,
        shared_test_origins=(pd.Timestamp("2022-02-01"), pd.Timestamp("2022-02-01")),
    )
    candidate = _scores("candidate", mase=0.90, coverage=0.78)
    baseline = _scores("ar_lag1_7", mase=1.00, coverage=0.75)
    with pytest.raises(ValueError, match="origins must be unique"):
        panel_admission_test(candidate, baseline, broken)
