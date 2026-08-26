"""Supplementary manuscript figures added after the 2026-08-14 interim review.

Three defects motivated these figures.

1.  The estimator ladder existed only as two tables. A reader could not see that
    the admitted specifications agree closely on the point estimate while the
    reported bands disagree by an order of magnitude, nor that the data-vintage
    gap is larger than the gap between admitted estimators.
2.  The synthetic-control placebo figure plotted gap *levels*, but the reported
    inference is a post/pre RMSPE *ratio*. In levels the treated path sits
    inside the placebo cloud, so the figure argued against its own statistic.
3.  The importer-divergence result, which the manuscript calls its most
    interesting descriptive finding, had no figure at all.

Every value is read from data/processed at run time. Nothing is hard-coded.
Output is deterministic: fixed ordering, no timestamps, stable filenames.
"""
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
from matplotlib.lines import Line2D  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from figure_style import (  # noqa: E402
    PDF_METADATA,
    PNG_METADATA,
    ACCENT_BLUE,
    ACCENT_ORANGE,
    COUNTERFACTUAL,
    THESIS_TEXTWIDTH_IN,
    NEUTRAL_DARK,
    NEUTRAL_LIGHT,
    NEUTRAL_MID,
    OBSERVED_TREATED,
    SECONDARY_BLUE,
    apply_publication_style,
    style_axes,
)
from lngfreight import config  # noqa: E402

TARGET = "hormuz_tanker_transits"
PROC = config.ROOT / "data" / "processed"

FIG_ESTIMATORS = "thesis_estimator_interval_agreement"
FIG_SC_RATIOS = "thesis_synthetic_control_placebo_ratios"
FIG_DIVERGENCE = "thesis_importer_divergence"

# Role labels as recorded in the admission artifact, mapped to display strings.
ROLE_LABELS = {
    "working_primary": "working primary",
    "conditional_sensitivity": "conditional sensitivity",
    "corroboration": "corroboration",
    "state_space_corroboration": "state-space corroboration",
    "benchmark": "benchmark",
    "zero_shot_cross_check": "zero-shot cross-check",
}
ROLE_COLOURS = {
    "working_primary": SECONDARY_BLUE,
    "conditional_sensitivity": ACCENT_ORANGE,
    "corroboration": ACCENT_BLUE,
    "state_space_corroboration": ACCENT_BLUE,
    "benchmark": NEUTRAL_MID,
    "zero_shot_cross_check": NEUTRAL_MID,
}
TYPOLOGY_COLOURS = {
    "high_exposure_high_offset": ACCENT_BLUE,
    "high_exposure_constrained": ACCENT_ORANGE,
    "low_exposure_stable": NEUTRAL_MID,
    "aggregate_comparator": NEUTRAL_LIGHT,
}


def _read(name: str) -> pd.DataFrame:
    path = PROC / name
    if not path.exists():
        raise FileNotFoundError(f"Missing upstream artifact: {path}")
    return pd.read_csv(path)


def _tight_width_pt(fig: plt.Figure) -> float:
    """Width in PDF points that this figure would occupy with a tight bbox."""
    renderer = fig.canvas.get_renderer()
    bbox = fig.get_tightbbox(renderer)
    return float(bbox.width) * 72.0


def _fit_to_textwidth(fig: plt.Figure) -> None:
    """Rescale until the tight bounding box equals the manuscript text width.

    A figure authored at the text width is written wider than it, because the
    tight box grows to fit tick labels, legends and footnotes, and
    \\includegraphics then scales it back down so its text prints smaller than
    designed. savefig also adds savefig.pad_inches on every side, so the target
    is the padded width rather than the raw one.

    The tight width is driven largely by text at a fixed point size, which does
    not shrink in proportion with the figure, so the iteration is damped, floored
    and stopped as soon as it stops closing the gap. Without those guards a
    text-heavy figure is shrunk until its axes collapse. Deterministic, so output
    stays reproducible.
    """
    pad_in = float(plt.rcParams.get("savefig.pad_inches", 0.1))
    target_pt = (THESIS_TEXTWIDTH_IN - 2.0 * pad_in) * 72.0
    floor_in = 0.80 * float(fig.get_size_inches()[0])
    previous_gap = float("inf")
    for _ in range(24):
        current = _tight_width_pt(fig)
        gap = abs(current - target_pt)
        if gap <= 0.5 or gap >= previous_gap:
            return
        width_in, height_in = fig.get_size_inches()
        scale = min(max(target_pt / current, 0.92), 1.08)
        if width_in * scale < floor_in:
            return
        previous_gap = gap
        fig.set_size_inches(width_in * scale, height_in * scale)


