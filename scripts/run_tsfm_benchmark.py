"""Unified, isolated benchmark runner for modern time-series foundation models.

Scores Chronos-2, TimesFM 2.5 and/or Moirai 2.0 on the SAME leakage-safe,
strictly pre-treatment rolling-origin folds as the transparent baselines, then
applies the configured admission test against the AR-only baseline. This script
is deliberately excluded from ``scripts/run_all.py`` and from the frozen core
requirements: the PyTorch stack and model weights are optional external
artifacts installed in separate environments.

Run in the isolated benchmark env (requirements/benchmark.txt, Python <= 3.12):

    python scripts/run_tsfm_benchmark.py --model all --acknowledge-benchmark-only
    python scripts/run_tsfm_benchmark.py --model chronos2 --acknowledge-benchmark-only

The dependency-free plumbing check (no weights, runs anywhere) is:

    python scripts/run_tsfm_benchmark.py --model stub --acknowledge-benchmark-only

Stub output is a harness plumbing check, NOT a foundation-model result.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from hormuz_throughput import config  # noqa: E402
from hormuz_throughput.specification import working_specification  # noqa: E402
from hormuz_throughput.tsfm import (  # noqa: E402
    DEFAULT_LOWER_Q,
    DEFAULT_UPPER_Q,
    FOUNDATION_MODELS,
    MODEL_REGISTRY,
    admission_test,
    aggregate_benchmark,
    configure_deterministic_execution,
    run_benchmark,
)
from hormuz_throughput.validation import resolve_cutoff, rolling_origin_splits, summary  # noqa: E402


def _load_panel() -> pd.DataFrame:
    path = config.path("data_processed") / "panel_aligned.csv"
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found. Run scripts/build_panel.py and "
            "scripts/align_panel.py first."
        )
    return pd.read_csv(path, parse_dates=["date"]).set_index("date")


def _merge_on_write(new: pd.DataFrame, path: Path, models_ran: list[str]) -> pd.DataFrame:
    """Combine freshly computed rows with any already on disk.

    Lets the Chronos-2/Moirai (.venv-bench) and TimesFM (.venv-timesfm) runs
    accumulate into one file: prior rows for the models that just ran are dropped
    (a re-run replaces itself), other models' rows are kept, then new rows append.
    """
    if path.exists():
        try:
            prior = pd.read_csv(path)
            prior = prior[~prior["model"].isin(models_ran)]
            return pd.concat([prior, new], ignore_index=True)
        except (KeyError, pd.errors.EmptyDataError):
            return new
    return new


def _drop_wall_clock_columns(frame: pd.DataFrame) -> pd.DataFrame:
    """Keep frozen benchmark artifacts free of nondeterministic timings."""
    runtime_columns = [
        column for column in frame.columns if column.startswith("runtime_s")
    ]
    return frame.drop(columns=runtime_columns, errors="ignore")


def _load_ar_aggregate() -> pd.DataFrame | None:
    """AR-only baseline aggregate for the admission test, if available."""
    path = config.path("data_processed") / "baseline_summary.csv"
    if not path.exists():
        return None
    return pd.read_csv(path)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--model",
        default="all",
        help="comma-separated subset of {chronos2,timesfm,moirai,stub} or 'all'. "
             "TimesFM 2.5 needs its own env (.venv-timesfm); run it separately — "
             "results accumulate into the same CSVs by merge-on-write.",
    )
    parser.add_argument("--acknowledge-benchmark-only", action="store_true")
    parser.add_argument("--device-map", default="cpu")
    parser.add_argument("--lower-q", type=float, default=DEFAULT_LOWER_Q)
    parser.add_argument("--upper-q", type=float, default=DEFAULT_UPPER_Q)
    parser.add_argument(
        "--ar-model",
        default="ar_lag1_7",
        help="AR-only baseline model name to compare against in the admission test.",
    )
    args = parser.parse_args()

    if not args.acknowledge_benchmark_only:
        raise SystemExit(
            "Refusing to run without --acknowledge-benchmark-only. These models "
            "are isolated benchmarks, not the thesis foundation or an enabled "
            "estimator. Nothing here is promoted into the counterfactual pipeline."
        )

    if args.model == "all":
        requested = list(FOUNDATION_MODELS)
    else:
        requested = [m.strip() for m in args.model.split(",") if m.strip()]
    unknown = [m for m in requested if m not in MODEL_REGISTRY]
    if unknown:
        raise SystemExit(
            f"Unknown model(s) {unknown}; choose from {sorted(MODEL_REGISTRY)} or 'all'."
        )

    spec = working_specification()
    targets = list(spec.outcomes)
    panel = _load_panel()
    folds = rolling_origin_splits(panel.index)
    seed = int(config.settings()["reproducibility"]["random_seed"])
    torch_deterministic = configure_deterministic_execution(seed)

    print(f"panel shape: {panel.shape}  "
          f"({panel.index.min().date()} -> {panel.index.max().date()})")
    print(
        f"determinism: seed={seed}, "
        f"torch_configured={torch_deterministic}"
    )
    print(f"treatment cutoff: {resolve_cutoff().date()} (all folds strictly before)")
    print(f"rolling-origin folds: {len(folds)}")
    print(summary(folds).tail(3).to_string(index=False))
    print(f"targets: {targets}")
    print(f"requested models: {requested}")
    print(f"central interval: [{args.lower_q}, {args.upper_q}] "
          f"(adapters that cannot emit this report their native level honestly)\n")

    all_scores = []
    all_forecasts = []
    skipped = []
    ran = []
    for model_name in requested:
        print(f"--- instantiating {model_name} (loads weights; may be slow) ---")
        try:
            adapter = MODEL_REGISTRY[model_name](
                **({"device_map": args.device_map} if model_name == "chronos2" else {})
            )
        except ImportError as exc:
            print(f"  SKIP {model_name}: {exc}")
            skipped.append(model_name)
            continue
        for target in targets:
            scores, forecasts = run_benchmark(
                panel,
                target=target,
                adapter=adapter,
                folds=folds,
                lower_q=args.lower_q,
                upper_q=args.upper_q,
                season_length=7,
            )
            all_scores.append(scores)
            all_forecasts.append(forecasts)
            mean = scores[["mase", "rmse", "empirical_coverage", "interval_width"]].mean()
            print(f"  {model_name} / {target}: "
                  f"MASE={mean['mase']:.3f}  RMSE={mean['rmse']:.3f}  "
                  f"cov={mean['empirical_coverage']:.3f}  width={mean['interval_width']:.3f}")
        ran.append(adapter.name)

    if not all_scores:
        raise SystemExit(
            "No models ran in this environment. Installed model(s) skipped: "
            f"{skipped or requested}. Run chronos2/moirai in .venv-bench and "
            "timesfm in .venv-timesfm."
        )

    out_dir = config.path("data_processed")
    scores_out = out_dir / "tsfm_benchmark_scores.csv"
    forecasts_out = out_dir / "tsfm_benchmark_forecasts.csv"
    aggregate_out = out_dir / "tsfm_benchmark_summary.csv"

    scores = _drop_wall_clock_columns(
        _merge_on_write(pd.concat(all_scores, ignore_index=True), scores_out, ran)
    )
    forecasts = _drop_wall_clock_columns(
        _merge_on_write(
            pd.concat(all_forecasts, ignore_index=True), forecasts_out, ran
        )
    )
    aggregate = aggregate_benchmark(scores)
    scores.to_csv(scores_out, index=False)
    forecasts.to_csv(forecasts_out, index=False)
    aggregate.to_csv(aggregate_out, index=False)

    print("\nAggregate scores:")
    cols = [
        "model", "target", "mase_mean", "rmse_mean",
        "empirical_coverage_mean", "nominal_coverage_mean",
        "coverage_error_mean", "interval_width_mean",
    ]
    print(aggregate[[c for c in cols if c in aggregate.columns]].to_string(index=False))

    ar_agg = _load_ar_aggregate()
    if ar_agg is not None:
        try:
            verdict = admission_test(aggregate, ar_agg, ar_model=args.ar_model)
            verdict_out = out_dir / "tsfm_admission_test.csv"
            verdict.to_csv(verdict_out, index=False)
            print("\nAdmission test (vs AR-only baseline):")
            print(verdict[["model", "target", "mase_improvement",
                           "beats_ar_mase", "keeps_calibration", "admitted"]]
                  .to_string(index=False))
            for _, row in verdict.iterrows():
                print(f"  - {row['model']}/{row['target']}: {row['verdict']}")
            print(f"\nwrote {verdict_out}")
        except ValueError as exc:
            print(f"\nAdmission test skipped: {exc}")
    else:
        print("\nAdmission test skipped: run scripts/run_baseline.py first to "
              "produce baseline_summary.csv for the AR-only comparison.")

    print(f"\nwrote {scores_out}")
    print(f"wrote {forecasts_out}")
    print(f"wrote {aggregate_out}")

    print("\nInterpretation constraints:")
    print(" - These are pre-treatment validation scores, NOT causal effects.")
    print(" - A model is promoted into the post-treatment comparison only if the")
    print("   admission test marks it ADMITTED; otherwise AR-only remains primary.")
    print(" - The calibration leg needs the AR-only raw interval: run")
    print("   scripts/run_ar_interval.py for the final matched-subset verdict.")
    print(" - ADMITTED means eligible to ENTER the comparison as a cross-check; it")
    print("   is never itself evidence of a causal effect and never replaces AR-only.")
    if "stub" in requested:
        print(" - WARNING: 'stub' is a harness plumbing check, not a model result.")


if __name__ == "__main__":
    main()
