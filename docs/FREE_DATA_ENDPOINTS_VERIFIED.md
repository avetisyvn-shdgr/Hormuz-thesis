# Verified free endpoints — the foundational data layer

**All tests run 2026-07-21/22, read-only, one small request each. No bulk download, no registration, no authentication bypass.**
Companion to `DATA_SOURCE_DEEP_DIVE.md`. Where this file and the deep dive disagree, **this file supersedes it** — the tests here are live and specific.

Status legend: **PASS** = endpoint returned usable data anonymously · **KEY** = endpoint reachable, free key required · **GAP** = endpoint exists but does not cover the study window.

---

## Summary

| # | Source | Status | Covers 2026-02-28? | Key needed |
|---|---|---|---|---|
| 1 | IMF PortWatch — daily chokepoints | **PASS** | Yes (to 2026-07-19) | No |
| 2 | IMF PortWatch — chokepoint reference | **PASS** | n/a (static) | No |
| 3 | WTO/AXSMarine Hormuz LNG index | **PASS** | Yes | No |
| 4 | Eurostat `nrg_ti_gasm` | **PASS** | Yes (to 2026-06) | No |
| 5 | ENTSOG operational data | **PASS** | Yes | No |
| 6 | GIE ALSI (LNG terminals) | **KEY** | Expected yes | Free, mandatory |
| 7 | EIA Open Data v2 | **KEY** | Yes | Free, instant |
| 8 | Global Fishing Watch v3 | **KEY** | Yes | Free token |
| 9 | NOAA/BOEM MarineCadastre AIS | **GAP** | **No — 2026 not published** | No |
| 10 | ACCC LNG netback | PASS (link only) | Yes | No |

---

## 1. IMF PortWatch — daily chokepoint transits ✅ PASS

The deep dive pointed at the *chokepoint reference* layer. The **daily time series lives in a different service**, found by enumerating the IMF feature server. This is the correct one:

```
https://services9.arcgis.com/weJ1QsnbMYJlCHdG/ArcGIS/rest/services/Daily_Chokepoints_Data/FeatureServer/0
```

**Layer metadata** (`?f=pjson`) — returned HTTP 200:
- Type `Table`, `capabilities: "Query"`, `maxRecordCount: 1000`, `standardMaxRecordCount: 32000`
- `supportedExportFormats`: `csv, shapefile, sqlite, geoPackage, filegdb, featureCollection, geojson, kml, excel`
- **Fields (21):** `date` (dateOnly), `year`, `month`, `day`, `portid`, `portname`, `n_container`, `n_dry_bulk`, `n_general_cargo`, `n_roro`, **`n_tanker`**, `n_cargo`, `n_total`, `capacity_container`, `capacity_dry_bulk`, `capacity_general_cargo`, `capacity_roro`, **`capacity_tanker`**, `capacity_cargo`, `capacity`, `ObjectId`

`n_tanker` and `capacity_tanker` are exactly the two fields `config/sources.yaml` pins for `hormuz_tanker_transits` and `hormuz_tanker_capacity`.

**Row count** — returned `{"count":76412}`:
```
.../Daily_Chokepoints_Data/FeatureServer/0/query?where=1%3D1&returnCountOnly=true&f=json
```

**Latest date** — returned `2026-07-19`:
```
.../Daily_Chokepoints_Data/FeatureServer/0/query?where=1%3D1&outFields=date&orderByFields=date%20DESC&resultRecordCount=1&f=json
```

**Practical retrieval.** `maxRecordCount` is 1000 against 76,412 rows, so a full pull needs pagination via `resultOffset`. Filter server-side to one chokepoint first:

```
.../FeatureServer/0/query
  ?where=portname='Strait of Hormuz' AND date>=DATE '2022-01-01'
  &outFields=date,portname,n_tanker,capacity_tanker,n_total,capacity
  &orderByFields=date ASC
  &resultOffset=0&resultRecordCount=1000
  &f=json
```
Then increment `resultOffset` by 1000 until `exceededTransferLimit` is absent. CSV comes from the same query with `&f=csv`.

**This replaces the manual snapshot.** `config/settings.yaml` currently notes "no stable public API endpoint pinned yet" for `portwatch_csv`. There is one. Moving from a hand-downloaded CSV to this query would make the PortWatch pull reproducible — but it is a registry change and belongs in `registry.get_variable()`, not in ad-hoc code.

> **Caveat unchanged:** still aggregate, still no LNG class, still no vessel identity or laden/ballast.

**Reference layer** (28 chokepoints, coordinates, shares) — also PASS:
```
https://services9.arcgis.com/weJ1QsnbMYJlCHdG/ArcGIS/rest/services/PortWatch_chokepoints_database/FeatureServer/0?f=pjson
```

