"""Assemble the cross-source evidence cascade for the Hormuz LNG study.

This module does not compute new estimates. It packages results that already
exist in frozen artifacts into one ordered transmission chain so the thesis reads
as a single triangulated argument rather than four disconnected analyses. Each
link names its independent data source and its interpretation boundary, so the
cascade cannot be mistaken for a causal ton-mile multiplier.
"""
from __future__ import annotations

import pandas as pd


def percent_change(pre: float, post: float) -> float:
    """Signed percent change from a positive pre-period base."""
    if pre is None or post is None or not pre > 0:
        return float("nan")
    return (post - pre) / pre * 100.0


def build_evidence_cascade(
    *,
    hormuz_observed: float,
    hormuz_counterfactual: float,
    hormuz_signed_deviation: float,
    hormuz_rw_p: float,
    donor_separation_pessimistic: float,
    gfw_pre: float,
    gfw_post: float,
    wto_pre: float,
    wto_post: float,
    voyages_pre: float,
    voyages_post: float,
    total_pre: float,
    total_post: float,
    mean_per_voyage_pct: float,
    mean_bca_lower: float,
    mean_bca_upper: float,
    composition_share_pct: float,
    destination_risers: dict[str, float],
) -> pd.DataFrame:
    """Return the ordered evidence cascade as a tidy table.

    Inputs are already-extracted scalars from the frozen processed outputs, which
    keeps this function pure and unit-testable.
    """
    risers = ", ".join(
        f"{name} {value:+.0%}"
        for name, value in sorted(destination_risers.items(), key=lambda kv: -kv[1])
    )
    rows = [
        {
            "step": 1,
            "layer": "Chokepoint disruption",
            "independent_source": "IMF PortWatch (satellite AIS)",
            "metric": "Strait of Hormuz tanker transits, 94-day window",
            "pre_value": round(hormuz_counterfactual, 1),
            "post_value": round(hormuz_observed, 1),
            "percent_change": round(hormuz_signed_deviation * 100.0, 1),
            "corroboration": (
                f"donor synthetic control {donor_separation_pessimistic:.1f}x "
                f"separation (survives pessimistic screen); Romano-Wolf p={hormuz_rw_p:.2f}"
            ),
            "interpretation_boundary": "AR counterfactual, not an identified ATT",
        },
        {
            "step": 2,
            "layer": "Commodity-specific export collapse",
            "independent_source": "GFW port visits + WTO/AXSMarine index (two sources)",
            "metric": "Gulf LNG departures: GFW calls / WTO outbound index",
            "pre_value": round(gfw_pre, 1),
            "post_value": round(gfw_post, 1),
            "percent_change": round(percent_change(gfw_pre, gfw_post), 1),
            "corroboration": (
                f"WTO index {wto_pre:.1f}->{wto_post:.1f} "
                f"({percent_change(wto_pre, wto_post):+.1f}%), no calibration applied"
            ),
            "interpretation_boundary": "inferred departures, not observed cargo tonnage",
        },
        {
            "step": 3,
            "layer": "Fleet-activity contraction",
            "independent_source": "GFW voyage reconstruction (624-carrier census)",
            "metric": "Resolved Gulf LNG voyages (30km, expanded route QA)",
            "pre_value": round(voyages_pre, 1),
            "post_value": round(voyages_post, 1),
            "percent_change": round(percent_change(voyages_pre, voyages_post), 1),
            "corroboration": (
                f"aggregate inferred capacity-distance "
                f"{percent_change(total_pre, total_post):+.1f}% (also a decline)"
            ),
            "interpretation_boundary": "terminal-sequence inference; right-censoring present",
        },
        {
            "step": 4,
            "layer": "Routing composition shift",
            "independent_source": "GFW capacity-nautical-mile reconstruction",
            "metric": "Mean capacity-distance per retained voyage",
            "pre_value": None,
            "post_value": None,
            "percent_change": round(mean_per_voyage_pct, 1),
            "corroboration": (
                f"BCa 95% CI [{mean_bca_lower:+.1f}%, {mean_bca_upper:+.1f}%]; "
                f"{composition_share_pct:.0f}% from route composition, not elongation"
            ),
            "interpretation_boundary": "composition effect; NOT observed laden ton-miles",
        },
        {
            "step": 5,
            "layer": "Destination substitution",
            "independent_source": "IMF PortWatch corridor map",
            "metric": "Alternative corridors above counterfactual",
            "pre_value": None,
            "post_value": None,
            "percent_change": None,
            "corroboration": f"risers: {risers}",
            "interpretation_boundary": "descriptive; no voyage-level flow tracing",
        },
    ]
    return pd.DataFrame(rows)
