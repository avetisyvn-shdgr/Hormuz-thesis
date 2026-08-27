# Hormuz detection model card

**Current phase:** A4 — final Hormuz stress test  
**Model status:** implemented; A2 accepted by Mher on 2026-08-27  
**Detector status:** design **version 2**, **accepted by Mher on 2026-08-28**;
thresholds frozen  
**A4 status:** implemented and tested; **not executed**. Claude has not scored
Hormuz and has not inspected any Hormuz outcome.  
**Track owner:** Claude, reassigned from ChatGPT by Mher on 2026-08-27  
**Governing plan:** `HORMUZ_TECHNICAL_EXECUTION_PLAN.md`, version 1.2

## Purpose

A1 fixes the forecasting-task geometry and the information boundaries that all
later Track A phases must reuse. The research object is out-of-sample forecast
and detection performance across fixed chronological tasks. It is not a causal
effect estimator and does not estimate a Hormuz shortfall.

## Frozen task contract

- Outcome: daily PortWatch `n_tanker`.
- Development population: the 27 non-Hormuz chokepoints listed in
  `config/hormuz_detection.yaml`.
- Direct horizons: 1, 7, and 30 calendar days.
- Development targets end on 2023-12-31.
- Hyperparameter-selection targets are restricted to 2024 and begin only when
  their forecast origin reaches the 2023-12-31 development cutoff: 2024-01-01,
  2024-01-07, and 2024-01-30 for the 1-, 7-, and 30-day horizons respectively.
- Rolling-origin residual blocks run from 2021-01-01 through 2025-11-30 with
  expanding training windows, 30-day assessment blocks, and 30-day steps.
  Within each block, the fit cutoff is horizon-specific (`score_start -
  horizon`), so it is never later than any scored task's forecast origin.
- Residuals from 2024 are labeled hyperparameter-validation residuals and are
  not eligible for detector calibration. Eligible calibration geometry comes
  from 2021–2023 and 2025 through 2025-11-30, subject to the event mask.
- Hormuz is never a fitted category and never enters fitting, feature
  selection, scaling, hyperparameter selection, or detector calibration.
- Hormuz targets from 2025-12-01 through 2026-07-07 are scoring-only. The
  operational onset remains 2026-02-28.
- July and August are independent measurement states. A restricted operation
  rejects a task table containing both states.

The deterministic task key is:

```text
measurement_state, fold_id, unit, horizon_days, target_timestamp
```

Every row also records `feature_timestamp`, and the invariant is:

```text
target_timestamp = feature_timestamp + horizon_days
feature_timestamp < target_timestamp
fit_end <= feature_timestamp  # validation and rolling residual tasks
```

Task validation reconstructs role-specific frozen bounds, rolling fold
membership, horizon-specific fit cutoffs, residual roles, and calibration
eligibility. Caller-supplied labels cannot authorize a non-frozen horizon,
unknown fold, post-window task, or relabeled residual role.

## Feature contract

A1 implements only compact, same-unit features:

- lags 1, 7, 14, 28, and 56;
- rolling mean, median, and standard deviation over 7, 28, and 56 days;
- target day of week and cyclical target month, which are calendar facts known
  at forecast time.

`lag_1` is the value observed at the feature timestamp; `lag_k` is observed
`k-1` days earlier. Rolling windows end at the feature timestamp. Materialized
tasks record the maximum feature-source timestamp so a later timestamp cannot
enter silently. Network factors and identity embeddings are disabled. Any
future network-factor extension must estimate factors independently inside
each training fold.

## Scaling contract

The feature standardizer can be fitted only on rows labeled `development_fit`
or `rolling_fit`, and only on a non-empty subset of the feature names declared
in the A1 specification. Targets, timestamps, identifiers, task metadata, and
undeclared columns are rejected. It records the measurement state, maximum
fit-target timestamp, task-geometry hash, means, and scales. It refuses an
implicit cross-state transform.

The scale-invariant detector's future baseline is prepared by a separate
median/MAD context scaler. Its context ends on 2025-11-30. Surveillance and
post-onset Hormuz values cannot enter its center or scale.

## Unit-day event mask

