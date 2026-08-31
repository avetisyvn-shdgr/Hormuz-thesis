"""Run pre-treatment-selected weekly freight counterfactual forecasts."""
from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys

os.environ.setdefault("MPLCONFIGDIR", "/tmp/hormuz_throughput-matplotlib")

import matplotlib  # noqa: E402
matplotlib.use("Agg")
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
from hormuz_throughput import config  # noqa: E402
from hormuz_throughput.bloomberg_market import ANALYSIS_COLUMNS  # noqa: E402
from hormuz_throughput.freight_counterfactual import (  # noqa: E402
    fit_freight_counterfactuals,
)


LABELS = {
    "east_spot": "East of Suez spot",
    "west_spot": "West of Suez spot",
    "one_year_charter": "One-year time charter",
}
COLORS = {"observed": "#2F6690", "forecast": "#D17A22", "interval": "#F3C98B"}
PDF_METADATA = {
    "Creator": "hormuz_throughput reproducible pipeline",
    "CreationDate": datetime(2026, 2, 28, tzinfo=timezone.utc),
    "ModDate": datetime(2026, 2, 28, tzinfo=timezone.utc),
}


def _plot(weekly: pd.DataFrame, cutoff: str) -> None:
    apply_publication_style()
    fig, axes = plt.subplots(3, 1, figsize=(FIGURE_WIDTH_IN, 6.2), sharex=True)
    for ax, (series, group) in zip(axes, weekly.groupby("series", sort=False)):
        group = group.sort_values("week_end")
        ax.fill_between(
            group["week_end"],
            group["lower_90_usd_per_day"] / 1000,
            group["upper_90_usd_per_day"] / 1000,
            color=COLORS["interval"],
            alpha=0.45,
            linewidth=0,
            label="90% pointwise conformal interval",
        )
        ax.plot(
            group["week_end"],
            group["observed_usd_per_day"] / 1000,
            color=COLORS["observed"],
            marker="o",
            markersize=2.6,
            linewidth=1.2,
            label="Observed assessment",
        )
        ax.plot(
            group["week_end"],
            group["counterfactual_usd_per_day"] / 1000,
            color=COLORS["forecast"],
            linestyle="--",
            linewidth=1.3,
            label=f"Counterfactual ({group['selected_model'].iloc[0]})",
        )
        ax.axvline(
            pd.Timestamp(cutoff),
            color="#B44C43",
            linewidth=1.1,
            label=f"Treatment cutoff {cutoff}",
        )
        ax.set_title(LABELS[series], loc="left", pad=4)
        ax.set_ylabel("USD/day (thousands)")
        style_axes(ax, grid_axis="y")
    axes[-1].set_xlabel("Assessment week")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(
        handles,
        labels,
        loc="lower center",
        bbox_to_anchor=(0.5, 0.045),
        ncol=2,
        frameon=False,
    )
    fig.text(
        0.01,
        0.005,
        "Models and interval radius selected using pre-treatment rolling-origin "
        "validation only. Post forecasts are recursive and do not use observed "
        "post-event lags. Forecast deviations are supplementary, not ATT estimates.",
        ha="left",
        fontsize=7.0,
        color=NEUTRAL_MID,
    )
    fig.tight_layout(rect=[0, 0.115, 1, 1])
    fig.savefig(config.path("lng_freight_counterfactual_png"), dpi=180, bbox_inches="tight")
    fig.savefig(
        config.path("lng_freight_counterfactual_pdf"),
        bbox_inches="tight",
        metadata=PDF_METADATA,
    )
    plt.close(fig)


def main() -> None:
    window = config.settings()["study_window"]
    data = pd.read_csv(config.path("lng_freight_descriptive_weekly_csv"))
    first_post = pd.date_range(
        pd.Timestamp(window["primary_treatment_cutoff"]) + pd.Timedelta(days=1),
        periods=1,
        freq="W-FRI",
    )[0]
    scores, weekly, summary, placebos, manifest = fit_freight_counterfactuals(
        data,
        first_post_week=first_post.date().isoformat(),
        series_columns=ANALYSIS_COLUMNS,
    )
    scores.to_csv(config.path("lng_freight_validation_scores_csv"), index=False)
    weekly.to_csv(
        config.path("lng_freight_counterfactual_weekly_csv"),
        index=False,
        date_format="%Y-%m-%d",
    )
    summary.to_csv(config.path("lng_freight_counterfactual_summary_csv"), index=False)
    placebos.to_csv(config.path("lng_freight_time_placebos_csv"), index=False)
    config.path("lng_freight_counterfactual_manifest_json").write_text(
        f"{json.dumps(manifest, indent=2)}\n", encoding="utf-8"
    )
    _plot(weekly, window["primary_treatment_cutoff"])
    print(config.path("lng_freight_validation_scores_csv"))
    print(config.path("lng_freight_counterfactual_weekly_csv"))
    print(config.path("lng_freight_counterfactual_summary_csv"))
    print(config.path("lng_freight_time_placebos_csv"))
    print(config.path("lng_freight_counterfactual_png"))


if __name__ == "__main__":
    main()
