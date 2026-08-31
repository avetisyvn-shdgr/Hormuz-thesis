"""Outcome-independent block geometry for the horizon/resolution frontier.

This module answers a design question, not an estimation question: given a daily
pre-treatment calendar, a locked training cutoff, and a minimum training length,
*which* disjoint reference blocks of a chosen length exist, how many of them can
coexist, and what finite-sample inference does that block count permit?

Two disciplines are enforced here by construction.

1. **Outcome independence.** Every function in the geometry half of this module
   takes a :class:`pandas.DatetimeIndex` and integers. None of them can see an
   outcome column, a forecast, a loss, or a p-value, so no origin rule in this
   project can be selected because it produced a favourable result.

2. **Complete enumeration.** The locked primary artifact greedily selects
   disjoint windows out of a 30-day-stepped candidate set. That is a restricted
   subsample, and it can return fewer blocks than the calendar supports.
   :func:`enumerate_candidate_blocks` enumerates *every* feasible daily origin
   and :func:`maximum_disjoint_packing` returns a maximum-cardinality disjoint
   set, so the attainable block count is reported rather than assumed.

The finite-sample consequences follow mechanically from the block count ``K``:
the smallest attainable rank p-value is ``1 / (K + 1)``, the largest coverage a
split-conformal interval can support is ``K / (K + 1)``, and any requested level
whose order statistic ``ceil((K + 1) * level)`` exceeds ``K`` has an infinite
radius. Reporting an unbounded interval is the honest outcome; clipping the rank
would silently deliver less coverage than the label claims.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import pandas as pd

from .validation import Fold, require_chronological_index


PRIMARY_RULE = "forward_anchored_direct"
SENSITIVITY_RULE = "backward_anchored_from_cutoff"
LEGACY_RULE = "legacy_greedy_step30"
ORIGIN_RULES = (PRIMARY_RULE, SENSITIVITY_RULE, LEGACY_RULE)
LEGACY_STEP_DAYS = 30

_GEOMETRY_COLUMNS = [
    "origin_rule",
    "horizon_days",
    "block_index",
    "block_name",
    "test_start",
    "test_end",
    "train_start",
    "train_end",
    "n_train_days",
    "n_test_days",
]


@dataclass(frozen=True)
class Block:
    """One disjoint reference block. Inclusive ``[start, end]`` calendar bounds."""

    name: str
    start: pd.Timestamp
    end: pd.Timestamp

    @property
    def length_days(self) -> int:
        return int((self.end - self.start).days) + 1

    def overlaps(self, other: "Block") -> bool:
        return self.start <= other.end and other.start <= self.end


def anchor_origin(index: pd.DatetimeIndex, min_initial_train_days: int) -> pd.Timestamp:
    """Earliest admissible reference-block start date.

    The anchor is the panel start plus the minimum training length. It depends
    on the calendar alone and reproduces the anchor already used by the locked
    primary placebo construction.
    """
    if min_initial_train_days <= 0:
        raise ValueError("min_initial_train_days must be > 0.")
    index = require_chronological_index(index)
    if len(index) == 0:
        raise ValueError("Need a non-empty index to anchor reference blocks.")
    return index.min() + pd.Timedelta(days=min_initial_train_days)


def available_reference_days(
    index: pd.DatetimeIndex,
    cutoff: pd.Timestamp | str,
    min_initial_train_days: int,
) -> int:
    """Number of calendar days available to reference blocks.

    This is the span from the anchor to the last pre-cutoff day, inclusive. It
    is the denominator of the packing bound and never depends on the outcome.
    """
    index = require_chronological_index(index)
    cut = pd.Timestamp(cutoff)
    anchor = anchor_origin(index, min_initial_train_days)
    pre = index[index < cut]
    if len(pre) == 0:
        raise ValueError(f"No pre-cutoff rows before {cut.date()}.")
    last = pre.max()
    if last < anchor:
        return 0
    return int((last - anchor).days) + 1


def packing_upper_bound(
    index: pd.DatetimeIndex,
    cutoff: pd.Timestamp | str,
    horizon_days: int,
    min_initial_train_days: int,
) -> int:
    """Maximum number of disjoint ``horizon_days`` blocks the calendar admits.

    For equal-length intervals on a contiguous daily line this bound is exact
    and is attained by direct tiling from the anchor.
    """
    if horizon_days <= 0:
        raise ValueError("horizon_days must be > 0.")
    span = available_reference_days(index, cutoff, min_initial_train_days)
    return int(span // horizon_days)


def enumerate_candidate_blocks(
    index: pd.DatetimeIndex,
    cutoff: pd.Timestamp | str,
    horizon_days: int,
    min_initial_train_days: int,
) -> list[Block]:
    """Every feasible reference block, one per admissible daily origin.

    A block is feasible when it starts on or after the anchor, has a fully
    observed ``horizon_days`` span in the index, and ends strictly before the
    training cutoff. Candidates deliberately overlap; disjointness is imposed
    later by an explicit selection rule.
    """
    if horizon_days <= 0:
        raise ValueError("horizon_days must be > 0.")
    index = require_chronological_index(index)
    cut = pd.Timestamp(cutoff)
    anchor = anchor_origin(index, min_initial_train_days)
    observed = set(index)
    candidates: list[Block] = []
    for start in index[(index >= anchor) & (index < cut)]:
        end = start + pd.Timedelta(days=horizon_days - 1)
        if end >= cut:
            continue
        span = pd.date_range(start, end, freq="D")
        if not observed.issuperset(span):
            continue
        candidates.append(
            Block(name=f"cand_{start.date()}", start=start, end=end)
        )
    return candidates


def maximum_disjoint_packing(candidates: list[Block]) -> list[Block]:
    """Maximum-cardinality disjoint subset, by the earliest-end greedy rule.

    Selecting the compatible interval with the earliest end is optimal for
    interval scheduling, so the returned length is the true maximum over all
    disjoint subsets of ``candidates`` -- not merely one greedy answer among
    many. This is the audit contrast against selecting greedily from a
    coarsened candidate set.
    """
    selected: list[Block] = []
    last_end: pd.Timestamp | None = None
    for block in sorted(candidates, key=lambda b: (b.end, b.start)):
        if last_end is None or block.start > last_end:
            selected.append(block)
            last_end = block.end
    return selected


def _forward_anchored_direct(
    index: pd.DatetimeIndex,
    cut: pd.Timestamp,
    horizon_days: int,
    min_initial_train_days: int,
) -> list[Block]:
    anchor = anchor_origin(index, min_initial_train_days)
    observed = set(index)
    blocks: list[Block] = []
    start = anchor
    while True:
        end = start + pd.Timedelta(days=horizon_days - 1)
        if end >= cut:
            break
        span = pd.date_range(start, end, freq="D")
        if not observed.issuperset(span):
            break
        blocks.append(Block(name=f"fwd_{len(blocks) + 1:02d}", start=start, end=end))
        start = end + pd.Timedelta(days=1)
    return blocks


def _backward_anchored_from_cutoff(
    index: pd.DatetimeIndex,
    cut: pd.Timestamp,
    horizon_days: int,
    min_initial_train_days: int,
) -> list[Block]:
    anchor = anchor_origin(index, min_initial_train_days)
    observed = set(index)
    blocks: list[Block] = []
    end = cut - pd.Timedelta(days=1)
    while True:
        start = end - pd.Timedelta(days=horizon_days - 1)
        if start < anchor:
            break
        span = pd.date_range(start, end, freq="D")
        if not observed.issuperset(span):
            break
        blocks.append(Block(name="bwd", start=start, end=end))
        end = start - pd.Timedelta(days=1)
    blocks.reverse()
    return [
        Block(name=f"bwd_{position + 1:02d}", start=b.start, end=b.end)
        for position, b in enumerate(blocks)
    ]


def _legacy_greedy_step30(
    index: pd.DatetimeIndex,
    cut: pd.Timestamp,
    horizon_days: int,
    min_initial_train_days: int,
) -> list[Block]:
    """Reproduce the locked artifact: greedy disjoint choice from 30-day steps.

    The candidate set is coarsened to a 30-calendar-day origin lattice before
    the greedy pass, which is why it can return fewer blocks than the calendar
    supports.
    """
    anchor = anchor_origin(index, min_initial_train_days)
    observed = set(index)
    last = index.max()
    coarse: list[Block] = []
    origin = anchor
    while True:
        end_exclusive = origin + pd.Timedelta(days=horizon_days)
        if end_exclusive > cut or end_exclusive - pd.Timedelta(days=1) > last:
            break
        end = end_exclusive - pd.Timedelta(days=1)
        span = pd.date_range(origin, end, freq="D")
        if observed.issuperset(span):
            coarse.append(Block(name="coarse", start=origin, end=end))
        origin = origin + pd.Timedelta(days=LEGACY_STEP_DAYS)

    selected: list[Block] = []
    last_end: pd.Timestamp | None = None
    for block in sorted(coarse, key=lambda b: b.start):
        if last_end is None or block.start > last_end:
            selected.append(
                Block(
                    name=f"legacy_{len(selected) + 1:02d}",
                    start=block.start,
                    end=block.end,
                )
            )
            last_end = block.end
    return selected


_RULE_DISPATCH = {
    PRIMARY_RULE: _forward_anchored_direct,
    SENSITIVITY_RULE: _backward_anchored_from_cutoff,
    LEGACY_RULE: _legacy_greedy_step30,
}


def reference_blocks(
    index: pd.DatetimeIndex,
    cutoff: pd.Timestamp | str,
    horizon_days: int,
    min_initial_train_days: int,
    origin_rule: str = PRIMARY_RULE,
) -> list[Block]:
    """Disjoint reference blocks under one frozen, outcome-independent rule."""
    if origin_rule not in _RULE_DISPATCH:
        raise ValueError(
            f"Unknown origin_rule {origin_rule!r}; expected one of {ORIGIN_RULES}."
        )
    if horizon_days <= 0:
        raise ValueError("horizon_days must be > 0.")
    index = require_chronological_index(index)
    cut = pd.Timestamp(cutoff)
    blocks = _RULE_DISPATCH[origin_rule](
        index, cut, horizon_days, min_initial_train_days
    )
    assert_disjoint(blocks)
    for block in blocks:
        if block.end >= cut:
            raise AssertionError(
                f"Reference block {block.name} crosses the training cutoff."
            )
        if block.length_days != horizon_days:
            raise AssertionError(
                f"Reference block {block.name} has the wrong length."
            )
    return blocks


def assert_disjoint(blocks: list[Block]) -> None:
    """Raise if any two reference blocks share a calendar day."""
    ordered = sorted(blocks, key=lambda b: b.start)
    for earlier, later in zip(ordered, ordered[1:]):
        if earlier.overlaps(later):
            raise AssertionError(
                f"Reference blocks {earlier.name} and {later.name} overlap."
            )


def block_fold(
    index: pd.DatetimeIndex,
    block: Block,
    name: str | None = None,
) -> Fold:
    """Expanding-training fold that scores exactly one reference block.

    Training is every observed day strictly before the block start, matching the
    expanding scheme already locked for the primary placebo construction.
    """
    index = require_chronological_index(index)
    train_idx = np.flatnonzero(index < block.start)
    test_idx = np.flatnonzero((index >= block.start) & (index <= block.end))
    if len(train_idx) == 0:
        raise ValueError(f"Block {block.name} has no training history.")
    if len(test_idx) != block.length_days:
        raise ValueError(
            f"Block {block.name} is not fully observed in the index."
        )
    return Fold(
        name=name or block.name,
        train_idx=train_idx,
        test_idx=test_idx,
        train_start=index[train_idx[0]],
        train_end=index[train_idx[-1]],
        test_start=index[test_idx[0]],
        test_end=index[test_idx[-1]],
    )


def geometry_frame(
    index: pd.DatetimeIndex,
    cutoff: pd.Timestamp | str,
    horizon_days: int,
    min_initial_train_days: int,
    origin_rule: str = PRIMARY_RULE,
) -> pd.DataFrame:
    """Tabular block geometry. Contains no outcome value of any kind."""
    blocks = reference_blocks(
        index,
        cutoff,
        horizon_days,
        min_initial_train_days,
        origin_rule=origin_rule,
    )
    rows = []
    for position, block in enumerate(blocks, start=1):
        fold = block_fold(index, block)
        rows.append({
            "origin_rule": origin_rule,
            "horizon_days": int(horizon_days),
            "block_index": position,
            "block_name": block.name,
            "test_start": fold.test_start.date().isoformat(),
            "test_end": fold.test_end.date().isoformat(),
            "train_start": fold.train_start.date().isoformat(),
            "train_end": fold.train_end.date().isoformat(),
            "n_train_days": int(len(fold.train_idx)),
            "n_test_days": int(len(fold.test_idx)),
        })
    return pd.DataFrame(rows, columns=_GEOMETRY_COLUMNS)


def conformal_rank(n_blocks: int, level: float) -> int:
    """Split-conformal order statistic ``ceil((K + 1) * level)``."""
    if n_blocks < 0:
        raise ValueError("n_blocks must be >= 0.")
    if not 0 < level < 1:
        raise ValueError(f"level must lie strictly in (0, 1), got {level}.")
    return int(math.ceil((n_blocks + 1) * level))


def frontier_capacity(n_blocks: int, levels) -> dict:
    """Finite-sample inference capacity implied by ``K`` reference blocks.

    Returns the rank p-value floor, the maximum attainable conformal coverage,
    and the explicit split of requested levels into finite and necessarily
    unbounded. Nothing here depends on any estimate.
    """
    if n_blocks <= 0:
        raise ValueError("Need at least one reference block.")
    requested = [float(level) for level in levels]
    finite = [lvl for lvl in requested if conformal_rank(n_blocks, lvl) <= n_blocks]
    unbounded = [lvl for lvl in requested if conformal_rank(n_blocks, lvl) > n_blocks]
    return {
        "n_reference_blocks": int(n_blocks),
        "rank_p_value_floor": 1.0 / (n_blocks + 1),
        "maximum_attainable_coverage": n_blocks / (n_blocks + 1),
        "requested_levels": requested,
        "finite_interval_levels": finite,
        "unbounded_interval_levels": unbounded,
        "any_level_unbounded": bool(unbounded),
        "five_percent_floor_attainable": bool(1.0 / (n_blocks + 1) <= 0.05),
        "order_statistic_rank_by_level": {
            f"{lvl:.2f}": conformal_rank(n_blocks, lvl) for lvl in requested
        },
    }


def minimum_blocks_for_level(level: float) -> int:
    """Smallest ``K`` whose split-conformal radius at ``level`` is finite.

    ``ceil((K + 1) * level) <= K`` first holds near ``level / (1 - level)``, but
    that closed form is not safe in binary floating point: at ``level = 0.80``,
    ``1 - level`` evaluates to ``0.19999999999999996`` and the quotient rounds
    up to 5 instead of the correct 4. The closed form is therefore used only as
    a starting point and the answer is settled by the exact rank predicate that
    the rest of this module uses.
    """
    if not 0 < level < 1:
        raise ValueError(f"level must lie strictly in (0, 1), got {level}.")
    candidate = max(1, int(math.floor(level / (1.0 - level))) - 1)
    while conformal_rank(candidate, level) > candidate:
        candidate += 1
    return candidate
