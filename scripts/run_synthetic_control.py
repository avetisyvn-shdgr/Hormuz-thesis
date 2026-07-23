"""Phase 4, step 7: donor-weighted synthetic control as corroboration.

This is not the anchor estimator. It excludes obvious rerouting/spillover
corridors and matches on pre-period mean-scaled throughput so the check is about
shape, not raw chokepoint size.

Run from the repo root:
    python scripts/run_synthetic_control.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lngfreight import config  # noqa: E402
from lngfreight.inference import empirical_p_value  # noqa: E402
from lngfreight.spatial import chokepoint_metadata, wide_chokepoint_panel  # noqa: E402
from lngfreight.synthetic import (  # noqa: E402
    fit_simplex_weights,
    post_pre_ratio,
    rmspe,
    scale_by_pre_period_mean,
)
from lngfreight.validation import resolve_cutoff  # noqa: E402


VALUE_COLS = [
    "n_tanker",
    "capacity_tanker",
]

TREATED = "strait_of_hormuz"
MIN_PRE_ROWS = 365
PRIMARY_PREFIT_RMSPE_MULTIPLIER = 2.0
PREFIT_RMSPE_SENSITIVITY_MULTIPLIERS = (1.5, 2.0, 5.0, 10.0, np.inf)


def _clean_donor_slugs(meta: pd.DataFrame) -> list[str]:
    clean = meta.loc[
        (~meta["contamination_flag"]) & (meta["slug"] != TREATED),
        "slug",
    ].tolist()
    if not clean:
        raise ValueError("No clean donors available after contamination exclusions.")
    return clean


def _fit_unit(
    scaled: pd.DataFrame,
    treated: str,
    donors: list[str],
    pre_mask: pd.Series,
    post_mask: pd.Series,
) -> tuple[dict[str, object], pd.Series, pd.DataFrame]:
    columns = [treated, *donors]
    available = scaled[columns].dropna(axis="columns", how="all")
    if treated not in available.columns:
        raise ValueError(f"Treated series {treated!r} has no scaled observations.")
    donor_cols = [c for c in donors if c in available.columns]
    donor_cols = [
        c for c in donor_cols
        if available.loc[pre_mask, c].notna().sum() >= MIN_PRE_ROWS
    ]
    if not donor_cols:
        raise ValueError(f"No donors have at least {MIN_PRE_ROWS} pre-period rows.")

    pre_available = available.loc[pre_mask, [treated, *donor_cols]]
    fit_frame = pre_available.dropna()
    while len(fit_frame) < MIN_PRE_ROWS and len(donor_cols) > 1:
        donor_pre_counts = pre_available[donor_cols].notna().sum().sort_values()
        donor_cols.remove(str(donor_pre_counts.index[0]))
        pre_available = available.loc[pre_mask, [treated, *donor_cols]]
        fit_frame = pre_available.dropna()
    if len(fit_frame) < MIN_PRE_ROWS:
        raise ValueError(
            f"Only {len(fit_frame)} complete pre-period rows for {treated!r}; "
            f"need at least {MIN_PRE_ROWS}."
        )

    weights = fit_simplex_weights(
        fit_frame[treated],
        fit_frame[donor_cols],
    )
    synth = scaled[donor_cols] @ weights
    y = scaled[treated]
    pre_rmspe = rmspe(y.loc[pre_mask], synth.loc[pre_mask])
    post_rmspe = rmspe(y.loc[post_mask], synth.loc[post_mask])
    ratio = post_pre_ratio(post_rmspe, pre_rmspe)
    valid_post = y.loc[post_mask].notna() & synth.loc[post_mask].notna()
    scaled_loss = float((synth.loc[post_mask][valid_post] - y.loc[post_mask][valid_post]).sum())
    summary = {
        "unit": treated,
        "n_donors": len(donor_cols),
        "n_pre_fit_days": int(len(fit_frame)),
        "n_post_days": int(valid_post.sum()),
        "pre_rmspe": pre_rmspe,
        "post_rmspe": post_rmspe,
        "post_pre_rmspe_ratio": ratio,
        "cumulative_scaled_throughput_loss": scaled_loss,
        "mean_daily_scaled_throughput_loss": scaled_loss / valid_post.sum()
        if valid_post.sum()
        else float("nan"),
        "top_weight_slug": str(weights.idxmax()),
        "top_weight": float(weights.max()),
        "effective_n_weights": float(1.0 / np.sum(weights.to_numpy() ** 2)),
    }
    daily = pd.DataFrame({
        "date": scaled.index,
        "unit": treated,
        "y_scaled": y.to_numpy(dtype="float64"),
        "synthetic_scaled": synth.to_numpy(dtype="float64"),
    })
    daily["gap_observed_minus_synthetic"] = daily["y_scaled"] - daily["synthetic_scaled"]
    daily["scaled_throughput_loss"] = daily["synthetic_scaled"] - daily["y_scaled"]
    daily["period"] = np.where(daily["date"] < scaled.index[post_mask][0], "pre", "post")
    weight_rows = weights.rename_axis("donor_slug").reset_index()
    weight_rows["unit"] = treated
    return summary, weights, daily


def _prefit_screen_sensitivity(
    *,
    value_col: str,
    actual_ratio: float,
    treated_pre_rmspe: float,
    placebos: pd.DataFrame,
) -> pd.DataFrame:
    """Evaluate donor-placebo inference across pre-fit RMSPE screens."""
    required = {"pre_rmspe", "post_pre_rmspe_ratio"}
    missing = required - set(placebos.columns)
    if missing:
        raise ValueError(f"Missing placebo fit columns: {sorted(missing)}")
    rows = []
    for multiplier in PREFIT_RMSPE_SENSITIVITY_MULTIPLIERS:
        if np.isinf(multiplier):
            eligible = placebos.copy()
            screen = "unscreened"
            max_pre_rmspe = float("inf")
        else:
            max_pre_rmspe = float(multiplier * treated_pre_rmspe)
            eligible = placebos.loc[placebos["pre_rmspe"] <= max_pre_rmspe].copy()
            screen = f"pre_rmspe_le_{multiplier:g}x_treated"
        ratios = eligible["post_pre_rmspe_ratio"].dropna()
        p_value = (
            empirical_p_value(actual_ratio, ratios, alternative="greater")
            if len(ratios)
            else float("nan")
        )
        p95 = float(ratios.quantile(0.95)) if len(ratios) else float("nan")
        rows.append(
            {
                "value_col": value_col,
                "screen": screen,
                "is_primary_screen": bool(
                    not np.isinf(multiplier)
                    and multiplier == PRIMARY_PREFIT_RMSPE_MULTIPLIER
                ),
                "pre_rmspe_multiplier": (
                    float(multiplier) if not np.isinf(multiplier) else np.nan
                ),
                "treated_pre_rmspe": float(treated_pre_rmspe),
                "maximum_eligible_pre_rmspe": max_pre_rmspe,
                "actual_post_pre_rmspe_ratio": float(actual_ratio),
                "n_placebos_total": int(len(placebos)),
                "n_placebos_eligible": int(len(ratios)),
                "n_placebos_excluded": int(len(placebos) - len(ratios)),
                "p_ratio_ge_actual": p_value,
                "p_value_floor": 1.0 / (len(ratios) + 1) if len(ratios) else np.nan,
                "placebo_ratio_p95": p95,
                "ratio_vs_placebo_p95": (
                    float(actual_ratio / p95) if p95 and np.isfinite(p95) else np.nan
                ),
            }
        )
    return pd.DataFrame(rows)


def _run_value_col(
    value_col: str,
    meta: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    cutoff = resolve_cutoff()
    wide = wide_chokepoint_panel(value_col=value_col)
    pre_mask = pd.Series(wide.index < cutoff, index=wide.index)
    post_mask = pd.Series(wide.index >= cutoff, index=wide.index)
    scaled, scale = scale_by_pre_period_mean(wide, pre_mask)
    clean_donors = _clean_donor_slugs(meta)
    clean_donors = [c for c in clean_donors if c in scaled.columns and pd.notna(scale.get(c))]

    try:
        actual_summary, actual_weights, actual_daily = _fit_unit(
            scaled,
            treated=TREATED,
            donors=clean_donors,
            pre_mask=pre_mask,
            post_mask=post_mask,
        )
        actual_summary.update({
            "value_col": value_col,
            "is_actual": True,
            "fixed_train_cutoff": cutoff.date(),
            "pre_start": wide.index[pre_mask].min().date(),
            "pre_end": wide.index[pre_mask].max().date(),
            "post_start": wide.index[post_mask].min().date(),
            "post_end": wide.index[post_mask].max().date(),
            "donor_pool": "low_contamination_donors",
            "fit_status": "computed",
            "fit_warning": "",
        })
    except ValueError as exc:
        actual_summary = {
            "value_col": value_col,
            "unit": TREATED,
            "is_actual": True,
            "fixed_train_cutoff": cutoff.date(),
            "pre_start": wide.index[pre_mask].min().date(),
            "pre_end": wide.index[pre_mask].max().date(),
            "post_start": wide.index[post_mask].min().date(),
            "post_end": wide.index[post_mask].max().date(),
            "donor_pool": "low_contamination_donors",
            "fit_status": "failed",
            "fit_warning": str(exc),
        }
        actual_weights = pd.Series(dtype="float64", name="weight")
        actual_daily = pd.DataFrame()

    placebo_summaries = []
    placebo_daily = []
    placebo_weights = []
    for pseudo in clean_donors:
        donors = [d for d in clean_donors if d != pseudo]
        try:
            summary, weights, daily = _fit_unit(
                scaled,
                treated=pseudo,
                donors=donors,
                pre_mask=pre_mask,
                post_mask=post_mask,
            )
            summary.update({
                "value_col": value_col,
                "is_actual": False,
                "fixed_train_cutoff": cutoff.date(),
                "pre_start": wide.index[pre_mask].min().date(),
                "pre_end": wide.index[pre_mask].max().date(),
                "post_start": wide.index[post_mask].min().date(),
                "post_end": wide.index[post_mask].max().date(),
                "donor_pool": "low_contamination_donors",
                "fit_status": "computed",
                "fit_warning": "",
            })
            weights = weights.rename_axis("donor_slug").reset_index()
            weights["unit"] = pseudo
            weights["value_col"] = value_col
            daily["value_col"] = value_col
            daily["is_actual"] = False
            placebo_summaries.append(summary)
            placebo_daily.append(daily)
            placebo_weights.append(weights)
        except ValueError as exc:
            placebo_summaries.append({
                "value_col": value_col,
                "unit": pseudo,
                "is_actual": False,
                "fixed_train_cutoff": cutoff.date(),
                "donor_pool": "low_contamination_donors",
                "fit_status": "failed",
                "fit_warning": str(exc),
            })

    if not actual_daily.empty:
        actual_daily["value_col"] = value_col
        actual_daily["is_actual"] = True
    actual_weights = actual_weights.rename_axis("donor_slug").reset_index()
    if not actual_weights.empty:
        actual_weights["unit"] = TREATED
        actual_weights["value_col"] = value_col

    placebo_summary = pd.DataFrame(placebo_summaries)
    computed_placebos = placebo_summary[placebo_summary["fit_status"] == "computed"]
    if actual_summary["fit_status"] == "computed":
        sensitivity = _prefit_screen_sensitivity(
            value_col=value_col,
            actual_ratio=float(actual_summary["post_pre_rmspe_ratio"]),
            treated_pre_rmspe=float(actual_summary["pre_rmspe"]),
            placebos=computed_placebos,
        )
        primary = sensitivity.loc[sensitivity["is_primary_screen"]].iloc[0]
        primary_max = float(primary["maximum_eligible_pre_rmspe"])
        placebo_summary["pre_rmspe_multiple_of_treated"] = (
            placebo_summary["pre_rmspe"] / float(actual_summary["pre_rmspe"])
        )
        placebo_summary["eligible_primary_prefit_screen"] = (
            placebo_summary["fit_status"].eq("computed")
            & placebo_summary["pre_rmspe"].le(primary_max)
        )
        actual_summary["primary_prefit_rmspe_multiplier"] = (
            PRIMARY_PREFIT_RMSPE_MULTIPLIER
        )
        actual_summary["primary_prefit_max_pre_rmspe"] = primary_max
        actual_summary["n_placebos_total"] = int(primary["n_placebos_total"])
        actual_summary["n_placebos_eligible"] = int(primary["n_placebos_eligible"])
        actual_summary["n_placebos_excluded"] = int(primary["n_placebos_excluded"])
        actual_summary["p_ratio_ge_actual"] = float(primary["p_ratio_ge_actual"])
        actual_summary["p_value_floor"] = float(primary["p_value_floor"])
        actual_summary["placebo_ratio_p95"] = float(primary["placebo_ratio_p95"])
        actual_summary["ratio_vs_placebo_p95"] = float(
            primary["ratio_vs_placebo_p95"]
        )
    else:
        sensitivity = pd.DataFrame()
        placebo_summary["pre_rmspe_multiple_of_treated"] = np.nan
        placebo_summary["eligible_primary_prefit_screen"] = False
        actual_summary["primary_prefit_rmspe_multiplier"] = (
            PRIMARY_PREFIT_RMSPE_MULTIPLIER
        )
        actual_summary["primary_prefit_max_pre_rmspe"] = float("nan")
        actual_summary["n_placebos_total"] = int(len(computed_placebos))
        actual_summary["n_placebos_eligible"] = 0
        actual_summary["n_placebos_excluded"] = int(len(computed_placebos))
        actual_summary["p_ratio_ge_actual"] = float("nan")
        actual_summary["p_value_floor"] = float("nan")
        actual_summary["placebo_ratio_p95"] = float("nan")
        actual_summary["ratio_vs_placebo_p95"] = float("nan")

    summary = pd.concat([
        pd.DataFrame([actual_summary]),
        placebo_summary,
    ], ignore_index=True)
    daily_parts = [x for x in [actual_daily, *placebo_daily] if not x.empty]
    weight_parts = [x for x in [actual_weights, *placebo_weights] if not x.empty]
    daily = pd.concat(daily_parts, ignore_index=True) if daily_parts else pd.DataFrame()
    weights = pd.concat(weight_parts, ignore_index=True) if weight_parts else pd.DataFrame()
    scale_frame = scale.rename("pre_period_scale").rename_axis("slug").reset_index()
    scale_frame["value_col"] = value_col
    return summary, daily, weights, scale_frame, sensitivity


def main() -> None:
    meta = chokepoint_metadata()
    all_summary = []
    all_daily = []
    all_weights = []
    all_scales = []
    all_sensitivity = []
    for value_col in VALUE_COLS:
        summary, daily, weights, scales, sensitivity = _run_value_col(value_col, meta)
        all_summary.append(summary)
        all_daily.append(daily)
        all_weights.append(weights)
        all_scales.append(scales)
        all_sensitivity.append(sensitivity)

    summary = pd.concat(all_summary, ignore_index=True)
    daily = pd.concat(all_daily, ignore_index=True)
    weights = pd.concat(all_weights, ignore_index=True)
    scales = pd.concat(all_scales, ignore_index=True)
    sensitivity = pd.concat(all_sensitivity, ignore_index=True)

    out_dir = config.path("data_processed")
    summary_out = out_dir / "synthetic_control_summary.csv"
    daily_out = out_dir / "synthetic_control_daily.csv"
    weights_out = out_dir / "synthetic_control_weights.csv"
    scales_out = out_dir / "synthetic_control_scales.csv"
    sensitivity_out = out_dir / "synthetic_control_prefit_sensitivity.csv"
    summary.to_csv(summary_out, index=False)
    daily.to_csv(daily_out, index=False)
    weights.to_csv(weights_out, index=False)
    scales.to_csv(scales_out, index=False)
    sensitivity.to_csv(sensitivity_out, index=False)

    actual = summary[summary["is_actual"]].copy()
    print("Synthetic-control corroboration summary:")
    print(actual.to_string(index=False))
    print("\nPre-fit RMSPE screen sensitivity:")
    print(sensitivity.to_string(index=False))
    print(f"\nwrote {summary_out}")
    print(f"wrote {daily_out}")
    print(f"wrote {weights_out}")
    print(f"wrote {scales_out}")
    print(f"wrote {sensitivity_out}")
    print("\nInterpretation guard:")
    print(" - This is corroboration, not the anchor estimator.")
    print(" - Donors exclude Panama, Suez, Bab el-Mandeb, Cape of Good Hope, and Gibraltar.")
    print(" - Matching is on pre-period mean-scaled throughput, not raw levels.")
    print(" - Pre-period RMSPE is the fit-credibility metric; weak fit limits interpretation.")
    print(
        " - The remediation-primary eligibility rule is placebo pre-RMSPE <= "
        f"{PRIMARY_PREFIT_RMSPE_MULTIPLIER:g}x the treated pre-RMSPE."
    )
    print(
        " - Threshold sensitivity at 1.5x, 2x, 5x, 10x, and unscreened is "
        "reported so interpretation does not depend on one screen."
    )
    print(
        " - Abadie-style rank inference compares the treated post/pre RMSPE ratio "
        "only with eligible clean-donor placebos."
    )


if __name__ == "__main__":
    main()
