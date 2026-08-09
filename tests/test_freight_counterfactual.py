from __future__ import annotations

import numpy as np
import pandas as pd

from lngfreight.freight_counterfactual import (
    WeeklyValidationDesign,
    fit_freight_counterfactuals,
    forecast_candidate,
)


def test_recursive_forecast_does_not_read_observed_future_values():
    pre = np.linspace(10, 50, 120)
    values_a = np.r_[pre, [100, 200, 300, 400]]
    values_b = np.r_[pre, [-1000, -2000, -3000, -4000]]
    for candidate in ("last_observation", "seasonal_naive_52", "ar_lags_1_2_4"):
        first = forecast_candidate(values_a, origin=120, horizon=4, candidate=candidate)
        second = forecast_candidate(values_b, origin=120, horizon=4, candidate=candidate)
        np.testing.assert_allclose(first, second)


def test_model_selection_and_calibration_are_strictly_pre_treatment():
    weeks = pd.date_range("2020-01-03", periods=150, freq="W-FRI")
    pre = 50 + 5 * np.sin(np.arange(130) / 5)
    base = pd.DataFrame({"week_end": weeks, "rate": np.r_[pre, np.repeat(80.0, 20)]})
    changed = base.copy()
    changed.loc[130:, "rate"] = -5000
    design = WeeklyValidationDesign(initial_train_weeks=80, horizon_weeks=4, step_weeks=4)
    out_a = fit_freight_counterfactuals(
        base,
        first_post_week=weeks[130].date().isoformat(),
        series_columns={"rate": "rate"},
        design=design,
    )
    out_b = fit_freight_counterfactuals(
        changed,
        first_post_week=weeks[130].date().isoformat(),
        series_columns={"rate": "rate"},
        design=design,
    )
    assert out_a[4]["selected_models"] == out_b[4]["selected_models"]
    np.testing.assert_allclose(
        out_a[1]["counterfactual_usd_per_day"],
        out_b[1]["counterfactual_usd_per_day"],
    )
    assert out_a[2].iloc[0]["causal_effect_interpretation_permitted"] == False
    assert 0 < out_a[2].iloc[0]["two_sided_placebo_p_value"] <= 1
