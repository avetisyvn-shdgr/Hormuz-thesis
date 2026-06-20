"""The one function analysis code calls to get data.

Resolves a logical thesis variable (e.g. "henry_hub_spot") through the
registry to whichever provider currently supplies it, fetches it, logs
provenance, and returns the tidy (date, value) frame. Under the fallback
branch it transparently uses the `proxy` entry when `status` is not free/primary.
"""
from __future__ import annotations

import pandas as pd

from . import config
from .sources import get_provider
from .sources.gfw import GFWClient, exact_imo_vessel_ids, normalize_port_visits
from . import provenance


def _resolve_entry(spec: dict) -> tuple[dict, str]:
    """Pick which backend to use given the variable's status. Returns
    (backend_dict, channel) where channel is 'primary' or 'proxy'."""
    status = spec.get("status")
    if status in ("free", "primary"):
        return spec["primary"], "primary"
    # proxy / unavailable -> use proxy if one exists
    if "proxy" in spec:
        return spec["proxy"], "proxy"
    raise NotImplementedError(
        f"Variable has status={status!r} and no proxy backend. "
        f"This is a go/no-go gap - see docs/DATA_ACCESS_CHECKLIST.md."
    )


def get_variable(name: str, start: str | None = None, end: str | None = None) -> pd.DataFrame:
    reg = config.registry()
    if name not in reg:
        raise KeyError(f"Unknown variable {name!r}. Defined variables: {list(reg)}")
    spec = reg[name]

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