def _save(fig: plt.Figure, stem: str) -> Path:
    _fit_to_textwidth(fig)
    figures = config.path("figures")
    figures.mkdir(parents=True, exist_ok=True)
    pdf = figures / f"{stem}.pdf"
    png = figures / f"{stem}.png"
    fig.savefig(pdf, bbox_inches="tight", metadata=PDF_METADATA)
    fig.savefig(png, dpi=300, bbox_inches="tight", metadata=PNG_METADATA)
    plt.close(fig)
    print(f"wrote {pdf.name}")
    return pdf


_LOWERCASE_PARTICLES = {"of", "the", "and"}


def _pretty_unit(slug: object) -> str:
    """Slug to display name, keeping English particles lowercase.

    'strait_of_hormuz' becomes 'Strait of Hormuz', not 'Strait of hormuz'.
    """
    words = str(slug).replace("_", " ").split()
    out = []
    for i, word in enumerate(words):
        if i and word.lower() in _LOWERCASE_PARTICLES:
            out.append(word.lower())
        else:
            out.append(word[:1].upper() + word[1:])
    return " ".join(out)


# --------------------------------------------------------------------- fig 1
def fig_estimator_interval_agreement() -> Path:
    """Point estimates agree; reported bands do not; the vintage gap beats both.

    The interim-report version of this figure showed five estimators and
    reported their spread as roughly ten per cent of the primary. That omitted
    the route-plus-energy ARX, which the manuscript admits as a conditional
    sensitivity rather than excluding, and omitted the synthetic control. Both
    are shown here, and the two spreads are annotated separately so the smaller
    number is never read as the whole story.
    """
    spec = _read("run_spec_comparison.csv")
    spec = spec[spec["outcome"] == TARGET].copy()

    lh = _read("long_horizon_intervals_summary.csv")
    lh = lh[lh["target"] == TARGET].set_index("model")
    tsfm = _read("tsfm_counterfactual_summary.csv")
    tsfm = tsfm[(tsfm["target"] == TARGET) & (tsfm["model"] == "chronos2")].iloc[0]
    vintage = _read("portwatch_vintage_sensitivity.csv")
    vintage = vintage[vintage["target"] == TARGET].set_index("scenario")
    frontier = _read("horizon_frontier_summary.csv")
    frontier = frontier[
        (frontier["outcome"] == TARGET)
        & (frontier["horizon_days"] == 130)
        & (frontier["origin_rule"] == "forward_anchored_direct")
        & (frontier["role"] == "primary")
    ].set_index("level")

    primary = float(spec.loc[spec["role"] == "working_primary", "point_shortfall"].iloc[0])

    # Points: everything in the admission artifact, plus the two specifications
    # that live in their own artifacts.
    points = [
        (str(r.specification), str(r.role), float(r.point_shortfall))
        for r in spec.itertuples()
    ]
    points.append((
        "seasonal_naive_7d",
        "benchmark",
        float(lh.loc["seasonal_naive_7d", "point_cumulative_throughput_loss"]),
    ))
    points.append((
        "chronos2",
        "zero_shot_cross_check",
        float(tsfm.cumulative_throughput_loss),
    ))
    points.sort(key=lambda row: row[2])

    admitted = [p for p in points if p[1] != "conditional_sensitivity"]
    spread_admitted = max(p[2] for p in admitted) - min(p[2] for p in admitted)
    spread_all = max(p[2] for p in points) - min(p[2] for p in points)

    vintage_primary = float(vintage.loc["pinned_primary", "cumulative_throughput_loss"])
    vintage_alt = float(vintage.loc["vintage_same_window", "cumulative_throughput_loss"])
    vintage_gap = abs(vintage_primary - vintage_alt)

    # Intervals, each carrying its own construction and nominal coverage.
    ar_row = lh.loc["ar_lag1_7"]
    intervals = [
        ("Residual-calibrated\n30-day folds", ar_row["interval_30dfold_lower"],
         ar_row["interval_30dfold_upper"], "no nominal coverage", False),
        ("Circular block bootstrap\n14-day blocks", ar_row["interval_circular_bootstrap_lower"],
         ar_row["interval_circular_bootstrap_upper"], "no nominal coverage", False),
        ("Overlapping placebo\nquantile band", ar_row["overlapping_placebo_quantile_band_lower"],
         ar_row["overlapping_placebo_quantile_band_upper"], "no nominal coverage", False),
        ("Block conformal\n8 blocks, nominal 80%", frontier.loc[0.80, "interval_lower"],
         frontier.loc[0.80, "interval_upper"], "nominal 80%", False),
        ("Block conformal\n8 blocks, nominal 90/95%", np.nan, np.nan, "nominal 90% and 95%", True),
        ("BSTS posterior predictive\nnominal 95%",
         float(spec.loc[spec["role"] == "state_space_corroboration", "reported_band_lower"].iloc[0]),
         float(spec.loc[spec["role"] == "state_space_corroboration", "reported_band_upper"].iloc[0]),
         "nominal 95%, conditional on model", False),
    ]

    apply_publication_style()
    fig, (axl, axr) = plt.subplots(
        2, 1, figsize=(THESIS_TEXTWIDTH_IN, 5.85),
        gridspec_kw={"height_ratios": [1.0, 1.05], "hspace": 0.42},
    )

    # ---- panel (a)
    ys = np.arange(len(points))[::-1]
    for y, (name, role, value) in zip(ys, points):
        colour = ROLE_COLOURS.get(role, NEUTRAL_MID)
        marker = "D" if role == "conditional_sensitivity" else "o"
        axl.plot(value, y, marker, color=colour, ms=6.5, zorder=3)
        axl.annotate(f"{value:,.0f}", (value, y), textcoords="offset points",
                     xytext=(9, 0), ha="left", va="center", fontsize=7.4, color=colour)
    axl.set_yticks(ys)
    axl.set_yticklabels([name for name, _, _ in points], fontsize=7.4)
    axl.axvline(primary, color=NEUTRAL_MID, lw=0.9, ls="--", zorder=1)

    # The data-vintage comparison sits on the same axis as a separate row, so the
    # reader can see it is wider than the disagreement between estimators.
    y_vint = -1.35
    axl.plot([vintage_alt, vintage_primary], [y_vint, y_vint], color=OBSERVED_TREATED,
             lw=2.2, solid_capstyle="butt", zorder=3)
    for value in (vintage_alt, vintage_primary):
        axl.plot([value], [y_vint], "|", color=OBSERVED_TREATED, ms=9, mew=1.6, zorder=4)
    axl.annotate(
        f"data vintage: {vintage_gap:,.0f}",
        xy=((vintage_alt + vintage_primary) / 2, y_vint - 0.55),
        ha="center", va="center", fontsize=7.4, color=OBSERVED_TREATED,
    )
    # Reserve an empty strip above the top row for the spread annotation.
    # At the previous limit the annotation was drawn straight through the
    # topmost marker and its value label.
    axl.set_ylim(-2.2, len(points) + 1.45)
    # The right-most value label ran into the axes frame; widen the view a
    # little so every annotation stays inside the panel.
    x_lo, x_hi = axl.get_xlim()
    axl.set_xlim(x_lo, x_hi + 0.07 * (x_hi - x_lo))
    axl.set_xlabel("Cumulative shortfall over 130 days (transits)")
    axl.set_title("(a) Specifications and one data vintage", loc="left")
    axl.grid(axis="x", alpha=0.25, lw=0.6)
    axl.annotate(
        f"spread excluding conditional sensitivities: {spread_admitted:,.0f}"
        f" ({spread_admitted / primary:.1%})\n"
        f"spread including them: {spread_all:,.0f} ({spread_all / primary:.1%})",
        xy=(0.02, 0.97), xycoords="axes fraction", fontsize=6.9, color=NEUTRAL_MID,
        va="top", ha="left",
    )

    # ---- panel (b)
    ysi = np.arange(len(intervals))[::-1]
    for y, (label, lo, hi, coverage, unbounded) in zip(ysi, intervals):
        nominal = not coverage.startswith("no nominal")
        colour = COUNTERFACTUAL if nominal else NEUTRAL_DARK
        if unbounded:
            axr.annotate("", xy=(600, y), xytext=(12600, y),
                         arrowprops=dict(arrowstyle="<->", color=colour, lw=1.3, ls=":"))
            axr.text(6600, y + 0.26, "unbounded", ha="center", fontsize=7.2,
                     color=colour, style="italic")
            continue
        axr.plot([lo, hi], [y, y], color=colour, lw=2.4, solid_capstyle="butt", zorder=3)
        for edge in (lo, hi):
            axr.plot([edge, edge], [y - 0.15, y + 0.15], color=colour, lw=1.3, zorder=3)
        axr.text(hi + 220, y, f"width {hi - lo:,.0f}", va="center", fontsize=7.0, color=colour)

    axr.axvline(primary, color=NEUTRAL_MID, lw=0.9, ls="--", zorder=1)
    axr.axvline(0, color="black", lw=0.8, zorder=1)
    axr.set_yticks(ysi)
    axr.set_yticklabels([label for label, _, _, _, _ in intervals], fontsize=7.2)
    axr.set_xlim(-700, 14600)
    axr.set_ylim(-0.95, len(intervals) - 0.30)
    axr.set_xlabel("Cumulative shortfall over 130 days (transits)")
    axr.set_title("(b) Six reported bands around the same point", loc="left")
    axr.grid(axis="x", alpha=0.25, lw=0.6)

    # Bracket panel (a)'s range onto panel (b)'s axis. Without it the two panels
    # sit side by side on incompatible scales and invite a false comparison.
    lo_pts = min(p[2] for p in points)
    hi_pts = max(p[2] for p in points)
    y_bracket = -0.62
    axr.plot([lo_pts, hi_pts], [y_bracket, y_bracket], color=ACCENT_ORANGE, lw=2.0,
             solid_capstyle="butt", zorder=4)
    for edge in (lo_pts, hi_pts):
        axr.plot([edge, edge], [y_bracket - 0.11, y_bracket + 0.11],
                 color=ACCENT_ORANGE, lw=1.3, zorder=4)
    axr.annotate(f"panel (a) spans {hi_pts - lo_pts:,.0f}", xy=(hi_pts + 300, y_bracket),
                 ha="left", va="center", fontsize=7.0, color=ACCENT_ORANGE)

    fig.legend(
        handles=[
            Line2D([0], [0], color=COUNTERFACTUAL, lw=2.4, label="nominal coverage stated"),
            Line2D([0], [0], color=NEUTRAL_DARK, lw=2.4, label="no nominal coverage claimed"),
            Line2D([0], [0], color=ACCENT_ORANGE, lw=2.0, label="span of panel (a)"),
        ] + [
            Line2D([0], [0], marker="D" if role == "conditional_sensitivity" else "o",
                   color="none", markerfacecolor=colour, markeredgecolor=colour,
                   ms=6, label=ROLE_LABELS[role])
            for role, colour in (
                ("working_primary", SECONDARY_BLUE),
                ("conditional_sensitivity", ACCENT_ORANGE),
                ("corroboration", ACCENT_BLUE),
                ("benchmark", NEUTRAL_MID),
            )
        ],
        loc="lower center", bbox_to_anchor=(0.5, -0.125), ncol=3, fontsize=7.2,
        frameon=False,
    )
    return _save(fig, FIG_ESTIMATORS)


