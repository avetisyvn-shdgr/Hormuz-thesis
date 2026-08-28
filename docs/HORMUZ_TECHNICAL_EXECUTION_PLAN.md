# Hormuz revision-robust ML: technical execution plan

**Prepared:** 2026-08-27

**Version:** 1.2 (A4 baseline scope corrected; Track A reassigned)

**Status:** Revised shared implementation contract. Mher must approve and
freeze Phase 0 before implementation.

**Participants:** Mher (release authority), ChatGPT (Track A), Claude (Track B).

Version 1.1 replaces the fixed 2025 detector-calibration window, removes
pseudo-precision from resampled temporal placebos, separates proportional
measurement rescaling from non-proportional revision, makes receiver analysis
a gated extension, and removes the LNG-darkness pilot from the committed thesis
scope. It also records the current branch dependency and the permitted negative
result if the global model loses to a local baseline.

## Amendment record

### Version 1.2 -- 2026-08-27, directed by Mher

Two corrections, both arising from Mher's review of the completed A2 run. The
rest of version 1.1 is unchanged and remains controlling.

1. **A4 baseline scope.** Section 6 A4 mode 4 previously said "all predeclared
   baselines". A local AR(1,7) needs a unit-specific fit, and the leave-Hormuz-out
   contract in Phase 0 forbids fitting anything on Hormuz, so no Hormuz local AR
   can exist. Mode 4 now names the baselines that can actually be scored on
   Hormuz. Local AR remains a development-population comparator, reported on the
   27 development units. `tasks.hormuz_training_prohibited` is unchanged, and the
   alternative of fitting a local AR on pre-surveillance Hormuz history was
   considered and declined.

2. **Track ownership.** Section 5 assigns Track A to ChatGPT. On 2026-08-27 Mher
   reassigned Track A to Claude, accepting on the record that the cross-review in
   section 8, under which Claude reviews Track A, is not available for work Claude
   itself wrote. The file lists in section 5 are unchanged; only the owner is.

### Execution-artifact correction -- 2026-08-28, directed by Mher

Not a version bump. The design of A1--A4 is unchanged: no model, threshold,
scale, prediction, alarm date or severity value is altered by anything in this
addendum, and none may be. The corrections are to what the A4 run *records* and
to which cells it *evaluates*, both of which had drifted from what section 6
declares.

1. **Mode 3 form scope.** The runner evaluated both detector forms under the
   transport pairing, producing six raw-level cells the plan never declared.
   Mode 3 now states its evaluated form explicitly and the runner reads the
   declaration rather than looping every form. Removing those six cells
   mechanically re-ranks the `august` raw-level group, which is the only
   permitted consequence; every declared alarm date and severity value is
   byte-identical to the run before the correction.

2. **Coverage assertion.** The run now asserts exact set equality between the
   declared mode/model/form/horizon cells and the cells actually evaluated,
   in both directions, and fails on any difference.

3. **Git checkpoint before writing.** The checkpoint was taken after the
   outputs were written, so it reported the run's own untracked outputs as
   dirt and could not distinguish a clean checkout from a dirty one.

4. **Plan and input hashes.** The manifest recorded the configuration hash
   only. It now records the plan hash and the hash of every input read.

5. **Cross-vintage revision artifact.** It was written to a path derived from
   another output's name, so no declaration named it and no hash covered it.
   It is now declared in `final.outputs` and hashed like every other output.

None of this suppresses a result. In particular the pre-onset alarms -- the
detectors that fire during the surveillance window well before the operational
onset -- are preserved, counted, and reported in the manifest. They are a
finding about detector behaviour on this unit and are not to be tuned away.

Amending this document supersedes the plan hash recorded in the Phase 0 freeze
entry of `docs/DECISION_LOG.md`. Mher owns that log and records the new hash
there; no assistant edits it.

## 1. Purpose and governance

This is the durable shared plan for the proposed revision-robust Hormuz
machine-learning work. It assigns non-overlapping ownership to ChatGPT and
Claude and makes Mher's local execution authoritative for every empirical
result.

