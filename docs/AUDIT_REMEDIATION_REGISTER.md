# AUDIT REMEDIATION REGISTER — Single Source of Truth

**Created:** 2026-07-23
**Owner:** Mher Avetisyan (mher.avetisyan@tum.de)
**Provenance:** Consolidated and deduplicated from five independent adversarial
audits of this repository (referred to below as **A1**–**A5**):

- **A1 — Methodological rigor** (identification vs prediction)
- **A2 — Code & solution quality**
- **A3 — Data-source legitimacy**
- **A4 — Analysis & judgement quality**
- **A5 — Meta / fabrication & AI-generation tells**

Two factual conflicts left open by the audits were resolved by direct file
inspection on 2026-07-23; see **Section D**. Where an item is confirmed by more
than one audit, the confirming audits are listed — those are the highest-confidence
items and should be trusted without re-litigation.

---

## SECTION A — HOW TO USE THIS DOCUMENT (read first)

This is the **authoritative work plan**. Each defect has a stable ID (e.g.
`INF-01`), a severity, the confirming audits, exact `file:line` locations, the
defect, and the required fix. Work top-to-bottom by priority tier (P0 → P6).

**For the executing assistant:**
1. Treat every fix as a **proposal** until Mher has run the code and pasted back
   real output. Do **not** claim anything "works," "passes," or "is fixed" on your
   own authority. (See Guardrail G4.)
2. Change **one item at a time**. After each, state what to run to verify it.
3. Do **not** modify anything in **Section C (Verified-Solid)** — those are
   correct and load-bearing. "Fixing" them would introduce regressions.
4. Update the **Status** field of each item as you go:
   `TODO → IN PROGRESS → NEEDS-VERIFY → DONE` (or `WONTFIX` with a reason).
5. Never invent numbers, citations, dates, or access rights to close an item. If
   the true value is unknown, mark the item `BLOCKED` and say what is needed.

---

## SECTION B — GUARDRAILS (non-negotiable; from CLAUDE.md)

- **G1 — Never fabricate.** No invented datasets, results, numbers, dates, or
  citations. Unrun code is a hypothesis, label it so.
- **G2 — Prediction ≠ identification.** Forecast accuracy is never evidence of a
  causal effect. Do not reintroduce causal language when closing items.
- **G3 — Chronological splits only.** Never random-split. Training uses
  pre-treatment data only. The locked cutoff is `2026-02-28` (subject to the
  re-examination required by `DATA-01`).
- **G4 — The human runs the code.** Nothing is "done" until Mher pastes real
  output. Assistants propose; they do not certify.
- **G5 — All external data via `registry.get_variable()`** so provenance is logged.
- **G6 — Free vs proprietary honesty.** Respect `config/sources.yaml` status flags;
  a proxy swap is a documented decision, never a silent substitution.

---

## SECTION C — VERIFIED-SOLID (DO NOT CHANGE)

These were checked and confirmed correct across audits. Preserve them.

| ID | Fact | Confirmed by |
|---|---|---|
| OK-1 | Primary AR result recomputes exactly: 130 days, 529 observed vs 7,397.996 counterfactual → 6,868.996 shortfall, 52.84/day | A2, A4, A5 |
| OK-2 | Capacity-nautical-mile aggregation reconstructs (pre 628.245 bn, post 530.191 bn, −15.6%) | A2 |
| OK-3 | No fabricated commercial datasets (Spark/Platts/Bloomberg/ICE/AIS); `unavailable` flags are truthful | A3, A5 |
| OK-4 | Core sources legitimate and live-matched: EIA, PortWatch, WTO, GFW, GEM, Japan e-Stat, Eurostat | A3, A5 |
| OK-5 | No treatment-period training leakage in current primary/BSTS/SCM/TSFM fits | A1 |
| OK-6 | Operational onset 2026-02-28 corroborated by the DoD Operation Epic Fury fact sheet | A5 |
| OK-7 | Core methodological citations real (Brodersen, Abadie, Xu–Xie, Verschuur, Pratson, Yang) | A5 |
| OK-8 | 265 tests pass locally (passing ≠ reproducible; see `REP-01`) | A1, A2, A5 |
| OK-9 | Proxy swaps in the active panel are documented, not silent | A3 |

---

## SECTION D — CONTRADICTIONS RESOLVED THIS SESSION (evidence attached)

**D-1 — PortWatch treatment-window vintage conflict (A3 vs A5).**
Two divergent Hormuz transit snapshots exist in `data/raw/portwatch/`:

| Date | `hormuz_tanker_transits__chokepoint_strait_of_hormuz_n_tanker.csv` | `...__6631382171dc.csv` |
|---|---|---|
| 2026-02-27 | 53 | 35 |
| 2026-02-28 | 44 | 35 |
| 2026-03-01 | 7 | 10 |
| 2026-03-02 | 2 | 2 |
| 2026-03-04 | 0 | 0 |

