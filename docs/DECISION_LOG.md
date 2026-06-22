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
- **Rationale:** 0 of the required 10 importers clear the admission rule (official
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
