"""Generate the downstream PortWatch sensitivity-budget reporting card.

The upstream model-vintage matrix is immutable and G4-verified. This script
only transforms its frozen summary into reporting artifacts. It keeps the two
absolute-scale sensitivity axes separate and adds a subordinate model-specific
counterfactual normalization as scale context, never as a third budget axis.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path

# Keep Matplotlib/font discovery out of non-writable user cache locations.
_MPL_CACHE = Path(tempfile.gettempdir()) / "lngfreight-matplotlib-cache"
_MPL_CACHE.mkdir(parents=True, exist_ok=True)
_XDG_CACHE = _MPL_CACHE / "xdg"
_XDG_CACHE.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(_MPL_CACHE))
os.environ.setdefault("XDG_CACHE_HOME", str(_XDG_CACHE))
os.environ.setdefault("MPLBACKEND", "Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from lngfreight import config  # noqa: E402
from figure_style import (  # noqa: E402
    DECREASE_COLOR,
    FIGURE_WIDTH_IN,
    INCREASE_COLOR,
    NEUTRAL_DARK,
    NEUTRAL_MID,
    apply_publication_style,
    save_pdf_and_png,
    style_axes,
)


DESIGN_PATH = config.CONFIG_DIR / "portwatch_sensitivity_budget_card.yaml"
MODEL_LABELS = {
    "seasonal_naive_7d": "Seasonal naive",
    "ar_lag1_7": "AR(1,7)",
    "chronos2": "Chronos-2",
    "bsts_local_level_weekly": "BSTS",
}
MODEL_COLORS = {
    "seasonal_naive_7d": "#7570B3",
    "ar_lag1_7": "#D95F02",
    "chronos2": "#1B9E77",
    "bsts_local_level_weekly": "#666666",
}
VINTAGE_LABELS = {
    "pinned_primary": "Pinned July",
    "vintage_20260809": "August",
}
PINNED = "pinned_primary"
AUGUST = "vintage_20260809"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_design() -> tuple[dict, str]:
    raw = DESIGN_PATH.read_bytes()
    return yaml.safe_load(raw), hashlib.sha256(raw).hexdigest()


def output_path(design: dict, key: str) -> Path:
    return config.ROOT / design["outputs"][key]


def load_verified_inputs(design: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Verify every parent hash and the exact reporting population."""
    parents = design["parent_artifacts"]
    for label, spec in parents.items():
        path = config.ROOT / spec["path"]
        if not path.is_file():
            raise FileNotFoundError(f"sensitivity-card parent missing: {label}")
        actual = sha256_file(path)
        if actual != spec["sha256"]:
            raise ValueError(
                f"sensitivity-card parent hash drift for {label}: {actual}"
            )

    summary = pd.read_csv(config.ROOT / parents["matrix_summary"]["path"])
    admission = pd.read_csv(
        config.ROOT / parents["admission_known_results"]["path"]
    )
    validate_matrix_summary(summary, design)
    return summary, admission


