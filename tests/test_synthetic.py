
import numpy as np
import pandas as pd
import pytest


from hormuz_throughput import config
from hormuz_throughput.synthetic import (  # noqa: E402
    fit_simplex_weights,
    post_pre_ratio,
    project_to_simplex,
    rmspe,
    scale_by_pre_period_mean,
)
from run_synthetic_control import (  # noqa: E402
    PRIMARY_PREFIT_RMSPE_MULTIPLIER,
    _clean_donor_slugs,
    _prefit_screen_sensitivity,
)


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


def test_prefit_screen_sensitivity_uses_multiplier_and_finite_sample_floor():
    placebos = pd.DataFrame(
        {
            "pre_rmspe": [0.5, 1.0, 3.0],
            "post_pre_rmspe_ratio": [1.0, 4.0, 9.0],
        }
    )

    out = _prefit_screen_sensitivity(
        value_col="n_tanker",
        actual_ratio=5.0,
        treated_pre_rmspe=0.5,
        placebos=placebos,
    )
    primary = out.loc[out["is_primary_screen"]].iloc[0]
    unscreened = out.loc[out["screen"] == "unscreened"].iloc[0]

    assert primary["pre_rmspe_multiplier"] == PRIMARY_PREFIT_RMSPE_MULTIPLIER
    assert primary["maximum_eligible_pre_rmspe"] == pytest.approx(1.0)
    assert primary["n_placebos_eligible"] == 2
    assert primary["n_placebos_excluded"] == 1
    assert primary["p_ratio_ge_actual"] == pytest.approx(1 / 3)
    assert primary["p_value_floor"] == pytest.approx(1 / 3)
    assert unscreened["n_placebos_eligible"] == 3


def test_frozen_synthetic_control_primary_prefit_screen():
    summary = pd.read_csv(
        config.path("data_processed") / "synthetic_control_summary.csv"
    )
    actual = summary.loc[
        summary["is_actual"].astype(str).str.lower().eq("true")
        & summary["value_col"].eq("n_tanker")
    ].iloc[0]
    placebos = summary.loc[
        ~summary["is_actual"].astype(str).str.lower().eq("true")
        & summary["value_col"].eq("n_tanker")
        & summary["fit_status"].eq("computed")
    ]
    sensitivity = pd.read_csv(
        config.path("data_processed") / "synthetic_control_prefit_sensitivity.csv"
    )
    primary = sensitivity.loc[
        sensitivity["value_col"].eq("n_tanker")
        & sensitivity["is_primary_screen"].astype(bool)
    ].iloc[0]

    assert actual["primary_prefit_rmspe_multiplier"] == pytest.approx(2.0)
    assert actual["n_placebos_total"] == 22
    assert actual["n_placebos_eligible"] == 14
    assert actual["n_placebos_excluded"] == 8
    assert actual["p_ratio_ge_actual"] == pytest.approx(1 / 15)
    assert actual["p_value_floor"] == pytest.approx(1 / 15)
    assert placebos["eligible_primary_prefit_screen"].astype(bool).sum() == 14
    assert primary["p_ratio_ge_actual"] == pytest.approx(actual["p_ratio_ge_actual"])
