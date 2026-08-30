# AGENTS.md — Canonical operating rules for the technical thesis repository

This repository implements the technical evidence for a TUM Bachelor thesis on
the 2026 Strait of Hormuz disruption. The implemented study is an explicitly
non-causal, public-data analysis of the disruption-associated shortfall in
observable daily tanker throughput, supplemented by descriptive LNG and
shipping-network adaptation evidence. Methodological discipline outranks speed.

This is the canonical AI-assistance instruction file for `Technical/`.
`CLAUDE.md` is only a compatibility pointer and must not contain a second set of
rules.

## Source-of-truth order

When two files disagree, use this order and report the conflict rather than
silently choosing a convenient interpretation:

1. The researcher's explicit instruction for the current task.
2. `LITERATURE_REVIEW_THEMATIC_BLUEPRINT.md` in the separate clean literature
   workspace for the thesis plot, research questions, contribution, and claim
   boundaries. Its folder may be renamed during cleanup; if the file is not
   available, use the current research design below and report the missing
   source instead of substituting an older technical document.
3. `config/settings.yaml`, `config/sources.yaml`, and the applicable frozen
   manifests for locked computational specifications and data provenance.
4. `docs/DECISION_LOG.md` for adopted engineering decisions, known failures, and
   approval-gated reproducibility boundaries.
5. `README.md` and current method-specific documentation for commands and
   repository navigation.

`docs/CURRENT_PLAN.md` and documents describing causal ATT, dose-response,
mediation, g-formula, PCMCI, freight rates as the dependent variable, or an
aggregate ton-mile multiplier are historical design records. They are not the
active thesis roadmap unless the researcher explicitly re-adopts them.

## Current research design

- **Primary outcome:** daily IMF PortWatch tanker transit count at Hormuz. It is
  an AIS-derived aggregate observation, not LNG cargo, laden state, a freight
  rate, welfare, or a complete physical census.
- **Primary estimand:** the cumulative disruption-associated counterfactual
  shortfall over the locked post-onset window.
- **Primary estimator:** transparent target-only AR forecasting trained strictly
  on pre-onset information.
- **Corroborating layers:** chronological and horizon-matched validation,
  uncertainty calibration, temporal and spatial placebos, and
  contamination-aware donor checks.
- **Interpretive layer:** LNG-specific activity, routed-voyage nominal
  capacity-distance, alternative-corridor activity, and importer-origin
  portfolios. These are descriptive evidence of contraction, substitution, or
  network reallocation.
- **Model hierarchy:** Chronos, TimesFM, Moirai, and other foundation models are
  benchmark or robustness evidence only. Better forecasting cannot strengthen
  identification by itself.

## Non-negotiable rules

1. **Never fabricate.** Do not invent datasets, access rights, model results,
   numbers, dates, citations, or execution success. Label untested ideas as
   hypotheses. Verify claims against primary or authoritative sources whenever
   the claim requires it.
2. **Prediction is not identification.** Forecast accuracy, synthetic control,
   donor comparisons, and placebos do not turn the estimated shortfall into a
   causal ATT. Use `disruption-associated counterfactual shortfall`; do not use
   `causal effect`, `treatment effect`, or equivalent language without a newly
   approved identification design.
3. **Work one bounded phase at a time.** Make the smallest useful, testable
   change. Do not generate a new monolithic pipeline or redesign the thesis in
   one step.
4. **Verify before claiming.** Run available local tests and scripts when the
   environment permits, record the exact result, and distinguish verified
   outputs from hypotheses and credential-gated checks. Never claim that code
   works merely because it was written.
5. **Use chronological evaluation.** Never random-split time-series data. Train
   models on pre-onset observations only and use rolling-origin or otherwise
   justified chronological validation.
6. **Treat observation systems as measurements, not truth.** For AIS, satellite,
   news, or customs data, carry forward reporting and coverage bias,
   treatment-correlated missingness, classification error, temporal leakage,
   class imbalance, and overfitting where relevant.
7. **Use the registry and preserve provenance.** External analysis inputs must go
   through `registry.get_variable()` or an explicitly governed equivalent, with
   `config/sources.yaml` updated first. Do not add ad-hoc network pulls to
   analysis scripts or silently substitute a proxy.
8. **Keep the public/proprietary boundary explicit.** The default thesis design
   uses admitted public data. Bloomberg, Fearnleys, ClearLynx, Spark, Platts,
   Kpler, and similar inputs are excluded from the default evidence set unless
   rights and provenance are separately cleared. Bloomberg is excluded, not a
   pending layer. Never place credentials or restricted source bytes in a public
   release.

## Governance and reproducibility guards

- Do not regenerate, refresh, or re-pin a frozen manifest merely to make a test
  pass. If the applicable decision log marks a pin or manifest as requiring
  explicit approval, stop and request that approval.
- Never weaken a validation gate without documenting the measured failure mode,
  the proposed tolerance or rule, and the resulting claim boundary.
- Preserve source-native units. China, Japan, Korea, and Taiwan importer data are
  mass-based; India is value-based; EU27 is a volume-basis aggregate comparator.
  Do not pool these as if they were a homogeneous panel.
- Do not interpret routed nominal capacity-distance as observed cargo, observed
  sailed distance, ton-miles, or one-to-one cargo replacement.
- The primary cutoff is `2026-02-28`. Training is strictly before that date and
  scoring begins on that date. Describe it as externally anchored and inspected
  during audit, not as ex ante preregistered. Later event milestones can change
  scored windows but cannot admit affected observations to training.
- Before deleting or relocating technical files, check Git tracking, imports,
  configuration references, tests, manifests, and documentation dependencies.
  Archive governance or provenance records even when their substantive design
  is historical.

## Repository map

- `config/` — locked settings, source registry, experiment specifications, and
  approval gates.
- `src/lngfreight/` — reusable acquisition, cleaning, modelling, inference, and
  audit code.
- `scripts/` — bounded acquisition, build, run, freeze, audit, and rendering
  entry points.
- `experiments/` — admitted robustness and descriptive adaptation experiments;
  not independent thesis plots.
- `tests/` — offline unit, governance, and integration checks.
- `data/raw/` — immutable local source snapshots with provenance; redistribution
  rights must be assessed separately.
- `data/processed/` — governed model inputs, outputs, diagnostics, and manifests.
- `reports/` — technical summaries, transcripts, and generated figures.
- `docs/` — current documentation plus historical design and decision records.
- `references/` — technical bibliographic seed data.
- The clean manuscript and current literature review are maintained outside this
  repository. Do not assume their folder name during cleanup, and do not write
  generated technical output into them unless the researcher explicitly requests
  a controlled transfer.

## When adding or changing modelling code

State, in order: (a) methodological justification, (b) data requirement,
(c) expected limitation, and (d) next practical action. Then implement only the
current bounded phase. Keep research logic separate from computational mechanics,
preserve the primary-versus-robustness hierarchy, and report the tests actually
run.
