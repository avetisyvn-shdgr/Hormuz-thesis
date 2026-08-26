# Event chronology and treatment-cutoff rule

**Status:** Re-audited 2026-06-19 after a primary-source conflict was found.
Extended 2026-08-09 with post-March context events through 2026-08-01 (see
`DATA_REGISTRY_REVIEW_2026-08.md` for verification detail). This document
controls the event labels used by the working implementation.

## Purpose

The model needs one leakage-safe training boundary, while the historical record
contains distinct military, operational, legal, and commercial milestones.
Treating these as interchangeable "treatment dates" caused the force-majeure
date to drift between 4 March and 25/26 March. This audit assigns one date to
each event and locks the modeling rule separately.

## Method and caveats

- News is media observation, not ground truth. Primary institutional records
  lead: the US Department of Defense for the kinetic onset and QatarEnergy for
  its production and force-majeure decisions.
- Single-sourced or contested events remain labelled as such.
- The internal PortWatch series is a measurement cross-check, not an independent
  historical source or a treatment-date selector. In the pinned vintage, Hormuz
  tanker transits are 35 on 27 February, 35 on 28 February, 10 on 1 March,
  2 on 2 March, and 0 on 4 March. See `PORTWATCH_VINTAGE_REGISTER.md`.

## Locked modeling rule

**Primary pre-treatment cutoff: 2026-02-28.** Models train on dates strictly
before 28 February and score the post period beginning on 28 February. This is
the earliest defensible operational onset for the current tanker-throughput
estimand under the outcome-blind external rule: the US operation began at 01:15
that day. The pinned PortWatch series is unchanged from 27 to 28 February and
then falls sharply on 1 March, so it is not used to select the cutoff. The
outcome was inspected during the chronology audit; the date is therefore not
presented as an ex ante preregistered choice. It does not assert that every
later declaration, commercial decision, or physical damage event began
simultaneously.

Later milestones define sensitivity scoring windows only. They never move
disrupted observations into training.

## Event ledger

| Slot | Event | Date | Evidentiary role | Modeling role |
|---|---|---|---|---|
| `kinetic_trigger` | US CENTCOM operation begins | **2026-02-28** | DoD fact sheet (external operational-onset rule) | **Primary cutoff and anchored window** |
| `closure_declaration` | Public closure-confirmation milestone | **2026-03-02** | Authoritative reporting; operational collapse already underway | Anchored sensitivity window |
| `force_majeure` | QatarEnergy declares force majeure after stopping LNG production | **2026-03-04** | QatarEnergy primary announcement | Anchored sensitivity and donut boundary |
| `ras_laffan_damage` | Later attacks damage Ras Laffan facilities and reduce capacity | **2026-03-18/19** | QatarEnergy primary statements | Separate escalation; not force-majeure date |
| `regime_consolidation` | No discrete, verifiable event | - | Unsupported analyst construct | Dropped |

## Date rationale

**Kinetic and operational onset: 2026-02-28.** The US Department of Defense
records CENTCOM commencing Operation Epic Fury at 01:15 on 28 February. This
external event rule fixes the training boundary independently of the outcome.
The pinned AIS-derived series is 35 on both 27 and 28 February, then falls to
10 on 1 March, 2 on 2 March, and 0 on 4 March. Because the cutoff is exclusive
for training, no observation at or after the external operational onset enters
model fitting. The outcome was inspected during the chronology audit, so the
choice is disclosed as externally anchored rather than ex ante preregistered.

**Closure-confirmation milestone: 2026-03-02.** This date is retained as a
scoring-window sensitivity, not as the primary training boundary. Moving the
training cutoff here would admit already affected 28 February and 1 March
observations and create leakage.

**QatarEnergy force majeure: 2026-03-04.** QatarEnergy's own archive says it
stopped LNG production on 2 March, stopped some downstream production on
3 March, and declared force majeure on 4 March. The former 25/26 March entry
conflated this declaration with later contractual reporting and the separate
18-19 March attacks that damaged Ras Laffan capacity. That damage remains an
important escalation, but it is not the original force-majeure date.

**Regime consolidation: dropped.** The closure hardened gradually, so assigning
a single 10 March consolidation date would create a false precision. Persistence
is evaluated with rolling post-period windows instead.

