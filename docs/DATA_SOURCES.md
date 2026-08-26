# Data Sources — The Bloomberg-Terminal Alternative

**Purpose.** This is the load-bearing document for the data-access (go/no-go) decision in the proposal. It maps every variable in the proposal's *minimum viable dataset* to a concrete source, states honestly what is free vs proprietary, and records what each source can and **cannot** capture. Nothing here asserts access rights that have not been verified.

Non-series external inputs use the same registry gate. Entries marked
`kind: artifact` preserve their native CSV, JSON, GeoJSON, or workbook schema;
`registry.get_variable()` verifies the frozen checksum and records the analysis
consumer before returning a `RegisteredArtifact`. An input cannot bypass source
status and provenance merely because it is not a one-dimensional time series.

**The honest headline.** There is **no free, like-for-like replacement** for your dependent variable. Spark25S / Spark30S are proprietary Spark Commodities assessments; JKM is a proprietary S&P Global Platts assessment. A "professional" alternative to Bloomberg is therefore *not* a scraper that imitates these series — it is (a) a clear-eyed registry of what each free source genuinely is, and (b) a software layer that lets you run the whole pipeline on free proxies now and swap in the proprietary feeds later by editing one config file. That layer is already built (`config/sources.yaml` + `src/lngfreight/`).

---

## Status legend

| status | meaning |
|---|---|
| **free** | A free series that *is* the real thing the proposal wants. No proprietary gap. |
| **proxy** | A free, *imperfect* stand-in carrying basis/timing risk. Must be documented as such. |
| **unavailable** | No adequate free option exists. Slot reserved for proprietary access. |
| **restricted** | Local checksum-pinned input available only through an explicit opt-in; provenance or licence metadata is incomplete, so it cannot enter the default pipeline. |

---

## Variable-by-variable

### Dependent variable — LNG spot freight

| Variable | What the proposal wants | Free reality | Status |
|---|---|---|---|
| `spark30s_atlantic_freight` | Spark30S daily spot assessment (Sabine Pass → Gate) | Spark publishes only **indicative** prices publicly; full daily data needs a Spark subscription. ICE lists Spark30S freight futures, but no verified accessible historical settlement feed is implemented. | unavailable |
| `spark25s_pacific_freight` | Spark25S daily spot assessment (NWS → Tianjin) | Same as above. | unavailable |

- **What the proxy captures:** broad direction and large moves in LNG freight cost.
- **What it cannot capture:** the *daily physical spot assessment itself*. A front-month future is a different instrument with its own roll, term structure and liquidity. Treating it as the spot series is a **measurement-validity assumption** that would have to be defended in the data chapter — and it partly undercuts the proposal's headline that the Atlantic spot posted a *record single-day* move (futures need not move identically).
- **Bias introduced:** basis risk, roll effects, lower granularity. **Do not** silently substitute; if you must use it, the thesis degrades to the documented fallback branch.

### Provenance-limited Fearnleys assessments supplied 2026-08-08

Three user-supplied structured workbooks contain weekly Fearnleys assessments
for East-of-Suez spot, West-of-Suez spot, and a one-year LNG-carrier time
charter (155-165k cbm, USD/day). They cover 230 of 235 expected Friday weeks in
the locked study window and include 18 post-cutoff weeks. They are analytically
useful because they supply direct monetary freight-market observations that the
free branch lacks.

Their status is nevertheless **restricted / provenance-limited secondary**, not
an admitted replacement for Spark25S/30S. The repository does not hold the
original terminal-export payloads, extraction receipts, assessment
methodology, verified definition history, or confirmed thesis reuse rights.
**Update 2026-08-09:** the exact Bloomberg identifiers are now held —
`FLNGEASZ Index` (East of Suez spot), `FLNGWTSZ Index` (West of Suez spot),
and `FLNG1YTC Index` (one-year time charter) — verified from user-supplied
Bloomberg Charts PDFs plus six exact extreme-value/date matches against the
transcriptions (see `config/bloomberg_exports.yaml` comments and
`data/raw/bloomberg_transcription/originals/charts/README.md`). The earlier
"identifiers unknown" caveat is downgraded to "identifiers known"; everything
else in this paragraph stands. **Update 2026-08-19:** Bloomberg's help desk did
not authorise use of Bloomberg data in the thesis, so the layer is excluded
rather than awaiting a rights decision. Three rows are marked as reconstructed transcription boundaries, and
two zero West-of-Suez rows are preserved raw but masked in analysis. The
workbooks are checksum-pinned and loaded only through the registry-controlled
local provider. Raw values are not published.

