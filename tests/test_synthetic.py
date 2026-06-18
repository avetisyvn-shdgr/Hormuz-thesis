import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from lngfreight.synthetic import (  # noqa: E402
    fit_simplex_weights,
    post_pre_ratio,
    project_to_simplex,
    rmspe,
    scale_by_pre_period_mean,
)
from run_synthetic_control import _clean_donor_slugs  # noqa: E402


def test_project_to_simplex_is_nonnegative_and_sums_to_one():
    out = project_to_simplex(np.array([0.2, -4.0, 3.0]))
    assert (out >= 0).all()
    assert out.sum() == pytest.approx(1.0)


def test_fit_simplex_weights_recovers_simple_average():
    donors = pd.DataFrame({
        "a": [1.0, 2.0, 3.0, 4.0],
        "b": [3.0, 4.0, 5.0, 6.0],
    })
    y = 0.5 * donors["a"] + 0.5 * donors["b"]

    weights = fit_simplex_weights(y, donors)

    assert weights.sum() == pytest.approx(1.0)
    assert (weights >= 0).all()
    assert weights["a"] == pytest.approx(0.5, abs=1e-4)
    assert weights["b"] == pytest.approx(0.5, abs=1e-4)


def test_scale_by_pre_period_mean_uses_only_pre_rows():
    wide = pd.DataFrame({
        "x": [2.0, 4.0, 100.0],
        "y": [10.0, 10.0, 10.0],
    })
    pre_mask = pd.Series([True, True, False], index=wide.index)

    scaled, scale = scale_by_pre_period_mean(wide, pre_mask)

    assert scale["x"] == pytest.approx(3.0)
    assert scaled.loc[2, "x"] == pytest.approx(100.0 / 3.0)


def test_rmspe_and_ratio_handle_basic_cases():
    assert rmspe([1, 2, None], [2, 2, 99]) == pytest.approx(np.sqrt(0.5))
    assert post_pre_ratio(4.0, 2.0) == pytest.approx(2.0)
    assert np.isnan(post_pre_ratio(4.0, 0.0))


def test_clean_donors_exclude_contaminated_and_treated():
    meta = pd.DataFrame([
        {"slug": "strait_of_hormuz", "contamination_flag": False},
        {"slug": "panama_canal", "contamination_flag": True},
        {"slug": "malacca_strait", "contamination_flag": False},
    ])

    assert _clean_donor_slugs(meta) == ["malacca_strait"]
