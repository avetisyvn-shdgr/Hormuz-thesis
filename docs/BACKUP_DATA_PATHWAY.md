# Backup Data Pathway — Who Actually Suffered From the Hormuz Disruption

**Status:** Proposed; data availability verified by live probes 2026-06-21. Not yet
wired into the registry or the reproducibility manifest.
**Focus (corrected 2026-06-21):** the **Gulf-dependent importers and Gulf exporters**
that lost supply — NOT the EU, which substituted costlessly and is the resilient
comparator, not the victim.

## Why this exists

The approved proposal's two proprietary inputs — Spark25S/30S **freight rates** and
AIS **laden ton-miles** — were never obtained. This pathway needs **no paid or trial
Spark/Bloomberg access** and answers a question the current pipeline cannot:

> **Which countries actually suffered a supply loss** from the Strait of Hormuz
> disruption, how exposed was each (share of LNG that must transit Hormuz), and did
> the affected importers re-source, ration, or go short?

It does **not** recover the freight *price* — no free like-for-like assessment exists
(`DATA_SOURCES.md` §"Freight-target access decision"); that gap is deliberately
abandoned as low-return. This is a quantity/exposure analysis layer.

## The organizing idea: exposure = captivity

The sharpest framing the data supports:

> **Disruption impact is mediated by substitution optionality.** Countries with
> short-haul alternatives absorbed the shock at near-zero volume loss; countries
> captive to Gulf supply took measurable cuts. The thesis can *rank* countries on
> this axis.

- **Resilient (NOT the focus):** EU27 — total LNG imports actually **rose +1,204
  MIO_M³** post-onset, substituting away from Qatar/Nigeria toward short-haul Algeria
  (+871) and Atlantic US (+539). The EU is the **control/benchmark** that proves the
  contrast, not an impact case.
- **Affected (THE focus):** Gulf-captive Asian importers and the Gulf exporters
  behind Hormuz, where preliminary public figures already show real losses (below).

## The affected universe

| Role | Countries | Hormuz exposure |
|---|---|---|
| **Exporters behind Hormuz** | **Qatar** (world's top LNG exporter, ~all via Hormuz), **UAE**, Oman¹ | ~100% / high |
| **Captive importers** | **India** (~50% Qatar + 12% UAE ≈ 62% Gulf), **South Korea**, **Japan**, **China**, **Taiwan**, **Pakistan**, **Bangladesh**, Kuwait | high → moderate |

¹ Oman's Sohar is just outside the strait; treat as sensitivity, not core.

## Preliminary public signals (already visible, pre-build)

- **India:** LNG imports **−20.97% YoY in May 2026** (PPAC). India is the single most
  Hormuz-exposed major importer (~62% Gulf). 
- **Japan:** total LNG imports **−20.6% in April 2026** (MOF), with Russian share
  rising — a captive importer partially re-sourcing to the Pacific/Sakhalin.
- **EU (contrast):** **no volume loss** — substituted freely (see above).

These are secondary-reported figures pending primary-source confirmation; they
establish the *direction* and justify the build, they are not yet thesis numbers.

## Sources — verified status (probed live 2026-06-21)

| Source | LNG-specific | Granularity | Coverage | Status |
|---|---|---|---|---|
| **India PPAC** (`ppac.gov.in/natural-gas/import`) | Yes | imports, monthly, by-source | **May 2026** | ✅ current; the most-exposed importer |
| **Japan MOF / e-Stat** (`customs.go.jp`, e-Stat API) | Yes | imports by source country, monthly | **Apr 2026** (updated Jun 5) | ✅ current; by-source |
| **Global Fishing Watch** (Events/port-visit API, token held) | vessel-level | LNG-carrier arrivals at importer terminals; Gulf departures | near-real-time | ✅ **harmonized timely backbone** — already integrated; cross-validates national stats and covers Gulf-export side |
| Korea (KOSIS/KESIS), Taiwan, China (GACC) customs | Yes | imports by source, monthly | confirm at build | 🔧 candidate national sources |
| **EIA** `move/expc` `ENG` | Yes | US LNG exports by destination | through 2026-03 | ✅ Atlantic-supply (substitution into Asia) |
| **Eurostat** `nrg_ti_gasm` `G3200` | Yes | EU imports by partner | through 2026-05 | ✅ **comparator/control only** |
| **UN Comtrade** preview | HS 2711 | bilateral monthly | **USA + Japan only** for 2026 | ⚠️ Korea/China/India/Qatar **blank** — corroboration only |
| **JODI-Gas** free bulk CSV | Yes | country totals by flow | **stale — ends 2018-12** | ❌ direct CSV not current; live data behind portal/API, refresh path **unconfirmed** |

### Two limitations the probes exposed (do not paper over)
1. **No harmonized free trade-stat backbone covers the affected Asian importers for
   2026.** Comtrade lags (blank), JODI free CSV is stale. The affected side therefore
   rests on **heterogeneous national statistics + GFW vessel tracking**, not one tidy
   feed. GFW is the only harmonized, timely, free instrument spanning all of them.
2. **The Gulf-exporter side has no easy national feed** (Qatar/UAE do not publish
   timely by-destination LNG stats). Reconstruct it from (a) importers' by-source data
   and (b) **GFW Gulf LNG departures**, which the repo already measures at **−93%** —
   a result this layer extends from "departures fell" to "whose supply those
   departures were."

## Proposed analysis layer (if adopted)

1. **Exposure index per country** = pre-disruption share of LNG sourced from Hormuz-
   transiting origins (Qatar/UAE/Oman), from national by-source stats. Ranks captivity.
2. **Observed loss per country** = pre-vs-post LNG import volume (national stats /
   GFW arrivals), as % and absolute.
3. **Impact = exposure × (in)ability to substitute.** Regress/*describe* observed loss
   against exposure; the EU sits at exposure>0 but loss≈0 (high optionality), the
   captive importers at exposure-high, loss-high. This is the headline relationship.
4. **GFW cross-validation** of national stats (mirrors the repo's strongest existing
   result, WTO≈GFW −98.6%/−93% with no calibration).
5. **Ton-mile angle** (secondary): for substituters (Japan→Pacific, EU→Algeria/US),
   volume × `searoute` distance to test haul shortening/lengthening; for captives
   (India), the story is *shortfall*, not re-routing.

## Role in the thesis & honesty rules

- Slots under the mechanism / "who was affected" branch; **descriptive,
  disruption-associated, never causal/ATT** — same discipline as the rest of the repo.
- Does **not** change the locked primary estimator (AR-only Hormuz throughput) or
  reopen the freight-price gap.
- Strengthens the contribution from "Hormuz throughput collapsed" to "**the
  disruption's burden fell on Gulf-captive importers (India, Japan, …) while
  optionality-rich buyers (EU) escaped — impact tracked exposure, not proximity.**"
- This expands scope beyond the approved proposal → **must be flagged to Prof. Li**
  alongside the pending `SUPERVISOR_DECISION_MEMO.md`.

## Next actions

- [ ] Pull India PPAC + Japan e-Stat by-source LNG imports; freeze with SHA-256.
- [ ] Build the per-country exposure index + observed-loss table (Gulf-captive set).
- [ ] Extend GFW to importer-terminal arrivals; cross-validate national stats; quantify
      the Gulf-exporter side from departures.
- [ ] Re-pull Eurostat to confirm/deny the provisional April Qatar 0.0 vs May.
- [ ] Confirm Korea/Taiwan/China national feeds; confirm a live JODI access route or drop it.
- [ ] Wire adopted sources through `registry.get_variable()` + `provenance.jsonl`.
