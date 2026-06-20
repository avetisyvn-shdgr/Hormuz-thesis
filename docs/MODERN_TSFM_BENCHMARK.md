# Modern Time-Series Foundation Model Benchmark Gate

Status: optional engineering extension, clean-rebuilt and checked 2026-06-20.
This does not alter the
formal proposal, estimand, hypotheses, locked AR-only primary, or Transformer
prohibition. A foundation model remains an isolated benchmark until it improves
both pre-treatment fit and interval calibration.

## Ranked candidates

1. **Chronos-2 (Amazon, released 2025-10-20; 120M parameters).** First choice.
   The official package supports zero-shot univariate, multivariate, and
   covariate-informed probabilistic forecasts. Use univariate input here: future
   route or energy values observed after treatment can absorb the disruption and
   invalidate the counterfactual. Official source:
   <https://github.com/amazon-science/chronos-forecasting>
2. **TimesFM 2.5 (Google, released 2025-09-15; 200M parameters).** Second choice.
   It supports 16k context and continuous quantile forecasts to a 1k horizon.
   Its long context is unnecessary for the four-year PortWatch history, but its
   quantile head makes interval calibration directly testable. Official source:
   <https://github.com/google-research/timesfm>
3. **Moirai 2.0 R-small (Salesforce, released 2025-08).** Probabilistic
   zero-shot cross-check with flexible context/horizon through Uni2TS. It is a
   useful third model, not the first integration because its GluonTS stack is
   heavier than the Chronos DataFrame interface. Official source:
   <https://github.com/SalesforceAIResearch/uni2ts>
4. **Tiny Time Mixers R2 / Granite TSFM (IBM, 2025 generation).** Useful when
   CPU cost and few-shot tuning matter. Lower priority for this thesis because
   the main need is an independent probabilistic counterfactual, not deployment
   efficiency. Official source: <https://github.com/ibm-granite/granite-tsfm>

Kairos, TiRex, Sundial, and Time-MoE are research-watch candidates. Adding many
models would inflate multiple-comparison risk without improving identification.

## Admission test

Every candidate must use the existing expanding, chronological, strictly
pre-treatment folds. Report mean/median MASE, RMSE, empirical interval coverage,
interval width, and runtime. It enters the post-treatment comparison only if it
materially improves AR-only MASE **and** does not worsen interval calibration,
without using post-treatment observed covariates. The fixed treatment date and
folds may not be tuned after seeing the disruption window.

`src/lngfreight/tsfm.admission_test()` encodes this gate against the AR-only
baseline (`baseline_summary.csv`): a candidate is `ADMITTED` for a target only if
its mean MASE is at or below AR-only's **and** its absolute mean coverage error
is no larger than AR-only's. Calibration is compared on `|coverage_error|`
(empirical minus nominal coverage), which stays meaningful even when models
report different native nominal levels — see the interval-level note below.

### Interval levels are not mislabeled

The harness requests a 95% central interval (`[0.025, 0.975]`) by default. Each
adapter reports the quantile levels it **actually** produced via
`QuantileForecast.level_lower/level_upper` and `nominal_coverage`:

- **Chronos-2** emits arbitrary quantiles, so the requested 95% interval is native.
- **TimesFM 2.5** and **Moirai 2.0** *both* emit only a fixed decile grid
  (0.1…0.9) — verified at runtime against the installed packages. Their widest
  native central interval is **80%** (0.1/0.9), not 95%. (TimesFM additionally
  returns a leading mean column, handled by the adapter.) Each adapter snaps to
  the nearest deciles and records `nominal_coverage = 0.80` rather than
  extrapolating a fake 95% interval. Cross-model comparison therefore uses the
  calibration error (empirical − nominal), not raw coverage.

## Implementation

