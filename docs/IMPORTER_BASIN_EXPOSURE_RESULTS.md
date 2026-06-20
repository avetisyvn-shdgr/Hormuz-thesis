# Importer and basin exposure results

**Status:** Verified locally; 153 tests pass.  
**Scope:** Descriptive inferred nominal-capacity exposure, not observed imports,
cargo allocation, or causal replacement.

## Construction

The primary table uses the 30 km terminal match and expanded 60 nm route-snap
specification. A Hormuz-exposed leg must both originate at QatarEnergy LNG North
or Das Island and traverse the modeled `ormuz` passage. This excludes intra-Gulf
deliveries that do not cross the strait.

Destination markets are assigned explicitly to Atlantic, Pacific, or Middle
East groups. This follows the LNG industry's regional-market framing while
keeping Gulf/Red Sea importers separate. It is an analytical grouping, not a
claim that each country belongs unambiguously to one physical ocean basin.

## Basin results

| Destination basin | Pre Hormuz-exposed capacity share | Exposed capacity change | Non-Gulf capacity change | Total capacity change | Capacity-distance change |
|---|---:|---:|---:|---:|---:|
| Pacific | 21.8% | -20.26m m3 | -0.33m m3 | -21.9% | -8.4% |
| Atlantic | 1.9% | -1.17m m3 | -13.02m m3 | -23.6% | -28.9% |
| Middle East | 0.0% | 0 | +0.37m m3 | +9.8% | +16.0% |

Pacific capacity-distance falls much less than nominal capacity. Among retained
sequences, this is consistent with a shift toward longer supply paths. It does
not establish that specific non-Gulf cargoes replaced missing Gulf cargoes.

## Importer exposure

| Importer | Pre exposed share | Lost exposed capacity | Non-Gulf change | Descriptive offset | Total capacity change | Capacity-distance change |
|---|---:|---:|---:|---:|---:|---:|
| India | 66.8% | -7.90m m3 | +5.29m m3 | 67.1% | -22.0% | +59.3% |
| Bangladesh | 85.2% | -1.90m m3 | +1.88m m3 | 99.2% | -0.7% | +86.8% |
| China | 13.4% | -2.27m m3 | +1.86m m3 | 81.7% | -2.3% | +1.7% |
| Pakistan | 100.0% | -2.06m m3 | 0 | 0.0% | -93.7% | -93.7% |
| Taiwan | 37.3% | -3.48m m3 | +0.24m m3 | 6.9% | -34.7% | -35.5% |

India and Bangladesh combine lost Gulf-origin capacity with much higher
capacity-distance per retained supply, which is the clearest descriptive
signature of the proposed fleet-distance mechanism. Pakistan instead shows
near-complete loss with no observed non-Gulf offset. These are heterogeneous
exposure patterns, not estimates of unmet demand.

## Coverage and limitations

- The table contains 971 pre and 746 post resolved voyages across 37 destination
  countries and three market basins.
- Expanded route coverage is 97.6% pre and 97.3% post.
- No destination country or basin is missing.
- Only 145 pre and two post voyages meet the modeled Hormuz-crossing definition.
- Nominal vessel capacity is not loaded cargo volume. Terminal sequences may
  still reflect partial cargoes, reloads, floating storage, or AIS omissions.
- The descriptive offset ratio is a composition calculation. It must not be
  described as a causal substitution rate.

Industry context for regional LNG-market framing: International Gas Union,
2025 World LNG Report: https://www.igu.org/igu-reports/2025-world-lng-report
