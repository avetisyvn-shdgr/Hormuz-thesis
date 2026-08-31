"""Generate the integrated open-data LNG mechanism report and summary figure."""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/hormuz_throughput-matplotlib")

import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

sys.path.insert(0, str(Path(__file__).resolve().parent))
from figure_style import (  # noqa: E402
    THESIS_TEXTWIDTH_IN,
    NEUTRAL_MID,
    apply_publication_style,
    style_axes,
)
from hormuz_throughput import config  # noqa: E402


REPORT = "mechanism_results_summary.md"
FIGURE = "mechanism_evidence_summary.png"
PDF_METADATA = {
    "Creator": "hormuz_throughput reproducible pipeline",
    "CreationDate": datetime(2026, 2, 28, tzinfo=timezone.utc),
    "ModDate": datetime(2026, 2, 28, tzinfo=timezone.utc),
}


def _csv(path_key: str) -> pd.DataFrame:
    path = config.ROOT / config.settings()["paths"][path_key]
    if not path.exists():
        raise FileNotFoundError(f"Missing upstream artifact: {path}")
    return pd.read_csv(path)


def _json(path_key: str) -> dict:
    path = config.ROOT / config.settings()["paths"][path_key]
    if not path.exists():
        raise FileNotFoundError(f"Missing upstream artifact: {path}")
    return json.loads(path.read_text())


def _pct(value: float) -> str:
    return f"{value:+.1f}%"


