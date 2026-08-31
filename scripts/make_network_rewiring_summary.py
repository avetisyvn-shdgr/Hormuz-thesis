"""Render network-rewiring figures and a thesis-facing summary report."""
from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/hormuz_throughput-matplotlib")

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

sys.path.insert(0, str(Path(__file__).resolve().parent))
from figure_style import (  # noqa: E402
    ACCENT_BLUE,
    ACCENT_ORANGE,
    THESIS_TEXTWIDTH_IN,
    NEUTRAL_DARK,
    NEUTRAL_LIGHT,
    NEUTRAL_MID,
    apply_publication_style,
    style_axes,
)
from hormuz_throughput import config  # noqa: E402


REPORT = "network_rewiring_summary.md"
FIG_ORIGIN = "network_rewiring_origin_composition"
FIG_TOTAL = "network_rewiring_gulf_vs_total"
FIG_STRUCTURE = "network_rewiring_source_structure"
PDF_METADATA = {
    "Creator": "hormuz_throughput reproducible pipeline",
    "CreationDate": datetime(2026, 2, 28, tzinfo=timezone.utc),
    "ModDate": datetime(2026, 2, 28, tzinfo=timezone.utc),
}


def _read(path_key: str) -> pd.DataFrame:
    path = config.ROOT / config.settings()["paths"][path_key]
    if not path.exists():
        raise FileNotFoundError(f"Missing upstream artifact: {path}")
    return pd.read_csv(path)


def _fmt(value: object, digits: int = 1) -> str:
    if value is None:
        return "NA"
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return str(value)
    if not np.isfinite(numeric):
        return "NA"
    return f"{numeric:,.{digits}f}"


def _fmt_signed(value: object, digits: int = 1) -> str:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return "NA"
    if not np.isfinite(numeric):
        return "NA"
    return f"{numeric:+,.{digits}f}"


def _fit_to_textwidth(fig: plt.Figure) -> None:
    """Rescale until the tight bounding box equals the manuscript text width.

    See make_thesis_figure_supplements._fit_to_textwidth for the reasoning; the
    damping, floor and no-improvement break stop a text-heavy figure from being
    shrunk until its axes collapse.
    """
    pad_in = float(plt.rcParams.get("savefig.pad_inches", 0.1))
    target_pt = (THESIS_TEXTWIDTH_IN - 2.0 * pad_in) * 72.0
    floor_in = 0.80 * float(fig.get_size_inches()[0])
    previous_gap = float("inf")
    for _ in range(24):
        renderer = fig.canvas.get_renderer()
        current = float(fig.get_tightbbox(renderer).width) * 72.0
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
    out = config.path("figures") / f"{stem}.png"
    fig.savefig(out, dpi=180, bbox_inches="tight")
    fig.savefig(out.with_suffix(".pdf"), bbox_inches="tight", metadata=PDF_METADATA)
    plt.close(fig)
    print(f"wrote {out}")
    print(f"wrote {out.with_suffix('.pdf')}")
    return out


def _ordered_units(summary: pd.DataFrame) -> list[str]:
    importer = summary["destination_unit_type"].eq("importer")
    return (
        summary.assign(_sort=np.where(importer, 0, 1))
        .sort_values(["_sort", "destination_unit"])
        ["destination_unit"]
        .tolist()
    )


