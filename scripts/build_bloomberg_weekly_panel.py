"""Build the provenance-limited weekly LNG freight assessment panel."""
from __future__ import annotations

import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lngfreight import config  # noqa: E402
from lngfreight.bloomberg_admission import load_manifest  # noqa: E402
from lngfreight.bloomberg_market import (  # noqa: E402
    build_weekly_freight_panel,
    load_freight_series,
)


def main() -> None:
    window = config.settings()["study_window"]
    manifest = load_manifest(config.ROOT / "config/bloomberg_exports.yaml")
    frames = load_freight_series(window["full_start"], window["full_end"])
    panel, quality, output_manifest = build_weekly_freight_panel(
        frames,
        manifest,
        study_start=window["full_start"],
        study_end=window["full_end"],
        treatment_cutoff=window["primary_treatment_cutoff"],
    )
    panel_path = config.path("lng_freight_weekly_panel_csv")
    quality_path = config.path("lng_freight_weekly_quality_csv")
    manifest_path = config.path("lng_freight_weekly_manifest_json")
    panel.to_csv(panel_path, index=False, date_format="%Y-%m-%d")
    quality.to_csv(quality_path, index=False)
    manifest_path.write_text(
        f"{json.dumps(output_manifest, indent=2)}\n", encoding="utf-8"
    )
    print(panel_path)
    print(quality_path)
    print(manifest_path)


if __name__ == "__main__":
    main()
