"""Verify and describe inputs that are permitted only in sensitivity analyses.

The gate is deliberately separate from the pinned-primary raw scope. It fails
if the August PortWatch artifact drifts, loses its sensitivity-only registry
label, aliases the primary snapshot, or is consumed outside the registry.

Run from the repository root:
    .venv/bin/python scripts/verify_sensitivity_inputs.py
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

import pandas as pd
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from hormuz_throughput import config, registry  # noqa: E402
from freeze_reproducibility import (  # noqa: E402
    SENSITIVITY_HASH_FILE,
    SENSITIVITY_RAW_INPUTS,
    sensitivity_raw_hashes,
)


SENSITIVITY_VARIABLE = "portwatch_chokepoints_vintage_20260809_snapshot"
PINNED_VARIABLE = "portwatch_chokepoints_snapshot"
FIXITY_ONLY_RAW_REFERENCES = {
    "scripts/freeze_reproducibility.py",
    "scripts/build_model_admission_checkpoint.py",
}
SENSITIVITY_ENTRYPOINTS = (
    "scripts/run_portwatch_sensitivity.py",
    "scripts/run_model_vintage_matrix.py",
)
DERIVED_SENSITIVITY_CONSUMERS = (
    "scripts/build_model_admission_protocol.py",
)


def _production_python_files(root: Path) -> tuple[Path, ...]:
    return tuple(sorted((root / "scripts").rglob("*.py"))) + tuple(
        sorted((root / "src").rglob("*.py"))
    )


def _declares_sensitivity_variable(node: object) -> bool:
    """True if a parsed config names the vintage as a registry variable."""
    if isinstance(node, dict):
        for key, value in node.items():
            if key in ("registry_variable", "registry_entry"):
                if value == SENSITIVITY_VARIABLE:
                    return True
            if _declares_sensitivity_variable(value):
                return True
    elif isinstance(node, list):
        return any(_declares_sensitivity_variable(item) for item in node)
    return False


def _configs_declaring_sensitivity(root: Path) -> dict[str, str]:
    """Frozen configs that resolve the vintage on some consumer's behalf."""
    found: dict[str, str] = {}
    for path in sorted((root / "config").rglob("*.yaml")):
        text = path.read_text(encoding="utf-8")
        if SENSITIVITY_VARIABLE not in text:
            continue
        try:
            parsed = yaml.safe_load(text)
        except yaml.YAMLError:
            continue
        if _declares_sensitivity_variable(parsed):
            found[path.relative_to(root).as_posix()] = text
    return found


def _consumer_declaration_sites(
    relative: str, texts: dict[str, str], config_texts: dict[str, str]
) -> list[str]:
    """Where `relative` is bound as the consumer string presented to the registry.

    The binding may sit in another module (a runner whose loader presents the
    runner's own path) or in the frozen config that carries the opt-in. Matching
    a bare quoted path would catch step lists and docstrings, so the path must be
    bound to a `consumer` key or CONSUMER constant. `registry.get_variable`
    splits a `path:phase` consumer on the colon, so an optional suffix is
    allowed here too.
    """
    pattern = re.compile(
        r"""(?:CONSUMER\s*=|["']?consumer["']?\s*[:=])\s*"""
        r"""["']""" + re.escape(relative) + r"""(?::[^"']*)?["']"""
    )
    sites = [name for name, text in texts.items() if pattern.search(text)]
    sites += [name for name, text in config_texts.items() if pattern.search(text)]
    return sorted(sites)


