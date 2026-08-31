"""Render the Chapter 4 research-design and evidence-hierarchy figure.

The diagram is a view of the implemented analysis, not a hand-maintained
manuscript illustration.  Dates, horizon length, primary model, and the number
of horizon-matched reference blocks are read from the frozen configuration and
processed admission/frontier artifacts at run time.  Any disagreement between
those sources stops rendering instead of silently producing an outdated figure.
"""
from __future__ import annotations

import csv
import os
import sys
from dataclasses import dataclass
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/hormuz_throughput-matplotlib")

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from figure_style import (  # noqa: E402
    ACCENT_BLUE,
    ACCENT_ORANGE,
    GRID_COLOR,
    NEUTRAL_DARK,
    NEUTRAL_MID,
    SECONDARY_BLUE,
    THESIS_TEXTWIDTH_IN,
    apply_publication_style,
    save_pdf_and_png,
)
from hormuz_throughput import config  # noqa: E402


STEM = "research_design_evidence_hierarchy"


@dataclass(frozen=True)
class DesignFacts:
    analysis_start: str
    cutoff: str
    scoring_end: str
    horizon_days: int
    primary_model: str
    reference_blocks: int


def _single_csv_row(path: Path, predicate) -> dict[str, str]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = [row for row in csv.DictReader(handle) if predicate(row)]
    if len(rows) != 1:
        raise ValueError(f"Expected one matching row in {path}, found {len(rows)}.")
    return rows[0]


def _design_facts() -> DesignFacts:
    settings = config.settings()
    study = settings["study_window"]
    model_cfg = settings["modeling"]["working_specification"]

    admission = _single_csv_row(
        ROOT / "data" / "processed" / "model_admission_protocol.csv",
        lambda row: row["model"] == model_cfg["primary_estimator"],
    )
    horizon = int(admission["expected_scored_days"])
    frontier = _single_csv_row(
        ROOT / "data" / "processed" / "horizon_frontier_summary.csv",
        lambda row: (
            row["origin_rule"] == "forward_anchored_direct"
            and row["role"] == "primary"
            and int(row["horizon_days"]) == horizon
            and row["level"] == "0.8"
        ),
    )

    expected = {
        "analysis_start": study["full_start"],
        "cutoff": study["primary_treatment_cutoff"],
        "scoring_end": study["full_end"],
    }
    observed = {
        "analysis_start": admission["analysis_start"],
        "cutoff": admission["locked_cutoff"],
        "scoring_end": admission["scoring_end"],
    }
    if observed != expected:
        raise ValueError(
            "Settings and model-admission dates disagree: "
            f"settings={expected}, admission={observed}."
        )
    if int(frontier["n_reference_blocks"]) < 1:
        raise ValueError("The primary horizon frontier has no reference blocks.")

    return DesignFacts(
        analysis_start=expected["analysis_start"],
        cutoff=expected["cutoff"],
        scoring_end=expected["scoring_end"],
        horizon_days=horizon,
        primary_model=admission["model"],
        reference_blocks=int(frontier["n_reference_blocks"]),
    )


def _date_label(value: str) -> str:
    year, month, day = value.split("-")
    months = (
        "Jan", "Feb", "Mar", "Apr", "May", "Jun",
        "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
    )
    return f"{int(day)} {months[int(month) - 1]} {year}"


def _model_label(model: str) -> str:
    if model == "ar_lag1_7":
        return "recursive AR(1,7)"
    return model.replace("_", " ")


def _box(
    ax: plt.Axes,
    x: float,
    y: float,
    width: float,
    height: float,
    text: str,
    *,
    face: str,
    edge: str,
    fontsize: float = 8.7,
    weight: str = "normal",
    text_color: str = NEUTRAL_DARK,
    linewidth: float = 0.85,
) -> None:
    patch = FancyBboxPatch(
        (x, y),
        width,
        height,
        boxstyle="round,pad=0.008,rounding_size=0.012",
        facecolor=face,
        edgecolor=edge,
        linewidth=linewidth,
        transform=ax.transAxes,
        clip_on=False,
        zorder=2,
    )
    ax.add_patch(patch)
    ax.text(
        x + width / 2,
        y + height / 2,
        text,
        transform=ax.transAxes,
        ha="center",
        va="center",
        fontsize=fontsize,
        fontweight=weight,
        color=text_color,
        linespacing=1.22,
        zorder=3,
    )


def _arrow(
    ax: plt.Axes,
    start: tuple[float, float],
    end: tuple[float, float],
    *,
    color: str = NEUTRAL_MID,
    connectionstyle: str = "arc3",
) -> None:
    arrow = FancyArrowPatch(
        start,
        end,
        arrowstyle="-|>",
        mutation_scale=8.5,
        linewidth=0.8,
        color=color,
        connectionstyle=connectionstyle,
        transform=ax.transAxes,
        clip_on=False,
        zorder=1,
    )
    ax.add_patch(arrow)


