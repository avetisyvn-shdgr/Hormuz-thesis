# Data / literature / event candidate review — 2026-08

**Prepared:** 2026-08-09 (Claude session; all web checks performed this date).
**Scope:** Candidate data sources, literature, and events relevant to the thesis
through 2026-08-01, per Mher's request.

> **EXECUTION STATUS — updated 2026-08-09 after Mher's blanket approval.**
> This file was written as a decision memo; the recommendations in §10 have
> since been **acted on**. What was changed: `docs/EVENT_CHRONOLOGY.md`
> (post-March context table + sources), `docs/SUTVA_CONTAMINATION_AUDIT.md`
> (non-Hormuz supply-side shock section), `config/settings.yaml` (**comment
> block only** — no key changed), `docs/LITERATURE_MATRIX.md` +
> `references/literature_seed.bib` + `docs/LITERATURE_SEARCH_LOG.md`,
> `config/bloomberg_exports.yaml` (three `bloomberg_identifier` fields),
> `config/sources.yaml` (**comment only**), `docs/DATA_SOURCES.md`,
> `data/raw/bloomberg_transcription/originals/charts/` (3 PDFs + README),
> `docs/WINDOW_EXTENSION_V2_RUNBOOK.md` (v3 note), `docs/DECISION_LOG.md`.
> **v3 executed 2026-08-09 with a changed outcome.** `study_window.full_end`
> deliberately **remains 2026-07-07**: a fresh PortWatch capture was found to
> revise 2,680/2,750 (97.45%) of all overlapping Hormuz days and 1,514/1,519
> (99.67%) of the configured training days. The configured 2022–cutoff mean
> falls 17.68%; the separate 16.9% figure uses the longer 2019–cutoff overlap. So
> Mher's decision was to keep the pinned vintage as the reporting basis and
> deliver the extension through 2026-08-01 as a **sensitivity layer** instead.
> See `PORTWATCH_VINTAGE_REGISTER.md`,
> `PORTWATCH_VINTAGE_SENSITIVITY_RESULTS.md`, and the two `DECISION_LOG.md`
> entries of 2026-08-09. Headline finding: the vintage moves the daily
> shortfall −17.1% at identical dates, while extending the window 25 days
> moves it +0.6%. That cumulative average concealed a temporary partial
> post-MoU rebound followed by relapse after 07-07; the defensible conclusion is
> no sustained recovery through 08-01, not “no rebound.”
> The two unverified items in §9 remain unlogged. The Bloomberg cross-check
> in §8 was **run**: all six anchors matched.

**Method and honesty notes.**
- Each candidate was independently checked against the most primary source
  reachable by web search/fetch on 2026-08-09, then checked for prior coverage
  in the five governance documents above plus a full-repo grep. None of the
  candidates appears anywhere in the repo today.
- Web fetches in this review are **verification for this memo, not data
  ingestion**. Anything that enters the analysis still goes through
  `registry.get_variable()` with `config/sources.yaml` edited first (CLAUDE.md
  rule 7). One live-currency observation (WTO tracker, §4) must be
  re-established with `scripts/fetch_wto_hormuz_lng.py` before it is relied on.
- News reporting is treated as observation, not truth. Single-sourced or
  attribution-contested items are labelled as such and carry a
  reporting-bias/missingness caveat. Nothing below was accepted from the
  candidate list without an independent check; two items could **not** be fully
  verified and are flagged (§8) rather than asserted.

---

## 1. PRIORITY — Damietta terminal attack (Egypt), 2026-07-29

### 1.1 What verified

- **Date:** Wednesday **2026-07-29** (one day earlier than the 07-30/31
  reporting dates on the candidate list; Splash247, Al Jazeera, CNBC, Euronews
  pieces are dated 07-29/30 *about* a 07-29 strike).
- **Event:** an unidentified drone struck the FSRU **Energos Winter**
  (US-linked, Marshall Islands-flagged) alongside at Egypt's Damietta LNG
  terminal; the resulting fire spread to the adjacent LNG carrier
  **GasLog Salem** (155,000 m³, 2015-built). Fires extinguished, no casualties
  reported; Egyptian officials stated port operations were not significantly
  affected and gas/fuel supplies "fully secured."