Analytical role before the rights decision: candidate secondary descriptives,
context, and supplementary pre-treatment-selected forecast deviations. Final
thesis role after the 2026-08-19 decision: excluded. Prohibited use includes raw
redistribution, silent Spark substitution, primary-outcome activation, ATT
language, structural causal freight claims, and identified mediation claims.

### Energy confounders

| Variable | Source (free) | What it is | Status | Notes / bias |
|---|---|---|---|---|
| `henry_hub_spot` | **EIA API** `NG.RNGWHHD.D` (cross-check: **FRED** `DHHNGSP`) | Henry Hub natural gas spot, USD/MMBtu, daily | **free** | Genuine match. US gas benchmark — exactly the series the proposal lists. Public domain. |
| `brent_spot` | **EIA API** `PET.RBRTE.D` (cross-check: **FRED** `DCOILBRENTEU`) | Europe Brent spot, USD/bbl, daily, from 1987 | **free** | Genuine match. Public domain. |
| `ttf_gas` | User-supplied structured Bloomberg workbook (exact provider/identifier unverified) | Dutch TTF day-ahead assessment, EUR/MWh | **restricted** | Excluded from the thesis after the 2026-08-19 vendor decision; raw publication prohibited. |
| `jkm_lng` | S&P Global Platts assessment; EEX settlement retained only as an access candidate | Japan-Korea Marker LNG | **unavailable** | No verified accessible historical feed or implemented provider. A future would be a different instrument with basis/timing risk. |

Singapore VLSFO is likewise registered as a restricted context series from the
user-supplied ClearLynx-labelled workbook. It is excluded from the thesis after
the 2026-08-19 vendor decision and does not enter the headline freight forecasts
as an observed post-event control.

### Route / chokepoint capacity

| Variable | Source (free) | What it is | Status | Notes / bias |
|---|---|---|---|---|
| `panama_transit` | **IMF PortWatch** (AIS/satellite, ~90k ships) | Daily transit calls + trade-volume estimate, Panama Canal | **free** | Strong free covariate for the Panama-arbitrage channel. Updated weekly (Tue). |
| `hormuz_transit` | **IMF PortWatch** | Daily transit calls + trade-volume estimate, Strait of Hormuz | **free** | Lets you observe the disruption directly in operational data. |

- **Units:** PortWatch reports chokepoint transit volume in metric tonnes. The
  registered `capacity_tanker` field is therefore described conservatively as
  an AIS-derived tanker transit-volume/capacity proxy in metric tonnes, rather
  than as cargo actually observed aboard each vessel.
- **What PortWatch captures:** aggregate vessel-traffic intensity through a named chokepoint — a real, independent, public window onto the event.
- **What it cannot capture:** laden vs ballast legs, vessel identity, commodity split per vessel, or per-voyage ton-miles. It is **chokepoint-aggregate**, not vessel-level.
- **Bias / caveats:** AIS coverage gaps, gap-filling/modelling assumptions in PortWatch's own pipeline, and it is *not* LNG-specific at the transit-count level. Treat as media-of-observation data, not ground truth.
- **Frozen vintage:** The active Hormuz transit series is explicitly checksum-
  pinned to the July 2026 repository capture. PortWatch revised historical
  values between captures; both versions and their roles are recorded in
  `docs/PORTWATCH_VINTAGE_REGISTER.md`. The older version is preserved but
  quarantined from active input scopes.

### LNG-specific public robustness outcome discovered 2026-06-18