Landing pages: https://portwatch.imf.org/pages/data-and-methodology · https://portwatch.imf.org/datasets/42132aa4e2fc4d41bdaf9a445f688931_0/about

---

## 2. WTO / AXSMarine Strait of Hormuz LNG index ✅ PASS

```
https://wtomais.blob.core.windows.net/strait-of-hormuz-tracker/voy_intake_index_lng_export.csv
```
HTTP 200, body returned, no key. LNG-only outbound shipment-volume index, 2025 average = 100, LPG excluded. Already integrated as `wto_hormuz_lng_outbound_index`. Only 423 pre-onset days, and **not independent of Signal Ocean/AXSMarine**.

---

## 3. Eurostat `nrg_ti_gasm` ✅ PASS

Live JSON-stat, no key. LNG is `siec=G3200`:

```
https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/nrg_ti_gasm?format=JSON&lang=EN&siec=G3200&partner=QA&geo=EU27_2020&lastTimePeriod=3
```

Verified from the response's own metadata:
- `OBS_PERIOD_OVERALL_OLDEST`: **2008-01** · `OBS_PERIOD_OVERALL_LATEST`: **2026-06**
- `UPDATE_DATA`: **2026-07-21T11:00** (refreshed the day before this test)
- `siec` `G3200` = "Liquefied natural gas"; units `MIO_M3` (million m³) and `TJ_GCV`
- DOI `10.2908/NRG_TI_GASM`

Swap `partner=` for any exporter (`QA`, `US`, `DZ`, `RU`, `NG`…), `geo=` for any member state, and drop `lastTimePeriod` for `sinceTimePeriod=2022-01`. **This gives 2008 onward — a far longer pre-period than the 2022 study window requires**, which is useful for seasonality baselines.

> Observation worth flagging, not interpreting: for `partner=QA`, `geo=EU27_2020`, the returned values for **2026-04 and 2026-05 are both 0.000** (2026-06 is flagged no-data). That is consistent with a Gulf supply halt, but Eurostat zeros can also be suppression or reporting lag. Verify against the national customs snapshots before it goes anywhere near a figure.

---

## 4. ENTSOG Transparency Platform ✅ PASS

```
https://transparency.entsog.eu/api/v1/operationaldata.json?limit=1
```
HTTP 200, JSON, **no API key**. 34 fields returned including `indicator`, `periodType`, `periodFrom`, `periodTo`, `operatorKey`, `pointKey`, `pointLabel`, `directionKey`, `unit` (kWh/d), `value`, `flowStatus`, `isNA`. Also serves CSV and XLSX via the same base. Useful for isolating LNG terminal entry points into the EU network.

Caveat: the sample row came back with an empty `value` and `isNA: 1` — null density is high, so filter on `isNA=0` and a specific `pointKey`.

---

## 5. GIE ALSI — LNG terminal send-out and inventory 🔑 KEY (licence now verified)

```
https://alsi.gie.eu/api          (LNG terminals — the one you want)
https://agsi.gie.eu/api          (gas storage — sibling)
```
Anonymous request returned HTTP 200 with:
`{"dataset":"storage ERROR","error":"access denied","message":"Invalid or missing API key"}`

**Registration:** https://alsi.gie.eu/account — the GIE page states the API "is made available to the public **free of charge**", that "**Registration is mandatory**" and yields a personal API key, that the export format is JSON, and that documentation is provided after registration.

**Licence — this is the important part, and it is now verified rather than assumed:**
> "All data published on AGSI & ALSI can be used or repackaged in any way you see fit but a clear indication on GIE as data source is mandatory… If no credit or source is mentioned, GIE can disable / de-activate your API access key."

That is an unusually clean permission for a thesis: repackaging and derived publication are explicitly allowed, with attribution as the only condition. **This is the best licensing position of any LNG-specific source in the whole scan.**

Daily, LNG-specific, discharge-side. Gives an independent check on the European arrivals your capacity-nautical-mile reconstruction infers.

---

## 6. EIA Open Data v2 🔑 KEY

Free instant key: https://www.eia.gov/opendata/register.php

The v2 API keeps a **v1 series-ID compatibility route**, confirmed verbatim in EIA's own documentation (https://www.eia.gov/opendata/documentation.php):
```
https://api.eia.gov/v2/seriesid/ELEC.SALES.CO-RES.A?api_key=xxxxxx
```

