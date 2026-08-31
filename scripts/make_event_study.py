"""Layer-1: render the descriptive event-study figures to reports/figures/.

Consumes the step-4 outputs:
  data/processed/panel_aligned.csv   (series)
  data/processed/alignment_audit.csv (to mark forward-filled price points)
  data/interim/panel_free.csv        (honest missingness map)

Writes PDF (thesis/LaTeX) + PNG (preview) per figure.

Run from the repo root:
    python scripts/make_event_study.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")

import pandas as pd  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from hormuz_throughput import config, eventstudy as es  # noqa: E402


def _load(path: Path, **kw) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found. Run scripts/build_panel.py and "
            f"scripts/align_panel.py first.")
    return pd.read_csv(path, parse_dates=["date"], **kw).set_index("date")


def main() -> None:
    interim = config.path("data_interim")
    processed = config.path("data_processed")

    aligned = _load(processed / "panel_aligned.csv")
    raw = _load(interim / "panel_free.csv")
    audit = pd.read_csv(processed / "alignment_audit.csv")

    figures = {
        "fig1_chokepoint_event_study": es.fig_chokepoint_event_study(aligned),
        "fig2_hormuz_robustness": es.fig_hormuz_robustness(aligned),
        "fig3_energy_response": es.fig_energy_response(aligned, audit),
        "fig4_missingness_map": es.fig_missingness(raw),
    }

    for name, fig in figures.items():
        for p in es.save(fig, name):
            print(f"wrote {p}")

    print("\nReminder (CLAUDE.md): these are DESCRIPTIVE figures.")
    print(" - Treatment lines are VERIFIED dates (docs/EVENT_CHRONOLOGY.md).")
    print(" - Hormuz vs Panama is a contrast, not an estimated effect.")
    print(" - Price panel shows co-movement; weekend points are forward-filled.")


if __name__ == "__main__":
    main()
