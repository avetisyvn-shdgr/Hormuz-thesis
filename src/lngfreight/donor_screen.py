"""Data-driven donor-contamination screening for the synthetic-control SPOF.

The synthetic control and spatial placebo both rest on one shared assumption: the
partition of chokepoints into "contaminated" (excluded) and "clean" donors
(`docs/SUTVA_CONTAMINATION_AUDIT.md`). That screen is currently a-priori — five
corridors named by judgement. A Hormuz disruption causes rerouting, so a donor
whose own traffic *rose* post-treatment is a rerouting suspect that should be
screened out; if such a donor is mis-kept, both corroboration layers are biased
together in the anti-conservative direction.

This module turns that audit recommendation into a reproducible, data-driven
screen. It measures each donor's post-period directional deviation with the same
AR-only counterfactual used elsewhere, flags donors whose traffic rose, and builds
the screen sets (a-priori, data-driven, pessimistic union, none) so the
synthetic-control separation can be stress-tested across all of them. Removing
risen (low-loss) donors can only raise the donor-loss reference, so the
pessimistic screen yields a conservative separation floor, not a flattering one.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .corridor_transmission import ar_window_statistic


def donor_directional_deviation(
    wide: pd.DataFrame,
    *,
    treated_slug: str,
    history_start,
    cutoff,
    horizon_days: int,
    min_scored_days: int,
) -> pd.DataFrame:
    """Post-period scaled signed deviation for every non-treated chokepoint.

    A positive deviation means the donor's observed throughput exceeded its own
    AR counterfactual over the post-treatment window — i.e. its traffic rose,
    making it a rerouting suspect under a Hormuz disruption.
    """
    rows: list[dict[str, object]] = []
    for slug in wide.columns:
        if slug == treated_slug:
            continue
        try:
            out = ar_window_statistic(
                wide[slug],
                history_start=history_start,
                origin=cutoff,
                horizon_days=horizon_days,
            )
            deviation = float(out["statistic_value"])
            n_scored = int(out["n_scored"])
        except (ValueError, KeyError):
            deviation = float("nan")
            n_scored = 0
        rows.append({
            "slug": slug,
            "post_signed_deviation": deviation,
            "n_scored": n_scored,
            "reliable": n_scored >= min_scored_days,
            "rose_post_treatment": bool(np.isfinite(deviation) and deviation > 0),
        })
    return pd.DataFrame(rows).sort_values("post_signed_deviation", ascending=False, ignore_index=True)


def build_screens(
    diagnostic: pd.DataFrame,
    *,
    a_priori_slugs,
    rise_tolerance: float = 0.0,
) -> dict[str, frozenset[str]]:
    """Return the contaminated-slug set for each named screen.

    - ``a_priori``: the judgement-based screen already in the codebase;
    - ``data_driven_rose``: every reliable donor whose traffic rose post-treatment;
    - ``pessimistic_union``: the union of the two (the conservative screen);
    - ``none``: keep all donors (the anti-conservative extreme).
    """
    a_priori = frozenset(str(s) for s in a_priori_slugs)
    risen = frozenset(
        str(row.slug)
        for row in diagnostic.itertuples()
        if row.reliable
        and np.isfinite(row.post_signed_deviation)
        and row.post_signed_deviation > rise_tolerance
    )
    return {
        "a_priori": a_priori,
        "data_driven_rose": risen,
        "pessimistic_union": a_priori | risen,
        "none": frozenset(),
    }


def screen_agreement(
    diagnostic: pd.DataFrame,
    screens: dict[str, frozenset[str]],
) -> pd.DataFrame:
    """Annotate each donor with which screens exclude it (audit transparency)."""
    out = diagnostic.copy()
    for name, contaminated in screens.items():
        out[f"excluded_{name}"] = out["slug"].isin(contaminated)
    # Flag a-priori-clean donors that the data-driven screen would now exclude:
    out["data_driven_only_suspect"] = out["excluded_data_driven_rose"] & ~out["excluded_a_priori"]
    return out
