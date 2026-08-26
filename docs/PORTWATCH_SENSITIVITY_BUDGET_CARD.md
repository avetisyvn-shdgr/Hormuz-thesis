# PortWatch sensitivity-budget reporting card

**Artifact role:** Assistant-generated from the G4-verified matrix. Human verification state is tracked in `DECISION_LOG.md`, not embedded in these frozen bytes.

## Primary absolute-throughput result

| Selected specification | Pinned | August | Pinned − August |
|---|---:|---:|---:|
| Seasonal naive | 54.800 | 43.700 | 11.100 |
| AR(1,7) | 52.838 | 43.814 | 9.025 |
| Chronos-2 | 50.884 | 42.177 | 8.707 |
| BSTS | 49.625 | 40.167 | 9.458 |

Holding the vintage fixed, the selected four-specification range is **5.175 lost transits/day** in the pinned vintage and **3.646/day** in the August vintage. Holding the model fixed, vintage differences span **8.707–11.100/day**. Every same-model vintage difference exceeds both within-vintage selected-model ranges.

For the locked AR primary, the vintage difference is **9.025/day**, or **1.744×** the pinned selected-model range. This ratio names one exact comparison; it is not a share or general importance measure.

## Secondary denominator check

| Selected specification | Pinned | August | August − pinned |
|---|---:|---:|---:|
| Seasonal naive | 93.0877% | 93.4068% | +0.3191 pp |
| AR(1,7) | 92.8494% | 93.4227% | +0.5733 pp |
| Chronos-2 | 92.5951% | 93.1849% | +0.5898 pp |
| BSTS | 92.4215% | 92.8683% | +0.4468 pp |

Using each cell's own model counterfactual as denominator, all eight shortfall shares lie between **92.4215%** and **93.4227%**. Same-model vintage changes are only **0.3191–0.5898 percentage points**. Thus the vintage materially changes the absolute scale while the model-relative shortfall shares are numerically clustered. Because the denominators are cell-specific and the ratios sit near a ceiling, this is descriptive scale context rather than independent robustness evidence, a third budget component, or the raw observed pre/post decline.

## Admission-rule challenge

The post-treatment-covariate ARX route-energy row is 62.858/day. If it is mixed into the pinned numeric range, that mixed-information range is **13.233/day**, which exceeds the selected-model vintage differences. It remains disclosed but excluded because it conditions on observed post-cutoff route and energy covariates. Therefore the headline is explicitly conditional on the selected same-observed-local-information rule, which was frozen ex post and unblinded.

TimesFM and Moirai have no frozen matched 130-day cells. Synthetic control uses post-period donors and mean-scaled transit-equivalent units. None enters this selected-model range.

## Defence-ready answer

> On the identical 130-day window, the four selected specifications span 5.175 transits/day in the pinned vintage and 3.646 in the August vintage. Holding the model fixed, the vintage changes the absolute estimate by 8.707–11.100/day, while model-relative shortfall shares stay numerically near 92.4–93.4%. I therefore report absolute magnitude as vintage-sensitive within this selected case, not as a variance decomposition, ATT, or all-model result.

## Interpretation guard

The absolute axes are separate and non-additive. There is no combined budget total and no vintage average. This is a descriptive case-local sensitivity analysis of counterfactual forecast shortfalls, not an uncertainty interval, variance decomposition, ATT, claim that either vintage is more accurate, or general statement about AIS reliability. Changing vintage replaces the saved series used for both pre-treatment training and post-treatment scoring; the comparison is not attributable only to revised post-treatment counts. The August raw source-byte archive deposit remains pending.
