"""Multi-event chokepoint shock propagation (Phase 2, SECONDARY estimator).

Fits a rank-1 response model to several historical chokepoint disruptions and
reports, per event, where displaced traffic appeared and on what timescale.

    Delta[e, c, h]  ~  a_e * v_e[c] * f(h)

    a_e    event amplitude (scalar)
    v_e[c] receiver loading for chokepoint c under event e  (unit norm)
    f(h)   response profile over horizon, SHARED across events (unit norm)

WHAT THIS IS. An out-of-sample PREDICTIVE model of network response. It is not
a causal spillover parameter (CLAUDE.md rule 2). Nothing here identifies a
treatment effect, and `v_e` is a description of co-movement after an event, not
a proof that a specific vessel rerouted.

HORMUZ IS SEALED. `fit_propagation` refuses any event whose role is HELD_OUT.
Unsealing happens in Phase 5 only, with the commit hash recorded first.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

BASELINE_DAYS = 365
PRE_WINDOW_DAYS = 28
WEEK = 7


@dataclass(frozen=True)
class EventSpec:
    """One disruption: which unit was hit, when, and what to call it."""

    name: str
    unit: str
    onset: pd.Timestamp
    role: str = "train"
    mechanism: str = ""

    @property
    def held_out(self) -> bool:
        return self.role == "HELD_OUT"


@dataclass
class PropagationFit:
    amplitude: dict[str, float]
    receiver_loadings: pd.DataFrame          # index event, columns chokepoint
    profile: pd.Series                       # index horizon week
    reallocation_share: dict[str, dict[str, float]]
    response: dict[str, pd.DataFrame]        # event -> (chokepoint x horizon)
    fitted: dict[str, pd.DataFrame]
    diagnostics: dict = field(default_factory=dict)


def _baseline(series: pd.Series, onset: pd.Timestamp) -> float:
    window = series.loc[: onset - pd.Timedelta(days=1)].tail(BASELINE_DAYS)
    base = float(window.mean())
    if not np.isfinite(base) or base <= 0:
        raise ValueError(f"Non-positive baseline for onset {onset.date()}.")
    return base


def normalise(panel: pd.DataFrame, onset: pd.Timestamp) -> pd.DataFrame:
    """Scale every chokepoint by its own pre-onset baseline (ratio, not z)."""
    bases = {c: _baseline(panel[c], onset) for c in panel.columns}
    return panel.divide(pd.Series(bases), axis=1)


def global_factor(
    normalised: pd.DataFrame, affected: list[str]
) -> pd.Series:
    """Cross-sectional median over units with no active disruption.

    Using the median of UNAFFECTED units keeps a treated unit's own collapse out
    of the common factor it is being compared against.
    """
    donors = [c for c in normalised.columns if c not in affected]
    if len(donors) < 5:
        raise ValueError(f"Need >=5 unaffected donors, got {len(donors)}.")
    return normalised[donors].median(axis=1)


def event_response(
    panel: pd.DataFrame,
    spec: EventSpec,
    horizon_weeks: int,
    affected: list[str],
) -> pd.DataFrame:
    """Weekly response of every chokepoint relative to its own pre-onset level."""
    norm = normalise(panel, spec.onset)
    resid = norm.subtract(global_factor(norm, affected), axis=0)

    pre = resid.loc[
        spec.onset - pd.Timedelta(days=PRE_WINDOW_DAYS) : spec.onset - pd.Timedelta(days=1)
    ].mean()

    rows = {}
    for h in range(horizon_weeks + 1):
        start = spec.onset + pd.Timedelta(days=h * WEEK)
        stop = start + pd.Timedelta(days=WEEK - 1)
        block = resid.loc[start:stop]
        if block.empty:
            break
        rows[h] = block.mean() - pre
    if not rows:
        raise ValueError(f"No post-onset data for {spec.name}.")
    return pd.DataFrame(rows)  # index chokepoint, columns horizon


def _rank1_als(
    stacked: dict[str, np.ndarray], iters: int = 200, tol: float = 1e-9
) -> tuple[dict[str, np.ndarray], np.ndarray, dict[str, float]]:
    """Alternating least squares for a shared profile and per-event loadings."""
    events = list(stacked)
    n_h = stacked[events[0]].shape[1]
    f = np.ones(n_h) / np.sqrt(n_h)
    v = {e: np.ones(stacked[e].shape[0]) / np.sqrt(stacked[e].shape[0]) for e in events}
    a = {e: 1.0 for e in events}

    prev = np.inf
    for _ in range(iters):
        for e in events:
            w = a[e] * f
            denom = float(w @ w)
            v[e] = (stacked[e] @ w) / denom if denom > 0 else v[e]
            n = np.linalg.norm(v[e])
            if n > 0:
                v[e] /= n
                a[e] = n
        num = np.zeros(n_h)
        den = 0.0
        for e in events:
            num += a[e] * (v[e] @ stacked[e])
            den += (a[e] ** 2) * float(v[e] @ v[e])
        if den > 0:
            f = num / den
        n = np.linalg.norm(f)
        if n > 0:
            f /= n
            for e in events:
                a[e] *= n
        loss = sum(
            float(((stacked[e] - a[e] * np.outer(v[e], f)) ** 2).sum()) for e in events
        )
        if abs(prev - loss) < tol:
            break
        prev = loss
    return v, f, a


def reallocation_share(
    response: pd.DataFrame, treated: str, baselines: pd.Series
) -> dict[str, float]:
    """Where the traffic went, in absolute transits per day.

    The response tensor is baseline-normalised, so a small chokepoint gaining two
    ships looks the same size as a large one gaining twenty. Summing normalised
    gains across 27 units therefore inflates the total badly. Every quantity here
    is converted back to transits per day with each unit's own baseline before
    anything is added up.

    `share` is gross gains over the treated unit's loss. It is an accounting
    ratio over co-movement, NOT proof that any particular vessel rerouted, and
    the net figure can be negative when the shock suppressed traffic globally.
    """
    mean_resp = response.mean(axis=1)
    absolute = mean_resp * baselines.reindex(mean_resp.index)
    loss = -float(absolute.get(treated, np.nan))
    if not np.isfinite(loss) or loss <= 0:
        return {"share": float("nan"), "loss_per_day": float("nan"),
                "gross_gain_per_day": float("nan"), "net_gain_per_day": float("nan")}
    others = absolute.drop(index=treated, errors="ignore")
    gross = float(others[others > 0].sum())
    net = float(others.sum())
    return {
        "share": gross / loss,
        "net_share": net / loss,
        "loss_per_day": loss,
        "gross_gain_per_day": gross,
        "net_gain_per_day": net,
    }


def placebo_reallocation(
    panel: pd.DataFrame,
    spec: EventSpec,
    affected: list[str],
    *,
    horizon_weeks: int = 8,
    n_draws: int = 200,
    seed: int = 20260826,
) -> pd.DataFrame:
    """Null distribution for the reallocation accounting.

    Summing residual gains across 27 chokepoints integrates a lot of noise: each
    unit's normalised wobble is multiplied back up by its own baseline, and the
    large chokepoints dominate. A raw gross-gain number is therefore
    uninterpretable on its own. This re-runs the identical accounting at random
    pseudo-onsets in quiet periods, so the observed value can be read against
    what the same procedure produces when nothing happened.

    Draws avoid a two-year guard band around every real event onset.
    """
    rng = np.random.default_rng(seed)
    span = pd.Timedelta(days=(horizon_weeks + 2) * WEEK)
    guard = pd.Timedelta(days=365)
    earliest = panel.index[0] + pd.Timedelta(days=BASELINE_DAYS + 30)
    latest = panel.index[-1] - span
    blocked = [spec.onset]

    rows = []
    attempts = 0
    while len(rows) < n_draws and attempts < n_draws * 40:
        attempts += 1
        offset = int(rng.integers(0, max((latest - earliest).days, 1)))
        cand = earliest + pd.Timedelta(days=offset)
        if any(abs((cand - b).days) < guard.days for b in blocked):
            continue
        try:
            fake = EventSpec(f"placebo_{len(rows)}", spec.unit, cand, "train")
            resp = event_response(panel, fake, horizon_weeks, affected)
            base = pd.Series({c: _baseline(panel[c], cand) for c in panel.columns})
            acc = reallocation_share(resp, spec.unit, base)
        except ValueError:
            continue
        if not np.isfinite(acc.get("gross_gain_per_day", np.nan)):
            continue
        rows.append({"onset": cand, **acc})
    return pd.DataFrame(rows)


def screened_receivers(
    response: pd.DataFrame,
    panel: pd.DataFrame,
    onset: pd.Timestamp,
    treated: str,
    *,
    z: float = 1.5,
) -> list[str]:
    """Receivers whose response is large against their own pre-onset variability."""
    pre = panel.loc[onset - pd.Timedelta(days=BASELINE_DAYS) : onset - pd.Timedelta(days=1)]
    weekly = pre.resample("W").mean()
    bases = pd.Series({c: _baseline(panel[c], onset) for c in panel.columns})
    sd = (weekly / bases).std()
    mean_resp = response.mean(axis=1)
    keep = [
        c for c in mean_resp.index
        if c != treated and sd.get(c, np.nan) > 0
        and abs(mean_resp[c]) > z * sd[c]
    ]
    return sorted(keep)


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


def fit_propagation(
    panel: pd.DataFrame,
    specs: list[EventSpec],
    *,
    horizon_weeks: int = 8,
    allow_held_out: bool = False,
) -> PropagationFit:
    """Fit the shared-profile rank-1 model over the training events."""
    sealed = [s for s in specs if s.held_out]
    train = [s for s in specs if not s.held_out]
    if not allow_held_out:
        # A held-out spec MAY be passed: it is needed so the unit is kept out of
        # the donor set that forms the common factor. What must never happen is
        # its post-onset data entering a training window.
        train = [s for s in train]
        horizon_end = pd.Timedelta(days=(horizon_weeks + 1) * WEEK)
        for held in sealed:
            for s in train:
                if s.onset + horizon_end > held.onset:
                    raise ValueError(
                        f"Training event {s.name!r} window reaches "
                        f"{(s.onset + horizon_end).date()}, past the sealed onset "
                        f"of {held.name!r} ({held.onset.date()}). Unsealing is a "
                        "Phase 5 action recorded in DECISION_LOG.md."
                    )
    else:
        train = [s for s in specs]
    if len(train) < 2:
        raise ValueError("Need at least two training events.")

    affected = sorted({s.unit for s in specs})
    responses = {
        s.name: event_response(panel, s, horizon_weeks, affected) for s in train
    }
    width = min(r.shape[1] for r in responses.values())
    responses = {k: r.iloc[:, :width] for k, r in responses.items()}

    order = list(panel.columns)
    stacked = {k: r.reindex(order).fillna(0.0).to_numpy() for k, r in responses.items()}
    v, f, a = _rank1_als(stacked)

    loadings = pd.DataFrame(
        {k: pd.Series(v[k], index=order) for k in responses}
    ).T
    profile = pd.Series(f, index=range(width), name="profile")
    fitted = {
        k: pd.DataFrame(
            a[k] * np.outer(v[k], f), index=order, columns=range(width)
        )
        for k in responses
    }
    unit_of = {s.name: s.unit for s in train}
    onset_of = {s.name: s.onset for s in train}
    shares = {
        k: reallocation_share(
            responses[k],
            unit_of[k],
            pd.Series({c: _baseline(panel[c], onset_of[k]) for c in panel.columns}),
        )
        for k in responses
    }

    ss_res = sum(
        float(((stacked[k] - fitted[k].to_numpy()) ** 2).sum()) for k in responses
    )
    ss_tot = sum(float((stacked[k] ** 2).sum()) for k in responses)
    diagnostics = {
        "n_train_events": len(train),
        "horizon_weeks": width - 1,
        "variance_explained": 1.0 - ss_res / ss_tot if ss_tot > 0 else float("nan"),
        "sealed_events": [s.name for s in sealed],
    }
    return PropagationFit(a, loadings, profile, shares, responses, fitted, diagnostics)


def sanity_gate(
    fit: PropagationFit, event: str, emitter: str, receiver: str
) -> dict:
    """Does the fit recover a known substitution edge, and how strongly?"""
    if event not in fit.receiver_loadings.index:
        return {"passed": False, "reason": f"event {event!r} not fitted"}
    row = fit.receiver_loadings.loc[event]
    signed = row * np.sign(fit.amplitude[event])
    rank = int(signed.rank(ascending=False).loc[receiver])
    return {
        "event": event,
        "emitter": emitter,
        "receiver": receiver,
        "loading": float(row.loc[receiver]),
        "rank_among_receivers": rank,
        "n_receivers": int(row.size),
        "passed": bool(float(row.loc[receiver]) > 0 and rank <= 5),
    }
