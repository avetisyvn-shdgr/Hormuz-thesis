"""Data-driven donor-contamination stress test for the synthetic-control SPOF.

Implements the two pre-committed hardenings from docs/SUTVA_CONTAMINATION_AUDIT.md:
(1) a contamination stress test across donor screens, and (2) a donor-influence
diagnostic that screens donors by their own post-treatment change sign. The
question answered: does the Hormuz synthetic-control separation survive when every
rerouting-suspect donor is removed (the pessimistic screen)?

This strengthens a corroboration layer; it is not the anchor. The AR-only
within-unit estimator remains primary and is immune to this failure mode.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from lngfreight import config  # noqa: E402
from lngfreight.donor_screen import (  # noqa: E402
    build_screens,
    donor_directional_deviation,
    screen_agreement,
)
from lngfreight.inference import empirical_p_value  # noqa: E402
from lngfreight.spatial import chokepoint_metadata, wide_chokepoint_panel  # noqa: E402
from lngfreight.synthetic import scale_by_pre_period_mean  # noqa: E402
from lngfreight.validation import resolve_cutoff  # noqa: E402
from run_synthetic_control import TREATED, _fit_unit  # noqa: E402

HISTORY_START = pd.Timestamp("2022-01-01")
HORIZON_DAYS = 94
MIN_SCORED_DAYS = 76
VALUE_COLS = ["n_tanker", "capacity_tanker"]
CONTAINMENT_SEPARATION_FLOOR = 2.0


def _fit_under_screen(value_col, contaminated, meta):
    cutoff = resolve_cutoff()
    wide = wide_chokepoint_panel(value_col=value_col)
    pre = pd.Series(wide.index < cutoff, index=wide.index)
    post = pd.Series(wide.index >= cutoff, index=wide.index)
    scaled, scale = scale_by_pre_period_mean(wide, pre)
    donors = [
        slug for slug in meta.loc[meta["slug"] != TREATED, "slug"]
        if slug not in contaminated
        and slug in scaled.columns
        and pd.notna(scale.get(slug))
    ]
    actual, _, _ = _fit_unit(scaled, TREATED, donors, pre, post)
    # Abadie placebos: each clean donor as pseudo-treated against the others.
    placebo_ratios = []
    for pseudo in donors:
        others = [d for d in donors if d != pseudo]
        try:
            summary, _, _ = _fit_unit(scaled, pseudo, others, pre, post)
            placebo_ratios.append(summary["post_pre_rmspe_ratio"])
        except ValueError:
            continue
    placebo = pd.Series(placebo_ratios, dtype="float64")
    p95 = float(placebo.quantile(0.95)) if len(placebo) else float("nan")
    return {
        "value_col": value_col,
        "n_donors": int(len(donors)),
        "pre_rmspe": actual["pre_rmspe"],
        "post_pre_rmspe_ratio": actual["post_pre_rmspe_ratio"],
        "cumulative_scaled_throughput_loss": actual["cumulative_scaled_throughput_loss"],
        "top_weight_slug": actual["top_weight_slug"],
        "n_placebos": int(len(placebo)),
        "placebo_ratio_p95": p95,
        "separation_vs_placebo_p95": (
            actual["post_pre_rmspe_ratio"] / p95 if p95 and p95 == p95 else float("nan")
        ),
        "abadie_p_value": (
            empirical_p_value(actual["post_pre_rmspe_ratio"], placebo, alternative="greater")
            if len(placebo) else float("nan")
        ),
    }


def main() -> None:
    meta = chokepoint_metadata()
    a_priori_slugs = meta.loc[meta["contamination_flag"], "slug"].tolist()

    diag_wide = wide_chokepoint_panel(value_col="n_tanker", start=str(HISTORY_START.date()))
    diagnostic = donor_directional_deviation(
        diag_wide,
        treated_slug=TREATED,
        history_start=HISTORY_START,
        cutoff=resolve_cutoff(),
        horizon_days=HORIZON_DAYS,
        min_scored_days=MIN_SCORED_DAYS,
    )
    screens = build_screens(diagnostic, a_priori_slugs=a_priori_slugs)
    diagnostic = screen_agreement(diagnostic, screens)

    stress_rows = []
    for screen_name, contaminated in screens.items():
        for value_col in VALUE_COLS:
            row = _fit_under_screen(value_col, contaminated, meta)
            row["screen"] = screen_name
            row["n_contaminated"] = int(len(contaminated))
            stress_rows.append(row)
    stress = pd.DataFrame(stress_rows)[
        ["screen", "value_col", "n_contaminated", "n_donors", "pre_rmspe",
         "post_pre_rmspe_ratio", "separation_vs_placebo_p95", "abadie_p_value",
         "top_weight_slug", "cumulative_scaled_throughput_loss"]
    ].sort_values(["value_col", "screen"], ignore_index=True)

    pess = stress.loc[stress["screen"].eq("pessimistic_union")]
    min_pess_sep = float(pess["separation_vs_placebo_p95"].min())
    data_driven_only = sorted(diagnostic.loc[diagnostic["data_driven_only_suspect"], "slug"])
    verdict = {
        "purpose": "SUTVA single-point-of-failure hardening (audit recs 1 and 2).",
        "anchor_note": "Corroboration only; AR-only within-unit estimator remains primary.",
        "a_priori_contaminated": sorted(a_priori_slugs),
        "data_driven_risen_suspects": sorted(screens["data_driven_rose"]),
        "suspects_missed_by_a_priori_screen": data_driven_only,
        "pessimistic_screen_size": len(screens["pessimistic_union"]),
        "min_separation_under_pessimistic_screen": min_pess_sep,
        "containment_separation_floor": CONTAINMENT_SEPARATION_FLOOR,
        "spof_contained": bool(min_pess_sep > CONTAINMENT_SEPARATION_FLOOR),
    }

    paths = config.settings()["paths"]
    diag_path = config.ROOT / paths["donor_contamination_diagnostic_csv"]
    stress_path = config.ROOT / paths["donor_contamination_stress_csv"]
    verdict_path = config.ROOT / paths["donor_contamination_verdict_json"]
    diagnostic.to_csv(diag_path, index=False)
    stress.to_csv(stress_path, index=False)
    verdict_path.write_text(json.dumps(verdict, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    pd.set_option("display.width", 220)
    pd.set_option("display.max_columns", None)
    print("=== Donor-influence diagnostic: rerouting suspects the a-priori screen MISSED ===")
    missed = diagnostic.loc[diagnostic["data_driven_only_suspect"],
                            ["slug", "post_signed_deviation", "n_scored"]]
    print(missed.to_string(index=False) if len(missed) else "  (none)")
    print("\n=== Synthetic-control separation across contamination screens ===")
    print(stress.to_string(index=False))
    print("\n=== Verdict ===")
    print(json.dumps(verdict, indent=2, sort_keys=True))
    print(f"\nwrote {diag_path}")
    print(f"wrote {stress_path}")
    print(f"wrote {verdict_path}")


if __name__ == "__main__":
    main()
