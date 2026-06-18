"""Freeze raw-data hashes and write a reproducibility/run manifest.

Raw source files stay out of Git; `data/raw/SHA256SUMS` is the tracked identity
of the exact snapshots used. Processed artifacts and reports are versioned.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lngfreight import config  # noqa: E402
from lngfreight.specification import working_specification  # noqa: E402


RAW_HASH_FILE = "data/raw/SHA256SUMS"
RUN_MANIFEST = "data/processed/reproducibility_manifest.json"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def raw_hashes(root: Path) -> dict[str, str]:
    raw_dir = root / "data" / "raw"
    ignored = {
        raw_dir / "SHA256SUMS",
        raw_dir / "provenance.jsonl",
        raw_dir / ".gitkeep",
    }
    return {
        path.relative_to(root).as_posix(): sha256_file(path)
        for path in sorted(raw_dir.rglob("*"))
        if path.is_file() and path not in ignored
    }


def _artifact_hashes(root: Path) -> dict[str, str]:
    paths = [
        *sorted((root / "data" / "processed").glob("*")),
        *sorted((root / "reports").rglob("*")),
    ]
    manifest = root / RUN_MANIFEST
    return {
        path.relative_to(root).as_posix(): sha256_file(path)
        for path in paths
        if path.is_file() and path != manifest
    }


def _package_versions() -> dict[str, str]:
    out = {}
    for package in ("numpy", "pandas", "pytest", "requests", "PyYAML"):
        try:
            out[package] = version(package)
        except PackageNotFoundError:
            out[package] = "not-installed"
    return out


def _write_raw_hashes(root: Path, hashes: dict[str, str]) -> None:
    path = root / RAW_HASH_FILE
    text = "".join(f"{digest}  {name}\n" for name, digest in hashes.items())
    path.write_text(text, encoding="utf-8")


def _read_raw_hashes(root: Path) -> dict[str, str]:
    path = root / RAW_HASH_FILE
    if not path.exists():
        return {}
    rows = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        digest, name = line.split("  ", 1)
        rows[name] = digest
    return rows


def main(check: bool = False) -> int:
    root = config.ROOT
    current_raw = raw_hashes(root)
    if check:
        frozen = _read_raw_hashes(root)
        if frozen != current_raw:
            print("RAW HASH CHECK FAILED: current raw snapshots differ from SHA256SUMS.")
            print(f"frozen files={len(frozen)}, current files={len(current_raw)}")
            return 1
        print(f"RAW HASH CHECK PASSED: {len(current_raw)} files match.")
        return 0

    _write_raw_hashes(root, current_raw)
    spec = working_specification()
    manifest = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "packages": _package_versions(),
        "working_specification": {
            "status": spec.status,
            "branch": spec.branch,
            "primary_outcome": spec.primary_outcome,
            "robustness_outcome": spec.robustness_outcome,
            "active_secondary_outcomes": list(spec.active_secondary_outcomes),
            "dormant_secondary_outcomes": list(spec.dormant_secondary_outcomes),
            "primary_estimator": spec.primary_estimator,
            "benchmark_estimators": list(spec.benchmark_estimators),
            "conditional_sensitivity_estimators": list(
                spec.conditional_sensitivity_estimators
            ),
            "reporting_term": spec.reporting_term,
            "transformer_enabled": spec.transformer_enabled,
        },
        "config_sha256": {
            "config/settings.yaml": sha256_file(root / "config/settings.yaml"),
            "config/sources.yaml": sha256_file(root / "config/sources.yaml"),
        },
        "raw_sha256": current_raw,
        "artifact_sha256": _artifact_hashes(root),
        "test_command": ".venv/bin/python -m pytest -q",
    }
    path = root / RUN_MANIFEST
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {root / RAW_HASH_FILE} ({len(current_raw)} raw files)")
    print(f"wrote {path} ({len(manifest['artifact_sha256'])} artifacts)")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="verify raw files against frozen hashes")
    args = parser.parse_args()
    raise SystemExit(main(check=args.check))
