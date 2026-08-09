# Inferred capacity-nautical-mile results

**Build status:** Verified locally and covered by the current full suite.
**Interpretation:** Descriptive mechanism evidence, not a causal effect and not
observed cargo ton-miles.

## Main decomposition

| Terminal radius | Route rule | Total pre/post change | Routed voyages pre/post change | Mean per-voyage change |
|---:|---|---:|---:|---:|
| 10 km | strict 30 nm snap | -27.3% | -34.3% | +10.6% |
| 10 km | expanded 60 nm snap | -24.4% | -30.1% | +8.1% |
| 20 km | strict 30 nm snap | -20.0% | -28.9% | +12.4% |
| 20 km | expanded 60 nm snap | -19.0% | -25.6% | +9.0% |
| 30 km | strict 30 nm snap | -16.3% | -26.3% | +13.6% |
| 30 km | expanded 60 nm snap | -15.6% | -23.4% | +10.2% |

The robust directional result is not an increase in the aggregate total. Fewer
resolved/routed voyages are observed post disruption, while nominal
capacity-distance per retained voyage rises under all six specifications. At
the 30 km terminal radius with expanded route QA, the total falls from 628.2 to
530.2 billion `m3-nm`, while the mean rises from 662.7 to 730.3 million `m3-nm`
per voyage.

## Uncertainty and route-composition decomposition

At the primary 30 km / expanded-route specification, a 5,000-draw bootstrap
that resamples the 510 observed carriers as clusters gives a bias-corrected and
accelerated (BCa) 95% interval of **+4.39% to +17.05%** around the **+10.20%**
change in mean nominal capacity-distance per voyage. The original percentile
interval, **+4.05% to +16.70%**, is retained in the machine-readable output as a
comparison. The BCa adjustment is a small upward shift and does not change the
conclusion. These intervals reflect carrier-
sampling uncertainty; they do not cover route-model error, AIS missingness, or causal
identification.

An exact Kitagawa/Oaxaca decomposition is applied on the 189 terminal pairs
observed in both periods. Their absolute mean increase is 38.0 million `m3-nm`:
37.1 million comes from route-share composition and 0.8 million from changes
within the same terminal pair. Entry and exit of routes contribute a separate
29.6 million `m3-nm` residual to the full-sample 67.6 million increase. Because
modeled distance is fixed within a terminal pair, the small within-pair term is
vessel-capacity mix, **not evidence that a given route became longer**. The
common-route component is therefore predominantly route-share composition; the
full-sample headline combines that common-route shift with a separate entry/exit
sample-composition residual.

## Coverage and censoring

- The frozen carrier frame has 624 unique IMOs, no duplicate IMO, and no invalid
  nominal capacity. All candidate rows join to a carrier capacity.
- The union route matrix contains 621 terminal pairs. Expanded QA accepts 598
  pairs (96.3%); strict QA accepts 467 (75.2%). No resolved voyage is missing a
  route-pair record.
- Expanded route coverage is 96.8% to 97.6% across radius-period cells.
- At the 30 km radius, right-censoring is 19.6% pre and 21.6% post. The higher
  post rate may contribute to the lower completed-voyage total, but it does not
  by itself explain or correct the difference.

## Defensible conclusion at this stage

The open-data reconstruction shows a higher average capacity-distance among
retained post-period sequences, with the bootstrap interval above zero, but the
route decomposition attributes most of that change to composition. It also
shows a drop in observed completed voyages. These findings cannot distinguish
physical reallocation from changes in sample composition, terminal matching,
AIS coverage, censoring, partial cargoes, or actual laden state.

Aggregate Gulf-origin validation against the distinct WTO/AXSMarine LNG
outbound index is complete; see `GULF_DEPARTURE_WTO_VALIDATION_RESULTS.md`.
