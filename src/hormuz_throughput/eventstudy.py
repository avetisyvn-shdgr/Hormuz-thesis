"""Layer-1 DESCRIPTIVE event-study figures.

These figures document the 2026 Strait of Hormuz disruption in the free panel
and motivate the research design. They are descriptive only:

  * The event-study figure marks only the locked operational-onset cutoff. Later
    audited milestones remain in the chronology rather than being compressed
    into an unreadable cluster of vertical lines.
  * Hormuz-vs-Panama is a treated-vs-untreated CONTRAST (the visual seed of the
    later donor / synthetic-control design), NOT an estimated effect.
  * The energy-price panel shows CO-MOVEMENT, not a causal response; forward-
    filled (weekend/holiday) price points are marked hollow so the reader is not
    misled into reading weekend "signal" that is really carried-forward value.

Nothing here estimates anything. Pure plotting from the aligned panel.
"""
from __future__ import annotations

from datetime import datetime, timezone

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd

from . import config

_STYLE = {
    "figure.figsize": (7.0, 4.3),
    "figure.dpi": 130,
    "savefig.dpi": 200,
    "font.family": "serif",
    "font.serif": ["P052", "URW Palladio L", "Palatino", "TeX Gyre Pagella", "DejaVu Serif"],
    "font.size": 10,
    "axes.titlesize": 11,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "grid.alpha": 0.25,
    "legend.frameon": False,
}
_TREAT_COLORS = ["#c1121f", "#d4762a", "#6a4c93", "#118ab2"]
_OBSERVED_TREATED = "#B2182B"
_COMPARISON_SERIES = "#3F3F3F"
_EVENT_MARKER = "#000000"
_THESIS_TEXTWIDTH_IN = 418.25555 / 72.27
_SOURCE = "Source: IMF PortWatch (AIS-derived) & EIA. Free-data panel."
_PDF_METADATA = {
    "Creator": "Hormuz tanker-throughput reproducibility pipeline",
    "CreationDate": datetime(2026, 2, 28, tzinfo=timezone.utc),
    "ModDate": datetime(2026, 2, 28, tzinfo=timezone.utc),
}


def _candidates() -> dict[str, pd.Timestamp]:
    raw = config.settings()["study_window"]["treatment_candidates"]
    return {k: pd.Timestamp(v) for k, v in raw.items()}


def _mark_treatments(ax, *, label: bool = True) -> None:
    """Draw the configured event milestones as dashed vertical lines."""
    for (name, ts), color in zip(_candidates().items(), _TREAT_COLORS):
        ax.axvline(ts, ls="--", lw=1.0, color=color, alpha=0.9,
                   label=f"{name} ({ts.date()})" if label else None)


def _mark_primary_cutoff(ax) -> None:
    """Draw only the locked operational onset used by the primary model."""
    name, ts = next(iter(_candidates().items()))
    ax.axvline(
        ts,
        ls=(0, (3.0, 2.0)),
        lw=1.2,
        color=_EVENT_MARKER,
        alpha=0.95,
        label=f"Locked operational onset ({ts.date()})",
    )


def _footnote(fig, extra: str = "") -> None:
    note = _SOURCE + ("  " + extra if extra else "")
    fig.text(0.01, 0.005, note, fontsize=7, color="#555", ha="left")


def fig_chokepoint_event_study(panel: pd.DataFrame) -> plt.Figure:
    with plt.rc_context(_STYLE):
        fig, (ax_full, ax_zoom) = plt.subplots(
            2, 1, figsize=(_THESIS_TEXTWIDTH_IN, 5.15), height_ratios=[1, 1])

        for ax in (ax_full, ax_zoom):
            ax.plot(panel.index, panel["hormuz_tanker_transits"],
                    color=_OBSERVED_TREATED, lw=1.1,
                    label="Hormuz (observed treated)")
            ax.plot(panel.index, panel["panama_tanker_transits"],
                    color=_COMPARISON_SERIES, lw=1.1,
                    label="Panama (unaffected comparator)")
            ax.set_ylabel("Tanker transits / day")

        ax_full.set_title("Daily tanker transits: full study window", loc="left")
        ax_full.xaxis.set_major_locator(mdates.YearLocator())
        ax_full.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
        ax_full.legend(loc="upper left", ncol=2, fontsize=8)

        zoom = panel.loc["2026-01-01":]
        ax_zoom.set_xlim(zoom.index.min(), zoom.index.max())
        ax_zoom.set_ylim(0, max(zoom[["hormuz_tanker_transits",
                                      "panama_tanker_transits"]].max()) * 1.1)
        ax_zoom.xaxis.set_major_locator(mdates.MonthLocator())
        ax_zoom.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
        _mark_primary_cutoff(ax_zoom)
        ax_zoom.set_title("Zoom: January to June 2026, locked operational onset", loc="left")
        ax_zoom.legend(loc="upper right", fontsize=7)

        fig.suptitle("",
                     fontsize=12, y=0.99)
        _footnote(
            fig,
            "\nShared absolute scale preserves transit units; Panama variation is compressed\n"
            "by its lower level. Locked onset: 2026-02-28. Later verified milestones:\n"
            "docs/EVENT_CHRONOLOGY.md.",
        )
        fig.tight_layout(rect=(0, 0.10, 1, 0.98))
    return fig


