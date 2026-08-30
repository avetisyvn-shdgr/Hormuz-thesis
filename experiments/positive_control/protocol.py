"""Frozen configuration for the ex-ante designated Red Sea positive control."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import yaml


ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "config/redsea_positive_control.yaml"


@dataclass(frozen=True)
class Onset:
    name: str
    date: pd.Timestamp
    provenance: str
    known_limitation: str

    @property
    def event_end(self) -> pd.Timestamp:
        return self.date + pd.Timedelta(days=HORIZON - 1)


HORIZON = 130


@dataclass(frozen=True)
class PositiveControlProtocol:
    status: str
    claim: str
    raw_path: Path
    expected_raw_sha256: str
    horizon: int
    reference_origins: int
    onsets: tuple[Onset, ...]
    primary_onset: str | None
    anchor_receiver: str
    anchor_emitter: str
    anchor_class: str
    designation: str
    eligible_corridors: tuple[str, ...]
    control_classes: tuple[str, ...]
    control_corridors: tuple[str, ...]
    context_corridors: tuple[str, ...]
    primary_model: str
    primary_revision: str
    primary_context_length: int
    robustness_model: str
    block_length: int
    sensitivity_block_lengths: tuple[int, ...]
    n_draws: int
    seed: int
    outputs: dict[str, Path]

    @property
    def anchor_key(self) -> tuple[str, str]:
        return (self.anchor_receiver, self.anchor_class)

    @property
    def eligible_keys(self) -> tuple[tuple[str, str], ...]:
        return tuple((port, self.anchor_class) for port in self.eligible_corridors)

    @property
    def control_keys(self) -> tuple[tuple[str, str], ...]:
        return tuple(
            (port, vessel_class)
            for vessel_class in self.control_classes
            for port in self.control_corridors
        )

    @property
    def context_keys(self) -> tuple[tuple[str, str], ...]:
        return tuple((port, self.anchor_class) for port in self.context_corridors)

    @property
    def all_keys(self) -> tuple[tuple[str, str], ...]:
        return tuple(
            dict.fromkeys(self.eligible_keys + self.control_keys + self.context_keys)
        )

    def reference_start(self, onset: Onset) -> pd.Timestamp:
        """First day of the contiguous pre-onset residual reference."""
        return onset.date - pd.Timedelta(days=self.reference_origins * self.horizon)

    def reference_origins_for(self, onset: Onset) -> tuple[pd.Timestamp, ...]:
        start = self.reference_start(onset)
        return tuple(
            start + pd.Timedelta(days=self.horizon * index)
            for index in range(self.reference_origins)
        )


def load_protocol(path: str | Path = CONFIG_PATH) -> PositiveControlProtocol:
    source = Path(path)
    raw = yaml.safe_load(source.read_text(encoding="utf-8"))
    root = source.resolve().parents[1]
    protocol = PositiveControlProtocol(
        status=str(raw["status"]),
        claim=str(raw["claim"]),
        raw_path=root / raw["data"]["file"],
        expected_raw_sha256=str(raw["data"]["sha256"]),
        horizon=int(raw["data"]["event_horizon_days"]),
        reference_origins=int(raw["data"]["reference_origins"]),
        onsets=tuple(
            Onset(
                name=str(item["name"]),
                date=pd.Timestamp(item["date"]),
                provenance=str(item["provenance"]),
                known_limitation=str(item["known_limitation"]),
            )
            for item in raw["onsets"]["declared"]
        ),
        primary_onset=raw["onsets"]["primary"],
        anchor_receiver=str(raw["anchor"]["receiver"]),
        anchor_emitter=str(raw["anchor"]["emitter"]),
        anchor_class=str(raw["anchor"]["vessel_class"]),
        designation=str(raw["anchor"]["designation"]),
        eligible_corridors=tuple(
            str(x) for x in raw["eligible_receiver_family"]["corridors"]
        ),
        control_classes=tuple(
            str(x) for x in raw["negative_control_family"]["vessel_classes"]
        ),
        control_corridors=tuple(
            str(x) for x in raw["negative_control_family"]["corridors"]
        ),
        context_corridors=tuple(str(x) for x in raw["context_series"]["corridors"]),
        primary_model=str(raw["models"]["primary"]["name"]),
        primary_revision=str(raw["models"]["primary"]["revision"]),
        primary_context_length=int(raw["models"]["primary"]["context_length"]),
        robustness_model=str(raw["models"]["robustness"]["name"]),
        block_length=int(raw["inference"]["primary_block_length_days"]),
        sensitivity_block_lengths=tuple(
            int(x) for x in raw["inference"]["sensitivity_block_lengths_days"]
        ),
        n_draws=int(raw["inference"]["draws"]),
        seed=int(raw["inference"]["seed"]),
        outputs={name: root / value for name, value in raw["outputs"].items()},
    )
    validate_protocol(protocol)
    return protocol


def validate_protocol(protocol: PositiveControlProtocol) -> None:
    if protocol.status != "ex_ante_designated_positive_control":
        raise ValueError("this experiment exists to be the ex-ante designated test.")
    if protocol.designation != "ex_ante_route_topology":
        raise ValueError("the anchor designation may not be re-derived from outcomes.")
    if protocol.primary_onset is not None:
        raise ValueError(
            "both onsets are declared sensitivities; naming one primary after "
            "seeing both results is specification shopping."
        )
    if len(protocol.onsets) != 2:
        raise ValueError("both declared onsets must be reported.")
    if protocol.horizon != HORIZON:
        raise ValueError("the horizon must match the Hormuz corridor design.")
    if protocol.reference_origins != 8:
        raise ValueError("the residual reference must span eight 130-day origins.")
    if protocol.anchor_key not in protocol.eligible_keys:
        raise ValueError("the designated anchor must sit inside the family it is ranked in.")
    if len(set(protocol.eligible_corridors)) != len(protocol.eligible_corridors):
        raise ValueError("the eligible receiver family contains duplicates.")
    if "Strait of Hormuz" in protocol.eligible_corridors:
        raise ValueError("Hormuz is the held-out unit and may not enter this family.")
    if protocol.primary_model != "chronos2_univariate":
        raise ValueError("the admitted univariate Chronos model must remain primary.")
    if protocol.robustness_model != "ar_lag1_7":
        raise ValueError("AR(1,7) must remain the transparent robustness model.")
    block_lengths = (protocol.block_length, *protocol.sensitivity_block_lengths)
    if any(length <= 0 or length >= protocol.horizon for length in block_lengths):
        raise ValueError("bootstrap block lengths must lie inside the event horizon.")
    if protocol.n_draws < 999:
        raise ValueError("at least 999 synchronized bootstrap draws are required.")
    for onset in protocol.onsets:
        origins = protocol.reference_origins_for(onset)
        if origins[-1] + pd.Timedelta(days=protocol.horizon) != onset.date:
            raise ValueError(
                f"the {onset.name} residual reference does not end the day before the onset."
            )
