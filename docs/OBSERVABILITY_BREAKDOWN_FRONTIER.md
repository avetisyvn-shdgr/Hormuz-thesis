# Observability breakdown frontier

**Layer id:** `hormuz_observability_counterfactual_breakdown_frontier_v1`
**Status:** implemented and reproduced 2026-08-10. Mher ran both outcomes, the legacy
AIS-dark cross-check passed on 4 shared cells, and 25/25 focused plus 578/578 full tests
passed. The task-10 audit was regenerated and re-frozen afterwards and verifies clean.
**Scope class:** partial-identification sensitivity map. Not a new data source, not a new
estimand, not a causal correction.

This layer joins two robustness statements the thesis already makes separately and reports
where the headline claim breaks down when both are varied at once. It consumes only
committed pipeline artifacts. It adds no registry variable, requests no new access, and
does not touch the locked cutoff, the primary specification, or any frozen manifest.

## Why this layer and not SAR or a foundation-model contagion layer

Two extensions were proposed externally: Sentinel-1 SAR dark-fleet detection, and a
Moirai-MoE cross-commodity contagion model. Both were already adjudicated in
`data/processed/public_data_gate_decisions.csv` (task 9 of the integration-hardening
order, G4-verified):

- `sentinel1_sar` is `DEFER_POST_SUBMISSION`. Its recorded kill criteria include *any
  conversion of scene occupancy into a daily throughput estimate* and *any use before
  thesis submission*. A "dark fleet premium" multiplier is the first of those verbatim.
  The gate also records that `yang2026sar` already observes this event with Sentinel-1, so
  the novelty claim is unavailable.
- A cross-commodity forecasting layer would run a multivariate forecaster across
  outcomes jointly driven by weather, storage, demand, pipeline supply, generation
  availability, and policy. Forecast accuracy over such outcomes is not identification,
  which the project treats as a non-negotiable (`CLAUDE.md`, rule 2).

The binding constraint on the headline claim was never observation volume. It was that
the two acknowledged sources of slack — treatment-correlated measurement error and
counterfactual sampling uncertainty — had only ever been reported one at a time. This
layer closes that gap with arithmetic on artifacts already in hand.

## The identity

| Symbol | Meaning |
|---|---|
| `O` | observed post-period total (PortWatch) |
| `C` | counterfactual post-period total, on the observed/AIS-measured scale |
| `d` | **incremental** post-period dark rate: share of true post transits PortWatch misses, over and above the baseline non-detection already embedded in `C`'s scale |
| `s` | post-period false-positive rate: share of observed transits that are not distinct true transits (spoofing, loitering re-crossings, duplicate identities) |
| `R̄` | claim threshold — "the true reduction was at least `R̄`" |

```
T(d, s)     = O (1 - s) / (1 - d)                implied true post transits
R_true      = 1 - T(d, s) / C
d*(R̄, s, C) = 1 - O (1 - s) / (C (1 - R̄))        breakdown dark rate
T at d*     = C (1 - R̄)                          independent of s
```

`C` is a forecast fitted on observed pre-treatment PortWatch counts, so it predicts what
PortWatch *would have recorded*, not physical truth. Only the treatment-correlated
increment is unaccounted for; that is why `d` is defined as incremental and why the
pre-period baseline dark rate does not enter separately.

## Sign structure

`d` lowers the true reduction; `s` raises it. `assert_false_positive_direction` enforces
this on the emitted grid rather than assuming it. The consequence is reportable: the
one-sided undercount assumption in `scripts/run_ais_dark_bound.py` is the **conservative**
case, and the only claim-breaking directions are a large `d` and a counterfactual at the
low end of its interval. Both are mapped jointly here.

## Admissible counterfactuals

Interval endpoints are carried on the counterfactual scale as `O + loss`. Unbounded
conformal endpoints are **dropped with a recorded note, never clipped** — clipping an
infinite endpoint would manufacture a bound the inference does not support.

| Scenario | Family | Nominal coverage | Source artifact |
|---|---|---|---|
| `point_estimate` | point | n/a | `counterfactual_post_treatment_summary.csv` |
| `bootstrap_block_lower` / `_upper` | block-bootstrap residual | 0.95 | `counterfactual_intervals_summary.csv` |
| `conformal_0.80_lower` / `_upper` | split-conformal block rank | 0.80 | `block_conformal_summary.csv` |
| conformal at 0.90 / 0.95 | — | — | unbounded; dropped with a note |

The conformal family is materially wider than the bootstrap family and carries different
coverage semantics, so the two are reported as separate scenarios rather than pooled.

