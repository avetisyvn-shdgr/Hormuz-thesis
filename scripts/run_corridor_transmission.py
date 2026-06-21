"""Generate the exploratory AR-only corridor-transmission results (Task 7).

This runs the locked AR-only baseline over every eligible corridor, forms the
scaled signed deviation, applies the frozen shared-placebo Romano-Wolf contract,
reports basin point summaries, and writes a manifest. It is EXPLORATORY: the
specification was frozen before any post-cutoff value was viewed, but supervisor
sign-off has not been obtained, so no result may be described as "admitted" or
"significant". The nine-window design has a finite-sample p-value floor of 0.10.

Kept outside run_all.py by design.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lngfreight import config  # noqa: E402
from lngfreight.corridor_admission import load_corridor_admission_protocol  # noqa: E402
from lngfreight.corridor_inference import (  # noqa: E402
    corridor_romano_wolf,
    load_corridor_inference_protocol,
)
from lngfreight.corridor_transmission import (  # noqa: E402
    ar_baseline_fold_mase,
    ar_window_statistic,
    basin_point_summary,
    build_corridor_statistics,
)
from lngfreight.spatial import wide_chokepoint_panel  # noqa: E402


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _leakage_check(protocol) -> dict[str, object]:
    """Prove a corridor's deviation is invariant to other corridors' post data."""
    target, corridor = "n_tanker", "strait_of_hormuz"
    wide = wide_chokepoint_panel(target, start=str(protocol.history_start.date()), end="2026-06-01")
    base = ar_window_statistic(
        wide[corridor], history_start=protocol.history_start,
        origin=protocol.cutoff, horizon_days=protocol.post_horizon_days,
    )["statistic_value"]
    perturbed = wide.copy()
    post = perturbed.index >= protocol.cutoff
    for other in perturbed.columns:
        if other != corridor:
            perturbed.loc[post, other] = perturbed.loc[post, other] + 1000.0
    after = ar_window_statistic(
        perturbed[corridor], history_start=protocol.history_start,
        origin=protocol.cutoff, horizon_days=protocol.post_horizon_days,
    )["statistic_value"]
    if not np.isclose(base, after):
        raise AssertionError("leakage detected: corridor deviation changed with others' data.")
    return {"corridor_checked": f"{target}/{corridor}", "invariant_to_other_corridors": True}


def main() -> None:
    inference = load_corridor_inference_protocol()
    admission = load_corridor_admission_protocol()

    observed, placebo = build_corridor_statistics(inference)
    rw = corridor_romano_wolf(observed, placebo, inference)

    deviations = observed.assign(
        hypothesis=lambda d: d["model"] + "::" + d["target"] + "::" + d["corridor"]
    )
    results = rw.merge(
        deviations[[
            "hypothesis", "target", "corridor", "n_scored",
            "pre_period_mean", "observed_sum", "counterfactual_sum",
        ]],
        on="hypothesis",
        how="left",
        validate="one_to_one",
    )
    metadata = pd.read_csv(config.ROOT / "data/processed/corridor_transmission_metadata.csv")
    basin_map = metadata.set_index("slug")["basin_group"]
    results["basin_group"] = results["corridor"].map(basin_map)
    results["signed_deviation"] = results["observed_statistic"]
    results["interpretation"] = np.where(
        results["signed_deviation"] < 0, "below_counterfactual", "above_counterfactual"
    )
    results = results.sort_values(
        ["target", "signed_deviation"], ignore_index=True
    )

    basin = basin_point_summary(observed, metadata)
    ar_mase = ar_baseline_fold_mase(
        admission.shared_test_origins,
        history_start=admission.history_start,
        cutoff=admission.cutoff,
        eligible_corridors=admission.eligible_corridors,
        horizon_days=admission.horizon_days,
    )
    leakage = _leakage_check(inference)

    paths = config.settings()["paths"]
    results_path = config.ROOT / paths["corridor_transmission_results_csv"]
    basin_path = config.ROOT / paths["corridor_transmission_basin_csv"]
    mase_path = config.ROOT / paths["corridor_transmission_ar_mase_csv"]
    manifest_path = config.ROOT / paths["corridor_transmission_results_manifest_json"]

    results.to_csv(results_path, index=False)
    basin.to_csv(basin_path, index=False)
    ar_mase.to_csv(mase_path, index=False)

    manifest = {
        "schema_version": 1,
        "status": inference.status,
        "is_exploratory": True,
        "supervisor_signoff": False,
        "primary_estimator": "ar_lag1_7",
        "model_family": inference.family_name,
        "finite_sample_p_value_floor": inference.finite_sample_p_value_floor,
        "post_horizon_days": inference.post_horizon_days,
        "n_hypotheses": int(len(results)),
        "n_shared_placebo_origins": inference.expected_joint_draws,
        "leakage_check": leakage,
        "basin_interval_policy": inference.basin_interval_policy,
        "outputs_sha256": {
            results_path.name: _sha256(results_path),
            basin_path.name: _sha256(basin_path),
            mase_path.name: _sha256(mase_path),
        },
        "interpretation_guard": [
            "Exploratory: specification frozen pre-results; no supervisor sign-off.",
            "AR-only is the locked primary estimator; no causal/routing language.",
            "Adjusted p-values floor at 0.10; do not claim 5% significance.",
            "Basin output is point-only and never sums corridors.",
        ],
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    pd.set_option("display.width", 220)
    pd.set_option("display.max_columns", None)
    headline = results.sort_values("signed_deviation").head(8)
    print("=== Most below-counterfactual corridors (exploratory, p-floor = 0.10) ===")
    print(headline[[
        "target", "corridor", "basin_group", "signed_deviation",
        "raw_resampling_p_value", "romano_wolf_p_value", "n_scored",
    ]].to_string(index=False))
    print("\n=== Most above-counterfactual corridors ===")
    print(results.sort_values("signed_deviation", ascending=False).head(6)[[
        "target", "corridor", "basin_group", "signed_deviation",
        "raw_resampling_p_value", "romano_wolf_p_value",
    ]].to_string(index=False))
    print("\n=== Basin point summary (NOT additive) ===")
    print(basin.to_string(index=False))
    print(f"\nAR-only baseline median MASE across {ar_mase['n_folds_scored'].iloc[0]} folds: "
          f"{ar_mase['median_mase'].median():.3f} (median over corridors)")
    print(f"\nLeakage check: {leakage}")
    print(f"\nwrote {results_path}")
    print(f"wrote {basin_path}")
    print(f"wrote {mase_path}")
    print(f"wrote {manifest_path}")


if __name__ == "__main__":
    main()