So the two series already in `config/sources.yaml` are reachable unchanged:
```
https://api.eia.gov/v2/seriesid/NG.RNGWHHD.D?api_key=YOUR_KEY     # Henry Hub spot, USD/MMBtu, daily
https://api.eia.gov/v2/seriesid/PET.RBRTE.D?api_key=YOUR_KEY      # Brent spot, USD/bbl, daily
```
Native v2 form is `/v2/{route}/data/?api_key=…&data[0]=value&facets[series][]=…&frequency=daily&start=&end=`. Anonymous calls return nothing useful, so the key is required before any test — the project already holds one.

---

## 7. Global Fishing Watch v3 🔑 KEY

```
https://gateway.api.globalfishingwatch.org/v3/vessels/search
https://gateway.api.globalfishingwatch.org/v3/datasets
```
Both returned an **empty body unauthenticated** — consistent with the documented bearer-token requirement. Free token: https://globalfishingwatch.org/our-apis/tokens. Already integrated; no change needed.

---

## 8. NOAA/BOEM MarineCadastre AIS ⛔ GAP — this is the finding that matters

The deep dive ranked this the highest-value new free source. **That recommendation is now downgraded, and here is exactly why.**

**2025 is complete and beautifully structured.** `https://coast.noaa.gov/htdata/CMSP/AISDataHandler/2025/index.html` returned HTTP 200 listing **all 365 daily files** in a stable, fully predictable pattern:
```
https://coast.noaa.gov/htdata/CMSP/AISDataHandler/2025/ais-2025-01-01.csv.zst
https://coast.noaa.gov/htdata/CMSP/AISDataHandler/2025/ais-YYYY-MM-DD.csv.zst
```
The page states the year totals **81.5 GB** and was last updated **2026-03-05**.

**2026 is not published.** Both of these returned empty:
```
https://coast.noaa.gov/htdata/CMSP/AISDataHandler/2026/index.html
https://coast.noaa.gov/htdata/CMSP/AISDataHandler/2026/
```

The 2025 files appear to have been posted around March 2026 — roughly a one-year lag. **So MarineCadastre cannot currently see 2026-02-28.** It cannot serve the mechanism variable for the event window at all right now.

What it *can* do today: give you genuinely **observed** AIS positions for US Gulf liquefaction terminals across 2022–2025, which is enough to **validate the modelled-route method against observed tracks in the pre-period**, and to quantify how much error the `modelled_route` assumption introduces. That is a real methodological contribution — it converts an untested assumption into a measured one — but it is a *validation* use, not the mechanism measurement.

Re-check the 2026 directory around Q1 2027, or before any analysis freeze.

Landing pages: https://marinecadastre.gov/accessais/ · https://hub.marinecadastre.gov/pages/vesseltraffic

---

## 9. ACCC LNG netback ✅ link live

```
https://www.accc.gov.au/system/files/LNG%20netback%20price%20series%20-%20Public%20version%20-%201%20July%202026.xlsx
```
Present on the official page (modified 2026-07-01); file not downloaded. **The filename contains the release date, so the URL is not stable** — any fetcher must scrape the current link from https://www.accc.gov.au/inquiries-and-consultations/gas-inquiry-2017-30/lng-netback-price-series rather than hard-code it. Partially circular with any JKM-based control.

---

## What changed versus the deep dive

| Item | Deep dive said | Now verified |
|---|---|---|
| PortWatch daily series | reference layer URL only | correct `Daily_Chokepoints_Data` service, 76,412 rows, to 2026-07-19, paginated query pattern |
| Eurostat history | "monthly, to 2026-06" | **2008-01 → 2026-06**, updated 2026-07-21, LNG = `siec=G3200` |
| GIE ALSI licence | `UNVERIFIED` | **verified: free, attribution-only, repackaging explicitly permitted** |
| MarineCadastre | "best new free source", 2026 `UNVERIFIED` | **2026 not published — cannot cover the event window** |
| EIA v2 access path | generic `/v2/...` | **`/v2/seriesid/{v1_id}` compatibility route confirmed in EIA docs** |

**Revised free-data ranking:** PortWatch (reproducible now) → GIE ALSI (best licence, LNG-specific, daily) → Eurostat (longest history) → WTO index → ENTSOG. MarineCadastre drops to a pre-period validation tool until 2026 lands.

**Nothing here changes the price gap.** Every endpoint above is a volume, flow or transit measure. There is still no free structured source for a USD/day LNG freight rate covering 2026-02-28.

---

## Integration note

None of these were wired into the pipeline. Per `AGENTS.md` rule 7, any adoption goes through `config/sources.yaml` + `registry.get_variable()` as a documented decision — in particular, replacing the manual `portwatch_csv` snapshot with the live query is a registry change, not a code change.