def validate_matrix_summary(summary: pd.DataFrame, design: dict) -> None:
    required = {
        "vintage",
        "model",
        "point_definition",
        "unit",
        "train_start",
        "train_end",
        "scoring_start",
        "scoring_end",
        "n_scored_days",
        "observed_sum",
        "counterfactual_point_sum",
        "cumulative_common_point_shortfall",
        "mean_daily_common_point_shortfall",
    }
    missing = required.difference(summary.columns)
    if missing:
        raise ValueError(f"matrix summary lacks card columns: {sorted(missing)}")

    models = design["selected_representative_models"]
    vintages = design["vintages"]
    expected = {(vintage, model) for vintage in vintages for model in models}
    cells = set(zip(summary["vintage"], summary["model"]))
    if cells != expected or len(summary) != 8:
        raise ValueError("sensitivity card requires the exact selected 2x4 matrix")
    if summary.duplicated(["vintage", "model"]).any():
        raise ValueError("sensitivity-card matrix contains duplicate cells")
    if not summary["unit"].eq(design["comparison_basis"]["unit"]).all():
        raise ValueError("sensitivity-card matrix mixes units")
    if not summary["n_scored_days"].eq(
        design["comparison_basis"]["scored_days"]
    ).all():
        raise ValueError("sensitivity-card matrix support drifted")
    expected_dates = {
        "train_start": design["comparison_basis"]["training_start"],
        "train_end": design["comparison_basis"]["training_end"],
        "scoring_start": design["comparison_basis"]["scoring_start"],
        "scoring_end": design["comparison_basis"]["scoring_end"],
    }
    for column, expected_value in expected_dates.items():
        if not summary[column].eq(expected_value).all():
            raise ValueError(f"sensitivity-card {column} drifted")
    if (summary.groupby("vintage")["observed_sum"].nunique(dropna=False) != 1).any():
        raise ValueError("sensitivity-card observed totals differ within vintage")
    expected_points = design["expected_point_definitions"]
    for model, expected_point in expected_points.items():
        model_rows = summary.loc[summary["model"].eq(model), "point_definition"]
        if len(model_rows) != 2 or not model_rows.eq(expected_point).all():
            raise ValueError(f"sensitivity-card point definition drifted for {model}")

    numeric = summary[[
        "observed_sum",
        "counterfactual_point_sum",
        "cumulative_common_point_shortfall",
        "mean_daily_common_point_shortfall",
    ]].astype("float64")
    if not np.isfinite(numeric.to_numpy()).all():
        raise ValueError("sensitivity-card matrix contains non-finite values")
    if (numeric["counterfactual_point_sum"] <= 0).any():
        raise ValueError("sensitivity-card normalization denominator is non-positive")
    if not np.allclose(
        numeric["observed_sum"] + numeric["cumulative_common_point_shortfall"],
        numeric["counterfactual_point_sum"],
        rtol=0.0,
        atol=1e-8,
    ):
        raise ValueError("counterfactual sum does not reconcile to observed + shortfall")
    if not np.allclose(
        numeric["cumulative_common_point_shortfall"]
        / summary["n_scored_days"].astype("float64"),
        numeric["mean_daily_common_point_shortfall"],
        rtol=0.0,
        atol=1e-10,
    ):
        raise ValueError("common mean-daily statistic does not reconcile")


def build_cell_table(summary: pd.DataFrame, design: dict) -> pd.DataFrame:
    """Return one row per selected model with both vintages and both metrics."""
    work = summary.copy()
    work["shortfall_share_of_counterfactual_pct"] = (
        100.0
        * work["cumulative_common_point_shortfall"]
        / work["counterfactual_point_sum"]
    )
    absolute = work.pivot(
        index="model", columns="vintage", values="mean_daily_common_point_shortfall"
    )
    normalized = work.pivot(
        index="model", columns="vintage", values="shortfall_share_of_counterfactual_pct"
    )
    point_definition = work.groupby("model")["point_definition"].first()
    rows = []
    for model in design["selected_representative_models"]:
        pinned_absolute = float(absolute.loc[model, PINNED])
        august_absolute = float(absolute.loc[model, AUGUST])
        pinned_normalized = float(normalized.loc[model, PINNED])
        august_normalized = float(normalized.loc[model, AUGUST])
        rows.append({
            "model": model,
            "model_label": MODEL_LABELS[model],
            "point_definition": str(point_definition.loc[model]),
            "is_locked_primary_model": bool(
                model == design["locked_primary_model"]
            ),
            "pinned_shortfall_per_day": pinned_absolute,
            "august_shortfall_per_day": august_absolute,
            "pinned_minus_august_per_day": pinned_absolute - august_absolute,
            "august_lower_pct_of_pinned_shortfall": (
                100.0 * (pinned_absolute - august_absolute) / pinned_absolute
            ),
            "pinned_shortfall_share_of_counterfactual_pct": pinned_normalized,
            "august_shortfall_share_of_counterfactual_pct": august_normalized,
            "august_minus_pinned_percentage_points": (
                august_normalized - pinned_normalized
            ),
        })
    return pd.DataFrame(rows)


