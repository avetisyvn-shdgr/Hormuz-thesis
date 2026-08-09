# Bloomberg LNG Data Extraction Checklist

**Purpose:** determine whether the Bloomberg terminal provides usable LNG
freight histories for the thesis and, secondarily, obtain TTF and JKM energy
controls. Screenshots and current quotes are evidence of possible availability,
not a reproducible dataset.

## 1. Search the LNG freight catalogue

Open:

**Freight → Seaborne → Wet → LNG Tanker**

Search for the following series in priority order:

| Priority | Series | Required specification | Thesis role |
|---|---|---|---|
| 1 | Spark30S | Sabine Pass → Gate; 174,000 m³; two-stroke; USD/day | Preferred Atlantic freight outcome |
| 1 | Spark25S | North West Shelf → Tianjin; 174,000 m³; two-stroke; USD/day | Preferred Pacific freight outcome |
| 2 | BLNG1-174, BLNG2-174, BLNG3-174 | Baltic LNG route assessments; 174,000 m³ | Alternative freight evidence; not an automatic substitute for Spark |
| 3 | Atlantic and Asia-Pacific LNG carrier day rates | Record the precise route, vessel basis, methodology, and provider | Secondary freight evidence |
| 4 | TTF day-ahead and Platts JKM | Preserve native assessment definitions and units | Energy-price controls, not freight outcomes |

Do not treat oil-tanker rates, including VLCC Arab Gulf–China rates, as LNG
freight substitutes.

## 2. Record metadata for every candidate

- [ ] Exact Bloomberg ticker or security identifier
- [ ] Full series description
- [ ] Original assessment provider, such as Spark, Baltic, Platts, or Bloomberg
- [ ] Route and geographical coverage
- [ ] Vessel size and propulsion basis
- [ ] Unit and currency
- [ ] Frequency: daily, weekly, or another frequency
- [ ] Official price field used, such as the assessment or last-price field
- [ ] Earliest and latest accessible observation
- [ ] Publication time and timezone, if available
- [ ] Missing-value convention
- [ ] Whether the TUM licence permits historical export
- [ ] Whether the data may be used for thesis modelling
- [ ] Whether raw values or derived statistics may be published or retained

If a row has no current value, do not assume the series is unavailable. Open its
historical view and distinguish among missing observations, absent entitlement,
and an inactive series.

## 3. Export requirements

For each usable series:

- [ ] Export the native history from **2022-01-01 through at least 2026-07-07**.
- [ ] Preserve the original dates, values, currency, and units.
- [ ] Preserve missing observations.
- [ ] Do not interpolate, backfill, smooth, seasonally adjust, or average providers.
- [ ] Do not apply terminal-side currency or unit conversions.
- [ ] Export one consistently defined provider series rather than joining two
      similarly named assessments.
- [ ] Save the untouched original as CSV or XLSX.
- [ ] Save or photograph the accompanying Bloomberg metadata page.
- [ ] Record the terminal extraction date and the person performing the export.

The thesis analysis uses the fixed operational-onset cutoff **2026-02-28**.
Training must remain strictly before this date. Exporting more recent data does
not authorize changing that cutoff or the frozen analysis window.

## 4. Series-specific cautions

### Spark25S and Spark30S

These are the preferred downstream LNG freight assessments. Their availability
matters more than the number of generic LNG-related results returned by the
terminal. Both series must pass the documented coverage and licence checks
before activation.

### Baltic LNG benchmarks

These are separate market assessments, not aliases for Spark. They may be used
only after confirming a consistent definition, adequate history, acceptable
missingness, reproducible extraction, and publication rights. Do not silently
replace Spark with a Baltic series.

### TTF

The screenshot shows a Netherlands TTF **forward day-ahead** quote from more than
one Bloomberg source. Do not combine or average these sources. Preserve the exact
instrument definition and do not relabel a day-ahead assessment as physical spot.

### JKM

The visible “Platts LNG Japan/Korea Spot Cargo” entry is an LNG cargo-price
assessment, not a freight rate. A blank current value may reflect entitlement or
coverage limitations; historical access must be tested directly.

### Henry Hub and Brent

Do not spend Bloomberg extraction capacity on these unless needed for a licensed
cross-check. Authoritative free EIA versions are already integrated into the
project.

## 5. Governance and integration

- [ ] Do not transcribe screenshot values into the analytical dataset.
- [ ] Do not commit licensed raw prices to Git unless the licence explicitly
      permits it.
- [ ] Keep the original export unchanged and retain extraction metadata.
- [ ] Route any adopted external series through `registry.get_variable()` so its
      provenance is logged.
- [ ] Do not add a new series directly inside a notebook or modelling script.
- [ ] Do not change the locked PortWatch working primary merely because a price
      control becomes available.
- [ ] Activate freight only as a documented optional secondary outcome after the
      re-entry gate is satisfied.

## 6. Decision after extraction

| Result | Decision |
|---|---|
| Spark25S and Spark30S have adequate history and usable thesis rights | Run the documented secondary-outcome re-entry process |
| Only a Baltic or another LNG freight assessment is available | Evaluate it against the pre-declared coverage and missingness criteria; record any substitution as a methodological decision |
| Only TTF and/or JKM are available | Retain them as potential energy controls; do not claim that the freight-data gap is solved |
| Only current values or screenshots are available | Record access as insufficient and continue the accepted PortWatch integration plan |
| Export or thesis use is prohibited | Record the restriction; do not retain or analyse prohibited raw data |

## 7. Files to return for integration

- [ ] Original CSV/XLSX export for each series
- [ ] Metadata screenshot or exported description page
- [ ] Exact Bloomberg identifiers
- [ ] Written or photographed licence/export guidance
- [ ] Short note describing any entitlement errors or truncated history

After these files are available, coverage, frequency, missingness, and treatment-
window compatibility must be verified before any model is run.

## Project references

- `docs/SPARK_REENTRY.md`
- `docs/DATA_ACCESS_CHECKLIST.md`
- `docs/CURRENT_PLAN.md`
- `docs/DATA_SOURCES.md`
- `config/sources.yaml`
- `config/settings.yaml`