# --------------------------------------------------------------------- fig 2
def fig_synthetic_control_placebo_ratios() -> Path:
    """Plot the statistic the manuscript actually reports for the placebo test.

    The companion path figure shows observed-minus-synthetic gaps in levels,
    where the treated unit is not visibly outside the placebo cloud. Inference
    is drawn from the post/pre RMSPE ratio instead, so that is what is drawn
    here, with the pre-fit screen made visible rather than silent.
    """
    summary = _read("synthetic_control_summary.csv")

    bases = [
        ("n_tanker", "(a) Transit-count basis (primary)"),
        ("capacity_tanker", "(b) Capacity basis"),
    ]

    apply_publication_style()
    fig, axes = plt.subplots(
        1, 2, figsize=(THESIS_TEXTWIDTH_IN, 4.3),
        gridspec_kw={"width_ratios": [1, 1], "wspace": 0.42},
    )

    for ax, (value_col, title) in zip(axes, bases):
        frame = summary[summary["value_col"] == value_col].copy()
        actual = frame[frame["is_actual"].astype(bool)].iloc[0]
        placebos = frame[~frame["is_actual"].astype(bool)].copy()
        placebos["eligible"] = placebos["eligible_primary_prefit_screen"].astype(bool)
        placebos = placebos.sort_values("post_pre_rmspe_ratio", ascending=True)

        rows = [
            (_pretty_unit(r.unit), float(r.post_pre_rmspe_ratio), bool(r.eligible))
            for r in placebos.itertuples()
        ]
        rows.append((_pretty_unit(actual.unit), float(actual.post_pre_rmspe_ratio), True))
        y = np.arange(len(rows))

        for i, (_, ratio, eligible) in enumerate(rows):
            treated = i == len(rows) - 1
            if treated:
                colour, height = OBSERVED_TREATED, 0.74
            elif eligible:
                colour, height = NEUTRAL_MID, 0.62
            else:
                colour, height = NEUTRAL_LIGHT, 0.62
            ax.barh(i, ratio, height=height, color=colour, zorder=3)
        ax.set_yticks(y)
        ax.set_yticklabels(
            [name for name, _, _ in rows],
            fontsize=6.4,
        )
        ax.get_yticklabels()[-1].set_color(OBSERVED_TREATED)
        ax.get_yticklabels()[-1].set_fontweight("bold")

        p95 = float(actual.placebo_ratio_p95)
        ax.axvline(p95, color=NEUTRAL_DARK, lw=1.0, ls="--", zorder=4)
        ax.annotate(
            f"eligible placebo p95 = {p95:,.2f}",
            xy=(p95, len(rows) * 0.42), rotation=90, fontsize=6.8,
            color=NEUTRAL_DARK, ha="right", va="center",
        )
        ax.axvline(1.0, color=NEUTRAL_MID, lw=0.7, zorder=2)

        n_elig = int(actual.n_placebos_eligible)
        n_total = int(actual.n_placebos_total)
        p_value = float(actual.p_ratio_ge_actual)
        floor = float(actual.p_value_floor)
        ax.set_title(title, loc="left", fontsize=9.0)
        ax.set_xlabel("Post/pre RMSPE ratio")
        ax.annotate(
            f"treated ratio {float(actual.post_pre_rmspe_ratio):,.2f}\n"
            f"rank p = {p_value:.3f} (floor 1/{int(round(1 / floor))})\n"
            f"{n_elig} of {n_total} donors pass the pre-fit screen",
            xy=(0.97, 0.015), xycoords="axes fraction", ha="right", va="bottom",
            fontsize=7.0, color=NEUTRAL_DARK,
            bbox=dict(boxstyle="round,pad=0.28", facecolor="white",
                      edgecolor="none", alpha=0.88),
        )
        style_axes(ax, grid_axis="x")

    fig.legend(
        handles=[
            Line2D([0], [0], color=OBSERVED_TREATED, lw=6, label="Strait of Hormuz (treated)"),
            Line2D([0], [0], color=NEUTRAL_MID, lw=6, label="placebo donor, passes pre-fit screen"),
            Line2D([0], [0], color=NEUTRAL_LIGHT, lw=6, label="placebo donor, screened out"),
        ],
        loc="lower center", bbox_to_anchor=(0.5, -0.07), ncol=3, frameon=False,
        fontsize=7.2,
    )
    fig.text(
        0.005, -0.155,
        "Rank p is computed over screened-in donors only; screened-out donors\n"
        "are drawn so the screen is visible rather than silent. Rank p cannot\n"
        "fall below its floor: this is a bounded-resolution test, not a\n"
        "p-value with arbitrary precision.",
        ha="left", fontsize=7.0, color=NEUTRAL_MID,
    )
    fig.tight_layout()
    return _save(fig, FIG_SC_RATIOS)