def _range_record(
    cells: pd.DataFrame,
    *,
    vintage: str,
    value_column: str,
    unit: str,
) -> dict:
    values = cells.set_index("model")[value_column]
    min_model = str(values.idxmin())
    max_model = str(values.idxmax())
    return {
        "vintage": vintage,
        "vintage_label": VINTAGE_LABELS[vintage],
        "minimum_model": min_model,
        "minimum_model_label": MODEL_LABELS[min_model],
        "minimum": float(values.min()),
        "maximum_model": max_model,
        "maximum_model_label": MODEL_LABELS[max_model],
        "maximum": float(values.max()),
        "range": float(values.max() - values.min()),
        "unit": unit,
    }


def build_card_payload(
    cells: pd.DataFrame,
    admission: pd.DataFrame,
    design: dict,
    design_sha256: str,
) -> dict:
    """Build the full-precision machine card and explicit guardrails."""
    pinned_absolute = _range_record(
        cells,
        vintage=PINNED,
        value_column="pinned_shortfall_per_day",
        unit="transits_per_day",
    )
    august_absolute = _range_record(
        cells,
        vintage=AUGUST,
        value_column="august_shortfall_per_day",
        unit="transits_per_day",
    )
    pinned_normalized = _range_record(
        cells,
        vintage=PINNED,
        value_column="pinned_shortfall_share_of_counterfactual_pct",
        unit="percentage_points",
    )
    august_normalized = _range_record(
        cells,
        vintage=AUGUST,
        value_column="august_shortfall_share_of_counterfactual_pct",
        unit="percentage_points",
    )
    differences = cells["pinned_minus_august_per_day"]
    normalized_changes = cells["august_minus_pinned_percentage_points"]
    primary = cells.loc[cells["is_locked_primary_model"]].iloc[0]

    arx = admission.loc[
        admission["result_id"].eq("pinned_arx_route_energy_mixed_information")
    ]
    if len(arx) != 1 or bool(arx.iloc[0]["comparable_same_information"]):
        raise ValueError("conditional ARX admission disclosure is missing or drifted")
    arx_value = float(arx.iloc[0]["artifact_value"])
    mixed_information_range = arx_value - pinned_absolute["minimum"]

    cell_records = json.loads(cells.to_json(orient="records", double_precision=15))
    return {
        "schema_version": 1,
        "card_id": design["card_id"],
        "status": "assistant_generated_reporting_artifact",
        "human_verification_record": "docs/DECISION_LOG.md",
        "analysis_role": design["analysis_role"],
        "design_sha256": design_sha256,
        "source": {
            "matrix_summary_path": design["parent_artifacts"]["matrix_summary"]["path"],
            "matrix_summary_sha256": design["parent_artifacts"]["matrix_summary"]["sha256"],
            "matrix_manifest_sha256": design["parent_artifacts"]["matrix_manifest"]["sha256"],
            "complete_branch_manifest_sha256": design["parent_artifacts"]["complete_branch_manifest"]["sha256"],
            "upstream_matrix_g4": design["upstream_matrix_g4"],
        },
        "comparison_basis": design["comparison_basis"],
        "selected_representative_models": design["selected_representative_models"],
        "cells": cell_records,
        "primary_absolute_axes": {
            "selected_model_range_within_vintage": [
                pinned_absolute,
                august_absolute,
            ],
            "same_model_difference_across_vintages": {
                "direction": "pinned_primary_minus_vintage_20260809",
                "minimum": float(differences.min()),
                "minimum_model": str(
                    cells.loc[differences.idxmin(), "model"]
                ),
                "maximum": float(differences.max()),
                "maximum_model": str(
                    cells.loc[differences.idxmax(), "model"]
                ),
                "average_reported": False,
            },
            "cross_axis_reading": {
                "largest_within_vintage_model_range": float(
                    max(pinned_absolute["range"], august_absolute["range"])
                ),
                "smallest_same_model_vintage_difference": float(differences.min()),
                "smallest_vintage_difference_exceeds_largest_model_range": bool(
                    differences.min()
                    > max(pinned_absolute["range"], august_absolute["range"])
                ),
                "minimum_margin": float(
                    differences.min()
                    - max(pinned_absolute["range"], august_absolute["range"])
                ),
                "ar_primary_vintage_difference": float(
                    primary["pinned_minus_august_per_day"]
                ),
                "ar_primary_difference_minus_pinned_model_range": float(
                    primary["pinned_minus_august_per_day"]
                    - pinned_absolute["range"]
                ),
                "ar_primary_difference_to_pinned_model_range_ratio": float(
                    primary["pinned_minus_august_per_day"]
                    / pinned_absolute["range"]
                ),
            },
        },
        "secondary_normalized_context": {
            "role": design["comparison_basis"]["secondary_denominator_check"]["role"],
            "formula": design["comparison_basis"]["secondary_denominator_check"]["formula"],
            "denominator_scope": design["comparison_basis"]["secondary_denominator_check"]["denominator_scope"],
            "within_vintage_model_ranges": [pinned_normalized, august_normalized],
            "same_model_change_direction": "august_minus_pinned_percentage_points",
            "minimum_same_model_change_percentage_points": float(
                normalized_changes.min()
            ),
            "maximum_same_model_change_percentage_points": float(
                normalized_changes.max()
            ),
            "all_cells_minimum_pct": float(
                cells[[
                    "pinned_shortfall_share_of_counterfactual_pct",
                    "august_shortfall_share_of_counterfactual_pct",
                ]].min().min()
            ),
            "all_cells_maximum_pct": float(
                cells[[
                    "pinned_shortfall_share_of_counterfactual_pct",
                    "august_shortfall_share_of_counterfactual_pct",
                ]].max().max()
            ),
            "not_equivalent_to": design["comparison_basis"]["secondary_denominator_check"]["not_equivalent_to"],
        },
        "mixed_information_challenge": {
            "conditional_arx_route_energy_value_per_day": arx_value,
            "conditional_arx_comparable_same_information": False,
            "mixed_information_pinned_range_per_day": mixed_information_range,
            "mixed_information_range_exceeds_maximum_selected_vintage_difference": bool(
                mixed_information_range > differences.max()
            ),
            "interpretation": (
                "The absolute-scale headline is conditional on the selected "
                "same-observed-local-information rule. ARX uses observed "
                "post-cutoff covariates and answers a different conditional question."
            ),
        },
        "reporting_guards": design["reporting_guards"],
        "axes_are_additive": False,
        "combined_budget_total": None,
        "vintage_averaging": "prohibited_and_not_performed",
    }