Repository execution tracing on 2026-07-23 corrected the initial resolution
above: the active `2022-01-01` through `2026-07-07` registry result is the
**suffixed** file with SHA-256 `6631382171dc...`, derived from the July aggregate
snapshot. The unsuffixed `53/44/7` file is an earlier, shorter-window vintage.
Action and the corrected provenance record are tracked as `DATA-01`.

**D-2 — Henry Hub $30.57 (A5) — CONFIRMED FALSE.**
`data/raw/eia/henry_hub_spot__NG_RNGWHHD_D.csv` gives `2026-01-26 = 25.01`. The
value `30.57` appears nowhere; nearest is `2026-01-23 = 30.72`, after which prices
fell (25.01 → 17.19 → 9.34). Action tracked as `INT-01`.

---

## SECTION E — DEFECT REGISTER

Severity: **BLOCKER** (cannot submit) · **CRITICAL** · **HIGH** · **MEDIUM** · **LOW**

### PRIORITY 0 — Governance & scope (submission blockers; resolve first)

#### GOV-01 — Formal estimand/scope not reconciled with approved proposal
- **Severity:** BLOCKER · **Audits:** A1, A4, A5 · **Status:** BLOCKED
- **Where:** `docs/ESTIMAND_PROPOSAL_RECONCILIATION.md:29`,
  `docs/PENDING_ESTIMAND_REALIGNMENT_DRAFT.md:1`, `README.md:7`,
  `docs/DECISION_LOG.md:107`
- **Defect:** The manuscript implements a **descriptive throughput-shortfall**
  estimand, but the formal proposal on file still uses **causal ton-mile / freight
  ATT** framing. Prof. Li's ratification of the reframe is not recorded. This is a
  scope mismatch a committee can reject regardless of statistical quality.
- **Fix:** Complete the formal realignment (update the proposal to the descriptive
  estimand) and obtain/record the required supervisor ratification **before**
  submission. This gates the reframe items (FRM-*).
- **Blocking evidence (2026-07-23):** The archived Zhenyu Wang email verifies
  advisor-side acceptance of the revised title, research question, estimand,
  claim strength, and empirical scope. It does not contain direct Prof. Li
  ratification or state that Zhenyu had delegated authority to approve a formal
  proposal change. `AGENTS.md` therefore still prohibits editing the formal
  proposal. Completion requires either direct written Prof. Li ratification or
  written confirmation of Zhenyu's delegated approval authority. (G1)

#### GOV-02 — Supervisor acceptance email is unauditable
- **Severity:** BLOCKER · **Audits:** A5 · **Status:** DONE
- **Where:** `README.md:7`, `docs/DECISION_LOG.md:107`
- **Defect:** The claim that Zhenyu Wang approved title/RQ/estimand/claim-strength
  by email on 2026-07-23 has **no primary artifact** in the repo (no export,
  screenshot, message ID). The reframe's core defense rests on an unverifiable claim.
- **Fix:** Archive the actual email (raw `.eml`/export + message ID) into the repo
  (e.g. `docs/approvals/`). Establish whether it constitutes delegated authority;
  if not, obtain Prof. Li's direct ratification. Do **not** paraphrase — store the
  primary artifact. (G1)
- **Blocking evidence (2026-07-23):** A repository-wide search found no `.eml`,
  `.msg`, mailbox export, screenshot, message ID, or approval-artifact directory.
  Completion requires Mher to provide the original email/export and confirm
  whether the repository is private enough to retain its unredacted contents.
- **Remediation evidence (2026-07-23):** Mher supplied a five-page PDF print
  export of the complete email thread. It is archived unchanged at
  `docs/approvals/GOV_02_Evidence.pdf`; provenance, evidentiary scope, privacy
  handling, and the SHA-256 checksum are recorded in `docs/approvals/README.md`.
  The artifact verifies Zhenyu's written acceptance but does not establish
  direct Prof. Li ratification or delegated approval authority. It lacks a
  complete RFC `Message-ID`; this limitation is disclosed rather than inferred
  away. Mher supplied the primary artifact directly, satisfying the human-
  evidence requirement for this governance item. (G1, G4)

### PRIORITY 1 — Integrity: false / fabricated specifics

#### INT-01 — Fabricated Henry Hub price ($30.57 → $25.01)
- **Severity:** CRITICAL · **Audits:** A5 (+ verified D-2) · **Status:** DONE
- **Where:** `docs/EVENT_CHRONOLOGY.md:82`,
  `docs/thesis_drafts/manuscript/chapters/02_background_event_chronology.tex:129`
- **Defect:** "Henry Hub was $30.57/MMBtu on 2026-01-26" is false. Actual = 25.01.
  The "spike" in the window is actually 2026-01-23 = 30.72, with prices falling after.