def _plot_origin_composition(summary: pd.DataFrame) -> Path:
    units = _ordered_units(summary)
    frame = summary.set_index("destination_unit").loc[units]
    x = np.arange(len(frame))
    width = 0.34
    colors = {"gulf": "#B2182B", "non_gulf": "#2166AC"}

    apply_publication_style()
    fig, ax = plt.subplots(figsize=(THESIS_TEXTWIDTH_IN, 4.3))
    pre_gulf = frame["pre_gulf_share_mean"] * 100
    post_gulf = frame["post_gulf_share_mean"] * 100
    pre_non = 100 - pre_gulf
    post_non = 100 - post_gulf

    ax.bar(x - width / 2, pre_gulf, width, color=colors["gulf"], label="Gulf share")
    ax.bar(x - width / 2, pre_non, width, bottom=pre_gulf, color=colors["non_gulf"], label="Non-Gulf share")
    ax.bar(x + width / 2, post_gulf, width, color=colors["gulf"], alpha=0.55)
    ax.bar(x + width / 2, post_non, width, bottom=post_gulf, color=colors["non_gulf"], alpha=0.55)

    for i, (_, row) in enumerate(frame.iterrows()):
        ax.text(i - width / 2, 102, "pre", ha="center", va="bottom", fontsize=7.5, color=NEUTRAL_MID)
        ax.text(i + width / 2, 102, "post", ha="center", va="bottom", fontsize=7.5, color=NEUTRAL_MID)
        if "thin_post_window" in str(row["coverage_note"]):
            ax.text(i, -6, "thin post", ha="center", va="top", fontsize=7.5, color="#7A4E00")
        elif row["measurement_basis"] == "value_kusd":
            ax.text(i, -6, "value basis", ha="center", va="top", fontsize=7.5, color="#7A4E00")

    ax.set_ylabel("Share of observed monthly edge value (%)")
    ax.set_xticks(x, frame.index)
    ax.set_ylim(-15, 110)
    style_axes(ax, grid_axis="y")
    ax.legend(
        frameon=False,
        loc="lower center",
        bbox_to_anchor=(0.5, -0.34),
        ncol=2,
    )
    fig.text(
        0.01,
        0.005,
        "Shares use each source's native measurement basis. India is value-basis; "
        "EU27 is an aggregate comparator.",
        ha="left",
        fontsize=7.0,
        color=NEUTRAL_MID,
    )
    fig.tight_layout(rect=[0, 0.10, 1, 1])
    return _save(fig, FIG_ORIGIN)



def _label_grouped_bars(fig, ax, series, label_fontsize=7.0, base_pad_pts=2.0):
    """Annotate every bar in a grouped bar chart without colliding labels.

    Bars that sit side by side in a group can end at almost the same height, so
    a uniform padding puts neighbouring value labels on top of one another
    (India, Korea, Taiwan and EU27 all collided at 1:1 print scale). A uniform
    stagger is not the answer either: it separates the close pairs but pushes
    already-separated pairs together. Offsets are therefore computed per bar,
    and only where a horizontally adjacent label on the same side of zero would
    otherwise be within one line height.
    """
    fig.canvas.draw()
    y_lo, y_hi = ax.get_ylim()
    axes_height_pts = ax.get_window_extent().height * 72.0 / fig.dpi
    pts_per_unit = axes_height_pts / max(y_hi - y_lo, 1e-9)
    line_height_pts = label_fontsize * 1.70

    n_groups = len(series[0][1])
    for gi in range(n_groups):
        pads = [base_pad_pts] * len(series)
        for a, b in zip(range(len(series) - 1), range(1, len(series))):
            va, vb = series[a][1][gi], series[b][1][gi]
            if (va >= 0) != (vb >= 0):
                continue
            gap_pts = abs(va - vb) * pts_per_unit
            if gap_pts >= line_height_pts:
                continue
            outer = a if abs(va) >= abs(vb) else b
            pads[outer] += line_height_pts - gap_pts
        for (bars, values), pad in zip(series, pads):
            value = values[gi]
            patch = bars[gi]
            ax.annotate(
                _fmt_signed(value),
                xy=(patch.get_x() + patch.get_width() / 2.0, value),
                xytext=(0, pad if value >= 0 else -pad),
                textcoords="offset points",
                ha="center",
                va="bottom" if value >= 0 else "top",
                fontsize=label_fontsize,
            )

    fig.canvas.draw()
    inv = ax.transData.inverted()
    lo, hi = ax.get_ylim()
    for text in ax.texts:
        if not text.get_text().strip():
            continue
        box = text.get_window_extent(renderer=fig.canvas.get_renderer())
        lo = min(lo, inv.transform((0, box.y0))[1])
        hi = max(hi, inv.transform((0, box.y1))[1])
    span = hi - lo
    ax.set_ylim(lo - 0.02 * span, hi + 0.02 * span)

