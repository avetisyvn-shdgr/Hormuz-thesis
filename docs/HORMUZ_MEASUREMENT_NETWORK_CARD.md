# Hormuz measurement network card — B1 instrument revision audit

**Phase:** B1 (Track B) of `docs/HORMUZ_TECHNICAL_EXECUTION_PLAN.md` v1.1
**Specification:** `config/hormuz_measurement_audit.yaml` (version 1, frozen)
**Status:** **executed and verified** by Mher, 2026-08-27; config hash
`af3abb7f…4f92`; 11/11 frozen invariants reproduced
**Prepared:** 2026-08-27

This card documents what the B1 audit measures, how it is estimated, and what
may and may not be concluded from it. Results in §12 come from Mher's
authoritative local run; under the plan's verification contract no other
number is a project result.

---

## 1. What this audit is

Two IMF PortWatch captures describe the *same* historical period and disagree.
The disagreement is overwhelmingly concentrated on one chokepoint. B1
characterises that disagreement as a measurement fact and decomposes it into:

- a **proportional component** — a rescaling of the historical series, captured
  by a frozen zero-intercept July→August mapping; and
- a **non-proportional residual** — the date-specific remainder that survives
  that mapping.

The split exists because a purely multiplicative revision **cancels by
construction** under within-series normalisation. Cross-state agreement of a
scale-invariant statistic under such a revision is arithmetic, not evidence.
Only the residual carries information about how the historical measurement
construct changed, and only claims about raw-level behaviour and that residual
are empirically meaningful downstream.

## 2. What this audit is not

It does **not** identify why the provider revised the series. The two captures
show that a unit-specific retrospective revision occurred between two
collections taken while the event was unfolding. They do not establish a
provider-side reason. Treatment-dependent measurement error remains a
hypothesis and a material risk, not a demonstrated mechanism.

Explicitly not authorised by B1:

- that the Hormuz disruption caused the PortWatch revision;
- any causal ATT or structural treatment effect;
- that Hormuz traffic physically stopped;
- that the residual is a measurement-error variance;
- any averaging, blending, or substitution of the two measurement states.

## 3. Measurement states

Both states are admitted through `registry.get_variable()`, are checked against
the Phase 0 freeze hashes, and are **never averaged or substituted**.

| State | Registry variable | Path | SHA-256 |
|---|---|---|---|
| July | `portwatch_chokepoints_snapshot` | `data/raw/portwatch/Daily_Chokepoints_Data.csv` | `66f3a54a…f579d` |
| August | `portwatch_chokepoints_vintage_20260809_snapshot` | `data/raw/portwatch/vintages/Daily_Chokepoints_Data__vintage_2026-08-09.csv` | `0bc806a4…85bcb` |

### Registry sensitivity gate

The August vintage is registered `analysis_scope: sensitivity_only` with a
closed `allowed_consumers` list and a `promotion_policy` forbidding it from
replacing the pinned primary without a new recorded decision. B1 opts in as a
**declared sensitivity consumer**: it reads the vintage as the second
measurement state of a revision audit. It does not promote the vintage, does
not substitute it for the pinned primary, and does not average the two, so it
does not engage the promotion policy. The opt-in is declared in the frozen
audit spec (`states.august.allow_sensitivity`, `consumer`), not hard-coded in
the script, and is recorded in the manifest under `inputs.sensitivity_opt_in`
and `assertions.august_vintage_not_promoted_to_primary`.

Admitting the audit script to that allowlist is a data-access governance
decision recorded in `config/sources.yaml`, which Track B does not edit.

Separation is enforced in code, not by convention:

- `assert_states_separate` refuses equal hashes, a shared path, or a shared label;
- `assert_not_averaged` refuses any output column equal to the elementwise
  July/August mean;
- the two states are inner-joined on `(portname, date)` into side-by-side
  `july` / `august` columns and are never stacked into one value column;
