"""Generate the integrated open-data LNG mechanism report and summary figure."""
from __future__ import annotations

import json
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


REPORT = "mechanism_results_summary.md"
FIGURE = "mechanism_evidence_summary.png"


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
    fig, axes = plt.subplots(2, 2, figsize=(13.5, 9.5))
    fig.suptitle(
        "Open-data evidence on the LNG fleet-distance mechanism",
        fontsize=16,
        fontweight="bold",
        y=0.98,
    )

    ax = axes[0, 0]
    labels = ["WTO outbound\nindex", "GFW Gulf\ncalls", "GFW nominal\ncapacity"]
    values = [
        wto_changes["wto_mean_index_percent_change"],
        wto_changes["gfw_departure_calls_percent_change"],
        wto_changes["gfw_nominal_capacity_percent_change"],
    ]
    bars = ax.bar(labels, values, color=[colors["observed"], colors["inferred"], colors["inferred"]])
    ax.axhline(0, color="#333333", linewidth=0.8)
    ax.set(title="A. Independent departure-collapse validation", ylabel="Pre/post change (%)")
    ax.bar_label(bars, labels=[_pct(value) for value in values], padding=3, fontsize=9)
    ax.set_ylim(min(values) - 15, 8)
    ax.grid(axis="y", alpha=0.2)

    ax = axes[0, 1]
    labels = ["Routed\nvoyages", "Total capacity-\ndistance", "Mean capacity-\ndistance/voyage", "Mean sailing\ndays/voyage"]
    values = [
        capacity["expanded_routed_voyage_percent_change"],
        capacity["expanded_percent_change"],
        capacity["expanded_mean_per_voyage_percent_change"],
        vessel["mean_modeled_sailing_days_per_voyage_percent_change"],
    ]
    bars = ax.bar(
        labels,
        values,
        color=[colors["inferred"], colors["modeled"], colors["modeled"], colors["modeled"]],
    )
    ax.axhline(0, color="#333333", linewidth=0.8)
    ax.set(title="B. Count versus distance decomposition", ylabel="Pre/post change (%)")
    ax.bar_label(bars, labels=[_pct(value) for value in values], padding=3, fontsize=8)
    ax.set_ylim(min(values) - 8, max(values) + 8)
    ax.grid(axis="y", alpha=0.2)

    ax = axes[1, 0]
    top = importer.loc[importer["pre_hormuz_exposed_voyages"].gt(0)].head(7).copy()
    top = top.iloc[::-1]
    y = np.arange(len(top))
    ax.barh(
        y - 0.18,
        top["hormuz_exposed_capacity_absolute_change_m3"] / 1e6,
        height=0.34,
        color=colors["loss"],
        label="Hormuz-exposed change",
    )
    ax.barh(
        y + 0.18,
        top["non_gulf_capacity_absolute_change_m3"] / 1e6,
        height=0.34,
        color=colors["gain"],
        label="Non-Gulf change",
    )
    ax.set_yticks(y, top["destination_country"])
    ax.axvline(0, color="#333333", linewidth=0.8)
    ax.set(title="C. Largest pre-period importer exposures", xlabel="Nominal capacity change (million m3)")
    ax.legend(frameon=False, fontsize=8, loc="lower right")
    ax.grid(axis="x", alpha=0.2)

    ax = axes[1, 1]
    ordered = basin.set_index("destination_basin").reindex(["Pacific", "Atlantic", "Middle East"])
    y = np.arange(len(ordered))
    width = 0.34
    ax.barh(
        y - width / 2,
        ordered["total_capacity_percent_change"],
        height=width,
        color=colors["inferred"],
        label="Nominal capacity",
    )
    ax.barh(
        y + width / 2,
        ordered["expanded_m3_nm_percent_change"],
        height=width,
        color=colors["modeled"],
        label="Capacity-distance",
    )
    ax.set_yticks(y, ordered.index)
    ax.axvline(0, color="#333333", linewidth=0.8)
    ax.set(title="D. Destination-basin composition", xlabel="Pre/post change (%)")
    ax.legend(frameon=False, fontsize=8)
    ax.grid(axis="x", alpha=0.2)

    fig.text(
        0.5,
        0.012,
        "Observed aggregate index, inferred terminal sequences, and modeled routes are distinct evidence layers. "
        "No cargo quantity, sailed track, freight rate, or causal ATT is claimed.",
        ha="center",
        fontsize=9,
        color="#444444",
    )
    fig.tight_layout(rect=[0, 0.035, 1, 0.95])
    output = config.path("figures") / FIGURE
    fig.savefig(output, dpi=180, bbox_inches="tight")
    fig.savefig(output.with_suffix(".pdf"), bbox_inches="tight")
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
            "evidence_layer": "independent_aggregate_observation",
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
    top = importer.loc[importer["pre_hormuz_exposed_voyages"].gt(0)].head(5)
    importer_rows = [
        (
            f"| {row['destination_country']} | {row['pre_hormuz_exposure_capacity_share_pct']:.1f}% | "
            f"{row['descriptive_non_gulf_offset_ratio'] * 100:.1f}% | "
            f"{row['total_capacity_percent_change']:+.1f}% | "
            f"{row['expanded_m3_nm_percent_change']:+.1f}% |"
        )
        for _, row in top.iterrows()
    ]
    lines = [
        "# Integrated LNG Mechanism Results",
        "",
        "**Generated from processed artifacts.** Observed, inferred, and modeled "
        "quantities are kept separate throughout.",
        "",
        "## Evidence chain",
        "",
        f"1. The independent WTO/AXSMarine LNG outbound index falls **{abs(changes['wto_mean_index_percent_change']):.1f}%**.",
        f"2. Inferred Qatar/UAE departure calls fall **{abs(changes['gfw_departure_calls_percent_change']):.1f}%**, providing independent directional agreement.",
        f"3. At the 30 km terminal radius with expanded route QA, routed voyages fall **{abs(capacity['expanded_routed_voyage_percent_change']):.1f}%**, while mean capacity-distance per voyage rises **{capacity['expanded_mean_per_voyage_percent_change']:.1f}%**.",
        f"4. At 15 knots, mean modeled sailing days per voyage rise **{vessel['mean_modeled_sailing_days_per_voyage_percent_change']:.1f}%**, equivalent to **{vessel['descriptive_post_excess_sailing_days_vs_pre_mean']:.0f} descriptive excess post sailing days** versus the pre mean.",
        "5. Importer effects are heterogeneous: some markets show non-Gulf composition offsets, while others show near-complete loss.",
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
        "The evidence is consistent with a fleet-distance multiplier among retained "
        "post-period LNG voyages: fewer voyages are observed, but retained voyages "
        "are longer and consume more nominal capacity-time on average. It does not "
        "identify actual cargo quantities, unmet demand, sailed AIS tracks, freight "
        "rates, or a causal ATT. The non-Gulf offset ratio is descriptive composition, "
        "not a substitution coefficient.",
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