def _plot_gulf_vs_total(summary: pd.DataFrame) -> Path:
    units = _ordered_units(summary)
    frame = summary.set_index("destination_unit").loc[units]
    x = np.arange(len(frame))
    width = 0.26

    apply_publication_style()
    fig, ax = plt.subplots(figsize=(THESIS_TEXTWIDTH_IN, 4.3))
    total = frame["edge_total_pct_change"]
    total_same = frame["same_calendar_edge_total_pct_change"]
    gulf = frame["gulf_share_change_pp"]
    bars_total = ax.bar(
        x - width,
        total,
        width,
        label="Total change vs 12m pre (%)",
        color="#365F91",
    )
    bars_same = ax.bar(
        x,
        total_same,
        width,
        label="Total change vs same months 2025 (%)",
        color="#5B8E7D",
    )
    bars_gulf = ax.bar(
        x + width,
        gulf,
        width,
        label="Gulf-share change (pp)",
        color="#B44C43",
    )
    ax.axhline(0, color="#333333", linewidth=0.8)
    ax.set_ylabel("Change from comparison window\nto available post window")
    ax.set_xticks(x, frame.index)
    style_axes(ax, grid_axis="y")
    ax.legend(
        frameon=False,
        loc="lower center",
        bbox_to_anchor=(0.5, -0.38),
        ncol=2,
        fontsize=8.0,
    )
    fig.text(
        0.01,
        0.005,
        "Same-calendar totals compare available 2026 post months with the same "
        "months in 2025 to reduce seasonality confounding.",
        ha="left",
        fontsize=7.0,
        color=NEUTRAL_MID,
    )
    fig.tight_layout(rect=[0, 0.11, 1, 1])
    _label_grouped_bars(
        fig,
        ax,
        [(bars_total, list(total)), (bars_same, list(total_same)), (bars_gulf, list(gulf))],
        label_fontsize=7.0,
    )
    return _save(fig, FIG_TOTAL)


def _plot_source_structure(summary: pd.DataFrame, graph: pd.DataFrame, anomaly: pd.DataFrame) -> Path:
    """Vertically stacked small multiples, one full-width panel per quantity.

    The earlier version shared a left axis between the HHI change (order 0.01)
    and the Jensen-Shannon distance (order 0.1), which rendered the HHI bars
    invisible, and carried the anomaly z-score on a twin right axis where
    neighbouring bars invited a ratio reading the statistic does not support.
    Each quantity now owns its own scale and the unit ordering is repeated in
    three full-width rows.  This avoids compressing six category labels and
    three different axes into narrow side-by-side columns.
    """
    units = _ordered_units(summary)
    merged = (
        summary.merge(
            graph[["destination_unit", "edge_turnover_rate", "jensen_shannon_distance"]],
            on="destination_unit",
            how="left",
        )
        .merge(
            anomaly[["destination_unit", "post_max_zscore", "anomaly_flag"]],
            on="destination_unit",
            how="left",
        )
        .set_index("destination_unit")
        .loc[units]
    )
    flagged_count = int(anomaly["anomaly_flag"].astype(bool).sum())
    floor_denominator = int(anomaly["pre_calibration_months"].min()) + 1
    all_percentile_one = np.isclose(
        anomaly["post_max_empirical_percentile"].astype(float), 1.0
    ).all()
    percentile_text = (
        "empirical percentile 1.000 for each flagged unit"
        if all_percentile_one
        else "empirical percentiles vary by unit"
    )
    y = np.arange(len(merged))

    panels = (
        (
            "(a) Source concentration",
            "Change in source HHI",
            merged["source_hhi_change"],
            ACCENT_BLUE,
            lambda v: _fmt_signed(v, 2),
            True,
        ),
        (
            "(b) Portfolio reshuffling",
            "Jensen-Shannon distance",
            merged["jensen_shannon_distance"],
            ACCENT_ORANGE,
            lambda v: _fmt(v, 2),
            False,
        ),
        (
            "(c) Exploratory diagnostic",
            "Max post-shock z-score",
            merged["post_max_zscore"],
            NEUTRAL_MID,
            lambda v: _fmt(v, 1),
            False,
        ),
    )

    apply_publication_style()
    fig, axes = plt.subplots(3, 1, figsize=(THESIS_TEXTWIDTH_IN, 6.2))
    for ax, (title, xlabel, values, colour, formatter, signed) in zip(axes, panels):
        bars = ax.barh(y, values, height=0.58, color=colour, zorder=3)
        ax.bar_label(
            bars,
            labels=[formatter(v) for v in values],
            padding=3,
            fontsize=7.5,
        )
        ax.set_title(title, loc="left", fontsize=9.2, pad=4)
        ax.set_xlabel(xlabel, fontsize=9.0)
        ax.set_yticks(y, merged.index)
        ax.tick_params(axis="y", labelsize=8.2)
        ax.invert_yaxis()
        finite = values[np.isfinite(values.astype(float))]
        if len(finite):
            if signed:
                span = max(float(finite.max()) - min(float(finite.min()), 0.0), 1e-9)
                ax.set_xlim(
                    min(float(finite.min()), 0.0) - 0.18 * span,
                    float(finite.max()) + 0.28 * span,
                )
                ax.axvline(0, color=NEUTRAL_DARK, linewidth=0.9, zorder=2)
            else:
                ax.set_xlim(0.0, float(finite.max()) * 1.22)
        style_axes(ax, grid_axis="x")

    axes[2].axvspan(0, 1.96, color=NEUTRAL_LIGHT, alpha=0.55, zorder=1)

    fig.tight_layout(rect=[0, 0.17, 1, 1], h_pad=1.4)
    fig.text(
        0.005,
        0.015,
        (
            "Panel (a) is signed and carries a zero line; panels (b) and (c) are "
            "non-negative magnitudes anchored at zero.\nShading in panel (c) marks "
            "the conventional |z| < 1.96 region. All "
            f"{flagged_count}/{len(anomaly)} units flag, {percentile_text},\n"
            f"tail-p floor-censored at 1/{floor_denominator}, so the flag separates "
            "no unit from another. Panel (c) is ordinal evidence only;\nno panel is "
            "a causal estimate."
        ),
        ha="left",
        va="bottom",
        fontsize=6.6,
        color=NEUTRAL_MID,
        linespacing=1.35,
    )
    return _save(fig, FIG_STRUCTURE)