def fig_hormuz_robustness(panel: pd.DataFrame) -> plt.Figure:
    cut = min(_candidates().values())
    pre = panel.loc[:cut - pd.Timedelta(days=1)]
    norm = pd.DataFrame({
        "Transit count": panel["hormuz_tanker_transits"]
        / pre["hormuz_tanker_transits"].mean() * 100,
        "Deadweight capacity": panel["hormuz_tanker_capacity"]
        / pre["hormuz_tanker_capacity"].mean() * 100,
    }).loc["2025-10-01":]

    with plt.rc_context(_STYLE):
        fig, ax = plt.subplots()
        ax.plot(norm.index, norm["Transit count"], color="#c1121f", lw=1.2,
                label="Transit count")
        ax.plot(norm.index, norm["Deadweight capacity"], color="#457b9d",
                lw=1.2, label="Deadweight capacity")
        ax.axhline(100, color="#888", lw=0.8, ls=":")
        _mark_treatments(ax)
        ax.set_ylabel("Index, pre-treatment mean = 100")
        ax.set_title("Count versus capacity robustness", loc="left")
        ax.legend(loc="lower left", fontsize=7)
        _footnote(fig, "Capacity gaps = masked AIS-artifact days (transits>0, capacity=0).")
        fig.tight_layout(rect=(0, 0.03, 1, 1))
    return fig


def fig_energy_response(panel: pd.DataFrame,
                        audit: pd.DataFrame | None = None) -> plt.Figure:
    win = panel.loc["2026-01-15":"2026-05-01"]
    filled = set()
    if audit is not None and not audit.empty:
        filled = set(pd.to_datetime(
            audit.loc[audit["reason"] == "ffill", "date"]))

    with plt.rc_context(_STYLE):
        fig, ax1 = plt.subplots()
        ax2 = ax1.twinx()
        ax2.spines["right"].set_visible(True)

        ax1.plot(win.index, win["brent_spot"], color="#e63946", lw=1.3,
                 label="Brent (USD/bbl, left)")
        ax2.plot(win.index, win["henry_hub_spot"], color="#1d3557", lw=1.3,
                 label="Henry Hub (USD/MMBtu, right)")

        bf = [d for d in win.index if d in filled]
        if bf:
            ax1.scatter(bf, win.loc[bf, "brent_spot"], s=14,
                        facecolors="none", edgecolors="#e63946", lw=0.7,
                        zorder=5, label="forward-filled (non-trading day)")

        _mark_treatments(ax1, label=False)
        ax1.set_ylabel("Brent, USD/bbl", color="#e63946")
        ax2.set_ylabel("Henry Hub, USD/MMBtu", color="#1d3557")
        ax1.set_title("Energy prices around the Hormuz closure (co-movement, not causal)")
        l1, lab1 = ax1.get_legend_handles_labels()
        l2, lab2 = ax2.get_legend_handles_labels()
        ax1.legend(l1 + l2, lab1 + lab2, loc="upper left", fontsize=7)
        _footnote(fig, "Hollow markers are carried-forward weekend/holiday values, not new observations.")
        fig.tight_layout(rect=(0, 0.03, 1, 1))
    return fig


def fig_missingness(raw_panel: pd.DataFrame) -> plt.Figure:
    miss = raw_panel.isna().T
    with plt.rc_context(_STYLE):
        fig, ax = plt.subplots(figsize=(7.0, 3.0))
        ax.imshow(miss.values, aspect="auto", cmap="Greys",
                  interpolation="nearest",
                  extent=[0, miss.shape[1], miss.shape[0], 0])
        ax.set_yticks([i + 0.5 for i in range(len(miss.index))])
        ax.set_yticklabels(miss.index, fontsize=7)
        n = miss.shape[1]
        idx = raw_panel.index
        ticks = range(0, n, max(1, n // 6))
        ax.set_xticks(list(ticks))
        ax.set_xticklabels([idx[i].strftime("%Y-%m") for i in ticks], fontsize=8)
        ax.set_title("Missingness map — panel_free (black = missing, pre-alignment)")
        ax.grid(False)
        _footnote(fig, "Price rows: regular weekend/holiday gaps. Operational rows: complete 7-day.")
        fig.tight_layout(rect=(0, 0.04, 1, 1))
    return fig


def save(fig: plt.Figure, name: str) -> list:
    """Write a figure to the configured figures dir as PDF + PNG."""
    out_dir = config.path("figures")
    paths = []
    for ext in ("pdf", "png"):
        p = out_dir / f"{name}.{ext}"
        metadata = _PDF_METADATA if ext == "pdf" else None
        fig.savefig(p, bbox_inches="tight", metadata=metadata)
        paths.append(p)
    plt.close(fig)
    return paths
