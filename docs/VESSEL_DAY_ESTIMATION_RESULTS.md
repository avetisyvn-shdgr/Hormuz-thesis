# Modeled vessel-day estimation

**Status:** Verified locally and covered by the current full suite.
**Measure:** Speed-based modeled sailing days, not observed AIS voyage duration.

## Method

Modeled terminal-to-terminal nautical miles are divided by an assumed sailing
speed. The central assumption is 15 knots, with 13 and 17 knots reported as
sensitivities. Waiting, anchorage, storage, canal delay, and port time are not
included.

The speed range is consistent with published evidence that large LNG carriers
are commonly designed near 19–20 knots while observed operating-to-design speed
ratios vary roughly from 0.65 to 0.95. The assumptions are not vessel-specific
speed observations.

## Primary result

The primary specification uses the 30 km terminal radius and expanded 60 nm
route-snap rule.

| Assumed speed | Pre sailing vessel-days | Post sailing vessel-days | Total change | Mean days/voyage change | Descriptive post excess vs pre mean |
|---:|---:|---:|---:|---:|---:|
| 13 knots | 12,136 | 10,050 | -17.2% | +8.1% | +757 days |
| 15 knots | 10,518 | 8,710 | -17.2% | +8.1% | +656 days |
| 17 knots | 9,280 | 7,686 | -17.2% | +8.1% | +579 days |

At 15 knots, routed voyages fall from 948 to 726 (-23.4%), so total modeled
sailing demand falls. However, mean modeled sailing time rises from 11.09 to
12.00 days per retained voyage. Holding the number of post voyages fixed, their
longer route composition requires about 656 additional sailing days relative to
the pre-period mean.

Capacity-weighted vessel-days fall 15.6% in total but rise 10.2% per voyage. The
central descriptive excess is approximately 136.3 million nominal `m3-days`.
This is algebraically consistent with the capacity-nautical-mile results.

## Endpoint elapsed-time audit

Endpoint elapsed time is not used as sailing duration because it includes
unobserved waiting and intermediate activity:

- Pre: median 12.54 days; 921 plausible implied-speed records and 50 extended
  elapsed records.
- Post: median 12.73 days; 702 plausible records, 42 extended records, one
  negative elapsed interval, and one implausibly fast interval.

These anomalies remain in the audit output rather than being repaired or used
to calibrate sailing speed.

## Interpretation

The result supports a descriptive fleet-time multiplier among retained voyages:
post-period routes are longer on average even though fewer completed voyages are
observed. The 656-day quantity is not an ATT, a forecast, or proof of physical
replacement. It depends directly on terminal classification, modeled routes,
the retained-voyage sample, and the 15-knot assumption.

Speed evidence: ICCT/UCL, *Assessment of shipping's efficiency using satellite
AIS data*: https://theicct.org/wp-content/uploads/2021/06/UCL_ship_efficiency_forICCT_2013.pdf
