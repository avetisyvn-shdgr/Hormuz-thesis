"""Leakage-safety tests for panel assembly (panel.py) and alignment (clean.py).

These guard the three promises the data layer makes but, until now, asserted
only in docstrings:

  1. proxy guard      - a proxy series can never silently enter the panel as if
                        it were the real thing (CLAUDE.md rule 8).
  2. forward-fill only - a future observation can never reach the present
                        (CLAUDE.md rule 5; no backfill, no interpolation).
  3. bounded gap cap  - a real multi-day outage cannot be laundered into
                        fabricated observations.
  4. capacity-artifact mask - an AIS rounding zero cannot masquerade as a
                        genuine closure-zero, and a genuine closure-zero is
                        left untouched.

All tests are NO-network / NO-key: build_panel's proxy guard fires before any
fetch, and align_panel is a pure function over in-memory frames + the local
registry. Run: pytest -q
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lngfreight import panel as panel_mod
from lngfreight import config as config_mod
from lngfreight.clean import align_panel, alignment_report


# Explicit imputation policy so these tests never depend on settings.yaml drift.
SETTINGS = {"imputation": {"price_ffill_max_gap_days": 2,
                           "capacity_zero_with_transits": "mask"}}


def _dates(n: int) -> pd.DatetimeIndex:
    return pd.date_range("2026-01-01", periods=n, freq="D", name="date")


# --------------------------------------------------------------------------
# panel.py : free/proxy contract
# --------------------------------------------------------------------------
def test_free_variables_excludes_proxy_and_unavailable():
    free = set(panel_mod.free_variables())
    # genuinely-free series are in:
    assert "henry_hub_spot" in free
    assert "hormuz_tanker_transits" in free
    # proxy-status and unavailable series are NOT:
    assert "ttf_gas" not in free            # status: proxy
    assert "jkm_lng" not in free            # status: proxy
    assert "spark30s_atlantic_freight" not in free  # status: unavailable
    assert "ais_laden_tonmiles_usgc" not in free    # status: unavailable


def test_build_panel_refuses_proxy_without_optin():
    # ttf_gas resolves through its proxy backend; the guard must raise BEFORE
    # any network fetch, so this needs no API key.
    with pytest.raises(ValueError, match="proxy"):
        panel_mod.build_panel(variables=["ttf_gas"], allow_proxies=False)


def test_build_panel_from_frozen_raw_is_offline_and_calendar_aligned(
    tmp_path, monkeypatch
):
    raw = tmp_path / "data" / "raw" / "provider"
    raw.mkdir(parents=True)
    source = raw / "x.csv"
    pd.DataFrame({
        "date": ["2026-01-01", "2026-01-03"],
        "value": [1.0, 3.0],
    }).to_csv(source, index=False)
    provenance = tmp_path / "data" / "raw" / "provenance.jsonl"
    provenance.write_text(
        '{"variable":"x","file":"data/raw/provider/x.csv"}\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(config_mod, "ROOT", tmp_path)
    monkeypatch.setattr(config_mod, "settings", lambda: {
        "study_window": {"full_start": "2026-01-01", "full_end": "2026-01-03"},
        "paths": {"provenance_log": "data/raw/provenance.jsonl"},
    })
    out = panel_mod.build_panel_from_frozen_raw(variables=["x"])
    assert out["x"].tolist()[0] == 1.0
    assert np.isnan(out["x"].tolist()[1])
    assert out["x"].tolist()[2] == 3.0


# --------------------------------------------------------------------------
# clean.py : forward-fill only, bounded, no leakage
# --------------------------------------------------------------------------
def test_ffill_is_bounded_by_the_cap():
    idx = _dates(7)
    raw = pd.DataFrame(
        {"henry_hub_spot": [10.0, np.nan, np.nan, np.nan, 20.0, np.nan, np.nan]},
        index=idx,
    )
    clean, audit = align_panel(raw, settings=SETTINGS)
    got = clean["henry_hub_spot"].tolist()
    # cap=2: two NaNs after 10 get filled, the third stays NaN (real outage);
    # two NaNs after 20 get filled.
    assert got[0] == 10.0
    assert got[1] == 10.0 and got[2] == 10.0      # filled within cap
    assert np.isnan(got[3])                        # beyond cap -> stays NaN
    assert got[4] == 20.0
    assert got[5] == 20.0 and got[6] == 20.0
    assert (audit["reason"] == "ffill").sum() == 4


def test_ffill_never_pulls_a_future_value_backwards():
    # The gap between 10 and 20 must be filled with the PAST value (10),
    # never the future value (20). This is the core no-leakage guarantee.
    idx = _dates(7)
    raw = pd.DataFrame(
        {"henry_hub_spot": [10.0, np.nan, np.nan, np.nan, 20.0, np.nan, np.nan]},
        index=idx,
    )
    clean, _ = align_panel(raw, settings=SETTINGS)
    assert clean["henry_hub_spot"].iloc[1] == 10.0   # not 20.0


def test_leading_nans_are_never_backfilled():
    # No observation precedes the leading NaNs, so they must remain NaN
    # (backfill / interpolation are intentionally not offered).
    idx = _dates(4)
    raw = pd.DataFrame({"henry_hub_spot": [np.nan, np.nan, 5.0, np.nan]}, index=idx)
    clean, _ = align_panel(raw, settings=SETTINGS)
    got = clean["henry_hub_spot"].tolist()
    assert np.isnan(got[0]) and np.isnan(got[1])
    assert got[2] == 5.0 and got[3] == 5.0


def test_non_price_columns_are_not_forward_filled():
    # A route COUNT (role=route) is not a price series and must not be ffilled.
    idx = _dates(3)
    raw = pd.DataFrame({"hormuz_tanker_transits": [5.0, np.nan, 3.0]}, index=idx)
    clean, audit = align_panel(raw, settings=SETTINGS)
    assert np.isnan(clean["hormuz_tanker_transits"].iloc[1])
    assert audit.empty


# --------------------------------------------------------------------------
# clean.py : capacity-artifact mask
# --------------------------------------------------------------------------
def test_capacity_artifact_masked_but_real_closure_kept():
    idx = _dates(4)
    raw = pd.DataFrame(
        {
            "hormuz_tanker_capacity": [0.0, 100.0, 0.0, 0.0],
            "hormuz_tanker_transits": [5.0, 3.0, 0.0, 2.0],
        },
        index=idx,
    )
    clean, audit = align_panel(raw, settings=SETTINGS)
    cap = clean["hormuz_tanker_capacity"].tolist()
    assert np.isnan(cap[0])          # 0 capacity with 5 transits -> artifact
    assert cap[1] == 100.0           # untouched
    assert cap[2] == 0.0             # genuine closure (0 transits) -> KEPT
    assert np.isnan(cap[3])          # 0 capacity with 2 transits -> artifact
    masked = audit[audit["reason"] == "artifact_masked"]
    assert len(masked) == 2


def test_capacity_keep_policy_leaves_artifacts():
    idx = _dates(2)
    raw = pd.DataFrame(
        {"hormuz_tanker_capacity": [0.0, 50.0],
         "hormuz_tanker_transits": [5.0, 3.0]},
        index=idx,
    )
    settings = {"imputation": {"price_ffill_max_gap_days": 2,
                               "capacity_zero_with_transits": "keep"}}
    clean, audit = align_panel(raw, settings=settings)
    assert clean["hormuz_tanker_capacity"].iloc[0] == 0.0   # trusted
    assert audit.empty


def test_invalid_capacity_policy_raises():
    idx = _dates(2)
    raw = pd.DataFrame(
        {"hormuz_tanker_capacity": [0.0, 50.0],
         "hormuz_tanker_transits": [5.0, 3.0]},
        index=idx,
    )
    settings = {"imputation": {"price_ffill_max_gap_days": 2,
                               "capacity_zero_with_transits": "nonsense"}}
    with pytest.raises(ValueError, match="mask"):
        align_panel(raw, settings=settings)


# --------------------------------------------------------------------------
# clean.py : purity + audit/report integrity
# --------------------------------------------------------------------------
def test_align_panel_does_not_mutate_input():
    idx = _dates(4)
    raw = pd.DataFrame(
        {
            "henry_hub_spot": [10.0, np.nan, 20.0, np.nan],
            "hormuz_tanker_capacity": [0.0, 100.0, 0.0, 0.0],
            "hormuz_tanker_transits": [5.0, 3.0, 0.0, 2.0],
        },
        index=idx,
    )
    before = raw.copy(deep=True)
    align_panel(raw, settings=SETTINGS)
    pd.testing.assert_frame_equal(raw, before)


def test_audit_log_has_contract_columns():
    idx = _dates(3)
    raw = pd.DataFrame({"henry_hub_spot": [1.0, np.nan, 3.0]}, index=idx)
    _, audit = align_panel(raw, settings=SETTINGS)
    assert list(audit.columns) == ["date", "column", "old", "new", "reason"]


def test_alignment_report_counts_match_audit():
    idx = _dates(7)
    raw = pd.DataFrame(
        {"henry_hub_spot": [10.0, np.nan, np.nan, np.nan, 20.0, np.nan, np.nan]},
        index=idx,
    )
    clean, audit = align_panel(raw, settings=SETTINGS)
    report = alignment_report(raw, clean, audit)
    row = report.loc["henry_hub_spot"]
    assert row["null_before"] == 5
    assert row["cells_altered"] == 4
    assert row["null_after"] == 1          # the one cell beyond the cap
