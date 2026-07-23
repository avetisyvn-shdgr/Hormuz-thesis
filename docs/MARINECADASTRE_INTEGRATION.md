# MarineCadastre AIS — integration guide

**Verified 2026-07-22.** Endpoints below were fetched live. Licence text and file
listings are quoted from NOAA's own pages.

---

## (a) Methodological justification

The mechanism measure is currently `vessel capacity (m³) × modelled route distance`.
The distance term is a model output that has **never been checked against an
observed track**. `INFERRED_CAPACITY_NAUTICAL_MILES_RESULTS.md` reports a
Kitagawa/Oaxaca decomposition in which the within-pair term is near zero *by
construction*, because modelled distance is fixed within a terminal pair. That is
an assumption doing analytical work, unverified.

MarineCadastre gives observed AIS tracks for US waters under CC0. Comparing
modelled distance against observed track length for US Gulf departures converts
that assumption into a **measured error term with a distribution**. That is a
robustness section you can currently write for no money and no permissions.

It does **not** produce a new outcome variable, and it does not extend the
mechanism to the event window. See (c).

## (b) Data requirement

- Your frozen 624-IMO carrier frame (`data/interim/global_lng_carrier_frame.csv`)
- Your terminal dictionary (`data/raw/gem/global_lng_terminals.csv`) for US Gulf sites
- Your existing GFW port-visit artifacts, to select *which* dates to pull
- Disk: 1.0–1.8 GB per month pulled; ~16 GB for all of 2025

## (c) Expected limitations — state these before anyone gets excited

1. **No 2026.** Track files stop at `ais-track-2025-12.parquet`. The 2025 files were
   posted 2026-04-03, so the lag is roughly a year. **This cannot see 2026-02-28.**
   It is a pre-period validation instrument, not event-window evidence.
2. **US waters only.** You observe the departure leg inside the US EEZ, not the
   ocean crossing. Validation covers the first few hundred nautical miles of a
   voyage, so it bounds near-terminal route error — it does not validate the
   great-circle/route-network portion, which is most of the distance.
3. **Tracks are downsampled to the whole minute** and cleaned of sentinel values;
   track length is therefore itself a reconstruction, though a far better one than
   a modelled route.
4. **No cargo mass, no laden/ballast flag.** Nothing here moves you toward observed
   cargo ton-miles.
5. Identity resolution still depends on IMO being broadcast correctly; MMSI is
   mutable and must not be the join key.

## (d) Next practical action

Run the schema probe in step 1. It downloads a few KB, not a gigabyte. Decide
after seeing the columns.

---

## The data

**Licence: CC0 1.0 Universal public domain dedication.** No attribution required,
no redistribution restriction, derived publication unrestricted. This is the most
permissive licence of any source in the whole scan.

