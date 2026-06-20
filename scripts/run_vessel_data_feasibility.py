"""Refresh the local LNG vessel-data feasibility audit.

This script does not call GFW. It records whether the token and pre-committed
sample inputs exist, profiles the already-frozen aggregate sources, and writes a
machine-readable gate report. Credentialed API retrieval is added only after a
personal token is available and must go through a registered source adapter.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lngfreight import config  # noqa: E402
from lngfreight.feasibility import build_vessel_feasibility_report  # noqa: E402


def main() -> None:
    credentials = {
        name: bool(os.environ.get(name))
        for name in ("GFW_API_TOKEN", "SPARK_CLIENT_ID", "SPARK_CLIENT_SECRET")
    }
    report = build_vessel_feasibility_report(
        config.ROOT, config.settings(), credentials
    )
    out = config.path("data_processed") / "vessel_data_feasibility.json"
    out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(f"wrote {out}")
    print(f"empirical branch: {report['empirical_vessel_branch']['status']}")
    print(f"simulation fallback: {report['simulation_fallback']['status']}")
    print(f"Spark extension: {report['spark_extension']['status']}")
    for blocker in report["empirical_vessel_branch"]["blockers"]:
        print(f" - {blocker}")


if __name__ == "__main__":
    main()