The WTO/AXSMarine **Strait of Hormuz Trade Tracker** exposes a public daily
LNG-only outbound shipment-volume index (2025 average = 100) and explicitly
excludes LPG. The reproducible endpoint is
`https://wtomais.blob.core.windows.net/strait-of-hormuz-tracker/voy_intake_index_lng_export.csv`.
The frozen snapshot contains 534 complete daily rows from 2025-01-01 through
2026-06-18 (SHA-256
`5500461bcbb9f405f38fe255ee4ce6906fef4c75d3208d23b01b5430645f1a6f`).

This materially improves commodity specificity but does **not** recover the
approved freight-rate dependent variable: it is an indexed shipment-volume
series, not a carrier count, physical tonnage, ton-mile measure, or freight
assessment. Its pre-period is also short (423 days before 2026-02-28), and the
underlying voyage intelligence is supplied by AXSMarine. It is therefore kept
as an optional LNG-specific robustness outcome while PortWatch remains the
locked working primary.

### Mechanism — the ton-mile proxy (the proposal's go/no-go gate)

| Variable | What the proposal wants | Free reality | Status |
|---|---|---|---|
| `ais_laden_tonmiles_usgc` | AIS-derived **laden ton-miles to the US Gulf Coast** replacement origin | True vessel-level AIS with laden/ballast resolution is proprietary (Kpler, Spire, MarineTraffic). PortWatch is only a weak **aggregate** stand-in. | unavailable |

- This is the single most important data dependency in the thesis, because H3 (the contribution-bearing mechanism test) **pre-commits** to this exact proxy. PortWatch cannot substitute for it — it cannot separate laden ton-miles from raw transit counts.
- **Consequence, stated plainly:** the free branch cannot execute the proposal's
  original observed laden-ton-mile mechanism as specified. It now implements a
  weaker empirical layer using GFW terminal sequences, nominal vessel capacity,
  and modeled route distance. That inferred capacity-nautical-mile result is
  descriptive and explicitly not observed cargo ton-miles.

---

## What each free source contributes vs. what it cannot — summary

- **EIA / FRED** — *contribute:* clean, authoritative, free energy-price confounders (Henry Hub, Brent) that are genuine matches, with two independent providers for cross-checking. *Cannot:* give you any freight or LNG-assessment series.
- **ICE / EEX settlements** — *potential acquisition channels only:* no verified
  accessible historical feed is implemented for TTF, JKM, or Spark-linked
  freight futures. Even if access is obtained, futures cannot reproduce daily
  physical spot assessments and carry basis, roll, and timing risk.
- **IMF PortWatch** — *contribute:* a genuinely free, independent, AIS-derived operational view of the Hormuz and Panama chokepoints — valuable for the descriptive layer and as a route covariate. *Cannot:* deliver vessel-level laden ton-miles; it is aggregate only.
- **WTO/AXSMarine Hormuz tracker** — *contribute:* a public LNG-only daily outbound shipment-volume index that excludes LPG. *Cannot:* provide freight rates, carrier counts, physical tonnes, ton-miles, or a long pre-period.
- **Spark / Platts / Bloomberg / Kpler / Lloyd's** — *contribute:* the actual target and the primary mechanism variable. *Cannot:* be obtained free; these are the items to negotiate via TUM.

---

## Importer customs source decision -- Japan upgrade, 2026-07-17

Japan's importer-origin outcome is upgraded from the earlier UN Comtrade fallback
to the source-native Trade Statistics of Japan / e-Stat feed. This is a
methodological source upgrade under the free/proprietary honesty rule, not a
silent proxy swap: both sources describe HS 271111 LNG imports by partner, but
the e-Stat/Japan Customs snapshot is the national statistical source and extends
the public post-onset window through May 2026 at the time of capture.

