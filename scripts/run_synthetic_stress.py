"""Stress synthetic control across donor pools and donor-by-time placebos."""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from lngfreight import config  # noqa: E402
from lngfreight.inference import empirical_p_value, placebo_time_folds, select_non_overlapping_folds  # noqa: E402
from lngfreight.spatial import chokepoint_metadata, wide_chokepoint_panel  # noqa: E402
from lngfreight.synthetic import scale_by_pre_period_mean  # noqa: E402
from lngfreight.validation import resolve_cutoff  # noqa: E402
from run_synthetic_control import MIN_PRE_ROWS, TREATED, _fit_unit  # noqa: E402


def _eligible(meta: pd.DataFrame, wide: pd.DataFrame, clean: bool) -> list[str]:
    mask = meta["slug"] != TREATED
    if clean:
        mask &= ~meta["contamination_flag"]
    return [slug for slug in meta.loc[mask, "slug"] if slug in wide.columns]


def _actual_pool_fit(
    wide: pd.DataFrame, donors: list[str], label: str
) -> dict[str, object]:
    cutoff = resolve_cutoff()
    pre = pd.Series(wide.index < cutoff, index=wide.index)
    post = pd.Series(wide.index >= cutoff, index=wide.index)
    scaled, _ = scale_by_pre_period_mean(wide, pre)
    summary, _, _ = _fit_unit(scaled, TREATED, donors, pre, post)
    summary.update({"donor_pool": label, "placebo_type": "actual_pool_stress"})
    return summary


def main() -> None:
    meta = chokepoint_metadata()
    wide = wide_chokepoint_panel(value_col="n_tanker")
    clean = _eligible(meta, wide, clean=True)
    broad = _eligible(meta, wide, clean=False)
    actual_rows = [
        _actual_pool_fit(wide, clean, "low_contamination_donors"),
        _actual_pool_fit(wide, broad, "all_available_donors"),
    ]

    folds = select_non_overlapping_folds(placebo_time_folds(wide.index))
    placebo_rows = []
    for fold in folds:
        pre = pd.Series(wide.index < fold.test_start, index=wide.index)
        post = pd.Series(
            (wide.index >= fold.test_start) & (wide.index <= fold.test_end),
            index=wide.index,
        )
        scaled, _ = scale_by_pre_period_mean(wide, pre)
        for pseudo in clean:
            donors = [item for item in clean if item != pseudo]
            try:
                summary, _, _ = _fit_unit(scaled, pseudo, donors, pre, post)
                summary.update({
                    "placebo_type": "donor_in_time",
                    "donor_pool": "low_contamination_donors",
                    "placebo_fold": fold.name,
                    "placebo_start": fold.test_start.date(),
                    "placebo_end": fold.test_end.date(),
                    "fit_status": "computed",
                    "fit_warning": "",
                })
            except ValueError as exc:
                summary = {
                    "unit": pseudo,
                    "placebo_type": "donor_in_time",
                    "donor_pool": "low_contamination_donors",
                    "placebo_fold": fold.name,
                    "placebo_start": fold.test_start.date(),
                    "placebo_end": fold.test_end.date(),
                    "fit_status": "failed",
                    "fit_warning": str(exc),
                }
            placebo_rows.append(summary)

    actual = pd.DataFrame(actual_rows)
    placebos = pd.DataFrame(placebo_rows)
    valid = placebos.loc[placebos["fit_status"] == "computed"]
    anchor_ratio = float(actual.loc[
        actual["donor_pool"] == "low_contamination_donors",
        "post_pre_rmspe_ratio",
    ].iloc[0])
    inference = pd.DataFrame([{
        "actual_post_pre_rmspe_ratio": anchor_ratio,
        "n_requested_donor_time_placebos": len(placebos),
        "n_computed_donor_time_placebos": len(valid),
        "n_independent_time_windows": len(folds),
        "n_placebo_units": valid["unit"].nunique(),
        "donor_time_placebo_p_value": empirical_p_value(
            anchor_ratio, valid["post_pre_rmspe_ratio"], alternative="greater"
        ),
        "donor_time_ratio_p95": valid["post_pre_rmspe_ratio"].quantile(0.95),
        "actual_to_donor_time_p95_ratio": (
            anchor_ratio / valid["post_pre_rmspe_ratio"].quantile(0.95)
        ),
    }])

    out = config.path("data_processed")
    actual.to_csv(out / "synthetic_donor_pool_stress.csv", index=False)
    placebos.to_csv(out / "synthetic_donor_time_placebos.csv", index=False)
    inference.to_csv(out / "synthetic_donor_time_inference.csv", index=False)
    print("Synthetic donor-pool stress:")
    print(actual[["donor_pool", "n_donors", "pre_rmspe", "post_pre_rmspe_ratio",
                  "cumulative_scaled_throughput_loss"]].to_string(index=False))
    print("\nDonor-by-time placebo inference:")
    print(inference.to_string(index=False))


if __name__ == "__main__":
    main()
