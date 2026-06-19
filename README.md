# LNG Freight Thesis — Working Model Repository

The authorized working implementation uses free IMF PortWatch data to estimate
the **disruption-associated counterfactual shortfall** in Strait of Hormuz tanker
throughput. Daily tanker transit count is the primary outcome, deadweight
capacity is the robustness outcome, and AR-only is the primary counterfactual
estimator. Formal proposal/RQ/hypothesis realignment remains pending Prof. Li's
explicit approval; staged language is isolated in
`docs/PENDING_ESTIMAND_REALIGNMENT_DRAFT.md`.

> This is still a conservative modeling foundation, not the final thesis model.
> The first transparent benchmark now exists: leakage-safe rolling-origin
> seasonal-naive, AR, and conditional ARX forecasts for the free
> chokepoint-throughput outcomes.

## Why it is built this way

Your dependent variable (Spark25S/30S) and key mechanism data (AIS, Lloyd's,
Kpler) are proprietary. Rather than scrape imitations, the repo separates the
**logical thesis variable** from the **provider that supplies it**:

```
analysis code  ──►  registry.get_variable("henry_hub_spot")
                          │  (reads config/sources.yaml)
                          ▼
                    provider (EIA / FRED / PortWatch / …later Spark)
                          │
                          ▼
                 tidy (date, value) frame  +  provenance log
```

Spark is a dormant optional secondary-outcome extension, not a dependency. Its
reactivation procedure is documented in `docs/SPARK_REENTRY.md` and requires no
core model-code redesign.

## Quick start

```bash
python3.11 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # add free EIA + FRED keys
python scripts/fetch_baseline.py   # pulls the free energy confounders
pytest -q                     # 4 no-network contract tests
```
Full setup (PyCharm + Claude Code, macOS): `docs/SETUP_CLAUDE_PYCHARM.md`.

## Layout

| Path | Purpose |
|---|---|
| `config/sources.yaml` | Series registry — the swap-in layer (edit this, not code) |
| `config/settings.yaml` | Locked working specification, paths, dates, validation, seed |
| `src/lngfreight/specification.py` | Validates outcome and estimator roles |
| `src/lngfreight/registry.py` | `get_variable()` — the single data entry point |
| `src/lngfreight/sources/` | One module per provider, all sharing `base.BaseSource` |
| `src/lngfreight/provenance.py` | Immutable raw pulls + SHA-256 audit log |
| `src/lngfreight/metrics.py` | Dependency-free forecast metrics (MAE, RMSE, MASE, sMAPE) |
| `src/lngfreight/baselines.py` | Transparent seasonal-naive + ARX baselines over rolling-origin folds |
| `src/lngfreight/tsfm.py` | Isolated TSFM benchmark harness (Chronos-2 / TimesFM 2.5 / Moirai 2.0 adapters, shared scorer, admission test) |
| `src/lngfreight/ar_intervals.py` | Raw horizon-aware AR-only interval (calibration leg of the TSFM admission test) |
| `src/lngfreight/inference.py` | Counterfactual-gap summaries + placebo-in-time inference helpers |
| `scripts/fetch_baseline.py` | Phase-1 smoke test on free data |
| `scripts/run_baseline.py` | Phase-4 first benchmarks: free-data forecast scores |
| `scripts/run_tsfm_benchmark.py` | Unified foundation-model benchmark runner (`--model all\|chronos2\|timesfm\|moirai\|stub`); isolated, excluded from `run_all.py` |
| `requirements-benchmark.txt` | Isolated deps for Chronos-2 + Moirai 2.0 (`.venv-bench`, Python 3.11); kept out of frozen core |
| `requirements-timesfm.txt` | Isolated deps for TimesFM 2.5 (`.venv-timesfm`, Python 3.11; separate due to torch conflict) |
| `scripts/run_ar_interval.py` | Raw AR-only interval + final matched-subset TSFM admission verdict (core env, no weights) |
| `scripts/run_tsfm_counterfactual.py` | Counterfactual shortfall cross-check with an admitted model vs AR-only (robustness; needs weights) |
| `scripts/run_counterfactual.py` | Post-treatment observed-minus-counterfactual gap export |
| `scripts/run_placebo_inference.py` | Placebo-in-time p-values for counterfactual gaps |
| `scripts/run_spatial_placebo.py` | Same-date PortWatch chokepoint placebo checks |
| `scripts/run_interval_calibration.py` | Residual-calibrated pointwise and aggregate loss intervals |
| `scripts/make_results_summary.py` | Generated Markdown summary of current empirical results |
| `reports/current_results_summary.md` | Thesis-ready working table from processed outputs |
| `docs/INFERENCE_NOTES.md` | Reporting caveats for placebo-in-time evidence |
| `docs/` | Data-source registry, setup guide, go/no-go checklist |
| `CLAUDE.md` | Anti-hallucination rules for AI assistance |

## Phase roadmap (do NOT skip ahead)

1. **Data foundation** — skeleton + free sources + provenance.
2. **Go/no-go gate** — fallback branch selected; Spark/Bloomberg now upside.
3. **Cleaned daily panel + descriptive event study** — Layer 1 figures.
4. **Transparent baselines** ← *you are here.* Seasonal-naive + ARX, post-gap export, placebo-in-time inference.
5. **Corroboration and inference** — synthetic control, spatial/temporal placebos, long-horizon intervals.
6. **Optional model extension only after a gate** — no Transformer unless it materially improves pre-treatment fit and interval coverage, or Prof. Li requires it.

## Status of treatment dates

The treatment-date candidates in `settings.yaml` were verified on 2026-06-14
and documented in `docs/EVENT_CHRONOLOGY.md`. The earliest candidate
(`2026-02-28`) is used as the conservative modeling cutoff.
