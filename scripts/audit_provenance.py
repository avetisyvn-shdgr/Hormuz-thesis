"""Audit the raw-data provenance ledger and build a complete frozen-file inventory."""
from __future__ import annotations

import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lngfreight import config  # noqa: E402


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read_frozen_hashes(root: Path) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for relative in ("data/raw/SHA256SUMS", "data/raw/SHA256SUMS.vessel"):
        for line in (root / relative).read_text(encoding="utf-8").splitlines():
            if line.strip():
                digest, path = line.split(maxsplit=1)
                hashes[path] = digest
    return hashes


def _read_path_migrations(root: Path) -> dict[str, dict]:
    path = root / "config/provenance_path_migrations.json"
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != 1:
        raise ValueError(f"unsupported provenance path-migration schema: {path}")
    migrations: dict[str, dict] = {}
    for row in payload.get("renames", []):
        old_file = row["old_file"]
        if old_file in migrations:
            raise ValueError(f"duplicate provenance path migration: {old_file}")
        migrations[old_file] = row
    return migrations


def _capture_manifest(root: Path) -> dict[str, dict]:
    path = (
        root
        / "data/raw/public_snapshots_20260717/metadata/"
        "capture_manifest_20260717.json"
    )
    if not path.exists():
        return {}
    return {row["file_path"]: row for row in json.loads(path.read_text())}


def _backup_manifest(root: Path) -> dict[str, dict]:
    base = root / "data/raw/backup_pathway_probe_20260621"
    path = base / "MANIFEST.json"
    if not path.exists():
        return {}
    payload = json.loads(path.read_text())
    return {
        str((base / row["file"]).relative_to(root)): row
        for row in payload["files"]
    }


def main() -> int:
    root = config.ROOT
    ledger_path = root / config.settings()["paths"]["provenance_log"]
    records = [
        json.loads(line)
        for line in ledger_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    v2 = [record for record in records if record.get("schema_version") == 2]
    migrations = _read_path_migrations(root)

    missing_ledger_paths: list[str] = []
    resolved_renamed_ledger_paths: list[dict] = []
    stale_records: list[int] = []
    matching_by_path: dict[str, list[dict]] = {}
    for number, record in enumerate(records, 1):
        path = root / record["file"]
        if not path.exists():
            migration = migrations.get(record["file"])
            if migration is not None:
                renamed = root / migration["new_file"]
                actual = _sha256(renamed) if renamed.exists() else None
                if actual == migration["sha256"] == record["sha256"]:
                    resolved_renamed_ledger_paths.append({
                        "ledger_line": number,
                        "old_file": record["file"],
                        "new_file": migration["new_file"],
                        "sha256": actual,
                    })
                    continue
            missing_ledger_paths.append(record["file"])
            continue
        if _sha256(path) == record["sha256"]:
            matching_by_path.setdefault(record["file"], []).append(record)
        else:
            stale_records.append(number)

    v2_paths = {record["file"] for record in v2}
    current_without_v2 = sorted(set(matching_by_path) - v2_paths)

    source_by_path: dict[str, list[dict]] = {}
    source_hash_failures: list[str] = []
    for record in v2:
        for source in record.get("source_payloads", []):
            source_by_path.setdefault(source["file"], []).append(record)
            path = root / source["file"]
            if not path.exists() or _sha256(path) != source["sha256"]:
                source_hash_failures.append(source["file"])

    configured_free = {
        name
        for name, spec in config.registry().items()
        if spec.get("status") in {"free", "primary"}
    }
    mapped_registry = {
        name for record in v2 for name in record.get("registry_variables", [])
    }
    unmapped_free = sorted(configured_free - mapped_registry)

    frozen = _read_frozen_hashes(root)
    frozen_hash_failures = [
        path
        for path, expected in frozen.items()
        if not (root / path).exists() or _sha256(root / path) != expected
    ]
    captures = _capture_manifest(root)
    backups = _backup_manifest(root)
    inventory_rows: list[dict] = []
    for path, digest in sorted(frozen.items()):
        if path in v2_paths:
            channel = "provenance_v2_snapshot"
        elif path in source_by_path:
            channel = "provenance_v2_source_payload"
        elif path in captures:
            channel = "dated_capture_manifest"
        elif path in backups:
            channel = "dated_backup_manifest"
        elif path in matching_by_path:
            channel = "historical_v1_snapshot"
        else:
            channel = "fixity_only_metadata_gap"
        registry_variables = sorted({
            name
            for record in matching_by_path.get(path, [])
            for name in record.get("registry_variables", [])
        })
        inventory_rows.append({
            "file": path,
            "sha256": digest,
            "provenance_channel": channel,
            "registry_variables": "|".join(registry_variables),
        })

    processed = config.path("data_processed")
    inventory_path = processed / "raw_provenance_inventory.csv"
    summary_path = processed / "provenance_audit_summary.json"
    pd.DataFrame(inventory_rows).to_csv(inventory_path, index=False)
    channels = Counter(row["provenance_channel"] for row in inventory_rows)
    summary = {
        "ledger_records": len(records),
        "v2_records": len(v2),
        "current_ledger_paths": len(matching_by_path),
        "historical_stale_record_count": len(stale_records),
        "historical_stale_record_lines": stale_records,
        "missing_ledger_paths": sorted(set(missing_ledger_paths)),
        "resolved_renamed_ledger_paths": resolved_renamed_ledger_paths,
        "current_paths_without_v2": current_without_v2,
        "source_payload_hash_failures": sorted(set(source_hash_failures)),
        "configured_free_registry_variables": len(configured_free),
        "mapped_free_registry_variables": len(configured_free - set(unmapped_free)),
        "unmapped_free_registry_variables": unmapped_free,
        "frozen_raw_files": len(frozen),
        "frozen_hash_failures": frozen_hash_failures,
        "inventory_channels": dict(sorted(channels.items())),
        "interpretation": (
            "Historical stale lines are retained as evidence of pre-content-addressing "
            "path reuse. A later matching record establishes current fixity. "
            "historical_original_not_preserved is a disclosed gap, not a reconstructed "
            "source payload."
        ),
    }
    summary_path.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    failures = (
        missing_ledger_paths
        or current_without_v2
        or source_hash_failures
        or unmapped_free
        or frozen_hash_failures
    )
    print(f"ledger records={len(records)} v2={len(v2)}")
    print(
        f"current paths={len(matching_by_path)} "
        f"historical stale records={len(stale_records)}"
    )
    print(
        f"registry mapping={len(configured_free - set(unmapped_free))}/"
        f"{len(configured_free)} free variables"
    )
    print(f"frozen raw inventory={len(frozen)} channels={dict(sorted(channels.items()))}")
    print(f"wrote {inventory_path}")
    print(f"wrote {summary_path}")
    if failures:
        print("PROVENANCE AUDIT FAILED")
        return 1
    print("PROVENANCE AUDIT PASSED WITH DISCLOSED HISTORICAL SOURCE GAPS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
