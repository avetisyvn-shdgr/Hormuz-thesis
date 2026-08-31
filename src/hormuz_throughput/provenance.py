"""Versioned provenance for normalized snapshots and original source payloads.

The historical v1 ledger called normalized ``DataFrame.to_csv()`` output a
"raw payload". That wording was too strong: it fingerprinted the analysis-ready
snapshot, not necessarily the original HTTP response or downloaded file. New v2
records distinguish those two layers explicitly and link the normalized snapshot
to preserved source bytes when they are available.

The ledger is append-only under current code, but four historical entries point
to paths that were later overwritten before content-addressed filenames were
introduced. They remain visible as audit evidence; current-path verification must
use a later matching record, not assume every historical line is still resolvable.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import re

import pandas as pd

from . import config
from .sources.base import SourcePayload


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _safe_filename(filename: str) -> str:
    name = Path(filename).name
    return re.sub(r"[^A-Za-z0-9._-]+", "_", name)


def _persist_source_payload(
    payload: SourcePayload,
    *,
    provider: str,
) -> dict:
    """Return a hash-verified source-payload descriptor, copying only if needed."""
    if payload.path is not None:
        path = payload.path.resolve()
        if not path.exists():
            raise FileNotFoundError(f"source payload not found: {path}")
        content = path.read_bytes()
    else:
        path = None
        content = payload.content
    if content is None:
        raise ValueError("source payload has neither path nor content")
    digest = _sha256_bytes(content)

    root = config.ROOT.resolve()
    if path is None or not path.is_relative_to(root):
        original_dir = config.path("data_raw") / provider / "originals"
        original_dir.mkdir(parents=True, exist_ok=True)
        safe_name = _safe_filename(payload.filename)
        suffix = "".join(Path(safe_name).suffixes)
        stem = safe_name[:-len(suffix)] if suffix else safe_name
        stored = original_dir / f"{stem}__{digest[:12]}{suffix}"
        if not stored.exists():
            stored.write_bytes(content)
        elif _sha256_bytes(stored.read_bytes()) != digest:
            raise RuntimeError(f"source payload hash collision: {stored}")
    else:
        stored = path

    record = {
        "role": payload.role,
        "file": str(stored.relative_to(root)),
        "sha256": digest,
        "media_type": payload.media_type,
    }
    if payload.source_url:
        record["source_url"] = payload.source_url
    return record


def _append_identity(identity: dict) -> None:
    """Append one identity unless an identical non-temporal record exists."""
    log_path = config.ROOT / config.settings()["paths"]["provenance_log"]
    log_path.parent.mkdir(parents=True, exist_ok=True)
    if log_path.exists():
        for line in log_path.read_text(encoding="utf-8").splitlines():
            existing = json.loads(line)
            if all(existing.get(key) == value for key, value in identity.items()):
                return
    record = {
        "retrieved_utc": datetime.now(timezone.utc).isoformat(),
        **identity,
    }
    with open(log_path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(record) + "\n")


def save_raw(
    df: pd.DataFrame,
    *,
    provider: str,
    variable: str,
    code: str,
    query: dict,
    license_note: str,
    filename: str | None = None,
    source_payload: SourcePayload | None = None,
    source_payloads: list[SourcePayload] | None = None,
    source_payload_status: str | None = None,
    registry_variables: list[str] | None = None,
    artifact_role: str = "normalized_analysis_snapshot",
) -> Path:
    """Persist a normalized snapshot and append a versioned provenance record."""
    raw_dir = config.path("data_raw") / provider
    raw_dir.mkdir(parents=True, exist_ok=True)

    csv_text = df.to_csv(index=False)
    digest = _sha256(csv_text)
    fname = filename or f"{variable}__{code.replace(':', '_').replace('.', '_')}.csv"
    out_path = raw_dir / fname
    if out_path.exists() and _sha256(out_path.read_text(encoding="utf-8")) != digest:
        out_path = out_path.with_name(
            f"{out_path.stem}__{digest[:12]}{out_path.suffix}"
        )
    if not out_path.exists():
        out_path.write_text(csv_text, encoding="utf-8")
    elif _sha256(out_path.read_text(encoding="utf-8")) != digest:
        raise RuntimeError(f"raw snapshot hash collision: {out_path}")

    if source_payload is not None and source_payloads is not None:
        raise ValueError("pass source_payload or source_payloads, not both")
    supplied_payloads = (
        source_payloads
        if source_payloads is not None
        else ([source_payload] if source_payload is not None else [])
    )
    payload_records = [
        _persist_source_payload(payload, provider=provider)
        for payload in supplied_payloads
    ]
    payload_status = source_payload_status or (
        "preserved" if payload_records else "not_preserved"
    )
    identity = {
        "schema_version": 2,
        "artifact_role": artifact_role,
        "variable": variable,
        "registry_variables": sorted(set(registry_variables or [])),
        "provider": provider,
        "code": code,
        "query": query,
        "rows": int(len(df)),
        "columns": list(df.columns),
        "license": license_note,
        "file": str(out_path.relative_to(config.ROOT)),
        "sha256": digest,
        "source_payload_status": payload_status,
        "source_payloads": payload_records,
    }

    _append_identity(identity)
    return out_path


def register_existing_snapshot(
    path: Path,
    *,
    provider: str,
    variable: str,
    code: str,
    query: dict,
    license_note: str,
    registry_variables: list[str] | None = None,
    source_payloads: list[SourcePayload] | None = None,
    source_payload_status: str | None = None,
    artifact_role: str = "normalized_analysis_snapshot",
) -> Path:
    """Append v2 metadata for existing bytes without rewriting those bytes."""
    path = path.resolve()
    root = config.ROOT.resolve()
    if not path.is_relative_to(root):
        raise ValueError(f"existing snapshot must be inside repository: {path}")
    if not path.exists():
        raise FileNotFoundError(path)
    content = path.read_bytes()
    frame = pd.read_csv(path)
    payload_records = [
        _persist_source_payload(payload, provider=provider)
        for payload in (source_payloads or [])
    ]
    payload_status = source_payload_status or (
        "preserved" if payload_records else "not_preserved"
    )
    identity = {
        "schema_version": 2,
        "artifact_role": artifact_role,
        "variable": variable,
        "registry_variables": sorted(set(registry_variables or [])),
        "provider": provider,
        "code": code,
        "query": query,
        "rows": int(len(frame)),
        "columns": list(frame.columns),
        "license": license_note,
        "file": str(path.relative_to(root)),
        "sha256": _sha256_bytes(content),
        "source_payload_status": payload_status,
        "source_payloads": payload_records,
    }
    _append_identity(identity)
    return path


def register_existing_artifact(
    path: Path,
    *,
    provider: str,
    variable: str,
    code: str,
    query: dict,
    license_note: str,
    registry_variables: list[str] | None = None,
    source_payload_status: str = "artifact_is_preserved_source_payload",
) -> Path:
    """Append v2 metadata for a non-tabular or schema-preserving input artifact.

    Unlike :func:`register_existing_snapshot`, this does not parse or normalize
    the file. It records the exact bytes that an analysis consumer is about to
    read, allowing CSV, JSON, GeoJSON, XLS/XLSX, and other frozen formats to use
    the same registry/provenance gate.
    """
    path = path.resolve()
    root = config.ROOT.resolve()
    if not path.is_relative_to(root):
        raise ValueError(f"existing artifact must be inside repository: {path}")
    if not path.is_file():
        raise FileNotFoundError(path)
    content = path.read_bytes()
    identity = {
        "schema_version": 2,
        "artifact_role": "analysis_input_artifact",
        "variable": variable,
        "registry_variables": sorted(set(registry_variables or [])),
        "provider": provider,
        "code": code,
        "query": query,
        "license": license_note,
        "file": str(path.relative_to(root)),
        "sha256": _sha256_bytes(content),
        "source_payload_status": source_payload_status,
        "source_payloads": [],
    }
    _append_identity(identity)
    return path
