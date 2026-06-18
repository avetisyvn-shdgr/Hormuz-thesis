"""Export model-input coverage, capacity-missingness, and information-set audits."""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lngfreight import config  # noqa: E402
from lngfreight.diagnostics import (  # noqa: E402
    capacity_missingness,
    coverage_by_period,
    model_information_sets,
)
from lngfreight.validation import resolve_cutoff  # noqa: E402


def main() -> None:
    processed = config.path("data_processed")
    panel_path = processed / "panel_aligned.csv"
    audit_path = processed / "alignment_audit.csv"
    if not panel_path.exists() or not audit_path.exists():
        raise FileNotFoundError(
            "Run scripts/align_panel.py before model diagnostics."
        )

    panel = pd.read_csv(panel_path, parse_dates=["date"]).set_index("date")
    audit = pd.read_csv(audit_path, parse_dates=["date"])
    cutoff = resolve_cutoff()

    coverage = coverage_by_period(panel, cutoff)
    capacity = capacity_missingness(panel, audit, cutoff)
    information = model_information_sets()

    outputs = {
        "model_input_coverage.csv": coverage,
        "capacity_missingness_diagnostics.csv": capacity,
        "model_information_sets.csv": information,
    }
    for name, frame in outputs.items():
        path = processed / name
        frame.to_csv(path, index=False)
        print(f"wrote {path}")

    print(f"\nCutoff: {cutoff.date()}")
    print("\nPost-period target coverage:")
    print(coverage.loc[
        coverage["column"].str.startswith("hormuz_"),
        ["column", "post_rows", "post_non_null", "post_missing", "post_coverage"],
    ].to_string(index=False))
    print("\nCapacity missingness attribution:")
    print(capacity.to_string(index=False))
    print("\nModel information sets:")
    print(information.to_string(index=False))


if __name__ == "__main__":
    main()