The A1 mask is expanded from records in `config/hormuz_event_chronology.yaml`,
an external chronology compiled on 2026-08-27; that source file is SHA-256
checked.
Each executable mask record names a structured source-event key, and the
loader requires exact agreement with that source record's onset, end, and
formal affected-unit field. Each record also declares `residual_derived:
false`. The loader rejects unknown sources or source events, source-hash drift,
record/source divergence, duplicate unit-days, empty masks, Hormuz mask
records, or any record not explicitly sealed as non-residual-derived.

The Red Sea mask covers Bab el-Mandeb and Suez because those are the formal
affected units in the cited register. Cape of Good Hope is discussed there as
an observed substitution route but is not included in the executable mask.

Mask application joins on `(unit, target_timestamp)` only. An exposed unit-day
does not remove other chokepoints on the same date. Hormuz is excluded from the
calibration population independently of the event mask.

### Why the mask does not use the propagation register

`config/multi_event_propagation.yaml` records the same four events, but three
of its four onsets are marked "data-derived": they were fixed by applying a
rule to the PortWatch panel. Using them to trim the detector-calibration pool
would draw the mask boundary from the outcome being calibrated on, which
inflates apparent false-alarm control.

On 2026-08-27 Mher authorised replacing them with externally sourced dates.
The selection rules were declared before the dates were applied: for Panama,
the first announced reduction in the number of daily transits; for the Red Sea,
the first suspension of transits by a major carrier. Because the outcome is a
transit count, anchors must be events that reduce the number of transits;
Panama draft restrictions from 2023-05-22 limited cargo per vessel rather than
vessel numbers and are recorded as context only.

Two onsets moved, and both had been leaving disrupted days inside the
calibration pool:

| Event | Register onset | External onset | Effect |
|---|---|---|---|
| Suez Ever Given | 2021-03-23 | 2021-03-23 | unchanged; external record confirms |
| Kerch | 2022-02-24 | 2022-02-24 | unchanged; already externally anchored |
| Panama drought | 2023-12-19 | 2023-07-30 | 142 restricted days recovered |
| Red Sea | 2024-01-13 | 2023-12-14 | 30 days recovered at two chokepoints |

The mask grows from 2,985 to 3,187 unit-days, shrinking the calibration pool by
about 0.55%. The propagation register is **not modified**; it keeps its own
dates for its own estimator, so Phase 2 propagation results are unaffected.

The chronology carries a citation per date. The Kerch date is the one exception:
it is carried forward from the propagation register's own external-anchor
marking rather than independently restated, and the chronology says so.

## Audit output

`scripts/run_hormuz_detection.py --phase audit --check-only` prints one JSON
object. It contains:

- configuration, plan, input-state, event-source, event-mask, and geometry
  SHA-256 hashes;
- measurement-state file availability without reading outcome rows;
- feature names and fixed horizons;
- complete rolling-origin fold bounds;
- task counts and hashes by measurement state;
- event-mask exclusion counts;
- deliberate leakage-failure checks and computed sealing assertions, including
  hostile non-frozen horizons, target-column scaling, post-window tasks,
  origin-relative fit leakage, residual-role relabeling, and event/source
  record divergence.

The reported `status` is **derived from that evidence, never asserted**. A
hostile check that failed to fail, a positive sealing assertion that is False,
an assertion required to stay False that turned True, or a required assertion
that went missing each flip the audit to `FAIL`, populate `status_failures`,
and make the command exit non-zero. A hostile check that does not raise also
aborts the audit outright. `status: PASS` therefore cannot be printed over
contradicting evidence.

The check-only command writes no files, reads no PortWatch outcome rows, fits
no model, calibrates no detector, and prints no Hormuz outcome.

## Limitations and claim boundary

A1 proves only that the implemented task and access geometry obeys the frozen
rules under unit and synthetic tests. It provides no evidence about predictive
accuracy, detector sensitivity, false-alarm control, measurement robustness,
or the observed Hormuz event. PortWatch remains media/AIS-derived measurement
data with possible reporting bias, historical revision, missingness risk, and
unit heterogeneity. Later predictive results cannot be interpreted as causal
effects.

A3 is implemented and has been run by Claude; it is not accepted. A4 has not
been started.

