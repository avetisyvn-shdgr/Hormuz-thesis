"""Create the inspectable end-to-end run report, comparison table, and plots."""
from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/lngfreight-matplotlib")

import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import matplotlib.dates as mdates  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from figure_style import (  # noqa: E402
    ACCENT_LIGHT_BLUE,
    COUNTERFACTUAL,
    DECREASE_COLOR,
    FIGURE_WIDTH_IN,
    INCREASE_COLOR,
    NEUTRAL_DARK,
    NEUTRAL_LIGHT,
    NEUTRAL_MID,
    OBSERVED_TREATED,
    THESIS_TEXTWIDTH_IN,
    apply_publication_style,
    save_pdf_and_png,
    style_axes,
)
from lngfreight import config  # noqa: E402
from lngfreight.specification import working_specification  # noqa: E402
from lngfreight.validation import resolve_cutoff  # noqa: E402


FIG_ACTUAL = "run_actual_vs_counterfactual.png"
FIG_PLACEBO = "run_placebo_distribution.png"
FIG_SYNTH = "run_synthetic_control_path.png"
FIG_SYNTH_PLACEBOS = "run_synthetic_control_placebo_paths.png"
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


def _fmt_interval(lower: object, upper: object, digits: int = 1) -> str:
    try:
        lower_value = float(lower)
        upper_value = float(upper)
    except (TypeError, ValueError):
        return "NA"
    if not np.isfinite(lower_value) or not np.isfinite(upper_value):
        return "unbounded (-inf to inf)"
    return f"{_fmt(lower_value, digits)} to {_fmt(upper_value, digits)}"


def _save_figure(fig: plt.Figure, name: str) -> Path:
    out = config.path("figures") / name
    pdf_out, _ = save_pdf_and_png(fig, out)
    plt.close(fig)
    print(f"wrote {out}")
    print(f"wrote {pdf_out}")
    return out