The benchmark logic is a single shared, leakage-safe harness
(`src/lngfreight/tsfm.py`): one `QuantileForecast` contract, one `run_benchmark`
scorer reusing the baseline folds and metrics, plus one adapter per model
(`Chronos2Adapter`, `TimesFM25Adapter`, `Moirai2Adapter`) and a dependency-free
`StubAdapter` used only to test the plumbing. All three models thus share one
fold geometry and one scorer.

### Two benchmark environments (torch conflict)

The model stacks cannot share one env: **Moirai 2.0 / uni2ts pins torch 2.4.x**,
but **TimesFM 2.5 needs a newer torch (2.12.x)** and silently emits all-NaN
forecasts under the old pin (the harness guards against this). Both stacks also
need Python 3.11 (the repo core venv is 3.14; uni2ts is < 3.12). So:

| Env | Python | Models | Requirements |
|---|---|---|---|
| `.venv-bench` | 3.11 | Chronos-2 + Moirai 2.0 | `requirements-benchmark.lock.txt` |
| `.venv-timesfm` | 3.11 | TimesFM 2.5 | `requirements-timesfm.lock.txt` |

```bash
# Env 1 — Chronos-2 + Moirai 2.0:
/opt/homebrew/bin/python3.11 -m venv .venv-bench
.venv-bench/bin/python -m pip install -r requirements-benchmark.lock.txt
.venv-bench/bin/python scripts/run_tsfm_benchmark.py \
    --model chronos2,moirai --acknowledge-benchmark-only

# Env 2 — TimesFM 2.5 (results MERGE into the same CSVs via merge-on-write):
/opt/homebrew/bin/python3.11 -m venv .venv-timesfm
.venv-timesfm/bin/python -m pip install -r requirements-timesfm.lock.txt
.venv-timesfm/bin/python scripts/run_tsfm_benchmark.py \
    --model timesfm --acknowledge-benchmark-only

# Dependency-free plumbing check (runs in the core 3.14 venv; NOT a model result):
python scripts/run_tsfm_benchmark.py --model stub --acknowledge-benchmark-only
```

`--model all` is safe in either env: models not installed there are skipped with
a notice, and the runner keeps prior results on disk. `--model` also accepts a
comma-separated subset. `scripts/run_chronos2_benchmark.py` is retained as a thin
backward-compatible alias for `--model chronos2`.

Outputs (written to `data/processed/`): `tsfm_benchmark_scores.csv` (per fold),
`tsfm_benchmark_forecasts.csv` (per test day), `tsfm_benchmark_summary.csv`
(aggregate), and `tsfm_admission_test.csv` (the per-target verdict).

The `.lock.txt` files contain the complete exact-version environment used for the
citable rerun. The shorter unpinned requirements files remain development
constraints only and must not be used to claim reproduction of the reported
numbers.

## Status and clean rebuild confirmation (2026-06-20)

- **Harness, runner, contract tests, admission test: implemented and passing**
  (`tests/test_tsfm.py`, 9 tests in the core env).
- **All three adapters re-run end-to-end on real weights in newly created
  environments** built from the exact lockfiles above (macOS arm64, Python
  3.11.15), over all 38 strictly pre-treatment folds × both outcomes.
- Both environments pass `pip check`. Pandas import and distribution metadata
  agree: 2.1.4 in Chronos/Moirai and 2.3.3 in TimesFM.
- Compared with the pre-rebuild snapshot, admission decisions and Chronos
  counterfactual outputs are byte-equivalent after excluding runtime fields.
  Benchmark prediction differences are only floating-point noise (maximum
  `1.4e-14`; maximum score-field difference `4.7e-10`) and do not change any
  reported value.
- `data/processed/tsfm_run_manifest.json` records lockfile hashes, package
  versions, pandas consistency, `pip check`, model revisions, device, and output
  hashes.

Clean-rerun mean scores (pre-treatment validation, 30-day horizon, NOT causal
effects). AR-only baseline shown for reference (`baseline_summary.csv`):