def _discover_consumers(root: Path) -> set[str]:
    """Every production file that consumes the August vintage.

    Two access patterns count, and the guard must see both or it reports a file
    that is properly declared as an undeclared one:

    1. **Direct.** The file names `SENSITIVITY_VARIABLE` itself.
    2. **Config-mediated.** The file reads a frozen config that carries
       `registry_variable: <the vintage>`, and its own path is bound as the
       consumer string presented to `registry.get_variable`. Track A's A4 and
       Track B's B1 opt in this way: the variable is named in the hash-pinned
       config rather than in code, so the code cannot widen its own access.

    Both conditions are required for (2). Reading such a config alone is not
    consumption -- `config/settings.yaml` names the vintage and is read almost
    everywhere -- and being named as a consumer somewhere is not either.
    """
    consumers: set[str] = set()
    sensitivity_path = SENSITIVITY_RAW_INPUTS[0]
    texts: dict[str, str] = {}
    for path in _production_python_files(root):
        text = path.read_text(encoding="utf-8")
        relative = path.relative_to(root).as_posix()
        texts[relative] = text
        if SENSITIVITY_VARIABLE in text:
            consumers.add(relative)
        if (
            sensitivity_path in text
            and "read_csv" in text
            and relative not in FIXITY_ONLY_RAW_REFERENCES
        ):
            raise ValueError(
                f"sensitivity raw path is read directly outside the registry: {relative}"
            )

    config_texts = _configs_declaring_sensitivity(root)
    config_names = {Path(name).name for name in config_texts}
    for relative, text in texts.items():
        if relative in consumers:
            continue
        if not any(name in text for name in config_names):
            continue
        if _consumer_declaration_sites(relative, texts, config_texts):
            consumers.add(relative)
    return consumers


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read_hash_scope(path: Path) -> dict[str, str]:
    rows: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            digest, relative = line.split(maxsplit=1)
            rows[relative] = digest
    return rows


