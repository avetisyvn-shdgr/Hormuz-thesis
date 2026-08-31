"""Render the three Chapter 5 synthesis figures from frozen analysis artifacts.

The headline observed-versus-counterfactual path is already rendered by
``make_run_output.py``.  This module supplies the figures that the six-chapter
manuscript needs but the earlier, more segmented figure catalog did not:

* cumulative shortfall and endpoint uncertainty;
* a four-panel adaptation synthesis; and
* a four-panel falsification/robustness synthesis.

No model is fitted here.  Every plotted value is read from an admitted processed
artifact or a frozen experiment output.
"""
from __future__ import annotations

import os
import sys
import json
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/hormuz_throughput-matplotlib")

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.dates as mdates  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from figure_style import (  # noqa: E402
    ACCENT_BLUE,
    ACCENT_LIGHT_BLUE,
    ACCENT_ORANGE,
    COUNTERFACTUAL,
    NEUTRAL_DARK,
    NEUTRAL_LIGHT,
    NEUTRAL_MID,
    OBSERVED_TREATED,
    SECONDARY_BLUE,
    THESIS_TEXTWIDTH_IN,
    apply_publication_style,
    save_pdf_and_png,
    style_axes,
)
PROC = ROOT / "data" / "processed"
FIG_DIR = ROOT / "reports" / "figures"
NETWORK = ROOT / "experiments" / "network_adaptation" / "outputs"
POSITIVE = ROOT / "experiments" / "positive_control" / "outputs"
TARGET = "hormuz_tanker_transits"

FIG_CUMULATIVE = "chapter5_cumulative_shortfall_uncertainty.png"
FIG_ADAPTATION = "chapter5_adaptation_synthesis.png"
FIG_ROBUSTNESS = "chapter5_robustness_synthesis.png"


def _csv(path: Path, *, dates: tuple[str, ...] = ()) -> pd.DataFrame:
    if not path.is_file():
        raise FileNotFoundError(f"Missing upstream artifact: {path}")
    return pd.read_csv(path, parse_dates=list(dates) or None)


def _processed(name: str, *, dates: tuple[str, ...] = ()) -> pd.DataFrame:
    return _csv(PROC / name, dates=dates)


def _json(path: Path) -> dict:
    if not path.is_file():
        raise FileNotFoundError(f"Missing upstream artifact: {path}")
    return json.loads(path.read_text())


def _save(fig: plt.Figure, filename: str) -> Path:
    out = FIG_DIR / filename
    save_pdf_and_png(fig, out, dpi=300)
    plt.close(fig)
    print(f"wrote {out.with_suffix('.pdf').relative_to(ROOT)}")
    print(f"wrote {out.relative_to(ROOT)}")
    return out


def _bar_labels(
    ax: plt.Axes,
    bars,
    values: list[float],
    *,
    fmt: str = "{:+.1f}%",
    fontsize: float = 7.0,
    horizontal: bool = False,
) -> None:
    """Place signed labels outside bars and leave enough axis headroom."""
    for bar, value in zip(bars, values):
        if horizontal:
            y = bar.get_y() + bar.get_height() / 2
            if value < 0:
                x, dx, ha, colour = 0.0, -4, "right", "white"
            else:
                x, dx, ha, colour = value, 4, "left", NEUTRAL_DARK
            ax.annotate(
                fmt.format(value),
                xy=(x, y),
                xytext=(dx, 0),
                textcoords="offset points",
                ha=ha,
                va="center",
                fontsize=fontsize,
                color=colour,
            )
        else:
            x = bar.get_x() + bar.get_width() / 2
            ax.annotate(
                fmt.format(value),
                xy=(x, value),
                xytext=(0, 4 if value >= 0 else -4),
                textcoords="offset points",
                ha="center",
                va="bottom" if value >= 0 else "top",
                fontsize=fontsize,
            )