def render_markdown(payload: dict) -> str:
    cells = pd.DataFrame(payload["cells"])
    absolute = payload["primary_absolute_axes"]
    normalized = payload["secondary_normalized_context"]
    ranges = absolute["selected_model_range_within_vintage"]
    cross = absolute["cross_axis_reading"]
    challenge = payload["mixed_information_challenge"]

    absolute_rows = [
        "| Selected specification | Pinned | August | Pinned − August |",
        "|---|---:|---:|---:|",
    ]
    normalized_rows = [
        "| Selected specification | Pinned | August | August − pinned |",
        "|---|---:|---:|---:|",
    ]
    for row in cells.itertuples(index=False):
        absolute_rows.append(
            f"| {row.model_label} | {row.pinned_shortfall_per_day:.3f} | "
            f"{row.august_shortfall_per_day:.3f} | "
            f"{row.pinned_minus_august_per_day:.3f} |"
        )
        normalized_rows.append(
            f"| {row.model_label} | "
            f"{row.pinned_shortfall_share_of_counterfactual_pct:.4f}% | "
            f"{row.august_shortfall_share_of_counterfactual_pct:.4f}% | "
            f"{row.august_minus_pinned_percentage_points:+.4f} pp |"
        )

    return "\n".join([
        "# PortWatch sensitivity-budget reporting card",
        "",
        "**Artifact role:** Assistant-generated from the G4-verified matrix. "
        "Human verification state is tracked in `DECISION_LOG.md`, not embedded "
        "in these frozen bytes.",
        "",
        "## Primary absolute-throughput result",
        "",
        *absolute_rows,
        "",
        f"Holding the vintage fixed, the selected four-specification range is "
        f"**{ranges[0]['range']:.3f} lost transits/day** in the pinned vintage "
        f"and **{ranges[1]['range']:.3f}/day** in the August vintage. Holding "
        f"the model fixed, vintage differences span "
        f"**{absolute['same_model_difference_across_vintages']['minimum']:.3f}–"
        f"{absolute['same_model_difference_across_vintages']['maximum']:.3f}/day**. "
        "Every same-model vintage difference exceeds both within-vintage "
        "selected-model ranges.",
        "",
        f"For the locked AR primary, the vintage difference is "
        f"**{cross['ar_primary_vintage_difference']:.3f}/day**, or "
        f"**{cross['ar_primary_difference_to_pinned_model_range_ratio']:.3f}×** "
        "the pinned selected-model range. This ratio names one exact comparison; "
        "it is not a share or general importance measure.",
        "",
        "## Secondary denominator check",
        "",
        *normalized_rows,
        "",
        f"Using each cell's own model counterfactual as denominator, all eight "
        f"shortfall shares lie between **{normalized['all_cells_minimum_pct']:.4f}%** "
        f"and **{normalized['all_cells_maximum_pct']:.4f}%**. Same-model vintage "
        f"changes are only **{normalized['minimum_same_model_change_percentage_points']:.4f}–"
        f"{normalized['maximum_same_model_change_percentage_points']:.4f} percentage "
        "points**. Thus the vintage materially changes the absolute scale while "
        "the model-relative shortfall shares are numerically clustered. Because "
        "the denominators are cell-specific and the ratios sit near a ceiling, "
        "this is descriptive scale context rather than independent robustness "
        "evidence, a third budget component, or the raw observed pre/post decline.",
        "",
        "## Admission-rule challenge",
        "",
        f"The post-treatment-covariate ARX route-energy row is "
        f"{challenge['conditional_arx_route_energy_value_per_day']:.3f}/day. If it "
        f"is mixed into the pinned numeric range, that mixed-information range is "
        f"**{challenge['mixed_information_pinned_range_per_day']:.3f}/day**, which "
        "exceeds the selected-model vintage differences. It remains disclosed but "
        "excluded because it conditions on observed post-cutoff route and energy "
        "covariates. Therefore the headline is explicitly conditional on the "
        "selected same-observed-local-information rule, which was frozen ex post "
        "and unblinded.",
        "",
        "TimesFM and Moirai have no frozen matched 130-day cells. Synthetic "
        "control uses post-period donors and mean-scaled transit-equivalent units. "
        "None enters this selected-model range.",
        "",
        "## Defence-ready answer",
        "",
        "> On the identical 130-day window, the four selected specifications span "
        f"{ranges[0]['range']:.3f} transits/day in the pinned vintage and "
        f"{ranges[1]['range']:.3f} in the August vintage. Holding the model fixed, "
        f"the vintage changes the absolute estimate by "
        f"{absolute['same_model_difference_across_vintages']['minimum']:.3f}–"
        f"{absolute['same_model_difference_across_vintages']['maximum']:.3f}/day, "
        "while model-relative shortfall shares stay numerically near 92.4–93.4%. "
        "I therefore report "
        "absolute magnitude as vintage-sensitive within this selected case, not "
        "as a variance decomposition, ATT, or all-model result.",
        "",
        "## Interpretation guard",
        "",
        "The absolute axes are separate and non-additive. There is no combined "
        "budget total and no vintage average. This is a descriptive case-local "
        "sensitivity analysis of counterfactual forecast shortfalls, not an "
        "uncertainty interval, variance decomposition, ATT, claim that either "
        "vintage is more accurate, or general statement about AIS reliability. "
        "Changing vintage replaces the saved series used for both pre-treatment "
        "training and post-treatment scoring; the comparison is not attributable "
        "only to revised post-treatment counts. "
        "The August raw source-byte archive deposit remains pending.",
        "",
    ])


