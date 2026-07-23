# Decision log

**Owner:** Mher Avetisyan. **Purpose:** record every scope/method decision with
date, decision-maker, rationale, and affected files (task G3). "Pending" entries
are open gates awaiting an external decision and may not be treated as settled.

Each entry: **date · decision · decision-maker · rationale · affected files · status**.

---

## 2026-06-22 · Scope pivot to Option D (captivity differential event study)

- **Decision-maker:** Mher (researcher).
- **Decision:** Retire the freight-rate ATT / ton-mile / mediation framing; adopt
  the importer-level panel interaction difference-in-differences as the target
  design (differential vulnerability by pre-shock exposure and adaptive capacity).
- **Rationale:** Proprietary freight data (Bloomberg/Spark) remain unavailable;
  the public-data pipeline supports a differential, non-ATT claim that is the
  strongest the data honestly allow.
- **Affected files:** `docs/COLLABORATION_TASK_MAP.md` (§9 change log),
  `docs/CAPTIVITY_EVENT_STUDY_DESIGN.md`, `docs/GAP_VALIDATION.md`.
- **Status:** Recorded internally. **Not yet supervisor-approved** — see the G1
  entry below, which gates D5 and all of Layer E/M/C/R as the *final* thesis result.

## 2026-06-22 · P1 reproducibility re-verification committed

- **Decision-maker:** Mher (researcher), implementation by AI.
- **Decision:** Accept the provenance-immutability and frozen-panel-loading fix;
  refreeze the manifest at 94 artifact hashes.
- **Rationale:** Closes a discovered provenance-window mutation; 216 tests pass and
  `run_all.py` completes all 36 steps with all 94 hashes matching.
- **Affected files:** `src/lngfreight/provenance.py`, `src/lngfreight/panel.py`,
  `scripts/freeze_reproducibility.py`, the two regression tests, regenerated
  artifacts, `README.md`. Commit `0c1bad1`.
- **Status:** Done.

## 2026-06-22 · V1 coverage probe → NO_GO for the confirmatory importer panel

- **Decision-maker:** Determined by the coverage audit; recorded by Mher.
- **Decision:** Do not freeze or estimate the Option D confirmatory panel on
  currently frozen public data. Pursue V-layer sourcing first.
- **Rationale:** 0 of the required 15 importers clear the admission rule (official
  monthly total + official by-source series + ≥12 contiguous pre-months + ≥3 post
  months). EU27/Japan fail on post-months (data-lag), India is total-only,
  KR/CN/TW/PK/Bangladesh have no frozen official source.
- **Affected files:** `docs/IMPORTER_SOURCE_COVERAGE_REPORT.md`,
  `data/processed/importer_source_coverage.csv`,
  `data/processed/importer_source_coverage_summary.json`. Commit `519e96f`.
- **Status:** Done (finding stands); feeds the G1 memo §5 and gates D1.

---

## PENDING · G1 — Supervisor scope sign-off (Prof. Li)

- **Decision-maker:** Prof. Li (awaited).
- **Memo:** `docs/SUPERVISOR_SCOPE_MEMO_OPTION_D.md` (revised 2026-06-22 to disclose
  the V1 coverage gap; requests approval of the *direction* contingent on closing
  coverage, plus a view on GFW reconstruction and a fallback if coverage cannot
  close).
- **Requested:** approve the scope pivot, the differential non-ATT estimand, the
  primary outcome, a fallback design, and the GFW-reconstruction question.
- **Status:** **PENDING — memo not yet sent / no decision recorded.** This gate
  blocks D5 (pre-registration freeze) and the final-result status of Layers
  E/M/C/R. Record Prof. Li's written decision here when it arrives, then check the
  `[ ] Confirm scope with Prof. Li` box in `CAPTIVITY_EVENT_STUDY_DESIGN.md`.

---

## 2026-07-17 · No-third-layer integration plan accepted

- **Decision-maker:** Mher (researcher), accepting the implementation
  recommendation.
- **Decision:** Do not build a third empirical layer before thesis integration.
  Preserve the completed PortWatch and open-data LNG mechanism results, add only
  pre-declared Layer-2 sensitivity checks, upgrade the generated reports, and
  draft thesis-integration text from existing artifacts.