- **Closest-to-primary source:** the **Egyptian Cabinet statement** (quoted by
  Egypt Oil & Gas) that preliminary investigation attributes the fire to a UAV.
  Secondary: Splash247 ("Drone strike hits FSRU and LNG carrier at Egyptian
  terminal"), Al Jazeera (2026-07-29), CNBC (2026-07-30), Riviera, Maritime
  Executive, Seatrade.
- **Contested details (must stay flagged):** (a) **attribution** — no group
  has claimed responsibility; press names Iran as "chief suspect"
  (Splash247), which is inference, not record; (b) some Egyptian security
  sources initially attributed the fire to a technical malfunction before the
  Cabinet's UAV statement; (c) the exact charterer description varies across
  outlets (New Fortress Energy vs Energos Infrastructure). Log the event with
  the Cabinet statement as the anchor and attribution marked **unresolved**.

### 1.2 Coverage check

Not present in `EVENT_CHRONOLOGY.md` (stops at March 2026 events),
`SUTVA_CONTAMINATION_AUDIT.md` (covers rerouting contamination of donor
*chokepoints*, incl. generic Red Sea/Suez language), `sources.yaml`,
`DATA_SOURCES.md`, or `LITERATURE_MATRIX.md`. Genuinely new.

### 1.3 Assessment: distinct confound, not Red Sea/Suez boilerplate

**Yes — this needs its own entry, separate from the existing Red Sea/Suez
contamination language.** Three reasons:

1. **Different mechanism class.** The SUTVA audit's screen handles
   *transit-corridor* interference (rerouted flows contaminating donor
   chokepoints). Damietta is a **terminal-side supply/infrastructure shock on
   Egyptian soil, in the Mediterranean, outside established war-risk zones**
   (Splash247 explicitly frames it as the first such attack beyond the
   Hormuz/Red Sea concentration). The existing language does not describe it
   and cannot absorb it.
2. **It sits inside the window that matters.** With `full_end` extended to
   ≥ 2026-08-01 (§4), 2026-07-29 is in-window. For the **PortWatch Hormuz
   transit primary** the direct effect is plausibly nil (a Mediterranean
   terminal attack does not mechanically move Hormuz transit counts), but it
   can affect (a) **donor corridors** (Suez/East-Med risk perception —
   relevant to the contamination screen's "clean pool"), (b) the **restricted
   Fearnleys secondary freight series** (war-risk premia, esp. West-of-Suez;
   18 post-cutoff weeks are in scope), and (c) the **importer panel** (Egypt
   is a unit in `destination_basin_by_country`; its import capability was
   shocked by a non-Hormuz event mid-window).
3. **Attribution is unresolved.** If it is Iran-linked (unproven), it is
   arguably part of the same conflict complex — which raises a genuine
   methodological question: is it a *confound* or an *extension of the
   treatment*? That classification changes how the extended-window
   "disruption-associated shortfall" language must be worded, and it is
   **Mher's call, not a logging default.**

### 1.4 Recommended action — **requires Mher's sign-off**

- Add to `EVENT_CHRONOLOGY.md` as a dated context event (not a treatment
  candidate, not a placebo date), with the Cabinet statement as anchor and
  attribution flagged unresolved.
- Add a short section to `SUTVA_CONTAMINATION_AUDIT.md`: "Non-Hormuz LNG
  supply-side shocks inside the extended window," naming Damietta explicitly
  and stating which layers it can touch (donor Suez corridor, Fearnleys
  secondaries, importer panel — not the within-unit AR primary).
- Record in `DECISION_LOG.md` the treatment-vs-confound classification Mher
  chooses, with one sentence of justification.

---

## 2. Chronology extension through 2026-08-01

`EVENT_CHRONOLOGY.md` currently ends with the March 2026 ledger (last audit
2026-06-19); `settings.yaml` context milestones end at 2026-04-18. The
following verified events fill April–July. All are **context/annotation
events only** — none is a treatment candidate, and the 2026-02-28 training
cutoff does not move.

| Date | Event | Sourcing quality | Duplicate check | Action |
|---|---|---|---|---|
| 2026-04-07/08 | US–Iran **ceasefire**; major combat halts; US says Strait "set to open," but traffic remains restricted and Iran routes ships through its territorial waters, attacking noncompliant vessels | CRS R45281 (primary-adjacent), UK House of Commons Library briefing, ABC timeline | New (chronology currently jumps 03-27 → 04-18) | **Add** |
| 2026-04-18 | Iran formal closure statement | — | **Already logged** (placebo/falsification date) | Keep; note it post-dates the ceasefire |
| 2026-06-17 | **US–Iran 14-point Memorandum of Understanding** (Trump/Pezeshkian): removal of US naval blockade; Iranian "arrangements for the safe passage of commercial vessels with no charge, for 60 days only" | CRS R45281; Al Jazeera explainer "What has happened since the US-Iran MoU on June 17?" (2026-07-09); ABC timeline; corroborated by EIA TIE #67865 (Brent declined after 06-17) | New — and **load-bearing for v2/v3 interpretation**: the extended window spans closure → attempted reopening → renewed closure | **Add** |
| ~2026-06-25/28 | Iran drone strike on a vessel in the Strait "just over a week after" the MoU; US responds with contained strikes | ABC timeline (exact date not pinned in this review) | New | **Add only after pinning the exact date** — currently approximate; do not log a fuzzy date |
| 2026-07-07 | Iran attacks **three commercial ships in 24 hours**; widely read as MoU breakdown | Axios, CNN, Al Jazeera (3 independent outlets, same date) | New | **Add** |
| 2026-07-19/20 | Renewed tanker attack amid **10th consecutive night of US strikes** (i.e., campaign resumed ~07-10/11) | Washington Post | New; single-outlet in this review — treat as milestone of an ongoing campaign, not a discrete onset | **Add with single-sourced flag** |
| 2026-07-27/29 | Iran–Oman exchange of proposals on Strait administration; Iran **rejects Oman's joint-oversight proposal** on 07-29 | Bloomberg (07-27), Al Jazeera (07-29) | New | **Add** |
| 2026-07-29 | **Damietta attack** (§1) | See §1 | New | **Add per §1, with sign-off** |

**Post-window context (after 2026-08-01, do not log inside the study window;
optional "subsequent developments" note only):** Iran–Oman deal reported in
"final stages" (CNBC, 08-05); Iran announces an agreement with Oman
prohibiting US/Israeli vessels with fines up to 20% of cargo value (NPR,
08-07); UAE says Iran attacked an ADNOC-linked vessel with a missile
(gCaptain, 08-08). These matter for thesis framing ("the episode was not
resolved at window close") but are outside the requested coverage.

**Duplicate check vs the 2026-03-27 IRGC ship ban:** the announced Iran–Oman
vessel ban (08-07) is a **distinct, later, treaty-framed event** — not a
re-report of the unilateral March IRGC ban. If it is ever logged, label it as
such to avoid conflation. The candidate list's "Iran considering a new ship
ban" as a discrete late-July dated story could **not** be independently pinned
(§8) — what verified is the ban *materializing* in the 08-07 announcement.

---

## 3. Study-window extension (`study_window.full_end`)

Current: `full_end: 2026-07-07` (v2 = PortWatch max 2026-07-12 minus 5-day
buffer). Goal per request: capture at least 2026-08-01, which would bring the
07-07 attacks, the 07-19/20 escalation, the Iran–Oman proposals, and Damietta
inside the window.

- **PortWatch:** must be re-downloaded fresh (browser download per
  `WINDOW_EXTENSION_V2_RUNBOOK.md` Phase 1). PortWatch updates weekly; a
  download this week should carry data to early August. **Rule stays the
  runbook's rule: new `full_end` = max complete date − 5 days.** If the fresh
  snapshot's max is ≥ 2026-08-06, `full_end` ≥ 2026-08-01 is achievable. Do
  not pre-commit a date before seeing the snapshot.
- **WTO/AXSMarine tracker — live check, 2026-08-09:** the public blob now
  spans **2025-01-01 → 2026-08-09**. *(Corrected 2026-08-09 after the
  registry-sanctioned refresh: the post-cutoff index is not uniformly 0.0. It
  is zero on 155 of 163 post-cutoff days with eight isolated partial-loading
  days — see `WINDOW_EXTENSION_V2_RUNBOOK.md` v3 note. The defensible claim is
  **no sustained LNG resumption**, including after the 06-17 MoU.)* Two
  governance consequences: (a) the runbook's "tracker frozen/lagging at 2026-06-01"
  concern is resolved — the corroboration layer **can** extend; (b) the
  "rolling window already dropped Jan–Feb 2025" warning is **not borne out**
  as of today (start date still 2025-01-01). This observation must be
  re-established via `scripts/fetch_wto_hormuz_lng.py` (registry path) before
  any use — this memo's fetch is verification only.
- **Interpretive obligation:** a v3 window spanning
  closure → MoU/partial-reopening attempt → renewed attacks is a **regime
  mixture**, not "more of the same closure." The persistence write-up must
  say so, anchored on the 06-17 and 07-07 chronology entries. The Damietta
  confound (§1) is inside the extension tail and must be cross-referenced.
- **Governance:** v1 (2026-06-01) remains the pre-registered primary window;
  v2 remains what it is; the extension is a documented v3 following the same
  runbook. Cutoff 2026-02-28, sensitivity dates, and (unless deliberately
  revisited) the matched WTO `comparison_windows` do not move — though (b)
  above means extending the WTO validation is now *possible* and is a design
  choice, not a data constraint. **Window change = methodological decision
  requiring Mher's sign-off; the runbook execution itself is mechanical.**

---

## 4. EIA "Today in Energy" candidates

All five dates verified against the EIA archive. None is currently cited or
registered (the chronology cites two *different* TIE pieces: #67604 and
#67046).

| Date | id | Title (verified) | What it is | Recommendation |
|---|---|---|---|---|
| 2026-01-27 | 67064 | "Crude oil tanker rates reached multi-year highs in late 2025" | Pre-treatment tanker-rate context; underlying rates are **Argus Freight (proprietary)** | **Citation only** (pre-treatment market-context / confounder narrative). **Not a registry variable** — no free series behind it |
| 2026-02-17 | 67184 | "Maritime exports of petroleum products increased in January 2026" | Pre-treatment petroleum-trade context | **Citation only, low priority** (petroleum, not LNG/freight) |
| 2026-03-26 | 67386 | "Middle East crude oil tanker rates reached a multi-decade high in March" | In-crisis market observation; **independently corroborates the 2026-03-02 closure date** already logged | **Citation** in the event-study annotation; corroborating source for the `closure_declaration` milestone. Not a registry variable (Argus again) |
| 2026-07-14 | 67864 | "Global liquefied natural gas trade volumes reached record high in 2025" | GIIGNL-sourced annual 2025 LNG trade record (56.3 Bcf/d, +5.4%; US 15.1 Bcf/d) | **Citation**; additionally useful as a **partial cross-check on the [VERIFY]-flagged GIIGNL figures** in `CAPTIVITY_EVENT_STUDY_DESIGN.md` §14 — it confirms the GIIGNL 2026 report exists and gives independent headline numbers. Annual data → not a panel registry variable |
| 2026-07-15 | 67865 | "Petroleum markets responded to disruptions in the Middle East in the second quarter" | Q2 narrative: Brent $118 (04-29) high → $72 (06-26) low; **documents the 06-17 MoU**; no LNG content | **Citation** + chronology corroboration for the 06-17 MoU entry. Brent itself is already covered by the free `brent_spot` registry variable — no new variable |

**Summary: zero new registry variables from EIA TIE** (the underlying
freight-rate data is proprietary Argus; prices are already registered; GIIGNL
is annual). Their value is chronology corroboration and pre-treatment/placebo
*narrative* context. If any TIE chart value is quoted in the thesis, cite the
article, not a reconstructed series.

## 5. IEA candidates

All four items verified on iea.org with exact titles/dates:

1. "From Hormuz to the pump: Why oil price shocks hit consumers differently" —
   commentary, **2026-07-09** (Bressers & Codrington).
2. IEA Executive Director statement on oil markets — **2026-07-21**.
3. "Governments … commit to making energy efficiency a cornerstone of energy
   policy amid Strait of Hormuz crisis" — **2026-06-29**.
4. "Global demand for natural gas expected to contract this year as tighter
   supply pushes up prices" — **2026-07-07**.

**Should IEA become a tracked source class? Recommendation: no registry
source class.** These are commentary/news, not series; IEA's underlying data
products are largely paid. Nothing here enters the quantitative pipeline, so
`sources.yaml` (the swap-in layer for *variables*) is the wrong home.
Recommended handling: cite (1) and (4) in the Discussion — (4) is the
demand-side context for H3/substitution framing (global gas demand
contracting as supply tightens); (2) and (3) are optional color. If a future
draft quotes an IEA *number* (e.g., a demand-contraction percentage), that
number needs a primary check against the underlying IEA report first
(CITATION_INTEGRITY_AUDIT standard). This is a documented scope decision, not
a silent omission — record one line in `DECISION_LOG.md` if adopted.

## 6. arXiv methodology candidates

| ID | Verified identity | Relevance check | Recommendation |
|---|---|---|---|
| 2407.07652 | Fontagné, Micocci & Rungi, "The heterogeneous impact of the EU-Canada agreement with causal machine learning" (v5 2026-06-05) — **matrix-completion counterfactual** on firm×product×destination trade data (CETA) | Genuinely adjacent to two pieces of the design: the synthetic-control corroboration layer (matrix completion is the modern generalization of SCM-style counterfactuals) and the captivity design's causal-ML heterogeneity arm | **Optional literature-matrix add (Section C, methodological)** as "matrix-completion counterfactual precedent on trade data." Does not change any estimator. Note it is an *application* paper; if a canonical method cite is wanted instead, that is Athey et al.'s matrix-completion work — adding that instead/as well is Mher's choice |
| 2608.04839 | Halkiewicz, "Exact Inference in Fixed-Effect Regressions with Concentrated Identifying Variation" (v1 **2026-08-05**) — exact finite-sample sign-flip inference via nuisance-annihilating contrasts when identifying variation is concentrated | Directly on-point for the **small-N / wild-cluster-bootstrap limitation** flagged in `CAPTIVITY_EVENT_STUDY_DESIGN.md` §5/§9 (one shock, ~20–40 importers = concentrated identifying variation) | **Add as a limitations-section citation**: "exact-inference alternatives exist for this setting." **Do not re-implement inference before 09-01** — the paper is a 4-day-old, single-author, unrefereed preprint. Citing it as a pointer is safe; building on it is not |
| 2608.04469 | Flament, Hurlin, Lajaunie & Pull, "Generalized Impulse Responses of Portfolio Default Probabilities … Application to Geopolitical Risk" (2026-08-05) | Portfolio **credit risk** (BVAR + Merton-Vasicek); geopolitical-risk shocks to default probabilities | **Skip.** Wrong outcome domain; the GPR connection is already covered by Caldara & Iacoviello 2022 in the matrix |
| 2608.05017 | Yang & Zha, "Algorithm-Driven SVARs: Navigating the Wilderness of Big Data" (2026-08-05) | Bayesian variable selection for macro SVARs | **Skip.** No SVAR layer exists or is planned in the design |

## 7. Shipping/industry news (gCaptain, Splash247) through 2026-08-01

Covered event-by-event in §2. Source-class note: gCaptain and Splash247
verified as consistent with wire/primary accounts on every event checked here
(Damietta, renewed attacks, ADNOC vessel). Recommendation: keep them as
**secondary corroborating sources in chronology entries** — never the sole
anchor where a governmental/institutional record exists (Egyptian Cabinet,
CRS, DoD). No registry implication.

## 8. User-supplied Bloomberg chart PDFs (received 2026-08-07/09)

Three Bloomberg Charts exports were supplied outside the repo
(`../LNG Tanker 1.PDF` mtime 2026-08-07, `../LNG Tanker 2.PDF` and
`../LNG Tanker 3.PDF` mtime 2026-08-09). They are **chart images with legend
statistics, not data payloads**. Content, as read from the PDFs:

| File | Bloomberg ticker | Series | Legend statistics shown |
|---|---|---|---|
| LNG Tanker 1 | **FLNG1YTC Index** | LNG 1 Yr TC Suez $/Day | Last 44,000; High 190,000 on 2022-11-11; Average 73,718.33; Low 15,000 on 2025-02-14 |
| LNG Tanker 2 | **FLNGEASZ Index** | LNG East Suez $/Day | Last 47,000; High 325,000 on 2022-10-21; Average 69,592.76; Low 2,000 on 2025-02-07 |
| LNG Tanker 3 | **FLNGWTSZ Index** | LNG West Suez $/Day | Last 35,000; High 375,000 on 2022-10-21; Average 72,626.70; Low **0.00 on 2025-01-31** |

Assessment:

1. **They close a named provenance gap.** `DATA_SOURCES.md` states the repo
   "does not hold the exact Bloomberg identifiers" for the three restricted
   Fearnleys series. These PDFs supply them: `FLNG1YTC`, `FLNGEASZ`,
   `FLNGWTSZ` (Fearnleys LNG assessments distributed via Bloomberg), matching
   `fearnleys_lng_one_year_time_charter`, `fearnleys_lng_spot_east_suez`, and
   `fearnleys_lng_spot_west_suez` respectively.
2. **They cross-validate the transcribed workbooks — check RUN 2026-08-09,
   all six anchors matched.** Each chart's High and Low match the
   corresponding transcription on **both value and date**, and each chart
   extreme is also the workbook extreme over the 2022–2026 overlap
   (all three files: 230 rows, no nulls, 2022-01-07 → 2026-07-03):

   | Series | Chart high | Workbook | Chart low | Workbook |
   |---|---|---|---|---|
   | FLNGEASZ | 325,000 @ 2022-10-21 | ✅ same | 2,000 @ 2025-02-07 | ✅ same |
   | FLNGWTSZ | 375,000 @ 2022-10-21 | ✅ same | 0.00 @ 2025-01-31 | ✅ same |
   | FLNG1YTC | 190,000 @ 2022-11-11 | ✅ same | 15,000 @ 2025-02-14 | ✅ same |

   Two consequences beyond identifier confirmation: (a) the West Suez
   **0.00 on 2025-01-31 appears in Bloomberg's own charted series**, so the
   masked zeros are **not transcription artifacts** — whether they are
   genuine market assessments is still unverified and the analysis mask is
   unchanged; (b) the charts show a sharp 2026 post-onset spike (West to
   ~200k $/day) before settling, qualitative corroboration of the disruption
   signature in the restricted layer. The chart **Averages** span 2018–2026
   and are not comparable to the 2022-start transcriptions; they were not
   used.
3. **What they do not change.** No new analyzable data (images only); the
   Bloomberg/Fearnleys **reuse-rights question remains open**, and Bloomberg
   chart exports carry their own redistribution restrictions — do not place
   these charts in the thesis. Status of the three series stays
   `restricted`; the chart legend "Last Price" values carry no visible as-of
   date beyond the x-axis reaching mid-2026, so they must not be transcribed
   as dated observations.

Actions taken 2026-08-09 (approved): (a) `bloomberg_identifier` filled for the
three Fearnleys entries in `config/bloomberg_exports.yaml` with the evidence
recorded inline, cross-referenced from `config/sources.yaml`, and the
"identifiers unknown" caveat in `DATA_SOURCES.md` downgraded to "identifiers
known, rights unverified"; (b) PDFs archived to
`data/raw/bloomberg_transcription/originals/charts/` under ticker-based names
with a SHA-256 capture README; (c) cross-check run and recorded in
`DECISION_LOG.md`. Note the admission audit's
`exact_bloomberg_identifier_present` gate now passes for these three series —
this narrows a provenance gap but does **not** admit them to the pipeline:
`rights` fields are still null, so the branch stays dormant.

## 9. Could not verify — flagged, not guessed

1. **Exact date of the first post-MoU strike (~2026-06-25/28).** ABC's
   timeline places it "just over a week after" 06-17, but this review did not
   pin the day. Do not log until pinned.
2. **A discrete late-July "Iran considering a new ship ban" story
   (Splash247).** Not found as a dated item in this review; the ban element
   verified only as part of the 2026-08-07 Iran–Oman agreement announcement
   (post-window). Treat the "considering" story as unverified.
3. **Damietta attribution** (§1.1) — unresolved by design; log as such.
4. **PortWatch current max date** — knowable only from a fresh download;
   deliberately not asserted here.

---

## 10. What to act on before 2026-09-01

### Safe to log now (chronology/context; no methodological change)

1. **Extend `EVENT_CHRONOLOGY.md`** with the verified April–July entries
   (§2): 04-07/08 ceasefire, 06-17 MoU, 07-07 attack resumption, 07-19/20
   escalation (flagged single-sourced), 07-27/29 Iran–Oman proposals. Keep
   all as context milestones; cutoff and treatment candidates untouched.
2. **Add citations**: EIA TIE #67386 (corroborates 03-02), #67865
   (corroborates 06-17 MoU), #67864 (GIIGNL cross-check), #67064
   (pre-treatment tanker-rate context); IEA 07-07 gas-demand commentary in
   the Discussion.
3. **Literature matrix**: add arXiv 2608.04839 as a limitations-pointer and
   (optionally) 2407.07652 as a Section-C methodological precedent. Skip
   2608.04469 and 2608.05017 — one line in the search log
   (`LITERATURE_SEARCH_LOG.md`) noting they were screened and excluded.
4. **Bloomberg tickers (§8):** record `FLNG1YTC`/`FLNGEASZ`/`FLNGWTSZ`
   against the three `fearnleys_*` registry entries and in
   `DATA_SOURCES.md`; archive the three PDFs into the provenance area; run
   the chart-extremes cross-check against the transcribed workbooks. Safe —
   it only *narrows* an existing documented provenance gap; rights status
   stays "unverified" and the series stay `restricted`.

### Requires a methodological decision from Mher first

5. **Damietta classification (the big one):** confound vs
   treatment-extension, and the corresponding SUTVA-audit section + wording
   of the extended-window shortfall claim (§1.4). Decide before the v3
   run so the write-up and the window share one story.
6. **Window extension to v3 (`full_end` ≥ 2026-08-01):** approve the
   runbook-rule extension (fresh PortWatch download, `full_end` = max − 5
   days), acknowledging the regime-mixture interpretation (§3) and that
   Damietta then sits in-window. Mechanical execution follows
   `WINDOW_EXTENSION_V2_RUNBOOK.md` unchanged.
7. **WTO validation window:** now that the live tracker reaches August
   (verified 08-09, pending registry re-fetch), decide whether the matched
   YoY `wto_departure_validation.comparison_windows` stay at v1 (default,
   conservative) or a documented extension is made. Do not stretch silently.
8. **IEA scope decision:** adopt the "citations, no source class"
   recommendation (§5) with a one-line `DECISION_LOG.md` entry, or overrule.

Items 1–4 are low-risk and reversible; items 5–7 shape how the thesis's
headline claim is worded and should be settled in one sitting before the v3
rebuild. Nothing in this memo moves the 2026-02-28 cutoff.
