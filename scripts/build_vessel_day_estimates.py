"""Estimate sailing vessel-days under explicit LNG-carrier speed assumptions."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from hormuz_throughput import config  # noqa: E402
from hormuz_throughput.vessel_days import (  # noqa: E402
    add_elapsed_time_diagnostics,
    elapsed_time_diagnostics,
    modeled_vessel_day_summary,
    vessel_day_pre_post_comparison,
)


def main() -> None:
    settings = config.settings()
    paths = settings["paths"]
    policy = settings["vessel_data_feasibility"]["vessel_day_estimation"]
    voyages = pd.read_csv(
        config.ROOT / paths["inferred_capacity_nm_voyages_csv"], dtype={"imo": str}
    )
    diagnosed = add_elapsed_time_diagnostics(
        voyages,
        min_implied_speed_knots=float(policy["elapsed_implied_speed_min_knots"]),
        max_implied_speed_knots=float(policy["elapsed_implied_speed_max_knots"]),
    )
    summary = modeled_vessel_day_summary(
        diagnosed, speeds_knots=[float(value) for value in policy["speed_sensitivity_knots"]]
    )
    comparison = vessel_day_pre_post_comparison(summary)
    diagnostics = elapsed_time_diagnostics(diagnosed, primary_radius_km=30)
    diagnostics["policy"] = policy
    diagnostics["measure"] = "modeled_sailing_vessel_days"
    diagnostics["observed_ais_duration"] = False
    diagnostics["causal_interpretation_supported"] = False

    outputs = {
        paths["vessel_day_voyage_diagnostics_csv"]: diagnosed,
        paths["vessel_day_period_summary_csv"]: summary,
        paths["vessel_day_comparison_csv"]: comparison,
    }
    for relative_path, frame in outputs.items():
        output = config.ROOT / relative_path
        output.parent.mkdir(parents=True, exist_ok=True)
        frame.to_csv(output, index=False)
        print(f"wrote {output}")
    diagnostics_path = config.ROOT / paths["vessel_day_diagnostics_json"]
    diagnostics_path.write_text(json.dumps(diagnostics, indent=2, sort_keys=True) + "\n")
    print(f"wrote {diagnostics_path}")
    primary = comparison.loc[
        comparison["terminal_match_radius_km"].eq(30)
        & comparison["route_specification"].eq("expanded_60nm_snap")
        & comparison["speed_knots"].eq(float(policy["primary_speed_knots"]))
    ]
    print(primary.to_string(index=False))


if __name__ == "__main__":
    main()