def _save_figure(
    wto_changes: dict,
    capacity: pd.Series,
    vessel: pd.Series,
    importer: pd.DataFrame,
    basin: pd.DataFrame,
) -> Path:
    colors = {
        "observed": "#365F91",
        "inferred": "#D17A22",
        "modeled": "#5B8E7D",
        "loss": "#B44C43",
        "gain": "#4F7C5B",
        "neutral": "#7A7A7A",
    }
    estimable = importer.loc[
        importer["pre_hormuz_exposed_voyages"].gt(0)
        & importer["country_hormuz_exposed_estimate_estimable"].eq(True)
    ]
    if not estimable.empty:
        raise RuntimeError(
            "importer_exposure_summary now contains "
            f"{len(estimable)} estimable country-level Hormuz-exposed rows. "
            "The suppressed-importer panel was removed while that set was empty; "
            "reinstate a panel rather than leaving the evidence out of the figure."
        )

    apply_publication_style()
    fig = plt.figure(figsize=(THESIS_TEXTWIDTH_IN, 5.6))
    grid_top = fig.add_gridspec(
        1, 2, left=0.135, right=0.985, top=0.880, bottom=0.610, wspace=0.10
    )
    grid_bottom = fig.add_gridspec(
        1, 1, left=0.135, right=0.985, top=0.425, bottom=0.225
    )
    ax_a = fig.add_subplot(grid_top[0, 0])
    ax_b = fig.add_subplot(grid_top[0, 1], sharey=ax_a)
    ax_c = fig.add_subplot(grid_bottom[0, 0])

    ax = ax_a
    labels = ["WTO outbound\nindex", "GFW Gulf\ncalls", "GFW nominal\ncapacity"]
    values_a = [
        wto_changes["wto_mean_index_percent_change"],
        wto_changes["gfw_departure_calls_percent_change"],
        wto_changes["gfw_nominal_capacity_percent_change"],
    ]
    bars = ax.bar(
        labels,
        values_a,
        color=[colors["observed"], colors["inferred"], colors["inferred"]],
    )
    ax.set_title("A. Cross-source departure collapse", loc="left", pad=4, fontsize=8.3)
    ax.set_ylabel("Pre/post change (%)", fontsize=9.0)
    ax.bar_label(bars, labels=[_pct(value) for value in values_a], padding=2, fontsize=7.0)
    style_axes(ax, grid_axis="y")
    ax.tick_params(axis="x", labelsize=7.5)

    ax = ax_b
    labels = [
        "Routed\nvoyages",
        "Total\ncap.-dist.",
        "Cap.-dist.\nper voyage",
        "Sailing days\nper voyage",
    ]
    values_b = [
        capacity["expanded_routed_voyage_percent_change"],
        capacity["expanded_percent_change"],
        capacity["expanded_mean_per_voyage_percent_change"],
        vessel["mean_modeled_sailing_days_per_voyage_percent_change"],
    ]
    bars = ax.bar(
        labels,
        values_b,
        color=[colors["inferred"], colors["modeled"], colors["modeled"], colors["modeled"]],
    )
    ax.set_title("B. Count versus distance decomposition", loc="left", pad=4, fontsize=8.3)
    ax.bar_label(bars, labels=[_pct(value) for value in values_b], padding=2, fontsize=7.0)
    style_axes(ax, grid_axis="y")
    ax.tick_params(axis="x", labelsize=6.8)
    ax.tick_params(axis="y", labelleft=False)

    shared = [float(value) for value in values_a + values_b]
    span = max(shared) - min(shared)
    for ax in (ax_a, ax_b):
        ax.set_ylim(min(shared) - 0.17 * span, max(shared) + 0.22 * span)
        ax.axhline(0, color="#333333", linewidth=0.8, zorder=2)

    layer_handles = [
        Patch(facecolor=colors["observed"], label="Observed index"),
        Patch(facecolor=colors["inferred"], label="Inferred terminal sequence"),
        Patch(facecolor=colors["modeled"], label="Modeled route work"),
    ]
    fig.legend(
        handles=layer_handles,
        frameon=False,
        fontsize=7.2,
        loc="upper center",
        bbox_to_anchor=(0.5, 1.0),
        ncol=3,
        handlelength=1.2,
        handleheight=0.9,
        columnspacing=1.6,
    )

    ax = ax_c
    ordered = basin.set_index("destination_basin").reindex(["Pacific", "Atlantic", "Middle East"])
    y = np.arange(len(ordered))
    width = 0.34
    ax.barh(
        y - width / 2,
        ordered["total_capacity_percent_change"],
        height=width,
        color=colors["inferred"],
        label="Nominal capacity (inferred)",
    )
    ax.barh(
        y + width / 2,
        ordered["expanded_m3_nm_percent_change"],
        height=width,
        color=colors["modeled"],
        label="Capacity-distance (modeled)",
    )
    ax.set_yticks(y, ordered.index)
    ax.axvline(0, color="#333333", linewidth=0.8)
    ax.set_title(
        "C. Destination-basin composition",
        loc="left",
        pad=0,
        y=1.28,
        fontsize=8.3,
    )
    ax.set_xlabel("Pre/post change (%)", fontsize=9.0)
    ax.legend(
        frameon=False,
        fontsize=7.0,
        loc="lower left",
        bbox_to_anchor=(0.0, 1.03),
        borderaxespad=0.0,
        ncol=2,
        handlelength=1.4,
        columnspacing=1.5,
    )
    style_axes(ax, grid_axis="x")
    ax.tick_params(axis="y", labelsize=8.0)

    fig.text(
        0.005,
        0.055,
        "Panels A and B share one scale and one zero line; panel C is a different "
        "cut and carries its own.\nCountry-level Hormuz-exposed changes are not "
        "estimable (post n = 2 overall) and are reported as a null, not plotted.\n"
        "Observed aggregate index, inferred terminal sequences, and modeled routes "
        "are distinct evidence layers. No cargo\nquantity, sailed track, freight "
        "rate, or causal ATT is claimed.",
        ha="left",
        va="bottom",
        fontsize=6.6,
        color=NEUTRAL_MID,
        linespacing=1.35,
    )
    output = config.path("figures") / FIGURE
    fig.savefig(output, dpi=180, bbox_inches="tight")
    fig.savefig(
        output.with_suffix(".pdf"), bbox_inches="tight", metadata=PDF_METADATA
    )
    plt.close(fig)
    return output


