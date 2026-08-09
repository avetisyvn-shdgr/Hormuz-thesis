"""Build and plot the separate TTF/VLSFO market-context layer."""
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
import pandas as pd  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lngfreight import config  # noqa: E402
from lngfreight.bloomberg_admission import load_manifest  # noqa: E402
from lngfreight.bloomberg_market import (  # noqa: E402
    build_market_context_panel,
    load_market_context,
)

PDF_METADATA = {
    "Creator": "lngfreight reproducible pipeline",
    "CreationDate": datetime(2026, 2, 28, tzinfo=timezone.utc),
    "ModDate": datetime(2026, 2, 28, tzinfo=timezone.utc),
}


def _plot(panel: pd.DataFrame, cutoff: str) -> None:
    fig, axes = plt.subplots(3, 1, figsize=(12, 10), sharex=True)
    fig.suptitle("Gas and bunker-price context for LNG freight", fontsize=16, fontweight="bold", y=0.98)
    axes[0].plot(panel["date"], panel["ttf_eur_per_mwh"], color="#2F6690")
    axes[0].set(title="A. Netherlands TTF day-ahead", ylabel="EUR/MWh")
    axes[1].plot(panel["date"], panel["vlsfo_singapore_usd_per_metric_tonne"], color="#D17A22")
    axes[1].set(title="B. Singapore VLSFO", ylabel="USD/metric tonne")
    axes[2].plot(panel["date"], panel["ttf_eur_per_mwh_pre_zscore"], color="#2F6690", label="TTF")
    axes[2].plot(panel["date"], panel["vlsfo_singapore_usd_per_metric_tonne_pre_zscore"], color="#D17A22", label="VLSFO")
    axes[2].axhline(0, color="#666666", linewidth=0.8)
    axes[2].set(title="C. Pre-event standardized context", ylabel="Pre-event standard deviations")
    axes[2].legend(frameon=False)
    for ax in axes:
        ax.axvline(pd.Timestamp(cutoff), color="#B44C43", linewidth=1.1, label="Operational cutoff")
        ax.grid(axis="y", alpha=0.2)
    axes[-1].set_xlabel("Date")
    fig.text(
        0.5,
        0.012,
        "Context only: TTF and VLSFO are not controls in the headline freight forecasts and may reflect common shocks or mediating paths. Missing business days are not filled.",
        ha="center",
        fontsize=8.5,
        color="#444444",
    )
    fig.tight_layout(rect=[0, 0.04, 1, 0.95])
    fig.savefig(config.path("freight_market_context_png"), dpi=180, bbox_inches="tight")
    fig.savefig(
        config.path("freight_market_context_pdf"),
        bbox_inches="tight",
        metadata=PDF_METADATA,
    )
    plt.close(fig)


def main() -> None:
    window = config.settings()["study_window"]
    manifest = load_manifest(config.ROOT / "config/bloomberg_exports.yaml")
    frames = load_market_context(window["full_start"], window["full_end"])
    panel, quality, output_manifest = build_market_context_panel(
        frames,
        manifest,
        study_start=window["full_start"],
        study_end=window["full_end"],
        treatment_cutoff=window["primary_treatment_cutoff"],
    )
    panel.to_csv(config.path("freight_market_context_csv"), index=False, date_format="%Y-%m-%d")
    quality.to_csv(config.path("freight_market_context_quality_csv"), index=False)
    config.path("freight_market_context_manifest_json").write_text(
        f"{json.dumps(output_manifest, indent=2)}\n", encoding="utf-8"
    )
    _plot(panel, window["primary_treatment_cutoff"])
    print(config.path("freight_market_context_csv"))
    print(config.path("freight_market_context_quality_csv"))
    print(config.path("freight_market_context_png"))


if __name__ == "__main__":
    main()
