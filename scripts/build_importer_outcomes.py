"""Build the importer LNG outcome series (task V2) from frozen snapshots."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lngfreight import config  # noqa: E402
from lngfreight.importer_outcomes import build_outcomes, outcomes_summary  # noqa: E402


def main() -> None:
    probe_dir = config.path("data_raw") / "backup_pathway_probe_20260621"
    customs_dir = config.path("importer_customs_dir")
    eurostat_path = config.ROOT / config.settings()["paths"][
        "eurostat_lng_eu27_by_partner_json"
    ]
    frame = build_outcomes(
        probe_dir, customs_dir=customs_dir, eurostat_path=eurostat_path
    )
    summary = outcomes_summary(frame)

    frame_path = config.path("data_processed") / "importer_outcomes.csv"
    summary_path = config.path("data_processed") / "importer_outcomes_summary.json"
    frame.to_csv(frame_path, index=False)
    summary_path.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"wrote {frame_path}")
    print(f"wrote {summary_path}")
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