- the overlap window and unit count are checked against the frozen config.

Analysis is restricted to the date range both states cover. The August state
extends further; those extra dates have no July counterpart and are excluded
from every comparison.

## 4. Coverage

- Unit: chokepoint-day. 28 chokepoints.
- Measures audited: seven vessel-class counts (`n_tanker`, `n_container`,
  `n_dry_bulk`, `n_general_cargo`, `n_roro`, `n_cargo`, `n_total`) and the seven
  matching capacity columns, including `capacity_tanker` and `capacity`.
- Primary measure: `n_tanker`. Focus unit: `Strait of Hormuz`.
- Locked operational onset: `2026-02-28` — used **only** to partition residual
  reporting into pre-onset and post-onset. It never selects an estimation
  sample.

## 5. Estimators (frozen before fitting)

Three least-squares mapping forms, July → August:

| Form | Model |
|---|---|
| `proportional` | `august = scale · july` (zero intercept) |
| `affine` | `august = intercept + scale · july` |
| `additive` | `august = july + intercept` (unit scale) |

Four declarations, with roles fixed in the config before any fit was inspected:

| Name | Form | Sample | Role |
|---|---|---|---|
| `proportional_2019_2025` | proportional | 2019-01-01 → 2025-12-31 | **default reporting basis** |
| `affine_2019_2025` | affine | 2019-01-01 → 2025-12-31 | declared sensitivity |
| `proportional_2019_2026_02_27` | proportional | 2019-01-01 → 2026-02-27 | declared sensitivity |
| `additive_2019_2025` | additive | 2019-01-01 → 2025-12-31 | declared sensitivity |

**Anti-shopping rule.** The default is the mapping named by the plan. Every
other declaration is a sensitivity that is reported whatever it shows. Samples
are selected by configured dates only, never by residual behaviour. Changing
the default after seeing residuals invalidates the run and requires a new
config version. Residuals are always evaluated on the **full overlap**, not
only on the estimation sample, so post-onset behaviour cannot be hidden by the
sample choice.

### Decomposition

For the frozen mapping `m`:

```
raw revision      r_t = august_t − july_t
residual          e_t = august_t − m(july_t)
fraction remaining     = Σ e_t² / Σ r_t²
absorbed by rescaling  = 1 − fraction remaining
```

"Absorbed by rescaling" is the share of squared revision error consistent with
a pure proportional change under this one frozen estimator. It is a descriptive
decomposition, not a variance model.

## 6. WTO measurement-state audit

Reports the WTO Hormuz index file count, retrieval horizons, and distinct
historical value regimes.

- Retrieval horizons come from `data/raw/provenance.jsonl`: `retrieved_utc`
  and the recorded `query.start` / `query.end` per file, alongside each file's
  actual data coverage.
- **Regime rule:** two files share a regime only if their values agree exactly
  on every date in their overlap. Because overlap windows differ between files,
  this relation is **not transitive**, so grouping uses a strict clique in
  deterministic filename order — a file joins a regime only if it agrees with
  every existing member. Nothing is merged through a chain of pairwise
  agreements, and the complete pairwise comparison matrix (including files that
  differ on a single date) is written to the manifest.
- Column aliases handle the normalised snapshots (`date`, `value`) and the
  preserved original source payload (`voy_load_date`, `voy_intake_index`).

## 7. Outputs

| Path | Contents |
|---|---|
| `data/processed/portwatch_instrument_shift_by_chokepoint.csv` | one row per (measure, chokepoint): overlap days, changed rows, percent changed, both state means, ratio, difference |
| `data/processed/portwatch_hormuz_revision_daily.csv` | one row per overlapping Hormuz day: both states, raw revision, ratio, changed flag, one residual column per declared mapping, default residual, pre/post-onset period, year, month |
| `data/processed/portwatch_hormuz_revision_annual.csv` | one row per year: days, changed rows, percent changed, share of all revisions, both state means, August/July ratio, partial-year flag |
| `data/processed/wto_measurement_state_audit.csv` | one row per WTO file: hash, rows, data horizon, provenance retrieval horizons, artifact role, regime id, pairwise conflicts |
| `data/processed/hormuz_measurement_state_manifest.json` | manifest (below) |

