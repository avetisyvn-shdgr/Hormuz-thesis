"""Phase 4, step 4: same-date spatial placebo checks.

This script applies the same seasonal-naive counterfactual to every PortWatch
chokepoint at the real Hormuz treatment date. It asks: do other chokepoints show
same-window throughput losses of comparable size?

This is not synthetic control. It is a donor-pool diagnostic that helps detect
whether the Hormuz result is merely a global shipping-wide forecast failure.

Run from the repo root:
    python scripts/run_spatial_placebo.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from hormuz_throughput import config  # noqa: E402
from hormuz_throughput.baselines import seasonal_naive_forecast  # noqa: E402
from hormuz_throughput.inference import (  # noqa: E402
    counterfactual_effect,
    post_treatment_fold,
)
from hormuz_throughput.spatial import (  # noqa: E402
    chokepoint_metadata,
    leave_one_donor_out_summary,
    spatial_placebo_summary,
    wide_chokepoint_panel,
)


VALUE_COLS = [
    "n_tanker",
    "capacity_tanker",
]

TREATED = "strait_of_hormuz"


def _effect_rows(wide: pd.DataFrame, value_col: str) -> pd.DataFrame:
    fold = post_treatment_fold(wide.index)
    rows = []
    for slug in wide.columns:
        pred = seasonal_naive_forecast(wide[slug], fold=fold, season_length=7)
        true = wide.loc[pred.index, slug]
        eff = counterfactual_effect(true, pred)
        normalized_loss = (
            eff["cumulative_throughput_loss"] / eff["counterfactual_sum"]
            if eff["counterfactual_sum"] else float("nan")
        )
        rows.append({
            "value_col": value_col,
            "slug": slug,
            "is_treated": slug == TREATED,
            "train_start": fold.train_start.date(),
            "train_end": fold.train_end.date(),
            "test_start": fold.test_start.date(),
            "test_end": fold.test_end.date(),
            "normalized_throughput_loss": normalized_loss,
            **eff,
        })
    return pd.DataFrame(rows)


def main() -> None:
    meta = chokepoint_metadata()
    all_effects = []
    for value_col in VALUE_COLS:
        wide = wide_chokepoint_panel(value_col=value_col)
        effects = _effect_rows(wide, value_col)
        all_effects.append(effects)

    effects = pd.concat(all_effects, ignore_index=True)
    summary = spatial_placebo_summary(effects, meta)
    leave_one_out = leave_one_donor_out_summary(effects, meta)
    effects = effects.merge(meta, on="slug", how="left")

    out_dir = config.path("data_processed")
    effects_out = out_dir / "spatial_placebo_effects.csv"
    summary_out = out_dir / "spatial_placebo_summary.csv"
    leave_one_out_out = out_dir / "spatial_placebo_leave_one_out.csv"
    effects.to_csv(effects_out, index=False)
    summary.to_csv(summary_out, index=False)
    leave_one_out.to_csv(leave_one_out_out, index=False)

    print("Spatial placebo summary:")
    print(summary.to_string(index=False))
    print("\nLeave-one-donor-out summary:")
    print(
        leave_one_out[
            [
                "value_col",
                "donor_set",
                "dropped_slug",
                "n_donors",
                "loss_vs_donor_p95_ratio",
                "normalized_loss_vs_donor_p95_ratio",
                "p_donor_loss_ge_actual",
                "p_donor_normalized_loss_ge_actual",
            ]
        ].to_string(index=False)
    )
    print(f"\nwrote {effects_out}")
    print(f"wrote {summary_out}")
    print(f"wrote {leave_one_out_out}")

    print("\nInterpretation guard:")
    print(" - This is same-date spatial placebo evidence, not synthetic control.")
    print(" - Leave-one-donor-out is a sensitivity check on the same unweighted donor pool.")
    print(" - Lead with normalized loss (% of counterfactual) because raw counts are scale-confounded.")
    print(" - Low-contamination donors exclude obvious rerouting/spillover corridors.")
    print(" - Donor p-values are descriptive with small N; report raw and normalized separation ratios.")
    print(" - Seasonal naive is used because route-ARX is not symmetric across donors.")


if __name__ == "__main__":
    main()
