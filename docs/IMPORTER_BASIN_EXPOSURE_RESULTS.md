# Importer and basin exposure results

**Status:** Verified locally and covered by the current full suite.
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

Country-level Hormuz-exposed changes are **not estimable** in this snapshot.
Only two post-period voyages meet the modeled crossing definition across all
countries, below the pre-specified minimum of five post voyages per country.
Accordingly, all 39 country rows retain sample-size and total-flow diagnostics
but suppress the exposed-capacity change, percent change, and offset ratio. No
country ranking or country-specific mechanism claim should be reported.

## Coverage and limitations

- The table contains 971 pre and 746 post resolved voyages across 37 destination
  countries and three market basins.
- Expanded route coverage is 97.6% pre and 97.3% post.
- No destination country or basin is missing.
- Only 145 pre and two post voyages meet the modeled Hormuz-crossing definition;
  all country-level exposed estimates are therefore suppressed.
- Nominal vessel capacity is not loaded cargo volume. Terminal sequences may
  still reflect partial cargoes, reloads, floating storage, or AIS omissions.
- The descriptive offset ratio is a composition calculation. It must not be
  described as a causal substitution rate.
- Korea retains only the normalized table scrape, China retains portal-export
  CSVs without query receipts/terms capture, and India retains a parsed table
  capture rather than original HTTP responses. These historical source-artifact
  gaps limit independent auditability of the importer extension; they do not
  affect the PortWatch primary outcome. See `docs/DATA_SOURCES.md`.

Industry context for regional LNG-market framing: International Gas Union,
2025 World LNG Report: https://www.igu.org/igu-reports/2025-world-lng-report
