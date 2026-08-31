"""Step 4: leakage-safe alignment / imputation of the assembled panel.

This is the SEPARATE, documented imputation step that build_panel.py
deliberately defers (see panel.py decision 2). It takes the honest, un-filled
panel and produces an analysis-ready, gap-aligned panel PLUS a cell-level audit
log, so every altered value stays traceable and the missingness map remains
meaningful (CLAUDE.md rule 6).

Two transformations, both policy-driven from settings.yaml `imputation:`:

1. PRICE FORWARD-FILL (energy/target columns). Business-day price series carry
   their last *observed* value across non-trading calendar days, bounded to
   `price_ffill_max_gap_days` consecutive days. Forward-fill only: it can never
   use a future value, so it introduces no temporal leakage. Interpolation and
   backfill are intentionally NOT offered — both pull a future observation into
   the present. A gap longer than the cap is left NaN (a real outage, flagged).

2. CAPACITY-ARTIFACT MASK (route/mechanism `*_capacity` columns). Days where the
   sibling `*_transits` count is > 0 but capacity logged 0 are AIS artifacts
   (rounding / sub-resolution vessels), not genuine closure-zeros. Under the
   "mask" policy they become NaN so they cannot masquerade as a true zero; the
   real closure days (transits == 0 AND capacity == 0) are left untouched.

Nothing here mutates data/raw or data/interim. Output is for step 5 to persist.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import config


def _price_columns(columns: list[str]) -> list[str]:
    """Registry columns whose role is a business-day price series."""
    reg = config.registry()
    price_roles = {"energy", "target"}
    out = []
    for c in columns:
        base = c[:-7] if c.endswith("__proxy") else c
        if reg.get(base, {}).get("role") in price_roles:
            out.append(c)
    return out


def _capacity_transit_pairs(columns: list[str]) -> list[tuple[str, str]]:
    """(`*_capacity`, sibling `*_transits`) pairs both present in the panel."""
    cols = set(columns)
    pairs = []
    for c in columns:
        if c.endswith("_capacity"):
            sib = c[: -len("_capacity")] + "_transits"
            if sib in cols:
                pairs.append((c, sib))
    return pairs


def align_panel(
    panel: pd.DataFrame,
    settings: dict | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return (aligned_panel, audit_log).

    `aligned_panel` is the same shape/index as `panel` with the two policies
    applied. `audit_log` has one row per altered cell:
    columns [date, column, old, new, reason], reason in
    {"ffill", "artifact_masked"}. Pure function: `panel` is not mutated.
    """
    cfg = (settings or config.settings())["imputation"]
    cap_days = int(cfg["price_ffill_max_gap_days"])
    cap_policy = cfg["capacity_zero_with_transits"]

    clean = panel.copy()
    audit: list[dict] = []

    for c in _price_columns(list(panel.columns)):
        raw = panel[c]
        filled = raw.ffill(limit=cap_days)
        newly = filled.notna() & raw.isna()
        for dt in raw.index[newly]:
            audit.append({"date": dt, "column": c, "old": np.nan,
                          "new": float(filled.loc[dt]), "reason": "ffill"})
        clean[c] = filled

    if cap_policy == "mask":
        for cap_col, transit_col in _capacity_transit_pairs(list(panel.columns)):
            mask = (panel[cap_col] == 0) & (panel[transit_col] > 0)
            for dt in panel.index[mask]:
                audit.append({"date": dt, "column": cap_col,
                              "old": float(panel.loc[dt, cap_col]),
                              "new": np.nan, "reason": "artifact_masked"})
            clean.loc[mask, cap_col] = np.nan
    elif cap_policy != "keep":
        raise ValueError(
            f"imputation.capacity_zero_with_transits must be 'mask' or 'keep', "
            f"got {cap_policy!r}."
        )

    audit_log = pd.DataFrame(
        audit, columns=["date", "column", "old", "new", "reason"]
    )
    return clean, audit_log


def alignment_report(
    raw: pd.DataFrame, clean: pd.DataFrame, audit: pd.DataFrame
) -> pd.DataFrame:
    """Per-column before/after null counts + how many cells were altered."""
    counts = (audit.groupby("column").size()
              if not audit.empty else pd.Series(dtype=int))
    out = []
    for c in raw.columns:
        out.append({
            "column": c,
            "null_before": int(raw[c].isna().sum()),
            "null_after": int(clean[c].isna().sum()),
            "cells_altered": int(counts.get(c, 0)),
        })
    return pd.DataFrame(out).set_index("column")