- **Fix:** Correct the value **and** the narrative (the local maximum is Jan 23 =
  30.72, not a Jan 26 spike of 30.57). Verify against
  `data/raw/eia/henry_hub_spot__NG_RNGWHHD_D.csv` before writing any replacement number.
- **Remediation (2026-07-23):** Corrected `EVENT_CHRONOLOGY.md`, the manuscript
  chronology chapter, and the stale `verify_sources.py` comment to report the
  frozen EIA sequence exactly: 30.72 on 23 January, 25.01 on 26 January, 17.19
  on 27 January, and 9.34 on 28 January. The narrative now describes a
  23 January peak followed by a decline. Mher verified the source rows and
  `git diff --check` output on 2026-07-23. (G1, G4)

#### INT-02 — Wan et al. mischaracterised ("spatial" vs "ship-type" heterogeneity)
- **Severity:** HIGH · **Audits:** A5 · **Status:** DONE
- **Where:** `docs/LITERATURE_REVIEW_FOUNDATION_DRAFT.md:30` (repo's own flag:
  `docs/LITERATURE_MATRIX.md:59`)
- **Defect:** Cited as showing "spatially heterogeneous" effects; the verified
  finding is heterogeneity **by ship type**. Dimension mismatch = likely fabrication.
- **Fix:** Rewrite to "heterogeneous by ship type," or drop the claim. Align with
  `LITERATURE_MATRIX.md`.
- **Remediation (2026-07-23):** Direct verification against the official
  ScienceDirect record showed that the audit's either/or diagnosis was too
  narrow: the publisher highlights report both uneven regional impacts and
  ship-type heterogeneity. The literature draft and both matrices now state
  those dimensions explicitly, and `CITATION_INTEGRITY_AUDIT.md` records the
  primary-source resolution. Mher ran `git diff --check` successfully on
  2026-07-23; the requested content search could not run because `rg` is absent
  from the user's shell, so the already-completed workspace content check was
  retained as supporting verification. (G1, G4)

#### INT-03 — Unverified citation specifics (Nguyen et al.; Polemis & Bentsos)
- **Severity:** MEDIUM · **Audits:** A5 · **Status:** DONE
- **Where:** `docs/LITERATURE_REVIEW_FOUNDATION_DRAFT.md:27,55` (repo's own flag:
  `docs/CITATION_INTEGRITY_AUDIT.md:61,68`)
- **Defect:** The four-category taxonomy (Nguyen) and the weekly-data/event-study/
  ARFIMA method details (Polemis & Bentsos) were never full-text confirmed.
- **Fix:** Obtain full text and add page citations, or soften to what is verifiable.
  Do not assert unconfirmed specifics. (G1)
- **Remediation (2026-07-23):** Removed the unverified Nguyen four-category
  taxonomy and replaced it with an abstract-aligned statement about
  disruption-management measures and resilience/performance links. Full-text
  screening of the open-access Polemis and Bentsos article confirmed weekly
  Clarksons data (pp. 5–6), event-study abnormal returns (pp. 8–9), and ARFIMA
  (p. 10); page citations were added to the draft and matrix. Mher verified the
  cited page markers and `git diff --check` output on 2026-07-23. (G1, G4)

### PRIORITY 2 — Invalid inference (highest multi-audit consensus)

#### INF-01 — The "95% interval" and p = 0.028 are invalid as labeled
- **Severity:** CRITICAL · **Audits:** A1, A2, A4, A5 · **Status:** DONE
- **Where (code):** `scripts/run_placebo_inference.py:105-164`,
  `scripts/run_long_horizon_intervals.py:82-100`, `src/lngfreight/inference.py:317-402`
- **Where (claims):** `docs/thesis_drafts/manuscript/chapters/01_introduction.tex:40`,
  `docs/thesis_drafts/manuscript/chapters/05_results_throughput_shortfall.tex:13,16`,
  `reports/current_results_summary.md:15`
- **Defect:** 130-day placebo windows step every 30 days → ~35 **overlapping**
  windows treated as independent. Only **~7 disjoint blocks** exist. The empirical
  2.5–97.5% band (5,430.3–8,088.9) is labeled a "95% interval," and p = 0.028 /
  1/36 is presented as significance. The repo's own block-conformal output
  (`data/processed/block_conformal_summary.csv`) says a finite 95% interval is
  **unbounded** (max finite coverage 87.5%); disjoint-block rank is **p = 0.125**.
- **Fix:** Everywhere the interval/p-value appears (reports **and** manuscript):
  (a) stop calling `5,430–8,089` a "95% interval" — relabel it an *empirical
  overlapping-placebo quantile band* with **no** nominal coverage; (b) lead with the
  honest disjoint-block result: loss exceeds all 35 placebos; rank **p = 0.125**;
  95% conformal **unbounded**. Also fix the Xu–Xie citation (`04_methods.tex:138`):
  it supports conformal methodology generally, not 95% coverage on 7 blocks.
