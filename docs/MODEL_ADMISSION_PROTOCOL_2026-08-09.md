# Model-admission lock for the PortWatch vintage matrix

**Locked locally:** 2026-08-09T21:18:46Z.  
**Protocol SHA-256:**
`bb050aa041e8fc1c8391b908baeab529aaf2e9944d5f35b07af661349176adce`.  
**Status:** Ex post, unblinded governance lock; anchored in commit `ca925a8`.
Mher completed the pre-run G4 verification on 2026-08-09. The subsequently
generated matrix has a separate post-run verification gate.

## What this lock does—and does not do

The lock fixes the comparison rule before a persisted eight-cell matrix and
before the August Chronos cell is run. It is not a preregistration and does not
show that the roster was selected without seeing results.

At lock time, all pinned-vintage results, the August outcome path, all six rows
of the existing AR vintage/window table, and the pre-treatment TSFM validation
results were already known. During the independent review of the earlier,
unanchored v1 draft, approximate August seasonal-naive and BSTS values were also
seen in memory. They are disclosed in the protocol; the four-model roster was
not changed afterward.

## Frozen comparison contract

The selected range holds fixed:

1. PortWatch Strait of Hormuz `n_tanker` as the outcome.
2. Actual transits per day as the unit.
3. Training from 2022-01-01 through 2026-02-27.
4. The locked 2026-02-28 cutoff.
5. The same 130 scored dates through 2026-07-07.
6. No observed post-cutoff covariates or donor outcomes.
7. Separate estimates for each measurement vintage—never a vintage average.

The selected four-specification comparison set is seasonal naive, AR(1,7),
Chronos-2, and BSTS. This is a deliberately selected representative set, not
the range of every model that passed a pre-period gate.

| Model | Pre-period gate | Frozen 130-day pinned cell | Selected set | Disposition |
|---|---:|---:|---:|---|
| Seasonal naive (7-day) | Yes | Yes | **Yes** | Transparent predeclared benchmark |
| AR(1,7) | Yes | Yes | **Yes** | Locked primary |
| Chronos-2 | Yes | Yes | **Yes** | Historically implemented TSFM representative |
| BSTS local level + weekly | Yes | Yes | **Yes** | Existing outcome-only state-space cross-check |
| TimesFM 2.5 | Yes | **No** | No | Additional admitted TSFM; common-window range not run |
| Moirai 2.0 | Yes | **No** | No | Additional admitted TSFM; common-window range not run |
| ARX route / route+energy | Yes | Yes | No | Same units, but observed post-cutoff covariates |
| Synthetic control | Different role | Yes | No | Post donors and mean-scaled transit-equivalent units |
| Seasonal stub | No | No | No | Test fixture |

Therefore:

- The **selected four-specification same-information range** will be reported.
- An all-preperiod-admitted range is **not estimated**, because matching
  TimesFM and Moirai cells do not exist.
- No range is computed across the ARX rows because their information sets
  differ.
- Synthetic control is never put into a numeric range with direct transit
  forecasts because its units are mean-scaled transit equivalents.

## Why Chronos is the representative

Chronos was the documented first engineering candidate and the default
robustness implementation before its post-period output was committed
(`41c3c92` precedes `f15f0e9`). The justification is not that it won every point
metric. On the matched pre-period transit folds, TimesFM had lower MASE
(0.781724 versus 0.800037), while Chronos had the smallest absolute coverage
error (0.012319 versus 0.047826 for Moirai and 0.053623 for TimesFM), supports
the requested native 95% interval, and is already part of `run_all.py`.

## Harmonized statistic

The cross-model statistic is:

`mean(daily point-or-marginal-median prediction − observed)`

over the same 130 days. BSTS therefore uses the sum of daily marginal posterior
medians divided by 130 for the comparison range, while the median of the joint
cumulative posterior shortfall remains a model-native secondary value.

For the already-saved pinned outputs:

- Harmonized four-model range: **5.175 transits/day**.
- Earlier native-summary range: **5.278 transits/day**.
- BSTS harmonized daily statistic: **49.625/day**.
- BSTS joint-native statistic: **49.522/day**.

These are sensitivity ranges, not uncertainty intervals, pooled estimates, or
variance decompositions.

## Machine verification

`scripts/build_model_admission_protocol.py` runs no forecast. It verifies 14
known artifact rows against exact source hashes, required filters, formulas,
units, and support. Every direct daily comparison must contain exactly 130
unique consecutive dates from February 28 through July 7, finite observations
and forecasts, observed sum 529, and the identical observed-vector hash.

The generated tables are:

- `data/processed/model_admission_protocol.csv`
- `data/processed/model_admission_known_results.csv`

Mher ran the builder and focused checks and pasted 43/43 passing tests before
the matrix began. The matrix was then generated under the anchored design;
those new outputs remain `NEEDS-VERIFY` until Mher runs the post-matrix command
block. The immutable pre-run checkpoint retains its historical `pending_g4`
field because it records the state before that human verification.
