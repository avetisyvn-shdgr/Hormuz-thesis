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
import hashlib
import json

import numpy as np
import pandas as pd
import pytest


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
    # descriptive monthly importer outcomes are registry-accessible but not
    # part of the daily PortWatch modeling panel:
    assert "korea_lng_import_total" not in free
    assert "india_lng_import_gulf" not in free
    # unavailable series are NOT:
    assert "ttf_gas" not in free            # status: restricted opt-in
    assert "jkm_lng" not in free            # status: unavailable
    assert "spark30s_atlantic_freight" not in free  # status: unavailable
    assert "ais_laden_tonmiles_usgc" not in free    # status: unavailable


def test_build_panel_refuses_proxy_without_optin():
    # The acquisition candidate is retained as proxy metadata, but the registry
    # status remains unavailable and the guard fires before any provider call.
    with pytest.raises(ValueError, match="proxy"):
        panel_mod.build_panel(variables=["jkm_lng"], allow_proxies=False)


def test_unimplemented_price_candidates_and_taiwan_terms_are_truthful():
    registry = config_mod.registry()
    assert registry["ttf_gas"]["status"] == "restricted"
    assert registry["jkm_lng"]["status"] == "unavailable"
    for variable in ("taiwan_lng_import_total", "taiwan_lng_import_gulf"):
        license_note = registry[variable]["primary"]["license"]
        assert "reuse terms unverified" in license_note
        assert "Open Government Data License" not in license_note


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
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    provenance = tmp_path / "data" / "raw" / "provenance.jsonl"
    provenance.write_text(
        json.dumps({
            "variable": "x",
            "file": "data/raw/provider/x.csv",
            "query": {"start": "2026-01-01", "end": "2026-01-03"},
            "sha256": digest,
        }) + "\n",
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

    source.write_text("date,value\n2026-01-01,999\n", encoding="utf-8")
    with pytest.raises(ValueError, match="hash mismatch"):
        panel_mod.build_panel_from_frozen_raw(variables=["x"])


def test_build_panel_from_frozen_raw_rejects_wrong_window(tmp_path, monkeypatch):
    raw = tmp_path / "data" / "raw" / "provider"
    raw.mkdir(parents=True)
    source = raw / "x.csv"
    source.write_text("date,value\n2026-01-02,2\n", encoding="utf-8")
    provenance = tmp_path / "data" / "raw" / "provenance.jsonl"
    provenance.write_text(json.dumps({
        "variable": "x",
        "file": "data/raw/provider/x.csv",
        "query": {"start": "2026-01-02", "end": "2026-01-02"},
        "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
    }) + "\n", encoding="utf-8")
    monkeypatch.setattr(config_mod, "ROOT", tmp_path)
    monkeypatch.setattr(config_mod, "settings", lambda: {
        "study_window": {"full_start": "2026-01-01", "full_end": "2026-01-03"},
        "paths": {"provenance_log": "data/raw/provenance.jsonl"},
    })

    with pytest.raises(FileNotFoundError, match="2026-01-01"):
        panel_mod.build_panel_from_frozen_raw(variables=["x"])


def test_build_panel_from_frozen_raw_honors_explicit_pin(tmp_path, monkeypatch):
    raw = tmp_path / "data" / "raw" / "provider"
    raw.mkdir(parents=True)
    pinned = raw / "x__pinned.csv"
    legacy = raw / "x.csv"
    pinned.write_text("date,value\n2026-01-01,2\n", encoding="utf-8")
    legacy.write_text("date,value\n2026-01-01,1\n", encoding="utf-8")
    pinned_digest = hashlib.sha256(pinned.read_bytes()).hexdigest()
    legacy_digest = hashlib.sha256(legacy.read_bytes()).hexdigest()
    query = {"start": "2026-01-01", "end": "2026-01-01"}
    provenance = tmp_path / "data" / "raw" / "provenance.jsonl"
    provenance.write_text(
        "\n".join([
            json.dumps({
                "variable": "x",
                "file": "data/raw/provider/x__pinned.csv",
                "query": query,
                "sha256": pinned_digest,
            }),
            # Deliberately last: without a pin this legacy record would win.
            json.dumps({
                "variable": "x",
                "file": "data/raw/provider/x.csv",
                "query": query,
                "sha256": legacy_digest,
            }),
        ]) + "\n",
        encoding="utf-8",
    )
    settings = {
        "study_window": {
            "full_start": "2026-01-01",
            "full_end": "2026-01-01",
        },
        "paths": {"provenance_log": "data/raw/provenance.jsonl"},
        "frozen_raw_pins": {
            "x": {
                "file": "data/raw/provider/x__pinned.csv",
                "sha256": pinned_digest,
            },
        },
    }
    monkeypatch.setattr(config_mod, "ROOT", tmp_path)
    monkeypatch.setattr(config_mod, "settings", lambda: settings)

    out = panel_mod.build_panel_from_frozen_raw(variables=["x"])
    assert out["x"].tolist() == [2]

    settings["frozen_raw_pins"]["x"]["sha256"] = "0" * 64
    with pytest.raises(ValueError, match="pin/provenance hash mismatch"):
        panel_mod.build_panel_from_frozen_raw(variables=["x"])


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
