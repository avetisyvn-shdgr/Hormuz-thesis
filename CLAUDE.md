# CLAUDE.md — Operating rules for AI assistance on this thesis

This is a Bachelor thesis at TUM (Transportation Analytics): a **causal-inference**
study of the 2026 Strait of Hormuz disruption and LNG freight markets (the
"ton-mile multiplier" mechanism). Methodological discipline outranks speed.
Read these rules at the start of every session and follow them.

## Non-negotiable rules

1. **Never fabricate.** Do not invent datasets, access rights, model results,
   numbers, dates, or citations. If something has not been run in code, say so
   and label it a hypothesis. If a fact is not from a primary source, flag it.
2. **Prediction ≠ identification.** A forecaster's accuracy is never evidence of
   a causal effect. Identification rests on the dose-response and donor-based
   estimators, not on which model fits best.
3. **One phase at a time.** Build incrementally (see README roadmap). Do not
   generate the whole pipeline or large monolithic notebooks at once.
4. **The human runs the code.** Do not claim anything "works" until Mher has run
   it and pasted back real output.
5. **Chronological splits.** This is time-series data. Never random-split.
   All trained models use pre-treatment data only, with rolling-origin validation.
6. **Treat news data as observation, not truth.** Mention reporting bias,
   missingness, temporal leakage, class imbalance and overfitting where relevant.
7. **All external data goes through `registry.get_variable()`** so provenance is
   logged. No ad-hoc `requests.get` in analysis code or notebooks.
8. **Free vs proprietary honesty.** Respect `config/sources.yaml` status flags.
   Never silently substitute a proxy for a proprietary target; a proxy swap is a
   documented methodological decision (see docs/DATA_SOURCES.md).

## Project structure

- `config/sources.yaml` — series registry (the swap-in layer). Edit this, not code,
  when data access changes.
- `config/settings.yaml` — paths, study window, treatment-date candidates, seed.
- `src/lngfreight/` — the package. `registry.get_variable(name)` is the entry point.
- `scripts/` — runnable, one concern each.
- `docs/` — data-source registry, setup, go/no-go checklist.
- `data/raw/` — immutable; provenance.jsonl logs every pull.

## When asked to add modelling code

State first, in order: (a) methodological justification, (b) data requirement,
(c) expected limitations, (d) the next practical action. Then write *only* the
code for the current phase. Keep research logic separate from implementation.

## Treatment dates

The four candidate dates in settings.yaml are PROVISIONAL, pulled from the
proposal text, NOT yet re-sourced. Do not treat them as confirmed. Phase 1 is to
verify each against primary sources (CRS, EIA, Lloyd's List, Spark, Argus, S&P).