## Implication for implementation

- `study_window.primary_treatment_cutoff` controls all training and validation.
- `study_window.treatment_candidates` controls annotated and scored sensitivity
  windows only.
- The donut sensitivity excludes 28 February through 4 March and begins scoring
  on 5 March.
- After changing any date, re-run the event-study and treatment-window scripts
  so figures and processed tables remain synchronized.

## Post-March context chronology (added 2026-08-09, coverage through 2026-08-01)

These are **context/annotation events only**: none is a treatment candidate,
none moves the 2026-02-28 training boundary, and none redefines a sensitivity
window without a separate documented decision. All were verified against the
sources listed below on 2026-08-09; single-sourced items are flagged. News
remains observation, not ground truth.

| Date | Event | Sourcing | Flags |
|---|---|---|---|
| **2026-04-07/08** | US–Iran ceasefire; major combat halts. US statements say the Strait is "set to open," but traffic remains restricted; Iran routes ships through its territorial waters and attacks noncompliant vessels | CRS R45281; UK House of Commons Library CBP-10637; ABC News timeline | Multi-sourced |
| 2026-04-18 | Iran formal closure statement (already logged as placebo/falsification date) | — | Note: post-dates the ceasefire; both are real, the sequence is not contradictory — closure terms were asserted amid ceasefire |
| **2026-06-17** | US–Iran 14-point Memorandum of Understanding (Trump/Pezeshkian): removal of US naval blockade; Iranian arrangements for safe passage of commercial vessels "with no charge, for 60 days only" | CRS R45281; Al Jazeera MoU explainer (2026-07-09); ABC News timeline; corroborated by EIA TIE #67865 (Brent declined after 06-17) | **Load-bearing for v2/v3 interpretation**: the extended window spans closure → attempted reopening → renewed closure. The WTO LNG outbound index shows **no sustained resumption** after the MoU — three isolated partial-loading days (06-28, 07-05, 07-06, at 26–29 vs a 2025 base of 100) followed by 34 consecutive zeros through 08-09 |
| ~2026-06-25/28 | First post-MoU Iranian strike on a vessel in the Strait; contained US response | ABC News timeline ("just over a week after" 06-17) | **Date not pinned — do not use as a dated event until confirmed** |
| **2026-07-07** | Iran attacks three commercial ships in 24 hours; widely read as the MoU breakdown | Axios; CNN; Al Jazeera (three independent outlets, same date) | Multi-sourced |
| 2026-07-19/20 | Renewed tanker attack amid the 10th consecutive night of US strikes (campaign resumed ~07-10/11) | Washington Post | **Single-sourced in the 2026-08-09 review**; milestone of an ongoing campaign, not a discrete onset |
| **2026-07-27/29** | Iran–Oman exchange of proposals on Strait administration; Iran rejects Oman's joint-oversight proposal on 07-29 | Bloomberg (07-27); Al Jazeera (07-29) | Multi-sourced |
| **2026-07-29** | **Damietta terminal attack (Egypt)** — drone strikes the FSRU Energos Winter alongside at the Damietta LNG terminal; fire spreads to the LNG carrier GasLog Salem (155k m³). No casualties; Egyptian officials state supplies secured | Egyptian Cabinet statement (UAV attribution; via Egypt Oil & Gas); Splash247; Al Jazeera; CNBC | **Non-Hormuz confound event** — see `SUTVA_CONTAMINATION_AUDIT.md` and `DECISION_LOG.md` 2026-08-09. Attribution **unresolved** (no claim of responsibility; "Iran chief suspect" is press inference); early technical-malfunction accounts conflict with the Cabinet statement |

**Post-window developments (after 2026-08-01; context for framing only, not
window events):** Iran–Oman deal reported in "final stages" (CNBC, 08-05);
Iran announces an Iran–Oman agreement prohibiting US/Israeli vessels with
fines up to 20% of cargo value (NPR, 08-07) — a **distinct, treaty-framed
event, not a re-report of the unilateral 2026-03-27 IRGC ban**; UAE says Iran
attacked an ADNOC-linked vessel with a missile (gCaptain, 08-08). The episode
was not resolved at window close.

