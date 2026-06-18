"""Step 4: apply the leakage-safe alignment/imputation policy and inspect it.

Pipeline: build_panel()  ->  clean.align_panel()  ->  data/processed/.

Writes two inspection artifacts:
  - data/processed/panel_aligned.csv : the gap-aligned, analysis-ready panel
  - data/processed/alignment_audit.csv : one row per altered cell (full audit)

Persistence FORMAT (Parquet vs CSV vs DB) is still the step-5 decision; these
CSVs are inspection artifacts, like panel_free.csv.

Run from the repo root:
    python scripts/align_panel.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lngfreight import config                              # noqa: E402
from lngfreight.panel import build_panel                   # noqa: E402
from lngfreight.clean import align_panel, alignment_report  # noqa: E402


def main() -> None:
    raw = build_panel()
    clean, audit = align_panel(raw)

    print(f"panel shape: {clean.shape}  "
          f"({clean.index.min().date()} -> {clean.index.max().date()})\n")

    print("Alignment report (per column):")
    print(alignment_report(raw, clean, audit).to_string())

    print("\nAudit log — cells altered by reason:")
    if audit.empty:
        print("  (none)")
    else:
        print(audit["reason"].value_counts().to_string())

    # Sanity guards the human should eyeball: the REAL closure-zeros must
    # survive untouched; only the artifact days become NaN.
    if "hormuz_tanker_transits" in clean.columns:
        z = int((clean["hormuz_tanker_transits"] == 0).sum())
        print(f"\nHormuz transit-zero days preserved: {z} "
              f"(genuine closure signal — must NOT be filled)")
    if "hormuz_tanker_capacity" in clean.columns:
        n = int(clean["hormuz_tanker_capacity"].isna().sum())
        print(f"Hormuz capacity cells masked to NaN: {n} (AIS artifact days)")

    out_dir = config.path("data_processed")
    panel_out = out_dir / "panel_aligned.csv"
    audit_out = out_dir / "alignment_audit.csv"
    clean.to_csv(panel_out)
    audit.to_csv(audit_out, index=False)
    print(f"\nwrote {panel_out}")
    print(f"wrote {audit_out}")

    print("\nSpot-check, closure window (raw NaN -> ffilled), Brent + Hormuz:")
    cols = [c for c in ["brent_spot", "henry_hub_spot",
                        "hormuz_tanker_transits", "hormuz_tanker_capacity"]
            if c in clean.columns]
    print(clean.loc["2026-02-26":"2026-03-08", cols].to_string())


if __name__ == "__main__":
    main()
