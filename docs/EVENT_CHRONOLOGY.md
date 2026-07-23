# Event chronology and treatment-cutoff rule

**Status:** Re-audited 2026-06-19 after a primary-source conflict was found.
This document controls the event labels used by the working implementation.

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