The committed thesis core is B1 plus A1--A4. B2 is a positive-control gate and
B3 opens only if B2 passes its design and support criteria. B4 is not part of
the committed implementation. Feasibility constrains the design but is not the
criterion by which scientific value or chapter priority is ranked.

This document does not silently replace the formal proposal, prior advisor-side
acceptance, `config/settings.yaml`, the locked treatment cutoff, or frozen
legacy artifacts. `AGENTS.md` remains controlling. Any formal thesis
realignment still follows the documented governance process.

Instruction priority is:

1. Mher's explicit request for the current phase.
2. `AGENTS.md` and repository safety/governance rules.
3. Phase 0 specifications frozen under this plan.
4. This document.
5. Older exploratory plans.

No assistant may treat an attached document as authorization to expand scope,
acquire proprietary data, change the formal proposal, or edit files owned by
the other track.

## 2. Thesis concept

### One-sentence version

The measurement instrument for Hormuz changed while the disruption was
unfolding, so the project builds a cross-chokepoint system that can detect and
describe the Hormuz disruption despite that unit-specific historical revision.

### Working title

> **An Instrument That Moved: Revision-Robust Machine Learning and
> Cross-Chokepoint Evidence from the 2026 Strait of Hormuz Disruption**

Alternative:

> **An Instrument That Moved: Cross-Chokepoint Forecasting, Calibrated
> Detection, and the 2026 Strait of Hormuz Disruption**

The final title is a Phase 0 governance decision.

### Research questions

1. **Instrument stability:** How exceptional was the retrospective revision of
   Hormuz tanker counts relative to the other 27 chokepoints, and how did it
   change the historical measurement construct?
2. **ML detection:** Can a model trained across the other 27 chokepoints detect
   the Hormuz disruption with controlled false alarms? How do a raw-level
   detector and a scale-invariant detector differ across the July and August
   PortWatch states after proportional rescaling is separated from the
   non-proportional residual revision?
3. **Observable redistribution (gated extension):** If the Red Sea-to-Cape
   positive control survives a pre-specified, dependence-aware spatial placebo
   design, does a multiplicity-adjusted receiver test find compensating
   chokepoint activity after Hormuz?

### Known facts to reproduce, never hard-code

- Hormuz tanker rows changed July to August: approximately **97.4545%**.
- Malacca, next highest: approximately **0.1091%**.
- Median across 28 chokepoints: approximately **0.0364%**.
- August/July annual Hormuz ratios for 2019--2025: approximately
  `0.843, 0.848, 0.842, 0.827, 0.825, 0.818, 0.826`.
- Red Sea positive control: Bab el-Mandeb loss approximately **7.88** tanker
  transits/day; Cape gain approximately **7.03/day**; aggregate correspondence
  approximately **89%**.

Scripts must derive these values from frozen inputs. A discrepancy stops the
relevant phase.

### Claim boundaries

Permitted:

- retrospective measurement-state revision;
- cross-chokepoint predictive and detection performance;
- retrospective out-of-training Hormuz stress test;
- observable compensating activity at specified chokepoints;
- aggregate changes consistent with rerouting.

Prohibited without new evidence:

- causal ATT or structural treatment effect;
- claiming PortWatch changed Hormuz because of the disruption;
- claiming the same vessels moved from Bab el-Mandeb to the Cape;
- claiming Hormuz traffic physically stopped;
- fleet-wide darkness correction from the LNG-carrier frame;
- observed cargo ton-miles, freight incidence, or cargo-level flows;
- averaging July and August measurement states;
- calling Hormuz a pristine prospective holdout;
- post-Hormuz model, threshold, feature, receiver, or hyperparameter tuning.

Cross-vintage agreement after within-series normalization is not, by itself,
an empirical robustness result: a purely multiplicative revision cancels by
construction. Robustness claims apply only to raw-level behavior and to the
non-proportional, date-specific residual revision that remains after the
proportional component is removed.

The snapshots show that a unit-specific historical revision occurred between
two captures collected during the event. They do not establish the provider-side
reason. Treatment-dependent measurement error is a hypothesis and material
risk, not a demonstrated mechanism without documentary evidence.

## 3. Verification contract

Mher is the release authority. A real-data result does not become a project
result until Mher runs the command locally and supplies the complete output.

