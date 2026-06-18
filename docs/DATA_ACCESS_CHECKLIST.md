# Go / No-Go Data-Access Checklist

The proposal makes data access the *critical path* and a binary gate. This is the
concrete checklist that resolves it. Work the FREE column first (you can start
today); pursue the PROPRIETARY column in parallel via TUM, because lead times are long.

## Tier A — Free, start immediately (no gate)
- [ ] EIA API key registered, `.env` filled, `henry_hub_spot` pulls OK
- [ ] FRED API key registered, Henry Hub cross-check matches EIA within tolerance
- [ ] Brent pulls OK from EIA (+ FRED cross-check)
- [ ] IMF PortWatch: download Hormuz + Panama chokepoint CSV once by hand; pin the
      real column names into `sources/portwatch.py`; confirm daily coverage across
      the study window
- [ ] Descriptive event-study layer (Layer 1) reproducible from free data alone

## Tier B — Proprietary, negotiate via TUM (the real gate)
For each, record: *can TUM provide it? at what granularity? for which date range? export-allowed?*
- [ ] **Spark25S / Spark30S** daily spot assessments (the dependent variable) — via TUM Bloomberg or a Spark academic licence
- [ ] **Baltic** LNG benchmarks (supervisor mentioned) — confirm availability
- [ ] **Platts JKM** assessment (vs the EEX-futures proxy)
- [ ] **TTF** physical assessment (vs the ICE-futures proxy)
- [ ] **Lloyd's List** war-risk listed-area premia (needed for the H2 rival-hypothesis equivalence test)
- [ ] **AIS / vessel positioning** with laden-vs-ballast resolution (Kpler / Spire / MarineTraffic) — needed for the H3 primary ton-mile proxy

## The decision
- **Full branch** (Tier B Spark + AIS + Lloyd's secured): run all five layers incl. the mechanism mediation and causal-direction tests.
- **Fallback branch** (Tier B not secured): run Layers 1–4 on free data + futures proxies; reframe the mechanism question as *descriptive*; the identification *protocol* remains the contribution. The proposal already declares this a valid, passing outcome.

## What to ask your supervisor / TUM library, specifically
1. Does the TUM Bloomberg terminal expose Spark25S, Spark30S and Baltic LNG benchmarks, and **may data be exported** for a thesis (some terminal licences forbid bulk export)?
2. Is there an institutional Platts / S&P Global Commodity Insights subscription?
3. Any existing TUM agreement with an AIS provider (Kpler/Spire/MarineTraffic) or maritime-analytics group?
4. Is a *documented scenario-analysis* fallback acceptable to the examiner if AIS access fails? (The proposal says yes — confirm the supervisor agrees in writing.)
