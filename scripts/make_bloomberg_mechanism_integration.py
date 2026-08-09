"""Create the synchronized physical/monetary/context evidence panel."""
from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys

os.environ.setdefault("MPLCONFIGDIR", "/tmp/lngfreight-matplotlib")

import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import matplotlib.dates as mdates  # noqa: E402
import pandas as pd  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lngfreight import config  # noqa: E402
from lngfreight.freight_integration import (  # noqa: E402
    build_freight_mechanism_integration,
)

PDF_METADATA = {
    "Creator": "lngfreight reproducible pipeline",
    "CreationDate": datetime(2026, 2, 28, tzinfo=timezone.utc),
    "ModDate": datetime(2026, 2, 28, tzinfo=timezone.utc),
}


def _plot(panel: pd.DataFrame, cutoff: str) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(14, 9), sharex=True)
    fig.suptitle(
        "Synchronized physical and LNG freight-market evidence",
        fontsize=16,
        fontweight="bold",
        y=0.98,
    )
    ax = axes[0, 0]
    ax.plot(panel["week_end"], panel["portwatch_tanker_transits_observed_daily_mean"], color="#2F6690", label="Observed")
    ax.plot(panel["week_end"], panel["portwatch_tanker_transits_counterfactual_daily_mean"], color="#D17A22", linestyle="--", label="Counterfactual")
    ax.set(title="A. PortWatch tanker throughput", ylabel="Mean daily transits")
    ax.legend(frameon=False)

    ax = axes[0, 1]
    ax.plot(panel["week_end"], panel["wto_lng_outbound_index_observed_daily_mean"], color="#2F6690", label="Observed")
    ax.plot(panel["week_end"], panel["wto_lng_outbound_index_counterfactual_daily_mean"], color="#D17A22", linestyle="--", label="Counterfactual")
    ax.set(title="B. WTO LNG outbound-volume index", ylabel="Index (2025 mean = 100)")
    ax.legend(frameon=False)

    ax = axes[1, 0]
    for series, color, label in [
        ("east_spot", "#2F6690", "East spot"),
        ("west_spot", "#D17A22", "West spot"),
        ("one_year_charter", "#5B8E7D", "One-year charter"),
    ]:
        ax.plot(panel["week_end"], panel[f"{series}_deviation_usd_per_day"] / 1000, color=color, label=label)
    ax.axhline(0, color="#555555", linewidth=0.8)
    ax.set(title="C. Freight forecast deviations", ylabel="Observed minus counterfactual\n(USD/day, thousands)")
    ax.legend(frameon=False)

    ax = axes[1, 1]
    ax.plot(panel["week_end"], panel["ttf_eur_per_mwh_pre_zscore"], color="#2F6690", label="TTF")
    ax.plot(panel["week_end"], panel["vlsfo_singapore_usd_per_metric_tonne_pre_zscore"], color="#D17A22", label="VLSFO")
    ax.axhline(0, color="#555555", linewidth=0.8)
    ax.set(title="D. Market context", ylabel="Pre-event standard deviations")
    ax.legend(frameon=False)

    for ax in axes.flat:
        ax.axvline(pd.Timestamp(cutoff), color="#B44C43", linewidth=1.0)
        ax.grid(axis="y", alpha=0.2)
        ax.set_xlabel("Week ending Friday")
        ax.xaxis.set_major_locator(mdates.MonthLocator())
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
    fig.text(
        0.5,
        0.012,
        "Layers are synchronized for triangulation, not pooled into one estimator. PortWatch is the working primary; freight assessments are secondary; TTF and VLSFO are context. No mediation or freight ATT is identified.",
        ha="center",
        fontsize=8.5,
        color="#444444",
    )
    fig.tight_layout(rect=[0, 0.04, 1, 0.95])
    fig.savefig(config.path("freight_mechanism_png"), dpi=180, bbox_inches="tight")
    fig.savefig(
        config.path("freight_mechanism_pdf"),
        bbox_inches="tight",
        metadata=PDF_METADATA,
    )
    plt.close(fig)


def main() -> None:
    window = config.settings()["study_window"]
    first_post = pd.date_range(
        pd.Timestamp(window["primary_treatment_cutoff"]) + pd.Timedelta(days=1),
        periods=1,
        freq="W-FRI",
    )[0]
    portwatch = pd.read_csv(config.ROOT / "data/processed/counterfactual_intervals_daily.csv")
    wto = pd.read_csv(config.ROOT / "data/processed/lng_index_counterfactual_daily.csv")
    freight = pd.read_csv(config.path("lng_freight_counterfactual_weekly_csv"))
    context = pd.read_csv(config.path("freight_market_context_csv"))
    panel, summary, manifest = build_freight_mechanism_integration(
        portwatch,
        wto,
        freight,
        context,
        first_post_week=first_post.date().isoformat(),
    )
    panel.to_csv(config.path("freight_mechanism_weekly_csv"), index=False, date_format="%Y-%m-%d")
    summary.to_csv(config.path("freight_mechanism_summary_csv"), index=False)
    config.path("freight_mechanism_manifest_json").write_text(
        f"{json.dumps(manifest, indent=2)}\n", encoding="utf-8"
    )
    _plot(panel, window["primary_treatment_cutoff"])
    print(config.path("freight_mechanism_weekly_csv"))
    print(config.path("freight_mechanism_summary_csv"))
    print(config.path("freight_mechanism_png"))


if __name__ == "__main__":
    main()
