# Horizon/resolution inference frontier

**Design id:** `hormuz_horizon_resolution_inference_frontier_v1`  
**Design SHA-256:** `8c286420a882e0ddd6be80ddf7d443f997fed0e235fddac8baf55e075a08bd45`  
**Frozen (UTC):** 2026-08-09T22:45:56Z  
**Freeze status:** frozen_before_generation_not_preregistered  
**Verification status:** `NEEDS-VERIFY` until the complete pipeline is run.

This document audits and extends the block/placebo inference design. It reports what the pre-treatment calendar can support. It is not a significance test and it does not identify a causal effect.

## What is held fixed

| Element | Value |
|---|---|
| Outcome | `hormuz_tanker_transits` |
| Unit | transits_per_day |
| Model | `ar_lag1_7`, lags [1, 7], no exog |
| Training scheme | expanding_from_panel_start |
| Training cutoff (exclusive) | 2026-02-28 |
| Treated window | 2026-02-28 to 2026-07-07 (130 days) |
| Minimum initial training | 365 days |

Only the reference partition and its resolution vary. A horizon shorter than the treated window scores a strictly nested sub-window that still starts on the locked operational-onset date; no cell moves the treatment date, the model, or the units.

## Origin rules, frozen before generation

| Rule | Role | Definition |
|---|---|---|
| `forward_anchored_direct` | primary | Anchor the first reference block at panel_start + min_initial_train_days, then tile forward in steps of exactly one horizon. A block is admitted only if it ends strictly before the training cutoff. |
| `backward_anchored_from_cutoff` | sensitivity | Anchor the last reference block to end on the day before the training cutoff, then tile backward in steps of exactly one horizon while the remaining training span stays at or above min_initial_train_days. |
| `legacy_greedy_step30` | audit_reproduction | Reproduce the locked primary construction: enumerate candidate origins on a 30-calendar-day step from the anchor, then greedily retain disjoint windows in chronological order. |

Each rule is a pure function of the calendar index, the locked cutoff, and the minimum training length. None of them can read the outcome, so no rule in this grid was or can be selected for a favourable result.

## Complete enumeration versus greedy subsampling

The locked primary artifact coarsens candidate origins to a 30-day lattice and then greedily retains disjoint windows. This phase instead enumerates every feasible daily origin and reports the maximum-cardinality disjoint packing, which for equal-length blocks on a contiguous daily calendar is exactly `floor(available_reference_days / horizon)`.

| Horizon (days) | Feasible candidate blocks | Packing bound | `forward_anchored_direct` | `backward_anchored_from_cutoff` | `legacy_greedy_step30` |
|---:|---:|---:|---:|---:|---:|
| 30 | 1125 | 38 | 38 | 38 | 38 |
| 65 | 1090 | 17 | 17 | 17 | 13 |
| 91 | 1064 | 12 | 12 | 12 | 9 |
| 130 | 1025 | 8 | 8 | 8 | 7 |

## Finite-sample inference frontier

With `K` disjoint reference blocks the smallest attainable rank p-value is `1/(K+1)`, the largest coverage a split-conformal interval can support is `K/(K+1)`, and a requested level is necessarily unbounded whenever `ceil((K+1) * level) > K`.

| Horizon | Rule | K | p-floor `1/(K+1)` | Observed rank p | Max coverage | Finite levels | Unbounded levels |
|---:|---|---:|---:|---:|---:|---|---|
| 30 | `backward_anchored_from_cutoff` | 38 | 0.0256 | 0.0256 | 0.9744 | 80%, 90%, 95% | none |
| 65 | `backward_anchored_from_cutoff` | 17 | 0.0556 | 0.0556 | 0.9444 | 80%, 90% | 95% |
| 91 | `backward_anchored_from_cutoff` | 12 | 0.0769 | 0.0769 | 0.9231 | 80%, 90% | 95% |
| 130 | `backward_anchored_from_cutoff` | 8 | 0.1111 | 0.1111 | 0.8889 | 80% | 90%, 95% |
| 30 | `forward_anchored_direct` | 38 | 0.0256 | 0.0256 | 0.9744 | 80%, 90%, 95% | none |
| 65 | `forward_anchored_direct` | 17 | 0.0556 | 0.0556 | 0.9444 | 80%, 90% | 95% |
| 91 | `forward_anchored_direct` | 12 | 0.0769 | 0.0769 | 0.9231 | 80%, 90% | 95% |
| 130 | `forward_anchored_direct` | 8 | 0.1111 | 0.1111 | 0.8889 | 80% | 90%, 95% |
| 30 | `legacy_greedy_step30` | 38 | 0.0256 | 0.0256 | 0.9744 | 80%, 90%, 95% | none |
| 65 | `legacy_greedy_step30` | 13 | 0.0714 | 0.0714 | 0.9286 | 80%, 90% | 95% |
| 91 | `legacy_greedy_step30` | 9 | 0.1000 | 0.1000 | 0.9000 | 80%, 90% | 95% |
| 130 | `legacy_greedy_step30` | 7 | 0.1250 | 0.1250 | 0.8750 | 80% | 90%, 95% |

