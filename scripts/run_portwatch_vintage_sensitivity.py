"""Vintage + window sensitivity for the PortWatch throughput primary.

Answers one question and nothing else: how much of the reported
disruption-associated shortfall is a property of the *data vintage* and the
*window end*, rather than of the event?

Design (deliberately narrow):

* The reporting basis stays the pinned vintage. This script never writes to
  the primary artifacts and never re-pins anything.
* The comparison vintage is the 2026-08-09 capture, registered as
  ``portwatch_chokepoints_vintage_20260809_snapshot`` and read through
  ``registry.get_variable()`` so the checksum is verified and the read is
  logged (CLAUDE.md rule 7).
* The estimator is the project's own working-specification primary
  (``ar_lag1_7`` via ``arx_forecast``) with the locked 2026-02-28 cutoff. It
  is reused, not reimplemented, so any difference is attributable to inputs.

A self-check runs first: the harness rebuilds the pinned-vintage result from
raw and must reproduce the committed
``counterfactual_post_treatment_summary.csv`` value. If it does not, the
script fails loudly rather than reporting an unvalidated comparison.

Run from the repo root:
    python scripts/run_portwatch_vintage_sensitivity.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lngfreight import config, registry  # noqa: E402
from lngfreight.baselines import arx_forecast  # noqa: E402
from lngfreight.validation import Fold, resolve_cutoff  # noqa: E402

PINNED_VARIABLE = "portwatch_chokepoints_snapshot"
VINTAGE_VARIABLE = "portwatch_chokepoints_vintage_20260809_snapshot"

# Column mapping for the two working-specification outcomes.
TARGET_COLUMNS = {
    "hormuz_tanker_transits": "n_tanker",
    "hormuz_tanker_capacity": "capacity_tanker",
}
CHOKEPOINT = "Strait of Hormuz"

# Sensitivity window end, 1-day buffer on the 2026-08-02 vintage max. The
# v1/v2 rule was a 5-day buffer; the departure is deliberate and documented in
# docs/PORTWATCH_VINTAGE_REGISTER.md so that the 2026-07-29 Damietta event
# falls inside the analysed window.
SENSITIVITY_FULL_END = pd.Timestamp("2026-08-01")

REPRODUCTION_TOLERANCE = 1e-6


def _hormuz_series(csv_path: Path, column: str) -> pd.Series:
    """Extract one Hormuz column, applying the project's capacity-artifact policy.

    ``imputation.capacity_zero_with_transits`` masks days where transit count is
    positive but deadweight capacity logged zero (AIS rounding / sub-resolution
    vessels), because those are not genuine closure zeros. The same rule is
    applied here so the harness matches ``lngfreight.clean``; without it the
    capacity outcome does not reproduce the committed result.
    """
    frame = pd.read_csv(csv_path, encoding="utf-8-sig", parse_dates=["date"])
    wanted = ["date", column] + ([] if column == "n_tanker" else ["n_tanker"])
    subset = frame.loc[frame["portname"] == CHOKEPOINT, wanted]
    if subset.empty:
        raise ValueError(f"no {CHOKEPOINT} rows found in {csv_path}")
    subset = subset.set_index("date").sort_index()
    if subset.index.has_duplicates:
        raise ValueError(f"duplicate dates for {CHOKEPOINT} in {csv_path}")

    series = subset[column].astype("float64")
    policy = config.settings().get("imputation", {}).get("capacity_zero_with_transits")
    if column.startswith("capacity") and policy == "mask":
        artifact = (series == 0) & (subset["n_tanker"].astype("float64") > 0)
        series = series.mask(artifact)
    elif column.startswith("capacity") and policy != "keep":
        raise ValueError(
            f"imputation.capacity_zero_with_transits must be 'mask' or 'keep', "
            f"got {policy!r}."
        )
    return series


def _shortfall(series: pd.Series, *, start: pd.Timestamp, end: pd.Timestamp) -> dict:
    """Fit the working-specification primary and return the shortfall summary."""
    window = series.loc[(series.index >= start) & (series.index <= end)]
    panel = window.to_frame(name="y")
    cutoff = resolve_cutoff()

    train_idx = np.flatnonzero(panel.index < cutoff)
    test_idx = np.flatnonzero(panel.index >= cutoff)
    if len(train_idx) == 0 or len(test_idx) == 0:
        raise ValueError(f"cutoff {cutoff.date()} does not split this window")

    fold = Fold(
        name="post_treatment",
        train_idx=train_idx,
        test_idx=test_idx,
        train_start=panel.index[train_idx[0]],
        train_end=panel.index[train_idx[-1]],
        test_start=panel.index[test_idx[0]],
        test_end=panel.index[test_idx[-1]],
    )
    y_pred = arx_forecast(panel, target="y", fold=fold, exog_cols=[], y_lags=(1, 7))
    y_true = panel.loc[y_pred.index, "y"]
    loss = y_pred - y_true
    return {
        "window_start": panel.index[0].date(),
        "window_end": panel.index[-1].date(),
        "pre_days": int(len(train_idx)),
        "post_days": int(len(test_idx)),
        "pre_mean_observed": float(panel.iloc[train_idx]["y"].mean()),
        "observed_sum": float(y_true.sum()),
        "counterfactual_sum": float(y_pred.sum()),
        "cumulative_throughput_loss": float(loss.sum()),
        "mean_daily_throughput_loss": float(loss.mean()),
    }


def _committed_reference(target: str) -> dict:
    path = config.path("data_processed") / "counterfactual_post_treatment_summary.csv"
    frame = pd.read_csv(path)
    row = frame[(frame["model"] == "ar_lag1_7") & (frame["target"] == target)]
    if len(row) != 1:
        raise ValueError(f"expected exactly one committed ar_lag1_7 row for {target}")
    return row.iloc[0].to_dict()


def main() -> None:
    root = config.ROOT
    cutoff = resolve_cutoff()
    window = config.settings()["study_window"]
    full_start = pd.Timestamp(window["full_start"])
    primary_end = pd.Timestamp(window["full_end"])

    pinned_artifact = registry.get_variable(
        PINNED_VARIABLE,
        query={
            "consumer": "scripts/run_portwatch_vintage_sensitivity.py",
            "analysis_scope": "sensitivity_only",
        },
    )
    artifact = registry.get_variable(
        VINTAGE_VARIABLE,
        query={"consumer": "scripts/run_portwatch_vintage_sensitivity.py"},
        allow_sensitivity=True,
    )
    print(f"cutoff (locked): {cutoff.date()}")
    print(f"pinned aggregate:  {pinned_artifact.path.relative_to(root)}")
    print(f"pinned sha256:     {pinned_artifact.sha256}")
    print(f"vintage artifact:  {artifact.path.relative_to(root)}")
    print(f"vintage sha256:    {artifact.sha256}")

    rows = []
    for target, column in TARGET_COLUMNS.items():
        pinned = _hormuz_series(pinned_artifact.path, column)
        vintage = _hormuz_series(artifact.path, column)

        # (1) Self-check: reproduce the committed pinned-vintage result.
        repro = _shortfall(pinned, start=full_start, end=primary_end)
        reference = _committed_reference(target)
        delta = abs(
            repro["mean_daily_throughput_loss"]
            - float(reference["mean_daily_throughput_loss"])
        )
        rel = delta / abs(float(reference["mean_daily_throughput_loss"]))
        status = "REPRODUCED" if rel <= REPRODUCTION_TOLERANCE else "MISMATCH"
        print(
            f"\n[{target}] harness self-check vs committed summary: {status}"
            f" (committed {float(reference['mean_daily_throughput_loss']):.6f},"
            f" harness {repro['mean_daily_throughput_loss']:.6f},"
            f" rel.diff {rel:.2e})"
        )
        if status == "MISMATCH":
            raise SystemExit(
                f"harness failed to reproduce the committed {target} result; "
                "refusing to report an unvalidated vintage comparison."
            )

        # (2) Vintage held at the primary window end: isolates the revision.
        vintage_same_window = _shortfall(vintage, start=full_start, end=primary_end)
        # (3) Vintage extended to the sensitivity window end: adds persistence.
        vintage_extended = _shortfall(vintage, start=full_start, end=SENSITIVITY_FULL_END)

        for label, res in (
            ("pinned_primary", repro),
            ("vintage_same_window", vintage_same_window),
            ("vintage_extended_window", vintage_extended),
        ):
            rows.append({"target": target, "scenario": label, **res})

    out = pd.DataFrame(rows)
    out_path = config.path("data_processed") / "portwatch_vintage_sensitivity.csv"
    out.to_csv(out_path, index=False)

    pd.set_option("display.width", 200)
    print("\n=== vintage / window sensitivity ===")
    print(
        out[[
            "target", "scenario", "window_end", "post_days",
            "pre_mean_observed", "mean_daily_throughput_loss",
            "cumulative_throughput_loss",
        ]].to_string(index=False)
    )

    print("\n=== interpretation guard ===")
    print(" - The pinned vintage remains the reporting basis; this is a sensitivity layer.")
    print(" - vintage_same_window isolates the DATA REVISION (same dates, different vintage).")
    print(" - vintage_extended_window adds the WINDOW EXTENSION on top of that revision;")
    print("   the two effects are reported separately and must not be conflated.")
    print(" - The extended window contains the 2026-07-29 Damietta confound and spans a")
    print("   regime mixture (closure -> 06-17 MoU -> renewed attacks); see EVENT_CHRONOLOGY.md.")
    print(f"\nwrote {out_path}")


if __name__ == "__main__":
    main()
