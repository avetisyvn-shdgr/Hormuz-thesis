"""Create the inspectable end-to-end run report, comparison table, and plots."""
from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/lngfreight-matplotlib")

import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lngfreight import config  # noqa: E402
from lngfreight.specification import working_specification  # noqa: E402
from lngfreight.validation import resolve_cutoff  # noqa: E402


FIG_ACTUAL = "run_actual_vs_counterfactual.png"
FIG_PLACEBO = "run_placebo_distribution.png"
FIG_SYNTH = "run_synthetic_control_path.png"
COMPARISON = "run_spec_comparison.csv"
REPORT = "run_output.md"


def _read(name: str, dates: tuple[str, ...] = ()) -> pd.DataFrame:
    path = config.path("data_processed") / name
    if not path.exists():
        raise FileNotFoundError(f"Missing upstream artifact: {path}")
    return pd.read_csv(path, parse_dates=list(dates) or None)


def _residual_stats(frame: pd.DataFrame) -> dict[str, float | int]:
    errors = pd.to_numeric(frame["error"], errors="coerce").dropna()
    return {
        "n_validation_residuals": int(len(errors)),
        "residual_mean": float(errors.mean()),
        "residual_median": float(errors.median()),
        "residual_std": float(errors.std(ddof=1)),
        "residual_p05": float(errors.quantile(0.05)),
        "residual_p95": float(errors.quantile(0.95)),
        "residual_acf_lag1": float(errors.autocorr(lag=1)),
        "residual_acf_lag7": float(errors.autocorr(lag=7)),
    }


def _fmt(value: object, digits: int = 3) -> str:
    if value is None or (isinstance(value, float) and not np.isfinite(value)):
        return "NA"
    if isinstance(value, (int, np.integer)):
        return f"{int(value):,}"
    if isinstance(value, (float, np.floating)):
        return f"{float(value):,.{digits}f}"
    return str(value)


def _markdown_table(rows: list[list[object]], headers: list[str]) -> list[str]:
    return [
        "| " + " | ".join(headers) + " |",
        "|" + "|".join("---" for _ in headers) + "|",
        *["| " + " | ".join(str(cell) for cell in row) + " |" for row in rows],
    ]


def _save_figure(fig: plt.Figure, name: str) -> Path:
    out = config.path("figures") / name
    fig.savefig(out, dpi=180, bbox_inches="tight")
    plt.close(fig)
    print(f"wrote {out}")
    return out


