# Inferred capacity-nautical-mile results

**Build status:** Verified locally; 149 tests pass.  
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

The open-data reconstruction is consistent with longer and/or larger nominal
LNG voyages among retained post-period sequences. It is also consistent with a
drop in observed completed voyages. These findings cannot yet distinguish
physical reallocation from changes in sample composition, terminal matching,
AIS coverage, censoring, partial cargoes, or actual laden state.

Aggregate Gulf-origin validation against the independent WTO/AXSMarine LNG
outbound index is complete; see `GULF_DEPARTURE_WTO_VALIDATION_RESULTS.md`.
