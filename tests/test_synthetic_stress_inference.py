import pandas as pd
import pytest

from hormuz_throughput import config
from run_synthetic_stress import _aggregate_donor_time_blocks


def test_donor_time_aggregation_returns_one_maximum_per_block():
    rows = pd.DataFrame(
        {
            "placebo_fold": ["a", "a", "b", "b"],
            "placebo_start": ["2022-01-01", "2022-01-01", "2022-02-01", "2022-02-01"],
            "placebo_end": ["2022-01-10", "2022-01-10", "2022-02-10", "2022-02-10"],
            "unit": ["u1", "u2", "u1", "u2"],
            "post_pre_rmspe_ratio": [1.0, 3.0, 2.0, 4.0],
        }
    )

    out = _aggregate_donor_time_blocks(rows)

    assert out["placebo_fold"].tolist() == ["a", "b"]
    assert out["n_pseudo_units"].tolist() == [2, 2]
    assert out["max_post_pre_rmspe_ratio"].tolist() == [3.0, 4.0]


def test_donor_time_aggregation_rejects_missing_columns():
    with pytest.raises(ValueError, match="Missing donor-time columns"):
        _aggregate_donor_time_blocks(pd.DataFrame({"placebo_fold": ["a"]}))


def test_frozen_donor_time_inference_uses_seven_disjoint_block_maxima():
    summary = pd.read_csv(
        config.path("data_processed") / "synthetic_donor_time_inference.csv"
    ).iloc[0]
    blocks = pd.read_csv(
        config.path("data_processed") / "synthetic_donor_time_block_maxima.csv",
        parse_dates=["placebo_start", "placebo_end"],
    )

    assert summary["inference_unit"] == "disjoint_time_block"
    assert summary["n_computed_donor_time_fits"] == 154
    assert summary["n_disjoint_time_blocks"] == 7
    assert bool(summary["pooled_donor_time_p_value_supported"]) is False
    assert summary["block_max_rank_p_value"] == pytest.approx(0.125)
    assert summary["block_max_rank_p_value_floor"] == pytest.approx(0.125)
    assert len(blocks) == 7
    assert blocks["n_pseudo_units"].eq(22).all()
    assert all(
        left < right
        for left, right in zip(
            blocks.sort_values("placebo_start")["placebo_end"],
            blocks.sort_values("placebo_start")["placebo_start"].iloc[1:],
        )
    )