For each phase:

1. The assistant states methodological justification, data requirement,
   expected limitations, and next practical action.
2. The assistant implements only the current phase and synthetic/unit tests.
3. The assistant returns files changed, exact commands, expected schema and
   invariants, known warnings, and a stop-and-report instruction.
4. Mher runs the commands and pastes complete terminal output.
5. The owner verifies; the other assistant performs read-only adversarial review.
6. Mher authorizes or rejects the next phase.

Assistants may run synthetic tests. Mher reruns all real-data scripts, tests,
and final artifact generation. "All tests passed" without the actual summary is
not verification.

Changing a frozen configuration after a Hormuz final run invalidates that run.
Any later specification receives a new version and is labeled exploratory.

## 4. Phase 0: user-owned scope freeze

| Item | Recommended decision |
|---|---|
| Primary outcome | `n_tanker` |
| Development population | 27 non-Hormuz chokepoints |
| Full data start | `2019-01-01` |
| Development period | `2019-01-01` through `2023-12-31` |
| Hyperparameter validation | `2024-01-01` through `2024-12-31` |
| Detector calibration | Multi-year out-of-fold/prequential residuals from 27 non-Hormuz units, excluding pre-declared exposed unit-days |
| Hormuz pre-onset surveillance | `2025-12-01` through `2026-02-27`; scoring only, never calibration |
| Locked operational onset | `2026-02-28` |
| Common July/August scoring end | `2026-07-07` |
| Forecast horizons | 1, 7, and 30 days |
| Final test description | Retrospective out-of-training stress test |
| Measurement states | July and August, never averaged |
| Detector forms | Raw-level and scale-invariant, both frozen before Hormuz scoring |
| Post-Hormuz tuning | Prohibited |
| New causal layer | Dropped |

Phase 0 must freeze the rolling-origin fold geometry and a unit-day event mask
before calibration. The mask excludes exposed observations for the affected
unit only; an event at one chokepoint does not delete that date for all other
units. The mask must be based on dated external/event records and cannot be
constructed from large residuals. There is no assumption that the whole of
2025 was a normal calibration regime.

### Recommended alarm definition

- Daily standardized negative forecast error is the nonconformity score.
- Alarm begins after two consecutive threshold exceedances.
- A new episode requires seven quiet days.
- Primary threshold targets at most approximately two alarm episodes per
  monitored chokepoint-year in the eligible out-of-fold residual pool.
- System-wide episodes across all 27 development units are also reported.
- Thresholds are calibrated separately for each frozen model/detector form.
- Calibration reports pooled and unit-level false alarms so a few quiet series
  cannot hide poor control on volatile or structurally changing units.

### Recommended severity measures

- first alarm date;
- detection delay from `2026-02-28`;
- cumulative standardized negative error over 7 and 30 days;
- Hormuz rank among 28 chokepoints;
- agreement of alarm date and rank across measurement states.
- whether any alarm occurred during the pre-onset surveillance interval.

An alarm before `2026-02-28` is reported as a pre-onset alert and, relative to
the locked operational onset, as a false alarm. It is not removed, relabeled,
or used to retune the threshold after inspection.

### Repository checkpoint

At the time version 1.1 was written, the current branch was
`ml/multi-event-propagation`, `main` was its ancestor, and it was 19 commits
ahead of `main`. The plan file itself was untracked. These are recorded facts,
not permanent assumptions; Mher must reproduce them before implementation.

The multi-event branch is the required foundation because it contains the
panel builder and existing pair statistic. Do not begin from `main` and then
silently reconstruct or cherry-pick the dependency chain. Before
implementation, Mher runs:

```bash
git branch --show-current
git status --short
git diff --stat
git rev-parse HEAD
git rev-list --count main..HEAD
git merge-base --is-ancestor main HEAD
```

Mher reviews untracked artifacts. Do not blindly use `git add -A`, discard
unrelated work, or use a destructive reset.

After Mher has checkpointed or otherwise resolved existing uncommitted work,
Mher records the foundation commit and creates the implementation branch from
that exact commit. Recommended branch name:

```bash
git switch -c ml/hormuz-revision-robust
```