def figure_cumulative_shortfall_uncertainty() -> Path:
    post = _processed("counterfactual_post_treatment.csv", dates=("date",))
    post = post[
        post["model"].eq("ar_lag1_7") & post["target"].eq(TARGET)
    ].sort_values("date")
    if len(post) != 130:
        raise ValueError(f"Expected 130 primary post-period rows, found {len(post)}")

    long_horizon = _processed("long_horizon_intervals_summary.csv")
    long_row = long_horizon[
        long_horizon["model"].eq("ar_lag1_7")
        & long_horizon["target"].eq(TARGET)
    ].iloc[0]
    bsts = _processed("run_spec_comparison.csv")
    bsts = bsts[
        bsts["outcome"].eq(TARGET)
        & bsts["specification"].eq("bsts_local_level_weekly")
    ].iloc[0]
    frontier = _processed("horizon_frontier_summary.csv")
    frontier = frontier[
        frontier["horizon_days"].eq(130)
        & frontier["outcome"].eq(TARGET)
        & frontier["level"].eq(0.80)
    ]

    def _frontier(rule: str) -> pd.Series:
        row = frontier[frontier["origin_rule"].eq(rule)]
        if len(row) != 1:
            raise ValueError(f"Expected one 130-day 80% row for {rule}")
        return row.iloc[0]

    locked = _frontier("legacy_greedy_step30")
    packed = _frontier("forward_anchored_direct")
    point = float(post["cumulative_throughput_loss"].iloc[-1])

    intervals = [
        (
            "BSTS predictive, 95%\n(model-conditional)",
            float(bsts["reported_band_lower"]),
            float(bsts["reported_band_upper"]),
            "model",
        ),
        (
            "Block conformal, 80%\n(exhaustive 8-block sensitivity)",
            float(packed["interval_lower"]),
            float(packed["interval_upper"]),
            "nominal",
        ),
        (
            "Block conformal, 80%\n(locked 7-block partition)",
            float(locked["interval_lower"]),
            float(locked["interval_upper"]),
            "nominal_primary",
        ),
        (
            "Overlapping-placebo\nquantile band",
            float(long_row["overlapping_placebo_quantile_band_lower"]),
            float(long_row["overlapping_placebo_quantile_band_upper"]),
            "descriptive",
        ),
        (
            "Circular block bootstrap\n(14-day blocks)",
            float(long_row["interval_circular_bootstrap_lower"]),
            float(long_row["interval_circular_bootstrap_upper"]),
            "descriptive",
        ),
        (
            "Residual-calibrated\n30-day folds",
            float(long_row["interval_30dfold_lower"]),
            float(long_row["interval_30dfold_upper"]),
            "descriptive",
        ),
    ]

    apply_publication_style()
    fig, (ax_path, ax_band) = plt.subplots(
        2,
        1,
        figsize=(THESIS_TEXTWIDTH_IN, 5.85),
        gridspec_kw={"height_ratios": [1.0, 1.32], "hspace": 0.48},
    )
    fig.subplots_adjust(left=0.31, right=0.975, top=0.965, bottom=0.205)

    ax_path.fill_between(
        post["date"],
        0,
        post["cumulative_throughput_loss"],
        color=OBSERVED_TREATED,
        alpha=0.12,
        linewidth=0,
    )
    ax_path.plot(
        post["date"],
        post["cumulative_throughput_loss"],
        color=OBSERVED_TREATED,
        linewidth=1.8,
    )
    checkpoints = post.iloc[[29, 64, 89, 129]]
    ax_path.scatter(
        checkpoints["date"],
        checkpoints["cumulative_throughput_loss"],
        s=19,
        color=OBSERVED_TREATED,
        zorder=4,
    )
    for row in checkpoints.itertuples():
        ax_path.annotate(
            f"{row.cumulative_throughput_loss:,.0f}",
            xy=(row.date, row.cumulative_throughput_loss),
            xytext=(-3 if row.Index == checkpoints.index[-1] else 0, 7),
            textcoords="offset points",
            ha="right" if row.Index == checkpoints.index[-1] else "center",
            fontsize=7.0,
            color=OBSERVED_TREATED,
        )
    ax_path.set_title("(a) Accumulation over the scored window", loc="left", fontsize=9.3)
    ax_path.set_ylabel("Cumulative shortfall\n(transits)")
    ax_path.set_xlabel("Date")
    ax_path.xaxis.set_major_locator(mdates.MonthLocator())
    ax_path.xaxis.set_major_formatter(mdates.DateFormatter("%b\n2026"))
    ax_path.set_ylim(bottom=0)
    style_axes(ax_path, grid_axis="y")

    colours = {
        "model": ACCENT_LIGHT_BLUE,
        "nominal": COUNTERFACTUAL,
        "nominal_primary": SECONDARY_BLUE,
        "descriptive": NEUTRAL_DARK,
    }
    y = np.arange(len(intervals))[::-1]
    for yi, (_, lo, hi, role) in zip(y, intervals):
        colour = colours[role]
        linewidth = 3.0 if role == "nominal_primary" else 2.2
        ax_band.plot([lo, hi], [yi, yi], color=colour, linewidth=linewidth, zorder=3)
        ax_band.plot([lo, lo], [yi - 0.13, yi + 0.13], color=colour, linewidth=1.1)
        ax_band.plot([hi, hi], [yi - 0.13, yi + 0.13], color=colour, linewidth=1.1)
        ax_band.plot(point, yi, "o", color=OBSERVED_TREATED, markersize=3.6, zorder=4)
    ax_band.axvline(point, color=OBSERVED_TREATED, linewidth=0.85, linestyle="--")
    ax_band.axvline(0, color=NEUTRAL_MID, linewidth=0.7)
    ax_band.set_yticks(y)
    ax_band.set_yticklabels([label for label, _, _, _ in intervals], fontsize=7.0)
    ax_band.set_xlim(-350, 12250)
    ax_band.set_xlabel("Cumulative shortfall over 130 days (transits)")
    ax_band.set_title("(b) Endpoint uncertainty depends on the reference construction", loc="left", fontsize=9.3)
    style_axes(ax_band, grid_axis="x")

    fig.text(
        0.01,
        0.002,
        "The locked seven-block partition supports a finite 80% band only; its 90% and 95% block-conformal bands are unbounded.\n"
        "The eight-block packing is a declared partition sensitivity. Descriptive bands are shown for scale, not as confidence intervals.",
        fontsize=6.4,
        color=NEUTRAL_MID,
        ha="left",
        va="bottom",
    )
    return _save(fig, FIG_CUMULATIVE)