def _markdown_table(rows: list[list[object]], headers: list[str]) -> str:
    lines = [
        "| " + " | ".join(headers) + " |",
        "|" + "|".join("---" for _ in headers) + "|",
    ]
    lines.extend("| " + " | ".join(str(cell) for cell in row) + " |" for row in rows)
    return "\n".join(lines)


def _display_unit(unit: object, unit_type: object) -> str:
    if str(unit_type) == "aggregate_comparator":
        return f"{unit} (aggregate comparator)"
    return str(unit)


def _source_note(*paths: str) -> str:
    joined = ", ".join(f"`{path}`" for path in paths)
    return f"Source artifact(s): {joined}."


def _quantity_basis_rows(merged: pd.DataFrame) -> list[list[object]]:
    order = ["China", "Korea", "Taiwan", "Japan", "EU27"]
    frame = (
        merged[merged["destination_unit"].isin(order)]
        .set_index("destination_unit")
        .loc[order]
        .reset_index()
    )
    rows = []
    for _, row in frame.iterrows():
        rows.append([
            _display_unit(row["destination_unit"], row["destination_unit_type"]),
            row["primary_typology"],
            row["evidence_strength"],
            row["unit_of_measure"],
            f"{_fmt(row['pre_gulf_share_mean'] * 100)}%",
            f"{_fmt_signed(row['gulf_share_change_pp'])} pp",
            f"{_fmt_signed(row['edge_total_pct_change'])}%",
            f"{_fmt_signed(row['same_calendar_edge_total_pct_change'])}%",
            _fmt(row["jensen_shannon_distance"], 2),
            _fmt(row["post_max_zscore"], 2),
            row["typology_total_change_basis"],
            str(row["coverage_note"]),
        ])
    return rows