## A2 — global forecasting model

### What A2 fits

One pooled model per direct horizon (1, 7, 30 days) across the 27 non-Hormuz
development units, on the frozen A1 feature set, fitted on development targets
through 2023-12-31 and scored on the frozen 2024 tasks.

The estimator is **ridge regression solved in closed form**, not gradient
boosting. Plan v1.1 permits "a defensible global gradient-boosting *or
regularized* model supported by the existing environment"; scikit-learn is
absent from `.venv` and `requirements.txt` defers modelling libraries by
design, so the regularized branch was taken. A boosting library would need
Mher's documented dependency approval and a new configuration version. The
penalty is added to the diagonal of the Gram matrix, which makes it positive
definite for any design, so the Cholesky solve is exact and never singular.

### Context normalisation

The development units span three orders of magnitude — Bering Strait averages
under one tanker a day, Malacca over seventy. Pooling raw levels would let the
largest units dominate the loss, so each unit's series is mapped into its own
robust space using the A1 `median/MAD` context scale before pooling:

- level features (lags, rolling means and medians) are centred and scaled;
- dispersion features (`rolling_std_*`) are scaled but never re-centred;
- calendar features are dimensionless and untouched.

Predictions are inverted back to tanker transits per day before scoring, so
every reported error is in raw outcome units.

**The context closes at 2023-12-31, not at the frozen `scaling.context_end` of
2025-11-30.** Nothing selected on 2024 may be influenced by 2024. The later
context end belongs to A4 scoring, not to development.

### Declared comparators

1. **Seasonal naive** — the most recent observation at or before the forecast
   origin whose weekday matches the target weekday. Its source date is
   `target - 7 * ceil(horizon / 7)`, which is always at or before the origin.
2. **Local AR(1,7)** — per unit and per horizon, least squares of the target on
   `lag_1` and `lag_7` with an intercept, fitted on development targets only.
   Direct multi-horizon form, so its task is identical to the global model's.

Frozen Chronos-2 and TimesFM artefacts are **excluded**. Plan v1.1 admits them
only "where identical task compatibility is demonstrated", and they score
`hormuz_tanker_transits`/`hormuz_tanker_capacity` on 30-day rolling folds
inside 2023 from Hormuz's own history: a different unit population, a different
task geometry, and a unit A1 forbids in fitting. Their exclusion authorises no
new transformer training.

### Selection

The ridge penalty is chosen from a frozen grid on the 2024 tasks alone, per
horizon, by mean MASE over the 27 units, ties going to the smaller penalty. No
weighted winner score is computed. Losing to a baseline is a reportable result
and does not authorise reopening the grid: if the local AR(1,7) wins, the
finding is that pooling did not overcome cross-chokepoint heterogeneity under
this design, and the winning baseline becomes the operational comparator.

### Intervals are provisional

Interval half-widths come from empirical quantiles of **in-sample development
residuals**, so they are expected to be anti-conservative. The reported 2024
coverage is the honest check on them. Calibrated intervals are an A3
deliverable and are not claimed at A2.

### A2 sealing assertions

The manifest derives `PASS`/`FAIL` from evidence, exactly as the A1 audit does.
Four assertions must be **False**: a Hormuz row reaching any estimator,
Hormuz being materialised into a task, the validation year influencing a
context scale, and the two measurement states being mixed. The remainder must
be True, including that development
targets stay inside the frozen period, that validation targets stay inside
2024, that the feature scaler saw development only, and that the population is
exactly the 27 non-Hormuz units.

### Known environment warning

numpy here is built against Apple Accelerate, which emits a spurious
`RuntimeWarning: divide by zero encountered in matmul` on healthy, finite
inputs — a plain product of two well-conditioned random matrices reproduces it.
It is a BLAS artefact, not a numerical failure. The code verifies every fitted
coefficient and every design matrix is finite and raises if it is not, rather
than suppressing the warning.

### What A2 does not do

A2 fits no detector, sets no threshold, and touches the August measurement
state not at all. Reading August additionally requires an `allowed_consumers`
entry in `config/sources.yaml` that has not been granted to this script. No A2
number is evidence about the disruption.

