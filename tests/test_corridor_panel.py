"""Contracts for the basin-keyed corridor input panel and audit."""
import hashlib
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lngfreight.corridor_panel import (
    build_corridor_panel,
    load_corridor_panel_protocol,
)


def test_basin_mapping_is_complete_non_additive_and_reviewable():
    protocol = load_corridor_panel_protocol()
    assert len(protocol.basin_mapping) == 28
    assert protocol.grouping_type == "operational_maritime_region"
    assert protocol.aggregation_allowed is False
    assert all(group and note for group, note in protocol.basin_mapping.values())


def test_corridor_panel_has_complete_keys_and_locked_history():
    protocol = load_corridor_panel_protocol()
    panel, metadata, quality, audit = build_corridor_panel(protocol)
    assert len(panel) == 1613 * 28 * 2
    assert not panel.duplicated(["date", "target", "corridor"]).any()
    assert panel["date"].min() == pd.Timestamp("2022-01-01")
    assert panel["date"].max() == pd.Timestamp("2026-06-01")
    assert len(metadata) == 28
    assert len(quality) == 56
    assert audit["n_duplicate_keys"] == 0
    assert audit["diagnostic_scope"] == "pre_cutoff_only"
    assert audit["raw_history_before_panel_start_is_intentionally_unused"] is True


def test_panel_preserves_target_units_missingness_and_eligibility():
    protocol = load_corridor_panel_protocol()
    panel, metadata, quality, audit = build_corridor_panel(protocol)
    units = panel.groupby("target")["unit"].unique().map(tuple).to_dict()
    assert units == {
        "capacity_tanker": ("daily_tanker_deadweight_capacity",),
        "n_tanker": ("daily_tanker_transit_count",),
    }
    missing = quality.groupby("target")["n_missing"].sum().to_dict()
    assert missing["n_tanker"] == 0
    assert missing["capacity_tanker"] > 0
    assert metadata["eligible_n_tanker"].sum() == 28
    assert metadata["eligible_capacity_tanker"].sum() == 20
    assert audit["eligible_corridors"] == {
        target: list(corridors)
        for target, corridors in protocol.eligible_corridors.items()
    }


def test_quality_statistics_use_pre_cutoff_rows_only():
    protocol = load_corridor_panel_protocol()
    panel, _, quality, _ = build_corridor_panel(protocol)
    expected_days = int((protocol.cutoff - protocol.start).days)
    assert quality["n_days_expected"].eq(expected_days).all()
    hormuz_count = quality[
        quality["target"].eq("n_tanker")
        & quality["corridor"].eq("strait_of_hormuz")
    ].iloc[0]
    direct = panel[
        panel["target"].eq("n_tanker")
        & panel["corridor"].eq("strait_of_hormuz")
        & panel["is_pre_cutoff"]
    ]["value"]
    assert hormuz_count["pre_mean"] == direct.mean()
    assert hormuz_count["n_zero_days"] == int(direct.eq(0).sum())


def test_frozen_panel_manifest_hashes_only_input_artifacts():
    root = Path(__file__).resolve().parents[1]
    manifest = json.loads(
        (root / "data/processed/corridor_transmission_panel_manifest.json").read_text()
    )
    assert manifest["artifact_scope"] == "corridor_input_panel_only_no_forecasts"
    assert set(manifest["output_sha256"]) == {
        "data/processed/corridor_transmission_panel.csv",
        "data/processed/corridor_transmission_metadata.csv",
        "data/processed/corridor_transmission_quality.csv",
        "data/processed/corridor_transmission_panel_audit.json",
    }
    for relative, expected in manifest["output_sha256"].items():
        actual = hashlib.sha256((root / relative).read_bytes()).hexdigest()
        assert actual == expected