| Model | Native | Transits MASE | Capacity MASE | Transits cov. | Capacity cov. |
|---|---|---|---|---|---|
| AR-only `ar_lag1_7` | — | ~0.916 | ~0.736 | n/a | n/a |
| Chronos-2 | 95% | 0.775 | 0.686 | 0.937 | 0.957 |
| TimesFM 2.5 | 80% | 0.766 | 0.687 | 0.761 | 0.821 |
| Moirai 2.0 | 80% | 0.807 | 0.698 | 0.769 | 0.830 |

Reading: all three beat AR-only on point MASE, and Chronos-2 is well-calibrated
at a true 95%. This does **not** by itself admit any model — see the open
calibration leg below — and a better forecaster is **not** evidence of a causal
effect (CLAUDE.md rule 2). AR-only remains the locked primary estimator.

### Calibration leg — resolved (raw AR interval)

The calibration leg is now assessed. `src/lngfreight/ar_intervals.py` gives the
AR-only baseline a **raw, horizon-aware** predictive interval (per-step residual
spread, `z(q)·σ_s`, estimated from strictly-earlier folds only — leakage-safe,
and *not* the conformal machinery in `inference.py`). `scripts/run_ar_interval.py`
then re-runs the admission test on the **matched fold subset** where the AR
interval is defined (the 23 later folds with ≥15 prior calibration folds), so
MASE and calibration are compared on identical folds. It runs in the core env
(no model weights). Outputs: `ar_interval_{scores,bands,summary}.csv` and the
final `tsfm_admission_test.csv`.

**Clean-rerun verdict (matched subset, 2026-06-20):** all three models
beat AR-only on MASE **and** on calibration, so all six model×target cells are
`ADMITTED`. The AR raw band under-covers (empirical ≈0.87–0.90 transits/capacity
vs 0.95 nominal) because recursive AR multi-step errors are fat-tailed; the
foundation models' native probabilistic heads are better calibrated. This is
**robust to the interval sub-method**: an empirical-quantile per-step band covers
even less (≈0.84–0.86), i.e. the Gaussian-per-step choice is the *more*
AR-favorable of the two raw options, so the verdict is not an artifact of it.

Caveats to carry into the thesis (CLAUDE.md rules 1, 2):
- `ADMITTED` means only **eligible to enter** the post-treatment comparison as a
  cross-check. It is **not** evidence of a causal effect and does **not** replace
  AR-only as the locked primary estimator (the ton-mile identification rests on
  the dose-response and donor estimators, not on which forecaster fits best).
- The AR interval is a raw per-step-residual band, **not** a guaranteed-coverage
  interval; treat the calibration comparison as indicative, not exact.
- These results are an optional robustness extension. They are not load-bearing
  for the core throughput estimate and may be omitted without changing the
  primary model, inference, or conclusions.

### Counterfactual cross-check (robustness, optional)

Once a model is `ADMITTED`, `scripts/run_tsfm_counterfactual.py` re-estimates the
post-treatment shortfall with that model (default Chronos-2) in place of AR-only
and reports the cumulative shortfall and its % difference vs the AR-only estimate
(`counterfactual_post_treatment_summary.csv`). It trains univariate on strictly
pre-cutoff data — no post-treatment covariate leaks in — and is a robustness
sentence ("the shortfall survives a stronger, better-calibrated forecaster"), not
a promoted estimator and not causal inference. Pointwise daily bands are written
but are deliberately NOT summed into a cumulative interval (that is the residual /
placebo-horizon job of `run_long_horizon_intervals.py`).

```bash
.venv-bench/bin/python scripts/run_tsfm_counterfactual.py \
    --model chronos2 --acknowledge-benchmark-only
# plumbing check in the core env (NOT a model result):
python scripts/run_tsfm_counterfactual.py --model stub --acknowledge-benchmark-only
```

This benchmark is deliberately excluded from `scripts/run_all.py` and the frozen
core requirements because model weights and the PyTorch stack are optional
external artifacts.