- **Remediation (2026-07-23):** The overlapping-window generator now emits
  explicitly labeled empirical 2.5/97.5% quantile bands with
  `nominal_coverage_supported = False`; the old horizon-matched interval schema
  was removed. Its `1/36` statistic is now an overlapping-window reference rank,
  explicitly not a p-value. Reports and manuscript lead with the seven
  disjoint-block result (`p = 0.125`) and the unbounded nominal 95%
  block-conformal interval (maximum finite coverage 87.5%). Temporal
  Romano–Wolf correction now also uses the seven shared disjoint blocks rather
  than 35 overlapping windows. The Xu–Xie citation is limited to conformal
  methodology generally. Generated artifacts, report generators, manuscript
  prose, and regression tests were updated. Mher ran the 27 focused tests and
  inspected the processed/report outputs on 2026-07-23: seven disjoint blocks,
  `p = 0.125`, unbounded nominal 95% conformal interval, maximum finite coverage
  87.5%, and no nominal coverage/p-value claim for the overlapping diagnostics.
  (G1, G2, G4)

#### INF-02 — Pseudo-replication in donor×time synthetic-stress p-value
- **Severity:** HIGH · **Audits:** A1 · **Status:** DONE
- **Where:** `scripts/run_synthetic_stress.py:49-104`, `reports/run_output.md:64-72`
- **Defect:** 22 donors × 7 windows = 154 fits pooled into one p-value (claimed floor
  1/155). Units within a window share shocks; not 154 independent randomizations.
- **Fix:** Aggregate within the 7 disjoint time blocks or use a joint resampling
  statistic that preserves unit dependence. Do not claim a 1/155 floor.
- **Remediation (2026-07-23):** The 154 donor×time fits are retained as
  descriptive diagnostics but are no longer pooled as independent draws. Each
  of the seven disjoint time windows now contributes one pre-specified
  conservative maximum across its 22 pseudo-units. The treated post/pre RMSPE
  ratio is ranked against those seven block maxima, yielding a max-statistic
  rank `p = 0.125` with floor `1/8`; the old `0.006452` / `1/155` fields and
  claims were removed. The new
  `synthetic_donor_time_block_maxima.csv` records every block statistic, the
  inference artifact declares that a pooled donor×time p-value is unsupported,
  and report/regression-test consumers were updated. Mher reran the stress
  analysis and nine focused tests on 2026-07-23, confirming 154 fits, seven
  22-unit block maxima, pooled support `False`, and block-max rank
  `p = 0.125`. (G2, G3, G4)

#### INF-03 — No placebo pre-fit (RMSPE) screen in SCM p-value
- **Severity:** HIGH · **Audits:** A1 · **Status:** DONE
- **Where:** `scripts/run_synthetic_control.py:170-230`,
  `data/processed/synthetic_control_summary.csv`
- **Defect:** Poorly-fitted placebos (e.g. Bering pre-RMSPE 2.17 vs Hormuz 0.26;
  8/22 placebos > 2× treated) inflate the apparent extremeness of Hormuz.
- **Fix:** Pre-specify and report a pre-RMSPE eligibility threshold; recompute the
  p-value across several defensible thresholds; plot treated vs placebo paths.
- **Remediation (2026-07-23):** The
  remediation-primary rule now retains placebo units whose pre-period RMSPE is
  no greater than 2x the treated unit's pre-period RMSPE. For tanker transits,
  the generated artifacts currently show 14/22 eligible placebos (8 excluded),
  treated post/pre RMSPE ratio 3.254, eligible-placebo p95 1.502, separation
  2.166x, and rank `p = 0.066667` at its `1/15` finite-sample floor. The new
  `synthetic_control_prefit_sensitivity.csv` reports 1.5x, 2x, 5x, 10x, and
  unscreened specifications; current rank values range from 0.043478 to
  0.083333, with unscreened `p = 0.043478`. Active reports now state the
  threshold, eligible/excluded counts, rank floor, and sensitivity range, while
  `run_synthetic_control_placebo_paths.png` plots the treated gap against the 14
  eligible placebo gap paths. Regression tests protect the screened primary
  claim and prevent the old unscreened `1/23` result from returning as the
  headline. Mher reran the synthetic-control pipeline, report generators, and
  14 focused tests on 2026-07-23. The pasted output confirms the 14/22
  eligibility split, screened `p = 0.066667` at floor `1/15`, the complete
  threshold-sensitivity grid, regenerated figures/reports, and 14 passing
  tests. (G1, G2, G3, G4)

### PRIORITY 3 — Reframe causal → descriptive (gated by GOV-01)