Implementation consequence: `japan_lng_import_total` and
`japan_lng_import_gulf` now use provider `importer_customs` with codes
`jp:total` and `jp:gulf`. The canonical registry series is weight-basis
(`weight_ton`). The source e-Stat files also include value in JPY thousand; that
value is preserved in
`data/raw/importer_customs/originals/jp_original_lng271111_with_jpy.csv` and is
not relabeled as USD in the canonical snapshot. Oman remains explicitly excluded
from the Gulf/Hormuz-dependent set because Qalhat/Sur load outside the Strait of
Hormuz.

The previous UN Comtrade Japan snapshot remains in
`data/raw/backup_pathway_probe_20260621/` as provenance for the earlier coverage
probe, but it is no longer the active Japan source when the importer-customs
provider is used.

## Refreshed EU27 snapshot, 2026-07-17

EU27 remains an aggregate comparator, not an importer. The active Eurostat
`nrg_ti_gasm` JSON-stat snapshot now points to the 2026-07-17 public capture in
`data/raw/public_snapshots_20260717/eurostat/`. The returned time dimension runs
through 2026-06, and the last month with any non-null partner value is 2026-05.

## Manual-capture and source-artifact limitations

The following frozen extension inputs cannot be independently reconstructed
from original response evidence held in this repository. This is a provenance
limitation, not evidence that the values are wrong. It restricts auditability
and therefore the strength assigned to importer- and vessel-extension results.
It does not affect the independently frozen PortWatch primary outcome.

| Input | What is retained | What was not retained | Consequence |
|---|---|---|---|
| Korea KCS importer table | Normalized table scrape and capture-method metadata | Original rendered HTML/HTTP response, query receipt, contemporaneous terms page | The repository cannot independently prove the historical server response from frozen bytes; Korea importer results are extension evidence only. |
| China GACC importer table | Three portal-export CSV files, one per queried year | Surrounding HTML, request/query receipts, contemporaneous terms page | File contents are hash-verifiable, but the exact portal interaction and reuse terms cannot be independently reconstructed. |
| India DGCI&S Tradestat table | Parsed, concatenated table capture (`in_original_long.csv`) and acquisition script | Original response HTML, response headers, contemporaneous terms page | The retained CSV is not an original HTTP payload. Historical capture used a browser-compatible User-Agent; future requests identify the academic script explicitly. |
| Q-Flex 31-vessel benchmark | Manually assembled CSV with row-level Nakilat and IGU URLs | The supporting Nakilat fleet-list and IGU-report PDFs, page extracts, and a transcription log were not frozen with the roster | Schema, IMO checksums, and cited URLs are auditable, but row-level transcription cannot be independently verified from repository-held source documents. |

No result from these inputs should be presented as independently source-
reproducible. Re-capture would create a new dated vintage; it would not
retroactively repair the missing historical response evidence.

---

## Registration / API-key requirements (flagged)

| Source | Key needed? | Cost | Where |
|---|---|---|---|
| EIA | Yes — instant, free | Free | https://www.eia.gov/opendata/register.php |
| FRED | Yes — instant, free | Free | https://fred.stlouisfed.org/docs/api/api_key.html |
| IMF PortWatch | No key — direct CSV/GeoJSON download + WFS API | Free | https://portwatch.imf.org |
| ICE / EEX settlements | No verified accessible historical feed; full feeds licensed | Unavailable in the working pipeline | ice.com / eex.com |
| Spark, Platts, Bloomberg, Kpler | Subscription / institutional access | Paid | via TUM negotiation |

**Immediately usable today, with zero approvals beyond two instant keys:** Henry Hub, Brent (EIA+FRED), and Hormuz/Panama transits (PortWatch). These support the descriptive throughput pipeline; they do not supply the missing freight-price outcome.

