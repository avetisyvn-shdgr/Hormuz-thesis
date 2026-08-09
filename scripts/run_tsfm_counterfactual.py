"""Counterfactual cross-check with an ADMITTED foundation model (robustness).

Re-estimates the post-treatment observed-minus-counterfactual throughput shortfall
using a foundation model (default Chronos-2, the best-calibrated admitted model)
instead of AR-only, and compares the cumulative shortfall against the AR-only
estimate in ``counterfactual_post_treatment_summary.csv``. The purpose is a single
robustness sentence: does the headline shortfall survive a stronger, better-
calibrated forecaster? It does NOT promote the model into the locked pipeline and
is NOT causal inference on its own (CLAUDE.md rule 2).

Needs real weights -> run in the isolated env (.venv-bench for chronos2/moirai,
.venv-timesfm for timesfm; see docs/MODERN_TSFM_BENCHMARK.md). Upstream:

    python scripts/run_counterfactual.py        # -> AR-only shortfall (reference)
    .venv-bench/bin/python scripts/run_tsfm_counterfactual.py \
        --model chronos2 --acknowledge-benchmark-only

The dependency-free plumbing check (core env; NOT a model result):

    python scripts/run_tsfm_counterfactual.py --model stub --acknowledge-benchmark-only
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lngfreight import config  # noqa: E402
from lngfreight.specification import working_specification  # noqa: E402
from lngfreight.tsfm import (  # noqa: E402
    DEFAULT_LOWER_Q,
    DEFAULT_UPPER_Q,
    MODEL_REGISTRY,
    configure_deterministic_execution,
    counterfactual_shortfall,
)
from lngfreight.validation import resolve_cutoff  # noqa: E402

AR_MODEL = "ar_lag1_7"


def _load_panel() -> pd.DataFrame:
    path = config.path("data_processed") / "panel_aligned.csv"
    if not path.exists():
        raise FileNotFoundError(f"{path} not found. Build the panel first.")
    return pd.read_csv(path, parse_dates=["date"]).set_index("date")


def _ar_reference() -> tuple[pd.DataFrame, pd.DataFrame]:
    out_dir = config.path("data_processed")
    summary_path = out_dir / "counterfactual_post_treatment_summary.csv"
    daily_path = out_dir / "counterfactual_post_treatment.csv"
    missing = [str(path) for path in (summary_path, daily_path) if not path.exists()]
    if missing:
        raise FileNotFoundError(
            "Matched AR reference artifacts are required before the TSFM "
            f"comparison; missing {missing}."
        )
    summary = pd.read_csv(summary_path)
    daily = pd.read_csv(daily_path, parse_dates=["date"])
    return (
        summary.loc[summary["model"].eq(AR_MODEL)].copy(),
        daily.loc[daily["model"].eq(AR_MODEL)].copy(),
    )


def _attach_matched_ar_reference(
    *,
    target: str,
    tsfm_daily: pd.DataFrame,
    tsfm_summary: dict[str, object],
    ar_summary: pd.DataFrame,
    ar_daily: pd.DataFrame,
) -> dict[str, object]:
    """Attach AR comparison only after exact scored-date and outcome matching."""
    ar_row = ar_summary.loc[ar_summary["target"].eq(target)]
    if len(ar_row) != 1:
        raise ValueError(
            f"Expected one active {AR_MODEL} summary row for {target!r}; "
            f"found {len(ar_row)}."
        )
    ar_row = ar_row.iloc[0]
    tsfm_valid = (
        tsfm_daily.dropna(subset=["y_true", "y_pred"])
        .sort_values("date")
        .reset_index(drop=True)
    )
    ar_valid = (
        ar_daily.loc[ar_daily["target"].eq(target)]
        .dropna(subset=["y_true", "y_pred"])
        .sort_values("date")
        .reset_index(drop=True)
    )
    dates_match = tsfm_valid["date"].equals(ar_valid["date"])
    observed_match = (
        len(tsfm_valid) == len(ar_valid)
        and np.allclose(
            tsfm_valid["y_true"].to_numpy(dtype="float64"),
            ar_valid["y_true"].to_numpy(dtype="float64"),
        )
    )
    summary_match = (
        str(tsfm_summary["start"]) == str(ar_row["start"])
        and str(tsfm_summary["end"]) == str(ar_row["end"])
        and int(tsfm_summary["n_days"]) == int(ar_row["n_days"])
        and np.isclose(
            float(tsfm_summary["observed_sum"]),
            float(ar_row["observed_sum"]),
        )
    )
    if not dates_match or not observed_match or not summary_match:
        raise ValueError(
            f"Refusing mismatched TSFM/AR comparison for {target!r}: "
            f"dates_match={dates_match}, observed_match={observed_match}, "
            f"summary_match={summary_match}."
        )

    ar_loss = float(ar_row["cumulative_throughput_loss"])
    tsfm_loss = float(tsfm_summary["cumulative_throughput_loss"])
    return {
        **tsfm_summary,
        "ar_start": ar_row["start"],
        "ar_end": ar_row["end"],
        "ar_n_days": int(ar_row["n_days"]),
        "ar_observed_sum": float(ar_row["observed_sum"]),
        "ar_cumulative_throughput_loss": ar_loss,
        "matched_ar_dates": True,
        "matched_ar_observed": True,
        "pct_diff_vs_ar": (tsfm_loss - ar_loss) / ar_loss * 100.0,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default="chronos2",
                        help="chronos2 (default) | moirai | timesfm | stub")
    parser.add_argument("--acknowledge-benchmark-only", action="store_true")
    parser.add_argument("--device-map", default="cpu")
    parser.add_argument("--lower-q", type=float, default=DEFAULT_LOWER_Q)
    parser.add_argument("--upper-q", type=float, default=DEFAULT_UPPER_Q)
    args = parser.parse_args()

    if not args.acknowledge_benchmark_only:
        raise SystemExit(
            "Refusing to run without --acknowledge-benchmark-only. This is a "
            "benchmark robustness cross-check, not a promoted estimator."
        )
    if args.model not in MODEL_REGISTRY:
        raise SystemExit(f"Unknown model {args.model!r}; choose from {sorted(MODEL_REGISTRY)}.")

    spec = working_specification()
    targets = list(spec.outcomes)
    panel = _load_panel()
    cut = resolve_cutoff()
    ar_summary, ar_daily = _ar_reference()
    seed = int(config.settings()["reproducibility"]["random_seed"])
    torch_deterministic = configure_deterministic_execution(seed)

    print(f"counterfactual cross-check: model={args.model}, cutoff={cut.date()}")
    print(
        f"determinism: seed={seed}, "
        f"torch_configured={torch_deterministic}"
    )
    print(f"train: < {cut.date()} (univariate, pre-treatment only)  "
          f"forecast: >= {cut.date()}\n")

    try:
        adapter = MODEL_REGISTRY[args.model](
            **({"device_map": args.device_map} if args.model == "chronos2" else {})
        )
    except ImportError as exc:
        raise SystemExit(f"{args.model}: {exc}")

    dailies, summaries = [], []
    for target in targets:
        daily, summary = counterfactual_shortfall(
            panel, target=target, adapter=adapter, cutoff=cut,
            lower_q=args.lower_q, upper_q=args.upper_q,
        )
        dailies.append(daily)
        summaries.append(
            _attach_matched_ar_reference(
                target=target,
                tsfm_daily=daily,
                tsfm_summary=summary,
                ar_summary=ar_summary,
                ar_daily=ar_daily,
            )
        )

    summary = pd.DataFrame(summaries)

    out_dir = config.path("data_processed")
    daily_out = out_dir / "tsfm_counterfactual_daily.csv"
    summary_out = out_dir / "tsfm_counterfactual_summary.csv"
    pd.concat(dailies, ignore_index=True).to_csv(daily_out, index=False)
    summary.to_csv(summary_out, index=False)

    print("Counterfactual shortfall (counterfactual - observed):")
    show = ["model", "target", "n_days", "observed_sum", "counterfactual_sum",
            "cumulative_throughput_loss", "ar_cumulative_throughput_loss",
            "pct_diff_vs_ar", "matched_ar_dates", "matched_ar_observed"]
    print(summary[[c for c in show if c in summary.columns]].to_string(index=False))

    print("\nInterpretation guard (CLAUDE.md rules 1, 2):")
    print(" - Robustness cross-check only: a similar shortfall under a stronger,")
    print("   better-calibrated forecaster shows the headline is not an AR artifact.")
    print(" - NOT causal inference; AR-only remains the locked primary estimator.")
    print(" - lower_cf/upper_cf are POINTWISE daily bands; do NOT sum them into a")
    print("   cumulative interval — use run_long_horizon_intervals.py for that.")
    if args.model == "stub":
        print(" - WARNING: 'stub' is a plumbing check, not a model result.")
    print(f"\nwrote {daily_out}")
    print(f"wrote {summary_out}")


if __name__ == "__main__":
    main()