def _india_value_basis_rows(merged: pd.DataFrame) -> list[list[object]]:
    india = merged[merged["destination_unit"] == "India"]
    if india.empty:
        return []
    row = india.iloc[0]
    return [[
        row["destination_unit"],
        row["primary_typology"],
        row["evidence_strength"],
        row["unit_of_measure"],
        row["caution_flags"],
        f"{_fmt(row['pre_gulf_share_mean'] * 100)}%",
        f"{_fmt_signed(row['gulf_share_change_pp'])} pp",
        f"{_fmt_signed(row['edge_total_pct_change'])}%",
        f"{_fmt_signed(row['same_calendar_edge_total_pct_change'])}%",
        _fmt(row["jensen_shannon_distance"], 2),
        _fmt(row["post_max_zscore"], 2),
        str(row["coverage_note"]),
    ]]


def _threshold_sensitivity_rows(threshold_sensitivity: pd.DataFrame) -> list[list[object]]:
    rows = []
    summary = threshold_sensitivity.drop_duplicates("destination_unit").set_index(
        "destination_unit"
    )
    for unit in ["China", "Korea", "Taiwan", "Japan", "EU27", "India"]:
        if unit not in summary.index:
            continue
        unit_rows = threshold_sensitivity[
            threshold_sensitivity["destination_unit"] == unit
        ]
        row = summary.loc[unit]
        alternatives = sorted(
            set(unit_rows["grid_primary_typology"]) - {row["headline_primary_typology"]}
        )
        rows.append([
            _display_unit(unit, row["destination_unit_type"]),
            row["headline_primary_typology"],
            f"{_fmt(row['unit_grid_agreement_share'] * 100)}%",
            f"{int(row['unit_grid_agreement_count'])}/{int(row['unit_grid_points'])}",
            "; ".join(alternatives) if alternatives else "none",
        ])
    return rows


def _post_month_sensitivity_rows(post_month_sensitivity: pd.DataFrame) -> list[list[object]]:
    rows = []
    for unit in ["China", "Korea", "Taiwan", "Japan", "EU27", "India"]:
        group = post_month_sensitivity[
            post_month_sensitivity["destination_unit"] == unit
        ]
        if group.empty:
            continue
        first = group.iloc[0]
        available = group[group["unit_had_dropped_month"].astype(bool)]
        flips = available[available["changed_under_drop"].astype(bool)]
        if str(first["destination_unit_type"]) == "aggregate_comparator":
            result = "aggregate comparator"
            detail = "context row; not interpreted as importer typology stability"
        elif flips.empty:
            result = "stable under deletion"
            detail = "no admissible dropped-month label changes"
        else:
            coverage_flips = flips[
                (flips["dropped_primary_typology"] == "not_estimable_coverage_limited")
                | (flips["post_months_after_drop"].astype(int) < 3)
            ]
            substantive_flips = flips.drop(index=coverage_flips.index)
            if not substantive_flips.empty and coverage_flips.empty:
                result = "admissible substantive change"
            elif not coverage_flips.empty and substantive_flips.empty:
                result = "coverage-induced non-estimability"
            else:
                result = "mixed coverage/substantive changes"
            parts = []
            for _, row in coverage_flips.iterrows():
                parts.append(
                    f"{row['dropped_month']} -> below three-post-month gate"
                )
            for _, row in substantive_flips.iterrows():
                parts.append(
                    f"{row['dropped_month']} -> {row['dropped_primary_typology']}"
                )
            detail = "; ".join(parts)
        rows.append([
            _display_unit(first["destination_unit"], first["destination_unit_type"]),
            first["headline_primary_typology"],
            result,
            detail,
        ])
    return rows