#### FRM-01 — Title / RQ still claim causal ton-mile identification
- **Severity:** CRITICAL · **Audits:** A1, A4 · **Status:** TODO
- **Where:** manuscript title/RQ; `docs/thesis_drafts/manuscript/chapters/09_limitations.tex:3-8`
- **Defect:** "Causal Identification of the Ton-Mile Multiplier Effect" vs the
  implemented "disruption-associated counterfactual shortfall." No freight outcome,
  no observed laden ton-miles, no ATT, no design excluding concurrent causes.
- **Fix:** Retitle to the descriptive object. Replace "identifies" with
  "estimates/reports." Remove causal ton-mile framing from title, RQ, abstract.

#### FRM-02 — "Ton-mile multiplier" is contradicted in aggregate
- **Severity:** CRITICAL · **Audits:** A4 · **Status:** TODO
- **Where:** `reports/mechanism_results_summary.md:41`,
  `docs/thesis_drafts/manuscript/chapters/06_results_mechanism.tex:104`
- **Defect:** Aggregate capacity-distance **falls 15.6%**, voyages −23.4%, vessel-days
  −17.2%. The +10.2% holds only among retained/resolved voyages, and 98% of that is
  route-share **composition**, not within-route elongation. No sailed tracks / laden
  states / cargo ton-miles exist.
- **Fix:** Delete the aggregate multiplier conclusion. State the defensible result:
  a **conditional sample-composition shift** among retained voyages. No aggregate
  ton-mile-multiplier claim anywhere.

#### FRM-03 — "Contraction plus substitution" outruns corridor evidence
- **Severity:** HIGH · **Audits:** A4 (+ ties to BUG-03) · **Status:** TODO
- **Where:** `docs/thesis_drafts/manuscript/chapters/06_results_mechanism.tex:133`;
  contract: `docs/CORRIDOR_TRANSMISSION_RESULTS.md:38`
- **Defect:** No lost Gulf shipment is traced to a replacement corridor; the corridor
  contract explicitly forbids reallocation/causal language; inference is p≤0.10-floored.
- **Fix:** Soften to "Gulf-linked activity contracted; portfolios/corridors changed
  in directions **compatible with** substitution." No routing/absorption claims.

#### FRM-04 — Independence of evidence layers overstated
- **Severity:** HIGH · **Audits:** A1, A4 · **Status:** TODO
- **Where:** `reports/transmission_chain_summary.md:10`,
  `reports/current_results_summary.md:79`,
  `reports/Hormuz_Thesis_Supervisor_Review.pptx` (slide 9)
- **Defect:** "Five independent layers" / "two structurally independent anchors" is
  false: the donut is the same fitted AR path (5 days dropped); spatial placebo and
  SCM share the donor pool + contamination screen; all sources share
  maritime-observation failure modes.
- **Fix:** Rephrase to "several partially dependent diagnostics agree directionally."
  Drop "independent corroboration" / "convergent falsification" rhetoric.

#### FRM-05 — Measurement described as physical; bound described as unconditional
- **Severity:** HIGH · **Audits:** A4, A5 · **Status:** TODO
- **Where:** `docs/thesis_drafts/manuscript/chapters/04_methods.tex:12`,
  `docs/AIS_DARK_VESSEL_BOUND.md:12,73`,
  `docs/thesis_drafts/manuscript/chapters/10_discussion_conclusion.tex:19`
- **Defect:** (a) "establishes an observable physical disruption" — it establishes a
  break in an AIS-derived, gap-filled series. (b) "92.8% is an upper bound" holds only
  under a one-sided-error assumption. (c) "86% dark rate … no source reports" is an
  unsupported negative (no dark-rate dataset).
- **Fix:** Say "AIS-observed throughput break." Relabel "conditional upper bound"
  and state the assumption. Remove the unsupported "no source reports" negative or
  cite one. (G1)

### PRIORITY 4 — Correctness bugs (re-run affected numbers after fixing)

#### BUG-01 — Network averages omit zero-origin months
- **Severity:** HIGH · **Audits:** A2 · **Status:** DONE
- **Where:** `src/lngfreight/network_rewiring.py:709,730,741,761`
- **Defect:** Origin rows exist only when a positive edge is observed; a one-month
  origin gets the same weight as a full-period one. Zero-filled recompute moved real
  numbers (China offset −0.174→−0.084; India turnover 0.472→0.556; EU27 offset
  missing→2.010) and can flip anomaly/resilience labels.
- **Fix:** Insert zero for months an origin disappears before averaging in
  `_portfolio_vector` / `_mean_edges_by_origin`. Re-run; check whether resilience
  categories change; update all downstream tables. Add regression test (TEST-01).
