# Data Sources — The Bloomberg-Terminal Alternative

**Purpose.** This is the load-bearing document for the data-access (go/no-go) decision in the proposal. It maps every variable in the proposal's *minimum viable dataset* to a concrete source, states honestly what is free vs proprietary, and records what each source can and **cannot** capture. Nothing here asserts access rights that have not been verified.

**The honest headline.** There is **no free, like-for-like replacement** for your dependent variable. Spark25S / Spark30S are proprietary Spark Commodities assessments; JKM is a proprietary S&P Global Platts assessment. A "professional" alternative to Bloomberg is therefore *not* a scraper that imitates these series — it is (a) a clear-eyed registry of what each free source genuinely is, and (b) a software layer that lets you run the whole pipeline on free proxies now and swap in the proprietary feeds later by editing one config file. That layer is already built (`config/sources.yaml` + `src/lngfreight/`).

---

## Status legend

| status | meaning |
|---|---|
| **free** | A free series that *is* the real thing the proposal wants. No proprietary gap. |
| **proxy** | A free, *imperfect* stand-in carrying basis/timing risk. Must be documented as such. |
| **unavailable** | No adequate free option exists. Slot reserved for proprietary access. |

---

## Variable-by-variable

### Dependent variable — LNG spot freight

| Variable | What the proposal wants | Free reality | Status |
|---|---|---|---|
| `spark30s_atlantic_freight` | Spark30S daily spot assessment (Sabine Pass → Gate) | Spark publishes only **indicative** prices publicly; full daily data needs a Spark subscription. ICE lists **Spark30S freight futures**, whose *settlement* prices are a partial free proxy. | unavailable (proxy = futures settlement) |
| `spark25s_pacific_freight` | Spark25S daily spot assessment (NWS → Tianjin) | Same as above. | unavailable (proxy = futures settlement) |

- **What the proxy captures:** broad direction and large moves in LNG freight cost.
- **What it cannot capture:** the *daily physical spot assessment itself*. A front-month future is a different instrument with its own roll, term structure and liquidity. Treating it as the spot series is a **measurement-validity assumption** that would have to be defended in the data chapter — and it partly undercuts the proposal's headline that the Atlantic spot posted a *record single-day* move (futures need not move identically).
- **Bias introduced:** basis risk, roll effects, lower granularity. **Do not** silently substitute; if you must use it, the thesis degrades to the documented fallback branch.

### Energy confounders

| Variable | Source (free) | What it is | Status | Notes / bias |
|---|---|---|---|---|
| `henry_hub_spot` | **EIA API** `NG.RNGWHHD.D` (cross-check: **FRED** `DHHNGSP`) | Henry Hub natural gas spot, USD/MMBtu, daily | **free** | Genuine match. US gas benchmark — exactly the series the proposal lists. Public domain. |
| `brent_spot` | **EIA API** `PET.RBRTE.D` (cross-check: **FRED** `DCOILBRENTEU`) | Europe Brent spot, USD/bbl, daily, from 1987 | **free** | Genuine match. Public domain. |
| `ttf_gas` | **ICE/EEX** front-month future settlement (free subset) | Dutch TTF gas, European benchmark | **proxy** | Front-month future ≠ physical TTF assessment. Calendar-roll and timing basis. |
| `jkm_lng` | **EEX** Platts JKM future settlement (delayed, free subset) | Japan-Korea Marker LNG | **proxy** | The *assessment* is proprietary Platts. Futures settlement is delayed and is a different instrument. Document timing/basis risk. |

### Route / chokepoint capacity

| Variable | Source (free) | What it is | Status | Notes / bias |
|---|---|---|---|---|
| `panama_transit` | **IMF PortWatch** (AIS/satellite, ~90k ships) | Daily transit calls + trade-volume estimate, Panama Canal | **free** | Strong free covariate for the Panama-arbitrage channel. Updated weekly (Tue). |
| `hormuz_transit` | **IMF PortWatch** | Daily transit calls + trade-volume estimate, Strait of Hormuz | **free** | Lets you observe the disruption directly in operational data. |

