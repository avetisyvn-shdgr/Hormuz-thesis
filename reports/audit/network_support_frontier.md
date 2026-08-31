# Selective network-support frontier

**Design id:** `lng_selective_network_support_frontier_v1`  
**Design SHA-256:** `dcf757f3d944f92a86fb208bc1d4a1699aa5de628f66a81682e3ac19fa4cc184`  
**Frozen (UTC):** 2026-08-09T23:32:47Z  
**Freeze status:** frozen_before_generation_not_preregistered  
**Verification status:** `NEEDS-VERIFY` until the complete pipeline is run.

This document measures **modeled resolved terminal-sequence support**: how many liquefaction-to-regasification sequences remain resolvable in the panel before and after the disruption, overall and for Hormuz-crossing sequences. It is a denominator audit, not a voyage count, not cargo, and not a causal estimate.

## What a missing edge means

A sequence leaves this panel when AIS coverage lapses, when neither endpoint can be attributed to a terminal within the chosen radius, or when no route can be resolved. Each of those failure modes is plausibly **more** likely during a disruption.

So a fall in modeled Hormuz-crossing support is evidence that the panel stopped observing those sequences. It is **not** evidence that no ship sailed, and no AIS-dark physical throughput may be inferred from it. Loss of support and loss of sailing are different propositions, and only the first is measurable here.

## Frozen definitions

| Cohort | Definition | Role |
|---|---|---|
| `all_resolved` | endpoint_status == resolved_liquefaction_to_regasification | overall_denominator |
| `hormuz_crossing` | resolved AND origin project in gulf_export_project_ids AND 'ormuz' in modeled route_passages | selective_denominator |
| `inside_hormuz_non_crossing` | resolved AND origin project in gulf_export_project_ids AND route does not transit Hormuz | diagnostic_contrast |
| `non_gulf` | resolved AND origin project not in gulf_export_project_ids | diagnostic_contrast |

Radii 10, 20, 30 km are frozen, with 30 km primary. Every selective count below is reported beside its overall denominator for the same radius and period.

## Primary radius (30 km)

| Cohort | Pre sequences | Post sequences | Change | Retention | Pre IMOs | Post IMOs | Pre dest. countries | Post dest. countries |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `all_resolved` | 971 | 746 | -225 | 76.8% | 476 | 404 | 37 | 37 |
| `hormuz_crossing` | 145 | 2 | -143 | 1.4% | 64 | 2 | 13 | 2 |
| `inside_hormuz_non_crossing` | 3 | 3 | +0 | 100.0% | 3 | 1 | 1 | 1 |
| `non_gulf` | 823 | 741 | -82 | 90.0% | 423 | 401 | 36 | 35 |

The panel as a whole retains 76.8% of its resolved sequences (971 to 746), while the Hormuz-crossing cohort retains 1.4% (145 to 2). The ratio of the two retention shares is 0.0180.

That is the selectivity result: general support largely persists while Hormuz-crossing support very nearly disappears from the panel. Both numbers describe observability.

## Radius sensitivity

| Radius (km) | All resolved pre | post | retention | Hormuz-crossing pre | post | retention | Retention ratio |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 10 | 567 | 396 | 69.8% | 116 | 1 | 0.9% | 0.0123 |
| 20 | 920 | 685 | 74.5% | 144 | 1 | 0.7% | 0.0093 |
| 30 | 971 | 746 | 76.8% | 145 | 2 | 1.4% | 0.0180 |

The direction is consistent at every frozen radius: the Hormuz-crossing cohort loses a larger share of its modeled support than the panel as a whole. Radius choice changes the level of both denominators, not the sign of the contrast.

## Both-period balanced cohort

Restricting to IMOs with at least one resolved sequence in both periods holds the observed carrier set fixed, so a support change cannot come purely from carriers entering or leaving the panel.

