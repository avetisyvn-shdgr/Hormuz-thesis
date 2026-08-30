# Current Empirical Results Summary

**Generated from processed artifacts.** This is a working results table, not final thesis language.

## Baseline Validation

| Target | Model | MAE mean | RMSE mean | MASE mean | sMAPE mean |
|---|---:|---:|---:|---:|---:|
| Hormuz tanker transits | Seasonal naive 7d | 13.65 | 16.69 | 1.00 | 26.03% |
| Hormuz tanker transits | AR lag 1/7, no observed post controls | 12.51 | 14.86 | 0.92 | 23.31% |
| Hormuz tanker transits | ARX lag 1/7 + route controls | 12.45 | 14.83 | 0.92 | 23.21% |

## Post-treatment Counterfactual Gap

Lead inference: 7 disjoint horizon blocks give a one-sided rank p-value of **0.125**. The nominal 95% block-conformal interval is **unbounded**, and the maximum finite coverage is **87.5%**.

| Model | Cumulative loss | Mean daily loss | Overlapping-window reference rank (not p) | Placebo p95 | Separation |
|---|---:|---:|---:|---:|---:|
| AR-only working primary, transit count | 6,869 transits | 52.8/day | 0.028 | 2,124 | 3.2x |
| Route-only ARX, transit count | 7,056 transits | 54.3/day | 0.028 | 2,171 | 3.3x |

Information-set sensitivity: AR-only uses no observed post-treatment covariates and gives an empirical overlapping-placebo 2.5/97.5% quantile band over 130 calendar days of **5,430 to 8,089 transits**, with no nominal coverage claim. Its close agreement with route ARX indicates that contemporaneous Panama controls are not driving the estimated gap. Route ARX remains a conditional sensitivity because Panama traffic is observed post-treatment.

Residual-calibrated 95% aggregate interval for the AR-only working-primary transit loss: **6,305 to 7,410 tanker transits**, or 48.5 to 57.0 per day. This band is calibrated on <=30-day folds and understates the current 130-calendar-day horizon.

Empirical overlapping-placebo 2.5/97.5% quantile band, using full-horizon forecast errors: **5,430 to 8,089 tanker transits** — about 2.4x wider than the short-fold band. This is a descriptive scale diagnostic, not a confidence, prediction, or conformal interval (7 disjoint windows are available for separate rank inference).
Independent circular-block cross-check (10,000 draws, 14-day blocks from the ordered out-of-fold residual path): **6,180 to 7,550 transits**. It is materially narrower than the placebo-window band, so band width is method-sensitive.

Matched-horizon TSFM sensitivity: Chronos-2 and AR-only use the same scored dates and observations through 2026-07-07 (130 transit days; 118 valid capacity days), both trained on this panel from 2022-01-01. Chronos-2 changes the locked-primary transit shortfall by **-3.7%** and the capacity shortfall by **-10.6%** (291.0M AR-only versus 260.0M Chronos-2). Capacity is therefore a directional secondary, model-sensitive outcome; its precise magnitude is not load-bearing.
The transit percentage is conditional on the 2022-01-01 training start. Under the longer PortWatch history the event panel uses, the sign of the Chronos-versus-AR difference reverses; both specifications and the shortfall percentages that are stable across them are generated into `experiments/network_adaptation/outputs/hormuz_shortfall_specification_sensitivity.csv`.

The loss exceeds all 35 overlapping placebo windows. Their 1/36 reference rank is descriptive, not a p-value; the separation ratio is reported alongside it. Only about 7 disjoint horizon windows are available.

## Treatment-window Robustness

All rows keep the training cutoff fixed at **2026-02-28**; later event dates define scoring windows only. Later cutoffs would train on disrupted days and poison the baseline.

| Window | Scored post window | Valid days | Cumulative loss | Mean daily loss |
|---|---:|---:|---:|---:|
| donut_clean_post_after_force_majeure | 2026-03-05 to 2026-07-07 | 125 | 6,642 | 53.1/day |
| anchored_kinetic_trigger | 2026-02-28 to 2026-07-07 | 130 | 6,869 | 52.8/day |
| anchored_closure_declaration | 2026-03-02 to 2026-07-07 | 128 | 6,808 | 53.2/day |
| anchored_force_majeure | 2026-03-04 to 2026-07-07 | 126 | 6,698 | 53.2/day |

