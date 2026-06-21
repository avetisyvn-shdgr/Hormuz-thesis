"""Tests for the data-driven donor-contamination screen."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lngfreight.donor_screen import (
    build_screens,
    donor_directional_deviation,
    screen_agreement,
)


def _panel():
    idx = pd.date_range("2022-01-01", periods=560, freq="D")
    cols = {}
    cols["strait_of_hormuz"] = np.r_[np.full(500, 50.0), np.full(60, 2.0)]   # collapse
    cols["riser"] = np.r_[np.full(500, 20.0), np.full(60, 40.0)]            # rose
    cols["faller"] = np.r_[np.full(500, 30.0), np.full(60, 15.0)]           # fell
    cols["steady"] = np.full(560, 25.0)                                     # flat -> ~0
    return pd.DataFrame(cols, index=idx)


def test_directional_deviation_signs_match_rise_and_fall():
    wide = _panel()
    diag = donor_directional_deviation(
        wide, treated_slug="strait_of_hormuz", history_start=wide.index[0],
        cutoff=wide.index[500], horizon_days=30, min_scored_days=20,
    )
    by = diag.set_index("slug")
    assert "strait_of_hormuz" not in by.index            # treated excluded
    assert by.loc["riser", "rose_post_treatment"]
    assert not by.loc["faller", "rose_post_treatment"]
    assert by.loc["riser", "post_signed_deviation"] > 0
    assert by.loc["faller", "post_signed_deviation"] < 0


def test_build_screens_unions_a_priori_and_data_driven():
    wide = _panel()
    diag = donor_directional_deviation(
        wide, treated_slug="strait_of_hormuz", history_start=wide.index[0],
        cutoff=wide.index[500], horizon_days=30, min_scored_days=20,
    )
    screens = build_screens(diag, a_priori_slugs=["faller"])
    assert "riser" in screens["data_driven_rose"]
    assert "faller" not in screens["data_driven_rose"]
    assert screens["a_priori"] == frozenset({"faller"})
    # The pessimistic screen is the union: it must contain both the a-priori
    # member and every data-driven suspect.
    assert {"faller", "riser"} <= screens["pessimistic_union"]
    assert screens["pessimistic_union"] == screens["a_priori"] | screens["data_driven_rose"]
    assert screens["none"] == frozenset()


def test_screen_agreement_flags_suspects_missed_by_a_priori():
    wide = _panel()
    diag = donor_directional_deviation(
        wide, treated_slug="strait_of_hormuz", history_start=wide.index[0],
        cutoff=wide.index[500], horizon_days=30, min_scored_days=20,
    )
    screens = build_screens(diag, a_priori_slugs=["faller"])
    annotated = screen_agreement(diag, screens).set_index("slug")
    # 'riser' rose but is not in the a-priori screen -> data-driven-only suspect.
    assert annotated.loc["riser", "data_driven_only_suspect"]
    assert not annotated.loc["faller", "data_driven_only_suspect"]


def test_unreliable_donor_is_not_flagged_as_risen():
    wide = _panel().copy()
    # Make 'riser' mostly missing in the post window so it is unreliable.
    post = wide.index >= wide.index[500]
    wide.loc[post, "riser"] = np.nan
    wide.iloc[505, wide.columns.get_loc("riser")] = 99.0  # one stray finite day
    diag = donor_directional_deviation(
        wide, treated_slug="strait_of_hormuz", history_start=wide.index[0],
        cutoff=wide.index[500], horizon_days=30, min_scored_days=20,
    )
    screens = build_screens(diag, a_priori_slugs=[])
    assert "riser" not in screens["data_driven_rose"]