### Manifest contract

Records script and command, UTC run time, git commit/branch/dirty status,
input paths and hashes, config path/hash/version, both measurement states and
the separation record, analysis window, measures audited, **estimator and
sample definitions with fitted coefficients**, the revision decomposition for
every declared mapping, pre-onset/post-onset/full residual distributions,
changed-row summary, annual ratios, the monthly temporal distribution, the WTO
regime audit with its pairwise matrix, the invariant verification table,
sealing assertions, environment versions, limitations, and the explicit list of
claims not authorised. Output paths carry their own SHA-256.

## 8. Invariant verification

The plan records known values that must reproduce from the frozen inputs and
must never be hard-coded. The config holds them as **verification targets
only**; every reported number is computed from the raw states at run time and
then compared. Enforcement is unconditional — there is no flag that disables
it, and a mismatch raises `InvariantMismatch` and stops the phase.

Checked: Hormuz changed-row percentage for `n_tanker`; the next-highest
chokepoint's percentage *and its identity*; the median across all 28
chokepoints; and the August/July annual Hormuz ratios for 2019–2025. The 2026
ratio is reported but is **not** an invariant target — both states cover 2026
only partially, and the two states' 2026 coverage differs.

## 9. Limitations

- Two captures of one period. The provider-side reason is unobserved and is
  not claimed.
- The proportional/non-proportional split is relative to one frozen estimator,
  not a measurement-error model.
- A purely multiplicative revision cancels under within-series normalisation;
  agreement after normalisation is arithmetic, not robustness.
- The post-onset overlap is short relative to the pre-onset period. Post-onset
  residual statistics are thin and are **not** a treatment signal. Any
  concentration or absence of residual revision after the onset is descriptive.
- **The pre-onset/post-onset residual comparison is not interpretable as
  specified.** The underlying July level falls from 54.10 to 4.05 transits/day
  across the split — a factor of 13 — and the direction of the comparison flips
  with the choice of normalisation (see §12.3). The frozen spec reports
  absolute RMSE, which is what it declared; that number is correct and stands,
  but it does not support a directional claim about whether the
  non-proportional revision is larger or smaller after the onset. Any future
  scale-relative diagnostic must be pre-declared, and because all three
  normalisations have now been seen, such an addition would be **exploratory,
  not confirmatory** — the honest options are to report all of them or none,
  never to select one.
- WTO regime grouping uses exact equality over unequal overlap windows; the
  clique rule is a reporting convention, and the pairwise matrix is the
  primary evidence.
- Capacity columns carry the provider's own imputation behaviour, which this
  audit describes but does not correct.

## 10. Reproduction

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest \
  tests/test_instrument_shift.py \
  -q -p no:cacheprovider
```

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python \
  scripts/run_hormuz_measurement_audit.py --check
```

`--check` prints the invariant verification table; enforcement is always on.
`--dry-run` performs every computation and check but writes no files.

After acceptance, record:

```bash
shasum -a 256 config/hormuz_measurement_audit.yaml
git rev-parse HEAD
```

## 11. Downstream use

Track A consumes the accepted manifest **read-only**. B1 authorises no
detector, model, threshold, or receiver decision. It supplies the measurement
description that makes the cross-state detector comparison in A4 interpretable
— specifically, the separation of the component that cancels by construction
from the residual that does not.

---

## 12. Verified results (Mher's run, 2026-08-27)

Config `af3abb7f…4f92`; branch `ml/hormuz-revision-robust`; HEAD `73ae8989`.
Overlap 2019-01-01 → 2026-07-12, 2,750 days × 28 chokepoints. All 11 frozen
invariants reproduced from the raw states.

