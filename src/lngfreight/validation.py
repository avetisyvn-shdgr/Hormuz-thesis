"""Phase 4 scaffolding: chronological rolling-origin validation splits.

This is the FIRST modeling-phase primitive and it is deliberately
TARGET-AGNOSTIC: it decides *when* a model may train and test, never *what*
the dependent variable is. The freight target (Spark25S/30S vs. a proxy vs. a
descriptive reframing) is still unresolved pending data access, so nothing here
commits to it. When a target arrives it is simply a column the caller selects;
the fold geometry produced here does not change. That is what makes building it
now safe against the go/no-go decision.

Why it exists (CLAUDE.md rules 2 & 5):
  * Identification rests on models trained on PRE-TREATMENT data only, scored
    out-of-sample on later pre-treatment windows. A random k-fold split would
    leak the future into the past and is forbidden for this time series.
  * Every downstream estimator (seasonal-naive, SARIMAX-X, the ML counterfactual,
    the donor synthetic control) reuses THIS split geometry, so it is defined
    once, here, with explicit leakage guards rather than re-implemented per model.

Two leakage guards, enforced by construction AND re-asserted before return:
  1. Each test fold lies strictly AFTER its own training window (no future->past).
  2. Every fold lies strictly BEFORE the treatment cutoff, so no training or
     validation ever sees the disruption regime. The cutoff defaults to the
     explicitly locked primary treatment cutoff in settings.yaml.

Policy (fold lengths, step, scheme, cutoff) lives in settings.yaml `modeling:`,
never hard-coded here. Folds are returned as integer POSITIONAL indices into the
caller's index (sklearn-style), so any model or library can consume them. The
caller index must already be chronological; silently sorting it would make the
returned positions unsafe when applied back to the caller's unsorted object.

Pure function over an in-memory DatetimeIndex + local settings. No network, no
key, no I/O. Run the guards via: pytest -q
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from . import config


@dataclass(frozen=True)
class Fold:
    """One rolling-origin split. `train_idx`/`test_idx` are positional indices
    into the index passed to `rolling_origin_splits` (use df.iloc[fold.train_idx]).
    The four timestamps are inclusive bounds, for human inspection / logging."""
    name: str
    train_idx: np.ndarray
    test_idx: np.ndarray
    train_start: pd.Timestamp
    train_end: pd.Timestamp
    test_start: pd.Timestamp
    test_end: pd.Timestamp


def resolve_cutoff(settings: dict | None = None) -> pd.Timestamp:
    """The date training+validation must stay strictly before.

    "auto" (the default) = ``study_window.primary_treatment_cutoff``. This is
    explicit so adding a later event milestone cannot silently change model
    training. An explicit YYYY-MM-DD in validation settings overrides it.
    """
    settings = settings or config.settings()
    raw = settings.get("modeling", {}).get("validation", {}).get("cutoff", "auto")
    if raw == "auto":
        study = settings["study_window"]
        primary = study.get("primary_treatment_cutoff")
        if primary is None:
            raise ValueError(
                "study_window.primary_treatment_cutoff is required when "
                "modeling.validation.cutoff is 'auto'."
            )
        return pd.Timestamp(primary)
    return pd.Timestamp(raw)


def require_chronological_index(
    index: pd.DatetimeIndex,
    *,
    name: str = "index",
) -> pd.DatetimeIndex:
    """Return ``index`` as a DatetimeIndex or reject unsafe positional order.

    Fold positions are consumed with ``.iloc`` throughout the modeling stack.
    Sorting a private copy here would detach those positions from the caller's
    rows, so unsorted inputs fail loudly instead.
    """
    index = pd.DatetimeIndex(index)
    if not index.is_monotonic_increasing:
        raise ValueError(
            f"{name} must be chronologically sorted in increasing order before "
            "building or applying positional folds."
        )
    return index


def rolling_origin_splits(
    index: pd.DatetimeIndex,
    settings: dict | None = None,
    cutoff: pd.Timestamp | str | None = None,
) -> list[Fold]:
    """Build chronological rolling-origin folds over `index`.

    Parameters
    ----------
    index :
        The model's time index (e.g. ``panel.index``). Daily, but gaps are
        tolerated — bounds are by date, fold membership by mask, so missing
        calendar days simply yield smaller folds rather than misaligned ones.
        Must be sorted in increasing chronological order because returned fold
        positions refer to this exact caller order.
    settings :
        Parsed settings.yaml. Defaults to ``config.settings()``. Reads the
        ``modeling.validation`` block: ``scheme`` (expanding|sliding),
        ``initial_train_days``, ``horizon_days``, ``step_days``,
        ``sliding_train_days``, ``max_folds``.
    cutoff :
        Override the treatment cutoff. ``None`` -> resolve from settings.

    Returns
    -------
    list[Fold]
        Chronologically ordered. Empty list is never returned silently: if the
        usable pre-cutoff history cannot fit even one fold, raises ValueError
        with the shortfall, so a too-short window fails loudly (CLAUDE.md rule 1).
    """
    settings = settings or config.settings()
    cfg = settings.get("modeling", {}).get("validation", {})
    scheme = cfg.get("scheme", "expanding")
    initial_train = int(cfg.get("initial_train_days", 365))
    horizon = int(cfg.get("horizon_days", 30))
    step = int(cfg.get("step_days", 30))
    sliding_train = int(cfg.get("sliding_train_days", initial_train))
    max_folds = cfg.get("max_folds", None)

    if scheme not in {"expanding", "sliding"}:
        raise ValueError(f"scheme must be 'expanding' or 'sliding', got {scheme!r}.")
    for nm, v in (("initial_train_days", initial_train),
                  ("horizon_days", horizon), ("step_days", step)):
        if v <= 0:
            raise ValueError(f"modeling.validation.{nm} must be > 0, got {v}.")

    index = require_chronological_index(index)

    cut = pd.Timestamp(cutoff) if cutoff is not None else resolve_cutoff(settings)

    # Restrict to the usable PRE-cutoff history. Guard #2 starts here.
    usable = index[index < cut]
    if len(usable) == 0:
        raise ValueError(
            f"No data before the treatment cutoff {cut.date()}; cannot build "
            f"any pre-treatment fold. Check study window vs. treatment dates."
        )
    t0, tN = usable.min(), usable.max()

    folds: list[Fold] = []
    # `origin` is each fold's train_end (EXCLUSIVE) = its test_start (inclusive).
    origin = t0 + pd.Timedelta(days=initial_train)
    while True:
        test_start = origin
        test_end_excl = origin + pd.Timedelta(days=horizon)
        # Test fold must fit entirely within the usable pre-cutoff history.
        if test_end_excl - pd.Timedelta(days=1) > tN:
            break

        train_start = (test_start - pd.Timedelta(days=sliding_train)
                       if scheme == "sliding" else t0)
        train_start = max(train_start, t0)

        train_mask = (index >= train_start) & (index < origin)
        test_mask = (index >= test_start) & (index < test_end_excl)
        train_pos = np.flatnonzero(train_mask)
        test_pos = np.flatnonzero(test_mask)

        # A fold with an empty side (e.g. a long gap) is skipped, not emitted.
        if len(train_pos) and len(test_pos):
            folds.append(Fold(
                name=f"fold_{len(folds) + 1:02d}",
                train_idx=train_pos,
                test_idx=test_pos,
                train_start=index[train_pos[0]],
                train_end=index[train_pos[-1]],
                test_start=index[test_pos[0]],
                test_end=index[test_pos[-1]],
            ))
            if max_folds is not None and len(folds) >= int(max_folds):
                break
        origin = origin + pd.Timedelta(days=step)

    if not folds:
        span = (tN - t0).days
        raise ValueError(
            f"Pre-treatment history is too short for one fold: have {span} days "
            f"before {cut.date()}, need initial_train_days ({initial_train}) + "
            f"horizon_days ({horizon}) = {initial_train + horizon}. Lengthen the "
            f"study window or shorten the windows in settings.yaml."
        )

    _assert_no_leakage(folds, index, cut)
    return folds


def _assert_no_leakage(folds: list[Fold], index: pd.DatetimeIndex,
                       cut: pd.Timestamp) -> None:
    """Re-check both guards independently of how folds were built. Cheap
    insurance against a future refactor silently introducing leakage."""
    for f in folds:
        if f.test_start <= f.train_end:
            raise AssertionError(
                f"{f.name}: test_start {f.test_start.date()} not strictly after "
                f"train_end {f.train_end.date()} — temporal leakage."
            )
        if f.test_end >= cut or f.train_end >= cut:
            raise AssertionError(
                f"{f.name}: a fold reaches the treatment cutoff {cut.date()} — "
                f"post-treatment leakage."
            )
        if np.intersect1d(f.train_idx, f.test_idx).size:
            raise AssertionError(f"{f.name}: train/test positions overlap.")


def summary(folds: list[Fold]) -> pd.DataFrame:
    """Human-readable fold table for logging / notebook inspection."""
    return pd.DataFrame([{
        "fold": f.name,
        "train_start": f.train_start.date(),
        "train_end": f.train_end.date(),
        "n_train": len(f.train_idx),
        "test_start": f.test_start.date(),
        "test_end": f.test_end.date(),
        "n_test": len(f.test_idx),
    } for f in folds])
