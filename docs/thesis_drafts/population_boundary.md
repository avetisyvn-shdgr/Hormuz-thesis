# DRAFT - Population boundary

This draft defines the descriptive network-rewiring population. Every empirical
number is cited to the artifact that supplies it.

The descriptive by-origin customs population consists of `5` importer cases plus
the `EU27` aggregate comparator (`data/processed/lng_rewiring_summary.csv`).
The importer cases are China, India, Japan, Korea, and Taiwan; EU27 is retained
for context and is not interpreted as a single importing country
(`data/processed/lng_rewiring_summary.csv`).

| Unit | Role | Observed post months | Monthly basis | Boundary note |
|---|---|---|---|---|
| China | importer | `3` (`data/processed/lng_rewiring_summary.csv`) | tonnes, `weight_ton` (`data/processed/lng_rewiring_summary.csv`) | strict origin-split national customs, weight basis (`data/processed/lng_rewiring_summary.csv`) |
| Korea | importer | `4` (`data/processed/lng_rewiring_summary.csv`) | tonnes, `weight_ton` (`data/processed/lng_rewiring_summary.csv`) | strict origin-split national customs, weight basis (`data/processed/lng_rewiring_summary.csv`) |
| Taiwan | importer | `4` (`data/processed/lng_rewiring_summary.csv`) | tonnes, `weight_ton` (`data/processed/lng_rewiring_summary.csv`) | strict origin-split national customs, weight basis (`data/processed/lng_rewiring_summary.csv`) |
| Japan | importer | `3` (`data/processed/lng_rewiring_summary.csv`) | tonnes, `weight_ton` (`data/processed/lng_rewiring_summary.csv`) | strict origin-split Japan Customs/e-Stat snapshot, weight basis (`data/processed/lng_rewiring_summary.csv`) |
| India | importer | `3` (`data/processed/lng_rewiring_summary.csv`) | `kUSD`, `value_kusd` (`data/processed/lng_rewiring_summary.csv`) | value-basis caution because Tradestat HS-6 monthly quantity is unpopulated (`data/processed/lng_rewiring_summary.csv`) |
| EU27 | aggregate comparator | `3` (`data/processed/lng_rewiring_summary.csv`) | `MIO_M3`, `volume_mio_m3` (`data/processed/lng_rewiring_summary.csv`) | origin-split Eurostat aggregate comparator, not a single importer (`data/processed/lng_rewiring_summary.csv`) |

This boundary is deliberately narrower than a confirmatory importer panel. The
current frozen public-data coverage admits `0` importers against the proposed
confirmatory rule requiring `15` importers, `12` contiguous pre-months, and `3`
post months (`data/processed/importer_source_coverage_summary.json`). Therefore
the network-rewiring table is a descriptive mechanism population, not an
admissible differential importer-panel estimand.
