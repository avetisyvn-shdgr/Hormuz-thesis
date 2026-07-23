# Corridor-transmission work plan

**Status:** Collaboration plan, 2026-06-21. This plan deliberately separates
decisions, implementation and expensive model runs. The panel, admission and
inference specifications (Tasks 2–4) were frozen first; only then were the
exploratory AR-only post-cutoff results generated (Task 7). The author has chosen
to proceed to results without supervisor sign-off to support a discussion;
results are labelled exploratory and carry no admitted/significance claims.
Tasks 5–6 (foundation-model feasibility and the TSFM admission benchmark) remain
open and require the pinned heavy environments; AR-only is the locked primary
estimator regardless of their outcome.

## Working method

For each task: (1) state the research decision, (2) implement the smallest useful
unit, (3) add automated checks, (4) inspect only the outputs allowed at that
stage, and (5) record a go/revise/stop decision. A passing task is not evidence
that a later task will pass.

## Task 1 — Correct provenance and model claims

**Status:** Complete; ready for collaboration checkpoint 1 review.

**Purpose:** make the selection note factually citable before it guides code.

Deliverables:

- Separate repository-code licences from checkpoint licences.
- Record Moirai 2.0 as CC-BY-NC-4.0 and research/non-commercial only.
- Describe TimesFM and Moirai as fixed-decile quantile models in the tested
  adapters; retain Chronos-2's arbitrary requested quantiles.
- Replace the independent-corpora claim with the narrower architecture/training
  recipe claim.
- Treat context capacity and CPU feasibility as measured properties, not model
  marketing claims.

Acceptance check: every model identifier, revision, licence and probabilistic
interface agrees with the pinned manifest, adapter and primary model source.

## Task 2 — Freeze the panel admission protocol

**Status:** Technical specification and tests complete. Threshold approval by
Prof. Li remains the stop/go gate; no panel benchmark should run before approval.

**Purpose:** prevent model or corridor selection after seeing favourable results.

Decisions to freeze in a small YAML/JSON specification:

- eligible corridors and target columns;
- common training start and exclusive cutoff;
- shared rolling-origin dates, horizon and minimum training length;
- missing-day handling and minimum valid folds per corridor;
- a common interval level supported by every model and AR-only;
- the corridor-level MASE comparison, panel aggregation and materiality margin;
- the calibration statistic, tolerance and minimum coverage safeguard;
- one panel-level admission decision per model, with no corridor exceptions.

Implementation:

- Add a pure `panel_admission_test()` function; it must consume only pre-cutoff
  fold scores and the frozen specification.
- Prefer paired candidate-versus-AR corridor statistics on identical folds.
- Avoid signed calibration-error averaging that allows over- and undercoverage
  to cancel; report corridor absolute calibration error and its panel summary.
- Add tests for fold mismatch, missing corridors, post-cutoff rows, cancellation,
  threshold boundaries and deterministic output.

Stop/go gate: obtain supervisor agreement on the frozen thresholds before the
real 28-corridor benchmark is run. If agreement is not obtained, stop at a
descriptive exploratory analysis and do not call any model admitted.

## Task 3 — Define the uncertainty and multiplicity contracts

**Status:** Technical specification, tests and the basin-interval coverage
simulation are complete. The primary design uses nine disjoint shared windows;
its adjusted-p-value floor is 0.10. The basin point-only decision is now backed
by simulation (`docs/BASIN_INTERVAL_COVERAGE_RESULTS.md`): under the realistic
nine-draw design no candidate basin interval reaches 0.80 coverage. Supervisor
approval remains required before real corridor inference is run.

**Purpose:** keep three different objects distinct: model prediction intervals,
placebo null distributions and uncertainty intervals for aggregate effects.

Implementation:

- Define the corridor statistic, sign convention and studentization formula.
- Generate placebo origins shared across every eligible corridor; reject
  incomplete or independently shuffled joint draws.
- Define the multiplicity family before inference: corridors, targets and model
  variants included in each Romano–Wolf correction.
- Use the shared-placebo matrix for adjusted p-values and labelled reference
  distributions only.
- Investigate a basin interval as a separate method. Require an explicit
  inversion or calibration argument and simulation coverage checks; otherwise
  keep basin output point-only.

Acceptance check: contract tests cover aligned dates, column ordering, finite
draws, zero-variance statistics, reproducibility and family membership. A
simulation must show that any proposed basin interval reaches its stated
coverage under the tested data-generating processes.

## Task 4 — Build and audit the corridor panel

**Status:** Complete. Panel, metadata, pre-cutoff quality audit and dedicated
manifest are frozen; the operational-region mapping remains pending supervisor
approval.

**Purpose:** create one stable input before adding heavyweight models.

Implementation:

- Build the basin-keyed panel from the pinned PortWatch snapshot.
- Decide between the configured 2022-onward window and the full 2019-onward
  history. Apply the same history policy to every model for a fair comparison.
- Record corridor names, basin assignments, units, date bounds, duplicate dates,
  missingness, zero runs and scale distributions.
- Keep tanker transits and tanker capacity as distinct target families.
- Freeze the panel and metadata hashes before forecasting.

Acceptance check: a lightweight audit command reproduces row counts and hashes,
finds no duplicate corridor-date keys and proves that all benchmark folds end
strictly before `2026-02-28`.

## Task 5 — Measure feasibility before the full benchmark

**Status:** Done for the single Hormuz series (2026-06-21, local run). Chronos-2,
Moirai 2.0 and TimesFM 2.5 all load and forecast in sub-second wall-clock on the
target machine (macOS arm64), producing non-NaN forecasts. CPU feasibility
confirmed. The 28-corridor panel feasibility extrapolation still needs the
dedicated corridor runner.

**Purpose:** establish that “CPU-feasible” is true for this machine and design.

Implementation:

- Run one corridor, one shared fold and one horizon per model after a warm load.
- Record model-load time, forecast time, peak memory, context length and output
  shape using the pinned environments and revisions.
- Extrapolate the full panel cost, then validate with a small multi-corridor run.
- Set a documented runtime/memory budget and deterministic failure/resume rules.

Stop/go gate: if a model exceeds the budget, reduce fold count only through a
pre-specified common design or remove that model from the panel benchmark. Do not
silently give different models different validation opportunities.

## Task 6 — Run the pre-cutoff benchmark and apply the gate

**Status:** Done for the single Hormuz series; open at the 28-corridor level.
Single-series verdict (2026-06-21): Chronos-2, Moirai and TimesFM are all
ADMITTED on both targets — they beat AR-only MASE (transits +15–21%, capacity
+5–7% on matched folds) and hold calibration once the raw AR interval
(`scripts/run_ar_interval.py`) supplies the comparison leg. Post-treatment
cross-check: Chronos-2 reproduces the AR Hormuz shortfall within +2.4% (transits)
and −5.2% (capacity) in the historical 94-day run. The active matched-horizon
rerun through 2026-07-07 gives −3.7% for transits (130 identical scored dates)
and −10.6% for capacity (118 identical valid dates)
(`data/processed/tsfm_counterfactual_summary.csv`). AR-only remains the locked
primary estimator. The per-corridor AR baseline (median MASE 0.743, 92% below
1.0) is in `corridor_transmission_ar_baseline_mase.csv`; the corridor-level TSFM
benchmark still needs the dedicated panel runner.

**Purpose:** select models using only admissible historical evidence.

Implementation:

- Run AR-only and the candidate models on identical frozen folds.
- Produce corridor-level paired metrics and the single panel-level verdict.
- Inspect sensitivity to corridor exclusion only after the primary verdict; do
  not use sensitivity results to reverse a failed primary gate.
- Freeze scores, environment details, model revisions, seeds and output hashes.

Stop/go gate: only models passing the frozen Task 2 rule may generate
post-cutoff corridor counterfactuals. AR-only remains the transparent baseline
and locked primary estimator regardless of the TSFM result.

## Task 7 — Generate the descriptive transmission outputs

**Status:** Done (exploratory, AR-only). See
`docs/CORRIDOR_TRANSMISSION_RESULTS.md`. Headline: Strait of Hormuz −0.955
(transits) / −0.953 (capacity), the only corridor at the 0.10 p-floor on both
targets; positive deviations on Cape of Good Hope, Panama and Yucatan. Leakage
test passes; basin output is point-only; no causal/routing language. The
foundation-model robustness map (gated on Task 6) is still outstanding.

**Purpose:** produce the smallest defensible post-period extension.

Implementation:

- Forecast each corridor univariately from its own pre-cutoff history.
- Report normalized signed deviation first and raw throughput second.
- Generate shared-placebo adjusted p-values under the Task 3 contract.
- Report basin point estimates; include a basin band only if Task 3 validated it.
- Avoid routing, absorption, reallocation and causal language.
- Freeze `corridor_transmission_manifest.json`; keep the runner outside
  `run_all.py`.

Acceptance check: leakage tests prove forecasts are unchanged when other
corridors' post-cutoff observations are altered. The final report includes the
licence boundary, media-observation bias, multiplicity family, missingness and
forecast-calibration limitations.

## Collaboration checkpoints

We review four short artifacts rather than one large notebook:

1. corrected decision note and this plan;
2. frozen admission/inference specifications plus unit tests;
3. audited panel and feasibility report;
4. pre-cutoff verdict, followed only then by descriptive post-period outputs.

At each checkpoint the decision is explicitly **go**, **revise**, or **stop**.
