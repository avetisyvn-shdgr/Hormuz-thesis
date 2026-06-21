"""Basin-interval coverage simulation for the Task 3 inference contract.

Produces the simulation evidence required before the corridor protocol may keep
basin output ``point_only``. This is a synthetic methodology study: it does not
read the corridor panel, does not touch post-cutoff observations and needs no
supervisor approval. It is deliberately kept outside ``run_all.py``.

Outputs:
- basin_interval_coverage_csv: per-scenario, per-method empirical coverage;
- basin_interval_coverage_summary_json: the decision summary and the best
  achievable coverage under the realistic design.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lngfreight import config  # noqa: E402
from lngfreight.basin_coverage import (  # noqa: E402
    BASIN_INTERVAL_METHODS,
    default_scenarios,
    run_coverage_grid,
)

ALPHA = 0.20
N_REPLICATIONS = 4000
SEED = 20260621
COVERAGE_TOLERANCE = 0.03
REALISTIC_SCENARIO = "realistic_design_nine_draws"


def main() -> None:
    grid = run_coverage_grid(
        default_scenarios(),
        alpha=ALPHA,
        n_replications=N_REPLICATIONS,
        seed=SEED,
        coverage_tolerance=COVERAGE_TOLERANCE,
    )

    csv_path = config.ROOT / config.settings()["paths"]["basin_interval_coverage_csv"]
    grid.to_csv(csv_path, index=False)

    realistic = grid.loc[grid["scenario"].eq(REALISTIC_SCENARIO)]
    best_realistic = realistic.loc[realistic["empirical_coverage"].idxmax()]
    any_method_passes_realistic = bool(realistic["meets_nominal_coverage"].any())

    summary = {
        "purpose": "Task 3 acceptance check: basin interval coverage evidence.",
        "synthetic_only": True,
        "uses_real_corridor_panel": False,
        "nominal_coverage": 1.0 - ALPHA,
        "coverage_tolerance": COVERAGE_TOLERANCE,
        "n_replications": N_REPLICATIONS,
        "seed": SEED,
        "methods_evaluated": list(BASIN_INTERVAL_METHODS),
        "realistic_scenario": REALISTIC_SCENARIO,
        "best_method_under_realistic_design": str(best_realistic["method"]),
        "best_coverage_under_realistic_design": float(best_realistic["empirical_coverage"]),
        "any_method_meets_nominal_under_realistic_design": any_method_passes_realistic,
        "decision": (
            "keep_basin_point_only"
            if not any_method_passes_realistic
            else "reconsider_basin_interval"
        ),
    }
    json_path = config.ROOT / config.settings()["paths"]["basin_interval_coverage_summary_json"]
    json_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    pd.set_option("display.width", 200)
    pd.set_option("display.max_columns", None)
    print(grid[[
        "scenario", "method", "corridor_correlation", "n_placebo_draws",
        "double_count_overlap", "nominal_coverage", "empirical_coverage",
        "coverage_mc_se", "mean_interval_width", "meets_nominal_coverage",
    ]].to_string(index=False))
    print()
    print(json.dumps(summary, indent=2, sort_keys=True))
    print(f"\nwrote {csv_path}")
    print(f"wrote {json_path}")
    print("\nInterpretation guard:")
    print(" - Synthetic study; no corridor panel or post-cutoff data is read.")
    print(" - placebo_reference_as_interval is the named anti-pattern and never covers.")
    print(" - A joint covariance-aware interval only reaches nominal coverage under")
    print("   large draws AND no double counting; the realistic 9-draw design fails.")


if __name__ == "__main__":
    main()
