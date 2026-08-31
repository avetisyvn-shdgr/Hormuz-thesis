"""Run and finalize the frozen PortWatch model × vintage sensitivity matrix.

The three phases use separate environments without touching locked primary
artifacts:

    .venv/bin/python scripts/run_model_vintage_matrix.py --phase core
    .venv-bench/bin/python scripts/run_model_vintage_matrix.py --phase chronos
    .venv/bin/python scripts/run_model_vintage_matrix.py --phase finalize
"""
from __future__ import annotations

import argparse
import importlib.metadata
import json
import platform
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from hormuz_throughput import config  # noqa: E402
from hormuz_throughput.vintage_matrix import (  # noqa: E402
    load_design,
    load_vintage_series,
    pinned_self_checks,
    run_chronos_vintage,
    run_core_vintage,
    sha256_file,
    validate_complete_matrix,
    validate_design,
)


CONSUMER = "scripts/run_model_vintage_matrix.py"
LOCKFILE_PATH_MIGRATIONS = {
    "requirements-benchmark.lock.txt": (
        "requirements/locks/benchmark-py311-macos-arm64.txt"
    ),
}


def _load() -> tuple[dict, str]:
    design, digest = load_design()
    validate_design(design)
    return design, digest


def _write(frame: pd.DataFrame, key: str) -> Path:
    path = config.path(key)
    frame.to_csv(path, index=False)
    print(f"wrote {path}")
    return path


def run_core() -> None:
    design, digest = _load()
    daily_frames = []
    summaries = []
    for vintage in design["completion_contract"]["expected_vintages"]:
        series, source = load_vintage_series(
            vintage, design, consumer=f"{CONSUMER}:core"
        )
        daily, summary = run_core_vintage(series, source, design, digest)
        daily_frames.append(daily)
        summaries.append(summary)
    daily = pd.concat(daily_frames, ignore_index=True)
    summary = pd.concat(summaries, ignore_index=True)
    summary["runtime_environment"] = "core_.venv"
    summary["runtime_python"] = platform.python_version()
    summary["runtime_seed"] = summary["model"].map({
        "bsts_local_level_weekly": int(
            design["models"]["bsts_local_level_weekly"]["seed"]
        )
    })
    _write(daily, "model_vintage_matrix_core_daily_csv")
    _write(summary, "model_vintage_matrix_core_summary_csv")
    print("core phase complete: 2 vintages × seasonal/AR/BSTS")


def _chronos_snapshot(design: dict) -> Path:
    spec = design["models"]["chronos2"]
    from huggingface_hub.constants import HF_HUB_CACHE  # type: ignore

    model_dir = spec["model_id"].replace("/", "--")
    path = Path(HF_HUB_CACHE) / f"models--{model_dir}" / "snapshots" / spec[
        "model_revision"
    ]
    if not path.is_dir():
        raise FileNotFoundError(
            f"frozen Chronos snapshot is unavailable in offline cache: {path}"
        )
    return path


def _verify_chronos_environment(design: dict) -> dict:
    spec = design["models"]["chronos2"]
    actual_python = platform.python_version()
    actual_package = importlib.metadata.version(spec["package"])
    lock_relative = LOCKFILE_PATH_MIGRATIONS.get(
        spec["lockfile"], spec["lockfile"]
    )
    lock_path = config.ROOT / lock_relative
    actual_lock = sha256_file(lock_path)
    if actual_python != spec["python_version"]:
        raise ValueError(
            f"Chronos Python drift: expected {spec['python_version']}, got {actual_python}"
        )
    if actual_package != spec["package_version"]:
        raise ValueError(
            f"Chronos package drift: expected {spec['package_version']}, "
            f"got {actual_package}"
        )
    if actual_lock != spec["lockfile_sha256"]:
        raise ValueError("Chronos environment lockfile hash drifted")
    snapshot = _chronos_snapshot(design)
    return {
        "runtime_environment": spec["environment"],
        "runtime_python": actual_python,
        "runtime_package": spec["package"],
        "runtime_package_version": actual_package,
        "runtime_lockfile_sha256": actual_lock,
        "runtime_model_revision": spec["model_revision"],
        "runtime_model_snapshot_path": str(snapshot),
        "runtime_seed": int(spec["seed"]),
        "runtime_device": spec["device_map"],
    }


def run_chronos() -> None:
    design, digest = _load()
    runtime = _verify_chronos_environment(design)
    from hormuz_throughput.tsfm import (
        Chronos2Adapter,
        configure_deterministic_execution,
    )

    configured = configure_deterministic_execution(runtime["runtime_seed"])
    if not configured:
        raise RuntimeError("Chronos phase requires deterministic Torch configuration")
    adapter = Chronos2Adapter(
        model_id=runtime["runtime_model_snapshot_path"],
        device_map=runtime["runtime_device"],
    )

    daily_frames = []
    summaries = []
    for vintage in design["completion_contract"]["expected_vintages"]:
        series, source = load_vintage_series(
            vintage, design, consumer=f"{CONSUMER}:chronos"
        )
        daily, summary = run_chronos_vintage(
            series, source, design, digest, adapter=adapter
        )
        daily_frames.append(daily)
        summaries.append(summary)
    daily = pd.concat(daily_frames, ignore_index=True)
    summary = pd.concat(summaries, ignore_index=True)
    for key, value in runtime.items():
        if key == "runtime_model_snapshot_path":
            continue
        summary[key] = value
    _write(daily, "model_vintage_matrix_chronos_daily_csv")
    _write(summary, "model_vintage_matrix_chronos_summary_csv")
    print("Chronos phase complete: exact cached revision, offline CPU")


