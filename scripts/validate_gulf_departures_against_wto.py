"""Validate GFW-inferred Gulf LNG departures against the WTO/AXSMarine index."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lngfreight import config  # noqa: E402
from lngfreight.registry import get_variable  # noqa: E402
from lngfreight.wto_validation import (  # noqa: E402
    build_gulf_departure_daily,
    complete_weekly_totals,
    validation_correlations,
    validation_summary,
)


def main() -> None:
    settings = config.settings()
    paths = settings["paths"]
    policy = settings["vessel_data_feasibility"]["wto_departure_validation"]
    windows = policy["comparison_windows"]
    start = min(bounds[0] for bounds in windows.values())
    end = max(bounds[1] for bounds in windows.values())

    voyages = pd.read_csv(
        config.ROOT / paths["inferred_capacity_nm_voyages_csv"], dtype={"imo": str}
    )
    wto = get_variable("wto_hormuz_lng_outbound_index", start=start, end=end)
    daily, terminal = build_gulf_departure_daily(
        voyages,
        wto,
        gulf_export_project_ids=list(policy["gulf_export_project_ids"]),
        terminal_match_radius_km=int(policy["terminal_match_radius_km"]),
        comparison_windows=windows,
    )
    weekly = complete_weekly_totals(daily)
    correlations = validation_correlations(
        daily, weekly, lags=list(policy["daily_lag_sensitivity_days"])
    )
    summary = validation_summary(daily, correlations)
    summary["policy"] = policy

    outputs = {
        paths["gulf_departure_validation_daily_csv"]: daily,
        paths["gulf_departure_validation_weekly_csv"]: weekly,
        paths["gulf_departure_validation_correlations_csv"]: correlations,
        paths["gulf_departure_validation_terminal_csv"]: terminal,
    }
    for relative_path, frame in outputs.items():
        output = config.ROOT / relative_path
        output.parent.mkdir(parents=True, exist_ok=True)
        frame.to_csv(output, index=False)
        print(f"wrote {output}")
    summary_path = config.ROOT / paths["gulf_departure_validation_summary_json"]
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(f"wrote {summary_path}")
    print(json.dumps(summary["pre_post_changes"], indent=2, sort_keys=True))
    print(f"directional_agreement={summary['directional_agreement']}")


if __name__ == "__main__":
    main()