def _anomaly_diagnostic_text(anomaly: pd.DataFrame) -> str:
    flagged = anomaly[anomaly["anomaly_flag"].astype(bool)]
    all_flag = len(flagged) == len(anomaly)
    all_percentile_one = np.isclose(
        anomaly["post_max_empirical_percentile"].astype(float), 1.0
    ).all()
    weakest = anomaly.sort_values("post_max_zscore").head(2)
    weakest_text = " and ".join(
        f"{row['destination_unit']} (z {_fmt(row['post_max_zscore'], 2)})"
        for _, row in weakest.iterrows()
    )
    eu27 = anomaly[anomaly["destination_unit"] == "EU27"].iloc[0]
    floor_denominator = int(anomaly["pre_calibration_months"].min()) + 1
    flag_sentence = (
        f"All {len(anomaly)} units flag"
        if all_flag
        else f"{len(flagged)} of {len(anomaly)} units flag"
    )
    percentile_sentence = (
        "post_max_empirical_percentile = 1.000 for all units"
        if all_percentile_one
        else "post_max_empirical_percentile differs across units"
    )
    return (
        f"{flag_sentence}, and {percentile_sentence}. The weakest flagged "
        f"post-shock portfolio z-scores in the current artifact are "
        f"{weakest_text}. EU27 is z {_fmt(eu27['post_max_zscore'], 2)} and "
        "remains an aggregate comparator rather than a single importer. The "
        f"empirical tail-p is floor-censored at 1/{floor_denominator} because "
        "the pre-period calibration uses leave-one-month-out distances over "
        "the available pre months."
    )


