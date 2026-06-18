import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lngfreight.inference import (
    block_residual_sums,
    counterfactual_effect,
    empirical_p_value,
    fixed_train_post_fold,
    long_horizon_loss_interval,
    non_overlapping_fold_count,
    placebo_time_folds,
    post_treatment_fold,
    residual_quantiles,
    separation_ratio,
)


def _index():
    return pd.date_range("2022-01-01", periods=180, freq="D", name="date")


def test_post_treatment_fold_splits_at_cutoff():
    fold = post_treatment_fold(_index(), cutoff="2022-05-01")
    assert fold.train_end == pd.Timestamp("2022-04-30")
    assert fold.test_start == pd.Timestamp("2022-05-01")
    assert fold.test_start > fold.train_end


def test_fixed_train_post_fold_keeps_cutoff_and_post_start_separate():
    fold = fixed_train_post_fold(
        _index(),
        train_cutoff="2022-03-01",
        post_start="2022-04-15",
        name="donut",
    )
    assert fold.name == "donut"
    assert fold.train_end == pd.Timestamp("2022-02-28")
    assert fold.test_start == pd.Timestamp("2022-04-15")
    assert fold.test_start > fold.train_end


def test_fixed_train_post_fold_rejects_post_start_before_train_cutoff():
    with pytest.raises(ValueError, match="post_start"):
        fixed_train_post_fold(
            _index(),
            train_cutoff="2022-03-01",
            post_start="2022-02-15",
        )


def test_placebo_time_folds_stay_before_real_cutoff():
    folds = placebo_time_folds(
        _index(),
        cutoff="2022-06-01",
        horizon_days=14,
        initial_train_days=30,
        step_days=20,
    )
    assert folds
    for fold in folds:
        assert fold.train_end < fold.test_start
        assert fold.test_end < pd.Timestamp("2022-06-01")


def test_non_overlapping_fold_count_is_greedy():
    folds = placebo_time_folds(
        pd.date_range("2022-01-01", periods=260, freq="D", name="date"),
        cutoff="2022-09-01",
        horizon_days=30,
        initial_train_days=30,
        step_days=10,
    )
    assert len(folds) > non_overlapping_fold_count(folds)
    assert non_overlapping_fold_count(folds) == 7


def test_placebo_time_folds_fail_loudly_if_no_window_fits():
    with pytest.raises(ValueError, match="No placebo folds"):
        placebo_time_folds(
            _index(),
            cutoff="2022-02-01",
            horizon_days=30,
            initial_train_days=30,
        )


def test_counterfactual_effect_summarizes_loss():
    out = counterfactual_effect([8.0, 9.0, None], [10.0, 12.0, 99.0])
    assert out["n_days"] == 2
    assert out["observed_sum"] == pytest.approx(17.0)
    assert out["counterfactual_sum"] == pytest.approx(22.0)
    assert out["cumulative_gap_observed_minus_predicted"] == pytest.approx(-5.0)
    assert out["cumulative_throughput_loss"] == pytest.approx(5.0)
    assert out["mean_daily_throughput_loss"] == pytest.approx(2.5)


def test_empirical_p_value_uses_plus_one_correction():
    assert empirical_p_value(10.0, [1.0, 5.0, 12.0], "greater") == pytest.approx(0.5)
    assert empirical_p_value(10.0, [-11.0, 2.0, 3.0], "two-sided") == pytest.approx(0.5)


def test_empirical_p_value_rejects_bad_alternative():
    with pytest.raises(ValueError, match="alternative"):
        empirical_p_value(1.0, [1.0], "sideways")


def test_separation_ratio_handles_zero_reference():
    assert separation_ratio(10.0, 2.0) == pytest.approx(5.0)
    assert pd.isna(separation_ratio(10.0, 0.0))


def test_residual_quantiles_are_empirical():
    lo, hi = residual_quantiles([-2, -1, 0, 1, 2], alpha=0.2)
    assert lo == pytest.approx(-1.6)
    assert hi == pytest.approx(1.6)


def test_block_residual_sums_are_deterministic_and_correct_shape():
    a = block_residual_sums([1, 2, 3], horizon=5, block_length=2, n_draws=4, seed=7)
    b = block_residual_sums([1, 2, 3], horizon=5, block_length=2, n_draws=4, seed=7)
    assert len(a) == 4
    assert (a == b).all()


def test_block_residual_sums_reject_bad_inputs():
    with pytest.raises(ValueError, match="horizon"):
        block_residual_sums([1], horizon=0)


def test_long_horizon_interval_centers_on_point_loss_and_is_symmetric():
    # Symmetric, mean-zero errors -> interval centered on the point loss.
    errors = [-100.0, -50.0, 0.0, 50.0, 100.0]
    out = long_horizon_loss_interval(5000.0, errors, alpha=0.2)
    assert out["pre_period_mean_error_centered_out"] == pytest.approx(0.0)
    # 10th/90th percentiles of centered errors are -80/+80.
    assert out["interval_lower"] == pytest.approx(4920.0)
    assert out["interval_upper"] == pytest.approx(5080.0)
    assert out["n_horizon_windows"] == 5


def test_long_horizon_interval_removes_pre_period_bias():
    # All errors shifted by +200; the bias is centered out, not propagated.
    errors = [100.0, 150.0, 200.0, 250.0, 300.0]
    out = long_horizon_loss_interval(5000.0, errors, alpha=0.2)
    assert out["pre_period_mean_error_centered_out"] == pytest.approx(200.0)
    assert (out["interval_lower"] + out["interval_upper"]) / 2 == pytest.approx(5000.0)


def test_long_horizon_interval_wider_errors_widen_band():
    narrow = long_horizon_loss_interval(5000.0, [-10, -5, 0, 5, 10], alpha=0.2)
    wide = long_horizon_loss_interval(5000.0, [-1000, -500, 0, 500, 1000], alpha=0.2)
    assert wide["interval_width"] > narrow["interval_width"]


def test_long_horizon_interval_excludes_zero_flag_and_bad_inputs():
    out = long_horizon_loss_interval(5000.0, [-100, 0, 100], alpha=0.2)
    assert out["excludes_zero"] is True
    with pytest.raises(ValueError, match="alpha"):
        long_horizon_loss_interval(1.0, [1.0, 2.0], alpha=1.0)
    with pytest.raises(ValueError, match="finite"):
        long_horizon_loss_interval(1.0, [float("nan")])