On Hormuz specifically, the accurate claim is narrower than "no Hormuz row is
read". The panel is loaded with all 28 chokepoints and the manifest records
`panel_units: 28`. The Hormuz column is never materialised into a task, fitted,
selected on, or scored, and `hormuz_handling` in the manifest records each of
those separately.

## What the A2 result supports, and what it does not

Mher accepted this reading of the A2 result on review of the 2026-08-27 run.

### Supported

The pooled 17-feature ridge model outperformed both declared baselines on the
frozen 2024 tasks: mean MASE roughly 0.74 to 0.78 against roughly 0.82 to 0.83
for local AR(1,7) and roughly 1.0 for seasonal naive. The advantage is
reasonably broad rather than driven by a few units, holding at 22 of 27, 23 of
27, and 20 of 27 chokepoints at the 1-, 7- and 30-day horizons.

### Not supported: "pooling helped"

The two models differ in more than pooling. The global model carries all 17
frozen features; the local AR baseline carries `lag_1` and `lag_7` only. The
comparison therefore cannot separate a pooling gain from a feature-richness
gain. Isolating pooling would need a local model given the same feature set.
State the result as the specified pooled model beating the specified local
baseline, and nothing stronger.

### Not supported: a claim about explained variance

A pooled R-squared against a constant-per-unit predictor comes out near 0.33 to
0.37, but that quantity is dominated by cross-unit scale differences and by the
high-volume waterways. Within each chokepoint the picture is much weaker:
prediction standard deviation is only about 18 to 26 percent of within-unit
actual variation, mean within-unit correlations are about 0.14, 0.13 and 0.05,
and against each unit's own full-2024 mean (an oracle diagnostic, not an
operational baseline) average R-squared is about 0.01, -0.01 and -0.09.

The model therefore tracks slowly changing levels rather than daily movement.
That can still support anomaly detection, which is what A3 asks of it. It does
not license a statement that the model explains a given share of the variation,
and it certainly does not license calling the unexplained remainder
irreducible noise.

### The ridge penalty

Performance was insensitive to alpha across the declared grid: the five
candidates differ in mean MASE by at most 0.000391, roughly 0.05 percent, and
two of the three horizons selected the largest value in the grid. Report that
insensitivity. Do not widen the grid after the fact, and do not read the
insensitivity as a demonstration that the model could not have overfit.

### A lattice in the seasonal-naive residuals only

Pooled seasonal-naive interval widths are identical across horizons because
those residuals are differences of integer counts divided by a context scale of
1.4826 times an integer MAD, so the pooled quantile lands on a lattice point.
The 80 percent boundary sits at 1.6862269, which is 5/2.9652, and the rows
sitting exactly on it come from the six MAD-2 units (Cape of Good Hope, Lombok,
Makassar, Oresund, Panama, Sunda) together with MAD-4 and MAD-6 units. The six
MAD-1 waterways cannot reach that point at all, since it would require an
integer residual of 2.5.

This is a property of integer-valued residuals. The ridge and local AR
residuals are continuous and their widths do differ by horizon (11.214, 11.263
and 11.382 for the selected ridge models), so the lattice says nothing about
how the continuous residuals A3 will calibrate on behave. What survives for A3
is only the narrow point that tied discrete scores are possible and must be
handled by taking the conservative attainable threshold.

## A3 — detector design, frozen 2026-08-27

The `detector:` block in `config/hormuz_detection.yaml` carries the design and
is frozen. It records per-item provenance: eight items Mher decided, and three
Claude proposed that Mher then named individually and ratified in his freeze
instruction, so none of them is carried on silence. Nothing in the block is
outstanding. Any later change to it takes a new configuration version rather
than being edited in place, and invalidates any run made under the old hash.

The direction came from Mher's 2026-08-27 review, which rejected per-chokepoint
thresholds outright: Hormuz never enters calibration, so a unit-specific
threshold would have no Hormuz counterpart to apply. One transferable threshold
per model, horizon and detector form, calibrated against the macro-average
episode rate across units rather than a pooled row-level residual quantile.

### Two leave-one-chokepoint-out tests, not one

The first draft conflated them. They are separate and both run.