- **Rationale:** The current evidence is strongest as a measurement and mechanism
  chain. Additional GEM capacity, Baltic freight, or persistence/recovery work
  would not strengthen identification before the thesis analysis freeze unless
  each clears a strict admission gate. The next highest-value work is therefore
  integrate, sensitivity-check, and write while keeping Spark as a dormant
  optional secondary-outcome path.
- **Candidate-extension kill criteria:**
  - **GEM:** workbook before analysis freeze + nameplate mapped to >=90% of
    observed non-Gulf supply + headroom grid, never nameplate-as-available.
  - **Baltic:** >=52 pre / >=12 post weeks of one consistently-defined series,
    <=10% missing, reproducible extraction, no subjective text coding.
  - **Persistence:** 6 complete post months for >=4 quantity-basis importers —
    currently **NO_GO**.
- **Accepted work plan:**
  - **Phase 1:** add Layer-2 sensitivity code for leave-one-post-month typology
    stability and pre-declared typology-threshold grids.
  - **Phase 2:** upgrade generated reporting once Phase-1 artifacts exist,
    including quantity-basis table separation, sensitivity reporting, balanced
    Layer-1 inference table, and anomaly-language cleanup.
  - **Phase 3:** draft manuscript-integration markdown only after checking for an
    existing manuscript directory, with artifact-path citations for every
    empirical number.
- **Affected files:** `docs/DECISION_LOG.md`, `docs/CURRENT_PLAN.md`; future
  Phase-1 through Phase-3 changes to be recorded when implemented.
- **Status:** Done for implementation planning. This entry does not record
  Prof. Li's formal proposal/RQ/estimand approval; the G1 gate above remains
  separate until written supervisor approval is logged.

---

## 2026-07-23 · Advisor acceptance, empirical sufficiency, and writing format

- **Decision-maker:** Zhenyu Wang (written email response; primary PDF export and
  checksum archived in `docs/approvals/`).
- **Accepted:** The revised title, research question, estimand, and cautious
  claim strength are acceptable. The completed empirical scope is sufficient
  for a Bachelor's thesis.
- **Scope consequence:** Continue the accepted no-third-layer integration plan:
  preserve the PortWatch counterfactual and open-data LNG mechanism evidence,
  complete only pre-declared corrections/sensitivity checks, and prioritize
  manuscript writing, citations, and presentation. Additional work may be
  reported selectively or placed in supplementary material; it is not a new
  empirical requirement.
- **Data consequence:** The thesis has reproducible public data for its two main
  empirical parts: tanker-throughput counterfactual measurement and the
  scope-limited LNG physical/network mechanism. No free, consistently defined
  LNG freight-rate series with adequate coverage has been established. The
  monetary freight-rate layer therefore remains a proprietary-access-dependent
  optional extension, not a blocker.
- **Writing/format decision:** Use the supplied LaTeX template. Do not select or
  defend APA 6, APA 7, or IEEE as a separate thesis requirement, and do not spend
  current effort on formatting adaptations. Draft content so it can be moved
  into a revised template later if necessary.
- **Length guidance:** Introduction plus related work should be no more than 30%
  of the main text. Total main-text length and whether bibliography/appendices
  are excluded remain unresolved because Prof. Li had not replied on that point.
- **Reporting:** Organize material progress and encountered issues into concise
  reports for Zhenyu.
- **Governance status:** This is written advisor-side acceptance. Because the
  response was authored by Zhenyu and expressly distinguished an unanswered
  Prof. Li question, it is not recorded as direct Prof. Li ratification. The
  formal proposal remains unchanged pending resolution of that distinction.
- **Affected files:** `AGENTS.md`, `README.md`, `docs/DECISION_LOG.md`,
  `docs/ESTIMAND_PROPOSAL_RECONCILIATION.md`,
  `docs/PENDING_ESTIMAND_REALIGNMENT_DRAFT.md`, `docs/CURRENT_PLAN.md`, and the
  manuscript planning notes.
- **Status:** Advisor decision recorded; content-first writing authorized;
  direct Prof. Li ratification remains unrecorded.
