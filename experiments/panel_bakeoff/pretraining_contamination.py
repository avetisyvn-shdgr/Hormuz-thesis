"""Bound the Chronos-2 pretraining-overlap risk with a by-origin advantage table.

Chronos-2 was released 2025-10-20, so its weights cannot have seen anything
dated after that.  The event window (2026-02-28 to 2026-07-07) is therefore
provably outside the pretraining corpus.  The pre-event bake-off is not: seven
of the eight rolling origins score windows that close before the release, and
the eighth closes sixteen days after it.  The generalisable claim -- "Chronos
forecasts this panel better than AR" -- rests on those pre-event folds, so it
carries an overlap risk the event result does not.

This refits nothing.  It reads the executed bake-off scores and asks whether the
Chronos advantage is concentrated in the origins with the most overlap
opportunity, which is the signature contamination would leave.  A flat or rising
advantage across origins does not prove the corpus is clean; it bounds how much
of the measured advantage a contamination story can plausibly claim.

Run with:

    .venv/bin/python -m experiments.panel_bakeoff.pretraining_contamination
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from .protocol import OUTPUT_DIR
from .summarize import BOOTSTRAP_DRAWS, BOOTSTRAP_SEED


CHALLENGER = "chronos2_univariate"
BASELINE = "ar_lag1_7"
PRIMARY_PANEL = "composition_28x5"
# docs/MODERN_TSFM_BENCHMARK.md: Chronos-2 (Amazon, released 2025-10-20).
MODEL_RELEASE = pd.Timestamp("2025-10-20")
CLEANEST_FOLD = "fold_08"


def _paired_scores() -> pd.DataFrame:
    """One row per panel-fold-horizon-series with both models' MASE."""
    frames = [
        pd.read_csv(OUTPUT_DIR / name, parse_dates=["origin"])
        for name in ("chronos_scores.csv", "classical_scores.csv")
    ]
    scores = pd.concat(frames, ignore_index=True)
    scores = scores.loc[scores["model"].isin({CHALLENGER, BASELINE})]
    keys = ["panel", "fold", "origin", "horizon", "portname", "vessel_class"]
    if scores.duplicated(["model", *keys]).any():
        raise ValueError("duplicate model-series-window scores in the bake-off output.")
    paired = scores.pivot_table(index=keys, columns="model", values="mase").reset_index()
    if paired[[CHALLENGER, BASELINE]].isna().any().any():
        raise ValueError("the two models were not scored on an identical window set.")
    return paired


def _window(origin: pd.Timestamp, horizon: int) -> tuple[pd.Timestamp, int]:
    """Scored window end, and how many of its days fall after the model release."""
    end = origin + pd.Timedelta(days=horizon - 1)
    dates = pd.date_range(origin, periods=horizon, freq="D")
    return end, int((dates > MODEL_RELEASE).sum())


def _reduction(part: pd.DataFrame) -> float:
    return 1.0 - part[CHALLENGER].mean() / part[BASELINE].mean()


def _cube(part: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, list[str], list[str]]:
    """Reshape to (port, fold, vessel_class) so chokepoints resample as clusters."""
    ports = sorted(part["portname"].unique())
    folds = sorted(part["fold"].unique())
    classes = sorted(part["vessel_class"].unique())
    index = pd.MultiIndex.from_product(
        [ports, folds, classes], names=["portname", "fold", "vessel_class"]
    )
    indexed = part.set_index(["portname", "fold", "vessel_class"]).reindex(index)
    shape = (len(ports), len(folds), len(classes))
    challenger = indexed[CHALLENGER].to_numpy().reshape(shape)
    baseline = indexed[BASELINE].to_numpy().reshape(shape)
    if not np.isfinite(challenger).all() or not np.isfinite(baseline).all():
        raise ValueError("incomplete paired cube; the by-origin contrast needs a full grid.")
    return challenger, baseline, ports, folds


