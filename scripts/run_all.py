"""Run the frozen PortWatch fallback pipeline end to end.

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
    ("Export model diagnostics", ["scripts/run_model_diagnostics.py"]),
    ("Run chronological validation", ["scripts/run_baseline.py"]),
    ("Run AR-only and sensitivity counterfactuals", ["scripts/run_counterfactual.py"]),
    ("Run temporal placebos", ["scripts/run_placebo_inference.py"]),
    ("Calibrate residual intervals", ["scripts/run_interval_calibration.py"]),
    ("Calibrate horizon-matched intervals", ["scripts/run_long_horizon_intervals.py"]),
    ("Run treatment-window robustness", ["scripts/run_treatment_robustness.py"]),
    ("Run spatial placebos", ["scripts/run_spatial_placebo.py"]),
    ("Run synthetic control", ["scripts/run_synthetic_control.py"]),
    ("Render inspectable run outputs", ["scripts/make_run_output.py"]),
    ("Refresh working results summary", ["scripts/make_results_summary.py"]),
    ("Freeze artifact manifest", ["scripts/freeze_reproducibility.py"]),
    ("Recheck frozen raw snapshots", ["scripts/freeze_reproducibility.py", "--check"]),
    ("Run full test suite", ["-m", "pytest", "-q"]),
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
