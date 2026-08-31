"""Leakage-safety tests for the rolling-origin validation harness
(validation.py). These guard the two promises the modeling phase makes:

  1. chronological order - every test fold lies strictly AFTER its train window
                           (no future -> past leakage; CLAUDE.md rule 5).
  2. pre-treatment only  - no fold ever reaches the treatment cutoff, so the
                           disruption regime can never enter training/validation.

Plus the mechanical contract: expanding train grows while sliding stays fixed,
max_folds is honoured, and a too-short history fails LOUDLY (CLAUDE.md rule 1)
rather than silently returning zero folds.

All tests are NO-network / NO-key: rolling_origin_splits is a pure function over
an in-memory DatetimeIndex + an explicit settings dict. Run: pytest -q
"""

import numpy as np
import pandas as pd
import pytest


from hormuz_throughput.validation import (
    rolling_origin_splits,
    resolve_cutoff,
    summary,
)


def _settings(scheme="expanding", initial=100, horizon=20, step=20,
              sliding=100, max_folds=None, cutoff="2024-01-01"):
    return {
        "study_window": {
            "primary_treatment_cutoff": "2024-01-01",
            "treatment_candidates": {
                "a": "2024-01-01", "b": "2024-02-01"}},
        "modeling": {"validation": {
            "scheme": scheme, "initial_train_days": initial,
            "horizon_days": horizon, "step_days": step,
            "sliding_train_days": sliding, "max_folds": max_folds,
            "cutoff": cutoff}},
    }


def _index(start="2022-01-01", periods=800):
    return pd.date_range(start, periods=periods, freq="D", name="date")


def test_test_fold_strictly_after_train():
    folds = rolling_origin_splits(_index(), _settings())
    assert folds, "expected at least one fold"
    for f in folds:
        assert f.test_start > f.train_end
        assert np.intersect1d(f.train_idx, f.test_idx).size == 0


def test_no_fold_crosses_treatment_cutoff():
    s = _settings(cutoff="2024-01-01")
    idx = _index()
    folds = rolling_origin_splits(idx, s)
    cut = pd.Timestamp("2024-01-01")
    for f in folds:
        assert f.test_end < cut
        assert f.train_end < cut
    post = np.flatnonzero(idx >= cut)
    for f in folds:
        assert np.intersect1d(f.test_idx, post).size == 0
        assert np.intersect1d(f.train_idx, post).size == 0


def test_cutoff_auto_uses_locked_primary_cutoff():
    s = _settings(cutoff="auto")
    assert resolve_cutoff(s) == pd.Timestamp("2024-01-01")


def test_milestone_dates_cannot_change_locked_primary_cutoff():
    s = _settings(cutoff="auto")
    s["study_window"]["primary_treatment_cutoff"] = "2024-01-15"
    s["study_window"]["treatment_candidates"]["a"] = "2023-12-01"
    assert resolve_cutoff(s) == pd.Timestamp("2024-01-15")


def test_cutoff_auto_requires_locked_primary_cutoff():
    s = _settings(cutoff="auto")
    del s["study_window"]["primary_treatment_cutoff"]
    with pytest.raises(ValueError, match="primary_treatment_cutoff"):
        resolve_cutoff(s)


def test_expanding_train_grows():
    folds = rolling_origin_splits(_index(), _settings(scheme="expanding"))
    sizes = [len(f.train_idx) for f in folds]
    assert sizes == sorted(sizes)
    assert sizes[-1] > sizes[0]
    assert len({f.train_start for f in folds}) == 1


def test_sliding_train_fixed_length():
    folds = rolling_origin_splits(
        _index(), _settings(scheme="sliding", sliding=100))
    sizes = {len(f.train_idx) for f in folds}
    assert sizes == {100}


def test_max_folds_caps_count():
    folds = rolling_origin_splits(_index(), _settings(max_folds=2))
    assert len(folds) == 2


def test_step_controls_origin_advance():
    folds = rolling_origin_splits(_index(), _settings(step=20))
    starts = [f.test_start for f in folds]
    gaps = {(b - a).days for a, b in zip(starts, starts[1:])}
    assert gaps == {20}


def test_too_short_history_raises():
    short = pd.date_range("2023-11-12", periods=50, freq="D", name="date")
    with pytest.raises(ValueError, match="too short"):
        rolling_origin_splits(short, _settings(initial=100, horizon=20))


def test_no_pretreatment_data_raises():
    idx = pd.date_range("2024-02-01", periods=100, freq="D", name="date")
    with pytest.raises(ValueError, match="No data before"):
        rolling_origin_splits(idx, _settings(cutoff="2024-01-01"))


def test_bad_scheme_raises():
    with pytest.raises(ValueError, match="scheme"):
        rolling_origin_splits(_index(), _settings(scheme="kfold"))


def test_nonpositive_window_raises():
    with pytest.raises(ValueError, match="must be > 0"):
        rolling_origin_splits(_index(), _settings(horizon=0))


def test_unsorted_index_is_rejected_before_positional_folds_are_built():
    unsorted = _index().to_series().sample(frac=1, random_state=7).index
    with pytest.raises(ValueError, match="chronologically sorted"):
        rolling_origin_splits(unsorted, _settings())


def test_summary_shape_matches_folds():
    folds = rolling_origin_splits(_index(), _settings())
    tbl = summary(folds)
    assert len(tbl) == len(folds)
    assert list(tbl.columns) == ["fold", "train_start", "train_end",
                                 "n_train", "test_start", "test_end", "n_test"]
