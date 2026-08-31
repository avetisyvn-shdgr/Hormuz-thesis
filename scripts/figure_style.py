"""Shared deterministic publication style for thesis figure scripts."""
from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt


FIGURE_WIDTH_IN = 7.2

THESIS_TEXTWIDTH_IN = 418.25555 / 72.27
DECREASE_COLOR = "#B2182B"
INCREASE_COLOR = "#2166AC"
NEUTRAL_DARK = "#3F3F3F"
NEUTRAL_MID = "#737373"
NEUTRAL_LIGHT = "#D9D9D9"
GRID_COLOR = "#D7D7D7"
BACKGROUND_COLOR = "#FFFFFF"
PDF_METADATA = {
    "Title": "Thesis figure",
    "Author": "Hormuz tanker-throughput thesis pipeline",
    "Subject": "Deterministic pipeline artifact",
    "Keywords": "LNG, maritime trade, thesis",
    "Creator": "Matplotlib",
    "Producer": "Matplotlib",
    "CreationDate": None,
    "ModDate": None,
}
PNG_METADATA = {
    "Software": "Matplotlib; deterministic thesis figure pipeline",
}

ACCENT_ORANGE = "#E37222"
SECONDARY_BLUE = "#003359"
ACCENT_LIGHT_BLUE = "#98C6EA"
ACCENT_BLUE = "#64A0C8"
ACCENT_GRAY = "#DAD7CB"

OBSERVED_TREATED = DECREASE_COLOR
COUNTERFACTUAL = INCREASE_COLOR
COMPARISON_SERIES = NEUTRAL_DARK
PLACEBO = NEUTRAL_LIGHT
EVENT_MARKER = "#000000"


def apply_publication_style() -> None:
    """Set print-legible typography and vector-font defaults.

    The thesis body font is Palatino (mathpazo in the fwalch TUM template).
    P052 is the URW Palladio clone of Palatino shipped with Ghostscript, so
    figure text matches the surrounding document; DejaVu Serif is the
    deterministic fallback.
    """
    plt.rcParams.update({
        "font.family": "serif",
        "font.serif": ["P052", "URW Palladio L", "Palatino", "TeX Gyre Pagella", "DejaVu Serif"],
        "mathtext.fontset": "custom",
        "mathtext.rm": "P052",
        "mathtext.it": "P052:italic",
        "mathtext.bf": "P052:bold",
        "font.size": 10.0,
        "axes.titlesize": 11.0,
        "axes.titleweight": "semibold",
        "axes.labelsize": 11.0,
        "axes.labelcolor": NEUTRAL_DARK,
        "axes.edgecolor": NEUTRAL_MID,
        "axes.linewidth": 0.65,
        "xtick.labelsize": 10.0,
        "ytick.labelsize": 10.0,
        "xtick.color": NEUTRAL_DARK,
        "ytick.color": NEUTRAL_DARK,
        "xtick.major.width": 0.65,
        "ytick.major.width": 0.65,
        "xtick.major.size": 3.0,
        "ytick.major.size": 3.0,
        "legend.fontsize": 9.0,
        "legend.frameon": False,
        "figure.facecolor": BACKGROUND_COLOR,
        "axes.facecolor": BACKGROUND_COLOR,
        "savefig.facecolor": BACKGROUND_COLOR,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
        "svg.fonttype": "none",
        "path.simplify": False,
    })


def style_axes(
    ax: plt.Axes,
    *,
    grid_axis: str = "y",
    keep_all_spines: bool = False,
) -> None:
    """Apply consistent axes, grid, and spine styling."""
    ax.set_axisbelow(True)
    ax.grid(
        axis=grid_axis,
        color=GRID_COLOR,
        linewidth=0.45,
        linestyle="-",
        alpha=0.75,
    )
    if not keep_all_spines:
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
    for spine in ax.spines.values():
        spine.set_linewidth(0.65)
        spine.set_color(NEUTRAL_MID)
    ax.tick_params(direction="out", width=0.65)


def save_pdf_and_png(
    fig: plt.Figure,
    png_path: Path,
    *,
    pdf_path: Path | None = None,
    dpi: int = 300,
) -> tuple[Path, Path]:
    """Save stable vector PDF plus a PNG preview without timestamp metadata."""
    png_path = Path(png_path)
    pdf_path = Path(pdf_path) if pdf_path is not None else png_path.with_suffix(".pdf")
    png_path.parent.mkdir(parents=True, exist_ok=True)
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(
        pdf_path,
        bbox_inches="tight",
        metadata=PDF_METADATA,
    )
    fig.savefig(
        png_path,
        dpi=dpi,
        bbox_inches="tight",
        metadata=PNG_METADATA,
    )
    return pdf_path, png_path