> Sources for the access facts above: [EIA Open Data](https://www.eia.gov/opendata/), [FRED Henry Hub series](https://fred.stlouisfed.org/series/DHHNGSP), [IMF PortWatch data & methodology](https://portwatch.imf.org/pages/data-and-methodology), [Spark LNG Freight](https://www.sparkcommodities.com/lng-freight/), [ICE Spark25S future](https://www.ice.com/products/79234892/Spark25S-Pacific-NWS-to-Tianjin-LNG-Freight-Future), [EEX Natural Gas/LNG](https://www.eex.com/en/markets/natural-gas/lng).

---

## Freight-target access decision — verified 2026-06-14

This section records the 2026-06-14 verification behind the conservative status
used throughout this document. Branch already chosen: **free/fallback** (no
proprietary access assumed).

### What was checked, and what is true

| Channel | Gives | Free? | Verified status (2026-06-14) |
|---|---|---|---|
| Spark **premium** API | Real Spark25S/30S daily assessment + full history | No | Confirmed paywalled (subscription / sales contact). |
| Spark **free-trial** account (OAuth2) | Real assessment; **history depth unknown** | Signup-free | Trial exists; whether it covers the **Feb–Mar 2026 daily** window is **UNVERIFIED** — must be tested empirically with credentials. |
| Spark **non-authenticated** endpoint | Real assessment but **"Price Release N-4"** (4 releases delayed) and appears **latest-value only** | Yes | N-4 delay confirmed. The delay is harmless for a *retrospective* study, but a latest-only endpoint **cannot rebuild** a past series now. |
| Spark **academic/research** access | Potentially full primary series | One email | **Not documented publicly**; common for providers. Action item, not a confirmed fact. |
| **ICE** LNG Freight Futures (Spark30S/25S-settled) — retained only as an acquisition candidate in `sources.yaml` | Front-month future, tightly linked to Spark spot | **NOT confirmed free** | ICE EOD settlement is licensed; resellers (Barchart) are premium. The earlier "free subset" claim is **not supported** by this check. |
| **EEX** | — | n/a | EEX *owns* Spark but the freight futures trade on **ICE**, not EEX's free market-data pages. No free freight-futures EOD found. |
| **Baltic Exchange** BLNG routes | Independent LNG freight assessment | No | Confirmed subscription. |

### The honest headline (revised)

**There is no confirmed zero-friction free *historical daily* feed for the dependent
variable — and, contrary to the earlier note, the ICE-futures "proxy" is not a
verified free escape hatch either.** Both the primary and the futures proxy funnel
back to the same gate. The only realistic free route to a *real* freight number is a
**Spark account** (free trial and/or academic grant), which — if its history reaches
the study window — returns the actual Spark25S/30S assessment, strictly better than a
futures proxy.

### Decision (2026-06-14): pursue Spark primary + prep adapter in parallel

1. **Goal = the primary series.** Mher to (a) email Spark for **academic/research
   access** (TUM Bachelor thesis), and (b) create a **free-trial account** and
   empirically test whether it returns Spark25S/30S over **2026-02-01 → 2026-06-01**
   at daily granularity. Record the answer here when known.
2. **Adapter prep, not proxy fabrication.** Build a `spark` source module (OAuth2,
   tidy `(date, value)` contract) that serves the real series *and* the constrained
   free-trial. It must **fail loudly without credentials** — never emit synthetic or
   placeholder freight numbers (CLAUDE.md rule 1).
3. **ICE-futures proxy is DEMOTED to "unverified-access".** Do **not** build an
   `ice_settlement` freight fetch until a genuinely free EOD source is confirmed; on
   present evidence it is no more accessible than the primary.
4. **If both fail**, the documented fallback is explicit in the proposal: run Layers
   1–4 on confounders + route covariates, and reframe the freight-target claims as
   limited/descriptive. That remains a *decision to be recorded*, not a silent gap.

> Verification method: web search + page fetches on 2026-06-14 of Spark API docs,
> ICE LNG Freight Futures product page, and EEX/Baltic listings. Marketing pages do
> not disclose free-tier history depth; the trial test in action item (1) is the only
> way to settle it. Sources: [Spark LNG Freight Contracts API](https://www.sparkcommodities.com/api/lng-freight/contracts.html),
> [Spark API code samples](https://github.com/spark-commodities/api-code-samples),
> [ICE LNG Freight Futures](https://www.ice.com/global-natural-gas-futures/lng-freight-futures),
> [Baltic Exchange gas services](https://www.balticexchange.com/en/data-services/market-information0/gas-services.html).
