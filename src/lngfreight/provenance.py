"""Provenance tracking.

Every raw pull is logged immutably: which provider, which code, the exact
query window, when it was retrieved, the row count, and a SHA-256 of the raw
payload. This is what makes the thesis reproducible and audit-able - you can
prove later exactly what data underpinned each result, and detect silently if
a "free" source revises history under you.

Raw data is written once and treated as read-only. Cleaning happens downstream
in data/interim and data/processed, never by mutating data/raw.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from . import config


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def save_raw(
    df: pd.DataFrame,
    *,
    provider: str,
    variable: str,
    code: str,
    query: dict,
    license_note: str,
    filename: str | None = None,
) -> Path:
    """Persist a raw pull as CSV and append a provenance record. Returns path."""
    raw_dir = config.path("data_raw") / provider
    raw_dir.mkdir(parents=True, exist_ok=True)

    fname = filename or f"{variable}__{code.replace(':', '_').replace('.', '_')}.csv"
    out_path = raw_dir / fname

    csv_text = df.to_csv(index=False)
    out_path.write_text(csv_text)

    identity = {
        "variable": variable,
        "provider": provider,
        "code": code,
        "query": query,
        "rows": int(len(df)),
        "columns": list(df.columns),
        "license": license_note,
        "file": str(out_path.relative_to(config.ROOT)),
        "sha256": _sha256(csv_text),
    }

    log_path = config.ROOT / config.settings()["paths"]["provenance_log"]
    log_path.parent.mkdir(parents=True, exist_ok=True)
    if log_path.exists():
        for line in log_path.read_text(encoding="utf-8").splitlines():
            existing = json.loads(line)
            if all(existing.get(key) == value for key, value in identity.items()):
                return out_path

    record = {
        "retrieved_utc": datetime.now(timezone.utc).isoformat(),
        **identity,
    }
    with open(log_path, "a") as fh:
        fh.write(json.dumps(record) + "\n")

    return out_path
