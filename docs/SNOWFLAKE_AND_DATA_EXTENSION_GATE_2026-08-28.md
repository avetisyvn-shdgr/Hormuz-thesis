# Snowflake and data-extension gate — 2026-08-28

## Decision

Snowflake is a usable delivery mechanism, but the free Marketplace shares do not
restore the proposal's proprietary dependent variable or observed laden
ton-miles. The repository must therefore keep the current PortWatch working
primary unless a licensed source passes the historical-coverage and publication
rights gates below.

No source in this document is admitted into `config/sources.yaml` merely because
it appears here. Admission still requires a frozen snapshot, schema check,
licence note, hash/provenance record, temporal-coverage check, and explicit
estimand role.

## Snowflake audit

| Product | Accessible coverage found | Decision |
|---|---:|---|
| Lloyd's List SeaOrbis standalone sample | 2 AIS rows | Reject as a time-series input |
| Lloyd's List Hormuz conflict sample | 1,162,821 pre messages / 6,641 identified vessels and 426,173 post messages / 2,821 identified vessels; two one-hour snapshots only | Retain as a descriptive pre/post vessel-presence cross-check |
| Energy Aspects `CARGO_TRACKING_FOR_LNG` | 35 cargo rows, 2023-12-02 to 2023-12-31; no study-window observations | Reject as a 2026 input |
| Kpler free LNG sample | Static September 2021 sample | Reject as a 2026 input |
| Platts Market Data — LNG / Shipping | Request-only; advertises JKM, LNG carrier day rates, route costs, voyage data and freight assessments | Highest-priority Snowflake access request; verify exact symbols, vessel basis, coverage and thesis rights |

The reproducible full-snapshot query is
`scripts/snowflake_hormuz_timeline_extract.sql`. It removes the arbitrary
`LIMIT 100`, filters the exact licensed snapshot windows, excludes null vessel
identifiers and returns one row per vessel per snapshot. Its verified result is
9,462 rows: 6,641 pre-onset and 2,821 post-onset.

## Ranked additions

### A. Highest-value licensed requests

1. **Spark Commodities — Spark25S/Spark30S.** This is the exact pre-committed
   target. The official API supports daily historical price releases and the
   `174-2stroke` vessel basis, but unlimited history requires Premium access.
   Request 2022-01-01 through latest, methodology, revisions and permission to
   publish derived coefficients while keeping raw prices private.
2. **Baltic Exchange — BLNG1-174/BLNG2-174/BLNG3-174.** Daily LNG route
   assessments for 174,000-cbm vessels. The 174 series began live reporting on
   2023-12-15, so it supplies a substantial but shorter pre-period than the
   preferred 2022 start. Request API/export and academic non-display rights.
3. **Kpler Freight Analytics / Cargo Analytics.** The official product describes
   ton-miles, distance, speed and laden/ballast splits with more than five years
   of history, alongside load/discharge location and cargo-volume information.
   This is the strongest single candidate for replacing modelled
   capacity-distance with a closer observed/estimated cargo-voyage mechanism.
4. **Spire Historical Vessel Points/Tracks.** Best candidate for observed sailed
   distance and waiting time for the frozen IMO roster. It does not supply cargo
   mass by itself and raw AIS redistribution is likely restricted.
5. **Platts LNG and Shipping through Snowflake.** Potentially covers JKM,
   Atlantic/Asia-Pacific day rates, ballast rates and voyages. Do not use a
   Platts route-cost series as independent evidence that distance causes price;
   that would be mechanically circular.

### B. Free additions worth a formal admission probe

| Source | Frequency / coverage | Legitimate thesis role | Main limitation |
|---|---|---|---|
| GIE ALSI | Daily LNG inventory and terminal send-out; historical data since 2012 or terminal start | Independent European discharge-side validation and terminal congestion/storage response | Facility reporting and revisions; does not identify cargo origin or freight price |
| ENTSOG Transparency Platform | Public REST API, daily/hourly operational gas flows at network and LNG-entry points | Validate whether LNG arrivals translated into European network entry; add terminal/network propagation layer | Point mapping and missing/not-applicable flags require careful QA |
| Caldara–Iacoviello Daily GPR | Daily, weekly-updated recent geopolitical-risk index | Broad geopolitical-news context or robustness plot | Media-observation index, not maritime war-risk premium; revised after publication |
| ACCC LNG netback | Monthly historical Asian LNG-linked netback from 2016 plus forward series; current through the 2026 window | Public Asian LNG price-context appendix | Derived from Asian LNG prices and freight assumptions; too circular and low-frequency for the freight equation |
| ACLED conflict events | Geolocated event API with account/OAuth | Descriptive conflict-intensity/event chronology around Gulf countries | Reporting lag and media bias; never a treatment selector or causal control added after seeing outcomes |
| IMO GISIS piracy/armed-robbery incidents | Incident-level reports | Maritime-security corroboration | Registration and incident under-reporting; not an insurance-premium series |

### C. Explicit non-solutions

- **NOAA/BOEM MarineCadastre AIS** currently exposes data only through 2025, so
  it cannot observe the 2026 event.
- **World Bank Pink Sheet** provides useful monthly commodity context, not JKM,
  TTF or LNG freight at the frequency required for the primary model.
- **ACLED, GPR, UKMTO and IMO incidents** cannot substitute for Lloyd's war-risk
  additional premiums.
- Increasing a SQL `LIMIT` cannot create dates absent from a provider's secure
  share. Coverage must be checked with `MIN(date)`, `MAX(date)` and in-window row
  counts before extraction.

## Admission order

1. Probe **GIE ALSI** and **ENTSOG** schemas and exact 2022-01-01 to 2026-07-07
   coverage without changing the locked primary model.
2. Freeze the **Daily GPR** vintage as a context-only series if its licence and
   study-window coverage pass.
3. Request **Spark**, **Baltic**, **Kpler/Spire**, and **Platts** in parallel,
   using the same academic-rights language already defined in
   `DATA_SOURCE_DEEP_DIVE.md`.
4. Promote nothing until the data licence permits thesis-derived figures and
   coefficients, the raw data can be retained privately for examination, and a
   chronological leakage audit passes.

## Official references checked on 2026-08-28

- Spark API: https://www.sparkcommodities.com/api/lng-freight/contracts.html
- Baltic Gas services: https://www.balticexchange.com/en/data-services/market-information0/gas-services.html
- Baltic 174-cbm launch notice: https://www.balticexchange.com/en/data-services/Circulars/market-announcements-/category-a/2023/circular-35-23---new-index--blng1-174--blng2-174--blng3-174-goes.html
- Kpler Freight Analytics: https://www.kpler.com/product/commodities/freight-analytics
- Kpler Cargo Analytics: https://www.kpler.com/product/commodities/cargo-analytics
- Spire historical tracks: https://documentation.spire.com/historical-vessel-points-and-tracks-hvp-hvt/
- GIE ALSI: https://www.gie.eu/agsi-and-alsi-transparency-platforms/
- ENTSOG API documentation: https://transparency.entsog.eu/pdf/TP_REG715_Documentation_TP_API_v1.3.pdf
- Daily GPR: https://www.matteoiacoviello.com/gpr.htm
- ACCC LNG netback: https://www.accc.gov.au/inquiries-and-consultations/gas-inquiry-2017-30/lng-netback-price-series
- ACLED API: https://acleddata.com/acled-api-documentation
- IMO GISIS: https://gisis.imo.org/Public/Default.aspx
- MarineCadastre AccessAIS: https://marinecadastre.gov/accessais/