If that branch already exists, or if the reproduced ancestry/count differs,
stop and inspect rather than overwriting it. No merge to `main` is required to
start; the foundation commit and resulting branch name belong in every phase
manifest.

Record source hashes:

```bash
shasum -a 256 \
  data/raw/portwatch/Daily_Chokepoints_Data.csv \
  data/raw/portwatch/vintages/Daily_Chokepoints_Data__vintage_2026-08-09.csv
```

Mher owns `docs/DECISION_LOG.md`. Neither assistant edits it unless explicitly
assigned one bounded update.

## 5. File ownership

### Track A -- ChatGPT

```text
config/hormuz_detection.yaml
src/lngfreight/global_forecaster.py
src/lngfreight/disruption_detector.py
scripts/run_hormuz_detection.py
tests/test_global_forecaster.py
tests/test_disruption_detector.py
docs/HORMUZ_DETECTION_MODEL_CARD.md
```

### Track B -- Claude

```text
config/hormuz_measurement_audit.yaml
config/hormuz_receiver_test.yaml
src/lngfreight/instrument_shift.py
src/lngfreight/receiver_equivalence.py
src/lngfreight/propagation.py          # B2 compatibility migration only
scripts/run_hormuz_measurement_audit.py
scripts/run_receiver_test.py
tests/test_instrument_shift.py
tests/test_receiver_equivalence.py
tests/test_propagation.py              # B2 compatibility test only
docs/HORMUZ_MEASUREMENT_NETWORK_CARD.md
```

### Shared-file rules

- Neither track edits `config/settings.yaml` or frozen primary configurations.
- ChatGPT does not edit propagation, GFW, receiver, or measurement code.
- Claude does not edit the global forecaster or detector.
- For B2 only, Claude may move the existing `pair_reallocation` implementation
  from `propagation.py` into `receiver_equivalence.py` and leave a compatibility
  import/wrapper. This is a preservation refactor, not a new implementation.
  The old and new import paths must return identical results in a regression
  test. No ALS behavior may be changed.
- Neither assistant edits raw data.
- External data enter through the registry with provenance.
- No new dependency without Mher's documented approval.
- Existing TSFM outputs may be frozen benchmarks. This plan does not authorize
  new transformer training or fine-tuning.
- If a shared code change is necessary, both tracks stop and Mher assigns one
  owner.

Parallel work uses disjoint files. If worktrees are used, first confirm that
immutable and gitignored snapshots are available in both. Otherwise run tracks
sequentially in the same working tree.

## 6. Track A -- core ML and detector

### A1. Task generator and leakage guards

#### Justification

The ML object is forecast and detection performance over fixed chronological
tasks, not an estimator-defined Hormuz shortfall. The model must transfer from
the other 27 chokepoints without Hormuz post-onset information.

#### Requirements

- Training examples come from 27 non-Hormuz chokepoints.
- Hormuz rows after `2026-02-27` are scoring-only.
- Hormuz is excluded from detector calibration entirely; its rows from
  `2025-12-01` onward are pre-onset/final surveillance scores.
- Hormuz post data are inaccessible to fitting, feature selection, scaling,
  calibration, and hyperparameter selection.
- Targets occur strictly after their feature windows.
- Chronological splits only.
- Context or train-only scaling.
- No identity embedding requiring a fitted Hormuz category.
- Separate direct tasks at 1, 7, and 30 days.
- Initial compact features:
  - lags 1, 7, 14, 28, and 56;
  - rolling mean/median and volatility;
  - calendar features;
  - optional network factors estimated inside each training fold.
- No contemporaneous future or post-treatment exogenous variables.

#### Tests

- Deliberate Hormuz-post training access raises an error.
- Shuffling Hormuz-post outcomes does not change development parameters.
- Scaling is training/context-only.
- Target timestamps follow feature timestamps.
- Split boundaries reproduce the frozen specification.
- Unit-day event-mask exclusions reproduce the frozen specification and do not
  delete unaffected units on the same dates.
- July and August are not joined or averaged.
- Fixed seed yields deterministic task geometry.

#### Mher commands

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest \
  tests/test_global_forecaster.py \
  tests/test_disruption_detector.py \
  -q -p no:cacheprovider