- **Remediation (2026-07-23):**
  `_portfolio_vector` and `_mean_edges_by_origin` now construct an observed
  period-by-origin matrix, fill an origin's absent months with zero, and only
  then average across months. A minimal two-month regression test verifies that
  an origin present in only one month receives the correct zero in the other
  month. The network graph, anomaly, typology, post-month sensitivity,
  threshold-sensitivity, and report artifacts were regenerated. Current
  results match the audit's independent recomputation: China non-Gulf offset
  `-0.084044`, India edge turnover `0.555286`, and EU27 non-Gulf offset
  `2.010427`. Headline resilience labels and all six anomaly flags are
  unchanged; Taiwan's leave-one-post-month label is now stable under every
  admissible deletion rather than changing when March is removed. Exact
  artifact assertions protect the three benchmark values. Mher reran all six
  affected network-analysis/report steps and 22 focused tests on 2026-07-23.
  The pasted output confirms the three benchmark values, unchanged headline
  typologies and anomaly flags, Taiwan deletion stability, and 22/22 passing
  tests. (G1, G2, G4)

#### BUG-02 — TSFM sensitivity compares different horizons
- **Severity:** HIGH · **Audits:** A2, A4 · **Status:** DONE
- **Where:** `data/processed/tsfm_counterfactual_summary.csv`,
  `scripts/make_results_summary.py:123,235`, `scripts/run_all.py:65`,
  `reports/current_results_summary.md:27`
- **Defect:** TSFM rows stop ~2026-06-01 (94 obs) vs primary 130 obs to 2026-07-07,
  and compare against a stale AR shortfall (5,121/206.9M), not the active 6,869/291M.
  `run_all.py` never regenerates TSFM. The "+2.4% / −5.2% vs AR" comparison is not
  interpretable.
- **Fix:** Regenerate TSFM at the matched 130-day horizon against the active AR
  baseline, **or** delete the comparison. Wire TSFM regeneration into `run_all.py`.
  Add a horizon/obs-count consistency check (TEST-02).
- **Remediation (2026-07-23):** The cached
  real Chronos-2 checkpoint was rerun offline against the active pinned panel
  through 2026-07-07. The new comparison uses identical TSFM/AR scored dates
  and observations: 130 transit days (`529` observed) and 118 valid capacity
  days (`27,499,733` observed). Chronos-2 now gives a transit shortfall of
  `6,614.888` versus AR-only `6,868.996` (`-3.699%`) and a capacity shortfall of
  `260.046M` versus AR-only `291.006M` (`-10.639%`). The real-model runner now
  refuses to write the comparison unless exact dates, observed values, summary
  endpoints, and counts all match. `run_all.py` invokes the admitted Chronos-2
  cross-check through `.venv-bench` in offline mode and fails loudly when the
  isolated environment/checkpoint is unavailable; the broader three-model
  admission benchmark remains isolated. Reports and current methodological
  notes were updated, the separate TSFM provenance manifest was refreshed, and
  regression tests protect both matched-horizon artifacts and report values.
  Mher reran the real cached Chronos-2 checkpoint offline, regenerated the
  report and TSFM provenance manifest, and ran 29 focused tests on 2026-07-23.
  The pasted output confirms the matched 130/118-day horizons, identical
  observed values, both match flags `True`, the revised `-3.699%`/`-10.639%`
  comparisons, clean environment/lock checks, and 29/29 passing tests.
  (G1, G2, G3, G4)

#### BUG-03 — Reallocation double-counts committed vessel capacity
- **Severity:** HIGH · **Audits:** A2 · **Status:** TODO
- **Where:** `src/lngfreight/reallocation.py:160,214`
- **Defect:** All observed post-period non-Gulf voyage capacity is offered as
  replacement supply without subtracting the destinations those voyages already
  served → artificial zero unmet demand.
- **Fix:** Net out committed capacity before offering it as replacement. Re-run;
  restate any feasibility/substitution numbers (feeds FRM-03).

### PRIORITY 5 — Reproducibility, provenance & data labels

#### REP-01 — "Frozen & reproducible" is currently false
- **Severity:** HIGH · **Audits:** A2, A5 · **Status:** TODO
- **Where:** `scripts/run_all.py:18`, `scripts/freeze_reproducibility.py:154,293`,
  `src/lngfreight/tsfm.py:430`, `docs/CURRENT_PLAN.md:20`,
  `docs/thesis_drafts/manuscript/chapters/03_data.tex:133`
- **Defect:** Fresh `--check` fails (unmanifested Natural Earth vessel file); `--verify`
  fails (3 figures + `config_sha256` + `vessel_raw_sha256` drifted). Runner is now 46
  steps, not covered by any passing frozen run. TSFM excluded from core manifest yet
  consumed by the report; wall-clock `runtime_s` and no Torch seed prevent byte-identical
  reruns; TSFM host-bound to macOS/arm64 (4/6 TSFM hashes currently mismatch).
