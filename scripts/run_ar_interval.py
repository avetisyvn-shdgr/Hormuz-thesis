"""Close the TSFM admission-test calibration leg with a raw AR interval.

Builds the AR-only baseline's raw, horizon-aware predictive interval (see
``src/lngfreight/ar_intervals.py``) from the pre-treatment rolling-origin
residuals already in ``baseline_forecasts.csv``, then applies the admission test
against the foundation-model benchmark on a MATCHED fold subset so MASE and
calibration are compared on exactly the folds where the AR interval is defined.

Runs in the core env (numpy/pandas only — no model weights). Upstream:
    python scripts/run_baseline.py          # -> baseline_forecasts.csv, scores
    python scripts/run_tsfm_benchmark.py ... # -> tsfm_benchmark_scores.csv
    python scripts/run_ar_interval.py

Writes (data/processed/):
    ar_interval_scores.csv    per-fold AR coverage diagnostics
    ar_interval_bands.csv     per-day AR point + interval
    ar_interval_summary.csv   per-target aggregate AR coverage
    tsfm_admission_test.csv   FINAL matched-subset verdict (overwrites placeholder)
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lngfreight import config  # noqa: E402
from lngfreight.ar_intervals import (  # noqa: E402
    aggregate_ar_interval,
    evaluate_ar_horizon_interval,
)
from lngfreight.tsfm import DEFAULT_LOWER_Q, DEFAULT_UPPER_Q, admission_test  # noqa: E402

AR_MODEL = "ar_lag1_7"
MIN_CALIB_FOLDS = 15


def _read(name: str) -> pd.DataFrame:
    path = config.path("data_processed") / name
    if not path.exists():
        raise FileNotFoundError(f"{path} not found. Run the upstream scripts first.")
    return pd.read_csv(path)


def _matched_aggregate(scores: pd.DataFrame, keep_starts: dict[str, set]) -> pd.DataFrame:
    """Mean MASE + coverage_error over only the AR-scored folds, per model/target."""
    scores = scores.copy()
    scores["test_start"] = scores["test_start"].astype(str)
    rows = []
    for (model, target), grp in scores.groupby(["model", "target"]):
        allowed = keep_starts.get(target, set())
        sub = grp[grp["test_start"].isin(allowed)]
        if sub.empty:
            continue
        row = {"model": model, "target": target, "mase_mean": float(sub["mase"].mean())}
        if "coverage_error" in sub.columns:
            row["coverage_error_mean"] = float(sub["coverage_error"].mean())
        rows.append(row)
    return pd.DataFrame(rows)


def main() -> None:
    out_dir = config.path("data_processed")
    baseline_fc = _read("baseline_forecasts.csv")
    ar_fc = baseline_fc[baseline_fc["model"] == AR_MODEL]
    if ar_fc.empty:
        raise SystemExit(f"No {AR_MODEL!r} rows in baseline_forecasts.csv.")

    all_scores, all_bands = [], []
    for target, grp in ar_fc.groupby("target"):
        scores, bands = evaluate_ar_horizon_interval(
            grp, lower_q=DEFAULT_LOWER_Q, upper_q=DEFAULT_UPPER_Q,
            min_calib_folds=MIN_CALIB_FOLDS,
        )
        all_scores.append(scores)
        all_bands.append(bands)

    ar_scores = pd.concat(all_scores, ignore_index=True)
    ar_bands = pd.concat(all_bands, ignore_index=True)
    ar_summary = aggregate_ar_interval(ar_scores)

    ar_scores.to_csv(out_dir / "ar_interval_scores.csv", index=False)
    ar_bands.to_csv(out_dir / "ar_interval_bands.csv", index=False)
    ar_summary.to_csv(out_dir / "ar_interval_summary.csv", index=False)

    print(f"AR raw horizon-aware interval (min_calib_folds={MIN_CALIB_FOLDS}, "
          f"nominal {DEFAULT_UPPER_Q - DEFAULT_LOWER_Q:.2f}):")
    print(ar_summary.to_string(index=False))

    # Matched fold subset: only the folds where the AR interval is defined.
    keep_starts = {
        t: set(g["test_start"].astype(str)) for t, g in ar_scores.groupby("target")
    }

    tsfm_scores = _read("tsfm_benchmark_scores.csv")
    baseline_scores = _read("baseline_scores.csv")

    tsfm_matched = _matched_aggregate(tsfm_scores, keep_starts)
    ar_mase_matched = _matched_aggregate(
        baseline_scores[baseline_scores["model"] == AR_MODEL], keep_starts
    )
    # Attach the AR interval's coverage error onto the AR MASE row.
    ar_cov = ar_summary[["target", "coverage_error_mean"]]
    ar_agg = ar_mase_matched.merge(ar_cov, on="target", how="left")

    print("\nMatched-subset means (only AR-scored folds):")
    print("  AR-only:")
    print(ar_agg.to_string(index=False))
    print("  Foundation models:")
    print(tsfm_matched.to_string(index=False))

    verdict = admission_test(tsfm_matched, ar_agg, ar_model=AR_MODEL)
    verdict.to_csv(out_dir / "tsfm_admission_test.csv", index=False)

    print("\nFINAL admission test (matched folds, calibration leg now assessable):")
    show = ["model", "target", "mase_improvement", "beats_ar_mase",
            "calibration_assessed", "keeps_calibration", "admitted"]
    print(verdict[[c for c in show if c in verdict.columns]].to_string(index=False))
    for _, row in verdict.iterrows():
        print(f"  - {row['model']}/{row['target']}: {row['verdict']}")

    print("\nInterpretation guard (CLAUDE.md rules 1, 2):")
    print(" - ADMITTED means only: eligible to ENTER the post-treatment comparison")
    print("   as a cross-check. It is NOT evidence of a causal effect, and it does")
    print("   NOT replace AR-only as the locked primary estimator.")
    print(" - The AR interval is a raw per-step-residual band, not a guaranteed-")
    print("   coverage interval; treat the calibration comparison as indicative.")
    print(f"\nwrote {out_dir / 'tsfm_admission_test.csv'}")


if __name__ == "__main__":
    main()
