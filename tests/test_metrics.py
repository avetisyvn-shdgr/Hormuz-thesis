import math

import numpy as np
import pytest


from lngfreight.metrics import mae, mase, rmse, score_forecast, smape


def test_metrics_drop_only_paired_missing_values():
    y_true = [1.0, 2.0, np.nan, 4.0]
    y_pred = [1.5, 1.0, 3.0, np.nan]
    assert mae(y_true, y_pred) == pytest.approx(0.75)
    assert rmse(y_true, y_pred) == pytest.approx(math.sqrt((0.5**2 + 1.0**2) / 2))


def test_smape_handles_joint_zero_as_zero_error():
    assert smape([0.0, 10.0], [0.0, 5.0]) == pytest.approx(33.3333333333)


def test_mase_uses_training_scale():
    # Training seasonal naive errors with season_length=1 are all 2.
    assert mase([10.0, 14.0], [8.0, 13.0], [2.0, 4.0, 6.0, 8.0], 1) == pytest.approx(0.75)


def test_mase_constant_training_returns_nan():
    out = mase([1.0], [2.0], [5.0, 5.0, 5.0], 1)
    assert math.isnan(out)


def test_score_forecast_returns_metric_bundle():
    out = score_forecast([2.0, 4.0], [1.0, 5.0], [1.0, 2.0, 3.0], season_length=1)
    assert set(out) == {"mae", "rmse", "mase", "smape"}


def test_no_finite_pairs_raises():
    with pytest.raises(ValueError, match="No finite paired"):
        mae([np.nan], [1.0])
