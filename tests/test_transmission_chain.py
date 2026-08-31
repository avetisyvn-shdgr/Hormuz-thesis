"""Tests for the evidence-cascade assembly."""

import numpy as np
import pytest


from hormuz_throughput.transmission_chain import build_evidence_cascade, percent_change


def test_percent_change_signs_and_guards():
    assert percent_change(100, 50) == pytest.approx(-50.0)
    assert percent_change(10, 13) == pytest.approx(30.0)
    assert np.isnan(percent_change(0, 5))
    assert np.isnan(percent_change(None, 5))


def _cascade():
    return build_evidence_cascade(
        hormuz_observed=245.0,
        hormuz_counterfactual=5366.3,
        hormuz_signed_deviation=-0.955,
        hormuz_rw_p=0.10,
        donor_separation_pessimistic=4.17,
        gfw_pre=171.0,
        gfw_post=12.0,
        wto_pre=101.8,
        wto_post=1.38,
        voyages_pre=948.0,
        voyages_post=726.0,
        total_pre=6.28e11,
        total_post=5.30e11,
        mean_per_voyage_pct=10.2,
        mean_bca_lower=4.4,
        mean_bca_upper=17.0,
        composition_share_pct=97.8,
        destination_risers={"cape_of_good_hope": 0.46, "panama_canal": 0.21},
    )


def test_cascade_has_five_ordered_links():
    df = _cascade()
    assert list(df["step"]) == [1, 2, 3, 4, 5]
    assert len(df) == 5
    assert {"layer", "source", "percent_change", "interpretation_boundary"} <= set(df.columns)
    assert "independent_source" not in df.columns


def test_cascade_directions_match_the_argument():
    df = _cascade().set_index("step")
    assert df.loc[1, "percent_change"] < 0
    assert df.loc[2, "percent_change"] < 0
    assert df.loc[3, "percent_change"] < 0
    assert df.loc[4, "percent_change"] > 0


def test_every_link_states_an_interpretation_boundary():
    df = _cascade()
    assert df["interpretation_boundary"].str.len().gt(0).all()
    assert "WTO" in df.loc[df["step"].eq(2), "corroboration"].iloc[0]
    joined = " ".join(df.fillna("").astype(str).to_numpy().ravel()).lower()
    assert "independent" not in joined


def test_corridor_link_does_not_claim_traced_substitution():
    df = _cascade().set_index("step")
    assert df.loc[5, "layer"] == "Alternative-corridor co-movement"
    boundary = df.loc[5, "interpretation_boundary"]
    assert "compatible with substitution" in boundary
    assert "no voyage-level flow tracing" in boundary


def test_hormuz_link_declares_mechanism_window_not_primary_headline():
    df = _cascade().set_index("step")
    assert "94-day mechanism-aligned" in df.loc[1, "metric"]
    assert "130-day primary headline" in df.loc[1, "interpretation_boundary"]


def test_hormuz_percent_change_matches_displayed_cumulative_pair():
    df = _cascade().set_index("step")
    expected = round(
        percent_change(df.loc[1, "pre_value"], df.loc[1, "post_value"]), 1
    )
    assert df.loc[1, "percent_change"] == pytest.approx(expected)
    assert "mean-scaled corridor statistic" in df.loc[1, "corroboration"]