- **Fix:** Manifest the vessel Natural Earth file; set a Torch seed + deterministic
  algorithms; strip wall-clock `runtime_s` from hashed artifacts; decide TSFM manifest
  policy (include it, since the report consumes it); regenerate all 46 steps; update
  manifests deliberately; **retain the full run transcript** in the repo. Until then,
  soften "frozen/reproducible" prose to "reproducible as of <dated historical run>."

#### PROV-01 — provenance.jsonl logs normalized frames, not originals; incomplete
- **Severity:** MEDIUM · **Audits:** A2, A3 · **Status:** TODO
- **Where:** `src/lngfreight/provenance.py:1`, `data/raw/provenance.jsonl`
- **Defect:** Logs `df.to_csv()` not original payloads; only ~29/156 raw files logged;
  4 records fail their own hash (path reuse/overwrite, not fabrication); ledger names
  (`kr_lng_imports_by_origin`) don't match registry variables (`korea_lng_import_total`);
  "logged immutably" is overstated.
- **Fix:** Log original payloads; backfill missing originals; reconcile ledger↔variable
  names; correct the "immutable" wording to what is true (fixity via SHA-256 manifest).

#### DATA-01 — Two conflicting PortWatch vintages; treatment date depends on which
- **Severity:** HIGH · **Audits:** A3, A5 (resolved in D-1) · **Status:** DONE
- **Where:** `data/raw/portwatch/hormuz_tanker_transits__chokepoint_strait_of_hormuz_n_tanker.csv`
  (53/44/7) vs `...__6631382171dc.csv` (35/35/10); `config/settings.yaml:112`;
  `docs/EVENT_CHRONOLOGY.md:20,24`
- **Defect:** The two snapshots disagree on Feb 27–Mar 1. Under 35/35/10, Feb 28 = Feb 27
  (no break until Mar 1), which undercuts the outcome-informed 2026-02-28 onset flagged
  by A1/A4.
- **Fix:** Confirm which vintage `registry.get_variable("hormuz_tanker_transits")`
  actually loads; pin exactly one with documented provenance; quarantine/remove the other.
  Then re-examine the treatment-date rationale under the confirmed vintage and justify
  the date from an **outcome-blind** external rule (disclose the outcome was inspected).
  Do not report a value not present in the pinned file. (G1)
- **Remediation (2026-07-23):** The registry returned 35/35/10/2/0 and a tidy
  SHA-256 of `6631382171dc...`; the provenance-ledger hash was unchanged by the
  check. `config/settings.yaml` now pins that exact derived file and checksum,
  and the frozen panel builder enforces the pin with a regression test. The
  earlier unsuffixed vintage is preserved for audit but excluded from active
  core/vessel scopes. `PORTWATCH_VINTAGE_REGISTER.md`, settings, chronology,
  data documentation, and manuscript now report the pinned values. The
  unchanged `2026-02-28` cutoff is justified by the external DoD kinetic onset,
  not the PortWatch outcome; prior outcome inspection is disclosed. Mher ran
  the three targeted regression tests and rebuilt the pinned frozen panel on
  2026-07-23; all three tests passed and the treatment-window sequence printed
  as 35/35/10/2/0. (G1, G3, G4)

#### DATA-02 — Mislabeled source flags & cross-document access drift
- **Severity:** MEDIUM · **Audits:** A3, A5 · **Status:** TODO
- **Where:** `config/sources.yaml:38,88,193`, `src/lngfreight/sources/__init__.py:27`,
  `docs/DATA_SOURCES.md:38`, `docs/DATA_SOURCE_DEEP_DIVE.md:218`
- **Defect:** `ttf_gas`/`jkm_lng` marked `proxy` but providers map to `None` (should be
  `unavailable`); Taiwan asserts OGL while the portal says "All Rights Reserved";
  `DATA_SOURCES.md` claims a free ICE/EEX subset that `sources.yaml` denies; Clarksons/
  Fearnleys access asserted as fact but are unproven hypotheses.
- **Fix:** Set TTF/JKM to `unavailable`; verify or downgrade the Taiwan license claim;
  reconcile the ICE/EEX statement to match `sources.yaml`; relabel Clarksons/Fearnleys
  access as acquisition hypotheses. Rename the mislabeled `ais_laden_tonmiles_usgc...csv`
  (it is byte-identical to the Panama capacity file).

#### DATA-03 — Disclose unverifiable manual captures
- **Severity:** MEDIUM · **Audits:** A3 · **Status:** TODO
- **Where:** `data/raw/importer_customs/originals/README.md:7` (Korea);
  Q-Flex roster; China GACC / India DGCI&S captures
- **Defect:** Korea ("the scrape IS the capture," no original), Q-Flex roster (manual,
  no source docs), China/India (no retained original HTML or ToS evidence; India uses a
  browser-impersonating UA) cannot be independently verified.
- **Fix:** For each, either re-capture with original-response preservation, or add an
  explicit line to a data-limitations section stating the original was not retained.
  Blast radius is the importer/vessel extensions, not the core throughput result.

