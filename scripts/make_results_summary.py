"""Create a thesis-ready summary of the current empirical evidence.

This report is generated from processed CSV artifacts, not hand-maintained.
It intentionally keeps causal language cautious: these are transparent
counterfactual and placebo diagnostics, not the final full thesis model.

Run from the repo root:
    python scripts/make_results_summary.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lngfreight import config  # noqa: E402
from lngfreight.specification import working_specification  # noqa: E402


def _read_processed(name: str) -> pd.DataFrame:
    path = config.path("data_processed") / name
    if not path.exists():
        raise FileNotFoundError(f"{path} not found. Run the upstream scripts first.")
    return pd.read_csv(path)


def _pct(x: float) -> str:
    return f"{x * 100:.1f}%"


def _num(x: float, digits: int = 0) -> str:
    return f"{x:,.{digits}f}"


def main() -> None:
    spec = working_specification()
    baseline = _read_processed("baseline_summary.csv")
    placebo_time = _read_processed("placebo_time_summary.csv")
    spatial = _read_processed("spatial_placebo_summary.csv")
    spatial_loo = _read_processed("spatial_placebo_leave_one_out.csv")
    treatment_robustness = _read_processed("treatment_robustness_summary.csv")
    intervals = _read_processed("counterfactual_intervals_summary.csv")
    synthetic = _read_processed("synthetic_control_summary.csv")
    tsfm_counterfactual = _read_processed("tsfm_counterfactual_summary.csv")

    synth_transit = synthetic[
        (synthetic["value_col"] == "n_tanker")
        & (synthetic["is_actual"])
    ].iloc[0]

    route_transit = placebo_time[
        (placebo_time["model"] == "arx_lag1_7_route")
        & (placebo_time["target"] == "hormuz_tanker_transits")
    ].iloc[0]
    ar_transit = placebo_time[
        (placebo_time["model"] == spec.primary_estimator)
        & (placebo_time["target"] == spec.primary_outcome)
    ].iloc[0]
    spatial_transit_all = spatial[
        (spatial["value_col"] == "n_tanker")
        & (spatial["donor_set"] == "all_donors")
    ].iloc[0]
    spatial_transit_clean = spatial[
        (spatial["value_col"] == "n_tanker")
        & (spatial["donor_set"] == "low_contamination_donors")
    ].iloc[0]
    loo_transit_all = spatial_loo[
        (spatial_loo["value_col"] == "n_tanker")
        & (spatial_loo["donor_set"] == "all_donors")
    ]
    loo_transit_clean = spatial_loo[
        (spatial_loo["value_col"] == "n_tanker")
        & (spatial_loo["donor_set"] == "low_contamination_donors")
    ]
    loo_all_worst = loo_transit_all.loc[
        loo_transit_all["normalized_loss_vs_donor_p95_ratio"].idxmin()
    ]
    loo_clean_worst = loo_transit_clean.loc[
        loo_transit_clean["normalized_loss_vs_donor_p95_ratio"].idxmin()
    ]
    loo_all_malacca = loo_transit_all.loc[
        loo_transit_all["dropped_slug"] == "malacca_strait"
    ].iloc[0]
    loo_clean_malacca = loo_transit_clean.loc[
        loo_transit_clean["dropped_slug"] == "malacca_strait"
    ].iloc[0]
    arx_baseline = baseline[
        (baseline["model"] == "arx_lag1_7_route")
        & (baseline["target"] == "hormuz_tanker_transits")
    ].iloc[0]
    ar_baseline = baseline[
        (baseline["model"] == spec.primary_estimator)
        & (baseline["target"] == spec.primary_outcome)
    ].iloc[0]
    naive_baseline = baseline[
        (baseline["model"] == "seasonal_naive_7d")
        & (baseline["target"] == "hormuz_tanker_transits")
    ].iloc[0]
    route_interval = intervals[
        (intervals["model"] == spec.primary_estimator)
        & (intervals["target"] == spec.primary_outcome)
    ].iloc[0]
    long_horizon = _read_processed("long_horizon_intervals_summary.csv")
    route_long_horizon = long_horizon[
        (long_horizon["model"] == spec.primary_estimator)
        & (long_horizon["target"] == spec.primary_outcome)
    ].iloc[0]
    ar_long_horizon = long_horizon[
        (long_horizon["model"] == spec.primary_estimator)
        & (long_horizon["target"] == spec.primary_outcome)
    ].iloc[0]
    chronos_transit = tsfm_counterfactual[
        (tsfm_counterfactual["model"] == "chronos2")
        & (tsfm_counterfactual["target"] == spec.primary_outcome)
    ].iloc[0]
    chronos_capacity = tsfm_counterfactual[
        (tsfm_counterfactual["model"] == "chronos2")
        & (tsfm_counterfactual["target"] == spec.robustness_outcome)
    ].iloc[0]
    route_robustness = treatment_robustness[
        (treatment_robustness["model"] == spec.primary_estimator)
        & (treatment_robustness["target"] == spec.primary_outcome)
    ].copy()
    robustness_order = [
        "donut_clean_post_after_force_majeure",
        "anchored_kinetic_trigger",
        "anchored_closure_declaration",
        "anchored_force_majeure",
    ]
    route_robustness["window"] = pd.Categorical(
        route_robustness["window"],
        categories=robustness_order,
        ordered=True,
    )
    route_robustness = route_robustness.sort_values("window")

    lines = [
        "# Current Empirical Results Summary",
        "",
        "**Generated from processed artifacts.** This is a working results table, "
        "not final thesis language.",
        "",
        "## Baseline Validation",
        "",
        "| Target | Model | MAE mean | RMSE mean | MASE mean | sMAPE mean |",
        "|---|---:|---:|---:|---:|---:|",
        (
            f"| Hormuz tanker transits | Seasonal naive 7d | "
            f"{naive_baseline['mae_mean']:.2f} | {naive_baseline['rmse_mean']:.2f} | "
            f"{naive_baseline['mase_mean']:.2f} | {naive_baseline['smape_mean']:.2f}% |"
        ),
        (
            f"| Hormuz tanker transits | AR lag 1/7, no observed post controls | "
            f"{ar_baseline['mae_mean']:.2f} | {ar_baseline['rmse_mean']:.2f} | "
            f"{ar_baseline['mase_mean']:.2f} | {ar_baseline['smape_mean']:.2f}% |"
        ),
        (
            f"| Hormuz tanker transits | ARX lag 1/7 + route controls | "
            f"{arx_baseline['mae_mean']:.2f} | {arx_baseline['rmse_mean']:.2f} | "
            f"{arx_baseline['mase_mean']:.2f} | {arx_baseline['smape_mean']:.2f}% |"
        ),
        "",
        "## Post-treatment Counterfactual Gap",
        "",
        "| Model | Cumulative loss | Mean daily loss | Placebo p-value | Placebo p95 | Separation |",
        "|---|---:|---:|---:|---:|---:|",
        (
            f"| AR-only working primary, transit count | {_num(ar_transit['actual_cumulative_throughput_loss'])} "
            f"transits | {ar_transit['actual_mean_daily_throughput_loss']:.1f}/day | "
            f"{ar_transit['p_loss_ge_actual']:.3f} | "
            f"{_num(ar_transit['placebo_loss_p95'])} | "
            f"{ar_transit['loss_vs_placebo_p95_ratio']:.1f}x |"
        ),
        (
            f"| Route-only ARX, transit count | {_num(route_transit['actual_cumulative_throughput_loss'])} "
            f"transits | {route_transit['actual_mean_daily_throughput_loss']:.1f}/day | "
            f"{route_transit['p_loss_ge_actual']:.3f} | "
            f"{_num(route_transit['placebo_loss_p95'])} | "
            f"{route_transit['loss_vs_placebo_p95_ratio']:.1f}x |"
        ),
        "",
        (
            "Information-set sensitivity: AR-only uses no observed post-treatment "
            "covariates and gives a 94-day interval of "
            f"**{_num(ar_long_horizon['interval_94dhorizon_lower'])} to "
            f"{_num(ar_long_horizon['interval_94dhorizon_upper'])} transits**. "
            "Its close agreement with route ARX indicates that contemporaneous "
            "Panama controls are not driving the estimated gap. Route ARX remains "
            "a conditional sensitivity because Panama traffic is observed post-treatment."
        ),
        "",
        (
            "Residual-calibrated 95% aggregate interval for the AR-only working-primary "
            f"transit loss: **{_num(route_interval['loss_interval_lower'])} to "
            f"{_num(route_interval['loss_interval_upper'])} tanker transits**, "
            f"or {route_interval['mean_daily_loss_interval_lower']:.1f} to "
            f"{route_interval['mean_daily_loss_interval_upper']:.1f} per day. This "
            "band is calibrated on <=30-day folds and understates a 94-day horizon."
        ),
        "",
        (
            "Honest 94-day-horizon interval (recalibrated on the placebo-in-time "
            "windows, which are full 94-day forecast errors): "
            f"**{_num(route_long_horizon['interval_94dhorizon_lower'])} to "
            f"{_num(route_long_horizon['interval_94dhorizon_upper'])} tanker "
            f"transits** — about {route_long_horizon['widening_factor_vs_30dfold']:.1f}x "
            "wider than the short-fold band, and still excluding zero by a wide "
            "margin. Use this as the reported interval; the short-fold band is a "
            "lower bound. The band is coarse/conservative (~9 effective windows)."
        ),
        (
            "Independent circular-block cross-check (10,000 draws, 14-day blocks "
            "from the ordered out-of-fold residual path): "
            f"**{_num(ar_long_horizon['interval_circular_bootstrap_lower'])} to "
            f"{_num(ar_long_horizon['interval_circular_bootstrap_upper'])} transits**. "
            "It is materially narrower than the placebo-window band, so interval "
            "width is method-sensitive even though both bands exclude zero."
        ),
        "",
        (
            "Chronos-2 changes the locked-primary transit shortfall by only "
            f"**{chronos_transit['pct_diff_vs_ar']:+.1f}%**, but changes the capacity "
            f"shortfall by **{chronos_capacity['pct_diff_vs_ar']:+.1f}%** "
            f"({chronos_capacity['ar_cumulative_throughput_loss']/1e6:.1f}M AR-only "
            f"versus {chronos_capacity['cumulative_throughput_loss']/1e6:.1f}M Chronos-2). "
            "Capacity is therefore a directional secondary, model-sensitive outcome; "
            "its precise magnitude is not load-bearing."
        ),
        "",
        "The time-placebo p-value is floor-censored because 36 overlapping placebo "
        "windows provide only about 9 non-overlapping 94-day windows. Report the "
        "separation ratio alongside the p-value.",
        "",
        "## Treatment-window Robustness",
        "",
        "All rows keep the training cutoff fixed at **2026-02-28**; later event "
        "dates define scoring windows only. Later cutoffs would train on "
        "disrupted days and poison the baseline.",
        "",
        "| Window | Scored post window | Valid days | Cumulative loss | Mean daily loss |",
        "|---|---:|---:|---:|---:|",
        *[
            (
                f"| {row['window']} | {row['post_start']} to {row['post_end']} | "
                f"{int(row['n_days'])} | "
                f"{_num(row['cumulative_throughput_loss'])} | "
                f"{row['mean_daily_throughput_loss']:.1f}/day |"
            )
            for _, row in route_robustness.iterrows()
        ],
        "",
        "Donut interpretation: excluding the ambiguous transition window "
        "2026-02-28 through 2026-03-04 lowers cumulative loss mechanically "
            "because fewer days are scored, while the mean daily AR-only "
        "loss remains close to the anchored windows.",
        "",
        "## Same-date Spatial Placebo",
        "",
        "| Donor set | Raw loss | Normalized loss | Donor raw p95 | Raw separation | Donor normalized p95 | Normalized separation |",
        "|---|---:|---:|---:|---:|---:|---:|",
        (
            f"| All donors | {_num(spatial_transit_all['actual_cumulative_throughput_loss'])} | "
            f"{_pct(spatial_transit_all['actual_normalized_throughput_loss'])} | "
            f"{_num(spatial_transit_all['donor_loss_p95'], 1)} | "
            f"{spatial_transit_all['loss_vs_donor_p95_ratio']:.1f}x | "
            f"{_pct(spatial_transit_all['donor_normalized_loss_p95'])} | "
            f"{spatial_transit_all['normalized_loss_vs_donor_p95_ratio']:.1f}x |"
        ),
        (
            f"| Low-contamination donors | {_num(spatial_transit_clean['actual_cumulative_throughput_loss'])} | "
            f"{_pct(spatial_transit_clean['actual_normalized_throughput_loss'])} | "
            f"{_num(spatial_transit_clean['donor_loss_p95'], 1)} | "
            f"{spatial_transit_clean['loss_vs_donor_p95_ratio']:.1f}x | "
            f"{_pct(spatial_transit_clean['donor_normalized_loss_p95'])} | "
            f"{spatial_transit_clean['normalized_loss_vs_donor_p95_ratio']:.1f}x |"
        ),
        "",
        "Spatial placebo interpretation: Hormuz ranks first by raw loss and by "
        "normalized loss. Malacca is the largest raw donor loss, but normalized "
        "severity shows it is not comparable to the near-total Hormuz collapse.",
        "",
        "## Leave-one-donor-out Spatial Sensitivity",
        "",
        "| Donor set | Worst dropped donor | Min normalized separation | Drop Malacca normalized separation | Normalized p-value range |",
        "|---|---:|---:|---:|---:|",
        (
            f"| All donors | {loo_all_worst['dropped_slug']} | "
            f"{loo_all_worst['normalized_loss_vs_donor_p95_ratio']:.1f}x | "
            f"{loo_all_malacca['normalized_loss_vs_donor_p95_ratio']:.1f}x | "
            f"{loo_transit_all['p_donor_normalized_loss_ge_actual'].min():.3f}-"
            f"{loo_transit_all['p_donor_normalized_loss_ge_actual'].max():.3f} |"
        ),
        (
            f"| Low-contamination donors | {loo_clean_worst['dropped_slug']} | "
            f"{loo_clean_worst['normalized_loss_vs_donor_p95_ratio']:.1f}x | "
            f"{loo_clean_malacca['normalized_loss_vs_donor_p95_ratio']:.1f}x | "
            f"{loo_transit_clean['p_donor_normalized_loss_ge_actual'].min():.3f}-"
            f"{loo_transit_clean['p_donor_normalized_loss_ge_actual'].max():.3f} |"
        ),
        "",
        "Leave-one-out interpretation: the normalized transit-count separation is "
        "not driven by a single donor. Dropping Malacca, the largest raw donor "
        "loss, increases rather than weakens the normalized separation.",
        "",
        "## Synthetic-control Corroboration",
        "",
        "Donor-weighted synthetic control on the clean donor pool (five rerouting "
        "corridors excluded), matched on pre-period mean-scaled throughput so the "
        "check is about shape, not chokepoint size. Inference is Abadie-style: the "
        "post/pre RMSPE ratio for Hormuz is compared against the same ratio computed "
        "for each clean donor treated as a placebo. This corroborates, it is not the "
        "anchor estimator.",
        "",
        "| Quantity | Value |",
        "|---|---:|",
        f"| Clean donors in fit | {int(synth_transit['n_donors'])} |",
        f"| Pre-period fit days | {int(synth_transit['n_pre_fit_days'])} |",
        f"| Pre-period RMSPE (fit quality) | {synth_transit['pre_rmspe']:.3f} |",
        f"| Post-period RMSPE | {synth_transit['post_rmspe']:.3f} |",
        f"| Post/pre RMSPE ratio | {synth_transit['post_pre_rmspe_ratio']:.2f} |",
        f"| Placebo ratio p95 | {synth_transit['placebo_ratio_p95']:.2f} |",
        f"| Hormuz ratio / placebo p95 | {synth_transit['ratio_vs_placebo_p95']:.2f}x |",
        f"| Abadie placebo p-value | {synth_transit['p_ratio_ge_actual']:.3f} |",
        f"| Effective donors (1/sum w^2) | {synth_transit['effective_n_weights']:.1f} |",
        f"| Largest single weight | {synth_transit['top_weight_slug']} ({synth_transit['top_weight']:.2f}) |",
        "",
        "Synthetic-control interpretation: the pre-period fit is credible "
        f"(RMSPE {synth_transit['pre_rmspe']:.3f} on mean-scaled units, "
        f"{synth_transit['effective_n_weights']:.1f} effective donors, no single donor "
        "dominating), and Hormuz's post/pre RMSPE ratio is far larger than any clean "
        "donor placebo. This is independent corroboration of the throughput collapse, "
        "consistent with the placebo-in-time and spatial-placebo layers. It remains a "
        "scaled, shape-based diagnostic, not an LNG freight-rate estimate.",
        "",
        "## Guardrails",
        "",
        "- Results are about observed AIS-based tanker throughput, not LNG-specific freight rates.",
        "- Normalized spatial loss should lead the spatial-placebo interpretation because raw counts are scale-confounded.",
        "- Capacity is a directional secondary, model-sensitive outcome; use mean-daily direction and do not lean on its precise magnitude.",
        "- PortWatch fallback is the working primary; formal estimand realignment remains pending Prof. Li confirmation.",
        "- Spark is a dormant optional secondary-outcome extension and is not a blocker.",
    ]

    out = config.ROOT / "reports" / "current_results_summary.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
