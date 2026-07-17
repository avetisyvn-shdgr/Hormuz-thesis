# Network rewiring results summary

This report is generated from the staged network-rewiring artifacts. It supports
the descriptive mechanism claim that the 2026 Hormuz LNG disruption was absorbed
through observable origin-portfolio rewiring and scenario-conditional adaptation
costs. It does not report an ATT, a freight-rate effect, or observed cargo-level
replacement.

## Figures

- `reports/figures/network_rewiring_origin_composition.png`
- `reports/figures/network_rewiring_gulf_vs_total.png`
- `reports/figures/network_rewiring_source_structure.png`

## Quantity-basis importer and comparator summary

| Unit | Typology | Strength | Basis | Pre Gulf share | Gulf-share change | Total change vs 12m pre | Total change vs same months | JS distance | Anomaly z | Typology total basis | Coverage |
|---|---|---|---|---|---|---|---|---|---|---|---|
| China | high_exposure_constrained | medium | t | 30.4% | -21.6 pp | -25.7% | -13.9% | 0.21 | 7.48 | same_calendar_prior_year | descriptive_coverage_ok |
| Korea | high_exposure_constrained | medium | t | 15.2% | -13.6 pp | -15.8% | -12.4% | 0.24 | 4.65 | same_calendar_prior_year | descriptive_coverage_ok |
| Taiwan | high_exposure_high_offset | high | t | 34.9% | -29.7 pp | +1.4% | +2.5% | 0.27 | 6.86 | same_calendar_prior_year | descriptive_coverage_ok |
| Japan | low_exposure_stable | medium | t | 6.5% | -5.1 pp | -13.1% | -7.7% | 0.17 | 3.11 | same_calendar_prior_year | descriptive_coverage_ok |
| EU27 (aggregate comparator) | aggregate_comparator | context_only | MIO_M3 | 5.8% | -3.7 pp | +3.5% | -3.3% | 0.15 | 4.96 | same_calendar_prior_year | descriptive_coverage_ok; aggregate_comparator |

Source artifact(s): `data/processed/lng_rewiring_summary.csv`, `data/processed/lng_rewiring_graph_metrics.csv`, `data/processed/lng_resilience_typology.csv`, `data/processed/lng_network_anomaly_summary.csv`.

## India — customs-value evidence

| Unit | Typology | Strength | Basis | Caution | Pre Gulf share | Gulf-share change | Total change vs 12m pre | Total change vs same months | JS distance | Anomaly z | Coverage |
|---|---|---|---|---|---|---|---|---|---|---|---|
| India | high_exposure_high_offset | medium | kUSD | value_basis_caution | 58.1% | -52.3 pp | +5.1% | +5.9% | 0.41 | 6.54 | descriptive_coverage_ok; value_basis |

India is retained as descriptive customs-value evidence only. Its `kUSD` basis
means the origin mix can embed price differentials as well as quantity changes;
do not pool this row with the physical weight/volume-basis table above.
Source artifact(s): `data/processed/lng_resilience_typology.csv`.

## Typology sensitivity

Threshold-grid agreement with the headline typology:

| Unit | Headline typology | Grid agreement share | Agreement count | Alternative grid labels |
|---|---|---|---|---|
| China | high_exposure_constrained | 100.0% | 81/81 | none |
| Korea | high_exposure_constrained | 66.7% | 54/81 | intermediate_rewiring |
| Taiwan | high_exposure_high_offset | 100.0% | 81/81 | none |
| Japan | low_exposure_stable | 100.0% | 81/81 | none |
| EU27 (aggregate comparator) | aggregate_comparator | 100.0% | 81/81 | none |
| India | high_exposure_high_offset | 100.0% | 81/81 | none |

Leave-one-post-month interpretation:

| Unit | Headline typology | Leave-one-post-month result | Dropped-month detail |
|---|---|---|---|
| China | high_exposure_constrained | coverage-induced non-estimability | 2026-03 -> below three-post-month gate; 2026-04 -> below three-post-month gate; 2026-05 -> below three-post-month gate |
| Korea | high_exposure_constrained | stable under deletion | no admissible dropped-month label changes |
| Taiwan | high_exposure_high_offset | admissible substantive change | 2026-03 -> intermediate_rewiring |
| Japan | low_exposure_stable | coverage-induced non-estimability | 2026-03 -> below three-post-month gate; 2026-04 -> below three-post-month gate; 2026-05 -> below three-post-month gate |
| EU27 (aggregate comparator) | aggregate_comparator | aggregate comparator | context row; not interpreted as importer typology stability |
| India | high_exposure_high_offset | coverage-induced non-estimability | 2026-03 -> below three-post-month gate; 2026-04 -> below three-post-month gate; 2026-05 -> below three-post-month gate |

Source artifact(s): `data/processed/lng_typology_threshold_sensitivity.csv`, `data/processed/lng_rewiring_post_month_sensitivity.csv`.

## Anomaly diagnostics

All 6 units flag, and post_max_empirical_percentile = 1.000 for all units. The weakest flagged post-shock portfolio z-scores in the current artifact are Japan (z 3.11) and Korea (z 4.65). EU27 is z 4.96 and remains an aggregate comparator rather than a single importer. The empirical tail-p is floor-censored at 1/13 because the pre-period calibration uses leave-one-month-out distances over the available pre months.
Source artifact(s): `data/processed/lng_network_anomaly_summary.csv`.

## Reallocation stress scenarios

| Scenario | Demand k m3 | Allocated k m3 | Unmet share % | Mean route nm | Mean additional nm | Coverage |
|---|---|---|---|---|---|---|
| incremental_non_gulf_growth_only | 21,425 | 8,045 | 62.5 | 4,089 | +331 | observed_route_transport_solution; unmet_replacement_capacity |
| post_non_gulf_pool | 21,425 | 21,425 | 0.0 | 676 | -2,858 | observed_route_transport_solution; unroutable_observed_supply_excluded; lower_bound_short_route_pool |

## Interpretation guardrails

- China and Korea are classified as high-exposure constrained: their Gulf shares
  fell sharply and non-Gulf growth did not offset the lost Gulf edge value in
  the observed origin-split table.
- Evidence strength follows the transparent typology rubric: `high` is reserved
  for unflagged high-exposure high-offset cases; constrained cases,
  low-exposure stable cases, and flagged high-offset cases are `medium`;
  aggregate comparators are `context_only`.
- India and Taiwan are classified as high-exposure high-offset. Taiwan is the
  unflagged high-strength case; India remains value-basis, so its substitution
  pattern should be read as customs-value evidence, not physical quantity
  evidence.
- EU27 is retained only as an aggregate comparator. Japan now has enough
  source-native e-Stat/Japan Customs support for the descriptive typology and
  is classified as a low-exposure stable comparator in this vintage.
- Graph-distance anomaly scores are exploratory mechanism diagnostics. The
  current artifact flags all six units at the empirical percentile ceiling, but
  this is floor-censored by the 12-month pre-calibration support and remains
  outside the primary causal inference family.
- The reallocation model is a transparent stress test over observed route
  costs. The `post_non_gulf_pool` case is a lower-bound routing exercise, not an
  observed replacement-cargo reconstruction; when flagged as a short-route pool,
  its negative additional-distance result should be read as a loose lower bound.
- Cross-unit tables mix native measurement bases: China, Japan, Korea, and
  Taiwan are tonnes; EU27 is MIO_M3; India is kUSD. Compare within-unit
  movements first, and treat India as value-basis evidence.
