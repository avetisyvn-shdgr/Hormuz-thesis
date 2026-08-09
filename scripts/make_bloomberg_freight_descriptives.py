"""Create non-causal descriptive tables and figures for LNG freight rates."""
from __future__ import annotations

from datetime import datetime, timezone
import os
from pathlib import Path
import sys

os.environ.setdefault("MPLCONFIGDIR", "/tmp/lngfreight-matplotlib")

import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

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
    fig, axes = plt.subplots(2, 2, figsize=(14, 9), sharex=True)
    fig.suptitle(
        "LNG freight assessments around the 2026 Hormuz disruption",
        fontsize=16,
        fontweight="bold",
        y=0.98,
    )

    ax = axes[0, 0]
    ax.plot(data["week_end"], data["east_spot_usd_per_day_analysis"] / 1000, color=COLORS["east"], label="East of Suez spot")
    ax.plot(data["week_end"], data["west_spot_usd_per_day_analysis"] / 1000, color=COLORS["west"], label="West of Suez spot")
    _event_lines(ax, window)
    ax.set(title="A. Basin spot assessments", ylabel="USD/day (thousands)")
    handles, labels = ax.get_legend_handles_labels()
    unique = dict(zip(labels, handles))
    ax.legend(unique.values(), unique.keys(), frameon=False, fontsize=8, ncol=2)

    ax = axes[0, 1]
    ax.plot(data["week_end"], data["east_minus_west_spot_usd_per_day"] / 1000, color=COLORS["spread"])
    ax.axhline(0, color="#555555", linewidth=0.8)
    _event_lines(ax, window)
    ax.set(title="B. East-minus-West spot spread", ylabel="USD/day (thousands)")

    ax = axes[1, 0]
    ax.plot(data["week_end"], data["one_year_charter_usd_per_day_analysis"] / 1000, color=COLORS["charter"])
    _event_lines(ax, window)
    ax.set(title="C. One-year time-charter assessment", ylabel="USD/day (thousands)")

    ax = axes[1, 1]
    ax.plot(data["week_end"], data["east_spot_pre12_index"], color=COLORS["east"], label="East spot")
    ax.plot(data["week_end"], data["west_spot_pre12_index"], color=COLORS["west"], label="West spot")
    ax.plot(data["week_end"], data["one_year_charter_pre12_index"], color=COLORS["charter"], label="One-year charter")
    ax.axhline(100, color="#777777", linewidth=0.8)
    _event_lines(ax, window)
    ax.set(title="D. Common pre-event index", ylabel="12-week pre-event mean = 100")
    ax.legend(frameon=False, fontsize=8, ncol=2)

    for ax in axes.flat:
        ax.grid(axis="y", alpha=0.2)
        ax.set_xlabel("Assessment week")
    fig.text(
        0.5,
        0.012,
        "Source: provenance-limited structured transcriptions of user-supplied Bloomberg workbooks. "
        "Missing weeks are not filled; flagged West zeros are masked only in analysis columns. "
        "Descriptive market evidence—no causal effect or ATT is claimed.",
        ha="center",
        fontsize=8.5,
        color="#444444",
    )
    fig.tight_layout(rect=[0, 0.04, 1, 0.95])
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