`threshold_loco` holds the unit out of threshold calibration only; the model,
context scaling and penalty selection still see it. This isolates whether a
threshold transfers to a unit it was not calibrated on.

`end_to_end_loco` holds the unit out of the cross-unit objects only: global
model fitting, pooled feature standardiser fitting, penalty selection and
threshold calibration. It keeps its own unit context scale, fitted on its own
history, because that is exactly how unseen Hormuz is normalised at A4.
Withholding that too would leave the scale-invariant score undefined and would
not resemble deployment. It costs 405 closed-form fits across 27 units, 3
horizons and 5 penalties, plus rolling residuals.

Two distinct objects were both being called "scaling", which is what the first
draft got wrong. The pooled feature standardiser is fitted across many units at
once and is therefore cross-unit. The unit context scale is one unit's own
median and MAD and is therefore unit-local.

Neither produces the operational threshold. That is refit on all 27 units; the
LOCO thresholds exist for evaluation.

### Detector forms

Mher chose the unstandardised raw score, `s_raw = yhat - y` in transits per day,
over a pooled-dispersion variant, settling the "standardised versus raw units"
tension in plan v1.1 for this form. The scale-invariant form divides by the
unit's own context scale and is invariant under `y -> c*y` because the refitted
context scale carries the same factor.

Stated before calibration, as a design expectation and not a result: a single
threshold in transits per day is dominated by high-volume units, so the raw form
should show little sensitivity on Bering, Magellan or Torres. That degeneracy is
the contrast the two forms exist to expose and must not be tuned away. Hormuz
averages roughly 54.6 transits per day in the July state over 2019-01-01 to
2025-11-30 and roughly 45.4 in the August state over the same window, so it sits
among the high-volume units in either state and the raw form should retain
sensitivity there.

Exceedance is strict (`score > threshold`), which leaves a tied score
non-firing. On ties the threshold is the smallest whose achieved rate is at or
below target, and the achieved rate is reported next to the requested one.

### Masked gaps are segment boundaries

A masked unit-day carries no admissible observation. An earlier draft only
interrupted the exceedance run without letting masked days count as quiet,
which would leave an episode open across Panama's masked interval of roughly a
year and across the open-ended Red Sea and Kerch masks.

A masked gap therefore resets both the exceedance and the quiet counter, no
episode spans a gap, an episode running into one is recorded as right-censored
and terminated on its last eligible day, and a new episode after the gap needs a
fresh pair of consecutive exceedances. Censored episodes are reported separately
so a truncated episode is never counted as a clean one. Per-unit exposure is
eligible days after masking, divided by 365.25.

### The frozen object is the scaling algorithm, not a constant

A3 residuals span 2021-01-01 to 2025-11-30 across 60 expanding folds. Carrying
one context scale fitted through 2023-12-31, as A2 did, would normalise a 2021
score using 2023 to 2025 information and trip the plan's leakage stop condition.
Freezing a single 2019-2020 constant instead would freeze an estimate that can be
badly stale by 2025, and reporting that staleness would not correct the
calibration mismatch.

Mher's ruling is to freeze the transformation. For each fold and horizon, every
unit's median and MAD are refitted on history through that fold's
horizon-specific `fit_end`. In end-to-end LOCO the held-out unit may use its own
history through `fit_end` for normalisation while staying out of every cross-unit
object. At A4 the Hormuz scale is fitted once through 2025-11-30 and held fixed
across surveillance and final scoring, so historical folds use the scale that
would have been available then and A4 uses the scale available at deployment.
Fold-specific normalised residuals stay comparable because the same predeclared
dimensionless transformation applies everywhere even though its constant differs
by fold. Each unit's scale trajectory across folds is reported as a drift
diagnostic.

### Local AR cannot be scored on Hormuz

Mher raised this and decided it on 2026-08-27. The local AR(1,7) needs a
unit-specific fit, which leave-Hormuz-out forbids, so it is a development-only
baseline and is not scored on Hormuz. `tasks.hormuz_training_prohibited` is
unchanged. Seasonal naive is a lookup rather than a fit, so it is scored on
Hormuz normally.

The accepted cost: A4 carries no pooled-versus-local contrast on Hormuz itself.
That contrast is reported on the 27 development units only. The alternative,
fitting a local AR on pre-surveillance Hormuz history, was considered and
declined because it puts a Hormuz-trained model inside a leave-Hormuz-out
design.

