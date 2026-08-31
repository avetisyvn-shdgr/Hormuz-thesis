"""Build the importer LNG outcome series (task V2) from frozen snapshots."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from hormuz_throughput import config  # noqa: E402
from hormuz_throughput.importer_outcomes import build_outcomes, outcomes_summary  # noqa: E402
from hormuz_throughput.registry import RegisteredArtifact, get_variable  # noqa: E402


def main() -> None:
    probe_dir = config.path("data_raw") / "backup_pathway_probe_20260621"
    artifact_names = [
        "korea_lng_by_origin_snapshot",
        "taiwan_lng_by_origin_snapshot",
        "china_lng_by_origin_snapshot",
        "india_lng_by_origin_snapshot",
        "japan_lng_by_origin_snapshot",
    ]
    artifacts = [
        get_variable(name, query={"consumer": "build_importer_outcomes"})
        for name in artifact_names
    ]
    eurostat = get_variable(
        "eurostat_lng_eu27_by_partner_snapshot",
        query={"consumer": "build_importer_outcomes"},
    )
    if not all(isinstance(item, RegisteredArtifact) for item in [*artifacts, eurostat]):
        raise TypeError("importer-outcome inputs must resolve as artifacts")
    customs_dirs = {item.path.parent for item in artifacts}
    if len(customs_dirs) != 1:
        raise ValueError("importer-customs artifacts must share one directory")
    customs_dir = customs_dirs.pop()
    eurostat_path = eurostat.path
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
