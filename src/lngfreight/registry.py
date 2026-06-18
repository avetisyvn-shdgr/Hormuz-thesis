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