## A3 — implementation, and what Claude's run found

`scripts/run_hormuz_detection.py --phase calibrate` implements the frozen design
in `src/lngfreight/detector_calibration.py`. Mher ran the version-1 build himself
on 2026-08-28 and verified it: PASS from a clean commit, A2 gate reproduced,
every leakage and sealing assertion in its required state, output hashes
reproduced. He then ratified the two items below, which moved the design to
version 2. **A3 is still not accepted** — that is a separate, explicit step, and
A4 does not start before it.

The phase refuses to run unless the accepted A2 manifest is `PASS`, was made
under the current configuration hash, was made from a clean tree, and its scores
and predictions still match their recorded hashes. A3 cannot calibrate a model
other than the one Mher accepted.

Claude's run: 110,121 admissible residual rows over 60 expanding folds spanning
2021-01-01 to 2025-11-30, with 5,628 unit-days removed by the frozen event mask,
all sealing assertions in their required state.

### Two items Mher ruled on, 2026-08-28

Both were raised by the version-1 run and are now settled. The detector design is
at **version 2**; `validate_detector_spec` refuses to run against version 1.

**The tie rule was degenerate and has been replaced.** Version 1 said "smallest
threshold whose achieved rate is at or below target". The episode rate is not
monotone in the threshold, and at the bottom of the range it collapses: when
every day exceeds, a unit's whole record becomes one unending episode per
segment, so the macro rate falls back *below* target. Read word by word the rule
therefore selected a threshold firing on 99.997% of unit-days that still "passed"
at well under 2 episodes per chokepoint-year. Mher ratified the **stable-tail
rule**: the smallest candidate whose rate is at or below target *and* whose rate
stays at or below target at every higher candidate. Strict greater-than
exceedance is unchanged. The superseded reading and the unit-day exceedance
share of both are written to every row of `hormuz_detector_calibration.csv`, so
the difference the amendment makes stays auditable. No A3 result was ever
accepted under version 1.

**Context-scale quantisation is an accepted limitation, not a defect to fix.**
`n_tanker` is an integer count, so a low-volume unit's median absolute deviation
is an integer and its context scale is a small integer multiple of 1.4826 that a
longer history does not move; 15 of the 27 units carry a scale constant across
all 60 folds. The per-fold refit is real and runs through each fold's own
`fit_end`; its estimate is simply coarse there. For those units the
scale-invariant score is the raw error over a constant, which narrows the
contrast between the two detector forms that the design exists to expose. Mher
accepted this as documented and **did not authorise changing the scaling
algorithm**, so `evaluation.context_scale_timing` is untouched.

### What the calibration shows

The raw-level form behaves as the frozen design predicted before calibration.
One threshold in transits per day is dominated by the high-volume units: the
median held-out unit never fires at all, while Taiwan, Korea and Malacca fire at
8 to 10 episodes per chokepoint-year against a target of 2. That degeneracy is
the informative contrast, not a defect to tune away.

The scale-invariant form spreads alarms more evenly and so puts *more* units over
target — 14 or 15 of 27 against 9 or 10 for the raw form — but its worst unit
sits at 5.6 rather than 10.5 episodes per year.

`end_to_end_loco` lands close to `threshold_loco` throughout (mean held-out rate
2.08 against 2.04 raw, 2.05 against 1.90 scale-invariant). Withholding a unit
from the model, the pooled standardiser and penalty selection costs little beyond
withholding it from the threshold alone. That is a result about 27 development
units and says nothing yet about Hormuz.

### The penalty is not a stable object

End-to-end LOCO reselects the ridge penalty per held-out unit, as the design
requires. At h=1, dropping one unit changes the selected penalty for 16 of 27
units; at h=7 dropping Bering alone moves it from 1000 to 0.1. This corroborates
A2's finding that the selection surface is nearly flat rather than contradicting
it — where the surface is flat the argmin wanders — but it means "the selected
penalty" should not be reported as a determinate quantity.

### What A3 does not do

