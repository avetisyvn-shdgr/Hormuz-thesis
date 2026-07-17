"""Regenerate and verify the frozen PortWatch + LNG mechanism pipeline.

Usage from the repository root:
    .venv/bin/python scripts/run_all.py
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


STEPS = [
    ("Verify frozen raw snapshots", ["scripts/freeze_reproducibility.py", "--check"]),
    ("Build panel from frozen raw data", ["scripts/build_panel.py", "--frozen-raw"]),
    ("Align and audit panel", ["scripts/align_panel.py", "--from-interim"]),
    ("Render descriptive event-study figures", ["scripts/make_event_study.py"]),
    ("Export model diagnostics", ["scripts/run_model_diagnostics.py"]),
    ("Run chronological validation", ["scripts/run_baseline.py"]),
    ("Run AR-only and sensitivity counterfactuals", ["scripts/run_counterfactual.py"]),
    ("Quantify AIS-dark-vessel bound", ["scripts/run_ais_dark_bound.py"]),
    ("Run Bayesian structural counterfactual", ["scripts/run_bsts_counterfactual.py"]),
    ("Run temporal placebos", ["scripts/run_placebo_inference.py"]),
    ("Run independent-block and conformal inference", ["scripts/run_block_inference.py"]),
    ("Calibrate residual intervals", ["scripts/run_interval_calibration.py"]),
    ("Calibrate horizon-matched intervals", ["scripts/run_long_horizon_intervals.py"]),
    ("Run treatment-window robustness", ["scripts/run_treatment_robustness.py"]),
    ("Run spatial placebos", ["scripts/run_spatial_placebo.py"]),
    ("Apply Romano-Wolf multiplicity correction", ["scripts/run_multiplicity_correction.py"]),
    ("Run synthetic control", ["scripts/run_synthetic_control.py"]),
    ("Stress synthetic donors and donor-time placebos", ["scripts/run_synthetic_stress.py"]),
    ("Run optional LNG-only index robustness", ["scripts/run_lng_index_analysis.py"]),
    ("Build Q-Flex LNG terminal crosswalk", ["scripts/build_lng_terminal_crosswalk.py"]),
    ("Score Q-Flex voyage feasibility", ["scripts/run_voyage_feasibility.py"]),
    ("Build global LNG carrier frame", ["scripts/build_global_carrier_frame.py"]),
    ("Build global LNG terminal crosswalk", ["scripts/build_global_lng_terminal_crosswalk.py"]),
    ("Score global voyage feasibility", ["scripts/run_global_voyage_feasibility.py"]),
    ("Build maritime route-distance matrix", ["scripts/build_maritime_route_distances.py"]),
    ("Build inferred capacity-nautical miles", ["scripts/build_inferred_capacity_nautical_miles.py"]),
    ("Validate Gulf departures against WTO", ["scripts/validate_gulf_departures_against_wto.py"]),
    ("Build importer and basin exposure", ["scripts/build_importer_basin_exposure.py"]),
    ("Build importer customs outcomes", ["scripts/build_importer_outcomes.py"]),
    ("Build LNG rewiring network", ["scripts/build_lng_rewiring_network.py"]),
    ("Build LNG rewiring summary", ["scripts/build_lng_rewiring_summary.py"]),
    ("Build LNG rewiring graph metrics", ["scripts/build_lng_rewiring_graph_metrics.py"]),
    ("Build LNG network anomaly scores", ["scripts/build_lng_network_anomaly_scores.py"]),
    ("Build LNG reallocation stress model", ["scripts/build_lng_reallocation_model.py"]),
    ("Build LNG resilience typology", ["scripts/build_lng_resilience_typology.py"]),
    ("Render LNG network rewiring summary", ["scripts/make_network_rewiring_summary.py"]),
    ("Build modeled vessel-day estimates", ["scripts/build_vessel_day_estimates.py"]),
    ("Refresh vessel-data feasibility audit", ["scripts/run_vessel_data_feasibility.py"]),
    ("Refresh integrated mechanism results", ["scripts/make_mechanism_summary.py"]),
    ("Render inspectable run outputs", ["scripts/make_run_output.py"]),
    ("Refresh working results summary", ["scripts/make_results_summary.py"]),
    ("Recheck frozen raw snapshots", ["scripts/freeze_reproducibility.py", "--check"]),
    ("Run full test suite", ["-m", "pytest", "-q"]),
    (
        "Verify regenerated artifacts against committed manifest",
        ["scripts/freeze_reproducibility.py", "--verify"],
    ),
]


def main() -> int:
    env = os.environ.copy()
    env["PYTHONHASHSEED"] = "0"
    env["OMP_NUM_THREADS"] = "1"
    env["OPENBLAS_NUM_THREADS"] = "1"
    env["MKL_NUM_THREADS"] = "1"
    env["NUMEXPR_NUM_THREADS"] = "1"
    env.setdefault("MPLCONFIGDIR", "/tmp/lngfreight-matplotlib")
    for number, (label, args) in enumerate(STEPS, start=1):
        print(f"\n{'=' * 72}\n[{number:02d}/{len(STEPS):02d}] {label}\n{'=' * 72}", flush=True)
        subprocess.run([sys.executable, *args], cwd=ROOT, env=env, check=True)
    print("\nEND-TO-END RUN COMPLETED CLEANLY", flush=True)
    print(f"Report: {ROOT / 'reports' / 'run_output.md'}", flush=True)
    print(f"Comparison: {ROOT / 'data' / 'processed' / 'run_spec_comparison.csv'}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