def figure_adaptation_synthesis() -> Path:
    mechanism = _processed("mechanism_evidence_summary.csv")
    route = _processed("inferred_capacity_nautical_miles_comparison.csv")
    route = route[route["terminal_match_radius_km"].eq(30)].iloc[0]
    vessel = _processed("vessel_day_comparison.csv")
    vessel = vessel[
        vessel["terminal_match_radius_km"].eq(30)
        & vessel["route_specification"].eq("expanded_60nm_snap")
        & vessel["speed_knots"].eq(15.0)
    ].iloc[0]
    wto_validation = _json(PROC / "gulf_departure_wto_validation_summary.json")
    corridor = _csv(NETWORK / "network_adaptation_inference.csv")
    corridor = corridor[
        corridor["family"].eq("restricted_tanker_adaptation")
        & corridor["model"].eq("chronos2_univariate")
        & corridor["block_length_days"].eq(14)
    ].copy()
    portfolios = _processed("lng_resilience_typology.csv")

    wto = float(
        mechanism.loc[
            mechanism["measure"].eq("WTO_Hormuz_LNG_outbound_index_mean"),
            "percent_change",
        ].iloc[0]
    )
    gfw_calls = float(
        mechanism.loc[
            mechanism["measure"].eq("inside_Hormuz_Gulf_departure_calls"),
            "percent_change",
        ].iloc[0]
    )
    gfw_capacity = float(
        wto_validation["pre_post_changes"]["gfw_nominal_capacity_percent_change"]
    )

    apply_publication_style()
    fig, axes = plt.subplots(2, 2, figsize=(THESIS_TEXTWIDTH_IN, 6.45))
    fig.subplots_adjust(left=0.115, right=0.98, top=0.965, bottom=0.235, wspace=0.48, hspace=0.62)
    ax_a, ax_b, ax_c, ax_d = axes.flat

    a_values = [wto, gfw_calls, gfw_capacity]
    a_labels = ["WTO LNG\noutbound index", "GFW Gulf\ndeparture calls", "GFW nominal\ncapacity"]
    bars = ax_a.bar(
        np.arange(3),
        a_values,
        color=[SECONDARY_BLUE, ACCENT_ORANGE, ACCENT_ORANGE],
        width=0.72,
    )
    ax_a.axhline(0, color=NEUTRAL_DARK, linewidth=0.75)
    ax_a.set_xticks(np.arange(3), a_labels, fontsize=6.8)
    ax_a.set_ylabel("Pre/post change (%)")
    ax_a.set_ylim(-112, 5)
    ax_a.set_title("(a) LNG-specific contraction", loc="left", fontsize=9.1)
    _bar_labels(ax_a, bars, a_values, fontsize=6.8)
    style_axes(ax_a, grid_axis="y")

    b_values = [
        float(route["expanded_routed_voyage_percent_change"]),
        float(route["expanded_percent_change"]),
        float(route["expanded_mean_per_voyage_percent_change"]),
        float(vessel["mean_modeled_sailing_days_per_voyage_percent_change"]),
    ]
    b_labels = [
        "Routed voyages",
        "Total nominal\ncapacity-distance",
        "Mean nominal capacity-\ndistance / voyage",
        "Mean modeled sailing\ndays / voyage",
    ]
    yb = np.arange(4)
    bars_b = ax_b.barh(
        yb,
        b_values,
        color=[ACCENT_ORANGE, ACCENT_ORANGE, ACCENT_BLUE, ACCENT_BLUE],
        height=0.62,
    )
    ax_b.axvline(0, color=NEUTRAL_DARK, linewidth=0.8)
    ax_b.set_yticks(yb, b_labels, fontsize=6.6)
    ax_b.invert_yaxis()
    ax_b.set_xlim(-31, 18)
    ax_b.set_xlabel("Pre/post change (%)")
    ax_b.set_title("(b) Retained network support", loc="left", fontsize=9.1)
    _bar_labels(ax_b, bars_b, b_values, fontsize=6.7, horizontal=True)
    style_axes(ax_b, grid_axis="x")

    order = ["Malacca Strait", "Gibraltar Strait", "Cape of Good Hope", "Panama Canal", "Yucatan Channel"]
    corridor = corridor.set_index("portname").loc[order]
    c_values = corridor["event_statistic"].astype(float).tolist()
    c_colours = [NEUTRAL_MID, NEUTRAL_MID, NEUTRAL_LIGHT, COUNTERFACTUAL, COUNTERFACTUAL]
    yc = np.arange(len(order))
    bars_c = ax_c.barh(yc, c_values, color=c_colours, height=0.58)
    ax_c.axvline(0, color=NEUTRAL_DARK, linewidth=0.8)
    ax_c.set_yticks(yc, [name.replace(" Strait", "\nStrait") for name in order], fontsize=6.6)
    ax_c.set_xlim(-0.24, 0.53)
    ax_c.set_xlabel("Mean deviation / pre-event mean")
    ax_c.set_title("(c) Corridor screen (retrospective)", loc="left", fontsize=9.1)
    _bar_labels(ax_c, bars_c, c_values, fmt="{:+.2f}", fontsize=6.6, horizontal=True)
    for name in ("Panama Canal", "Yucatan Channel"):
        row_y = order.index(name)
        ax_c.text(-0.225, row_y, "all cells", va="center", ha="left", fontsize=5.8, color=COUNTERFACTUAL)
    style_axes(ax_c, grid_axis="x")

    colours = {
        "high_exposure_constrained": ACCENT_ORANGE,
        "high_exposure_high_offset": ACCENT_BLUE,
        "low_exposure_stable": NEUTRAL_MID,
        "aggregate_comparator": NEUTRAL_LIGHT,
    }
    offsets = {
        "China": (4, -10, "left"),
        "Korea": (4, 5, "left"),
        "Taiwan": (4, 5, "left"),
        "India": (4, -10, "left"),
        "Japan": (-4, 5, "right"),
        "EU27": (-4, -11, "right"),
    }
    for row in portfolios.itertuples():
        colour = colours[row.primary_typology]
        marker = "s" if row.destination_unit == "India" else ("D" if row.destination_unit == "EU27" else "o")
        hollow = row.destination_unit == "EU27"
        ax_d.scatter(
            float(row.gulf_share_change_pp),
            float(row.seasonality_adjusted_edge_total_pct_change),
            s=42,
            marker=marker,
            facecolor="white" if hollow else colour,
            edgecolor=colour if not hollow else NEUTRAL_MID,
            linewidth=1.1,
            zorder=4,
        )
        dx, dy, ha = offsets[row.destination_unit]
        ax_d.annotate(
            row.destination_unit,
            xy=(float(row.gulf_share_change_pp), float(row.seasonality_adjusted_edge_total_pct_change)),
            xytext=(dx, dy),
            textcoords="offset points",
            ha=ha,
            va="center",
            fontsize=6.7,
        )
    ax_d.axhline(0, color=NEUTRAL_DARK, linewidth=0.8)
    ax_d.axvline(0, color=NEUTRAL_DARK, linewidth=0.8)
    ax_d.set_xlim(-58, 2)
    ax_d.set_ylim(-17, 9)
    ax_d.set_xlabel("Gulf-share change (percentage points)")
    ax_d.set_ylabel("Total change vs same months 2025 (%)")
    ax_d.set_title("(d) Importer-origin portfolios", loc="left", fontsize=9.1)
    style_axes(ax_d, grid_axis="both")

    fig.text(
        0.01,
        0.005,
        "Panels use non-equivalent units and are not pooled. WTO is an indexed LNG measure; GFW departures and routed voyages are inferred;\n"
        "capacity-distance uses nominal capacity and modeled routes. Cape is context because its historical reference crosses a prior regime change.\n"
        "Importer movements are within-unit: China, Japan, Korea and Taiwan use mass; India (square) uses customs value; EU27 (diamond) is a volume aggregate.",
        fontsize=6.2,
        color=NEUTRAL_MID,
        ha="left",
        va="bottom",
    )
    return _save(fig, FIG_ADAPTATION)