def _write_report(
    summary: pd.DataFrame,
    graph: pd.DataFrame,
    anomaly: pd.DataFrame,
    typology: pd.DataFrame,
    reallocation: pd.DataFrame,
    post_month_sensitivity: pd.DataFrame,
    threshold_sensitivity: pd.DataFrame,
    figures: list[Path],
) -> Path:
    merged = (
        summary.merge(
            graph[["destination_unit", "edge_turnover_rate", "jensen_shannon_distance", "non_gulf_offset_ratio"]],
            on="destination_unit",
            how="left",
        )
        .merge(
            anomaly[["destination_unit", "post_max_zscore", "anomaly_flag"]],
            on="destination_unit",
            how="left",
        )
        .merge(
            typology[[
                "destination_unit",
                "primary_typology",
                "evidence_strength",
                "caution_flags",
                "seasonality_adjusted_edge_total_pct_change",
                "typology_total_change_basis",
            ]],
            on="destination_unit",
            how="left",
        )
    )
    realloc_rows = []
    for _, row in reallocation.iterrows():
        realloc_rows.append([
            row["scenario"],
            _fmt(row["demand_k_m3"], 0),
            _fmt(row["gross_observed_post_k_m3"], 0),
            _fmt(row["committed_observed_post_k_m3"], 0),
            _fmt(row["residual_supply_k_m3"], 0),
            _fmt(row["allocated_residual_k_m3"], 0),
            _fmt(row["unmet_share"] * 100),
            _fmt(row["mean_route_nm"], 0),
            _fmt_signed(row["mean_additional_nm"], 0),
            row["coverage_note"],
        ])

    figure_lines = "\n".join(
        f"- `{figure.relative_to(config.ROOT).as_posix()}`" for figure in figures
    )
    text = f"""# Network rewiring results summary

This report is generated from the staged network-rewiring artifacts. It supports
the descriptive claim that origin portfolios changed around the 2026 Hormuz LNG
disruption and records the current reallocation model's data constraint. It does
not show that the disruption was absorbed, and it does not report an ATT, a
freight-rate effect, or observed cargo-level replacement.

## Figures

{figure_lines}

## Quantity-basis importer and comparator summary

{_markdown_table(
    _quantity_basis_rows(merged),
    [
        "Unit",
        "Typology",
        "Strength",
        "Basis",
        "Pre Gulf share",
        "Gulf-share change",
        "Total change vs 12m pre",
        "Total change vs same months",
        "JS distance",
        "Anomaly z",
        "Typology total basis",
        "Coverage",
    ],
)}

{_source_note(
    "data/processed/lng_rewiring_summary.csv",
    "data/processed/lng_rewiring_graph_metrics.csv",
    "data/processed/lng_resilience_typology.csv",
    "data/processed/lng_network_anomaly_summary.csv",
)}

## India — customs-value evidence

{_markdown_table(
    _india_value_basis_rows(merged),
    [
        "Unit",
        "Typology",
        "Strength",
        "Basis",
        "Caution",
        "Pre Gulf share",
        "Gulf-share change",
        "Total change vs 12m pre",
        "Total change vs same months",
        "JS distance",
        "Anomaly z",
        "Coverage",
    ],
)}

India is retained as descriptive customs-value evidence only. Its `kUSD` basis
means the origin mix can embed price differentials as well as quantity changes;
do not pool this row with the physical weight/volume-basis table above.
{_source_note("data/processed/lng_resilience_typology.csv")}

## Typology sensitivity

Threshold-grid agreement with the headline typology:

{_markdown_table(
    _threshold_sensitivity_rows(threshold_sensitivity),
    [
        "Unit",
        "Headline typology",
        "Grid agreement share",
        "Agreement count",
        "Alternative grid labels",
    ],
)}

Leave-one-post-month interpretation:

{_markdown_table(
    _post_month_sensitivity_rows(post_month_sensitivity),
    [
        "Unit",
        "Headline typology",
        "Leave-one-post-month result",
        "Dropped-month detail",
    ],
)}

{_source_note(
    "data/processed/lng_typology_threshold_sensitivity.csv",
    "data/processed/lng_rewiring_post_month_sensitivity.csv",
)}

## Anomaly diagnostics

{_anomaly_diagnostic_text(anomaly)}
{_source_note("data/processed/lng_network_anomaly_summary.csv")}

## Reallocation stress scenarios

{_markdown_table(
    realloc_rows,
    [
        "Scenario",
        "Demand k m3",
        "Gross observed post k m3",
        "Committed post k m3",
        "Residual supply k m3",
        "Allocated residual k m3",
        "Unmet share %",
        "Mean route nm",
        "Mean additional nm",
        "Coverage",
    ],
)}

## Interpretation guardrails

- China and Korea are classified as high-exposure constrained: their Gulf shares
  fell sharply and non-Gulf growth did not offset the lost Gulf edge value in
  the observed origin-split table.
- Evidence strength follows the transparent typology rubric: `high` is reserved
  for unflagged high-exposure high-offset cases; constrained cases,
  low-exposure stable cases, and flagged high-offset cases are `medium`;
  aggregate comparators are `context_only`.
- India and Taiwan are classified as high-exposure high-offset. Taiwan is the
  unflagged high-strength case; India remains value-basis, so its substitution
  pattern should be read as customs-value evidence, not physical quantity
  evidence.
- EU27 is retained only as an aggregate comparator. Japan now has enough
  source-native e-Stat/Japan Customs support for the descriptive typology and
  is classified as a low-exposure stable comparator in this vintage.
- Graph-distance anomaly scores are exploratory mechanism diagnostics. The
  current artifact flags all six units at the empirical percentile ceiling, but
  this is floor-censored by the 12-month pre-calibration support and remains
  outside the primary causal inference family.
- The reallocation model reserves every completed post-period non-Gulf voyage
  for its recorded destination before calculating spare supply. The voyage
  input therefore provides no observed uncommitted capacity, so the residual
  scenario is fully unmet. This is a data-availability result, not evidence that
  global LNG replacement was physically impossible. A positive spare-supply
  scenario requires independently sourced terminal headroom.
- Cross-unit tables mix native measurement bases: China, Japan, Korea, and
  Taiwan are tonnes; EU27 is MIO_M3; India is kUSD. Compare within-unit
  movements first, and treat India as value-basis evidence.
"""
    out = config.ROOT / "reports" / REPORT
    out.write_text(text, encoding="utf-8")
    print(f"wrote {out}")
    return out


def main() -> None:
    summary = _read("lng_rewiring_summary_csv")
    graph = _read("lng_rewiring_graph_metrics_csv")
    anomaly = _read("lng_network_anomaly_summary_csv")
    typology = _read("lng_resilience_typology_csv")
    reallocation = _read("lng_reallocation_summary_csv")
    post_month_sensitivity = _read("lng_rewiring_post_month_sensitivity_csv")
    threshold_sensitivity = _read("lng_typology_threshold_sensitivity_csv")

    figures = [
        _plot_origin_composition(summary),
        _plot_gulf_vs_total(summary),
        _plot_source_structure(summary, graph, anomaly),
    ]
    _write_report(
        summary,
        graph,
        anomaly,
        typology,
        reallocation,
        post_month_sensitivity,
        threshold_sensitivity,
        figures,
    )


if __name__ == "__main__":
    main()