# --------------------------------------------------------------------- fig 3
def fig_importer_divergence() -> Path:
    """Similar pre-shock exposure, opposite outcome.

    The manuscript states this as its most interesting descriptive finding but
    evidenced it only through a table and a grouped bar chart, neither of which
    shows the relationship between exposure and outcome.
    """
    typology = _read("lng_resilience_typology.csv").copy()
    rewiring = _read("lng_rewiring_summary.csv")[
        ["destination_unit", "same_calendar_edge_total_pct_change"]
    ]
    frame = typology.merge(rewiring, on="destination_unit", how="left")
    frame = frame.sort_values(
        ["destination_unit_type", "destination_unit"],
        key=lambda s: s.map(lambda v: (v != "importer", v)) if s.name == "destination_unit_type" else s,
    )

    apply_publication_style()
    fig, (axl, axr) = plt.subplots(
        1, 2, figsize=(THESIS_TEXTWIDTH_IN, 3.7), gridspec_kw={"wspace": 0.42}
    )

    for row in frame.itertuples():
        importer = row.destination_unit_type == "importer"
        colour = TYPOLOGY_COLOURS.get(row.primary_typology, NEUTRAL_MID)
        x = float(row.pre_gulf_share) * 100.0
        y_pre = float(row.edge_total_pct_change)
        y_cal = float(row.same_calendar_edge_total_pct_change)

        axl.plot([x, x], [y_pre, y_cal], color=colour, lw=0.9, alpha=0.8, zorder=2)
        axl.plot(x, y_pre, "o", color=colour, ms=8 if importer else 7,
                 markerfacecolor=colour if importer else "white",
                 markeredgecolor=colour, mew=1.4, zorder=4)
        axl.plot(x, y_cal, "s", color=colour, ms=5.5, markerfacecolor="white",
                 markeredgecolor=colour, mew=1.2, zorder=4)
        axl.annotate(
            row.destination_unit,
            xy=(x, max(y_pre, y_cal)), textcoords="offset points", xytext=(0, 8),
            ha="center", fontsize=7.6, color=NEUTRAL_DARK,
        )

        offset = float(row.non_gulf_offset_ratio)
        gulf_change = float(row.gulf_share_change_pp)
        axr.plot(gulf_change, offset, "o", ms=8 if importer else 7,
                 markerfacecolor=colour if importer else "white",
                 markeredgecolor=colour, mew=1.4, zorder=4)
        axr.annotate(
            row.destination_unit,
            xy=(gulf_change, offset), textcoords="offset points", xytext=(0, 8),
            ha="center", fontsize=7.6, color=NEUTRAL_DARK,
        )

    axl.axhline(0, color=NEUTRAL_DARK, lw=0.8, zorder=1)
    axl.set_xlabel("Pre-shock Gulf share of imports (%)")
    axl.set_ylabel("Change in total imports (%)")
    axl.set_title("(a) Exposure does not fix the outcome", loc="left", fontsize=9.0)
    style_axes(axl, grid_axis="both")

    axr.axhline(1.0, color=NEUTRAL_DARK, lw=0.9, ls="--", zorder=1)
    axr.axhline(0.0, color=NEUTRAL_MID, lw=0.8, zorder=1)
    axr.annotate("full offset of lost Gulf volume", xy=(axr.get_xlim()[1], 1.0),
                 xytext=(-4, 4), textcoords="offset points", ha="right",
                 fontsize=6.8, color=NEUTRAL_DARK)
    axr.set_xlabel("Gulf-share change (percentage points)")
    axr.set_ylabel("Non-Gulf offset ratio")
    axr.set_title("(b) Replacement capacity does", loc="left", fontsize=9.0)
    style_axes(axr, grid_axis="both")

    handles = [
        Line2D([0], [0], marker="o", color="none", markerfacecolor=colour,
               markeredgecolor=NEUTRAL_MID, mew=0.8, ms=8,
               label=label.replace("_", " "))
        for label, colour in TYPOLOGY_COLOURS.items()
    ]
    handles += [
        Line2D([0], [0], marker="o", color="none", markerfacecolor=NEUTRAL_DARK,
               markeredgecolor=NEUTRAL_DARK, ms=8, label="vs twelve-month pre mean"),
        Line2D([0], [0], marker="s", color="none", markerfacecolor="white",
               markeredgecolor=NEUTRAL_DARK, ms=6, label="vs same calendar months 2025"),
    ]
    fig.legend(handles=handles, loc="lower center", bbox_to_anchor=(0.5, -0.13),
               ncol=3, frameon=False, fontsize=7.0)
    fig.text(
        0.005, -0.245,
        "Hollow circles mark the EU27 aggregate comparator, which is context\n"
        "rather than a single importer. India is measured on a value basis and\n"
        "the others on a weight basis, so levels are not comparable across\n"
        "units. Panel (a) shows both comparison bases for every unit.",
        ha="left", fontsize=7.0, color=NEUTRAL_MID,
    )
    fig.tight_layout()
    return _save(fig, FIG_DIVERGENCE)


def main() -> None:
    fig_estimator_interval_agreement()
    fig_synthetic_control_placebo_ratios()
    fig_importer_divergence()


if __name__ == "__main__":
    main()
