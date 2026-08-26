"""Shift-share decomposition of the modeled route-burden mean.

The quantity decomposed is the **modeled distance per nominal vessel-capacity
m3 among retained inferred voyages**: the mean of (nominal carrier capacity x
modeled shortest-sea-route distance) over the sequences that survive into the
complete case.

Both factors are modeled, not measured. Nominal capacity is a design property of
the carrier rather than an observed cargo quantity, and the distance is a
shortest-path network estimate rather than an AIS track. A change in this mean
is therefore a statement about the *composition of the sequences that remain
observable*, never a measurement of any ship travelling farther.

The decomposition splits the pre-to-post change into three parts that sum to it
exactly:

``common_pair_share_reweighting``
    Retained-sequence mass shifting between terminal pairs that are supported in
    both periods.
``within_common_pair_capacity_mix``
    The mean nominal capacity carried on a given terminal pair changing. Route
    distance is a property of the pair, so within-pair movement is capacity mix.
``entry_exit_residual``
    Everything attributable to terminal pairs supported in only one period. It
    is the differenced gap between the overall mean and the common-pair
    conditional mean, and it is large exactly when support changes a lot -- which
    is the situation the task-7 support frontier documents.

The residual is defined as the remainder, so reconciliation is exact by
construction; :func:`decompose` asserts it rather than trusting it.

Only the split between the first two terms depends on index-number weighting.
The entry/exit residual is invariant across the weighting schemes here, which is
worth stating whenever the components are reported.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


SYMMETRIC = "symmetric_marshall_edgeworth"
LASPEYRES_SHARE = "laspeyres_share_paasche_within"
PAASCHE_SHARE = "paasche_share_laspeyres_within"
WEIGHTING_SCHEMES = (SYMMETRIC, LASPEYRES_SHARE, PAASCHE_SHARE)

PERIODS = ("pre", "post")


@dataclass(frozen=True)
class Decomposition:
    """One exact three-way split of the route-burden mean change."""

    weighting_scheme: str
    pre_mean: float
    post_mean: float
    total_change: float
    common_pair_share_reweighting: float
    within_common_pair_capacity_mix: float
    entry_exit_residual: float
    n_pre_sequences: int
    n_post_sequences: int
    n_common_pairs: int
    n_pre_only_pairs: int
    n_post_only_pairs: int
    common_pair_pre_share: float
    common_pair_post_share: float

    @property
    def reconciliation_error(self) -> float:
        return abs(
            self.common_pair_share_reweighting
            + self.within_common_pair_capacity_mix
            + self.entry_exit_residual
            - self.total_change
        )

    def component_percentages(self) -> dict[str, float]:
        """Each component as a percent of the total change.

        Undefined when the total change is zero; NaN is returned rather than a
        misleading large ratio.
        """
        if self.total_change == 0:
            return {
                "common_pair_share_reweighting_percent": float("nan"),
                "within_common_pair_capacity_mix_percent": float("nan"),
                "entry_exit_residual_percent": float("nan"),
            }
        return {
            "common_pair_share_reweighting_percent": (
                100.0 * self.common_pair_share_reweighting / self.total_change
            ),
            "within_common_pair_capacity_mix_percent": (
                100.0 * self.within_common_pair_capacity_mix / self.total_change
            ),
            "entry_exit_residual_percent": (
                100.0 * self.entry_exit_residual / self.total_change
            ),
        }

    def percent_stability_ratio(self) -> float:
        """``max(|component|) / |total_change|``.

        A large value means the components largely offset one another, so their
        percentage shares are numerically unstable and can exceed 100% or flip
        sign while describing nothing substantive. Infinite when the total
        change is exactly zero.
        """
        largest = max(
            abs(self.common_pair_share_reweighting),
            abs(self.within_common_pair_capacity_mix),
            abs(self.entry_exit_residual),
        )
        if self.total_change == 0:
            return float("inf")
        return largest / abs(self.total_change)

    def to_row(self) -> dict:
        return {
            "weighting_scheme": self.weighting_scheme,
            "pre_mean": self.pre_mean,
            "post_mean": self.post_mean,
            "total_change": self.total_change,
            "common_pair_share_reweighting": self.common_pair_share_reweighting,
            "within_common_pair_capacity_mix": self.within_common_pair_capacity_mix,
            "entry_exit_residual": self.entry_exit_residual,
            **self.component_percentages(),
            "percent_stability_ratio": self.percent_stability_ratio(),
            "reconciliation_error": self.reconciliation_error,
            "n_pre_sequences": self.n_pre_sequences,
            "n_post_sequences": self.n_post_sequences,
            "n_common_pairs": self.n_common_pairs,
            "n_pre_only_pairs": self.n_pre_only_pairs,
            "n_post_only_pairs": self.n_post_only_pairs,
            "common_pair_pre_share": self.common_pair_pre_share,
            "common_pair_post_share": self.common_pair_post_share,
        }


def _pair_stats(
    frame: pd.DataFrame, pair_column: str, outcome_column: str
) -> tuple[pd.Series, pd.Series]:
    grouped = frame.groupby(pair_column, sort=True)[outcome_column]
    means = grouped.mean()
    shares = grouped.size() / len(frame)
    return means, shares


def decompose(
    complete_case: pd.DataFrame,
    *,
    pair_column: str,
    outcome_column: str,
    weighting_scheme: str = SYMMETRIC,
    reconciliation_tolerance: float = 1e-6,
) -> Decomposition:
    """Exact three-way decomposition of the pre-to-post change in the mean.

    ``complete_case`` must already be restricted to retained sequences: rows
    with a null outcome are a support question, handled upstream, and are not
    silently imputed here.
    """
    if weighting_scheme not in WEIGHTING_SCHEMES:
        raise ValueError(
            f"Unknown weighting_scheme {weighting_scheme!r}; "
            f"expected one of {WEIGHTING_SCHEMES}."
        )
    for column in (pair_column, outcome_column, "sample_period"):
        if column not in complete_case.columns:
            raise ValueError(f"complete case lacks required column {column!r}")
    if complete_case[outcome_column].isna().any():
        raise ValueError(
            "complete case contains null outcomes; restrict to retained "
            "sequences before decomposing"
        )

    pre = complete_case.loc[complete_case["sample_period"].eq("pre")]
    post = complete_case.loc[complete_case["sample_period"].eq("post")]
    if pre.empty or post.empty:
        raise ValueError("decomposition needs non-empty pre and post periods")

    pre_mean = float(pre[outcome_column].mean())
    post_mean = float(post[outcome_column].mean())
    total_change = post_mean - pre_mean

    pre_means, pre_shares = _pair_stats(pre, pair_column, outcome_column)
    post_means, post_shares = _pair_stats(post, pair_column, outcome_column)
    common = sorted(set(pre_means.index) & set(post_means.index))
    if not common:
        raise ValueError(
            "no terminal pair is supported in both periods; the shift-share "
            "decomposition is undefined"
        )

    pre_common_mass = float(pre_shares.reindex(common).fillna(0.0).sum())
    post_common_mass = float(post_shares.reindex(common).fillna(0.0).sum())
    sigma_pre = pre_shares.reindex(common).fillna(0.0) / pre_common_mass
    sigma_post = post_shares.reindex(common).fillna(0.0) / post_common_mass
    m_pre = pre_means.reindex(common)
    m_post = post_means.reindex(common)

    if weighting_scheme == SYMMETRIC:
        share_weight = (m_pre + m_post) / 2.0
        within_weight = (sigma_pre + sigma_post) / 2.0
    elif weighting_scheme == LASPEYRES_SHARE:
        share_weight = m_pre
        within_weight = sigma_post
    else:
        share_weight = m_post
        within_weight = sigma_pre

    share_term = float(((sigma_post - sigma_pre) * share_weight).sum())
    within_term = float((within_weight * (m_post - m_pre)).sum())
    residual = float(total_change - share_term - within_term)

    result = Decomposition(
        weighting_scheme=weighting_scheme,
        pre_mean=pre_mean,
        post_mean=post_mean,
        total_change=total_change,
        common_pair_share_reweighting=share_term,
        within_common_pair_capacity_mix=within_term,
        entry_exit_residual=residual,
        n_pre_sequences=int(len(pre)),
        n_post_sequences=int(len(post)),
        n_common_pairs=int(len(common)),
        n_pre_only_pairs=int(len(set(pre_means.index) - set(post_means.index))),
        n_post_only_pairs=int(len(set(post_means.index) - set(pre_means.index))),
        common_pair_pre_share=pre_common_mass,
        common_pair_post_share=post_common_mass,
    )
    if result.reconciliation_error > reconciliation_tolerance:
        raise AssertionError(
            "route-burden components do not reconcile to the total change: "
            f"error {result.reconciliation_error}"
        )
    return result


def residual_identity_check(
    complete_case: pd.DataFrame,
    *,
    pair_column: str,
    outcome_column: str,
) -> float:
    """Independent value of the entry/exit residual, for cross-checking.

    Computes ``(Y_post - Y_common_post) - (Y_pre - Y_common_pre)`` directly from
    the conditional means instead of as a remainder. Agreement with
    :func:`decompose` confirms the residual is the support term it claims to be
    and not an accumulation of arithmetic slack.
    """
    pre = complete_case.loc[complete_case["sample_period"].eq("pre")]
    post = complete_case.loc[complete_case["sample_period"].eq("post")]
    common = set(pre[pair_column]) & set(post[pair_column])
    pre_common = pre.loc[pre[pair_column].isin(common), outcome_column].mean()
    post_common = post.loc[post[pair_column].isin(common), outcome_column].mean()
    gap_post = float(post[outcome_column].mean()) - float(post_common)
    gap_pre = float(pre[outcome_column].mean()) - float(pre_common)
    return gap_post - gap_pre


def pair_support_table(
    complete_case: pd.DataFrame,
    *,
    pair_column: str,
    outcome_column: str,
) -> pd.DataFrame:
    """Per-terminal-pair support and mean burden, with an entry/exit label."""
    rows = []
    pre = complete_case.loc[complete_case["sample_period"].eq("pre")]
    post = complete_case.loc[complete_case["sample_period"].eq("post")]
    pre_means, pre_shares = _pair_stats(pre, pair_column, outcome_column)
    post_means, post_shares = _pair_stats(post, pair_column, outcome_column)
    for pair in sorted(set(pre_means.index) | set(post_means.index)):
        in_pre = pair in pre_means.index
        in_post = pair in post_means.index
        rows.append({
            "terminal_pair": pair,
            "support_status": (
                "common" if in_pre and in_post
                else "pre_only_exit" if in_pre
                else "post_only_entry"
            ),
            "pre_sequences": int((pre[pair_column] == pair).sum()),
            "post_sequences": int((post[pair_column] == pair).sum()),
            "pre_share": float(pre_shares.get(pair, 0.0)),
            "post_share": float(post_shares.get(pair, 0.0)),
            "pre_mean_burden": float(pre_means.get(pair, np.nan)),
            "post_mean_burden": float(post_means.get(pair, np.nan)),
        })
    return pd.DataFrame(rows)
