"""Write or verify the provenance-limited Bloomberg-layer checksum freeze."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lngfreight import config  # noqa: E402


FILES = [
    "config/settings.yaml",
    "config/sources.yaml",
    "config/bloomberg_exports.yaml",
    "config/bloomberg_export_manifest.schema.json",
    "src/lngfreight/registry.py",
    "src/lngfreight/sources/__init__.py",
    "src/lngfreight/bloomberg_admission.py",
    "src/lngfreight/bloomberg_market.py",
    "src/lngfreight/freight_counterfactual.py",
    "src/lngfreight/freight_integration.py",
    "src/lngfreight/sources/bloomberg_transcription.py",
    "scripts/audit_bloomberg_exports.py",
    "scripts/build_bloomberg_weekly_panel.py",
    "scripts/make_bloomberg_freight_descriptives.py",
    "scripts/run_bloomberg_freight_counterfactual.py",
    "scripts/build_bloomberg_market_context.py",
    "scripts/make_bloomberg_mechanism_integration.py",
    "scripts/freeze_bloomberg_layer.py",
    "scripts/run_all.py",
    "data/processed/bloomberg_export_admission.csv",
    "data/processed/bloomberg_export_admission.json",
    "data/processed/lng_freight_weekly_panel.csv",
    "data/processed/lng_freight_weekly_quality.csv",
    "data/processed/lng_freight_weekly_manifest.json",
    "data/processed/lng_freight_descriptive_weekly.csv",
    "data/processed/lng_freight_descriptive_summary.csv",
    "data/processed/lng_freight_validation_scores.csv",
    "data/processed/lng_freight_counterfactual_weekly.csv",
    "data/processed/lng_freight_counterfactual_summary.csv",
    "data/processed/lng_freight_time_placebos.csv",
    "data/processed/lng_freight_counterfactual_manifest.json",
    "data/processed/freight_market_context.csv",
    "data/processed/freight_market_context_quality.csv",
    "data/processed/freight_market_context_manifest.json",
    "data/processed/freight_mechanism_weekly.csv",
    "data/processed/freight_mechanism_summary.csv",
    "data/processed/freight_mechanism_manifest.json",
    "reports/figures/lng_freight_market_descriptive.png",
    "reports/figures/lng_freight_market_descriptive.pdf",
    "reports/figures/lng_freight_counterfactual.png",
    "reports/figures/lng_freight_counterfactual.pdf",
    "reports/figures/freight_market_context.png",
    "reports/figures/freight_market_context.pdf",
    "reports/figures/freight_mechanism_integration.png",
    "reports/figures/freight_mechanism_integration.pdf",
    # Registry-captured Bloomberg payload snapshots under data/raw. These are
    # deliberately excluded from the global SHA256SUMS.vessel sweep (they exist
    # only where the opt-in branch has run), so this freeze is their sole
    # integrity ledger. The originals/ workbooks are additionally pinned by
    # config/bloomberg_exports.yaml and verified on every registry load.
    "data/raw/bloomberg_transcription/fearnleys_lng_spot_east_suez__fearnleys_lng_spot_east_suez.csv",
    "data/raw/bloomberg_transcription/fearnleys_lng_spot_west_suez__fearnleys_lng_spot_west_suez.csv",
    "data/raw/bloomberg_transcription/fearnleys_lng_one_year_time_charter__fearnleys_lng_one_year_time_charter.csv",
    "data/raw/bloomberg_transcription/ttf_gas__netherlands_ttf_day_ahead.csv",
    "data/raw/bloomberg_transcription/vlsfo_singapore__clearlynx_vlsfo_singapore.csv",
    "data/raw/bloomberg_transcription/originals/fearnleys_lng_tanker_east_of_suez_155_165k_cbm_spot_rate__8e06dcec9dec.xlsx",
    "data/raw/bloomberg_transcription/originals/fearnleys_lng_tanker_west_of_suez_155_165k_cbm_spot_rate__053af2af960a.xlsx",
    "data/raw/bloomberg_transcription/originals/fearnleys_lng_tanker_1y_time_charter_155_165k_cbm__34e7ee8e60c5.xlsx",
    "data/raw/bloomberg_transcription/originals/netherlands_ttf_natural_gas_forward_day_ahead__9f430cfd34c3.xlsx",
    "data/raw/bloomberg_transcription/originals/clearlynx_vlsfo_bunker_fuel_spot_price_singapore__dac372540e55.xlsx",
]


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _current() -> dict[str, str]:
    missing = [relative for relative in FILES if not (config.ROOT / relative).is_file()]
    if missing:
        raise FileNotFoundError(f"Bloomberg freeze inputs missing: {missing}")
    return {relative: _digest(config.ROOT / relative) for relative in FILES}


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    path = config.path("bloomberg_layer_freeze_json")
    current = _current()
    if args.write:
        payload = {
            "schema_version": 1,
            "generated_utc": datetime.now(timezone.utc).isoformat(),
            "designation": "provenance_limited_secondary",
            "strict_source_admission": False,
            "activation_status": "dormant_secondary_only",
            "files_sha256": current,
        }
        path.write_text(f"{json.dumps(payload, indent=2)}\n", encoding="utf-8")
        print(path)
        return 0
    if not path.is_file():
        raise FileNotFoundError(f"Bloomberg freeze manifest missing: {path}")
    expected = json.loads(path.read_text(encoding="utf-8"))["files_sha256"]
    mismatches = {
        key: {"expected": expected.get(key), "actual": current.get(key)}
        for key in sorted(set(expected) | set(current))
        if expected.get(key) != current.get(key)
    }
    if mismatches:
        print(json.dumps(mismatches, indent=2))
        return 2
    print(f"Bloomberg layer freeze verified: {len(current)} files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