```

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python \
  scripts/run_hormuz_detection.py --phase audit --check-only
```

**Stop and report:** A1 reports geometry, hashes, features, and leakage checks.
It must not print Hormuz post-event results.

### A2. Global forecasting model

Use a defensible global gradient-boosting or regularized model supported by the
existing environment. A practical default is one scikit-learn boosting model
per horizon with robust context normalization. Do not train a transformer from
scratch.

Baselines:

1. Seasonal naive.
2. Local AR(1,7).
3. Global gradient boosting.
4. Frozen Chronos-2 and TimesFM benchmarks where identical task compatibility
   is demonstrated.

Selection rules:

- Small grid frozen in `config/hormuz_detection.yaml`.
- Hyperparameters selected on 2024 only.
- Report MASE/scaled MAE.
- Report pinball loss if quantiles are modeled.
- Report interval coverage.
- Do not invent a weighted winner score.
- Losing to a baseline is reportable and does not authorize more tuning.

The scientific success criterion is a leakage-safe, reproducible comparison
and calibrated detector evaluation, not a global-model victory. Each frozen
model receives its own calibration. The global model remains the
cross-chokepoint transfer experiment even if it loses. If local AR(1,7) wins on
the frozen 2024 validation design, the primary conclusion is that pooling did
not overcome cross-chokepoint heterogeneity under this design; the winning
baseline is reported as the operational comparator. Hormuz results cannot
select the winner or reopen the grid.

#### Mher command

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python \
  scripts/run_hormuz_detection.py --phase validate
```

Expected outputs:

```text
data/processed/hormuz_detection_validation_scores.csv
data/processed/hormuz_detection_validation_predictions.csv
data/processed/hormuz_detection_validation_manifest.json
```

The manifest records input/configuration hashes, git commit, splits, features,
package versions, seed, command, and no-Hormuz-post confirmation.

### A3. Detector calibration

Produce genuine out-of-fold or rolling-origin residuals across the 27
non-Hormuz development units using the Phase 0 fold geometry. Remove only the
pre-declared exposed unit-days. Calibrate raw-level and scale-invariant
detectors separately, for every frozen model that will be evaluated in A4.

Report threshold, admissible residual count, event-mask exclusions,
false-alarm episodes per chokepoint-year, unit-level and pooled false alarms,
system-wide episodes, episode durations, and pseudo-held-out development-unit
results. No Hormuz row participates in calibration, and no residual-derived
rule may alter the event mask.

#### Mher command

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python \
  scripts/run_hormuz_detection.py --phase calibrate
```

Expected outputs:

```text
data/processed/hormuz_detector_calibration.csv
data/processed/hormuz_detector_false_alarms.csv
data/processed/hormuz_detector_calibration_manifest.json
```

After acceptance, Mher records:

```bash
shasum -a 256 config/hormuz_detection.yaml
git rev-parse HEAD
```

### A4. Final Hormuz stress test

Run the frozen system in the following modes:

1. July-state raw-level and scale-invariant detectors.
2. August-state raw-level and scale-invariant detectors.
3. Frozen July scale-invariant detector transported to August. Mode 3 evaluates
   the scale-invariant form **only**. A raw-level transport is not declared
   here and is not a result: the raw-level score is not invariant to the
   proportional component of the vintage revision, so a raw-level cell under
   this pairing would confound transport with rescaling. The raw-level score is
   still computed and kept in the daily record; it is simply not an evaluated
   cell. (Made explicit as an execution-artifact correction; no design change.)
4. Frozen global model and seasonal naive under both states. Local AR(1,7) is
   a development-only baseline and is not scored on Hormuz: it needs a
   unit-specific fit that leave-Hormuz-out forbids. Seasonal naive is a lookup
   rather than a fit, so it is scored on Hormuz normally. (Amended in 1.2.)

The evaluated cells are exactly the cross product of each mode's declared forms
with the models of mode 4 and the frozen horizons. The script asserts that set
equality in both directions -- no declared cell missing, no undeclared cell
present -- and fails the run on any difference.

