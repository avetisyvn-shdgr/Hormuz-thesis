
import numpy as np
import pandas as pd


from lngfreight.diagnostics import (
    capacity_missingness,
    coverage_by_period,
    model_information_sets,
)


def test_coverage_by_period_separates_pre_and_post():
    idx = pd.date_range("2026-01-01", periods=4, freq="D", name="date")
    panel = pd.DataFrame({"target": [1.0, np.nan, 0.0, 2.0]}, index=idx)
    out = coverage_by_period(panel, "2026-01-03").iloc[0]
    assert out["pre_rows"] == 2
    assert out["pre_missing"] == 1
    assert out["post_rows"] == 2
    assert out["post_zeros"] == 1


def test_capacity_missingness_uses_audit_attribution():
    idx = pd.date_range("2026-01-01", periods=4, freq="D", name="date")
    panel = pd.DataFrame({
        "hormuz_tanker_capacity": [10.0, np.nan, np.nan, 0.0],
        "hormuz_tanker_transits": [1.0, 1.0, 1.0, 0.0],
    }, index=idx)
    audit = pd.DataFrame({
        "date": [idx[1]],
        "column": ["hormuz_tanker_capacity"],
        "old": [0.0],
        "new": [np.nan],
        "reason": ["artifact_masked"],
    })
    post = capacity_missingness(panel, audit, "2026-01-03")
    pre = post[post["period"] == "pre"].iloc[0]
    after = post[post["period"] == "post"].iloc[0]
    assert pre["audit_confirmed_artifact_masks"] == 1
    assert pre["unexplained_missing_capacity"] == 0
    assert after["unexplained_missing_capacity"] == 1


def test_information_sets_label_observed_post_covariates():
    info = model_information_sets().set_index("model")
    assert info.loc["ar_lag1_7", "post_observed_covariates"] == ""
    assert info.loc["ar_lag1_7", "counterfactual_role"] == "working_primary"
    assert info.loc["arx_lag1_7_route", "counterfactual_role"] == "conditional_sensitivity"
