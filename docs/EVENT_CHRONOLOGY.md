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
  historical source. Hormuz tanker transits are 53 on 27 February, 44 on
  28 February, 7 on 1 March, 2 on 2 March, and 0 on 4 March.

## Locked modeling rule

**Primary pre-treatment cutoff: 2026-02-28.** Models train on dates strictly
before 28 February and score the post period beginning on 28 February. This is
the earliest defensible operational onset for the current tanker-throughput
estimand: the US operation began and the observed PortWatch series first breaks
on that date. It does not assert that every later declaration, commercial
decision, or physical damage event began simultaneously.

Later milestones define sensitivity scoring windows only. They never move
disrupted observations into training.

## Event ledger

| Slot | Event | Date | Evidentiary role | Modeling role |
|---|---|---|---|---|
| `kinetic_trigger` | US CENTCOM operation begins; first observed throughput break | **2026-02-28** | DoD record plus internal PortWatch series | **Primary cutoff and anchored window** |
| `closure_declaration` | Public closure-confirmation milestone | **2026-03-02** | Authoritative reporting; operational collapse already underway | Anchored sensitivity window |
| `force_majeure` | QatarEnergy declares force majeure after stopping LNG production | **2026-03-04** | QatarEnergy primary announcement | Anchored sensitivity and donut boundary |
| `ras_laffan_damage` | Later attacks damage Ras Laffan facilities and reduce capacity | **2026-03-18/19** | QatarEnergy primary statements | Separate escalation; not force-majeure date |
| `regime_consolidation` | No discrete, verifiable event | - | Unsupported analyst construct | Dropped |

## Date rationale

**Kinetic and operational onset: 2026-02-28.** The US Department of Defense
records CENTCOM commencing Operation Epic Fury at 01:15 on 28 February. The
AIS-derived series is consistent: the first break is that day, followed by a
near-total collapse on 1-4 March. Because the cutoff is exclusive for training,
this prevents the first affected day from entering model fitting.

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

Source verification flagged Henry Hub spot values of $30.72 on 23 January and
$30.57 on 26 January. EIA reporting supports treating this as a real weather
shock rather than a data error. It occurred roughly five weeks before the
primary cutoff and must not be winsorized or attributed to the Hormuz event.

## Sources

- [Operation Epic Fury fact sheet - US Department of Defense (primary)](https://media.defense.gov/2026/Mar/29/2003904283/-1/-1/1/OPERATION-EPIC-FURY-FACT-SHEET-THE-FIRST-29-DAYS.PDF)
- [QatarEnergy news archive - production stop, force majeure, and Ras Laffan statements (primary)](https://www.qatarenergy.qa/en/Pages/vHome.aspx)
- [International LNG prices rise amid Strait of Hormuz closure - EIA](https://www.eia.gov/todayinenergy/detail.php?id=67604)
- [Severe winter weather and natural gas prices - EIA](https://www.eia.gov/todayinenergy/detail.php?id=67046)