def _bootstrap_reduction(
    part: pd.DataFrame, seed: int, resample_folds: bool
) -> np.ndarray:
    """Cluster bootstrap of the macro MASE reduction, resampling chokepoints.

    Folds are resampled too when the leg pools several origins, so the interval
    covers origin-to-origin variation as well as cross-sectional variation. A
    single-origin leg has no fold dimension to resample.
    """
    challenger, baseline, ports, folds = _cube(part)
    rng = np.random.default_rng(seed)
    draws = np.empty(BOOTSTRAP_DRAWS, dtype="float64")
    for draw in range(BOOTSTRAP_DRAWS):
        sampled_ports = rng.integers(0, len(ports), size=len(ports))
        sampled_folds = (
            rng.integers(0, len(folds), size=len(folds))
            if resample_folds
            else np.arange(len(folds))
        )
        c = challenger[sampled_ports][:, sampled_folds, :]
        b = baseline[sampled_ports][:, sampled_folds, :]
        draws[draw] = 1.0 - c.mean() / b.mean()
    return draws


def _by_origin(paired: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (panel, horizon, fold), part in paired.groupby(
        ["panel", "horizon", "fold"], sort=True
    ):
        origin = part["origin"].iloc[0]
        end, post_release_days = _window(origin, int(horizon))
        seed = BOOTSTRAP_SEED + int(horizon) + 7919 * int(fold.split("_")[1])
        draws = _bootstrap_reduction(part, seed, resample_folds=False)
        rows.append({
            "panel": panel,
            "horizon": int(horizon),
            "fold": fold,
            "origin": str(origin.date()),
            "scored_end": str(end.date()),
            "days_after_model_release": post_release_days,
            "n_series": len(part),
            "chronos_mase": float(part[CHALLENGER].mean()),
            "ar_mase": float(part[BASELINE].mean()),
            "mase_reduction": _reduction(part),
            "paired_win_rate": float((part[CHALLENGER] < part[BASELINE]).mean()),
            "cluster_bootstrap_ci_lower": float(np.quantile(draws, 0.025)),
            "cluster_bootstrap_ci_upper": float(np.quantile(draws, 0.975)),
        })
    return pd.DataFrame(rows).sort_values(
        ["panel", "horizon", "fold"], kind="stable", ignore_index=True
    )


def _contrast(paired: pd.DataFrame, panel: str, horizon: int) -> dict[str, object]:
    """Cleanest origin against the rest, with a joint chokepoint bootstrap."""
    part = paired.loc[paired["panel"].eq(panel) & paired["horizon"].eq(horizon)]
    clean = part.loc[part["fold"].eq(CLEANEST_FOLD)]
    rest = part.loc[~part["fold"].eq(CLEANEST_FOLD)]
    if clean.empty or rest.empty:
        raise ValueError(f"missing {CLEANEST_FOLD} or its comparison origins.")

    clean_cube = _cube(clean)
    rest_cube = _cube(rest)
    if clean_cube[2] != rest_cube[2]:
        raise ValueError("the two legs do not share a chokepoint set.")
    ports = clean_cube[2]
    rng = np.random.default_rng(BOOTSTRAP_SEED + 104729 + int(horizon))
    differences = np.empty(BOOTSTRAP_DRAWS, dtype="float64")
    for draw in range(BOOTSTRAP_DRAWS):
        sampled_ports = rng.integers(0, len(ports), size=len(ports))
        sampled_folds = rng.integers(0, len(rest_cube[3]), size=len(rest_cube[3]))
        clean_c = clean_cube[0][sampled_ports]
        clean_b = clean_cube[1][sampled_ports]
        rest_c = rest_cube[0][sampled_ports][:, sampled_folds, :]
        rest_b = rest_cube[1][sampled_ports][:, sampled_folds, :]
        differences[draw] = (1.0 - clean_c.mean() / clean_b.mean()) - (
            1.0 - rest_c.mean() / rest_b.mean()
        )

    origin_reductions = (
        part.groupby("fold").apply(_reduction, include_groups=False).sort_index()
    )
    index = np.arange(1, len(origin_reductions) + 1, dtype="float64")
    slope = float(np.polyfit(index, origin_reductions.to_numpy(), 1)[0])

    return {
        "panel": str(panel),
        "horizon": int(horizon),
        "cleanest_fold": CLEANEST_FOLD,
        "cleanest_origin_reduction": float(_reduction(clean)),
        "earlier_origins_reduction": float(_reduction(rest)),
        "difference": float(_reduction(clean) - _reduction(rest)),
        "difference_ci_lower": float(np.quantile(differences, 0.025)),
        "difference_ci_upper": float(np.quantile(differences, 0.975)),
        "cleanest_origin_advantage_positive": bool(_reduction(clean) > 0),
        "reduction_slope_per_origin": slope,
        "n_origins": int(part["fold"].nunique()),
    }


def main() -> None:
    paired = _paired_scores()
    by_origin = _by_origin(paired)
    contrasts = [
        _contrast(paired, str(panel), int(horizon))
        for panel in sorted(paired["panel"].unique())
        for horizon in sorted(paired["horizon"].unique())
    ]

    primary = by_origin.loc[by_origin["panel"].eq(PRIMARY_PANEL)]
    clean_rows = primary.loc[primary["fold"].eq(CLEANEST_FOLD)]
    summary = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "question": (
            "Is the pre-event Chronos-over-AR advantage concentrated in the rolling "
            "origins with the most pretraining-overlap opportunity?"
        ),
        "chronos2_release_date": str(MODEL_RELEASE.date()),
        "event_window_is_provably_post_release": True,
        "bake_off_scored_span": {
            "start": str(by_origin["origin"].min()),
            "end": str(by_origin["scored_end"].max()),
        },
        "origins_with_any_post_release_scored_day": sorted(
            by_origin.loc[by_origin["days_after_model_release"].gt(0), "fold"].unique()
        ),
        "cleanest_origin_advantage_positive_at_every_horizon": bool(
            clean_rows["mase_reduction"].gt(0).all()
        ),
        "contrasts": contrasts,
        "bootstrap": {
            "draws": BOOTSTRAP_DRAWS,
            "seed": BOOTSTRAP_SEED,
            "clusters": "chokepoints; rolling origins additionally resampled in the pooled leg",
        },
        "confound": (
            "Chronos context length grows with the origin and caps at 2,048 days from "
            "fold_06, so a raw trend across origins mixes elapsed time with context "
            "length. The direction of that confound favours the later origins."
        ),
        "what_this_cannot_show": (
            "A flat advantage across origins is evidence against a contamination-driven "
            "advantage, not proof of a clean corpus. Amazon does not disclose the "
            "Chronos-2 pretraining corpus at a level that would let absence be verified."
        ),
    }

    table_path = OUTPUT_DIR / "chronos_by_origin_advantage.csv"
    summary_path = OUTPUT_DIR / "chronos_pretraining_contamination.json"
    by_origin.to_csv(table_path, index=False)
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(primary.drop(columns=["panel"]).to_string(index=False))
    print()
    for contrast in contrasts:
        if contrast["panel"] != PRIMARY_PANEL:
            continue
        print(
            f"h{contrast['horizon']}: cleanest origin {contrast['cleanest_origin_reduction']:+.4f} "
            f"vs earlier {contrast['earlier_origins_reduction']:+.4f} "
            f"(difference {contrast['difference']:+.4f}, 95% CI "
            f"[{contrast['difference_ci_lower']:+.4f}, {contrast['difference_ci_upper']:+.4f}]; "
            f"slope {contrast['reduction_slope_per_origin']:+.5f}/origin)"
        )
    print(f"\nwrote {table_path}")
    print(f"wrote {summary_path}")


if __name__ == "__main__":
    main()
