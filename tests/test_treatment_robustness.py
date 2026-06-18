import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from lngfreight.validation import resolve_cutoff
from run_treatment_robustness import _post_windows


def test_treatment_robustness_windows_keep_fixed_training_cutoff():
    cutoff = resolve_cutoff()
    windows = _post_windows()

    assert cutoff == pd.Timestamp("2026-02-28")
    assert [w["window"] for w in windows] == [
        "donut_clean_post_after_force_majeure",
        "anchored_kinetic_trigger",
        "anchored_closure_declaration",
        "anchored_force_majeure",
    ]
    assert all(pd.Timestamp(w["post_start"]) >= cutoff for w in windows)


def test_donut_window_excludes_ambiguous_transition():
    windows = {w["window"]: w for w in _post_windows()}
    donut = windows["donut_clean_post_after_force_majeure"]

    assert donut["is_donut"] is True
    assert pd.Timestamp(donut["excluded_start"]) == pd.Timestamp("2026-02-28")
    assert pd.Timestamp(donut["excluded_end"]) == pd.Timestamp("2026-03-25")
    assert pd.Timestamp(donut["post_start"]) == pd.Timestamp("2026-03-26")
