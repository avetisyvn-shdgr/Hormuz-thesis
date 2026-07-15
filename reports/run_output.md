# End-to-End PortWatch Fallback Run

- Working branch: `fallback_portwatch`
- Primary outcome: `hormuz_tanker_transits`
- Robustness outcome: `hormuz_tanker_capacity`
- Primary estimator: `ar_lag1_7`
- Treatment cutoff: `2026-02-28`
- Reporting estimand: **disruption-associated counterfactual shortfall**
- Transformer enabled: **no**

## Headline AR-only result

- Point shortfall: **6,869.0 tanker transits** (52.84/day).
- Horizon-matched 95% interval: **5,430.3 to 8,088.9 transits**.
- Independent 14-day circular-block bootstrap band: **6,179.5 to 7,549.5 transits**; narrower than the placebo-window band, so width is method-sensitive.
- Temporal-placebo p95: **2,124.3**; separation: **3.234x**.
- One-sided placebo p-value: **0.027778**, floor-censored with 36 overlapping / about 9 non-overlapping windows.
- BSTS posterior median shortfall: **6,437.9**; 95% posterior predictive interval: **1,754.6 to 11,709.6**.
- BSTS prior-grid median range: **6,457.6 to 6,751.9**; interval-envelope endpoints: **878.6 to 13,836.2**; pre-period PPC pointwise coverage: **97.1%**.

## Pre-treatment validation and residual fidelity

| Model | MASE | RMSE | Residual mean | Residual SD | ACF(1) | ACF(7) |
|---|---|---|---|---|---|---|
| seasonal_naive_7d | 1.005 | 16.691 | 1.828 | 17.049 | 0.259 | 0.289 |
| ar_lag1_7 | 0.920 | 14.862 | -5.001 | 14.361 | 0.481 | 0.231 |
| arx_lag1_7_route | 0.916 | 14.829 | -4.562 | 14.503 | 0.492 | 0.247 |
| arx_lag1_7_route_energy | 0.859 | 14.012 | -1.015 | 14.249 | 0.477 | 0.229 |

For the primary AR-only model, `1140` rolling-origin residuals have median `-5.854`, 5th/95th percentiles `-27.589` / `18.748`. Residual autocorrelation is reported above because remaining serial dependence limits naive pointwise uncertainty claims.

## Specification comparison

| Specification | Role | Pre MASE | Pre RMSE | Point shortfall | 94d lower | 94d upper | Placebo separation | p-value |
|---|---|---|---|---|---|---|---|---|
| ar_lag1_7 | working_primary | 0.920 | 14.862 | 6,869.0 | 5,430.3 | 8,088.9 | 3.234 | 0.028 |
| arx_lag1_7_route | conditional_sensitivity | 0.916 | 14.829 | 7,056.4 | 5,502.4 | 8,528.0 | 3.251 | 0.028 |
| arx_lag1_7_route_energy | conditional_sensitivity | 0.859 | 14.012 | 8,171.5 | 6,520.0 | 9,319.0 | 5.301 | 0.028 |
| synthetic_control | corroboration | NA | 14.739 | 6,174.6 | NA | NA | 2.602 | 0.043 |
| bsts_local_level_weekly | state_space_corroboration | 0.837 | 13.797 | 6,437.9 | 1,754.6 | 11,709.6 | NA | NA |

Full machine-readable table: [`data/processed/run_spec_comparison.csv`](../data/processed/run_spec_comparison.csv)

Synthetic-control shortfall is converted from mean-scaled units to a transit-equivalent magnitude for comparison. Its placebo metric is the post/pre RMSPE ratio, not the temporal cumulative-shortfall distribution, and no 94-day interval is asserted for it.
BSTS is an independent state-space corroboration. Its interval is posterior predictive conditional on the local-level model; it is not a causal posterior.

## Independent-block inference

- Disjoint 94-day placebo blocks: **7**; honest rank p-value: **0.125** (floor **0.125**).
- Actual / independent-placebo p95 separation: **4.161x**.
- 90% block-conformal interval: **-inf to inf**.
- 95% block-conformal interval: **unbounded**; nine independent blocks support at most **88%** finite-sample coverage.

## Synthetic-control corroboration

- Pre-period RMSPE: **0.258158 scaled units** (**14.739 transit-equivalent RMSE**).
- Post-period RMSPE: **0.839927**; post/pre ratio: **3.254**.
- Transit-equivalent cumulative gap: **6,174.6**.
- Donor-placebo p95 ratio: **1.250**; separation: **2.602x**; p-value: **0.043478**.
- Donors: **22**; effective donors: **7.44**; largest weight: `korea_strait` (0.216).
- Donor-pool stress: clean ratio **3.254**, broad-pool ratio **3.378**.
- Donor-by-time placebos: **154** fits across **7** disjoint windows; p-value **0.006452**, actual/p95 **2.261x**.

## LNG-specific robustness outcome

The public WTO/AXSMarine series is an LNG-only outbound shipment volume index (2025 average = 100) and excludes LPG. It is not a carrier count, physical volume, or freight rate.
- AR 94-day index-point shortfall: **12,923.5**.
- BSTS posterior median: **12,759.9**; 95% interval **3,105.6 to 25,066.1**.

## Data-quality checks

- Primary transit outcome has complete post-period coverage (94/94 days).
- Capacity is a directional secondary, model-sensitive outcome. It has `12` masked post-period values; all `12` are audit-confirmed zero-capacity/positive-transit artifacts and `0` are unexplained. Do not lean on its precise magnitude.

## Figures

![Observed vs AR-only counterfactual](figures/run_actual_vs_counterfactual.png)

![Temporal placebo distribution](figures/run_placebo_distribution.png)

![Actual vs synthetic control](figures/run_synthetic_control_path.png)

![BSTS counterfactual](figures/bsts_counterfactual.png)

![LNG-only index counterfactual](figures/lng_index_counterfactual.png)

## Interpretation guard

These are disruption-associated counterfactual shortfalls in observed AIS-based tanker throughput, not a causal ATT and not an LNG freight-rate estimate.