#### PROV-02 — External-data routing bypasses registry (G5 violation)
- **Severity:** MEDIUM · **Audits:** A2 · **Status:** TODO
- **Where:** ~15 sites incl. `scripts/run_lng_index_analysis.py:24`,
  `src/lngfreight/spatial.py:37`, `src/lngfreight/terminal_matching.py:45`,
  `scripts/build_importer_outcomes.py:14`, `src/lngfreight/importer_outcomes.py:133`,
  `src/lngfreight/network_rewiring.py:359`, `src/lngfreight/feasibility.py:131`,
  `scripts/make_route_map.py:561` (full list in A2 finding 4)
- **Defect:** Analysis-consumed external data is loaded directly, bypassing the
  `registry.get_variable()` provenance contract.
- **Fix:** Route analysis-consumed sources through the registry (at minimum log the
  variable/query/source-status/checksum). Acquisition scripts that append provenance
  manually are lower priority than analysis-path bypasses.

### PRIORITY 6 — Stale artifacts, tests & minor code

#### STALE-01 — Supervisor deck is stale and overclaims
- **Severity:** HIGH (visibility) · **Audits:** A4 · **Status:** TODO
- **Where:** `reports/Hormuz_Thesis_Supervisor_Review.pptx` (slides 5,6,7,9)
- **Defect:** Shows 5,121/94-day headline (vs current 6,869/130-day), 36 placebos /
  ~9 windows / old SCM values, and "independent anchors" language.
- **Fix:** Regenerate with current numbers and reframed (descriptive, INF-01-corrected)
  language **before** any supervisor meeting. Highest external-visibility item.

#### STALE-02 — Stale numbers in docs
- **Severity:** MEDIUM · **Audits:** A4, A5 · **Status:** TODO
- **Where:** `docs/ADVANCED_ML_RECONSIDERATION.md:47` (BSTS 4,982 vs current 6,437.9),
  `docs/PENDING_ESTIMAND_REALIGNMENT_DRAFT.md:45` ("about nine" windows vs actual 7)
- **Fix:** Update to current artifact values or mark explicitly as historical.

#### TEST-01 — Highest-risk paths untested
- **Severity:** MEDIUM · **Audits:** A2 · **Status:** TODO
- **Where:** `tests/test_network_rewiring.py:140,174`, `tests/test_reproducibility.py:54`
- **Defect:** No test for an origin disappearing (BUG-01), for model-comparison rows
  sharing dates/obs-counts (BUG-02), or that the report imports TSFM artifacts excluded
  from the manifest; no clean-room manifest rebuild test.
- **Fix:** Add regression tests alongside BUG-01/BUG-02 fixes; add a report↔manifest
  consistency test; add a clean-room rebuild test.

#### CODE-01 — Fold indices unsafe on unsorted input (dormant)
- **Severity:** LOW · **Audits:** A2 · **Status:** TODO
- **Where:** `src/lngfreight/validation.py:121`, `src/lngfreight/inference.py:15`,
  `src/lngfreight/baselines.py:180`
- **Defect:** Positions computed against a sorted copy are applied via `.iloc` to the
  original frame; an unsorted panel would train/evaluate on wrong dates. Current panels
  are sorted, so dormant.
- **Fix:** Assert sortedness or return the sorted frame; add a shuffled-input test.

#### CODE-02 — Dropping missing rows compresses calendar time
- **Severity:** LOW · **Audits:** A2 · **Status:** TODO
- **Where:** `src/lngfreight/bsts.py:102`, `src/lngfreight/tsfm.py:127`
- **Defect:** Silently dropping missing rows makes a multi-day gap look like one state
  transition; lag/seasonal meanings drift from calendar time.
- **Fix:** Reindex to a complete calendar and handle gaps explicitly, or document the
  assumption and assert gap sizes are bounded.

---

## SECTION F — SUGGESTED EXECUTION ORDER

1. **GOV-01, GOV-02** — settle scope/approval (blocks everything downstream).
2. **INT-01, INT-02, INT-03** — remove false/unverified specifics (integrity).
3. **INF-01** — fix the interval/p-value in code **and** all prose.
4. **FRM-01…FRM-05** — reframe causal→descriptive (after GOV-01).
5. **BUG-01, BUG-02, BUG-03** — fix, then re-run affected numbers.
6. **REP-01, PROV-01, DATA-01…DATA-03, PROV-02, INF-02, INF-03** — repro & provenance.
7. **STALE-01, STALE-02, TEST-01, CODE-01, CODE-02** — artifacts, tests, cleanup.

After any code change, the verification command is typically:

```bash
python -m pytest -q
```

and, once REP-01 is addressed, a full frozen run + verify (transcript retained).
Remember G4: no item is `DONE` until Mher pastes back real output.
