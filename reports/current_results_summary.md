# Current Empirical Results Summary

**Generated from processed artifacts.** This is a working results table, not final thesis language.

## Baseline Validation

| Target | Model | MAE mean | RMSE mean | MASE mean | sMAPE mean |
|---|---:|---:|---:|---:|---:|
| Hormuz tanker transits | Seasonal naive 7d | 9.47 | 11.57 | 1.03 | 17.23% |
| Hormuz tanker transits | AR lag 1/7, no observed post controls | 8.41 | 10.10 | 0.92 | 15.36% |
| Hormuz tanker transits | ARX lag 1/7 + route controls | 8.39 | 10.10 | 0.91 | 15.32% |

## Post-treatment Counterfactual Gap

| Model | Cumulative loss | Mean daily loss | Placebo p-value | Placebo p95 | Separation |
|---|---:|---:|---:|---:|---:|
| AR-only working primary, transit count | 5,121 transits | 54.5/day | 0.027 | 1,297 | 3.9x |
| Route-only ARX, transit count | 5,176 transits | 55.1/day | 0.027 | 1,307 | 4.0x |

Information-set sensitivity: AR-only uses no observed post-treatment covariates and gives a 94-day interval of **3,934 to 5,722 transits**. Its close agreement with route ARX indicates that contemporaneous Panama controls are not driving the estimated gap. Route ARX remains a conditional sensitivity because Panama traffic is observed post-treatment.

Residual-calibrated 95% aggregate interval for the AR-only working-primary transit loss: **4,758 to 5,434 tanker transits**, or 50.6 to 57.8 per day. This band is calibrated on <=30-day folds and understates a 94-day horizon.

Honest 94-day-horizon interval (recalibrated on the placebo-in-time windows, which are full 94-day forecast errors): **3,934 to 5,722 tanker transits** — about 2.6x wider than the short-fold band, and still excluding zero by a wide margin. Use this as the reported interval; the short-fold band is a lower bound. The band is coarse/conservative (~9 effective windows).

The time-placebo p-value is floor-censored because 36 overlapping placebo windows provide only about 9 non-overlapping 94-day windows. Report the separation ratio alongside the p-value.

## Treatment-window Robustness

All rows keep the training cutoff fixed at **2026-02-28**; later event dates define scoring windows only. Later cutoffs would train on disrupted days and poison the baseline.

| Window | Scored post window | Valid days | Cumulative loss | Mean daily loss |
|---|---:|---:|---:|---:|
| donut_clean_post_after_force_majeure | 2026-03-05 to 2026-06-01 | 89 | 4,889 | 54.9/day |
| anchored_kinetic_trigger | 2026-02-28 to 2026-06-01 | 94 | 5,121 | 54.5/day |
| anchored_closure_declaration | 2026-03-02 to 2026-06-01 | 92 | 5,058 | 55.0/day |
| anchored_force_majeure | 2026-03-04 to 2026-06-01 | 90 | 4,947 | 55.0/day |

Donut interpretation: excluding the ambiguous transition window 2026-02-28 through 2026-03-04 lowers cumulative loss mechanically because fewer days are scored, while the mean daily AR-only loss remains close to the anchored windows.

## Same-date Spatial Placebo

| Donor set | Raw loss | Normalized loss | Donor raw p95 | Raw separation | Donor normalized p95 | Normalized separation |
|---|---:|---:|---:|---:|---:|---:|
| All donors | 5,234 | 95.5% | 636.6 | 8.2x | 19.3% | 5.0x |
| Low-contamination donors | 5,234 | 95.5% | 601.9 | 8.7x | 20.3% | 4.7x |

Spatial placebo interpretation: Hormuz ranks first by raw loss and by normalized loss. Malacca is the largest raw donor loss, but normalized severity shows it is not comparable to the near-total Hormuz collapse.

## Leave-one-donor-out Spatial Sensitivity

| Donor set | Worst dropped donor | Min normalized separation | Drop Malacca normalized separation | Normalized p-value range |
|---|---:|---:|---:|---:|
| All donors | bab_el_mandeb_strait | 4.9x | 6.0x | 0.037-0.038 |
| Low-contamination donors | balabac_strait | 4.6x | 5.6x | 0.045-0.048 |

Leave-one-out interpretation: the normalized transit-count separation is not driven by a single donor. Dropping Malacca, the largest raw donor loss, increases rather than weakens the normalized separation.

## Synthetic-control Corroboration

Donor-weighted synthetic control on the clean donor pool (five rerouting corridors excluded), matched on pre-period mean-scaled throughput so the check is about shape, not chokepoint size. Inference is Abadie-style: the post/pre RMSPE ratio for Hormuz is compared against the same ratio computed for each clean donor treated as a placebo. This corroborates, it is not the anchor estimator.

| Quantity | Value |
|---|---:|
| Clean donors in fit | 22 |
| Pre-period fit days | 1519 |
| Pre-period RMSPE (fit quality) | 0.175 |
| Post-period RMSPE | 0.835 |
| Post/pre RMSPE ratio | 4.77 |
| Placebo ratio p95 | 1.23 |
| Hormuz ratio / placebo p95 | 3.87x |
| Abadie placebo p-value | 0.043 |
| Effective donors (1/sum w^2) | 8.7 |
| Largest single weight | korea_strait (0.18) |

Synthetic-control interpretation: the pre-period fit is credible (RMSPE 0.175 on mean-scaled units, 8.7 effective donors, no single donor dominating), and Hormuz's post/pre RMSPE ratio is far larger than any clean donor placebo. This is independent corroboration of the throughput collapse, consistent with the placebo-in-time and spatial-placebo layers. It remains a scaled, shape-based diagnostic, not an LNG freight-rate estimate.

## Guardrails

- Results are about observed AIS-based tanker throughput, not LNG-specific freight rates.
- Normalized spatial loss should lead the spatial-placebo interpretation because raw counts are scale-confounded.
- Capacity results require mean-daily interpretation because artifact masking changes valid day counts.
- PortWatch fallback is the working primary; formal estimand realignment remains pending Prof. Li confirmation.
- Spark is a dormant optional secondary-outcome extension and is not a blocker.