Compare alarm date, delay, 7-day and 30-day severity, rank, and cross-state
agreement. Decompose the cross-vintage difference into the component explained
by proportional rescaling and the component associated with the remaining
non-proportional residual revision. The script refuses a configuration-hash
mismatch.

A synthetic unit test must multiply an entire series by a positive constant
and verify the expected invariance of the scale-invariant detector. Agreement
under that test is mathematical behavior, not empirical evidence. The
cross-vintage empirical claim concerns departures from that proportional case.

#### Mher command

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python \
  scripts/run_hormuz_detection.py \
  --phase final \
  --vintages both \
  --confirm-frozen-spec YOUR_RECORDED_SHA256
```

Expected outputs:

```text
data/processed/hormuz_detection_final_daily.csv
data/processed/hormuz_detection_final_summary.csv
data/processed/hormuz_detection_cross_vintage.csv
data/processed/hormuz_detection_cross_vintage_revision.csv
data/processed/hormuz_detection_final_manifest.json
```

Every one of those paths is declared in the configuration's `final.outputs`
block and hashed into the manifest. The revision file carries the per-day
proportional/residual decomposition behind the cross-vintage summary; it was
previously written to a derived path that no declaration named, which is
corrected here.

The manifest records the plan hash, the configuration hash, the hash of every
input the run reads, and the git checkpoint captured **before** any output is
written -- a checkpoint captured afterwards reports the run's own outputs as
working-tree dirt and says nothing about the state the run was made from.

**Stop and report:** No tuning after A4.

## 7. Track B -- measurement and gated redistribution

### B1. Instrument revision audit

Analyze:

- percentage changed by chokepoint and vessel class;
- July/August means and annual Hormuz ratios;
- additive and multiplicative mappings;
- fitted proportional mapping and residuals after that mapping;
- share of the revision explained by proportional rescaling versus
  non-proportional/date-specific residual change;
- temporal distribution of revisions;
- tanker capacity and total-count revisions;
- proof that states remain separate;
- WTO file count, retrieval horizons, and distinct historical value regimes.

The proportional component must be identified by a frozen estimator and sample,
not chosen for the cleanest fit. The default is a zero-intercept July-to-August
mapping estimated on overlapping daily observations from `2019-01-01` through
`2025-12-31`, with an affine mapping and extension through `2026-02-27` reported
as declared sensitivities. Report the fitted scale, residual RMSE/distribution,
and the fraction of squared revision error remaining after proportional
mapping. Report pre-onset and post-onset residual behavior separately.

#### Mher commands

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest \
  tests/test_instrument_shift.py \
  -q -p no:cacheprovider
```

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python \
  scripts/run_hormuz_measurement_audit.py --check
```

Expected outputs:

```text
data/processed/portwatch_instrument_shift_by_chokepoint.csv
data/processed/portwatch_hormuz_revision_daily.csv
data/processed/portwatch_hormuz_revision_annual.csv
data/processed/wto_measurement_state_audit.csv
data/processed/hormuz_measurement_state_manifest.json
```

ChatGPT consumes the accepted manifest read-only.

### B2. Red Sea positive-control gate

Migrate the existing `pair_reallocation` function out of the exploratory ALS
module without changing its arithmetic. It is already independent of fitted
loadings. Preserve the legacy import path and prove numerical identity before
adding a new null design. Do not maintain two implementations.

Requirements:

- Pair fixed in configuration.
- Reproduce observed pair arithmetic before changing the null.
- Primary evidence is a placebo-in-space analysis at the actual Red Sea onset.
- The eligible ordered-pair family, support rules, and standardization are
  frozen before the observed post-onset receiver gains are inspected.
- Each pair statistic is standardized using only its own pre-onset variation;
  raw changes from dissimilar high- and low-volume pairs are not treated as
  exchangeable.
- Report same-receiver/alternative-emitter and
  same-emitter/alternative-receiver placebo families separately.
- Dependence across pairs is explicit. Use a pre-specified maximum statistic or
  cluster-aware randomization scheme; never call roughly 700 ordered pairs 700
  independent observations.
- A cross-sectional percentile may be reported descriptively. An inferential
  p-value is permitted only if the exchangeability and clustering design is
  justified and frozen.
- Secondary temporal placebos use every unique admissible pseudo-onset once,
  not 250 or 1,000 resamples with replacement.
- Exclude documented disruption windows from the temporal pool, preserve
  block dependence, and report sensitivity to 90-, 180-, and 365-day guards.
- For every guard, report the number of unique admissible dates, approximate
  non-overlapping window count, and attainable finite-sample p-value floor.
- Fixed seed only where a dependence-aware randomization actually requires it.
- Where valid, empirical finite p-values use:

  ```text
  p = (1 + number of null statistics >= observed) / (B + 1)
  ```

- `B` must count valid unique/randomization draws under the frozen design, not
  repeated samples presented as new temporal information.
- Report loss, gain, recovered fraction, null, and p-value.
- The 89% quantity is aggregate correspondence consistent with rerouting, not
  vessel linkage.

Gate: if pair exchangeability cannot be defended, the spatial analysis is only
a standardized rank; if temporal support is weak, its p-value is secondary and
reported with its floor. B2 may remain a descriptive positive control, but B3
does not open unless Mher accepts the null design and effective support.

#### Mher commands

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest \
  tests/test_receiver_equivalence.py \
  -q -p no:cacheprovider
```

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python \
  scripts/run_receiver_test.py --phase positive-control