### 12.1 The revision is a whole-history rewrite, not an event-window edit

Hormuz `n_tanker` differs on 2,680 of 2,750 overlapping days (97.4545%). The
next-highest chokepoint is Malacca Strait at 0.1091%; the median across all 28
units is 0.0364%. The revision is concentrated on one unit by roughly three
orders of magnitude.

Within Hormuz it is spread across the entire history, not near the event:

| Year | Days | Changed | % | August/July ratio |
|---|---|---|---|---|
| 2019 | 365 | 364 | 99.73 | 0.842825 |
| 2020 | 366 | 365 | 99.73 | 0.848370 |
| 2021 | 365 | 364 | 99.73 | 0.842049 |
| 2022 | 365 | 364 | 99.73 | 0.827109 |
| 2023 | 365 | 365 | 100.00 | 0.825321 |
| 2024 | 366 | 363 | 99.18 | 0.817771 |
| 2025 | 365 | 365 | 100.00 | 0.826064 |
| 2026 (partial) | 193 | 130 | 67.36 | 0.786714 |

Every complete year back to 2019 was revised on ≥99.18% of days.

### 12.2 It affects every vessel class, not only tankers

Changed-row percentages for Hormuz span `n_total` 99.45%, `capacity` 98.95%,
`n_cargo` 98.40%, `n_tanker` 97.45%, `capacity_tanker` 93.38%, down to
`n_roro` 24.55% and `capacity_roro` 12.51%. August/July mean ratios cluster in
0.79–0.87 across all fourteen measures.

The low changed-row percentages on `roro` and `general_cargo` are most likely a
**discreteness artifact rather than evidence those classes were spared**: those
series average 2.2 and 4.0 units/day, and at such levels a rescaling near 0.87
maps most small integers back onto themselves. Read the ratio column, not the
changed-row column, for those classes.

### 12.3 Proportional versus non-proportional decomposition

Frozen default `proportional_2019_2025`, n = 2,557: **scale = 0.831917**,
intercept 0 by construction. Evaluated on the full overlap:

- raw revision RMSE **9.756**
- RMSE after the mapping **3.194**
- squared revision error remaining **10.72%**
- absorbed by proportional rescaling **89.28%**

The declared sensitivities confirm the default is not a fragile choice: the
affine mapping puts the intercept at 0.150 transits/day against a July mean of
51.6 (slope 0.829330), and extending the sample through 2026-02-27 moves the
scale only from 0.831917 to 0.831297. The additive comparator fits a flat
−9.124/day shift.

**The pre/post residual split does not support a directional claim.** The three
defensible normalisations disagree:

| Normalisation | Pre-onset | Post-onset | Direction |
|---|---|---|---|
| absolute RMSE | 3.2652 | 1.1478 | post smaller |
| RMSE ÷ level | 0.0604 | 0.2833 | post ~4.7× larger |
| RMSE ÷ discreteness floor | 11.39 | 4.50 | post ~2.5× smaller |

July level falls from 54.10 to 4.05 transits/day across the split, so absolute
and scale-relative statistics cannot both be read as comparable. Post-onset,
62 of 135 days are unrevised and 55.6% of days sit exactly at
`round(0.831917 × July)`. The frozen absolute-RMSE figures stand as reported;
the comparison is simply uninformative about direction. See §9.

### 12.4 The WTO index also moved

Six files, **three distinct historical value regimes** under the strict clique
rule. One regime pair differs on 365 dates; a third file differs from its
nearest regime on exactly **one** date and was correctly held separate rather
than merged through a chain of pairwise agreements. PortWatch is therefore not
the only instrument in this project that was retrospectively revised.

### 12.5 What this does not establish

None of the above identifies **why** either provider revised. The audit
establishes a unit-specific retrospective revision between two captures. The
provider-side reason is unobserved, and the claim boundaries in §2 stand
unchanged.