## Outputs

A single invocation runs **both** the primary outcome (`hormuz_tanker_transits`) and the
robustness outcome (`hormuz_tanker_capacity`) and stacks them, so the twin can never
overwrite the primary artifacts and the two are always reported from identical inputs.
Every row carries a `unit` column looked up from a strict registry; an unregistered
outcome raises rather than shipping an unlabelled column, because a column named
"transits" carrying deadweight tonnes would be a reporting defect.

| Artifact | Content |
|---|---|
| `data/processed/observability_breakdown_frontier.csv` | one row per (outcome × scenario × claim threshold): `d*`, status, implied invisible total, per-day rate, share of pre-treatment daily mean |
| `data/processed/observability_breakdown_grid.csv` | full `(d, s, C)` cross-product of implied true reductions |
| `data/processed/observability_claim_calibration.csv` | strongest claim surviving each conceded dark rate |
| `data/processed/observability_breakdown_summary.json` | per-outcome blocks with binding rows, scenario ledger, dropped-endpoint notes and cross-check status, plus SHA-256 of every input and the guard text |

`implied_unobserved_share_of_pretreatment_daily_mean` is the column that makes the
frontier judgeable without a proprietary dark-fleet anchor: it converts an abstract rate
into invisible vessels per day, expressed against normal trailing-year pre-treatment
traffic. The reader weighs a vessel count, not a parameter.

## Cross-check against the existing bound

`assert_point_scenario_matches_legacy_bound` requires the `point_estimate` rows to
reproduce `ais_dark_bound_critical_rates.csv` exactly at the shared corner (`s = 0`,
`C` at the point estimate), on the legacy artifact's clipped `[0, 1]` scale. The guard
also refuses an empty join, so a silently non-overlapping merge cannot pass as agreement.
This layer generalises the existing bound; it must not silently disagree with it.

The legacy artifact exists for the primary outcome only. The robustness-outcome run
therefore has no shared cell, and `legacy_bound_cross_check` records
`SKIPPED: …` in the JSON and in the console output rather than silently omitting the
check. A run without the cross-check is visibly a weaker run.

## Reporting rules

1. Report the **binding** breakdown rate — the smallest across admissible scenarios — not
   the point-estimate rate. The point-estimate rate alone overstates the margin, and
   `interval_robustness_discount` quantifies by how much.
2. `tolerated_dark_rate` in the calibration table is an **author assumption**, not an
   estimate produced here. Any use in the manuscript must state where the conceded rate
   comes from and cite it.
3. Never describe any figure in these artifacts as a measured dark rate, a dark-fleet
   premium, or a corrected throughput estimate.
4. The frontier constrains claim *strength*. It does not license a new point estimate and
   does not replace the counterfactual shortfall as the reported estimand.

## Verification

```bash
.venv/bin/python scripts/run_observability_breakdown_frontier.py && .venv/bin/python -m pytest tests/test_observability_frontier.py -q
```

Full suite:

```bash
.venv/bin/python -m pytest -q
```

Registered in `scripts/run_all.py` after `run_interval_calibration.py`, since it depends
on the counterfactual, both interval families, and the legacy bound it cross-checks.

### Known consequence for the task-10 audit

`docs/*.md` is inside the audit's `scanned_globs`, so adding or editing this document
shifts the line numbers the frozen scan records and correctly invalidates it — exactly the
`run_last_after_all_documentation_edits` rule in `config/final_integration_audit.yaml`.
Until the phase is regenerated,
`tests/test_final_integration_audit.py::test_manifest_matches_its_live_rebuild` fails.

The freezer validates already-written outputs against a live rebuild, so it cannot be run
alone. The builder must regenerate the scan, ledger, diagnostics and both markdown
documents first:

```bash
.venv/bin/python scripts/run_final_integration_audit.py && .venv/bin/python scripts/freeze_final_integration_audit.py && .venv/bin/python scripts/freeze_final_integration_audit.py --verify
```

Re-run that sequence after **any** later edit to this document. This is a by-design
invalidation, not a defect in this layer.

## Relationship to the frozen record

This layer is additive and does not reopen any gate. It does not modify
`public_data_gate_decisions.csv`, the model-admission protocol, the vintage matrix, the
horizon/resolution frontier, the network-support frontier, or the route-burden
decomposition. Under stop rule 5 of
`INTEGRATION_HARDENING_EXECUTION_ORDER_2026-08-09.md`, it must not displace writing; it is
sized as a claim-calibration input to the results and defence chapters, not as a new
empirical branch.
