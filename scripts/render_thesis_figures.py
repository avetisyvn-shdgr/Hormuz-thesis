"""Render the complete manuscript figure set from processed artifacts.

This is the public, lightweight figure entry point. It does not refit models or
download data; it delegates to the existing figure generators and verifies that
each selected manuscript figure was written as both vector PDF and PNG preview.

Run from the repository root:
    python scripts/render_thesis_figures.py
    python scripts/render_thesis_figures.py --list
    python scripts/render_thesis_figures.py --check
    python scripts/render_thesis_figures.py --figure 6.1 --figure 6.2
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FIGURE_DIR = ROOT / "reports" / "figures"


@dataclass(frozen=True)
class FigureSpec:
    number: str
    title: str
    stem: str
    generator: str


FIGURES = (
    FigureSpec(
        "3.1",
        "Chokepoint event study",
        "fig1_chokepoint_event_study",
        "make_event_study.py",
    ),
    FigureSpec(
        "6.1",
        "Observed versus AR counterfactual throughput",
        "run_actual_vs_counterfactual",
        "make_run_output.py",
    ),
    FigureSpec(
        "6.2",
        "Temporal-placebo shortfall distribution",
        "run_placebo_distribution",
        "make_run_output.py",
    ),
    FigureSpec(
        "6.3",
        "Estimator and interval agreement",
        "thesis_estimator_interval_agreement",
        "make_thesis_figure_supplements.py",
    ),
    FigureSpec(
        "7.1",
        "Open-data LNG mechanism evidence",
        "mechanism_evidence_summary",
        "make_mechanism_summary.py",
    ),
    FigureSpec(
        "7.2",
        "Modeled route-network change",
        "modeled_route_network_change",
        "make_route_map.py",
    ),
    FigureSpec(
        "8.1",
        "Pre/post LNG origin composition",
        "network_rewiring_origin_composition",
        "make_network_rewiring_summary.py",
    ),
    FigureSpec(
        "8.2",
        "Gulf and total-import changes",
        "network_rewiring_gulf_vs_total",
        "make_network_rewiring_summary.py",
    ),
    FigureSpec(
        "8.3",
        "Importer divergence",
        "thesis_importer_divergence",
        "make_thesis_figure_supplements.py",
    ),
    FigureSpec(
        "8.4",
        "Source-portfolio structure",
        "network_rewiring_source_structure",
        "make_network_rewiring_summary.py",
    ),
    FigureSpec(
        "9.1",
        "Synthetic-control path",
        "run_synthetic_control_path",
        "make_run_output.py",
    ),
    FigureSpec(
        "9.2",
        "Synthetic-control placebo paths",
        "run_synthetic_control_placebo_paths",
        "make_run_output.py",
    ),
    FigureSpec(
        "9.3",
        "Synthetic-control placebo RMSPE ratios",
        "thesis_synthetic_control_placebo_ratios",
        "make_thesis_figure_supplements.py",
    ),
)

GENERATOR_ORDER = (
    "make_event_study.py",
    "make_run_output.py",
    "make_mechanism_summary.py",
    "make_route_map.py",
    "make_network_rewiring_summary.py",
    "make_thesis_figure_supplements.py",
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Render all 13 final manuscript figures, or a selected subset, "
            "from the repository's processed artifacts."
        )
    )
    parser.add_argument(
        "--figure",
        action="append",
        choices=[figure.number for figure in FIGURES],
        help="manuscript figure number to render; repeat for multiple figures",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--list",
        action="store_true",
        help="list figure numbers, titles, outputs, and generators without rendering",
    )
    mode.add_argument(
        "--check",
        action="store_true",
        help="verify that selected PDF and PNG outputs exist without rendering",
    )
    return parser


def _print_catalog(figures: tuple[FigureSpec, ...] = FIGURES) -> None:
    for figure in figures:
        print(
            f"Figure {figure.number}: {figure.title}\n"
            f"  output: reports/figures/{figure.stem}.{{pdf,png}}\n"
            f"  code:   scripts/{figure.generator}"
        )


def _selected(numbers: list[str] | None) -> tuple[FigureSpec, ...]:
    if not numbers:
        return FIGURES
    wanted = set(numbers)
    return tuple(figure for figure in FIGURES if figure.number in wanted)


def _run_generators(figures: tuple[FigureSpec, ...]) -> None:
    needed = {figure.generator for figure in figures}
    env = os.environ.copy()
    env.setdefault("MPLBACKEND", "Agg")
    env.setdefault("MPLCONFIGDIR", "/tmp/lngfreight-matplotlib")
    env.setdefault("PYTHONHASHSEED", "0")

    for generator in GENERATOR_ORDER:
        if generator not in needed:
            continue
        command = [sys.executable, str(ROOT / "scripts" / generator)]
        print(f"\nRendering with scripts/{generator}", flush=True)
        subprocess.run(command, cwd=ROOT, env=env, check=True)


def _verify_outputs(figures: tuple[FigureSpec, ...]) -> None:
    missing = [
        path
        for figure in figures
        for path in (
            FIGURE_DIR / f"{figure.stem}.pdf",
            FIGURE_DIR / f"{figure.stem}.png",
        )
        if not path.is_file() or path.stat().st_size == 0
    ]
    if missing:
        rendered = "\n".join(f" - {path.relative_to(ROOT)}" for path in missing)
        raise FileNotFoundError(f"Figure rendering left missing outputs:\n{rendered}")


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    figures = _selected(args.figure)
    if args.list:
        _print_catalog(figures)
        return 0
    if args.check:
        _verify_outputs(figures)
        print(
            f"Verified {len(figures)} existing manuscript figure(s) as PDF + PNG "
            f"in {FIGURE_DIR.relative_to(ROOT)}/"
        )
        return 0

    _run_generators(figures)
    _verify_outputs(figures)
    print(
        f"\nVerified {len(figures)} manuscript figure(s) as PDF + PNG in "
        f"{FIGURE_DIR.relative_to(ROOT)}/"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