def make_figure(cells: pd.DataFrame, payload: dict, design: dict) -> None:
    apply_publication_style()
    fig, (ax_shift, ax_range) = plt.subplots(
        1,
        2,
        figsize=(FIGURE_WIDTH_IN, 4.75),
        gridspec_kw={"width_ratios": [1.12, 1.0]},
    )

    x = np.array([0.0, 1.0])
    shift_label_offsets = {
        "seasonal_naive_7d": 0.48,
        "ar_lag1_7": -0.52,
        "chronos2": -0.42,
        "bsts_local_level_weekly": -0.35,
    }
    for row in cells.itertuples(index=False):
        y = np.array([row.pinned_shortfall_per_day, row.august_shortfall_per_day])
        color = MODEL_COLORS[row.model]
        ax_shift.plot(x, y, color=color, linewidth=1.5, marker="o", markersize=4.5)
        ax_shift.text(
            0.04,
            y[0] + 0.25,
            f"{row.pinned_shortfall_per_day:.1f}",
            color=color,
            fontsize=8,
            ha="left",
        )
        ax_shift.text(
            0.96,
            y[1] + shift_label_offsets[row.model],
            f"−{row.pinned_minus_august_per_day:.1f}",
            color=color,
            fontsize=8,
            ha="right",
        )
    ax_shift.set_xticks(x, ["Pinned July", "August"])
    ax_shift.set_xlim(-0.08, 1.08)
    ax_shift.set_ylim(38.5, 56.3)
    ax_shift.set_ylabel("Mean daily counterfactual shortfall")
    ax_shift.set_title("A  Same-model vintage differences")
    style_axes(ax_shift, grid_axis="y")

    ranges = payload["primary_absolute_axes"]["selected_model_range_within_vintage"]
    for y, record, color in zip((1.0, 0.0), ranges, (INCREASE_COLOR, DECREASE_COLOR)):
        ax_range.hlines(y, record["minimum"], record["maximum"], color=color, linewidth=4)
        ax_range.scatter(
            [record["minimum"], record["maximum"]],
            [y, y],
            color=color,
            s=28,
            zorder=3,
        )
        ax_range.text(
            (record["minimum"] + record["maximum"]) / 2.0,
            y + 0.16,
            f"range {record['range']:.3f}/day",
            color=color,
            ha="center",
            fontsize=8.5,
            fontweight="bold",
        )
        ax_range.text(
            record["minimum"],
            y - 0.17,
            f"{record['minimum']:.1f}",
            color=NEUTRAL_DARK,
            ha="center",
            fontsize=8,
        )
        ax_range.text(
            record["maximum"],
            y - 0.17,
            f"{record['maximum']:.1f}",
            color=NEUTRAL_DARK,
            ha="center",
            fontsize=8,
        )
    ax_range.set_yticks([1.0, 0.0], ["Pinned July", "August"])
    ax_range.set_xlim(38.5, 56.3)
    ax_range.set_ylim(-0.5, 1.5)
    ax_range.set_xlabel("Lost transits/day")
    ax_range.set_title("B  Selected four-model ranges")
    style_axes(ax_range, grid_axis="x")

    handles = [
        plt.Line2D([0], [0], color=MODEL_COLORS[model], marker="o", linewidth=1.5)
        for model in design["selected_representative_models"]
    ]
    labels = [MODEL_LABELS[model] for model in design["selected_representative_models"]]
    fig.legend(
        handles,
        labels,
        loc="upper center",
        bbox_to_anchor=(0.5, 0.875),
        ncol=4,
        columnspacing=1.2,
        handlelength=1.8,
    )
    normalized = payload["secondary_normalized_context"]
    fig.suptitle(
        "Absolute Hormuz shortfall is more vintage-sensitive within the selected matrix",
        y=0.985,
        fontsize=12,
        fontweight="bold",
        color=NEUTRAL_DARK,
    )
    fig.text(
        0.5,
        0.105,
        "Secondary scale check (not a budget component): shortfall / model-specific "
        f"counterfactual = {normalized['all_cells_minimum_pct']:.2f}%–"
        f"{normalized['all_cells_maximum_pct']:.2f}%; same-model vintage changes "
        f"{normalized['minimum_same_model_change_percentage_points']:.2f}–"
        f"{normalized['maximum_same_model_change_percentage_points']:.2f} pp.",
        ha="center",
        va="center",
        fontsize=8.2,
        color=NEUTRAL_DARK,
        bbox={"boxstyle": "round,pad=0.35", "facecolor": "#F2F2F2", "edgecolor": "#D0D0D0"},
    )
    fig.text(
        0.5,
        0.027,
        "Separate non-additive axes; selected four-specification range only. "
        "Counterfactual sensitivity, not ATT, variance decomposition, or general AIS claim.",
        ha="center",
        fontsize=7.6,
        color=NEUTRAL_MID,
    )
    fig.subplots_adjust(top=0.78, bottom=0.22, left=0.09, right=0.98, wspace=0.34)
    save_pdf_and_png(
        fig,
        output_path(design, "card_png"),
        pdf_path=output_path(design, "card_pdf"),
        dpi=300,
    )
    plt.close(fig)