def render() -> tuple[Path, Path]:
    facts = _design_facts()
    apply_publication_style()

    primary_face = "#EEF5FA"
    support_face = "#FFF4EC"
    neutral_face = "#F4F4F2"

    fig, ax = plt.subplots(figsize=(THESIS_TEXTWIDTH_IN, 5.85))
    fig.subplots_adjust(left=0.015, right=0.985, bottom=0.015, top=0.985)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    ax.text(
        0.25, 0.965, "A  Primary counterfactual",
        transform=ax.transAxes, ha="center", va="top",
        fontsize=10.2, fontweight="semibold", color=SECONDARY_BLUE,
    )
    ax.text(
        0.75, 0.965, "B  Descriptive adaptation",
        transform=ax.transAxes, ha="center", va="top",
        fontsize=10.2, fontweight="semibold", color=ACCENT_ORANGE,
    )
    ax.plot(
        [0.50, 0.50], [0.245, 0.925],
        transform=ax.transAxes, color=GRID_COLOR, linewidth=0.8,
        linestyle=(0, (2, 3)), zorder=0,
    )

    _box(
        ax, 0.035, 0.815, 0.43, 0.105,
        "Primary measurement\n"
        "PortWatch Hormuz tanker transits\n"
        f"{_date_label(facts.analysis_start)}–{_date_label(facts.scoring_end)}",
        face=primary_face, edge=SECONDARY_BLUE,
    )
    _box(
        ax, 0.535, 0.815, 0.43, 0.105,
        "Supporting measurements\n"
        "WTO index • GFW events and route model\n"
        "corridor counts • customs portfolios\n"
        "source-specific units and windows",
        face=support_face, edge=ACCENT_ORANGE, fontsize=8.4,
    )

    _arrow(ax, (0.25, 0.815), (0.25, 0.755), color=SECONDARY_BLUE)
    _arrow(ax, (0.75, 0.815), (0.75, 0.755), color=ACCENT_ORANGE)

    _box(
        ax, 0.035, 0.625, 0.43, 0.13,
        "Leakage-controlled forecast\n"
        f"train strictly before {_date_label(facts.cutoff)}\n"
        f"{_model_label(facts.primary_model)} • {facts.horizon_days}-day recursive path\n"
        r"daily and cumulative shortfall:  $\widehat{y}^{0}_{t}-y_t$",
        face=primary_face, edge=SECONDARY_BLUE, fontsize=8.55,
    )
    _box(
        ax, 0.535, 0.625, 0.43, 0.13,
        "Within-layer adaptation metrics\n"
        "LNG activity • inferred terminal sequences\n"
        "nominal capacity-distance\n"
        "corridor deviations\n"
        "importer-origin portfolios",
        face=support_face, edge=ACCENT_ORANGE, fontsize=8.2,
    )

    _arrow(ax, (0.25, 0.625), (0.25, 0.565), color=SECONDARY_BLUE)
    _arrow(ax, (0.75, 0.625), (0.75, 0.565), color=ACCENT_ORANGE)

    _box(
        ax, 0.035, 0.455, 0.43, 0.11,
        "Chronological validation and uncertainty\n"
        "30-day rolling-origin folds\n"
        f"+ {facts.reference_blocks} disjoint {facts.horizon_days}-day reference blocks\n"
        "rank and conformal calibration",
        face=neutral_face, edge=SECONDARY_BLUE, fontsize=8.2,
    )
    _box(
        ax, 0.535, 0.455, 0.43, 0.11,
        "Comparable calendars, separate scales\n"
        "matched windows within each source\n"
        "no pooling of non-equivalent units",
        face=neutral_face, edge=ACCENT_ORANGE, fontsize=8.4,
    )

    _arrow(ax, (0.25, 0.455), (0.25, 0.395), color=SECONDARY_BLUE)
    _arrow(ax, (0.75, 0.455), (0.75, 0.395), color=ACCENT_ORANGE)

    _box(
        ax, 0.035, 0.285, 0.43, 0.11,
        "Falsification and corroboration\n"
        "temporal and spatial placebos\n"
        "synthetic control • model and window checks\n"
        "capacity and vintage sensitivity",
        face=neutral_face, edge=SECONDARY_BLUE, fontsize=8.4,
    )
    _box(
        ax, 0.535, 0.285, 0.43, 0.11,
        "Triangulation by direction and timing\n"
        "contraction, substitution, and reallocation\n"
        "disagreement retained as evidence",
        face=neutral_face, edge=ACCENT_ORANGE, fontsize=8.4,
    )

    _arrow(
        ax, (0.25, 0.285), (0.40, 0.215),
        color=SECONDARY_BLUE, connectionstyle="arc3,rad=-0.04",
    )
    _arrow(
        ax, (0.75, 0.285), (0.60, 0.215),
        color=ACCENT_ORANGE, connectionstyle="arc3,rad=0.04",
    )

    _box(
        ax, 0.055, 0.065, 0.89, 0.15,
        "Permitted synthesis\n"
        "Disruption-associated counterfactual shortfall in observable tanker throughput\n"
        "+ separately bounded evidence on LNG and shipping-network adaptation\n"
        "Not a causal effect, physical census, freight-rate estimate, or identified cargo replacement",
        face="#EDEFF1", edge=NEUTRAL_DARK, fontsize=8.7, weight="semibold",
        linewidth=1.0,
    )

    output = config.path("figures") / f"{STEM}.png"
    paths = save_pdf_and_png(fig, output, dpi=300)
    plt.close(fig)
    print(f"wrote {paths[0]}")
    print(f"wrote {paths[1]}")
    return paths


def main() -> int:
    render()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
