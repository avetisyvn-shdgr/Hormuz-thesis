# Current Empirical Results Summary

**Generated from processed artifacts.** This is a working results table, not final thesis language.

## Baseline Validation

| Target | Model | MAE mean | RMSE mean | MASE mean | sMAPE mean |
|---|---:|---:|---:|---:|---:|
| Hormuz tanker transits | Seasonal naive 7d | 13.65 | 16.69 | 1.00 | 26.03% |
| Hormuz tanker transits | AR lag 1/7, no observed post controls | 12.51 | 14.86 | 0.92 | 23.31% |
| Hormuz tanker transits | ARX lag 1/7 + route controls | 12.45 | 14.83 | 0.92 | 23.21% |

## Post-treatment Counterfactual Gap

| Model | Cumulative loss | Mean daily loss | Placebo p-value | Placebo p95 | Separation |
|---|---:|---:|---:|---:|---:|
| AR-only working primary, transit count | 6,869 transits | 52.8/day | 0.028 | 2,124 | 3.2x |
| Route-only ARX, transit count | 7,056 transits | 54.3/day | 0.028 | 2,171 | 3.3x |

Information-set sensitivity: AR-only uses no observed post-treatment covariates and gives a 94-day interval of **5,430 to 8,089 transits**. Its close agreement with route ARX indicates that contemporaneous Panama controls are not driving the estimated gap. Route ARX remains a conditional sensitivity because Panama traffic is observed post-treatment.

Residual-calibrated 95% aggregate interval for the AR-only working-primary transit loss: **6,305 to 7,410 tanker transits**, or 48.5 to 57.0 per day. This band is calibrated on <=30-day folds and understates a 94-day horizon.

Honest 94-day-horizon interval (recalibrated on the placebo-in-time windows, which are full 94-day forecast errors): **5,430 to 8,089 tanker transits** — about 2.4x wider than the short-fold band, and still excluding zero by a wide margin. Use this as the reported interval; the short-fold band is a lower bound. The band is coarse/conservative (~9 effective windows).
Independent circular-block cross-check (10,000 draws, 14-day blocks from the ordered out-of-fold residual path): **6,180 to 7,550 transits**. It is materially narrower than the placebo-window band, so interval width is method-sensitive even though both bands exclude zero.

Chronos-2 changes the locked-primary transit shortfall by only **+2.4%**, but changes the capacity shortfall by **-5.2%** (206.9M AR-only versus 196.1M Chronos-2). Capacity is therefore a directional secondary, model-sensitive outcome; its precise magnitude is not load-bearing.

The time-placebo p-value is floor-censored because 36 overlapping placebo windows provide only about 9 non-overlapping 94-day windows. Report the separation ratio alongside the p-value.

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
| Placebo ratio p95 | 1.25 |
| Hormuz ratio / placebo p95 | 2.60x |
| Abadie placebo p-value | 0.043 |
| Effective donors (1/sum w^2) | 7.4 |
| Largest single weight | korea_strait (0.22) |

Synthetic-control interpretation: the pre-period fit is credible (RMSPE 0.258 on mean-scaled units, 7.4 effective donors, no single donor dominating), and Hormuz's post/pre RMSPE ratio is far larger than any clean donor placebo. This is independent corroboration of the throughput collapse, consistent with the placebo-in-time and spatial-placebo layers. It remains a scaled, shape-based diagnostic, not an LNG freight-rate estimate.

## Guardrails

- Results are about observed AIS-based tanker throughput, not LNG-specific freight rates.
- Normalized spatial loss should lead the spatial-placebo interpretation because raw counts are scale-confounded.
- Capacity is a directional secondary, model-sensitive outcome; use mean-daily direction and do not lean on its precise magnitude.
- PortWatch fallback is the working primary; formal estimand realignment remains pending Prof. Li confirmation.
- Spark is a dormant optional secondary-outcome extension and is not a blocker.
