# Go / No-Go Data-Access Checklist

The proposal makes data access the *critical path* and a binary gate. This is the
concrete checklist that resolves it. Work the FREE column first (you can start
today); pursue the PROPRIETARY column in parallel via TUM, because lead times are long.

## Current extension gate (added 2026-06-19)

The active plan is `CURRENT_PLAN.md`; the first reproducible audit is recorded
in `VESSEL_DATA_FEASIBILITY.md` and
`data/processed/vessel_data_feasibility.json`.

- [x] Audit existing PortWatch and WTO LNG schemas/coverage.
- [x] Define pre-committed vessel-sample acceptance thresholds.
- [x] Confirm from GFW documentation that identity and port visits cover all
      vessel types, while vessel presence is not a raw track and cargo state is
      not observed.
- [x] Register a personal GFW token and add `GFW_API_TOKEN` to `.env`.
- [x] Freeze a sourced 30-vessel LNG benchmark roster by IMO.
- [x] Pull a short identity and port-visit sample through registered adapters.
- [x] Score the sample gate: Q-Flex port-sequence feasibility passed.
- [x] Expand to the 624-vessel eligible global census and repeat coverage,
      terminal-match, and endpoint-resolution diagnostics.
- [x] Pre-commit route-distance and capacity-mile construction methods.
- [ ] Continue Spark academic/trial/Bloomberg access in parallel until the
      thesis is finalized.

## Tier A — Free, start immediately (no gate)
- [x] Frozen EIA Henry Hub and Brent snapshots cover the working panel.
- [ ] FRED API key registered, Henry Hub cross-check matches EIA within tolerance
- [ ] Complete the Brent FRED cross-check against the frozen EIA series.
- [x] IMF PortWatch: download Hormuz + Panama chokepoint CSV once by hand; pin the
      real column names into `sources/portwatch.py`; confirm daily coverage across
      the study window
- [x] Descriptive event-study layer (Layer 1) reproducible from free data alone

## Tier B — Proprietary, negotiate via TUM (the real gate)
For each, record: *can TUM provide it? at what granularity? for which date range? export-allowed?*
- [ ] **Spark25S / Spark30S** daily spot assessments (the dependent variable) — via TUM Bloomberg or a Spark academic licence
- [ ] **Baltic** LNG benchmarks (supervisor mentioned) — confirm availability
- [ ] **Platts JKM** assessment (EEX futures remain an unverified acquisition candidate, not an active proxy)
- [ ] **TTF** physical assessment (ICE futures remain an unverified acquisition candidate, not an active proxy)
- [ ] **Lloyd's List** war-risk listed-area premia (needed for the H2 rival-hypothesis equivalence test)
- [ ] **AIS / vessel positioning** with laden-vs-ballast resolution (Kpler / Spire / MarineTraffic) — needed for the H3 primary ton-mile proxy

## The decision
- **Full branch** (Tier B Spark + AIS + Lloyd's secured): run all five layers incl. the mechanism mediation and causal-direction tests.
- **Fallback branch (active):** run the throughput and open-data vessel pipelines
  on frozen free data; keep the inferred capacity-distance mechanism descriptive.
  The original freight-rate and laden-cargo claims remain unavailable without
  Tier B access.

## What to ask your supervisor / TUM library, specifically
1. Does the TUM Bloomberg terminal expose Spark25S, Spark30S and Baltic LNG benchmarks, and **may data be exported** for a thesis (some terminal licences forbid bulk export)?
2. Is there an institutional Platts / S&P Global Commodity Insights subscription?
3. Any existing TUM agreement with an AIS provider (Kpler/Spire/MarineTraffic) or maritime-analytics group?
4. Is a *documented scenario-analysis* fallback acceptable to the examiner if AIS access fails? (The proposal says yes — confirm the supervisor agrees in writing.)