def _matrix_manifest(
    design: dict,
    digest: str,
    checks: dict,
    summary: pd.DataFrame,
) -> dict:
    output_keys = (
        "model_vintage_matrix_core_daily_csv",
        "model_vintage_matrix_core_summary_csv",
        "model_vintage_matrix_chronos_daily_csv",
        "model_vintage_matrix_chronos_summary_csv",
        "model_vintage_matrix_daily_csv",
        "model_vintage_matrix_summary_csv",
    )
    output_hashes = {
        config.path(key).relative_to(config.ROOT).as_posix(): sha256_file(
            config.path(key)
        )
        for key in output_keys
    }
    chronos = summary.loc[summary["model"].eq("chronos2")].iloc[0]
    return {
        "manifest_schema": 1,
        "design_id": design["design_id"],
        "design_sha256": digest,
        "admission_protocol_sha256": design["admission_protocol_sha256"],
        "analysis_role": design["analysis_role"],
        "outcome": design["scope"]["outcome"],
        "unit": design["scope"]["unit"],
        "scoring_start": design["scope"]["cutoff"],
        "scoring_end": design["scope"]["scoring_end"],
        "expected_cells": design["completion_contract"]["expected_cells"],
        "completed_cells": int(len(summary)),
        "vintage_averaging": "prohibited_and_not_performed",
        "source_sha256": {
            name: spec["expected_sha256"]
            for name, spec in design["vintages"].items()
        },
        "pinned_self_checks": checks,
        "core_environment": {
            "python": platform.python_version(),
            "seed": int(config.settings()["reproducibility"]["random_seed"]),
        },
        "chronos_environment": {
            "environment": chronos["runtime_environment"],
            "python": chronos["runtime_python"],
            "package": chronos["runtime_package"],
            "package_version": chronos["runtime_package_version"],
            "lockfile_sha256": chronos["runtime_lockfile_sha256"],
            "model_revision": chronos["runtime_model_revision"],
            "seed": int(chronos["runtime_seed"]),
            "device": chronos["runtime_device"],
        },
        "output_sha256": output_hashes,
        "replication_archive_status": "pending_deposit_gitignored_august_source_bytes",
        "interpretation": (
            "Case-local model and measurement-vintage sensitivity; not an ATT, "
            "variance decomposition, pooled estimate, or general AIS claim."
        ),
    }


def finalize() -> None:
    design, digest = _load()
    daily = pd.concat([
        pd.read_csv(config.path("model_vintage_matrix_core_daily_csv"), parse_dates=["date"]),
        pd.read_csv(
            config.path("model_vintage_matrix_chronos_daily_csv"),
            parse_dates=["date"],
        ),
    ], ignore_index=True)
    summary = pd.concat([
        pd.read_csv(config.path("model_vintage_matrix_core_summary_csv")),
        pd.read_csv(config.path("model_vintage_matrix_chronos_summary_csv")),
    ], ignore_index=True)
    validate_complete_matrix(daily, summary, design, digest)
    checks = pinned_self_checks(daily, summary)

    model_order = {
        model: index
        for index, model in enumerate(design["completion_contract"]["expected_models"])
    }
    vintage_order = {
        vintage: index
        for index, vintage in enumerate(
            design["completion_contract"]["expected_vintages"]
        )
    }
    daily["_vintage_order"] = daily["vintage"].map(vintage_order)
    daily["_model_order"] = daily["model"].map(model_order)
    daily = daily.sort_values(["_vintage_order", "_model_order", "date"]).drop(
        columns=["_vintage_order", "_model_order"]
    )
    summary["_vintage_order"] = summary["vintage"].map(vintage_order)
    summary["_model_order"] = summary["model"].map(model_order)
    summary = summary.sort_values(["_vintage_order", "_model_order"]).drop(
        columns=["_vintage_order", "_model_order"]
    )
    _write(daily, "model_vintage_matrix_daily_csv")
    _write(summary, "model_vintage_matrix_summary_csv")

    manifest = _matrix_manifest(design, digest, checks, summary)
    manifest_path = config.path("model_vintage_matrix_manifest_json")
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"wrote {manifest_path}")
    print("\n=== complete representative matrix ===")
    print(summary[[
        "vintage", "model", "n_scored_days", "observed_sum",
        "mean_daily_common_point_shortfall",
        "mean_daily_model_native_shortfall",
    ]].to_string(index=False))
    print("\nInterpretation guard: separate model and vintage axes; never average")
    print("vintages, call this a variance decomposition, or generalize beyond this case.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", required=True, choices=("core", "chronos", "finalize"))
    args = parser.parse_args()
    if args.phase == "core":
        run_core()
    elif args.phase == "chronos":
        run_chronos()
    else:
        finalize()


if __name__ == "__main__":
    main()
