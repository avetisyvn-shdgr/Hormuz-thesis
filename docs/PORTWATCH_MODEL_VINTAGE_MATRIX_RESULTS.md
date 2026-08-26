# PortWatch model × vintage matrix results

**Role:** case-local, sensitivity-only comparison.  
**Frozen design:** `portwatch_two_vintage_four_specification_matrix_v1`.  
**Design SHA-256:**
`297908c214a0afab30a377854585cb1788922334c3bba976f8e2a1141c6ed73e`.  
**Admission protocol SHA-256:**
`bb050aa041e8fc1c8391b908baeab529aaf2e9944d5f35b07af661349176adce`.

## Common comparison

Every cell uses Hormuz PortWatch `n_tanker`, actual transits/day, training from
2022-01-01 through 2026-02-27, and the identical 130-day scoring calendar from
2026-02-28 through 2026-07-07. No selected model receives observed
post-treatment covariates. The vintages are estimated separately and are never
averaged.

The comparison statistic is the mean daily point-or-marginal-median
counterfactual shortfall. BSTS's joint cumulative posterior median remains a
secondary model-native statistic and is not substituted into the cross-model
range.

| Selected specification | Pinned July vintage | August vintage | Same-model vintage shift |
|---|---:|---:|---:|
| Seasonal naive (7-day) | 54.800 | 43.700 | 11.100 |
| AR(1,7) | 52.838 | 43.814 | 9.025 |
| Chronos-2 q0.5 | 50.884 | 42.177 | 8.707 |
| BSTS daily marginal median | 49.625 | 40.167 | 9.458 |

Values are lost transits/day relative to each model's counterfactual. The
observed 130-day sums are 529 in the pinned vintage and 401 in the August
vintage; this is a change in the saved measurement state, not a new economic
event estimate.

## Sensitivity-budget reading

- The selected four-specification range is **5.175 transits/day** in the pinned
  vintage and **3.646/day** in the August vintage.
- Holding the model fixed, the vintage shift is **8.707–11.100/day** across all
  four specifications.
- For the locked AR primary, the vintage shift is **9.025/day**, which is 3.850
  transits/day larger than, or 1.744 times, the pinned selected-model range.
- On the locked absolute statistic, the conclusion survives completion of the
  matrix: within this selected representative set, changing the measurement
  vintage moves the estimated magnitude more than changing among the four
  selected models.

That statement is metric-dependent. Dividing each cell's common shortfall by
its own model counterfactual places all eight cells between **92.4215% and
93.4227%**. The within-vintage selected-model spreads are 0.6662 percentage
points (pinned) and 0.5544 points (August), while same-model vintage changes
are 0.3191–0.5898 points. The defensible joint reading is therefore: absolute
magnitude is vintage-sensitive within the selected matrix, while the
model-relative shortfall shares are numerically clustered. Because their
denominators are cell-specific and the ratios sit near a ceiling, the
normalization is descriptive scale context rather than independent robustness
evidence, a third budget axis, or the raw observed pre/post decline.

The post-treatment-covariate ARX route-energy result remains visible at
62.858/day. Mixing it into the pinned numeric range would produce a
mixed-information range of 13.233/day and reverse the broad comparison. It is
excluded because it conditions on observed post-cutoff route and energy
covariates and answers a different question. The absolute headline is thus
conditional on the ex-post, unblinded same-observed-local-information rule.

This is a descriptive sensitivity budget, not a variance decomposition,
uncertainty interval, pooled estimate, or estimate of model uncertainty in
general. TimesFM and Moirai passed the pre-period gate but have no matched
130-day matrix cells, so this is not an all-admissible-model range.

The frozen downstream table, machine-readable qualifications, defence wording,
and figure are in `PORTWATCH_SENSITIVITY_BUDGET_CARD.md`. That card has its own
manifest and remains `NEEDS-VERIFY`; it does not modify this G4-verified matrix.

## Reconciliation and fixity

- Final daily artifact: `data/processed/model_vintage_matrix_daily.csv`
  (1,040 rows: 8 cells × 130 dates).
- Final summary: `data/processed/model_vintage_matrix_summary.csv` (8 unique
  model–vintage cells).
- Matrix manifest: `data/processed/model_vintage_matrix_manifest.json`.
- Complete optional-branch manifest:
  `data/processed/portwatch_sensitivity_complete_manifest.json` (13 artifact
  hashes). The distinct pre-run prepared manifest remains byte-identical to the
  checkpoint; it is not overwritten after the matrix run.
- Pinned predictions and observations reconcile to the existing seasonal, AR,
  Chronos, and BSTS artifacts within the frozen tolerance. Post-run tests
  independently recompute every summary from the daily rows and reject missing
  cells, wrong units, stale hashes, and date drift.

Chronos ran offline on CPU with Python 3.11.15,
`chronos-forecasting==2.3.0`, model revision
`29ec3766d36d6f73f0696f85560a422f50e8498c`, and the frozen benchmark-lock
hash. The host-specific cache path is not persisted. Core outputs record
Python 3.14.4 and exact implementation hashes, but not separate NumPy/Pandas
version fields; exact pinned-cell reconciliation is the stronger run-specific
cross-check.

## Limits

- These are counterfactual forecast shortfalls, not an ATT or proof that the
  disruption caused every missing observed transit.
- The result is local to one outcome, chokepoint, disruption, scoring window,
  and two non-exchangeable data vintages. It does not establish a general law
  about AIS indicators.
- Changing vintage replaces the saved series used for both pre-treatment
  fitting and post-treatment scoring. The absolute shift cannot be attributed
  only to revised post-treatment observations, and neither vintage is validated
  as closer to physical truth.
- The August raw bytes remain Git-ignored and require a permitted replication
  archive deposit. The derived artifacts and exact source hash are frozen, but
  clone-level sensitivity reproduction is not yet claimed.
- The matrix does not revise the separate placebo p-values, conformal bounds,
  or synthetic-control evidence.
- Mher reran all three matrix phases and pasted the complete 2026-08-10 output:
  9/9 matrix tests, 358/358 full tests, and the 13-artifact manifest passed.
  Phase 4 therefore satisfies G4. The separate August source-byte archive
  deposit remains pending.
