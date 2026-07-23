# AGENTS.md — Operating rules for AI assistance on this thesis

This is a Bachelor thesis at TUM (Transportation Analytics): a **causal-inference**
study of the 2026 Strait of Hormuz disruption and LNG freight markets (the
"ton-mile multiplier" mechanism). Methodological discipline outranks speed.
Read these rules at the start of every session and follow them.

## Current implementation status

- Prof. Li authorized proceeding with the free PortWatch dataset as the working
  primary. The locked engineering specification is in `config/settings.yaml`.
- On 2026-07-23, Zhenyu Wang explicitly confirmed that the revised title,
  research question, estimand, claim strength, and completed empirical scope are
  acceptable. This is recorded as written advisor-side acceptance, but it is not
  attributed to Prof. Li because no direct Prof. Li confirmation is on record.
  Do not edit the formal proposal until that governance distinction is resolved.
  Proposed language remains staged in
  `docs/PENDING_ESTIMAND_REALIGNMENT_DRAFT.md`.
- Spark remains dormant and optional. Follow `docs/SPARK_REENTRY.md`; never make
  it a blocker or silently replace a working-primary result.
- The active next-phase roadmap is `docs/CURRENT_PLAN.md`. Preserve the existing
  PortWatch work and keep Spark open through thesis completion while testing the
  vessel-data branch and its documented simulation fallback.
- Transformers are disabled unless the configured re-entry condition is met.

## Non-negotiable rules

1. **Never fabricate.** Do not invent datasets, access rights, model results,
   numbers, dates, or citations. If something has not been run in code, say so
   and label it a hypothesis. If a fact is not from a primary source, flag it.
2. **Prediction ≠ identification.** A forecaster's accuracy is never evidence of
   a causal effect. The working fallback reports counterfactual shortfalls and
   triangulates them with placebos and donor methods; it does not label them ATT.
3. **One phase at a time.** Build incrementally (see README roadmap). Do not
   generate the whole pipeline or large monolithic notebooks at once.
4. **Verify before claiming.** Run available local tests and scripts; distinguish
   verified outputs from hypotheses and from credential-gated checks.
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

The working throughput specification locks `2026-02-28` as the operational-onset
cutoff. Training must remain strictly before it. Later dates are event milestones
and sensitivity scoring windows, not alternative training cutoffs. The chronology
was re-audited on 2026-06-19; see `docs/EVENT_CHRONOLOGY.md` before changing any
date or label.
