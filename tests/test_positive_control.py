"""Contract tests for the ex-ante designated Red Sea positive control."""
from __future__ import annotations

import json

import pandas as pd
import pytest

from experiments.positive_control.protocol import load_protocol


def test_protocol_keeps_the_designation_and_refuses_a_primary_onset():
    protocol = load_protocol()
    assert protocol.designation == "ex_ante_route_topology"
    # Naming one onset primary after both results are known is specification
    # shopping; the B2 freeze forbids it and so does this protocol.
    assert protocol.primary_onset is None
    assert len(protocol.onsets) == 2
    assert protocol.anchor_receiver == "Cape of Good Hope"
    assert protocol.anchor_emitter == "Bab el-Mandeb Strait"
    assert protocol.anchor_key in protocol.eligible_keys
    assert len(protocol.eligible_keys) == 16
    assert "Strait of Hormuz" not in protocol.eligible_corridors


def test_residual_reference_ends_the_day_before_each_onset():
    protocol = load_protocol()
    for onset in protocol.onsets:
        origins = protocol.reference_origins_for(onset)
        assert len(origins) == protocol.reference_origins
        # Contiguous, disjoint, and closing exactly on the onset.
        gaps = {(b - a).days for a, b in zip(origins, origins[1:])}
        assert gaps == {protocol.horizon}
        assert origins[-1] + pd.Timedelta(days=protocol.horizon) == onset.date
        span = onset.date - protocol.reference_start(onset)
        assert span.days == protocol.reference_origins * protocol.horizon


def test_executed_forecasts_hold_no_post_onset_information():
    protocol = load_protocol()
    frame = pd.read_csv(protocol.outputs["event_forecasts"], parse_dates=["origin", "date"])
    expected = (
        len(protocol.onsets) * 2 * (protocol.reference_origins + 1)
        * len(protocol.all_keys) * protocol.horizon
    )
    assert len(frame) == expected
    assert not frame.duplicated(
        ["onset", "model", "origin", "portname", "vessel_class", "date"]
    ).any()
    for onset in protocol.onsets:
        reference = frame.loc[
            frame["onset"].eq(onset.name) & frame["origin_role"].eq("reference")
        ]
        assert reference["date"].max() < onset.date
        event = frame.loc[frame["onset"].eq(onset.name) & frame["origin_role"].eq("event")]
        assert event["date"].min() == onset.date
        assert event["date"].max() == onset.event_end


def test_the_designated_receiver_ranks_first_in_its_frozen_family():
    protocol = load_protocol()
    validation = json.loads(protocol.outputs["validation"].read_text(encoding="utf-8"))
    standing = validation["anchor_standing"]
    # Two onsets x two models, all four reported, none of them the headline.
    assert len(standing) == 4
    for key, value in standing.items():
        assert value["family_size"] == 16, key
        assert value["anchor_rank"] == 1, key
        assert value["anchor_is_family_max"], key
        assert value["anchor_romano_wolf_p"] < 0.05, key
    assert validation["anchor_detected_under_every_block_length"]


def test_the_controls_fire_on_a_corridor_wide_reallocation():
    """The point of this control family firing here is that it can fire at all."""
    protocol = load_protocol()
    inference = pd.read_csv(protocol.outputs["inference"])
    controls = inference.loc[
        inference["family"].eq("anchor_negative_controls")
        & inference["block_length_days"].eq(protocol.block_length)
    ]
    assert len(controls) == 2 * 2 * len(protocol.control_keys)
    # The Red Sea diversion rerouted every vessel class around the Cape, so a
    # control family that stayed null here would be broken. Under AR, which does
    # not blow up on the low-volume Ro-Ro series, every control fires.
    ar_controls = controls.loc[controls["model"].eq(protocol.robustness_model)]
    assert ar_controls["romano_wolf_p_value"].lt(0.05).all()
    assert ar_controls["event_statistic"].gt(0).all()


def test_context_series_are_descriptive_and_the_emitter_is_negative():
    protocol = load_protocol()
    inference = pd.read_csv(protocol.outputs["inference"])
    context = inference.loc[inference["family"].eq("context_descriptive_not_tested")]
    assert context["romano_wolf_p_value"].isna().all()
    emitter = context.loc[
        context["portname"].eq(protocol.anchor_emitter)
        & context["block_length_days"].eq(protocol.block_length)
    ]
    assert len(emitter) == 4
    assert emitter["event_statistic"].lt(0).all()


def test_validation_record_refuses_to_transfer_ex_ante_status():
    protocol = load_protocol()
    validation = json.loads(protocol.outputs["validation"].read_text(encoding="utf-8"))
    assert validation["primary_onset"] is None
    assert sorted(validation["onsets_reported"]) == ["external_onset", "register_onset"]
    assert any(
        "does not transfer" in caveat for caveat in validation["required_caveats"]
    )


@pytest.mark.parametrize("name", ["inference", "global_tests", "validation", "manifest"])
def test_declared_outputs_exist(name):
    assert load_protocol().outputs[name].exists()