## Pre-treatment confounder: January 2026 Henry Hub spike

The frozen EIA series records a local maximum of $30.72/MMBtu on 23 January,
followed by $25.01 on 26 January, $17.19 on 27 January, and $9.34 on 28 January
(`data/raw/eia/henry_hub_spot__NG_RNGWHHD_D.csv`). The sequence is therefore a
sharp 23 January peak followed by a decline, not a 26 January spike.
Contemporaneous EIA reporting identifies severe winter weather as the context
for late-January natural-gas price pressure. This pre-treatment shock occurred
roughly five weeks before the primary cutoff and must not be winsorized or
attributed to the Hormuz event.

## Sources

- [Operation Epic Fury fact sheet - US Department of Defense (primary)](https://media.defense.gov/2026/Mar/29/2003904283/-1/-1/1/OPERATION-EPIC-FURY-FACT-SHEET-THE-FIRST-29-DAYS.PDF)
- [QatarEnergy news archive - production stop, force majeure, and Ras Laffan statements (primary)](https://www.qatarenergy.qa/en/Pages/vHome.aspx)
- [International LNG prices rise amid Strait of Hormuz closure - EIA](https://www.eia.gov/todayinenergy/detail.php?id=67604)
- [Severe winter weather and natural gas prices - EIA](https://www.eia.gov/todayinenergy/detail.php?id=67046)

Post-March context chronology (2026-08-09 extension):

- [The Strait of Hormuz: Security Developments and Impacts - CRS R45281](https://www.congress.gov/crs-product/R45281)
- [US-Iran ceasefire and nuclear talks in 2026 - House of Commons Library CBP-10637](https://commonslibrary.parliament.uk/research-briefings/cbp-10637/)
- [How the US-Iran ceasefire and MOU broke down - ABC News timeline](https://abcnews.com/Politics/us-iran-ceasefire-mou-broke-timeline/story?id=134622392)
- [What has happened since the US-Iran MoU on June 17? - Al Jazeera](https://www.aljazeera.com/news/2026/7/9/strait-of-hormuz-what-has-happened-since-the-us-iran-mou-on-june-17)
- [Iran attacks three ships in 24 hours - Axios](https://www.axios.com/2026/07/07/iran-resumes-hormuz-attacks-us-officials) / [CNN](https://www.cnn.com/2026/07/07/middleeast/hormuz-tanker-iran-attack-intl-hnk) / [Al Jazeera](https://www.aljazeera.com/news/2026/7/7/ships-attacked-in-the-strait-of-hormuz-what-that-means-for-ongoing-talks)
- [Another tanker attacked as US strikes Iran for 10th consecutive night - Washington Post](https://www.washingtonpost.com/business/2026/07/19/iran-us-hormuz-strait-war-july-20-2026/85f64c6e-83ed-11f1-9cec-0fb26676f07e_story.html)
- [Iran-Oman talks focused on restarting Hormuz shipping - Bloomberg](https://www.bloomberg.com/news/articles/2026-07-27/iran-oman-talks-focused-on-restarting-hormuz-shipping-traffic) / [Iran and Oman swap proposals - Al Jazeera](https://www.aljazeera.com/news/2026/7/29/iran-and-oman-swap-proposals-to-manage-strait-of-hormuz-what-we-know)
- [Cabinet: Blaze on FSRU at Damietta Port Caused by Drone - Egypt Oil & Gas](https://egyptoil-gas.com/news/cabinet-drone-attack-sparked-blaze-on-fsru-at-damietta-port/) (closest-to-primary for Damietta)
- [Drone strike hits FSRU and LNG carrier at Egyptian terminal - Splash247](https://splash247.com/drone-strike-hits-fsru-and-lng-carrier-at-egyptian-terminal/)
- [Petroleum markets responded to Middle East disruptions in Q2 - EIA TIE #67865](https://www.eia.gov/todayinenergy/detail.php?id=67865) (corroborates the 06-17 MoU)
- [Middle East crude oil tanker rates reached a multi-decade high in March - EIA TIE #67386](https://www.eia.gov/todayinenergy/detail.php?id=67386) (independently corroborates the 03-02 closure milestone)