| Radius (km) | Cohort | Pre | Post | Retention | Pre IMOs | Post IMOs |
|---:|---|---:|---:|---:|---:|---:|
| 10 | `all_resolved` | 313 | 296 | 94.6% | 180 | 180 |
| 10 | `hormuz_crossing` | 15 | 1 | 6.7% | 11 | 1 |
| 10 | `inside_hormuz_non_crossing` | 0 | 0 | n/a † | 0 | 0 |
| 10 | `non_gulf` | 298 | 295 | 99.0% | 172 | 179 |
| 20 | `all_resolved` | 648 | 607 | 93.7% | 333 | 333 |
| 20 | `hormuz_crossing` | 26 | 1 | 3.8% | 16 | 1 |
| 20 | `inside_hormuz_non_crossing` | 0 | 3 | n/a † | 0 | 1 |
| 20 | `non_gulf` | 622 | 603 | 96.9% | 323 | 331 |
| 30 | `all_resolved` | 731 | 674 | 92.2% | 362 | 362 |
| 30 | `hormuz_crossing` | 37 | 2 | 5.4% | 20 | 2 |
| 30 | `inside_hormuz_non_crossing` | 1 | 3 | 300.0% † | 1 | 1 |
| 30 | `non_gulf` | 693 | 669 | 96.5% | 349 | 359 |

† Pre-period support of 10 sequences or fewer. A retention share on such a base is numerically unstable — a movement of one or two sequences can exceed 100% — and must not be read as a trend.

At 30 km the balanced cohort retains 92.2% of overall support and 5.4% of Hormuz-crossing support, so the contrast is not an artifact of carrier turnover.

## Census coverage

The eligible fleet census contains 624 IMOs under the `eligible_fleet_census` sampling design. Coverage shares below are the fraction of that census appearing at all in a cell. They are support-observation shares, never fleet utilisation.

| Radius (km) | Period | Cohort | Unique IMOs | Census coverage |
|---:|---|---|---:|---:|
| 10 | post | `all_resolved` | 253 | 40.5% |
| 10 | pre | `all_resolved` | 334 | 53.5% |
| 10 | post | `hormuz_crossing` | 1 | 0.2% |
| 10 | pre | `hormuz_crossing` | 56 | 9.0% |
| 20 | post | `all_resolved` | 377 | 60.4% |
| 20 | pre | `all_resolved` | 463 | 74.2% |
| 20 | post | `hormuz_crossing` | 1 | 0.2% |
| 20 | pre | `hormuz_crossing` | 63 | 10.1% |
| 30 | post | `all_resolved` | 404 | 64.7% |
| 30 | pre | `all_resolved` | 476 | 76.3% |
| 30 | post | `hormuz_crossing` | 2 | 0.3% |
| 30 | pre | `hormuz_crossing` | 64 | 10.3% |

## Audit expectation

Benchmark at 30 km: reproduced.

| Check | Expected | Observed | Reproduced |
|---|---:|---:|---|
| hormuz_crossing_pre_sequences | 145 | 145 | yes |
| hormuz_crossing_post_sequences | 2 | 2 | yes |
| all_resolved_pre_sequences | 971 | 971 | yes |
| all_resolved_post_sequences | 746 | 746 | yes |

A Hormuz-crossing sequence is a resolved liquefaction-to-regasification sequence whose origin is a registered Gulf export project AND whose modeled route transits the strait. This is the hormuz_exposed_leg flag already used by the importer/basin exposure layer. Counting every resolved sequence whose modeled route merely transits Hormuz gives 152 pre-period sequences instead of 145; the seven extra sequences originate outside the registered Gulf export projects (Oman Qalhat, Nigeria, Sabine Pass) and are reported in the non_gulf cohort.

## Interpretation limits

- The construct is modeled resolved terminal-sequence support. It is not observed voyages, not cargo, and not physical throughput.
- A missing modeled edge is a missing observation. It is not evidence that no ship sailed.
- No AIS-dark throughput may be inferred from these counts. The failure modes that remove a sequence from the panel are themselves plausibly correlated with the disruption, which would bias any such inference in an unknown direction.
- Selective support loss is a descriptive contrast between two observation counts. It is not an average treatment effect and it does not identify a causal mechanism.
- The upstream capacity and radius-comparison artifacts are hash-verified read-only inputs to this phase.