A3 reads no Hormuz row and scores nothing on Hormuz. It measures false alarms on
unlabelled development units: there is no disruption label here, so nothing in
this phase measures detection power. August is not read. No threshold calibrated
here is claimed to transfer to Hormuz — that is the A4 question.

## A4 — final Hormuz stress test

Implemented in `src/lngfreight/hormuz_stress.py`, run by
`scripts/run_hormuz_detection.py --phase final`. **Not executed at the time of
writing.** Claude implemented and tested it; the scoring run is Mher's, and no
Hormuz outcome has been inspected. The section below therefore describes what
A4 does and what it may claim, and contains no results.

A4 estimates nothing. It is the only phase that scores Hormuz and the only phase
authorised to read the August measurement state, on Mher's 2026-08-28
authorisation scoped to A4 alone.

### What it refuses to run against

- A configuration whose hash differs from the one the operator passes to
  `--confirm-frozen-spec`. This is the plan's own requirement.
- A3 artefacts whose hashes differ from the accepted
  `b2f04b23…` / `7468d403…`, an A3 manifest that is not PASS, one produced under
  a different design version, or one still carrying a ratification item.
- Any threshold that disagrees between the accepted CSV and the estimate frozen
  in `a3_acceptance.operational_thresholds`.

### No tuning after A4, as a mechanism

The stop condition in the plan is "no tuning after A4". A4 does not promise it;
it is built so that violating it fails.

Every estimated object — pooled standardiser, ridge coefficients, per-state
Hormuz context scale — is built from pre-surveillance data, and the whole system
is digested at that point. Loading the surveillance panel trips a one-way latch
with no reset. Any fit, calibration or threshold load attempted afterwards
raises `PostHormuzTuningError`; the run makes one such attempt on purpose and
records that it was refused. After scoring, the digest is recomputed and must
equal the sealed one. The latch catches an attempt; the digest catches a
success. Both are sealing assertions, and scoring also refuses to start if the
latch was never set, so the seal cannot be bypassed by omitting it.

### The four frozen modes

July-state detectors; August-state detectors; the July scale-invariant detector
transported to August, keeping its July-fitted Hormuz context scale, which is
what makes it a transport test rather than a refit; and the frozen global model
and seasonal naive under both states. Local AR(1,7) is **not** scored on Hormuz —
it needs the unit-specific fit leave-Hormuz-out forbids.

Each state gets its own Hormuz context scale, fitted on that state's own history
through 2025-11-30 and held fixed, per the frozen `a4_deployment` rule. Fitting
one scale from a joined series would average the states, which is prohibited.

### The model A4 deploys, and the one thing the config did not pin

Nothing in the frozen configuration said which fit window the "frozen global
model" uses at deployment. A4 uses **the last frozen rolling fold's fit**: the
fold geometry is frozen, the final fold is the most recent system it defines,
and its residuals sit inside the calibration the accepted thresholds were set
on. The alternative — the 2023-frozen A2 coefficients — would pair a stale model
with thresholds calibrated on per-fold refits. Claude chose this; it is declared
in the config and the manifest and is reversible if Mher disagrees.

### The cross-vintage decomposition

A single positive constant is estimated on the **pre-surveillance overlap only**,
so the surveillance-window split is out of sample with respect to it. The
revision is then split into what that constant reproduces and the residual it
does not. The scale-invariant detector is invariant to the first component by
construction, so only the residual can move it.

A synthetic test multiplies an entire series by a positive constant and verifies
the scale-invariant detector is unchanged, while the raw-level detector moves.
**Agreement under that test is mathematical behaviour, not evidence about the
vintages.** The empirical claim concerns departures from the proportional case
only.

### What A4 will not support

A4 scores one unit over one event. A fired alarm is not detection performance,
and no confidence statement about the detector follows from it. The false-alarm
rate the threshold was set to is a development-unit property whose transfer to
Hormuz is untestable here — and A3 already showed transfer is uneven, with the
worst development unit at roughly five times its target rate. `severity_rank`
orders cells inside the run only; ranking Hormuz against the development
distribution would need a recalibration A4 must not do. Severity is reported in
each form's own units and is not comparable across forms. Nothing here licenses
a causal reading, and the plan's stop condition stands: no tuning after A4.