def main() -> None:
    paths = config.settings()["paths"]
    capacity_all = _csv("inferred_capacity_nm_comparison_csv")
    vessel_all = _csv("vessel_day_comparison_csv")
    importer = _csv("importer_exposure_summary_csv")
    basin = _csv("basin_exposure_summary_csv")
    wto = _json("gulf_departure_validation_summary_json")
    exposure_diag = _json("importer_basin_exposure_diagnostics_json")
    route_diag = _json("inferred_capacity_nm_diagnostics_json")
    capacity_bootstrap = _json("inferred_capacity_nm_bootstrap_json")
    capacity_decomposition = _json("inferred_capacity_nm_decomposition_json")

    capacity = capacity_all.loc[
        capacity_all["terminal_match_radius_km"].eq(30)
    ].iloc[0]
    vessel = vessel_all.loc[
        vessel_all["terminal_match_radius_km"].eq(30)
        & vessel_all["route_specification"].eq("expanded_60nm_snap")
        & vessel_all["speed_knots"].eq(15.0)
    ].iloc[0]
    changes = wto["pre_post_changes"]

    evidence = pd.DataFrame([
        {
            "evidence_layer": "aggregate_cross_source_observation",
            "measure": "WTO_Hormuz_LNG_outbound_index_mean",
            "pre_value": wto["periods"]["pre"]["wto_mean_outbound_volume_index"],
            "post_value": wto["periods"]["post"]["wto_mean_outbound_volume_index"],
            "percent_change": changes["wto_mean_index_percent_change"],
            "unit": "index_2025_mean_100",
        },
        {
            "evidence_layer": "inferred_terminal_sequence",
            "measure": "inside_Hormuz_Gulf_departure_calls",
            "pre_value": wto["periods"]["pre"]["gfw_departure_calls"],
            "post_value": wto["periods"]["post"]["gfw_departure_calls"],
            "percent_change": changes["gfw_departure_calls_percent_change"],
            "unit": "calls",
        },
        {
            "evidence_layer": "modeled_route_x_nominal_capacity",
            "measure": "expanded_total_capacity_nautical_miles",
            "pre_value": capacity["expanded_pre_total_nominal_m3_nm"],
            "post_value": capacity["expanded_post_total_nominal_m3_nm"],
            "percent_change": capacity["expanded_percent_change"],
            "unit": "nominal_m3_nm",
        },
        {
            "evidence_layer": "modeled_route_x_speed_assumption",
            "measure": "expanded_total_sailing_vessel_days_at_15kn",
            "pre_value": vessel["pre_total_modeled_sailing_vessel_days"],
            "post_value": vessel["post_total_modeled_sailing_vessel_days"],
            "percent_change": vessel["total_modeled_sailing_vessel_days_percent_change"],
            "unit": "vessel_days",
        },
    ])
    evidence_path = config.ROOT / paths["mechanism_evidence_summary_csv"]
    evidence.to_csv(evidence_path, index=False)

    figure = _save_figure(changes, capacity, vessel, importer, basin)
    top = importer.loc[
        importer["pre_hormuz_exposed_voyages"].gt(0)
        & importer["country_hormuz_exposed_estimate_estimable"].eq(True)
    ].head(5)
    importer_rows = [
        (
            f"| {row['destination_country']} | {row['pre_hormuz_exposure_capacity_share_pct']:.1f}% | "
            f"{row['descriptive_non_gulf_offset_ratio'] * 100:.1f}% | "
            f"{row['total_capacity_percent_change']:+.1f}% | "
            f"{row['expanded_m3_nm_percent_change']:+.1f}% |"
        )
        for _, row in top.iterrows()
    ]
    if not importer_rows:
        importer_rows = [
            "| Not estimable | Country-level post Hormuz support is only 2 voyages overall | - | - | - |"
        ]
    lines = [
        "# Integrated LNG Mechanism Results",
        "",
        "**Generated from processed artifacts.** Observed, inferred, and modeled "
        "quantities are kept separate throughout.",
        "",
        "## Evidence chain",
        "",
        f"1. The distinct WTO/AXSMarine LNG outbound index falls **{abs(changes['wto_mean_index_percent_change']):.1f}%**.",
        f"2. Inferred Qatar/UAE departure calls fall **{abs(changes['gfw_departure_calls_percent_change']):.1f}%**, providing cross-source directional agreement; both measures retain maritime-observation risks.",
        f"3. At the 30 km terminal radius with expanded route QA, routed voyages fall **{abs(capacity['expanded_routed_voyage_percent_change']):.1f}%**, while mean capacity-distance per voyage rises **{capacity['expanded_mean_per_voyage_percent_change']:.1f}%** (carrier-cluster BCa 95% interval **{capacity_bootstrap['bca_ci_lower']:.1f}% to {capacity_bootstrap['bca_ci_upper']:.1f}%**; percentile comparison **{capacity_bootstrap['percentile_ci_lower']:.1f}% to {capacity_bootstrap['percentile_ci_upper']:.1f}%**).",
        f"4. At 15 knots, mean modeled sailing days per voyage rise **{vessel['mean_modeled_sailing_days_per_voyage_percent_change']:.1f}%**, equivalent to **{vessel['descriptive_post_excess_sailing_days_vs_pre_mean']:.0f} descriptive excess post sailing days** versus the pre mean.",
        "5. Country-level Hormuz-exposed changes are suppressed where post-period voyage support is below the pre-specified minimum; basin aggregates are retained.",
        "",
        "## Primary physical-mechanism specification",
        "",
        "| Quantity | Pre | Post | Change |",
        "|---|---:|---:|---:|",
        f"| Routed voyages | {capacity['expanded_pre_routed_voyages']:.0f} | {capacity['expanded_post_routed_voyages']:.0f} | {capacity['expanded_routed_voyage_percent_change']:+.1f}% |",
        f"| Nominal capacity-distance (billion m3-nm) | {capacity['expanded_pre_total_nominal_m3_nm']/1e9:.1f} | {capacity['expanded_post_total_nominal_m3_nm']/1e9:.1f} | {capacity['expanded_percent_change']:+.1f}% |",
        f"| Mean nominal capacity-distance/voyage (million m3-nm) | {capacity['expanded_pre_mean_nominal_m3_nm_per_voyage']/1e6:.1f} | {capacity['expanded_post_mean_nominal_m3_nm_per_voyage']/1e6:.1f} | {capacity['expanded_mean_per_voyage_percent_change']:+.1f}% |",
        f"| Modeled sailing vessel-days at 15 kn | {vessel['pre_total_modeled_sailing_vessel_days']:.0f} | {vessel['post_total_modeled_sailing_vessel_days']:.0f} | {vessel['total_modeled_sailing_vessel_days_percent_change']:+.1f}% |",
        "",
        "## Route shift-share decomposition",
        "",
        (
            f"Across **{capacity_decomposition['n_common_routes']}** terminal "
            "pairs observed in both periods, the common-route mean change is "
            f"**{capacity_decomposition['common_route_total_change']/1e6:.1f} "
            "million m3-nm**: "
            f"**{capacity_decomposition['common_route_composition_change']/1e6:.1f} "
            "million** from route-share composition and "
            f"**{capacity_decomposition['common_route_within_change']/1e6:.1f} "
            "million** within pairs. Entry/exit routes contribute a separate "
            f"**{capacity_decomposition['entry_exit_route_residual']/1e6:.1f} "
            "million m3-nm** residual to the full-sample mean increase of "
            f"**{capacity_decomposition['overall_absolute_change']/1e6:.1f} "
            "million m3-nm**."
        ),
        "",
        (
            "Modeled distance is fixed within a terminal pair, so the within-pair "
            "term reflects vessel-capacity mix, not route elongation. Within "
            "common terminal pairs, the change is overwhelmingly route-share "
            "composition; for the full-sample +10.2% headline, entry/exit is a "
            "separate sample-composition residual and should be named alongside "
            "the common-route decomposition."
        ),
        "",
        "## Highest importer exposures",
        "",
        "| Importer | Pre Hormuz-exposed share | Descriptive non-Gulf offset | Total capacity change | Capacity-distance change |",
        "|---|---:|---:|---:|---:|",
        *importer_rows,
        "",
        "## Coverage",
        "",
        f"- Carrier frame: **{route_diag['carrier_frame']['unique_imos']} unique IMOs**, no duplicate or invalid capacities.",
        f"- Resolved voyages: **{exposure_diag['by_period']['pre']['resolved_voyages']} pre**, **{exposure_diag['by_period']['post']['resolved_voyages']} post**.",
        f"- Expanded route coverage: **{exposure_diag['by_period']['pre']['expanded_route_coverage_rate']:.1%} pre**, **{exposure_diag['by_period']['post']['expanded_route_coverage_rate']:.1%} post**.",
        "- WTO comparison uses equal 94-day year-over-year windows and no fitted scaling factor.",
        "",
        "## Interpretation boundary",
        "",
        "The retained-voyage result is a conditional sample-composition shift, "
        "not a fleet-distance or ton-mile multiplier. Routed voyages and aggregate "
        "nominal capacity-distance both fall, while mean modeled capacity-distance "
        "rises only among resolved voyages retained in the post-period sample. "
        "Common-route route shares and a separate entry/exit residual drive that "
        "pattern; fixed terminal-pair distances do not establish route elongation. "
        "The evidence does not identify actual cargo quantities, unmet demand, "
        "sailed AIS tracks, freight rates, or a causal ATT. The non-Gulf offset "
        "ratio is descriptive composition, not a substitution coefficient.",
        "",
        "## Figure",
        "",
        f"![Integrated LNG mechanism evidence](figures/{FIGURE})",
    ]
    report = config.ROOT / "reports" / REPORT
    report.write_text("\n".join(lines) + "\n")
    print(f"wrote {evidence_path}")
    print(f"wrote {figure}")
    print(f"wrote {report}")


if __name__ == "__main__":
    main()