def figure_robustness_synthesis() -> Path:
    placebo = _processed("placebo_time_effects.csv")
    placebo = placebo[
        placebo["model"].eq("ar_lag1_7")
        & placebo["target"].eq(TARGET)
    ]
    actual_time = float(placebo.loc[placebo["is_actual"].astype(bool), "cumulative_throughput_loss"].iloc[0])
    placebo_values = placebo.loc[
        ~placebo["is_actual"].astype(bool), "cumulative_throughput_loss"
    ].dropna()
    placebo_summary = _processed("placebo_time_summary.csv")
    placebo_summary = placebo_summary[
        placebo_summary["model"].eq("ar_lag1_7")
        & placebo_summary["target"].eq(TARGET)
    ].iloc[0]

    spatial = _processed("spatial_placebo_effects.csv")
    spatial = spatial[spatial["value_col"].eq("n_tanker")].dropna(
        subset=["normalized_throughput_loss"]
    )
    spatial = spatial.sort_values("normalized_throughput_loss", ascending=False).reset_index(drop=True)
    spatial["rank"] = np.arange(1, len(spatial) + 1)

    synth = _processed("synthetic_control_summary.csv")
    synth = synth[synth["value_col"].eq("n_tanker")].copy()
    synth_actual = synth[synth["is_actual"].astype(bool)].iloc[0]
    synth_placebos = synth[~synth["is_actual"].astype(bool)].copy()
    synth_placebos["eligible"] = (
        synth_placebos["eligible_primary_prefit_screen"].astype(str).str.lower().eq("true")
    )

    positive = _csv(POSITIVE / "redsea_positive_control_inference.csv")
    positive = positive[
        positive["family"].eq("eligible_receiver_family")
        & positive["portname"].eq("Cape of Good Hope")
        & positive["vessel_class"].eq("n_tanker")
        & positive["block_length_days"].eq(14)
    ].copy()
    positive["cell"] = positive.apply(
        lambda row: ("External" if row["onset"] == "external_onset" else "Register")
        + "\n"
        + ("AR" if row["model"] == "ar_lag1_7" else "Chronos-2"),
        axis=1,
    )
    positive["order"] = positive["cell"].map(
        {"External\nAR": 0, "External\nChronos-2": 1, "Register\nAR": 2, "Register\nChronos-2": 3}
    )
    positive = positive.sort_values("order")

    apply_publication_style()
    fig, axes = plt.subplots(2, 2, figsize=(THESIS_TEXTWIDTH_IN, 6.25))
    fig.subplots_adjust(left=0.115, right=0.98, top=0.965, bottom=0.225, wspace=0.43, hspace=0.58)
    ax_a, ax_b, ax_c, ax_d = axes.flat

    counts, _, _ = ax_a.hist(
        placebo_values,
        bins=12,
        color=ACCENT_LIGHT_BLUE,
        edgecolor="white",
        linewidth=0.6,
    )
    p95 = float(placebo_summary["placebo_loss_p95"])
    ax_a.axvline(p95, color=NEUTRAL_DARK, linewidth=1.0, linestyle="--")
    ax_a.axvline(actual_time, color=OBSERVED_TREATED, linewidth=1.8)
    ymax = max(float(np.max(counts)), 1.0)
    ax_a.annotate(f"p95 {p95:,.0f}", xy=(p95, ymax * 0.78), xytext=(-3, 0),
                  textcoords="offset points", ha="right", fontsize=6.8)
    ax_a.annotate(f"actual {actual_time:,.0f}", xy=(actual_time, ymax * 0.55), xytext=(-3, 0),
                  textcoords="offset points", ha="right", fontsize=6.8, color=OBSERVED_TREATED)
    ax_a.set_xlabel("130-day cumulative shortfall")
    ax_a.set_ylabel("Overlapping placebo windows")
    ax_a.set_title("(a) Temporal placebo reference", loc="left", fontsize=9.1)
    style_axes(ax_a, grid_axis="y")

    donor = spatial[~spatial["is_treated"].astype(bool)]
    treated = spatial[spatial["is_treated"].astype(bool)]
    ax_b.scatter(donor["rank"], donor["normalized_throughput_loss"], s=18,
                 color=NEUTRAL_MID, alpha=0.75)
    ax_b.scatter(treated["rank"], treated["normalized_throughput_loss"], s=38,
                 color=OBSERVED_TREATED, zorder=4)
    top_donor = donor.iloc[0]
    treated_row = treated.iloc[0]
    ax_b.annotate(
        f"Hormuz {treated_row.normalized_throughput_loss:.2f}",
        xy=(treated_row["rank"], treated_row["normalized_throughput_loss"]),
        xytext=(5, -2), textcoords="offset points", fontsize=6.8,
        color=OBSERVED_TREATED, va="center",
    )
    ax_b.annotate(
        f"largest donor: {top_donor.portname} {top_donor.normalized_throughput_loss:.2f}",
        xy=(top_donor["rank"], top_donor["normalized_throughput_loss"]),
        xytext=(5, 5), textcoords="offset points", fontsize=6.3,
        color=NEUTRAL_DARK,
    )
    ax_b.axhline(0, color=NEUTRAL_DARK, linewidth=0.7)
    ax_b.set_xlabel("Rank by normalized shortfall")
    ax_b.set_ylabel("Shortfall / counterfactual sum")
    ax_b.set_title("(b) Same-date spatial placebos", loc="left", fontsize=9.1)
    style_axes(ax_b, grid_axis="y")

    eligible = synth_placebos[synth_placebos["eligible"]]
    excluded = synth_placebos[~synth_placebos["eligible"]]
    ax_c.scatter(excluded["post_pre_rmspe_ratio"], np.full(len(excluded), 0),
                 s=22, facecolor="white", edgecolor=NEUTRAL_MID, linewidth=0.8)
    ax_c.scatter(eligible["post_pre_rmspe_ratio"], np.full(len(eligible), 1),
                 s=24, color=COUNTERFACTUAL)
    ax_c.scatter(float(synth_actual["post_pre_rmspe_ratio"]), 2, s=40,
                 color=OBSERVED_TREATED, zorder=4)
    synth_p95 = float(synth_actual["placebo_ratio_p95"])
    ax_c.axvline(synth_p95, color=NEUTRAL_DARK, linewidth=1.0, linestyle="--")
    ax_c.annotate(f"eligible p95 {synth_p95:.2f}", xy=(synth_p95, 1.55),
                  xytext=(-3, 0), textcoords="offset points", ha="right", fontsize=6.5)
    ax_c.annotate(f"Hormuz {float(synth_actual.post_pre_rmspe_ratio):.2f}",
                  xy=(float(synth_actual.post_pre_rmspe_ratio), 2), xytext=(-4, 5),
                  textcoords="offset points", ha="right", fontsize=6.8, color=OBSERVED_TREATED)
    ax_c.set_yticks([0, 1, 2], ["Screened out", "Eligible placebo", "Hormuz"], fontsize=6.7)
    ax_c.set_ylim(-0.45, 2.45)
    ax_c.set_xlabel("Post/pre RMSPE ratio")
    ax_c.set_title("(c) Synthetic-control corroboration", loc="left", fontsize=9.1)
    style_axes(ax_c, grid_axis="x")

    xd = np.arange(len(positive))
    bars = ax_d.bar(xd, positive["event_statistic"], width=0.66,
                    color=[NEUTRAL_DARK, COUNTERFACTUAL, NEUTRAL_DARK, COUNTERFACTUAL])
    ax_d.set_xticks(xd, positive["cell"], fontsize=6.5)
    ax_d.set_ylim(0, 1.02)
    ax_d.set_ylabel("Scaled mean deviation")
    ax_d.set_title("(d) Red Sea positive control", loc="left", fontsize=9.1)
    _bar_labels(ax_d, bars, positive["event_statistic"].astype(float).tolist(), fmt="{:.2f}", fontsize=6.7)
    ax_d.text(0.02, 0.97, "Cape ranks 1/16 in all cells; RW p = 0.0001",
              transform=ax_d.transAxes, ha="left", va="top", fontsize=6.2,
              color=NEUTRAL_DARK)
    style_axes(ax_d, grid_axis="y")
    fig.text(
        0.01,
        0.005,
        "Temporal windows overlap and therefore provide a descriptive reference rank; the locked disjoint-block rank is p = 0.125.\n"
        "Spatial normalization uses each corridor's own counterfactual sum. Synthetic-control inference uses the post/pre RMSPE ratio after the 2x pre-fit screen.\n"
        "The Red Sea receiver was designated before inspection; it validates the machinery, not the retrospective selection of Hormuz-era corridors.",
        fontsize=6.2,
        color=NEUTRAL_MID,
        ha="left",
        va="bottom",
    )
    return _save(fig, FIG_ROBUSTNESS)


def main() -> None:
    figure_cumulative_shortfall_uncertainty()
    figure_adaptation_synthesis()
    figure_robustness_synthesis()


if __name__ == "__main__":
    main()
