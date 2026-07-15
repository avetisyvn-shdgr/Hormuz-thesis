import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lngfreight.baselines import seasonal_naive_forecast
from lngfreight.inference import counterfactual_effect, post_treatment_fold
from lngfreight.spatial import (
    chokepoint_metadata,
    leave_one_donor_out_summary,
    slugify_portname,
    spatial_placebo_summary,
    wide_chokepoint_panel,
)


def test_slugify_portname_is_stable():
    assert slugify_portname("Bab el-Mandeb Strait") == "bab_el_mandeb_strait"
    assert slugify_portname("Cape of Good Hope") == "cape_of_good_hope"


def test_wide_chokepoint_panel_contains_expected_controls():
    panel = wide_chokepoint_panel("n_tanker", start="2026-02-26", end="2026-03-02")
    assert "strait_of_hormuz" in panel.columns
    assert "panama_canal" in panel.columns
    assert panel.index.min().strftime("%Y-%m-%d") == "2026-02-26"
    assert panel.index.max().strftime("%Y-%m-%d") == "2026-03-02"


def test_wide_chokepoint_panel_can_exclude_hormuz():
    panel = wide_chokepoint_panel(
        "n_tanker",
        start="2026-02-26",
        end="2026-03-02",
        exclude=["Strait of Hormuz"],
    )
    assert "strait_of_hormuz" not in panel.columns


def test_capacity_panel_masks_zero_capacity_with_positive_transits():
    panel = wide_chokepoint_panel("capacity_tanker", start="2026-02-28", end="2026-06-01")
    # Matches the processed-panel policy: capacity artifacts are masked, so
    # Hormuz has fewer valid capacity observations than transit observations.
    # Pinned to the v2 PortWatch vintage (2026-07-15 download); the v1 vintage
    # value was 79 (window identical — pure upstream revision), quotable from
    # the v1 branch/commit.
    assert int(panel["strait_of_hormuz"].notna().sum()) == 84


def test_hormuz_transit_normalized_spatial_loss_is_near_total():
    panel = wide_chokepoint_panel("n_tanker")
    fold = post_treatment_fold(panel.index)
    pred = seasonal_naive_forecast(panel["strait_of_hormuz"], fold=fold)
    eff = counterfactual_effect(panel.loc[pred.index, "strait_of_hormuz"], pred)
    normalized = eff["cumulative_throughput_loss"] / eff["counterfactual_sum"]
    # Pinned to the v2 state: study window extended to full_end 2026-07-07 AND
    # revised v2 PortWatch vintage. The v1 pin was 0.955284 (94-day window,
    # v1 vintage); the lower v2 share reflects the partial July transit trickle,
    # not a pipeline change. v1 remains quotable from the v1 branch/commit.
    assert normalized == pytest.approx(0.930877, abs=1e-6)


def test_wide_chokepoint_panel_rejects_unknown_value_col():
    with pytest.raises(ValueError, match="value_col"):
        wide_chokepoint_panel("not_a_column")


def test_chokepoint_metadata_flags_known_contamination_risks():
    meta = chokepoint_metadata()
    flagged = set(meta.loc[meta["contamination_flag"], "slug"])
    assert "panama_canal" in flagged
    assert "cape_of_good_hope" in flagged


def test_leave_one_donor_out_keeps_treated_unit_fixed():
    effects = pd.DataFrame([
        {
            "value_col": "n_tanker",
            "slug": "strait_of_hormuz",
            "is_treated": True,
            "cumulative_throughput_loss": 100.0,
            "mean_daily_throughput_loss": 10.0,
            "counterfactual_sum": 120.0,
            "normalized_throughput_loss": 0.833333,
            "n_days": 10,
        },
        {
            "value_col": "n_tanker",
            "slug": "donor_a",
            "is_treated": False,
            "cumulative_throughput_loss": 10.0,
            "mean_daily_throughput_loss": 1.0,
            "counterfactual_sum": 100.0,
            "normalized_throughput_loss": 0.1,
            "n_days": 10,
        },
        {
            "value_col": "n_tanker",
            "slug": "donor_b",
            "is_treated": False,
            "cumulative_throughput_loss": 20.0,
            "mean_daily_throughput_loss": 2.0,
            "counterfactual_sum": 100.0,
            "normalized_throughput_loss": 0.2,
            "n_days": 10,
        },
        {
            "value_col": "n_tanker",
            "slug": "donor_c",
            "is_treated": False,
            "cumulative_throughput_loss": 30.0,
            "mean_daily_throughput_loss": 3.0,
            "counterfactual_sum": 100.0,
            "normalized_throughput_loss": 0.3,
            "n_days": 10,
        },
    ])
    meta = pd.DataFrame([
        {"slug": "strait_of_hormuz", "portname": "Strait of Hormuz", "contamination_flag": False},
        {"slug": "donor_a", "portname": "Donor A", "contamination_flag": False},
        {"slug": "donor_b", "portname": "Donor B", "contamination_flag": False},
        {"slug": "donor_c", "portname": "Donor C", "contamination_flag": False},
    ])

    summary = leave_one_donor_out_summary(effects, meta)

    assert "strait_of_hormuz" not in set(summary["dropped_slug"])
    assert set(summary["dropped_slug"]) == {"donor_a", "donor_b", "donor_c"}
    assert (summary["n_donors"] == 2).all()


def test_leave_one_donor_out_malacca_does_not_drive_transit_normalized_result():
    meta = chokepoint_metadata()
    panel = wide_chokepoint_panel("n_tanker")
    fold = post_treatment_fold(panel.index)
    rows = []
    for slug in panel.columns:
        pred = seasonal_naive_forecast(panel[slug], fold=fold)
        eff = counterfactual_effect(panel.loc[pred.index, slug], pred)
        normalized = (
            eff["cumulative_throughput_loss"] / eff["counterfactual_sum"]
            if eff["counterfactual_sum"]
            else float("nan")
        )
        rows.append({
            "value_col": "n_tanker",
            "slug": slug,
            "is_treated": slug == "strait_of_hormuz",
            "normalized_throughput_loss": normalized,
            **eff,
        })
    effects = pd.DataFrame(rows)

    baseline = spatial_placebo_summary(effects, meta)
    loo = leave_one_donor_out_summary(effects, meta)
    all_donors = baseline[
        (baseline["value_col"] == "n_tanker")
        & (baseline["donor_set"] == "all_donors")
    ].iloc[0]
    malacca_drop = loo[
        (loo["value_col"] == "n_tanker")
        & (loo["donor_set"] == "all_donors")
        & (loo["dropped_slug"] == "malacca_strait")
    ].iloc[0]

    assert malacca_drop["dropped_was_raw_max"]
    assert malacca_drop["normalized_loss_vs_donor_p95_ratio"] >= all_donors[
        "normalized_loss_vs_donor_p95_ratio"
    ]
