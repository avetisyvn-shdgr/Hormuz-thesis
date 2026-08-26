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
RUN_TRANSCRIPT = ROOT / "reports" / "reproducibility_run_transcript.txt"


STEPS = [
    ("Verify frozen raw snapshots", ["scripts/freeze_reproducibility.py", "--check"]),
    ("Build panel from frozen raw data", ["scripts/build_panel.py", "--frozen-raw"]),
    ("Align and audit panel", ["scripts/align_panel.py", "--from-interim"]),
    ("Render descriptive event-study figures", ["scripts/make_event_study.py"]),
    ("Export model diagnostics", ["scripts/run_model_diagnostics.py"]),
    ("Run chronological validation", ["scripts/run_baseline.py"]),
    ("Run AR-only and sensitivity counterfactuals", ["scripts/run_counterfactual.py"]),
    (
        "Run matched-horizon admitted Chronos-2 counterfactual",
        [
            ".venv-bench/bin/python",
            "scripts/run_tsfm_counterfactual.py",
            "--model",
            "chronos2",
            "--acknowledge-benchmark-only",
        ],
    ),
    ("Refresh deterministic TSFM provenance", ["scripts/freeze_tsfm_run.py"]),
    ("Quantify AIS-dark-vessel bound", ["scripts/run_ais_dark_bound.py"]),
    ("Run Bayesian structural counterfactual", ["scripts/run_bsts_counterfactual.py"]),
    ("Run temporal placebos", ["scripts/run_placebo_inference.py"]),
    ("Run independent-block and conformal inference", ["scripts/run_block_inference.py"]),
    ("Calibrate residual intervals", ["scripts/run_interval_calibration.py"]),
    (
        # Depends on the counterfactual, the block-bootstrap intervals, the
        # conformal intervals, and the legacy AIS-dark bound it cross-checks.
        "Map the observability/counterfactual breakdown frontier",
        ["scripts/run_observability_breakdown_frontier.py"],
    ),
    ("Build full-horizon empirical placebo bands", ["scripts/run_long_horizon_intervals.py"]),
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
    (
        "Build LNG rewiring post-month sensitivity",
        ["scripts/build_lng_rewiring_post_month_sensitivity.py"],
    ),
    (
        "Build LNG typology threshold sensitivity",
        ["scripts/build_lng_typology_threshold_sensitivity.py"],
    ),
    ("Render LNG network rewiring summary", ["scripts/make_network_rewiring_summary.py"]),
    ("Build modeled vessel-day estimates", ["scripts/build_vessel_day_estimates.py"]),
    ("Refresh vessel-data feasibility audit", ["scripts/run_vessel_data_feasibility.py"]),
    ("Refresh integrated mechanism results", ["scripts/make_mechanism_summary.py"]),
    ("Render inspectable run outputs", ["scripts/make_run_output.py"]),
    ("Refresh working results summary", ["scripts/make_results_summary.py"]),
    (
        "Render and verify complete manuscript figure set",
        ["scripts/render_thesis_figures.py"],
    ),
    ("Audit provenance coverage", ["scripts/audit_provenance.py"]),
    ("Recheck frozen raw snapshots", ["scripts/freeze_reproducibility.py", "--check"]),
    ("Run full test suite", ["-m", "pytest", "-q"]),
    (
        "Verify regenerated artifacts against committed manifest",
        ["scripts/freeze_reproducibility.py", "--verify"],
    ),
]

BLOOMBERG_STEPS = [
    ("Audit provenance-limited Bloomberg workbooks", ["scripts/audit_bloomberg_exports.py"]),
    ("Build weekly LNG freight assessment panel", ["scripts/build_bloomberg_weekly_panel.py"]),
    ("Render LNG freight descriptives", ["scripts/make_bloomberg_freight_descriptives.py"]),
    ("Run secondary freight counterfactuals", ["scripts/run_bloomberg_freight_counterfactual.py"]),
    ("Build TTF and VLSFO context layer", ["scripts/build_bloomberg_market_context.py"]),
    ("Integrate physical and monetary evidence", ["scripts/make_bloomberg_mechanism_integration.py"]),
    ("Verify Bloomberg layer freeze", ["scripts/freeze_bloomberg_layer.py", "--verify"]),
]


def _step_command(args: list[str]) -> list[str]:
    if args and args[0].endswith("/bin/python"):
        interpreter = ROOT / args[0]
        if not interpreter.exists():
            raise FileNotFoundError(
                f"Required isolated interpreter not found: {interpreter}"
            )
        return [str(interpreter), *args[1:]]
    return [sys.executable, *args]


def _emit(text: str, transcript) -> None:
    print(text, end="", flush=True)
    transcript.write(text)
    transcript.flush()


def _run_step(command: list[str], env: dict[str, str], transcript) -> None:
    process = subprocess.Popen(
        command,
        cwd=ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    assert process.stdout is not None
    for line in process.stdout:
        _emit(line, transcript)
    return_code = process.wait()
    if return_code:
        raise subprocess.CalledProcessError(return_code, command)


def main() -> int:
    env = os.environ.copy()
    env["PYTHONHASHSEED"] = "0"
    env["OMP_NUM_THREADS"] = "1"
    env["OPENBLAS_NUM_THREADS"] = "1"
    env["MKL_NUM_THREADS"] = "1"
    env["NUMEXPR_NUM_THREADS"] = "1"
    env["CUBLAS_WORKSPACE_CONFIG"] = ":4096:8"
    env["PYTHONUNBUFFERED"] = "1"
    env.setdefault("MPLCONFIGDIR", "/tmp/lngfreight-matplotlib")
    env.setdefault("HF_HUB_OFFLINE", "1")
    env.setdefault("TRANSFORMERS_OFFLINE", "1")
    steps = list(STEPS)
    if env.get("ENABLE_BLOOMBERG_LAYER") == "1":
        if not env.get("BLOOMBERG_EXPORT_DIR"):
            raise RuntimeError(
                "ENABLE_BLOOMBERG_LAYER=1 requires BLOOMBERG_EXPORT_DIR. "
                "The default free-data pipeline remains independent."
            )
        insertion = next(
            index
            for index, (label, _) in enumerate(steps)
            if label == "Audit provenance coverage"
        )
        steps[insertion:insertion] = BLOOMBERG_STEPS
    RUN_TRANSCRIPT.parent.mkdir(parents=True, exist_ok=True)
    with RUN_TRANSCRIPT.open("w", encoding="utf-8", buffering=1) as transcript:
        _emit(
            "LNG freight reproducibility run transcript\n"
            f"step_count={len(steps)}\n"
            f"bloomberg_layer_enabled={env.get('ENABLE_BLOOMBERG_LAYER') == '1'}\n",
            transcript,
        )
        for number, (label, args) in enumerate(steps, start=1):
            _emit(
                f"\n{'=' * 72}\n"
                f"[{number:02d}/{len(steps):02d}] {label}\n"
                f"{'=' * 72}\n",
                transcript,
            )
            _run_step(_step_command(args), env, transcript)
        _emit("\nEND-TO-END RUN COMPLETED CLEANLY\n", transcript)
        _emit(f"Report: {ROOT / 'reports' / 'run_output.md'}\n", transcript)
        _emit(
            f"Comparison: "
            f"{ROOT / 'data' / 'processed' / 'run_spec_comparison.csv'}\n",
            transcript,
        )
        _emit(f"Transcript: {RUN_TRANSCRIPT}\n", transcript)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
