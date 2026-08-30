from __future__ import annotations

import numpy as np
import pandas as pd

from experiments.panel_bakeoff.models import (
    interactive_fixed_effects,
    nuclear_norm_completion,
    recursive_ar17,
    seasonal_naive,
)
from experiments.panel_bakeoff.protocol import (
    EXPLICIT_CLASSES,
    composition_wide,
    folds,
    load_raw_panel,
)
from experiments.panel_bakeoff.pretraining_contamination import (
    MODEL_RELEASE,
    OUTPUT_DIR,
)
from experiments.panel_bakeoff.summarize import add_sequential_common_intervals


def test_raw_panel_has_five_nonoverlapping_classes_and_exact_aggregates():
    frame = load_raw_panel()
    assert len(EXPLICIT_CLASSES) == 5
    np.testing.assert_array_equal(frame[list(EXPLICIT_CLASSES)].sum(axis=1), frame["n_total"])
    np.testing.assert_array_equal(frame[list(EXPLICIT_CLASSES[:-1])].sum(axis=1), frame["n_cargo"])
    panel = composition_wide(frame)
    assert panel.shape == (2750, 140)


def test_frozen_fold_geometry_is_disjoint_and_pre_event():
    panel = composition_wide(load_raw_panel())
    built = folds(panel.index)
    long_folds = [fold for fold in built if fold.horizon == 130]
    assert len(long_folds) == 8
    for left, right in zip(long_folds, long_folds[1:]):
        assert left.test_dates[-1] < right.test_dates[0]
    assert long_folds[-1].test_dates[-1] < pd.Timestamp("2026-02-28")


def test_forecasters_return_finite_nonnegative_horizons():
    rng = np.random.default_rng(7)
    train = 20 + np.sin(np.arange(500) * 2 * np.pi / 7) + rng.normal(0, 0.2, 500)
    for prediction in (seasonal_naive(train, 30), recursive_ar17(train, 30)):
        assert prediction.shape == (30,)
        assert np.isfinite(prediction).all()
        assert (prediction >= 0).all()


def test_factor_estimators_recover_a_low_rank_heldout_block():
    rng = np.random.default_rng(11)
    loadings = rng.normal(size=(12, 2))
    train = np.dot(rng.normal(size=(300, 2)), loadings.T) + 20
    future = np.dot(rng.normal(size=(30, 2)), loadings.T) + 20
    missing = np.zeros(12, dtype=bool)
    missing[:3] = True
    ife = interactive_fixed_effects(train, future, missing, rank=2)
    mc, iterations, rank = nuclear_norm_completion(train, future, missing, 0.02)
    assert np.mean(np.abs(ife - future[:, :3])) < 1e-8
    assert np.mean(np.abs(mc - future[:, :3])) < 0.5
    assert iterations > 0
    assert rank > 0


def test_common_interval_calibration_never_uses_current_or_future_fold_errors():
    rows = []
    for fold, error in (("fold_01", 1.0), ("fold_02", 100.0), ("fold_03", 200.0)):
        for port in ("a", "b"):
            rows.append(
                {
                    "model": "m",
                    "panel": "p",
                    "horizon": 1,
                    "vessel_class": "c",
                    "fold": fold,
                    "lead": 1,
                    "portname": port,
                    "y_true": error,
                    "y_pred": 0.0,
                    "mase_scale": 1.0,
                }
            )
    framed = add_sequential_common_intervals(pd.DataFrame(rows))
    assert framed.loc[framed.fold == "fold_01", "common_q"].isna().all()
    assert set(framed.loc[framed.fold == "fold_02", "common_q"]) == {1.0}
    assert set(framed.loc[framed.fold == "fold_03", "common_q"]) == {100.0}


def test_event_window_lies_entirely_after_the_chronos_release():
    """The shortfall estimate must carry no pretraining-overlap risk at all."""
    import json

    protocol = json.loads(
        (OUTPUT_DIR / "chronos_pretraining_contamination.json").read_text(encoding="utf-8")
    )
    assert protocol["chronos2_release_date"] == "2025-10-20"
    assert MODEL_RELEASE < pd.Timestamp("2026-02-28")


def test_chronos_advantage_is_not_concentrated_in_the_earliest_origins():
    """The signature a contaminated corpus would leave is a decaying advantage."""
    table = pd.read_csv(OUTPUT_DIR / "chronos_by_origin_advantage.csv")
    primary = table.loc[table["panel"].eq("composition_28x5")]
    assert len(primary) == 16
    assert set(primary["fold"]) == {f"fold_{n:02d}" for n in range(1, 9)}

    latest = primary.loc[primary["fold"].eq("fold_08")]
    assert len(latest) == 2
    # The latest origin keeps a positive advantage at both horizons, and its
    # clustered interval excludes zero. If this ever fails, the generalisable
    # accuracy claim has to be re-hedged, not the test relaxed.
    assert latest["mase_reduction"].gt(0).all()
    assert latest["cluster_bootstrap_ci_lower"].gt(0).all()

    # Only the latest origin's long window reaches past the release date.
    reaching = primary.loc[primary["days_after_model_release"].gt(0)]
    assert set(reaching["fold"]) == {"fold_08"}