```

Expected outputs:

```text
data/processed/redsea_cape_positive_control.csv
data/processed/redsea_cape_null_distribution.csv
data/processed/redsea_cape_manifest.json
```

### B3. Freeze and run Hormuz receiver test

B3 is not part of the guaranteed core. It starts only after B1 and A1--A4 are
complete and B2 passes its gate. Claude proposes candidates from route topology, independent literature,
pre-event relationships, and operational logic. Post-Hormuz increases cannot
select receivers. Mher approves and freezes the candidate set, rationale,
horizon, standardized statistic, eligible spatial null, temporal sensitivity,
multiplicity correction, seed, and recovery-bound method.

Use a maximum statistic across candidates and produce an upper bound on
observable recovery. Do not report 27 unadjusted tests as independent.

Question:

> How much compensating activity at the pre-specified observable receivers
> could have occurred without detection?

Mher records:

```bash
shasum -a 256 config/hormuz_receiver_test.yaml
```

Then runs:

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python \
  scripts/run_receiver_test.py \
  --phase hormuz-final \
  --confirm-frozen-spec YOUR_RECORDED_SHA256
```

Expected outputs:

```text
data/processed/hormuz_receiver_tests.csv
data/processed/hormuz_receiver_max_null.csv
data/processed/hormuz_observable_recovery_bound.json
data/processed/hormuz_receiver_test_manifest.json
```

Permitted conclusion: no pre-specified receiver exceeded the adjusted null, and
the analysis rules out observable recovery above the reported bound within the
candidate set and measurement design. Do not write "the traffic stopped."

### B4. LNG darkness pilot -- outside the committed scope

Do not implement, rerun, or present this as a thesis phase under version 1.1.
Existing artifacts are preserved but quarantined as exploratory work. A bounded
LNG-carrier observability appendix may be reconsidered only after B1 and
A1--A4 are complete, through a new explicit authorization and plan version. It
may never be used to correct tanker-wide PortWatch counts or imply intentional
AIS darkness.

## 8. Cross-review and integration

1. ChatGPT reviews Claude's accepted manifests, null design, multiplicity, and
   interpretation without editing Claude's files.
2. Claude reviews ChatGPT's leakage guards, split geometry, calibration, and
   model card without editing ChatGPT's files.
3. Mher adjudicates findings.
4. Mher runs targeted and full tests.
5. Thesis figures/prose follow only after acceptance.

### Targeted tests

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest \
  tests/test_global_forecaster.py \
  tests/test_disruption_detector.py \
  tests/test_instrument_shift.py \
  tests/test_receiver_equivalence.py \
  tests/test_propagation.py \
  -q -p no:cacheprovider
```

### Full suite

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest \
  -q -p no:cacheprovider
```

### Final hashes

```bash
shasum -a 256 \
  config/hormuz_detection.yaml \
  config/hormuz_measurement_audit.yaml \
  config/hormuz_receiver_test.yaml \
  data/processed/hormuz_detection_final_manifest.json \
  data/processed/hormuz_receiver_test_manifest.json
```