In every cell of the grid the observed rank p-value sits exactly at its floor: the treated statistic exceeds every pre-treatment reference block under every origin rule and every resolution. The rank position is therefore maximal throughout, and what varies across the grid is only how small a number that maximal position is permitted to be. Both facts are design properties and neither is a significance statement.

## Primary cell: `forward_anchored_direct` at 130 days

| Level | Order statistic rank | Finite? | Radius | Interval |
|---:|---:|---|---:|---|
| 80% | 8 | yes | 2,095.043 | [4,773.953, 8,964.039] |
| 90% | 9 | no | unbounded | unbounded |
| 95% | 9 | no | unbounded | unbounded |

The treated statistic is a cumulative shortfall of 6,868.996 transits (52.838 per day) over 130 days. The rank p-value is 0.1111 against a floor of 0.1111.

- A 90% band needs at least 9 disjoint blocks; 1 more than this calendar supports at a 130-day resolution. It is reported as unbounded, not clipped.
- A 95% band needs at least 19 disjoint blocks; 11 more than this calendar supports at a 130-day resolution. It is reported as unbounded, not clipped.

## Audit expectation

Expectation under `forward_anchored_direct` at 130 days: reproduced.

| Check | Expected | Observed | Reproduced |
|---|---|---|---|
| n_reference_blocks | `8` | `8` | yes |
| rank_p_value_floor | `0.1111111111111111` | `0.1111111111111111` | yes |
| finite_interval_levels | `[0.8]` | `[0.8]` | yes |
| unbounded_interval_levels | `[0.9, 0.95]` | `[0.9, 0.95]` | yes |
| finite_radius_is_finite | `True` | `True` | yes |

Direct one-horizon tiling from the locked anchor attains the calendar packing bound; the locked primary artifact reports fewer blocks because its candidate origins are coarsened to a 30-day lattice before the greedy disjoint pass.

## The resolution trap, stated explicitly

At the primary resolution the p-value floor is 0.1111, so **no 5% claim is arithmetically available there whatever the data show**.

Finer resolutions in this grid do push the floor below 0.05 (horizons: 30 days). That is reported here for completeness and is **not** used as evidence, for three reasons.

1. The floor `1/(K+1)` falls purely because a shorter block length packs more blocks into the same fixed pre-period. No new observation is added.
2. At a shorter horizon each reference block, and the treated statistic itself, measures a shorter accumulation. The quantity being tested changes with the resolution.
3. Shorter blocks sit closer together in a serially dependent daily series, so treating them as independent calibration units is weaker than at the primary resolution.

The reporting resolution is fixed at 130 days by the frozen design, before any of these numbers existed. It is not swapped for whichever horizon produced the smallest floor, and this document makes no 5% significance claim at any resolution.

## Interpretation limits

- A lower floor at a finer resolution is a partition property, not additional evidence. Reading the finest resolution as the strongest result would be a resolution artifact.
- Reference blocks are pre-treatment windows for the same series, not untreated units. This is a rank position among earlier forecast errors, not an average treatment effect.
- Unbounded intervals are a property of the available pre-period length at a given resolution. They are reported as unbounded because clipping the order statistic would deliver less coverage than the label claims.
- The locked primary block artifacts are read-only inputs to this phase. They are hash-verified and never rewritten.