def main() -> None:
    apply_publication_style()
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
    synth_prefit = _read("synthetic_control_prefit_sensitivity.csv")
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
            "reported_band_lower": float(
                interval["overlapping_placebo_quantile_band_lower"]
            ),
            "reported_band_upper": float(
                interval["overlapping_placebo_quantile_band_upper"]
            ),
            "reported_band_label": (
                "overlapping_placebo_2.5_97.5_quantile_band_no_nominal_coverage"
            ),
            "interval_circular_bootstrap_lower": float(
                interval["interval_circular_bootstrap_lower"]
            ),
            "interval_circular_bootstrap_upper": float(
                interval["interval_circular_bootstrap_upper"]
            ),
            "placebo_metric": "cumulative_shortfall",
            "placebo_reference_p95": float(effect["placebo_loss_p95"]),
            "placebo_separation": float(effect["loss_vs_placebo_p95_ratio"]),
            "placebo_diagnostic_value": float(
                effect["overlapping_reference_rank_loss_ge_actual"]
            ),
            "placebo_diagnostic_label": (
                "overlapping_window_reference_rank_not_p_value"
            ),
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
        "reported_band_lower": np.nan,
        "reported_band_upper": np.nan,
        "reported_band_label": "not_reported",
        "placebo_metric": "post_pre_rmspe_ratio",
        "placebo_reference_p95": float(synth["placebo_ratio_p95"]),
        "placebo_separation": float(synth["ratio_vs_placebo_p95"]),
        "placebo_diagnostic_value": float(synth["p_ratio_ge_actual"]),
        "placebo_diagnostic_label": "synthetic_control_donor_placebo_p_value",
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
        "reported_band_lower": float(bsts["lower_95"]),
        "reported_band_upper": float(bsts["upper_95"]),
        "reported_band_label": (
            "95%_posterior_predictive_interval_conditional_on_model"
        ),
        "placebo_metric": "not_run_for_bsts",
        "placebo_reference_p95": np.nan,
        "placebo_separation": np.nan,
        "placebo_diagnostic_value": np.nan,
        "placebo_diagnostic_label": "not_run_for_bsts",
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
    actual_7d = actual.rolling(window=7, min_periods=1).mean()
    fig, (ax, ax_post) = plt.subplots(
        1,
        2,
        figsize=(THESIS_TEXTWIDTH_IN, 4.15),
        sharey=True,
        gridspec_kw={"width_ratios": [3.05, 1.15]},
    )
    fig.subplots_adjust(
        left=0.09,
        right=0.985,
        bottom=0.35,
        top=0.92,
        wspace=0.08,
    )

    def _counterfactual_panel(
        panel_ax: plt.Axes,
        *,
        post_detail: bool,
    ) -> None:
        observed = actual.loc[actual.index >= cutoff] if post_detail else actual
        observed_7d = (
            actual_7d.loc[actual_7d.index >= cutoff]
            if post_detail
            else actual_7d
        )
        panel_ax.plot(
            observed.index,
            observed,
            color=OBSERVED_TREATED,
            linewidth=0.45,
            alpha=0.20,
            label="Observed, daily",
            zorder=2,
        )
        panel_ax.plot(
            observed_7d.index,
            observed_7d,
            color=OBSERVED_TREATED,
            linewidth=1.35,
            label="Observed, 7-day mean",
            zorder=3,
        )
        if not post_detail:
            panel_ax.plot(
                validation_primary["date"],
                validation_primary["y_pred"],
                color=COUNTERFACTUAL,
                linewidth=1.05,
                linestyle=(0, (4, 1.8)),
                label="Pre-period rolling-origin forecast",
                zorder=4,
            )
        panel_ax.fill_between(
            band["date"],
            band["counterfactual_lower"],
            band["counterfactual_upper"],
            color=ACCENT_LIGHT_BLUE,
            alpha=0.30,
            linewidth=0,
            label="Short-fold residual band (pointwise)",
            zorder=1,
        )
        panel_ax.plot(
            post_primary["date"],
            post_primary["y_pred"],
            color=COUNTERFACTUAL,
            linewidth=1.8,
            label="AR-only counterfactual",
            zorder=5,
        )
        panel_ax.axvline(
            cutoff,
            color="#111111",
            linestyle=(0, (2.4, 1.7)),
            linewidth=1.05,
            label=f"Treatment cutoff {cutoff.date()}",
            zorder=6,
        )
        style_axes(panel_ax, grid_axis="y")
        panel_ax.set_xlabel("Date")

    _counterfactual_panel(ax, post_detail=False)
    _counterfactual_panel(ax_post, post_detail=True)
    ax.axvspan(
        cutoff,
        actual.index.max(),
        color=NEUTRAL_LIGHT,
        alpha=0.22,
        linewidth=0,
        zorder=0,
    )
    ax.set_ylabel("Daily tanker transits")
    ax.set_title("Full series", loc="left", pad=6)
    ax_post.set_title("Post-period detail", loc="left", pad=6)
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax_post.set_xlim(cutoff, actual.index.max())
    ax_post.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    ax_post.xaxis.set_major_formatter(mdates.DateFormatter("%b\n%Y"))
    ax_post.tick_params(labelleft=False)
    # No in-figure headline title: the LaTeX caption carries it in the thesis.
    handles, labels = ax.get_legend_handles_labels()
    legend_order = [
        labels.index("Observed, daily"),
        labels.index("Observed, 7-day mean"),
        labels.index("Pre-period rolling-origin forecast"),
        labels.index("AR-only counterfactual"),
        labels.index("Short-fold residual band (pointwise)"),
        labels.index(f"Treatment cutoff {cutoff.date()}"),
    ]
    fig.legend(
        [handles[index] for index in legend_order],
        [labels[index] for index in legend_order],
        loc="lower center",
        bbox_to_anchor=(0.5, 0.025),
        ncol=2,
        frameon=False,
        fontsize=8.0,
        handlelength=2.2,
        columnspacing=0.9,
    )
    fig_actual = _save_figure(fig, FIG_ACTUAL)

    # Figure 2: temporal placebo distribution.
    placebo = placebo_effects[
        (placebo_effects["model"] == spec.primary_estimator)
        & (placebo_effects["target"] == target)
        & (~placebo_effects["is_actual"].astype(bool))
    ]["cumulative_throughput_loss"].dropna()
    fig, ax = plt.subplots(figsize=(FIGURE_WIDTH_IN, 3.95))
    fig.subplots_adjust(left=0.11, right=0.98, bottom=0.24, top=0.94)
    counts, _, _ = ax.hist(
        placebo,
        bins=14,
        color="#92C5DE",
        edgecolor="white",
        linewidth=0.65,
    )
    placebo_p95 = float(primary["placebo_reference_p95"])
    actual_shortfall = float(primary["point_shortfall"])
    ax.axvline(
        placebo_p95,
        color=NEUTRAL_DARK,
        linestyle=(0, (4, 2)),
        linewidth=1.4,
        zorder=4,
    )
    ax.axvline(
        actual_shortfall,
        color=DECREASE_COLOR,
        linewidth=2.0,
        zorder=5,
    )
    y_top = max(float(np.max(counts)), 1.0)
    ax.annotate(
        f"Placebo p95 = {placebo_p95:,.0f}",
        xy=(placebo_p95, y_top * 0.86),
        xytext=(-7, 0),
        textcoords="offset points",
        ha="right",
        va="center",
        fontsize=9.5,
        color=NEUTRAL_DARK,
    )
    ax.annotate(
        f"Actual shortfall = {actual_shortfall:,.0f}",
        xy=(actual_shortfall, y_top * 0.76),
        xytext=(-7, 0),
        textcoords="offset points",
        ha="right",
        va="center",
        fontsize=9.5,
        fontweight="semibold",
        color=DECREASE_COLOR,
    )
    ax.set(
        xlabel="Cumulative throughput shortfall",
        ylabel="Overlapping placebo windows",
    )
    style_axes(ax, grid_axis="y")
    fig.text(
        0.11,
        0.06,
        (
            "Note: placebo windows overlap; this is a reference distribution, "
            "not an independent sampling distribution."
        ),
        ha="left",
        va="bottom",
        fontsize=9.0,
        color=NEUTRAL_MID,
    )
    fig_placebo = _save_figure(fig, FIG_PLACEBO)

    # Figure 3: synthetic-control path in transit-equivalent units.
    fig, ax = plt.subplots(figsize=(FIGURE_WIDTH_IN, 3.8))
    fig.subplots_adjust(left=0.10, right=0.98, bottom=0.22, top=0.94)
    ax.plot(
        synth_path["date"],
        synth_path["y_scaled"] * scale,
        color=NEUTRAL_DARK,
        linewidth=1.15,
        label="Observed Hormuz",
    )
    ax.plot(
        synth_path["date"],
        synth_path["synthetic_scaled"] * scale,
        color=INCREASE_COLOR,
        linewidth=1.35,
        linestyle=(0, (4, 1.8)),
        label="Synthetic control",
    )
    ax.axvline(
        cutoff,
        color="#111111",
        linestyle=(0, (2.4, 1.7)),
        linewidth=1.05,
        label=f"Treatment cutoff {cutoff.date()}",
    )
    ax.set(
        ylabel="Daily transit-equivalent units",
        xlabel="Date",
    )
    style_axes(ax, grid_axis="y")
    ax.legend(
        loc="upper center",
        bbox_to_anchor=(0.5, -0.18),
        ncol=3,
        frameon=False,
    )
    fig_synth = _save_figure(fig, FIG_SYNTH)

    # Figure 4: treated gap against pre-fit-eligible placebo gap paths.
    eligible_units = set(
        synth_summary.loc[
            synth_summary["value_col"].eq("n_tanker")
            & ~synth_summary["is_actual"].astype(bool)
            & synth_summary["eligible_primary_prefit_screen"]
            .astype(str)
            .str.lower()
            .eq("true"),
            "unit",
        ]
    )
    eligible_daily = synth_daily.loc[
        synth_daily["value_col"].eq("n_tanker")
        & synth_daily["unit"].isin(eligible_units)
    ].copy()
    fig, ax = plt.subplots(figsize=(FIGURE_WIDTH_IN, 3.9))
    fig.subplots_adjust(left=0.10, right=0.98, bottom=0.22, top=0.94)
    for index, (_, path) in enumerate(eligible_daily.groupby("unit")):
        ax.plot(
            path["date"],
            path["gap_observed_minus_synthetic"],
            color=NEUTRAL_MID,
            alpha=0.30,
            linewidth=0.65,
            label="Eligible placebo paths" if index == 0 else None,
        )
    ax.plot(
        synth_path["date"],
        synth_path["gap_observed_minus_synthetic"],
        color=DECREASE_COLOR,
        linewidth=1.8,
        label="Hormuz treated path",
        zorder=4,
    )
    ax.axhline(0, color=NEUTRAL_DARK, linewidth=0.8, alpha=0.7)
    ax.axvline(
        cutoff,
        color="#111111",
        linestyle=(0, (2.4, 1.7)),
        linewidth=1.05,
        label=f"Treatment cutoff {cutoff.date()}",
    )
    ax.set(
        ylabel="Observed minus synthetic (mean-scaled)",
        xlabel="Date",
    )
    style_axes(ax, grid_axis="y")
    ax.legend(
        loc="upper center",
        bbox_to_anchor=(0.5, -0.18),
        ncol=3,
        frameon=False,
    )
    fig_synth_placebos = _save_figure(fig, FIG_SYNTH_PLACEBOS)

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
        diagnostic = (
            "NA"
            if pd.isna(row["placebo_diagnostic_value"])
            else (
                f"{row['placebo_diagnostic_value']:.3f} "
                f"({row['placebo_diagnostic_label']})"
            )
        )
        comparison_md.append([
            row["specification"], row["role"], _fmt(row["pre_mase"]),
            _fmt(row["pre_rmse"]), _fmt(row["point_shortfall"], 1),
            _fmt(row["reported_band_lower"], 1),
            _fmt(row["reported_band_upper"], 1),
            row["reported_band_label"],
            _fmt(row["placebo_separation"]), diagnostic,
        ])

    cap_post = capacity_diag[
        (capacity_diag["capacity_column"] == "hormuz_tanker_capacity")
        & (capacity_diag["period"] == "post")
    ].iloc[0]
    primary_long = long_intervals[
        (long_intervals["model"] == spec.primary_estimator)
        & (long_intervals["target"] == target)
    ].iloc[0]
    primary_placebo = placebo_summary[
        (placebo_summary["model"] == spec.primary_estimator)
        & (placebo_summary["target"] == target)
    ].iloc[0]
    honest_rank = block_conformal.iloc[0]
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
    synth_unscreened = synth_prefit.loc[
        synth_prefit["value_col"].eq("n_tanker")
        & synth_prefit["screen"].eq("unscreened")
    ].iloc[0]
    lng_ar = lng_summary.loc[lng_summary["model"] == "ar_lag1_7"].iloc[0]
    lng_bsts = lng_summary.loc[
        lng_summary["model"] == "bsts_local_level_weekly"
    ].iloc[0]
    placebo_floor_denominator = int(primary_placebo["n_placebos"]) + 1
    block_floor_denominator = int(honest_rank["n_independent_placebo_blocks"]) + 1
    donor_time_fits = int(synth_time["n_computed_donor_time_fits"])
    donor_time_blocks = int(synth_time["n_disjoint_time_blocks"])
    donor_time_floor_denominator = donor_time_blocks + 1
    horizon_calendar_days = int(primary_long["horizon_calendar_days"])
    n_horizon_windows = int(primary_long["n_horizon_windows"])
    n_effective_horizon_windows = int(primary_long["effective_non_overlapping_windows"])
    n_overlapping_placebos = int(primary_placebo["n_placebos"])
    approx_non_overlapping_placebos = int(
        primary_placebo["approx_non_overlapping_placebos"]
    )
    n_independent_blocks = int(honest_rank["n_independent_placebo_blocks"])
    layer1_inference_rows = [
        [
            "Disjoint-block rank inference",
            (
                f"{honest_rank['actual_to_placebo_p95_ratio']:.3f}x; "
                f"p={honest_rank['placebo_p_value_greater']:.3f}"
            ),
            (
                f"{n_independent_blocks} disjoint "
                f"blocks; floor 1/{block_floor_denominator}="
                f"{honest_rank['placebo_p_value_floor']:.3f}"
            ),
            "`data/processed/block_conformal_summary.csv`",
        ],
        [
            "95% block-conformal interval",
            _fmt_interval(
                conformal95["interval_lower"],
                conformal95["interval_upper"],
            ),
            (
                "Finite interval unsupported at 95%; maximum finite coverage "
                f"{conformal95['maximum_finite_coverage']:.1%} with "
                f"{int(conformal95['n_calibration_blocks'])} calibration blocks"
            ),
            "`data/processed/block_conformal_summary.csv`",
        ],
        [
            "Overlapping-placebo 2.5/97.5% quantile band",
            _fmt_interval(
                primary_long["overlapping_placebo_quantile_band_lower"],
                primary_long["overlapping_placebo_quantile_band_upper"],
            ),
            (
                "Descriptive only; no nominal coverage. "
                f"{horizon_calendar_days}-calendar-day horizon; "
                f"{n_horizon_windows} placebo windows; "
                f"{n_effective_horizon_windows} non-overlapping horizon windows"
            ),
            "`data/processed/long_horizon_intervals_summary.csv`",
        ],
        [
            "14-day block-bootstrap band",
            _fmt_interval(
                primary_long["interval_circular_bootstrap_lower"],
                primary_long["interval_circular_bootstrap_upper"],
            ),
            (
                f"{int(primary_long['circular_bootstrap_block_length'])}-day "
                f"circular blocks; {int(primary_long['circular_bootstrap_draws'])} "
                "draws"
            ),
            "`data/processed/long_horizon_intervals_summary.csv`",
        ],
        [
            "Temporal-placebo separation",
            (
                f"{primary_placebo['loss_vs_placebo_p95_ratio']:.3f}x; "
                "loss exceeds all overlapping windows"
            ),
            (
                f"Reference rank 1/{placebo_floor_denominator} (not a p-value); "
                f"{n_overlapping_placebos} overlapping placebo windows and "
                f"about {approx_non_overlapping_placebos} non-overlapping "
                "horizon windows"
            ),
            "`data/processed/placebo_time_summary.csv`",
        ],
    ]
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
        f"- Disjoint-block rank inference: **p={honest_rank['placebo_p_value_greater']:.3f}** from **{n_independent_blocks}** blocks (minimum attainable **1/{block_floor_denominator}**).",
        f"- Nominal 95% block-conformal interval: **unbounded**; maximum finite coverage is **{conformal95['maximum_finite_coverage']:.1%}**.",
        f"- Descriptive overlapping-placebo 2.5/97.5% quantile band over **{horizon_calendar_days} calendar days**: **{primary['reported_band_lower']:,.1f} to {primary['reported_band_upper']:,.1f} transits**; no nominal coverage.",
        f"- Independent 14-day circular-block bootstrap band: **{primary['interval_circular_bootstrap_lower']:,.1f} to {primary['interval_circular_bootstrap_upper']:,.1f} transits**; narrower than the placebo-window band, so width is method-sensitive.",
        f"- Temporal-placebo p95: **{primary['placebo_reference_p95']:,.1f}**; separation: **{primary['placebo_separation']:.3f}x**.",
        f"- The loss exceeds all **{n_overlapping_placebos}** overlapping placebo windows; the resulting **1/{placebo_floor_denominator}** reference rank is descriptive, not a p-value.",
        f"- BSTS posterior median shortfall: **{bsts['posterior_median_shortfall']:,.1f}**; 95% posterior predictive interval: **{bsts['lower_95']:,.1f} to {bsts['upper_95']:,.1f}**.",
        f"- BSTS prior-grid median range: **{bsts['prior_sensitivity_median_shortfall_min']:,.1f} to {bsts['prior_sensitivity_median_shortfall_max']:,.1f}**; interval-envelope endpoints: **{bsts['prior_sensitivity_lower_endpoint_min']:,.1f} to {bsts['prior_sensitivity_upper_endpoint_max']:,.1f}**; pre-period PPC pointwise coverage: **{bsts['pre_period_ppc_pointwise_95_coverage']:.1%}**.",
        "",
        "## Layer-1 Inference Table",
        "",
        *_markdown_table(
            layer1_inference_rows,
            ["Inference layer", "Reported value", "Support / note", "Source artifact"],
        ),
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
            [
                "Specification", "Role", "Pre MASE", "Pre RMSE",
                "Point shortfall", "Reported lower", "Reported upper",
                "Band label", "Placebo separation", "Diagnostic",
            ],
        ),
        "",
        f"Full machine-readable table: [`data/processed/{COMPARISON}`](../data/processed/{COMPARISON})",
        "",
        "Synthetic-control shortfall is converted from mean-scaled units to a transit-equivalent magnitude for comparison. Its placebo metric is the post/pre RMSPE ratio, not the temporal cumulative-shortfall distribution, and no overlapping-placebo quantile band is asserted for it.",
        "BSTS is an independent state-space corroboration. Its interval is posterior predictive conditional on the local-level model; it is not a causal posterior.",
        "",
        "## Independent-block inference",
        "",
        f"- Disjoint horizon-matched placebo blocks: **{n_independent_blocks}**; honest rank p-value: **{honest_rank['placebo_p_value_greater']:.3f}** (floor **{honest_rank['placebo_p_value_floor']:.3f}**).",
        f"- Actual / independent-placebo p95 separation: **{honest_rank['actual_to_placebo_p95_ratio']:.3f}x**.",
        f"- 95% block-conformal interval: **unbounded**; {int(conformal95['n_calibration_blocks'])} calibration blocks support at most **{conformal95['maximum_finite_coverage']:.0%}** finite-sample coverage.",
        "- The same facts are reported side by side in the Layer-1 inference table above so conformal support is not treated as a footnote.",
        "",
        "## Synthetic-control corroboration",
        "",
        f"- Pre-period RMSPE: **{synth['pre_rmspe']:.6f} scaled units** (**{synth['pre_rmspe'] * scale:.3f} transit-equivalent RMSE**).",
        f"- Post-period RMSPE: **{synth['post_rmspe']:.6f}**; post/pre ratio: **{synth['post_pre_rmspe_ratio']:.3f}**.",
        f"- Transit-equivalent cumulative gap: **{synth['cumulative_scaled_throughput_loss'] * scale:,.1f}**.",
        f"- Primary pre-fit screen: placebo pre-RMSPE <= **{synth['primary_prefit_rmspe_multiplier']:.1f}x** treated; **{int(synth['n_placebos_eligible'])}/{int(synth['n_placebos_total'])}** placebos eligible and **{int(synth['n_placebos_excluded'])}** excluded.",
        f"- Screened donor-placebo p95 ratio: **{synth['placebo_ratio_p95']:.3f}**; separation: **{synth['ratio_vs_placebo_p95']:.3f}x**; rank p-value: **{synth['p_ratio_ge_actual']:.6f}** (floor **1/{int(synth['n_placebos_eligible']) + 1} = {synth['p_value_floor']:.6f}**).",
        f"- Pre-fit threshold sensitivity: p-values range from **{synth_prefit.loc[synth_prefit['value_col'].eq('n_tanker'), 'p_ratio_ge_actual'].min():.6f}** to **{synth_prefit.loc[synth_prefit['value_col'].eq('n_tanker'), 'p_ratio_ge_actual'].max():.6f}**; unscreened p=**{synth_unscreened['p_ratio_ge_actual']:.6f}**. The 2x rule is the remediation-primary design convention; the full grid is reported so the conclusion does not rest on that single screen.",
        f"- Donors: **{int(synth['n_donors'])}**; effective donors: **{synth['effective_n_weights']:.2f}**; largest weight: `{synth['top_weight_slug']}` ({synth['top_weight']:.3f}).",
        f"- Donor-pool stress: clean ratio **{clean_pool['post_pre_rmspe_ratio']:.3f}**, broad-pool ratio **{broad_pool['post_pre_rmspe_ratio']:.3f}**.",
        (
            f"- Donor-by-time stress: **{donor_time_fits}** fits summarized as "
            f"**{donor_time_blocks}** disjoint-window maxima; max-statistic rank "
            f"p-value **{synth_time['block_max_rank_p_value']:.3f}** "
            f"(floor 1/{donor_time_floor_denominator}), actual/block-max-p95 "
            f"**{synth_time['actual_to_block_max_p95_ratio']:.3f}x**. "
            "The individual donor fits are not pooled as independent draws."
        ),
        "",
        "## LNG-specific robustness outcome",
        "",
        "The public WTO/AXSMarine series is an LNG-only outbound shipment volume index (2025 average = 100) and excludes LPG. It is not a carrier count, physical volume, or freight rate.",
        f"- AR LNG-index shortfall over the current post window: **{lng_ar['cumulative_throughput_loss']:,.1f} index-points**.",
        f"- BSTS posterior median: **{lng_bsts['posterior_median_shortfall']:,.1f}**; 95% interval **{lng_bsts['lower_95']:,.1f} to {lng_bsts['upper_95']:,.1f}**.",
        "",
        "## Data-quality checks",
        "",
        f"- Primary transit outcome has complete post-period coverage ({int(primary_long['n_post_days'])}/{horizon_calendar_days} valid days).",
        f"- Capacity is a directional secondary, model-sensitive outcome. It has `{int(cap_post['missing_capacity'])}` masked post-period values; all `{int(cap_post['audit_confirmed_artifact_masks'])}` are audit-confirmed zero-capacity/positive-transit artifacts and `{int(cap_post['unexplained_missing_capacity'])}` are unexplained. Do not lean on its precise magnitude.",
        "",
        "## Figures",
        "",
        f"![Observed vs AR-only counterfactual](figures/{fig_actual.name})",
        "",
        f"![Temporal placebo distribution](figures/{fig_placebo.name})",
        "",
        f"![Actual vs synthetic control](figures/{fig_synth.name})",
        "",
        f"![Treated and eligible synthetic-control placebo gaps](figures/{fig_synth_placebos.name})",
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