**Citation (from NOAA's readme):** Martin, Daniel R., Jesse Brass, Matthew Dornback,
and Jeremy Fontenault. 2026. *Nationwide Automatic Identification System 2024.*
NOAA Office for Coastal Management.

### Option A — monthly vessel **tracks** (recommended)

Pre-built LineString geometries. GeoParquet 1.1.0, ZSTD, WKB LineString, WGS84,
UTC, minute-downsampled. This is what you want: you need *track length*, not points.

```
https://ocmgeodatastor1.blob.core.windows.net/marinecadastre/aistrack/ais-track-YYYY-MM.parquet
```

Verified index (all posted 2026-04-03):
`ais-track-2024-01` … `ais-track-2024-12`, `ais-track-2025-01` … `ais-track-2025-12`.
Sizes 1.01–1.78 GB. Index page:
https://ocmgeodatastor1.blob.core.windows.net/marinecadastre/aistrack/index-aistrack.html

**Coverage: 2024-01 through 2025-12 only.**

### Option B — daily broadcast points (2015–2025)

```
https://coast.noaa.gov/htdata/CMSP/AISDataHandler/2025/ais-2025-03-14.csv.zst
```
Pattern `ais-YYYY-MM-DD.csv.zst`, one file per day, all 365 days present for 2025;
the year totals 81.5 GB. Index: `.../AISDataHandler/2025/index.html`.
`.../2026/` returns nothing — confirmed twice.

Use this only for 2022–2023, where no track files exist. For validation purposes
2024–2025 is sufficient, so you probably never need it.

### Option C — AccessAIS custom order

https://marinecadastre.gov/accessais/ — map-driven, pick an area and timeframe,
≤2 GB per order, zipped CSV. Convenient but **interactive and not reproducible**,
which conflicts with the provenance rules. Use it once to eyeball the data, not as
the ingestion path.

---

## Step 1 — schema probe (do this first, costs a few KB)

DuckDB reads the Parquet footer over HTTP range requests without downloading the
file.

```bash
pip install duckdb --break-system-packages
```

```python
import duckdb

con = duckdb.connect()
con.execute("INSTALL httpfs; LOAD httpfs; INSTALL spatial; LOAD spatial;")

URL = ("https://ocmgeodatastor1.blob.core.windows.net/marinecadastre/"
       "aistrack/ais-track-2025-03.parquet")

print(con.execute(f"DESCRIBE SELECT * FROM read_parquet('{URL}')").fetchdf())
print(con.execute(f"SELECT count(*) FROM read_parquet('{URL}')").fetchone())
```

The exact column names are **not documented in NOAA's readme** — the readme
specifies only the geometry type and encoding. Do not assume `IMO`, `MMSI`,
`VesselType` etc. exist under those names. Read the schema, then write the filter.

## Step 2 — pull only what you need

Never download a whole month into the repo. Filter server-side on the IMO roster
and a US Gulf bounding box, and persist only the result.

```python
import duckdb, pandas as pd

roster = pd.read_csv("data/interim/global_lng_carrier_frame.csv")
imos = tuple(str(i) for i in roster["imo"].dropna().unique())   # check the column name

con = duckdb.connect()
con.execute("INSTALL httpfs; LOAD httpfs; INSTALL spatial; LOAD spatial;")
con.register("roster_imos", pd.DataFrame({"imo": imos}))

URL = ("https://ocmgeodatastor1.blob.core.windows.net/marinecadastre/"
       "aistrack/ais-track-2025-03.parquet")

# NOTE: replace <IMO_COL> and <GEOM_COL> with the real names from Step 1.
q = f"""
SELECT t.*, ST_Length_Spheroid(t.<GEOM_COL>) AS track_len_m
FROM read_parquet('{URL}') t
JOIN roster_imos r ON CAST(t.<IMO_COL> AS VARCHAR) = r.imo
WHERE ST_XMin(t.<GEOM_COL>) BETWEEN -98.0 AND -87.5
  AND ST_YMin(t.<GEOM_COL>) BETWEEN  25.5 AND  30.6
"""
df = con.execute(q).fetchdf()
```

The bounding box is a starting rectangle for the US Gulf liquefaction cluster
(Sabine Pass, Corpus Christi, Cameron, Freeport, Calcasieu Pass, Golden Pass,
Plaquemines). **Replace it with a box derived from your own terminal dictionary**
rather than trusting these numbers.

Convert metres to nautical miles with `/ 1852.0`.

## Step 3 — choose months, not years

Do not sweep 24 months. Use the GFW port-visit artifacts you already have to find
dates when roster vessels departed US Gulf terminals, then pull only those months.
Three or four well-chosen months across 2024–2025 give you enough paired
observations for an error distribution.

## Step 4 — the actual comparison

For each matched departure:

| Quantity | Source |
|---|---|
| `modelled_nm` | `data/processed/maritime_route_distances.csv`, truncated to the US-EEZ segment |
| `observed_nm` | `track_len_m / 1852.0` from Step 2 |
| `error` | `observed_nm − modelled_nm` |

Report the distribution of the relative error, not a single ratio. The honest
headline is something like: *"across N matched US Gulf departure legs, modelled
route distance deviates from observed AIS track length by a median of X% (IQR
Y–Z%), bounding the near-terminal component of route-model error."*

Do **not** rescale the main capacity-nautical-mile results by this factor. It is
measured on one leg of the voyage in one basin in a different period. It bounds an
error; it does not correct one.

---

## Step 5 — wiring it in properly

Per `AGENTS.md` rule 7, no ad-hoc `requests.get` in analysis code. The path is:

1. Add `src/lngfreight/sources/marinecadastre.py` following the existing provider
   contract in `sources/base.py` (see `portwatch.py` and `gfw.py` as models).
2. Register it in `sources/__init__.py::get_provider`.
3. Add a `config/sources.yaml` entry — role `mechanism`, status `free`,
   licence `"CC0 1.0 Universal (NOAA Office for Coastal Management)"`.
4. Add paths to `config/settings.yaml` under `paths:`.
5. Raw pulls land in `data/raw/` with a `provenance.jsonl` entry, as everything else
   does.

Suggested registry entry — **this is a proposal, not a committed change**:

```yaml
  usgulf_observed_track_nm:
    role: mechanism
    description: "Observed AIS track length for roster LNG carriers departing US Gulf terminals (US EEZ segment only, 2024-2025)."
    status: free
    primary:
      provider: marinecadastre
      code: "aistrack:usgulf"
      license: "CC0 1.0 Universal public domain dedication (NOAA OCM)"
      note: "US waters only; 2024-01 to 2025-12; no 2026 coverage. Validation of modelled route distance ONLY - not an event-window mechanism measure and not cargo ton-miles."
```

Keep the `note` field. It is the thing that stops this being misread later as
observed voyage distance for the disruption.

---

## Sources

- https://github.com/ocm-marinecadastre/ais-vessel-traffic (licence, formats, paths)
- https://ocmgeodatastor1.blob.core.windows.net/marinecadastre/aistrack/index-aistrack.html (file index)
- https://raw.githubusercontent.com/ocm-marinecadastre/ais-vessel-traffic/main/data/ais-tracks-2024-readme.md (format spec, citation, CC0)
- https://coast.noaa.gov/htdata/CMSP/AISDataHandler/2025/index.html (daily point files)
- https://marinecadastre.gov/accessais/ · https://hub.marinecadastre.gov/pages/vesseltraffic
- Support: MarineCadastre@noaa.gov