Preserve complete terminal output and the git commit. Reject hand-edited CSVs,
undocumented reruns, and manifests with mismatching hashes.

## 9. Manifest contract

Every real-data phase writes a JSON manifest with:

- script and command;
- UTC run time;
- git commit and dirty status;
- input paths and SHA-256 hashes;
- configuration path and hash;
- measurement state;
- analysis window;
- frozen event-mask path/hash and excluded unit-day counts, where applicable;
- detector form (`raw_level` or `scale_invariant`), where applicable;
- features/receivers as applicable;
- seed and package versions;
- output paths and hashes;
- leakage/sealing assertions;
- limitations;
- explicit `exploratory` or `frozen` status.

Outputs are never silently substituted across measurement states.

## 10. Assistant handoff template

```text
PHASE: [A1/B1/etc.]
STATUS: ready for Mher's execution | blocked

Methodological justification:
[short statement]

Data used:
[paths and measurement state; no unverified results]

Files changed:
- [file]

Unit/synthetic tests run by assistant:
- [command and output]

Mher must run:
1. [exact command]
2. [exact command]

Expected schema/invariants:
- [condition]

Claims not yet authorized:
- [real-data claims]

STOP AND REPORT:
Paste the complete terminal output. Do not proceed.
```

## 11. Ready-to-send initial commands

### Claude

> Own Track B only under
> `docs/HORMUZ_TECHNICAL_EXECUTION_PLAN.md`: instrument revision audit,
> then the gated receiver/equivalence test. Do not run the LNG-darkness pilot or
> edit the ML model, detector, primary settings, propagation module, raw data,
> or decision log, except for the explicitly authorized B2 compatibility
> migration of `pair_reallocation`. Begin with B1 only. Decompose the Hormuz
> revision into proportional and non-proportional components. State
> justification, data requirement, limitations, and next action; write code and
> unit tests; then stop and give me the real-data command, expected schema,
> invariants, and files changed. Do not claim a result until I run the command
> and paste the complete output.

### ChatGPT

> Start Track A, Phase A1 only, following
> `docs/HORMUZ_TECHNICAL_EXECUTION_PLAN.md`. Build the leave-Hormuz-out task
> generator, rolling-origin residual geometry, unit-day event-mask guards, and
> leakage tests under the Phase 0 frozen design. Do not edit Track
> B files, primary settings, raw data, or the decision log. Do not run, print,
> or inspect Hormuz post-event results. Stop after giving me files changed,
> unit-test and audit commands, expected invariants, and the stop-and-report
> handoff.

## 12. Stop conditions

Stop rather than work around:

- input hash mismatch;
- missing/redefined measurement-state file;
- fitting/calibration reads Hormuz post data;
- random train/test split;
- target leakage through factors or scaling;
- configuration changed after freeze hash;
- receiver selected from post-Hormuz outcomes;
- contaminated pseudo-onset null;
- temporal p-values based on repeated draws rather than effective unique
  support;
- spatial-pair inference that assumes independence or exchangeability without
  a frozen justification;
- calibration event mask inferred from model residuals;
- inclusion of Hormuz or exposed unit-days in detector calibration;
- new proprietary requirement;
- failure to reproduce raw-data invariants;
- attempt to relabel predictive/descriptive evidence as causal.

Negative results are not stop conditions. Report them under the frozen design.

## 13. Intended thesis structure

1. Problem and literature.
2. Data and the unit-specific measurement revision.
3. Cross-chokepoint model and calibrated detector.
4. Hormuz stress test across measurement states.
5. Gated extension: Red Sea positive control and, only if the gate passes,
   Hormuz observable-recovery bound.
6. Measurement-source and censoring limitations.
7. Limitations, negative results, and non-causal interpretation.

The legacy 6,869 AR shortfall becomes an opening illustration of specification-
and measurement-state dependence, not the primary estimand. The 28-chokepoint
panel becomes the ML development population. Frozen TSFM outputs become
benchmarks. The ALS propagation model remains exploratory description unless
rebuilt with a genuine held-emitter prediction function.