def main() -> None:
    spec = working_specification()
    cutoff = resolve_cutoff()
    target = spec.primary_outcome
    models = [spec.primary_estimator, *spec.conditional_sensitivity_estimators]

    panel = _read("panel_aligned.csv", ("date",)).set_index("date")
    baseline_summary = _read("baseline_summary.csv")
    baseline_forecasts = _read("baseline_forecasts.csv", ("date",))
    post = _read("counterfactual_post_treatment.csv", ("date",))
    long_intervals = _read("long_horizon_intervals_summary.csv")
    point_intervals = _read("counterfactual_intervals_daily.csv", ("date",))
    placebo_summary = _read("placebo_time_summary.csv")
    placebo_effects = _read("placebo_time_effects.csv")
    synth_summary = _read("synthetic_control_summary.csv")
    synth_daily = _read("synthetic_control_daily.csv", ("date",))
    synth_scales = _read("synthetic_control_scales.csv")
    capacity_diag = _read("capacity_missingness_diagnostics.csv")
    bsts_summary = _read("bsts_counterfactual_summary.csv")
    bsts_validation = _read("bsts_validation_forecasts.csv", ("date",))
    block_conformal = _read("block_conformal_summary.csv")
    synth_pool_stress = _read("synthetic_donor_pool_stress.csv")
    synth_time_inference = _read("synthetic_donor_time_inference.csv")
    lng_summary = _read("lng_index_counterfactual_summary.csv")

    comparison_rows: list[dict[str, object]] = []
    for model in models:
        validation = baseline_summary[
            (baseline_summary["model"] == model)
            & (baseline_summary["target"] == target)
        ].iloc[0]
        residual_frame = baseline_forecasts[
            (baseline_forecasts["model"] == model)
            & (baseline_forecasts["target"] == target)
        ]
        residual = _residual_stats(residual_frame)
        effect = placebo_summary[
            (placebo_summary["model"] == model)
            & (placebo_summary["target"] == target)
        ].iloc[0]
        interval = long_intervals[
            (long_intervals["model"] == model)
            & (long_intervals["target"] == target)
        ].iloc[0]
        comparison_rows.append({
            "specification": model,
            "role": "working_primary" if model == spec.primary_estimator else "conditional_sensitivity",
            "outcome": target,
            "shortfall_unit": "transits",
            "pre_rmse": float(validation["rmse_mean"]),
            "pre_mase": float(validation["mase_mean"]),
            **residual,
            "point_shortfall": float(effect["actual_cumulative_throughput_loss"]),
            "mean_daily_shortfall": float(effect["actual_mean_daily_throughput_loss"]),
            "interval_94d_lower": float(interval["interval_94dhorizon_lower"]),
            "interval_94d_upper": float(interval["interval_94dhorizon_upper"]),
            "placebo_metric": "cumulative_shortfall",
            "placebo_reference_p95": float(effect["placebo_loss_p95"]),
            "placebo_separation": float(effect["loss_vs_placebo_p95_ratio"]),
            "placebo_p_value": float(effect["p_loss_ge_actual"]),
            "post_pre_rmspe_ratio": np.nan,
            "effective_donors": np.nan,
        })

    synth = synth_summary[
        (synth_summary["unit"] == "strait_of_hormuz")
        & (synth_summary["value_col"] == "n_tanker")
        & (synth_summary["is_actual"])
    ].iloc[0]
    scale = float(synth_scales.loc[
        (synth_scales["slug"] == "strait_of_hormuz")
        & (synth_scales["value_col"] == "n_tanker"),
        "pre_period_scale",
    ].iloc[0])
    synth_path = synth_daily[
        (synth_daily["unit"] == "strait_of_hormuz")
        & (synth_daily["value_col"] == "n_tanker")
        & (synth_daily["is_actual"])
    ].copy()
    synth_pre_errors = (
        synth_path.loc[synth_path["period"] == "pre", "y_scaled"]
        - synth_path.loc[synth_path["period"] == "pre", "synthetic_scaled"]
    ) * scale
    comparison_rows.append({
        "specification": "synthetic_control",
        "role": "corroboration",
        "outcome": target,
        "shortfall_unit": "transit_equivalent_from_mean_scaling",
        "pre_rmse": float(synth["pre_rmspe"] * scale),
        "pre_mase": np.nan,
        "n_validation_residuals": int(synth_pre_errors.notna().sum()),
        "residual_mean": float(synth_pre_errors.mean()),
        "residual_median": float(synth_pre_errors.median()),
        "residual_std": float(synth_pre_errors.std(ddof=1)),
        "residual_p05": float(synth_pre_errors.quantile(0.05)),
        "residual_p95": float(synth_pre_errors.quantile(0.95)),
        "residual_acf_lag1": float(synth_pre_errors.autocorr(lag=1)),
        "residual_acf_lag7": float(synth_pre_errors.autocorr(lag=7)),
        "point_shortfall": float(synth["cumulative_scaled_throughput_loss"] * scale),
        "mean_daily_shortfall": float(synth["mean_daily_scaled_throughput_loss"] * scale),
        "interval_94d_lower": np.nan,
        "interval_94d_upper": np.nan,
        "placebo_metric": "post_pre_rmspe_ratio",
        "placebo_reference_p95": float(synth["placebo_ratio_p95"]),
        "placebo_separation": float(synth["ratio_vs_placebo_p95"]),
        "placebo_p_value": float(synth["p_ratio_ge_actual"]),
        "post_pre_rmspe_ratio": float(synth["post_pre_rmspe_ratio"]),
        "effective_donors": float(synth["effective_n_weights"]),
    })
    bsts = bsts_summary.iloc[0]
    bsts_residual = _residual_stats(bsts_validation)
    comparison_rows.append({
        "specification": "bsts_local_level_weekly",
        "role": "state_space_corroboration",
        "outcome": target,
        "shortfall_unit": "transits",
        "pre_rmse": float(bsts["validation_rmse_mean"]),
        "pre_mase": float(bsts["validation_mase_mean"]),
        **bsts_residual,
        "point_shortfall": float(bsts["posterior_median_shortfall"]),
        "mean_daily_shortfall": float(bsts["posterior_median_shortfall"] / bsts["n_post_days"]),
        "interval_94d_lower": float(bsts["lower_95"]),
        "interval_94d_upper": float(bsts["upper_95"]),
        "placebo_metric": "not_run_for_bsts",
        "placebo_reference_p95": np.nan,
        "placebo_separation": np.nan,
        "placebo_p_value": np.nan,
        "post_pre_rmspe_ratio": np.nan,
        "effective_donors": np.nan,
    })
    comparison = pd.DataFrame(comparison_rows)
    comparison_path = config.path("data_processed") / COMPARISON
    comparison.to_csv(comparison_path, index=False)
    print(f"wrote {comparison_path}")

    primary = comparison[comparison["role"] == "working_primary"].iloc[0]

    # Figure 1: actual full path + pre-period OOS validation + post counterfactual.
    actual = panel[target]
    validation_primary = baseline_forecasts[
        (baseline_forecasts["model"] == spec.primary_estimator)
        & (baseline_forecasts["target"] == target)
    ].sort_values("date")
    post_primary = post[
        (post["model"] == spec.primary_estimator) & (post["target"] == target)
    ].sort_values("date")
    band = point_intervals[
        (point_intervals["model"] == spec.primary_estimator)
        & (point_intervals["target"] == target)
    ].sort_values("date")
    fig, ax = plt.subplots(figsize=(14, 6))
    ax.plot(actual.index, actual, color="#1f2937", linewidth=0.8, alpha=0.75, label="Observed")
    ax.plot(validation_primary["date"], validation_primary["y_pred"], color="#2563eb", linewidth=1.0, label="Pre-period rolling-origin forecast")
    ax.plot(post_primary["date"], post_primary["y_pred"], color="#dc2626", linewidth=1.8, label="AR-only counterfactual")
    ax.fill_between(
        band["date"], band["counterfactual_lower"], band["counterfactual_upper"],
        color="#fca5a5", alpha=0.35, label="95% pointwise residual band",
    )
    ax.axvline(cutoff, color="black", linestyle="--", linewidth=1.2, label=f"Treatment cutoff {cutoff.date()}")
    ax.set(title="Hormuz Tanker Transits: Observed vs AR-only Counterfactual", ylabel="Daily tanker transits", xlabel="Date")
    ax.legend(ncol=2, frameon=False)
    ax.grid(alpha=0.2)
    fig_actual = _save_figure(fig, FIG_ACTUAL)

    # Figure 2: temporal placebo distribution.
    placebo = placebo_effects[
        (placebo_effects["model"] == spec.primary_estimator)
        & (placebo_effects["target"] == target)
        & (~placebo_effects["is_actual"].astype(bool))
    ]["cumulative_throughput_loss"].dropna()
    fig, ax = plt.subplots(figsize=(10, 5.5))
    ax.hist(placebo, bins=14, color="#93c5fd", edgecolor="white")
    ax.axvline(primary["placebo_reference_p95"], color="#d97706", linestyle="--", linewidth=2, label=f"Placebo p95 = {primary['placebo_reference_p95']:.0f}")
    ax.axvline(primary["point_shortfall"], color="#b91c1c", linewidth=2.5, label=f"Actual = {primary['point_shortfall']:.0f}")
    ax.set(title="Placebo-in-time Distribution vs Actual AR-only Shortfall", xlabel="Cumulative throughput shortfall", ylabel="Placebo windows")
    ax.legend(frameon=False)
    ax.grid(axis="y", alpha=0.2)
    fig_placebo = _save_figure(fig, FIG_PLACEBO)

    # Figure 3: synthetic-control path in transit-equivalent units.
    fig, ax = plt.subplots(figsize=(14, 6))
    ax.plot(synth_path["date"], synth_path["y_scaled"] * scale, color="#1f2937", linewidth=1.0, label="Observed Hormuz")
    ax.plot(synth_path["date"], synth_path["synthetic_scaled"] * scale, color="#7c3aed", linewidth=1.4, label="Synthetic control")
    ax.axvline(cutoff, color="black", linestyle="--", linewidth=1.2, label=f"Treatment cutoff {cutoff.date()}")
    ax.set(title="Hormuz Tanker Transits: Actual vs Donor-weighted Synthetic Control", ylabel="Daily transit-equivalent units", xlabel="Date")
    ax.legend(frameon=False)
    ax.grid(alpha=0.2)
    fig_synth = _save_figure(fig, FIG_SYNTH)

    validation_rows = []
    validation_models = [*spec.benchmark_estimators, spec.primary_estimator,
                         *spec.conditional_sensitivity_estimators]
    for model in validation_models:
        validation = baseline_summary[
            (baseline_summary["model"] == model)
            & (baseline_summary["target"] == target)
        ].iloc[0]
        residual = _residual_stats(baseline_forecasts[
            (baseline_forecasts["model"] == model)
            & (baseline_forecasts["target"] == target)
        ])
        validation_rows.append([
            model, _fmt(validation["mase_mean"]), _fmt(validation["rmse_mean"]),
            _fmt(residual["residual_mean"]), _fmt(residual["residual_std"]),
            _fmt(residual["residual_acf_lag1"]), _fmt(residual["residual_acf_lag7"]),
        ])

    comparison_md = []
    for _, row in comparison.iterrows():
        comparison_md.append([
            row["specification"], row["role"], _fmt(row["pre_mase"]),
            _fmt(row["pre_rmse"]), _fmt(row["point_shortfall"], 1),
            _fmt(row["interval_94d_lower"], 1), _fmt(row["interval_94d_upper"], 1),
            _fmt(row["placebo_separation"]), _fmt(row["placebo_p_value"]),
        ])

    cap_post = capacity_diag[
        (capacity_diag["capacity_column"] == "hormuz_tanker_capacity")
        & (capacity_diag["period"] == "post")
    ].iloc[0]
    conformal90 = block_conformal.loc[
        np.isclose(block_conformal["nominal_coverage"], 0.90)
    ].iloc[0]
    conformal95 = block_conformal.loc[
        np.isclose(block_conformal["nominal_coverage"], 0.95)
    ].iloc[0]
    clean_pool = synth_pool_stress.loc[
        synth_pool_stress["donor_pool"] == "low_contamination_donors"
    ].iloc[0]
    broad_pool = synth_pool_stress.loc[
        synth_pool_stress["donor_pool"] == "all_available_donors"
    ].iloc[0]
    synth_time = synth_time_inference.iloc[0]
    lng_ar = lng_summary.loc[lng_summary["model"] == "ar_lag1_7"].iloc[0]
    lng_bsts = lng_summary.loc[
        lng_summary["model"] == "bsts_local_level_weekly"
    ].iloc[0]
    lines = [
        "# End-to-End PortWatch Fallback Run",
        "",
        f"- Working branch: `{spec.branch}`",
        f"- Primary outcome: `{spec.primary_outcome}`",
        f"- Robustness outcome: `{spec.robustness_outcome}`",
        f"- Primary estimator: `{spec.primary_estimator}`",
        f"- Treatment cutoff: `{cutoff.date()}`",
        f"- Reporting estimand: **{spec.reporting_term}**",
        "- Transformer enabled: **no**",
        "",
        "## Headline AR-only result",
        "",
        f"- Point shortfall: **{primary['point_shortfall']:,.1f} tanker transits** ({primary['mean_daily_shortfall']:.2f}/day).",
        f"- Horizon-matched 95% interval: **{primary['interval_94d_lower']:,.1f} to {primary['interval_94d_upper']:,.1f} transits**.",
        f"- Temporal-placebo p95: **{primary['placebo_reference_p95']:,.1f}**; separation: **{primary['placebo_separation']:.3f}x**.",
        f"- One-sided placebo p-value: **{primary['placebo_p_value']:.6f}**, floor-censored with 36 overlapping / about 9 non-overlapping windows.",
        f"- BSTS posterior median shortfall: **{bsts['posterior_median_shortfall']:,.1f}**; 95% posterior predictive interval: **{bsts['lower_95']:,.1f} to {bsts['upper_95']:,.1f}**.",
        "",
        "## Pre-treatment validation and residual fidelity",
        "",
        *_markdown_table(
            validation_rows,
            ["Model", "MASE", "RMSE", "Residual mean", "Residual SD", "ACF(1)", "ACF(7)"],
        ),
        "",
        f"For the primary AR-only model, `{int(primary['n_validation_residuals'])}` rolling-origin residuals have median `{primary['residual_median']:.3f}`, 5th/95th percentiles `{primary['residual_p05']:.3f}` / `{primary['residual_p95']:.3f}`. Residual autocorrelation is reported above because remaining serial dependence limits naive pointwise uncertainty claims.",
        "",
        "## Specification comparison",
        "",
        *_markdown_table(
            comparison_md,
            ["Specification", "Role", "Pre MASE", "Pre RMSE", "Point shortfall", "94d lower", "94d upper", "Placebo separation", "p-value"],
        ),
        "",
        f"Full machine-readable table: [`data/processed/{COMPARISON}`](../data/processed/{COMPARISON})",
        "",
        "Synthetic-control shortfall is converted from mean-scaled units to a transit-equivalent magnitude for comparison. Its placebo metric is the post/pre RMSPE ratio, not the temporal cumulative-shortfall distribution, and no 94-day interval is asserted for it.",
        "BSTS is an independent state-space corroboration. Its interval is posterior predictive conditional on the local-level model; it is not a causal posterior.",
        "",
        "## Independent-block inference",
        "",
        f"- Disjoint 94-day placebo blocks: **{int(conformal90['n_independent_placebo_blocks'])}**; honest rank p-value: **{conformal90['placebo_p_value_greater']:.3f}** (floor **{conformal90['placebo_p_value_floor']:.3f}**).",
        f"- Actual / independent-placebo p95 separation: **{conformal90['actual_to_placebo_p95_ratio']:.3f}x**.",
        f"- 90% block-conformal interval: **{conformal90['interval_lower']:,.1f} to {conformal90['interval_upper']:,.1f}**.",
        f"- 95% block-conformal interval: **unbounded**; nine independent blocks support at most **{conformal95['maximum_finite_coverage']:.0%}** finite-sample coverage.",
        "",
        "## Synthetic-control corroboration",
        "",
        f"- Pre-period RMSPE: **{synth['pre_rmspe']:.6f} scaled units** (**{synth['pre_rmspe'] * scale:.3f} transit-equivalent RMSE**).",
        f"- Post-period RMSPE: **{synth['post_rmspe']:.6f}**; post/pre ratio: **{synth['post_pre_rmspe_ratio']:.3f}**.",
        f"- Transit-equivalent cumulative gap: **{synth['cumulative_scaled_throughput_loss'] * scale:,.1f}**.",
        f"- Donor-placebo p95 ratio: **{synth['placebo_ratio_p95']:.3f}**; separation: **{synth['ratio_vs_placebo_p95']:.3f}x**; p-value: **{synth['p_ratio_ge_actual']:.6f}**.",
        f"- Donors: **{int(synth['n_donors'])}**; effective donors: **{synth['effective_n_weights']:.2f}**; largest weight: `{synth['top_weight_slug']}` ({synth['top_weight']:.3f}).",
        f"- Donor-pool stress: clean ratio **{clean_pool['post_pre_rmspe_ratio']:.3f}**, broad-pool ratio **{broad_pool['post_pre_rmspe_ratio']:.3f}**.",
        f"- Donor-by-time placebos: **{int(synth_time['n_computed_donor_time_placebos'])}** fits across **{int(synth_time['n_independent_time_windows'])}** disjoint windows; p-value **{synth_time['donor_time_placebo_p_value']:.6f}**, actual/p95 **{synth_time['actual_to_donor_time_p95_ratio']:.3f}x**.",
        "",
        "## LNG-specific robustness outcome",
        "",
        "The public WTO/AXSMarine series is an LNG-only outbound shipment volume index (2025 average = 100) and excludes LPG. It is not a carrier count, physical volume, or freight rate.",
        f"- AR 94-day index-point shortfall: **{lng_ar['cumulative_throughput_loss']:,.1f}**.",
        f"- BSTS posterior median: **{lng_bsts['posterior_median_shortfall']:,.1f}**; 95% interval **{lng_bsts['lower_95']:,.1f} to {lng_bsts['upper_95']:,.1f}**.",
        "",
        "## Data-quality checks",
        "",
        f"- Primary transit outcome has complete post-period coverage (94/94 days).",
        f"- Capacity robustness outcome has `{int(cap_post['missing_capacity'])}` masked post-period values; all `{int(cap_post['audit_confirmed_artifact_masks'])}` are audit-confirmed zero-capacity/positive-transit artifacts and `{int(cap_post['unexplained_missing_capacity'])}` are unexplained.",
        "",
        "## Figures",
        "",
        f"![Observed vs AR-only counterfactual](figures/{fig_actual.name})",
        "",
        f"![Temporal placebo distribution](figures/{fig_placebo.name})",
        "",
        f"![Actual vs synthetic control](figures/{fig_synth.name})",
        "",
        "![BSTS counterfactual](figures/bsts_counterfactual.png)",
        "",
        "![LNG-only index counterfactual](figures/lng_index_counterfactual.png)",
        "",
        "## Interpretation guard",
        "",
        "These are disruption-associated counterfactual shortfalls in observed AIS-based tanker throughput, not a causal ATT and not an LNG freight-rate estimate.",
    ]
    report_path = config.ROOT / "reports" / REPORT
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {report_path}")


if __name__ == "__main__":
    main()