def build_sensitivity_manifest() -> dict:
    """Validate promotion guards and return a deterministic manifest."""
    root = config.ROOT
    registry_config = config.registry()
    sensitivity_spec = registry_config[SENSITIVITY_VARIABLE]
    pinned_spec = registry_config[PINNED_VARIABLE]

    if sensitivity_spec.get("analysis_scope") != "sensitivity_only":
        raise ValueError("August PortWatch vintage must be labelled sensitivity_only")
    if sensitivity_spec.get("promotion_policy") != (
        "must_not_replace_pinned_primary_without_new_recorded_decision"
    ):
        raise ValueError("August PortWatch vintage is missing its promotion guard")
    declared_consumers = set(sensitivity_spec.get("allowed_consumers", []))
    discovered_consumers = _discover_consumers(root)
    if declared_consumers != discovered_consumers:
        raise ValueError(
            "declared sensitivity consumers differ from repository discovery: "
            f"declared={sorted(declared_consumers)}, "
            f"discovered={sorted(discovered_consumers)}"
        )

    sensitivity_path = sensitivity_spec["primary"]["path"]
    pinned_path = pinned_spec["primary"]["path"]
    if sensitivity_path == pinned_path:
        raise ValueError("sensitivity and pinned PortWatch paths must differ")
    if tuple(SENSITIVITY_RAW_INPUTS) != (sensitivity_path,):
        raise ValueError("declared sensitivity scope does not match the registry path")

    declared = _read_hash_scope(root / SENSITIVITY_HASH_FILE)
    actual = sensitivity_raw_hashes(root)
    if declared != actual:
        raise ValueError("sensitivity input hash scope does not match current bytes")

    artifact = registry.get_variable(
        SENSITIVITY_VARIABLE,
        query={"consumer": "scripts/verify_sensitivity_inputs.py"},
        allow_sensitivity=True,
    )
    if artifact.sha256 != actual[sensitivity_path]:
        raise ValueError("registry-verified artifact hash differs from sensitivity scope")

    frame = artifact.read_csv(encoding="utf-8-sig", parse_dates=["date"])
    required = {"date", "portname", "n_tanker"}
    if not required.issubset(frame.columns):
        raise ValueError(f"sensitivity artifact lacks columns {sorted(required)}")
    if config.settings()["study_window"]["full_end"] != "2026-07-07":
        raise ValueError("pinned primary window changed while adding a sensitivity input")

    py_texts = {
        path.relative_to(root).as_posix(): path.read_text(encoding="utf-8")
        for path in _production_python_files(root)
    }
    config_texts = _configs_declaring_sensitivity(root)
    direct_call_sites: set[str] = set()
    config_mediated_call_sites: set[str] = set()
    for relative in sorted(declared_consumers):
        text = py_texts.get(relative) or (root / relative).read_text(encoding="utf-8")
        if (
            "registry.get_variable" in text
            and SENSITIVITY_VARIABLE in text
            and "allow_sensitivity" in text
        ):
            direct_call_sites.add(relative)
            continue
        sites = _consumer_declaration_sites(relative, py_texts, config_texts)
        mediated = any(
            "allow_sensitivity" in (py_texts.get(site) or config_texts.get(site, ""))
            and (
                site in config_texts
                or "get_variable" in py_texts.get(site, "")
            )
            for site in sites
        )
        if not mediated:
            raise ValueError(f"sensitivity consumer bypasses the registry: {relative}")
        config_mediated_call_sites.add(relative)
    matrix_entry = (root / SENSITIVITY_ENTRYPOINTS[1]).read_text(encoding="utf-8")
    if "load_vintage_series" not in matrix_entry:
        raise ValueError("matrix entrypoint no longer delegates to the guarded loader")
    branch_entry = (root / SENSITIVITY_ENTRYPOINTS[0]).read_text(encoding="utf-8")
    if "verify_sensitivity_inputs.py" not in branch_entry:
        raise ValueError("sensitivity runner no longer begins with the input gate")
    derived = (root / DERIVED_SENSITIVITY_CONSUMERS[0]).read_text(encoding="utf-8")
    if "known_vintage_sensitivity_rows_at_lock" not in derived:
        raise ValueError("admission builder no longer exposes the known August AR artifact")

    protocol_path = config.CONFIG_DIR / "model_admission_protocol.yaml"
    protocol = yaml.safe_load(protocol_path.read_text(encoding="utf-8"))
    if protocol["known_vintage_sensitivity_rows_at_lock"]["source"] != (
        "data/processed/portwatch_vintage_sensitivity.csv"
    ):
        raise ValueError("admission protocol no longer declares the known August AR artifact")
    return {
        "manifest_schema": 1,
        "analysis_scope": "sensitivity_only",
        "variable": SENSITIVITY_VARIABLE,
        "path": sensitivity_path,
        "sha256": artifact.sha256,
        "hash_scope_file": SENSITIVITY_HASH_FILE,
        "source_payload_status": artifact.source_status,
        "registry_analysis_scope": sensitivity_spec["analysis_scope"],
        "promotion_policy": sensitivity_spec["promotion_policy"],
        "pinned_primary_variable": PINNED_VARIABLE,
        "pinned_primary_path": pinned_path,
        "pinned_primary_window_end": "2026-07-07",
        "row_count": int(len(frame)),
        "date_min": frame["date"].min().date().isoformat(),
        "date_max": frame["date"].max().date().isoformat(),
        "direct_registry_call_sites": sorted(direct_call_sites),
        "config_mediated_call_sites": sorted(config_mediated_call_sites),
        "sensitivity_entrypoints": list(SENSITIVITY_ENTRYPOINTS),
        "derived_artifact_consumers": list(DERIVED_SENSITIVITY_CONSUMERS),
        "registry_opt_in_enforced": True,
        "model_admission_protocol_sha256": _sha256(protocol_path),
        "local_fixity_status": "verified",
        "replication_archive_status": "pending_deposit_gitignored_source_bytes",
    }


def main() -> None:
    manifest = build_sensitivity_manifest()
    path = config.path("portwatch_sensitivity_input_manifest_json")
    path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        "SENSITIVITY INPUT GATE PASSED: "
        f"{manifest['variable']} {manifest['sha256']}"
    )
    print("primary remains pinned through 2026-07-07")
    print("replication archive status: pending deposit of gitignored source bytes")
    print(f"wrote {path}")


if __name__ == "__main__":
    main()
