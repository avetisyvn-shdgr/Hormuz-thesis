"""Run the Phase 0 Bloomberg workbook source-admission audit."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from lngfreight import config  # noqa: E402
from lngfreight.bloomberg_admission import (  # noqa: E402
    audit_export,
    flatten_result,
    load_manifest,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Audit local Bloomberg workbooks without activating or modelling them."
        )
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=ROOT / "config/bloomberg_exports.yaml",
    )
    parser.add_argument(
        "--export-dir",
        type=Path,
        help="Local workbook directory; otherwise use the manifest environment variable.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "data/processed",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit with status 2 when any candidate remains blocked.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest = load_manifest(args.manifest)
    env_name = manifest["export_directory_env"]
    configured_dir = args.export_dir or (
        Path(os.environ[env_name]) if os.environ.get(env_name) else None
    )
    if configured_dir is None:
        raise RuntimeError(
            f"Set {env_name} to the licensed-export directory or pass --export-dir."
        )
    export_dir = configured_dir.expanduser().resolve()

    settings = config.settings()["study_window"]
    results = [
        audit_export(
            name,
            spec,
            export_dir,
            study_start=settings["full_start"],
            study_end=settings["full_end"],
            treatment_cutoff=settings["primary_treatment_cutoff"],
        )
        for name, spec in manifest["series"].items()
    ]
    args.output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = args.output_dir / "bloomberg_export_admission.csv"
    json_path = args.output_dir / "bloomberg_export_admission.json"
    pd.DataFrame([flatten_result(result) for result in results]).to_csv(
        csv_path, index=False
    )
    payload = {
        "schema_version": 1,
        "authorized_vintage": manifest["governance"]["authorized_date"],
        "manifest": (
            str(args.manifest.resolve().relative_to(ROOT.resolve()))
            if args.manifest.resolve().is_relative_to(ROOT.resolve())
            else args.manifest.name
        ),
        "export_directory_reference": f"environment_or_command_line:{env_name}",
        "export_directory_name": export_dir.name,
        "study_window": {
            "start": settings["full_start"],
            "end": settings["full_end"],
            "treatment_cutoff": settings["primary_treatment_cutoff"],
        },
        "summary": {
            "candidate_count": len(results),
            "admitted_count": sum(result["admitted"] for result in results),
            "blocked_count": sum(not result["admitted"] for result in results),
            "all_admitted": all(result["admitted"] for result in results),
        },
        "series": results,
    }
    json_path.write_text(f"{json.dumps(payload, indent=2)}\n", encoding="utf-8")
    print(
        f"Bloomberg admission audit: {payload['summary']['admitted_count']} admitted, "
        f"{payload['summary']['blocked_count']} blocked."
    )
    print(csv_path)
    print(json_path)
    if args.strict and not payload["summary"]["all_admitted"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
