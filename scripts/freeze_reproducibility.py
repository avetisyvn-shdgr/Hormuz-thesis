"""Freeze raw-data hashes and write a reproducibility/run manifest.

Raw source files stay out of Git; `data/raw/SHA256SUMS` is the tracked identity
of the exact snapshots used. Processed artifacts and reports are versioned.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lngfreight import config  # noqa: E402
from lngfreight.specification import working_specification  # noqa: E402


RAW_HASH_FILE = "data/raw/SHA256SUMS"
VESSEL_HASH_FILE = "data/raw/SHA256SUMS.vessel"
RUN_MANIFEST = "data/processed/reproducibility_manifest.json"

# The raw inputs the frozen PortWatch pipeline (scripts/run_all.py) actually
# consumes. The raw-hash check is scoped to THESE so the core run self-verifies
# independently of the optional Phase-3A vessel branch (CURRENT_PLAN.md branch
# isolation). Vessel-branch raw inputs are frozen separately in SHA256SUMS.vessel.
CORE_RAW_INPUTS = (
    "data/raw/eia/brent_spot__PET_RBRTE_D.csv",
    "data/raw/eia/henry_hub_spot__NG_RNGWHHD_D.csv",
    "data/raw/portwatch/Daily_Chokepoints_Data.csv",
    "data/raw/portwatch/ais_laden_tonmiles_usgc__chokepoint_panama_canal_capacity_tanker.csv",
    "data/raw/portwatch/hormuz_tanker_capacity__chokepoint_strait_of_hormuz_capacity_tanker.csv",
    "data/raw/portwatch/hormuz_tanker_transits__chokepoint_strait_of_hormuz_n_tanker.csv",
    "data/raw/portwatch/panama_tanker_capacity__chokepoint_panama_canal_capacity_tanker.csv",
    "data/raw/portwatch/panama_tanker_transits__chokepoint_panama_canal_n_tanker.csv",
    "data/raw/wto_hormuz/voy_intake_index_lng_export.csv",
)


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
        raw_dir / "SHA256SUMS.vessel",
        raw_dir / "provenance.jsonl",
        raw_dir / ".gitkeep",
    }
    return {
        path.relative_to(root).as_posix(): sha256_file(path)
        for path in sorted(raw_dir.rglob("*"))
        if path.is_file() and path not in ignored
    }


def core_raw_hashes(root: Path) -> dict[str, str]:
    """Hashes of the core PortWatch inputs the frozen pipeline consumes.

    Fails loudly if a declared core input is missing, so a renamed or deleted
    core snapshot cannot silently pass the check (CLAUDE.md rule 1).
    """
    out: dict[str, str] = {}
    for rel in CORE_RAW_INPUTS:
        path = root / rel
        if not path.is_file():
            raise FileNotFoundError(f"core raw input missing: {rel}")
        out[rel] = sha256_file(path)
    return out


def vessel_raw_hashes(root: Path) -> dict[str, str]:
    """Hashes of vessel-branch raw inputs: everything under data/raw that is not a
    core input or a transient download archive (.zip)."""
    core = set(CORE_RAW_INPUTS)
    return {
        rel: digest
        for rel, digest in raw_hashes(root).items()
        if rel not in core and not rel.endswith(".zip")
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


def _write_raw_hashes(root: Path, hashes: dict[str, str], rel: str = RAW_HASH_FILE) -> None:
    path = root / rel
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
    current_raw = core_raw_hashes(root)
    if check:
        frozen = _read_raw_hashes(root)
        if frozen != current_raw:
            print("RAW HASH CHECK FAILED: current core raw snapshots differ from SHA256SUMS.")
            print(f"frozen core files={len(frozen)}, current core files={len(current_raw)}")
            missing = sorted(set(frozen) - set(current_raw))
            extra = sorted(set(current_raw) - set(frozen))
            changed = sorted(k for k in set(frozen) & set(current_raw) if frozen[k] != current_raw[k])
            for tag, items in (("missing", missing), ("unexpected", extra), ("changed", changed)):
                for k in items:
                    print(f"  {tag}: {k}")
            return 1
        print(f"RAW HASH CHECK PASSED: {len(current_raw)} core files match.")
        return 0

    vessel_raw = vessel_raw_hashes(root)
    _write_raw_hashes(root, current_raw)
    _write_raw_hashes(root, vessel_raw, rel=VESSEL_HASH_FILE)
    spec = working_specification()
    manifest = {
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
        "vessel_raw_sha256": vessel_raw,
        "artifact_sha256": _artifact_hashes(root),
        "test_command": ".venv/bin/python -m pytest -q",
    }
    path = root / RUN_MANIFEST
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {root / RAW_HASH_FILE} ({len(current_raw)} core raw files)")
    print(f"wrote {root / VESSEL_HASH_FILE} ({len(vessel_raw)} vessel raw files)")
    print(f"wrote {path} ({len(manifest['artifact_sha256'])} artifacts)")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="verify raw files against frozen hashes")
    args = parser.parse_args()
    raise SystemExit(main(check=args.check))