def main() -> None:
    design, design_sha256 = load_design()
    summary, admission = load_verified_inputs(design)
    cells = build_cell_table(summary, design)
    payload = build_card_payload(cells, admission, design, design_sha256)

    csv_path = output_path(design, "card_csv")
    json_path = output_path(design, "card_json")
    markdown_path = output_path(design, "card_markdown")
    for path in (csv_path, json_path, markdown_path):
        path.parent.mkdir(parents=True, exist_ok=True)
    cells.to_csv(csv_path, index=False)
    json_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    markdown_path.write_text(render_markdown(payload), encoding="utf-8")
    make_figure(cells, payload, design)

    print("wrote PortWatch sensitivity-budget card")
    for key in ("card_csv", "card_json", "card_markdown", "card_png", "card_pdf"):
        print(f"  {output_path(design, key)}")
    absolute = payload["primary_absolute_axes"]
    normalized = payload["secondary_normalized_context"]
    ranges = absolute["selected_model_range_within_vintage"]
    print("\n=== primary absolute axes (non-additive) ===")
    print(f"pinned selected-model range: {ranges[0]['range']:.6f}/day")
    print(f"August selected-model range: {ranges[1]['range']:.6f}/day")
    print(
        "same-model vintage differences: "
        f"{absolute['same_model_difference_across_vintages']['minimum']:.6f}--"
        f"{absolute['same_model_difference_across_vintages']['maximum']:.6f}/day"
    )
    print("\n=== secondary denominator check ===")
    print(
        f"all cell shortfall shares: {normalized['all_cells_minimum_pct']:.6f}%--"
        f"{normalized['all_cells_maximum_pct']:.6f}%"
    )
    print("Interpretation guard: normalization is context, not a third budget axis.")


if __name__ == "__main__":
    main()
