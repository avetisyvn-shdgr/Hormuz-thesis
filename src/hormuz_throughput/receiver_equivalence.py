"""B2 - receiver equivalence and the Red Sea positive control.

This module owns the single-pair reallocation statistic. `pair_reallocation`
was moved here verbatim from `propagation.py` under the B2 compatibility
migration in `docs/HORMUZ_TECHNICAL_EXECUTION_PLAN.md` v1.1, section 5. The
arithmetic is unchanged, there is only one implementation, and the legacy
import path still works through a shim in `propagation.py`.

Why the move: the statistic never depended on the rank-1 ALS fit. It reads the
panel, normalises each chokepoint by its own pre-onset baseline, subtracts a
donor median, and reports one emitter/receiver pair. Keeping it inside the
exploratory ALS module implied a dependency that does not exist.

What this module does NOT claim: an observed gain at a receiver is aggregate
correspondence consistent with rerouting. It is not vessel linkage, and it is
not a causal reallocation parameter.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .propagation import (
    BASELINE_DAYS,
    WEEK,
    EventSpec,
    _baseline,
    event_response,
)

__all__ = [
    "pair_reallocation",
    "response_frame",
    "admissible_onsets",
    "temporal_support",
    "finite_sample_p_value",
    "eligible_units",
    "pre_onset_scales",
    "spatial_family",
]


def pair_reallocation(
    panel: pd.DataFrame,
    spec: EventSpec,
    receiver: str,
    affected: list[str],
    *,
    horizon_weeks: int = 8,
    n_draws: int = 250,
    guard_onsets: list[pd.Timestamp] | None = None,
    seed: int = 20260826,
) -> dict:
    """Traffic change at ONE named receiver, against its own placebo null.

    The aggregate version of this accounting sums residual gains over every
    chokepoint and fails: 27 units of noise, each scaled up by its own baseline,
    outweigh the handful of transits a real event displaces. Testing a single
    pre-registered pair instead removes 26 units of noise and the signal
    separates cleanly.

    The receiver MUST be named before the event is examined. Picking it after
    looking at the loadings turns this into a selection statistic and the null
    below stops being valid.

    MIGRATION NOTE (B2). Moved verbatim from `propagation.py`; arithmetic
    unchanged. The `n_draws` sampling below draws pseudo-onsets WITH
    replacement and applies a single hard-coded 365-day guard. Plan v1.1
    section 7 requires the B2 temporal null to instead enumerate every unique
    admissible pseudo-onset once and to report 90/180/365-day guard
    sensitivity. That replacement null is built separately; this function is
    preserved as-is so the legacy result remains reproducible.
    """
    rng = np.random.default_rng(seed)
    guard = [pd.Timestamp(o) for o in (guard_onsets or [spec.onset])]

    def gain(onset: pd.Timestamp) -> float:
        resp = event_response(panel, EventSpec("probe", spec.unit, onset),
                              horizon_weeks, affected)
        return float(resp.loc[receiver].mean() * _baseline(panel[receiver], onset))

    observed = gain(spec.onset)
    loss = -float(
        event_response(panel, spec, horizon_weeks, affected).loc[spec.unit].mean()
        * _baseline(panel[spec.unit], spec.onset)
    )

    lo = panel.index[0] + pd.Timedelta(days=BASELINE_DAYS + 35)
    hi = panel.index[-1] - pd.Timedelta(days=(horizon_weeks + 2) * WEEK)
    draws: list[float] = []
    attempts = 0
    while len(draws) < n_draws and attempts < n_draws * 40:
        attempts += 1
        cand = lo + pd.Timedelta(days=int(rng.integers(0, max((hi - lo).days, 1))))
        if any(abs((cand - g).days) < 365 for g in guard):
            continue
        try:
            draws.append(gain(cand))
        except (ValueError, KeyError):
            continue
    null = np.asarray(draws)
    return {
        "event": spec.name,
        "emitter": spec.unit,
        "receiver": receiver,
        "observed_gain_per_day": observed,
        "emitter_loss_per_day": loss,
        "recovered_fraction": observed / loss if loss > 0 else float("nan"),
        "null_median": float(np.median(null)) if null.size else float("nan"),
        "null_p95": float(np.quantile(null, 0.95)) if null.size else float("nan"),
        "percentile_of_observed": float((null < observed).mean() * 100) if null.size else float("nan"),
        "n_draws": int(null.size),
    }




def response_frame(
    panel: pd.DataFrame,
    onset: pd.Timestamp,
    affected: list[str],
    horizon_weeks: int,
) -> pd.Series:
    """Mean post-onset weekly residual per chokepoint, in transits per day.

    One call yields every unit, so the anchor pair, both spatial families, and
    the temporal null all read the same arithmetic rather than recomputing it
    per pair. Positive means the unit ran above its own pre-onset level after
    the donor median is removed.
    """
    spec = EventSpec("probe", "", pd.Timestamp(onset))
    response = event_response(panel, spec, horizon_weeks, affected)
    means = response.mean(axis=1)
    bases = pd.Series(
        {unit: _baseline(panel[unit], pd.Timestamp(onset)) for unit in means.index}
    )
    return means * bases


def admissible_onsets(
    panel: pd.DataFrame,
    disruption_events: list[tuple[pd.Timestamp, pd.Timestamp, set[str]]],
    *,
    relevant_units: set[str],
    horizon_weeks: int,
    baseline_days: int,
    guard_days: int,
) -> pd.DatetimeIndex:
    """Every unique pseudo-onset admissible under one guard, each listed once.

    Admissible means: enough history to form a baseline, enough future to form
    the analysis window, at least `guard_days` from the onset of every
    disruption that touches `relevant_units`, and an analysis window that does
    not intersect such a disruption. No date appears twice and none is sampled.

    Exclusion is UNIT-LOCAL. A disruption at a chokepoint that is not under
    test does not delete that date for the pair being tested; its unit is
    already kept out of the donor median by `global_factor`. Applying every
    disruption window to every pair would delete most of the panel for the sake
    of events the statistic never reads, and open-ended windows would delete
    everything after their onset.
    """
    window_days = (horizon_weeks + 1) * 7
    first = panel.index[0] + pd.Timedelta(days=baseline_days + 35)
    last = panel.index[-1] - pd.Timedelta(days=window_days)
    if first > last:
        raise ValueError("panel is too short to admit any pseudo-onset")

    relevant = {
        (onset, end)
        for onset, end, units in disruption_events
        if set(units) & set(relevant_units)
    }
    keep = []
    for candidate in pd.date_range(first, last, freq="D"):
        if any(abs((candidate - onset).days) < guard_days for onset, _ in relevant):
            continue
        stop = candidate + pd.Timedelta(days=window_days - 1)
        if any(onset <= stop and candidate <= end for onset, end in relevant):
            continue
        keep.append(candidate)
    return pd.DatetimeIndex(keep)


def temporal_support(
    admissible: pd.DatetimeIndex, *, horizon_weeks: int
) -> dict:
    """Effective support of a temporal null, including its p-value floor.

    Consecutive pseudo-onsets share almost all of their analysis window, so the
    count of admissible dates overstates the independent information. The
    approximate non-overlapping window count is reported alongside it, and the
    attainable p-value floor is 1/(B+1).
    """
    window_days = (horizon_weeks + 1) * 7
    n = int(len(admissible))
    if n == 0:
        return {
            "n_unique_admissible_dates": 0,
            "approx_non_overlapping_windows": 0,
            "attainable_p_value_floor": float("nan"),
            "span_days": 0,
        }
    span = int((admissible[-1] - admissible[0]).days) + 1
    return {
        "n_unique_admissible_dates": n,
        "approx_non_overlapping_windows": int(max(1, span // window_days)),
        "attainable_p_value_floor": 1.0 / (n + 1),
        "span_days": span,
    }


def finite_sample_p_value(null_values: np.ndarray, observed: float) -> dict:
    """p = (1 + #{null >= observed}) / (B + 1), with B the unique draw count."""
    values = np.asarray(null_values, dtype=float)
    values = values[np.isfinite(values)]
    b = int(values.size)
    if b == 0:
        return {"p_value": float("nan"), "B": 0, "n_null_ge_observed": 0, "floor": float("nan")}
    n_ge = int((values >= observed).sum())
    return {
        "p_value": (1.0 + n_ge) / (b + 1.0),
        "B": b,
        "n_null_ge_observed": n_ge,
        "floor": 1.0 / (b + 1.0),
    }


def eligible_units(
    panel: pd.DataFrame,
    onset: pd.Timestamp,
    *,
    min_baseline: float,
    always_excluded: list[str],
    disrupted_units: list[str],
) -> list[str]:
    """Units passing the frozen support rules at one onset.

    Support is decided on PRE-ONSET baseline volume and on documented
    disruption status. No post-onset outcome enters this decision.
    """
    keep = []
    for unit in panel.columns:
        if unit in set(always_excluded) or unit in set(disrupted_units):
            continue
        try:
            base = _baseline(panel[unit], pd.Timestamp(onset))
        except ValueError:
            continue
        if base >= min_baseline:
            keep.append(unit)
    return sorted(keep)


def pre_onset_scales(
    panel: pd.DataFrame,
    onset: pd.Timestamp,
    affected: list[str],
    pre_onset_dates: pd.DatetimeIndex,
    *,
    horizon_weeks: int,
    min_draws: int,
) -> pd.Series:
    """Each unit's own pre-onset variability of the response statistic.

    Uses only pseudo-onsets strictly before the onset under test, so nothing
    from the event window informs the scale a unit is judged against.
    """
    usable = pre_onset_dates[pre_onset_dates < pd.Timestamp(onset)]
    if len(usable) < min_draws:
        raise ValueError(
            f"only {len(usable)} pre-onset draws available, need {min_draws}"
        )
    rows = []
    for date in usable:
        try:
            rows.append(response_frame(panel, date, affected, horizon_weeks))
        except (ValueError, KeyError):
            continue
    if len(rows) < min_draws:
        raise ValueError(f"only {len(rows)} usable pre-onset draws, need {min_draws}")
    stacked = pd.DataFrame(rows)
    scales = stacked.std(ddof=1)
    return scales.replace(0.0, np.nan)


def spatial_family(
    response: pd.Series,
    scales: pd.Series,
    eligible: list[str],
    anchor: str,
    *,
    sign: float,
) -> dict:
    """Standardised rank of the anchor within one eligible family.

    `sign` is +1 for a receiver gain family and -1 for an emitter loss family,
    so that a larger standardised value always means "more extreme in the
    direction the hypothesis predicts". Descriptive only: no p-value is
    returned, because cross-sectional exchangeability across chokepoints is not
    claimed.
    """
    members = [unit for unit in eligible if unit in response.index]
    values = {}
    for unit in members:
        scale = scales.get(unit, np.nan)
        if not np.isfinite(scale) or scale <= 0:
            continue
        values[unit] = sign * float(response[unit]) / float(scale)
    if anchor not in values:
        raise ValueError(f"anchor {anchor!r} did not survive the support rules")
    series = pd.Series(values).sort_values(ascending=False)
    observed = float(series[anchor])
    others = series.drop(anchor)
    return {
        "anchor": anchor,
        "anchor_standardised": observed,
        "family_size": int(len(series)),
        "rank_of_anchor": int(series.index.get_loc(anchor)) + 1,
        "max_statistic": float(series.iloc[0]),
        "max_statistic_unit": str(series.index[0]),
        "anchor_is_family_max": bool(series.index[0] == anchor),
        "percentile_within_family": (
            float((others < observed).mean() * 100) if len(others) else float("nan")
        ),
        "family_median": float(series.median()),
        "standardised_values": {k: float(v) for k, v in series.items()},
        "inferential_p_value": None,
        "p_value_withheld_reason": (
            "cross-sectional exchangeability across chokepoints is not defensible"
        ),
    }