Donut interpretation: excluding the ambiguous transition window 2026-02-28 through 2026-03-04 lowers cumulative loss mechanically because fewer days are scored, while the mean daily AR-only loss remains close to the anchored windows.

## Same-date Spatial Placebo

| Donor set | Raw loss | Normalized loss | Donor raw p95 | Raw separation | Donor normalized p95 | Normalized separation |
|---|---:|---:|---:|---:|---:|---:|
| All donors | 7,124 | 93.1% | 1,010.9 | 7.0x | 20.4% | 4.6x |
| Low-contamination donors | 7,124 | 93.1% | 1,023.0 | 7.0x | 21.0% | 4.4x |

Spatial placebo interpretation: Hormuz ranks first by raw loss and by normalized loss. Malacca is the largest raw donor loss, but normalized severity shows it is not comparable to the near-total Hormuz collapse.

## Leave-one-donor-out Spatial Sensitivity

| Donor set | Worst dropped donor | Min normalized separation | Drop Malacca normalized separation | Normalized p-value range |
|---|---:|---:|---:|---:|
| All donors | bab_el_mandeb_strait | 4.5x | 5.0x | 0.037-0.038 |
| Low-contamination donors | balabac_strait | 4.4x | 4.9x | 0.045-0.048 |

Leave-one-out interpretation: the normalized transit-count separation is not driven by a single donor. Dropping Malacca, the largest raw donor loss, increases rather than weakens the normalized separation.

## Synthetic-control Corroboration

Donor-weighted synthetic control on the clean donor pool (five rerouting corridors excluded), matched on pre-period mean-scaled throughput so the check is about shape, not chokepoint size. Inference is Abadie-style: the post/pre RMSPE ratio for Hormuz is compared against the same ratio computed for each clean donor treated as a placebo. This corroborates, it is not the anchor estimator.

| Quantity | Value |
|---|---:|
| Clean donors in fit | 22 |
| Pre-period fit days | 1519 |
| Pre-period RMSPE (fit quality) | 0.258 |
| Post-period RMSPE | 0.840 |
| Post/pre RMSPE ratio | 3.25 |
| Primary pre-fit screen | placebo pre-RMSPE <= 2.0x treated |
| Eligible / total placebos | 14 / 22 (8 excluded) |
| Screened placebo ratio p95 | 1.502 |
| Hormuz ratio / screened placebo p95 | 2.166x |
| Screened rank p-value | 0.066667 |
| Screened rank floor | 1/15 = 0.066667 |
| Effective donors (1/sum w^2) | 7.4 |
| Largest single weight | korea_strait (0.22) |

Synthetic-control interpretation: the pre-period fit is credible (RMSPE 0.258 on mean-scaled units, 7.4 effective donors, no single donor dominating), and Hormuz's post/pre RMSPE ratio exceeds every placebo that passes the remediation-primary 2x pre-fit screen. Across the 1.5x, 2x, 5x, 10x, and unscreened specifications, the rank p-value ranges from 0.043478 to 0.083333; the unscreened value is 0.043478. The 2x rule is the remediation-primary convention, and the grid prevents the interpretation from depending on that single choice. This is a corroborating diagnostic consistent with the other falsification layers, not an independent design. It remains a scaled, shape-based diagnostic, not an LNG freight-rate estimate.

## Guardrails

- Results are about observed AIS-based tanker throughput, not LNG-specific freight rates.
- Normalized spatial loss should lead the spatial-placebo interpretation because raw counts are scale-confounded.
- Capacity is a directional secondary, model-sensitive outcome; use mean-daily direction and do not lean on its precise magnitude.
- PortWatch fallback is the working primary; formal estimand realignment remains pending Prof. Li confirmation.
- Spark is a dormant optional secondary-outcome extension and is not a blocker.
