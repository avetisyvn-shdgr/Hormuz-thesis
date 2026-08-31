"""Build the Fujairah FEDCom weekly inventory panel and its figure.

Independent, non-AIS physical evidence at the Fujairah bypass port.
Reads only from data/raw/fujairah_fedcom/. Writes:
  data/processed/fujairah_weekly_stocks.csv
  outputs/figures/fujairah_inventory_2026.{png,pdf}

Fails loudly if any observed row's components do not sum to its reported total.
Gaps are preserved as NaN and never interpolated.

Run:  python scripts/build_fujairah_inventory_panel.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "fujairah_fedcom"
PROC = ROOT / "data" / "processed"
FIGS = ROOT / "outputs" / "figures"

WAR_START = pd.Timestamp("2026-02-28")
FOIZ_FIRE = pd.Timestamp("2026-03-03")
CEASEFIRE = pd.Timestamp("2026-06-17")

COMPONENTS = ["light_mnbbl", "middle_mnbbl", "heavy_mnbbl"]
TOL = 0.0015


def load_stocks() -> pd.DataFrame:
    df = pd.read_csv(RAW / "fujairah_weekly_stocks_2026.csv",
                     parse_dates=["week_ending"])
    obs = df[df["status"] == "observed"]
    resid = (obs[COMPONENTS].sum(axis=1) - obs["total_mnbbl"]).abs()
    bad = obs.loc[resid > TOL, "week_ending"]
    if len(bad):
        sys.exit(f"FAIL component sum check on: {list(bad.dt.date)}")
    print(f"OK  {len(obs)} observed weeks, all components sum to total "
          f"(max residual {resid.max():.5f} mn bbl)")
    print(f"    {int((df['status'] == 'gap').sum())} gaps preserved as NaN")
    return df


def summarise(df: pd.DataFrame) -> None:
    obs = df[df["status"] == "observed"]
    peak = obs.loc[obs["total_mnbbl"].idxmax()]
    trough = obs.loc[obs["total_mnbbl"].idxmin()]
    prewar = obs[obs["week_ending"] < WAR_START].iloc[-1]
    print(f"    peak    {peak['week_ending']:%Y-%m-%d}  {peak['total_mnbbl']:.3f} mn bbl")
    print(f"    trough  {trough['week_ending']:%Y-%m-%d}  {trough['total_mnbbl']:.3f} mn bbl")
    print(f"    peak->trough   {trough['total_mnbbl'] / peak['total_mnbbl'] - 1:+.1%}")
    print(f"    vs last pre-war {trough['total_mnbbl'] / prewar['total_mnbbl'] - 1:+.1%}")
    pre = obs[obs["week_ending"] < WAR_START]
    print(f"    pre-event light distillate trend (3 wks to {pre['week_ending'].max():%Y-%m-%d}): "
          f"{list(pre['light_mnbbl'].round(3))}")


def make_figure(df: pd.DataFrame) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.dates as mdates
    import matplotlib.patheffects as pe
    import matplotlib.pyplot as plt

    INK, MUTED, GRID, SURF = "#1F2933", "#5C6773", "#DFE3E7", "#FCFCFB"
    BLUE, AMBER, MAGENTA, BAND = "#2B7FD4", "#C97A10", "#D13A8E", "#EEF1F4"

    d = df["week_ending"]
    fig, ax = plt.subplots(figsize=(9.2, 5.0))
    fig.patch.set_facecolor(SURF)
    ax.set_facecolor(SURF)
    ax.axvspan(WAR_START, CEASEFIRE, color=BAND, zorder=0, lw=0)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(GRID)
    ax.grid(axis="y", color=GRID, lw=.8)
    ax.set_axisbelow(True)
    ax.tick_params(colors=MUTED, labelsize=9.5, length=0)

    for col, c, lab in ((("light_mnbbl"), BLUE, "Light distillates"),
                        ("middle_mnbbl", AMBER, "Middle distillates"),
                        ("heavy_mnbbl", MAGENTA, "Heavy distillates")):
        ax.plot(d, df[col], color=c, lw=2, marker="o", ms=3.4, label=lab, zorder=4)
    ax.plot(d, df["total_mnbbl"], color=INK, lw=2.6, marker="o", ms=4.6,
            label="Total", zorder=5)

    ax.set_ylabel("Million barrels", color=MUTED, fontsize=10)
    ax.set_ylim(0, 24)
    ax.legend(frameon=False, fontsize=9.5, loc="upper right", labelcolor=INK,
              handlelength=1.6, borderaxespad=0.4)

    for x, lab in ((WAR_START, "Feb 28  operational onset"),
                   (FOIZ_FIRE, "Mar 3  FOIZ fire"),
                   (CEASEFIRE, "Jun 17  ceasefire")):
        ax.axvline(x, color=MUTED, lw=1, ls=(0, (4, 3)), zorder=2)
        t = ax.text(x, 0.45, "  " + lab, fontsize=8.3, color=MUTED,
                    rotation=90, va="bottom", ha="left", zorder=7)
        t.set_path_effects([pe.withStroke(linewidth=3.2, foreground=SURF)])

    ax.xaxis.set_major_locator(mdates.MonthLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b"))
    fig.text(0.005, 0.015,
             "Weekly stocks as of Monday. Fujairah Energy Data Committee, transcribed from "
             "S&P Global weekly reports (see data/raw/fujairah_fedcom/SOURCES.md).\n"
             "Gaps are weeks with no located report and are not interpolated.",
             fontsize=7.6, color=MUTED, linespacing=1.5)
    plt.subplots_adjust(left=.075, right=.985, top=.96, bottom=.135)

    FIGS.mkdir(parents=True, exist_ok=True)
    for ext in ("png", "pdf"):
        fig.savefig(FIGS / f"fujairah_inventory_2026.{ext}", dpi=200, facecolor=SURF)
    print(f"OK  wrote {FIGS/'fujairah_inventory_2026.png'} (+ .pdf)")


def main() -> None:
    df = load_stocks()
    summarise(df)
    PROC.mkdir(parents=True, exist_ok=True)
    out = PROC / "fujairah_weekly_stocks.csv"
    df.to_csv(out, index=False)
    print(f"OK  wrote {out}")
    make_figure(df)


if __name__ == "__main__":
    main()