- **What PortWatch captures:** aggregate vessel-traffic intensity through a named chokepoint — a real, independent, public window onto the event.
- **What it cannot capture:** laden vs ballast legs, vessel identity, commodity split per vessel, or per-voyage ton-miles. It is **chokepoint-aggregate**, not vessel-level.
- **Bias / caveats:** AIS coverage gaps, gap-filling/modelling assumptions in PortWatch's own pipeline, and it is *not* LNG-specific at the transit-count level. Treat as media-of-observation data, not ground truth.

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
- **ICE / EEX settlements** — *contribute:* free-ish *proxies* for TTF, JKM, and even the Spark freight benchmarks via futures. *Cannot:* reproduce the daily physical spot assessments; they carry basis, roll and timing risk.
- **IMF PortWatch** — *contribute:* a genuinely free, independent, AIS-derived operational view of the Hormuz and Panama chokepoints — valuable for the descriptive layer and as a route covariate. *Cannot:* deliver vessel-level laden ton-miles; it is aggregate only.
- **WTO/AXSMarine Hormuz tracker** — *contribute:* a public LNG-only daily outbound shipment-volume index that excludes LPG. *Cannot:* provide freight rates, carrier counts, physical tonnes, ton-miles, or a long pre-period.
- **Spark / Platts / Bloomberg / Kpler / Lloyd's** — *contribute:* the actual target and the primary mechanism variable. *Cannot:* be obtained free; these are the items to negotiate via TUM.

---

## Registration / API-key requirements (flagged)

| Source | Key needed? | Cost | Where |
|---|---|---|---|
| EIA | Yes — instant, free | Free | https://www.eia.gov/opendata/register.php |
| FRED | Yes — instant, free | Free | https://fred.stlouisfed.org/docs/api/api_key.html |
| IMF PortWatch | No key — direct CSV/GeoJSON download + WFS API | Free | https://portwatch.imf.org |
| ICE / EEX settlements | Free subset; full feed paid | Mixed | ice.com / eex.com |
| Spark, Platts, Bloomberg, Kpler | Subscription / institutional access | Paid | via TUM negotiation |

**Immediately usable today, with zero approvals beyond two instant keys:** Henry Hub, Brent (EIA+FRED), and Hormuz/Panama transits (PortWatch). That is enough to build and validate the entire pipeline and the descriptive event-study layer before any proprietary decision is made.

> Sources for the access facts above: [EIA Open Data](https://www.eia.gov/opendata/), [FRED Henry Hub series](https://fred.stlouisfed.org/series/DHHNGSP), [IMF PortWatch data & methodology](https://portwatch.imf.org/pages/data-and-methodology), [Spark LNG Freight](https://www.sparkcommodities.com/lng-freight/), [ICE Spark25S future](https://www.ice.com/products/79234892/Spark25S-Pacific-NWS-to-Tianjin-LNG-Freight-Future), [EEX Natural Gas/LNG](https://www.eex.com/en/markets/natural-gas/lng).

---

## Freight-target access decision — verified 2026-06-14

**Supersedes** the optimistic "partial free proxy via futures settlement" framing in
the dependent-variable table above (rows `spark30s_atlantic_freight`,
`spark25s_pacific_freight`) and the "free-ish proxies via futures" line in the
summary. Branch already chosen: **free/fallback** (no proprietary access assumed).
This section records what was actually verified about getting *any* freight-target
series for free, and the resulting decision.

### What was checked, and what is true

| Channel | Gives | Free? | Verified status (2026-06-14) |
|---|---|---|---|
| Spark **premium** API | Real Spark25S/30S daily assessment + full history | No | Confirmed paywalled (subscription / sales contact). |
| Spark **free-trial** account (OAuth2) | Real assessment; **history depth unknown** | Signup-free | Trial exists; whether it covers the **Feb–Mar 2026 daily** window is **UNVERIFIED** — must be tested empirically with credentials. |
| Spark **non-authenticated** endpoint | Real assessment but **"Price Release N-4"** (4 releases delayed) and appears **latest-value only** | Yes | N-4 delay confirmed. The delay is harmless for a *retrospective* study, but a latest-only endpoint **cannot rebuild** a past series now. |
| Spark **academic/research** access | Potentially full primary series | One email | **Not documented publicly**; common for providers. Action item, not a confirmed fact. |
| **ICE** LNG Freight Futures (Spark30S/25S-settled) — the proxy named in `sources.yaml` | Front-month future, tightly linked to Spark spot | **NOT confirmed free** | ICE EOD settlement is licensed; resellers (Barchart) are premium. The earlier "free subset" claim is **not supported** by this check. |
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
