"""Support denominators for the modeled LNG terminal-sequence network.

The question this module answers is deliberately narrow: in the resolved
terminal-sequence panel, how much *observational support* exists before and
after the disruption, overall and for Hormuz-crossing sequences specifically?

That is a statement about the panel, not about the sea. A sequence leaves this
panel whenever AIS coverage lapses, a terminal cannot be attributed within the
chosen radius, or a route cannot be resolved -- and every one of those failure
modes is plausibly *more* likely during a disruption. So a collapse in modeled
Hormuz-crossing support is evidence about support, and the honest reading is
that the panel stops observing those sequences, never that no ship sailed.

Two disciplines are enforced here.

1. **Paired denominators.** Every selective count is produced alongside the
   overall count for the same radius and period. :func:`support_denominators`
   cannot emit one without the other, so a Hormuz-crossing collapse can never be
   quoted without the general decline that contextualises it.

2. **Carrier composition held fixed on request.** :func:`balanced_cohort`
   restricts to IMOs observed in both periods, so a support change cannot be
   manufactured purely by carriers entering or leaving the resolved panel.

Nothing here estimates cargo, throughput, or a treatment effect.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


COHORTS = (
    "all_resolved",
    "hormuz_crossing",
    "inside_hormuz_non_crossing",
    "non_gulf",
)
PERIODS = ("pre", "post")

DENOMINATOR_COLUMNS = [
    "terminal_radius_km",
    "cohort",
    "sample_period",
    "n_sequences",
    "n_unique_imos",
    "n_destination_countries",
    "n_destination_terminals",
    "n_origin_terminals",
    "census_eligible_imos",
    "census_coverage_share",
    "share_of_all_resolved_sequences",
]

_REQUIRED_LEG_COLUMNS = {
    "event_id",
    "imo",
    "sample_period",
    "project_id",
    "terminal_name",
    "destination_project_id",
    "destination_terminal_name",
    "destination_country",
    "inside_hormuz_origin",
    "hormuz_exposed_leg",
    "origin_group",
}


def cohort_mask(legs: pd.DataFrame, cohort: str) -> pd.Series:
    """Boolean membership for one frozen cohort definition.

    The Hormuz-crossing cohort reuses ``hormuz_exposed_leg`` from
    ``exposure.attach_exposure_metadata`` rather than re-deriving it, so this
    phase cannot drift into a second, incompatible definition of the same
    construct.
    """
    if cohort not in COHORTS:
        raise ValueError(f"Unknown cohort {cohort!r}; expected one of {COHORTS}.")
    missing = _REQUIRED_LEG_COLUMNS.difference(legs.columns)
    if missing:
        raise ValueError(f"Resolved legs missing columns: {sorted(missing)}")

    if cohort == "all_resolved":
        return pd.Series(True, index=legs.index)
    if cohort == "hormuz_crossing":
        return legs["hormuz_exposed_leg"].astype(bool)
    if cohort == "inside_hormuz_non_crossing":
        return legs["inside_hormuz_origin"].astype(bool) & ~legs[
            "hormuz_exposed_leg"
        ].astype(bool)
    return ~legs["inside_hormuz_origin"].astype(bool)


def _cell_metrics(frame: pd.DataFrame) -> dict[str, int]:
    return {
        "n_sequences": int(len(frame)),
        "n_unique_imos": int(frame["imo"].nunique()),
        "n_destination_countries": int(frame["destination_country"].nunique()),
        "n_destination_terminals": int(frame["destination_project_id"].nunique()),
        "n_origin_terminals": int(frame["project_id"].nunique()),
    }


def support_denominators(
    legs: pd.DataFrame,
    *,
    terminal_radius_km: int,
    census_eligible_imos: int,
    cohorts: tuple[str, ...] = COHORTS,
) -> pd.DataFrame:
    """Pre/post support denominators for every cohort at one radius.

    ``all_resolved`` is always emitted, whatever ``cohorts`` requests, because a
    selective count reported without its overall denominator is exactly the
    misreading this phase exists to prevent.
    """
    if census_eligible_imos <= 0:
        raise ValueError("census_eligible_imos must be > 0.")
    requested = tuple(dict.fromkeys(("all_resolved", *cohorts)))

    totals = {
        period: int(legs["sample_period"].eq(period).sum()) for period in PERIODS
    }
    rows = []
    for cohort in requested:
        mask = cohort_mask(legs, cohort)
        for period in PERIODS:
            frame = legs.loc[mask & legs["sample_period"].eq(period)]
            metrics = _cell_metrics(frame)
            total = totals[period]
            rows.append({
                "terminal_radius_km": int(terminal_radius_km),
                "cohort": cohort,
                "sample_period": period,
                **metrics,
                "census_eligible_imos": int(census_eligible_imos),
                "census_coverage_share": (
                    metrics["n_unique_imos"] / census_eligible_imos
                ),
                "share_of_all_resolved_sequences": (
                    metrics["n_sequences"] / total if total else np.nan
                ),
            })
    return pd.DataFrame(rows, columns=DENOMINATOR_COLUMNS)


def balanced_cohort_imos(legs: pd.DataFrame) -> set:
    """IMOs with at least one resolved sequence in both periods."""
    seen = {
        period: set(legs.loc[legs["sample_period"].eq(period), "imo"].unique())
        for period in PERIODS
    }
    return seen["pre"] & seen["post"]


def balanced_cohort(legs: pd.DataFrame) -> pd.DataFrame:
    """Restrict the panel to carriers observed in both periods."""
    keep = balanced_cohort_imos(legs)
    return legs.loc[legs["imo"].isin(keep)].copy()


def support_change(
    denominators: pd.DataFrame,
    *,
    thin_denominator_threshold: int = 10,
) -> pd.DataFrame:
    """Pre-to-post change per radius and cohort, with retention shares.

    ``retention_share`` is the post count divided by the pre count. It is a
    support-retention ratio for the modeled panel and carries no throughput,
    utilisation, or causal meaning.

    ``pre_denominator_is_thin`` flags cells whose pre-period count is at or
    below ``thin_denominator_threshold``. Such a cell can report a retention
    share far above 1.0 from a movement of one or two sequences, which is
    arithmetically correct and substantively empty; the flag exists so that a
    reader is never invited to treat it as a trend.
    """
    if thin_denominator_threshold < 0:
        raise ValueError("thin_denominator_threshold must be >= 0.")
    rows = []
    grouped = denominators.groupby(["terminal_radius_km", "cohort"], sort=True)
    for (radius, cohort), group in grouped:
        indexed = group.set_index("sample_period")
        if not set(PERIODS).issubset(indexed.index):
            raise ValueError(
                f"Cell {cohort} at {radius} km lacks a pre/post pair."
            )
        pre = indexed.loc["pre"]
        post = indexed.loc["post"]
        pre_n = int(pre["n_sequences"])
        post_n = int(post["n_sequences"])
        rows.append({
            "terminal_radius_km": int(radius),
            "cohort": cohort,
            "pre_sequences": pre_n,
            "post_sequences": post_n,
            "absolute_change_sequences": post_n - pre_n,
            "retention_share": (post_n / pre_n) if pre_n else np.nan,
            "percent_change": ((post_n / pre_n - 1.0) * 100) if pre_n else np.nan,
            "pre_denominator_is_thin": bool(pre_n <= thin_denominator_threshold),
            "pre_unique_imos": int(pre["n_unique_imos"]),
            "post_unique_imos": int(post["n_unique_imos"]),
            "pre_destination_countries": int(pre["n_destination_countries"]),
            "post_destination_countries": int(post["n_destination_countries"]),
            "pre_destination_terminals": int(pre["n_destination_terminals"]),
            "post_destination_terminals": int(post["n_destination_terminals"]),
            "pre_census_coverage_share": float(pre["census_coverage_share"]),
            "post_census_coverage_share": float(post["census_coverage_share"]),
        })
    return pd.DataFrame(rows)


def selectivity_contrast(change: pd.DataFrame) -> pd.DataFrame:
    """Hormuz-crossing retention against the overall retention, per radius.

    The ratio of the two retention shares is the phase's headline descriptive
    quantity: it says how much more of its support the Hormuz-crossing cohort
    lost than the panel as a whole. It is a ratio of observation counts, not of
    voyages, cargo, or capacity.
    """
    rows = []
    for radius, group in change.groupby("terminal_radius_km", sort=True):
        indexed = group.set_index("cohort")
        for required in ("all_resolved", "hormuz_crossing"):
            if required not in indexed.index:
                raise ValueError(
                    f"Selectivity contrast needs the {required} cohort at "
                    f"{radius} km."
                )
        overall = float(indexed.loc["all_resolved", "retention_share"])
        selective = float(indexed.loc["hormuz_crossing", "retention_share"])
        rows.append({
            "terminal_radius_km": int(radius),
            "all_resolved_retention_share": overall,
            "hormuz_crossing_retention_share": selective,
            "retention_share_ratio": (selective / overall) if overall else np.nan,
            "retention_gap_percentage_points": (selective - overall) * 100,
            "selective_support_loss_exceeds_general": bool(selective < overall),
        })
    return pd.DataFrame(rows)
