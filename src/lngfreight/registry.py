"""The one function analysis code calls to get data.

Resolves a logical thesis variable (e.g. "henry_hub_spot") through the
registry to whichever provider currently supplies it, fetches it, logs
provenance, and returns the tidy (date, value) frame. Under the fallback
branch it transparently uses the `proxy` entry when appropriate. Restricted
local series remain explicit opt-ins and never enter the default free panel.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path

import pandas as pd

from . import config
from .sources import get_provider
from .sources.gfw import GFWClient, exact_imo_vessel_ids, normalize_port_visits
from . import provenance


@dataclass(frozen=True)
class RegisteredArtifact:
    """A checksum-verified external artifact admitted through the registry."""

    variable: str
    path: Path
    sha256: str
    media_type: str
    source_status: str

    def read_csv(self, **kwargs) -> pd.DataFrame:
        return pd.read_csv(self.path, **kwargs)

    def read_json(self, **kwargs):
        if kwargs:
            return pd.read_json(self.path, **kwargs)
        return json.loads(self.path.read_text(encoding="utf-8"))

    def read_bytes(self) -> bytes:
        return self.path.read_bytes()


def _frozen_hashes() -> dict[str, str]:
    hashes: dict[str, str] = {}
    for relative in (
        "data/raw/SHA256SUMS",
        "data/raw/SHA256SUMS.sensitivity",
        "data/raw/SHA256SUMS.vessel",
    ):
        path = config.ROOT / relative
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                digest, filename = line.split(maxsplit=1)
                hashes[filename] = digest
    manifest_path = config.ROOT / "data/processed/reproducibility_manifest.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        hashes.update(manifest.get("interim_input_sha256", {}))
    return hashes


def _get_registered_artifact(
    name: str,
    spec: dict,
    *,
    query: dict | None,
) -> RegisteredArtifact:
    backend, channel = _resolve_entry(spec)
    if backend.get("provider") != "frozen_artifact":
        raise ValueError(
            f"Artifact variable {name!r} must use provider='frozen_artifact'."
        )
    relative = backend["path"]
    path = (config.ROOT / relative).resolve()
    if not path.is_file():
        raise FileNotFoundError(f"registered artifact missing: {relative}")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    expected = _frozen_hashes().get(relative)
    if expected is None:
        raise ValueError(
            f"registered artifact is not in a frozen input scope: {relative}"
        )
    if digest != expected:
        raise ValueError(
            f"registered artifact hash mismatch for {relative}: "
            f"expected {expected}, got {digest}"
        )
    source_status = backend.get(
        "source_status", "artifact_is_preserved_source_payload"
    )
    provenance.register_existing_artifact(
        path,
        provider="frozen_artifact",
        variable=name,
        code=relative,
        query={
            "access_mode": "frozen_analysis_input",
            "channel": channel,
            **(query or {}),
        },
        license_note=backend.get("license", "unspecified"),
        registry_variables=[name],
        source_payload_status=source_status,
    )
    return RegisteredArtifact(
        variable=name,
        path=path,
        sha256=digest,
        media_type=backend.get("media_type", "application/octet-stream"),
        source_status=source_status,
    )


def _resolve_entry(spec: dict) -> tuple[dict, str]:
    """Pick which backend to use given the variable's status. Returns
    (backend_dict, channel) where channel is 'primary' or 'proxy'."""
    status = spec.get("status")
    if status in ("free", "primary", "restricted"):
        return spec["primary"], "primary"
    # proxy / unavailable -> use proxy if one exists
    if "proxy" in spec:
        return spec["proxy"], "proxy"
    raise NotImplementedError(
        f"Variable has status={status!r} and no proxy backend. "
        f"This is a go/no-go gap - see docs/DATA_ACCESS_CHECKLIST.md."
    )


def get_variable(
    name: str,
    start: str | None = None,
    end: str | None = None,
    *,
    query: dict | None = None,
    allow_sensitivity: bool = False,
) -> pd.DataFrame | RegisteredArtifact:
    reg = config.registry()
    if name not in reg:
        raise KeyError(f"Unknown variable {name!r}. Defined variables: {list(reg)}")
    spec = reg[name]
    effective_query = dict(query or {})
    if spec.get("analysis_scope") == "sensitivity_only":
        if not allow_sensitivity:
            raise PermissionError(
                f"{name!r} is sensitivity-only; pass allow_sensitivity=True "
                "from a declared sensitivity consumer"
            )
        consumer = str(effective_query.get("consumer", "")).split(":", 1)[0]
        allowed = set(spec.get("allowed_consumers", []))
        if not consumer or consumer not in allowed:
            raise PermissionError(
                f"undeclared sensitivity consumer {consumer!r} for {name!r}"
            )
        effective_query["analysis_scope"] = "sensitivity_only"
        effective_query["sensitivity_opt_in"] = True
    if spec.get("kind") == "artifact":
        if start is not None or end is not None:
            raise ValueError(
                f"Artifact variable {name!r} does not accept start/end bounds."
            )
        return _get_registered_artifact(name, spec, query=effective_query)

    win = config.settings()["study_window"]
    start = start or win["full_start"]
    end = end or win["full_end"]

    backend, channel = _resolve_entry(spec)
    provider = get_provider(backend["provider"])
    df = provider.fetch(backend["code"], start, end)

    provenance.save_raw(
        df,
        provider=backend["provider"],
        variable=name,
        code=backend["code"],
        query={"start": start, "end": end, "channel": channel, "role": spec["role"]},
        license_note=backend.get("license", "unspecified"),
        source_payload=provider.source_payload,
        registry_variables=[name],
    )
    return df


def get_gfw_vessel_identities(
    roster: pd.DataFrame,
    client: GFWClient | None = None,
) -> pd.DataFrame:
    """Resolve a sourced benchmark roster to exact-match GFW vessel IDs."""
    if "imo" not in roster.columns:
        raise ValueError("GFW identity lookup requires an 'imo' column.")
    client = client or GFWClient()
    rows: list[dict[str, str]] = []
    for imo in roster["imo"].astype(str):
        for vessel_id in exact_imo_vessel_ids(client.search_imo(imo), imo):
            rows.append({"imo": imo, "vessel_id": vessel_id})
    if not rows:
        return pd.DataFrame(columns=["imo", "vessel_id"])
    return pd.DataFrame(rows).drop_duplicates().sort_values(
        ["imo", "vessel_id"]
    ).reset_index(drop=True)


def get_gfw_vessel_identities_batched(
    roster: pd.DataFrame,
    client: GFWClient | None = None,
    batch_size: int = 10,
) -> pd.DataFrame:
    """Resolve a large frozen frame using bounded advanced-search batches."""
    if "imo" not in roster.columns:
        raise ValueError("GFW identity lookup requires an 'imo' column.")
    if batch_size < 1 or batch_size > 10:
        raise ValueError("batch_size must be between 1 and 10.")
    client = client or GFWClient()
    imos = sorted(roster["imo"].astype(str).unique())
    rows: list[dict[str, str]] = []
    for start in range(0, len(imos), batch_size):
        batch = imos[start:start + batch_size]
        entries = client.search_imos(batch)
        for imo in batch:
            for vessel_id in exact_imo_vessel_ids(entries, imo):
                rows.append({"imo": imo, "vessel_id": vessel_id})
    if not rows:
        return pd.DataFrame(columns=["imo", "vessel_id"])
    return pd.DataFrame(rows).drop_duplicates().sort_values(
        ["imo", "vessel_id"]
    ).reset_index(drop=True)


def get_gfw_port_visits(
    vessel_ids: list[str],
    windows: dict[str, tuple[str, str]],
    client: GFWClient | None = None,
) -> pd.DataFrame:
    """Fetch and normalize bounded GFW port-visit comparison windows."""
    client = client or GFWClient()
    rows: list[dict] = []
    for label, (start, end) in windows.items():
        events = client.port_visits(vessel_ids, start, end)
        rows.extend(normalize_port_visits(events, label))
    columns = [
        "event_id", "vessel_id", "start", "end", "port_id", "port_name",
        "port_country", "lat", "lon", "confidence", "at_dock", "sample_period",
    ]
    if not rows:
        return pd.DataFrame(columns=columns)
    frame = pd.DataFrame(rows, columns=columns)
    frame["start"] = pd.to_datetime(frame["start"], utc=True)
    frame["end"] = pd.to_datetime(frame["end"], utc=True)
    frame = frame.drop_duplicates(subset=["event_id", "sample_period"])
    return frame.sort_values(["sample_period", "start", "vessel_id"]).reset_index(drop=True)
