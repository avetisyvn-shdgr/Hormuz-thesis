"""Validated configuration for the restricted network-adaptation experiment."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import yaml


ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "config/network_adaptation.yaml"


@dataclass(frozen=True)
class AdaptationProtocol:
    status: str
    claim: str
    raw_path: Path
    expected_raw_sha256: str
    cutoff: pd.Timestamp
    horizon: int
    event_end: pd.Timestamp
    primary_model: str
    primary_revision: str
    primary_context_length: int
    robustness_model: str
    primary_class: str
    primary_corridors: tuple[str, ...]
    context_corridors: tuple[str, ...]
    negative_control_classes: tuple[str, ...]
    control_minimum_daily_transits: float
    control_weighting_schemes: tuple[str, ...]
    block_length: int
    sensitivity_block_lengths: tuple[int, ...]
    n_draws: int
    seed: int
    outputs: dict[str, Path]

    @property
    def primary_keys(self) -> tuple[tuple[str, str], ...]:
        return tuple((port, self.primary_class) for port in self.primary_corridors)

    @property
    def control_keys(self) -> tuple[tuple[str, str], ...]:
        return tuple(
            (port, vessel_class)
            for vessel_class in self.negative_control_classes
            for port in self.primary_corridors
        )

    @property
    def context_keys(self) -> tuple[tuple[str, str], ...]:
        return tuple((port, self.primary_class) for port in self.context_corridors)


def load_protocol(path: str | Path = CONFIG_PATH) -> AdaptationProtocol:
    source = Path(path)
    raw = yaml.safe_load(source.read_text(encoding="utf-8"))
    root = source.resolve().parents[1]
    outputs = {name: root / value for name, value in raw["outputs"].items()}
    protocol = AdaptationProtocol(
        status=str(raw["status"]),
        claim=str(raw["claim"]),
        raw_path=root / raw["data"]["file"],
        expected_raw_sha256=str(raw["data"]["sha256"]),
        cutoff=pd.Timestamp(raw["data"]["cutoff_exclusive"]),
        horizon=int(raw["data"]["event_horizon_days"]),
        event_end=pd.Timestamp(raw["data"]["event_end_inclusive"]),
        primary_model=str(raw["models"]["primary"]["name"]),
        primary_revision=str(raw["models"]["primary"]["revision"]),
        primary_context_length=int(raw["models"]["primary"]["context_length"]),
        robustness_model=str(raw["models"]["robustness"]["name"]),
        primary_class=str(raw["primary_family"]["vessel_class"]),
        primary_corridors=tuple(
            str(item["portname"]) for item in raw["primary_family"]["corridors"]
        ),
        context_corridors=tuple(str(x) for x in raw["context_series"]["corridors"]),
        negative_control_classes=tuple(
            str(x) for x in raw["negative_control_family"]["vessel_classes"]
        ),
        control_minimum_daily_transits=float(
            raw["negative_control_family"]["volume_eligibility"][
                "minimum_pre_event_daily_transits"
            ]
        ),
        control_weighting_schemes=tuple(
            str(x) for x in raw["negative_control_family"]["weighting_schemes"]
        ),
        block_length=int(raw["inference"]["primary_block_length_days"]),
        sensitivity_block_lengths=tuple(
            int(x) for x in raw["inference"]["sensitivity_block_lengths_days"]
        ),
        n_draws=int(raw["inference"]["draws"]),
        seed=int(raw["inference"]["seed"]),
        outputs=outputs,
    )
    validate_protocol(protocol)
    return protocol


def validate_protocol(protocol: AdaptationProtocol) -> None:
    if protocol.status != "exploratory_retrospective_restriction":
        raise ValueError("the analysis must retain its retrospective exploratory status.")
    if protocol.primary_model != "chronos2_univariate":
        raise ValueError("the admitted univariate Chronos model must remain primary.")
    if protocol.primary_context_length <= 0:
        raise ValueError("the declared Chronos context length must be positive.")
    if protocol.robustness_model != "ar_lag1_7":
        raise ValueError("AR(1,7) must remain the transparent robustness model.")
    if protocol.primary_class != "n_tanker":
        raise ValueError("the primary family must be tanker counts only.")
    if len(protocol.primary_corridors) != 5 or len(set(protocol.primary_corridors)) != 5:
        raise ValueError("the restricted primary family must contain five unique corridors.")
    if set(protocol.primary_corridors) & set(protocol.context_corridors):
        raise ValueError("context series cannot enter the primary family.")
    if set(protocol.negative_control_classes) != {"n_roro", "n_dry_bulk"}:
        raise ValueError("negative controls must remain Ro-Ro and dry bulk.")
    if protocol.control_minimum_daily_transits <= 0:
        raise ValueError("the declared control volume threshold must be positive.")
    if set(protocol.control_weighting_schemes) != {
        "equal", "inverse_reference_variance", "pre_event_volume"
    }:
        raise ValueError("the declared control weighting schemes changed.")
    if protocol.horizon != 130:
        raise ValueError("the matched long-horizon design is fixed at 130 days.")
    expected_end = protocol.cutoff + pd.Timedelta(days=protocol.horizon - 1)
    if protocol.event_end != expected_end:
        raise ValueError("event end does not match the 130-day cutoff geometry.")
    block_lengths = (protocol.block_length, *protocol.sensitivity_block_lengths)
    if any(length <= 0 or length >= protocol.horizon for length in block_lengths):
        raise ValueError("bootstrap block lengths must lie inside the event horizon.")
    if protocol.n_draws < 999:
        raise ValueError("at least 999 synchronized bootstrap draws are required.")
