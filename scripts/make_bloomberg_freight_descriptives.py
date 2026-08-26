"""Create non-causal descriptive tables and figures for LNG freight rates."""
from __future__ import annotations

from datetime import datetime, timezone
import os
from pathlib import Path
import sys

os.environ.setdefault("MPLCONFIGDIR", "/tmp/lngfreight-matplotlib")

import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.dates as mdates  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from figure_style import (  # noqa: E402
    FIGURE_WIDTH_IN,
    NEUTRAL_MID,
    apply_publication_style,
    style_axes,
)
from lngfreight import config  # noqa: E402
from lngfreight.bloomberg_market import descriptive_freight_layer  # noqa: E402


COLORS = {
    "east": "#2F6690",
    "west": "#D17A22",
    "charter": "#5B8E7D",
    "spread": "#7A5195",
}
PDF_METADATA = {
    "Creator": "lngfreight reproducible pipeline",
    "CreationDate": datetime(2026, 2, 28, tzinfo=timezone.utc),
    "ModDate": datetime(2026, 2, 28, tzinfo=timezone.utc),
}


def _event_lines(ax: plt.Axes, window: dict) -> None:
    events = [
        ("Operational cutoff", window["primary_treatment_cutoff"], "#B44C43", "-"),
        ("Closure confirmation", window["treatment_candidates"]["closure_declaration"], "#666666", "--"),
        ("Force majeure", window["treatment_candidates"]["force_majeure"], "#222222", ":"),
    ]
    for label, date, color, style in events:
        ax.axvline(pd.Timestamp(date), color=color, linestyle=style, linewidth=1.2, label=label)


def _plot(data: pd.DataFrame, window: dict) -> None:
    apply_publication_style()
    data = data.copy()
    data["week_end"] = pd.to_datetime(data["week_end"])
    fig, axes = plt.subplots(2, 2, figsize=(FIGURE_WIDTH_IN, 5.2), sharex=True)
    # No in-figure headline title: the LaTeX caption carries it in the thesis.

    ax = axes[0, 0]
    ax.plot(data["week_end"], data["east_spot_usd_per_day_analysis"] / 1000, color=COLORS["east"], linewidth=1.1, label="East of Suez spot")
    ax.plot(data["week_end"], data["west_spot_usd_per_day_analysis"] / 1000, color=COLORS["west"], linewidth=1.1, label="West of Suez spot")
    _event_lines(ax, window)
    ax.set_title("A. Basin spot assessments", loc="left", pad=4)
    ax.set_ylabel("USD/day (thousands)")

    ax = axes[0, 1]
    ax.plot(data["week_end"], data["east_minus_west_spot_usd_per_day"] / 1000, color=COLORS["spread"], linewidth=1.1, label="East-minus-West spread")
    ax.axhline(0, color="#555555", linewidth=0.8)
    _event_lines(ax, window)
    ax.set_title("B. East-minus-West spot spread", loc="left", pad=4)
    ax.set_ylabel("USD/day (thousands)")

    ax = axes[1, 0]
    ax.plot(data["week_end"], data["one_year_charter_usd_per_day_analysis"] / 1000, color=COLORS["charter"], linewidth=1.1, label="One-year time charter")
    _event_lines(ax, window)
    ax.set_title("C. One-year time-charter assessment", loc="left", pad=4)
    ax.set_ylabel("USD/day (thousands)")

    ax = axes[1, 1]
    ax.plot(data["week_end"], data["east_spot_pre12_index"], color=COLORS["east"], linewidth=1.1)
    ax.plot(data["week_end"], data["west_spot_pre12_index"], color=COLORS["west"], linewidth=1.1)
    ax.plot(data["week_end"], data["one_year_charter_pre12_index"], color=COLORS["charter"], linewidth=1.1)
    ax.axhline(100, color="#777777", linewidth=0.8)
    _event_lines(ax, window)
    ax.set_title("D. Common pre-event index", loc="left", pad=4)
    ax.set_ylabel("12-week pre-event mean = 100")

    for ax in axes.flat:
        style_axes(ax, grid_axis="y")
        ax.xaxis.set_major_locator(mdates.YearLocator())
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    for ax in axes[1]:
        ax.set_xlabel("Assessment week")

    # One shared legend: series colors from panels A-C, event lines once.
    handles: list = []
    labels: list = []
    for ax in (axes[0, 0], axes[0, 1], axes[1, 0]):
        for handle, label in zip(*ax.get_legend_handles_labels()):
            if label not in labels:
                handles.append(handle)
                labels.append(label)
    fig.legend(
        handles,
        labels,
        loc="lower center",
        bbox_to_anchor=(0.5, 0.035),
        ncol=4,
        frameon=False,
        fontsize=8.0,
        columnspacing=1.1,
    )
    fig.text(
        0.01,
        0.004,
        "Source: provenance-limited structured transcriptions of user-supplied "
        "Bloomberg workbooks. Missing weeks are not filled; flagged West zeros are "
        "masked only in analysis columns. Descriptive evidence; no causal effect "
        "or ATT is claimed.",
        ha="left",
        fontsize=6.8,
        color=NEUTRAL_MID,
    )
    fig.tight_layout(rect=[0, 0.14, 1, 1])
    png = config.path("lng_freight_descriptive_png")
    pdf = config.path("lng_freight_descriptive_pdf")
    fig.savefig(png, dpi=180, bbox_inches="tight")
    fig.savefig(pdf, bbox_inches="tight", metadata=PDF_METADATA)
    plt.close(fig)


def main() -> None:
    window = config.settings()["study_window"]
    panel = pd.read_csv(config.path("lng_freight_weekly_panel_csv"))
    first_post_week = pd.date_range(
        pd.Timestamp(window["primary_treatment_cutoff"]) + pd.Timedelta(days=1),
        periods=1,
        freq="W-FRI",
    )[0]
    data, summary = descriptive_freight_layer(
        panel, first_post_week=first_post_week.date().isoformat()
    )
    data.to_csv(
        config.path("lng_freight_descriptive_weekly_csv"),
        index=False,
        date_format="%Y-%m-%d",
    )
    summary.to_csv(config.path("lng_freight_descriptive_summary_csv"), index=False)
    _plot(data, window)
    print(config.path("lng_freight_descriptive_weekly_csv"))
    print(config.path("lng_freight_descriptive_summary_csv"))
    print(config.path("lng_freight_descriptive_png"))


if __name__ == "__main__":
    main()
