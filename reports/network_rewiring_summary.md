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

## Importer and comparator summary

| Unit | Typology | Strength | Pre Gulf share | Gulf-share change | Total change vs 12m pre | Total change vs same months | JS distance | Anomaly z | Typology total basis | Coverage |
|---|---|---|---|---|---|---|---|---|---|---|
| China | high_exposure_constrained | medium | 30.4% | -21.6 pp | -25.7% | -13.9% | 0.21 | 7.5 | same_calendar_prior_year | descriptive_coverage_ok |
| EU27 | aggregate_comparator | context_only | 5.8% | -3.7 pp | +3.5% | -3.3% | 0.15 | 5.0 | same_calendar_prior_year | descriptive_coverage_ok; aggregate_comparator |
| India | high_exposure_high_offset | medium | 58.1% | -52.3 pp | +5.1% | +5.9% | 0.41 | 6.5 | same_calendar_prior_year | descriptive_coverage_ok; value_basis |
| Japan | low_exposure_stable | medium | 6.5% | -5.1 pp | -13.1% | -7.7% | 0.17 | 3.1 | same_calendar_prior_year | descriptive_coverage_ok |
| Korea | high_exposure_constrained | medium | 15.2% | -13.6 pp | -15.8% | -12.4% | 0.24 | 4.6 | same_calendar_prior_year | descriptive_coverage_ok |
| Taiwan | high_exposure_high_offset | high | 34.9% | -29.7 pp | +1.4% | +2.5% | 0.27 | 6.9 | same_calendar_prior_year | descriptive_coverage_ok |

## Reallocation stress scenarios

| Scenario | Demand k m3 | Allocated k m3 | Unmet share % | Mean route nm | Mean additional nm | Coverage |
|---|---|---|---|---|---|---|
| incremental_non_gulf_growth_only | 21,425 | 8,045 | 62.5 | 4,089 | +331 | observed_route_transport_solution; unmet_replacement_capacity |
| post_non_gulf_pool | 21,425 | 21,425 | 0.0 | 676 | -2,858 | observed_route_transport_solution; unroutable_observed_supply_excluded; lower_bound_short_route_pool |

## Interpretation guardrails

- China and Korea are classified as high-exposure constrained: their Gulf shares
  fell sharply and non-Gulf growth did not offset the lost Gulf edge value in
  the observed origin-split table.
- India and Taiwan are classified as high-exposure high-offset. India remains
  value-basis, so its substitution pattern should be read as customs-value
  evidence, not physical quantity evidence.
- EU27 is retained only as an aggregate comparator. Japan now has enough
  source-native e-Stat/Japan Customs support for the descriptive typology and
  is classified as a low-exposure stable comparator in this vintage.
- Graph-distance anomaly scores are exploratory mechanism diagnostics. They
  use leave-one-month-out pre-period calibration and help describe unusual
  post-shock portfolio movement, but they are not part of the primary causal
  inference family.
- The reallocation model is a transparent stress test over observed route
  costs. The `post_non_gulf_pool` case is a lower-bound routing exercise, not an
  observed replacement-cargo reconstruction; when flagged as a short-route pool,
  its negative additional-distance result should be read as a loose lower bound.
- Cross-unit tables mix native measurement bases: China, Japan, Korea, and
  Taiwan are tonnes; EU27 is MIO_M3; India is kUSD. Compare within-unit
  movements first, and treat India as value-basis evidence.
