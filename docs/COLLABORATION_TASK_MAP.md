# Thesis collaboration task map — SINGLE SOURCE OF TRUTH

**Owner of this file:** Mher Avetisyan (researcher).
**Last rewritten:** 2026-06-22. **Baseline facts last updated:** 2026-07-18.
**Authority:** This document is the **single source of truth** for the thesis
work plan. If any other doc, chat message, or task tracker disagrees with this
file, this file wins until it is edited. The in-app task tracker mirrors only the
"This week" queue (§7) and is not authoritative.

**Integrity rules for this file (non-negotiable):**
- No fabricated facts, numbers, dates, citations, or task states. Every baseline
  metric carries the date it was last verified.
- "Done" means a generating command ran and output was checked — never inferred.
- Unverified inputs are tagged **[VERIFY]** and may not enter the thesis as fact.
- Plan reflects the **Option D** thesis (below). Superseded scopes are retired,
  not silently overwritten — see the change log (§9).

---

## 1. Thesis definition (current scope)

**Title (working):** "Captivity and Substitution in a Maritime Energy Shock:
Importer Vulnerability to the 2026 Strait of Hormuz Disruption."

**Research question:** How did the 2026 Strait of Hormuz disruption propagate
through global energy-import systems, and which importer-level **exposure** and
**adaptive-capacity** factors explain heterogeneous vulnerability?

**Estimand (frozen target):** panel interaction difference-in-differences
`Y_it = α_i + δ_t + β(Post_t×Exposure_i) + γ(Post_t×Flexibility_i) + X_it'θ + ε_it`.
Identifies the **differential** post-shock response by pre-shock captivity; the
common world shock is absorbed by `δ_t`. **Not** an ATT on world energy supply.

**Causal stance:** design-based + structure-learning. Ambitious question,
disciplined claim. Prediction is never identification.

**Primary outcome:** Y1 = Gulf-sourced import share/volume. Secondary: Y2 total
volume, Y3 substitution intensity, Y4 composite vulnerability index.

**Authoritative design doc:** `docs/CAPTIVITY_EVENT_STUDY_DESIGN.md` (estimand,
identification, variable spec, estimator hierarchy, falsification cascade).
**Gap:** `docs/GAP_VALIDATION.md`. **Citations:** `references/literature_seed.bib`
(26 entries, all verified — `docs/CITATION_INTEGRITY_AUDIT.md`).

---

## 2. Current baseline (verified facts, dated)

- Branch/worktree: `main` at commit `0c3f665`, with 2026-07-18 consistency edits
  currently uncommitted in the working tree.
- Test suite: **262 passed, re-verified 2026-07-18** (`.venv`, Python 3.14.4,
  full `pytest -q`, 16.09s; 262 collected = 262 passed, 0 failed).
- Reproducibility manifest: **REP-01 was human-verified at 123 artifacts**, and
  **PROV-01 was subsequently human-verified at 125 artifacts / 49 stages /
  285 tests**. DATA-02 was then human-verified at 49 stages / 125 artifacts /
  287 tests and removes
  one mislabeled duplicate from active inputs (8 core, 145 vessel, 1 interim),
  while preserving its historical provenance. The DATA-03 candidate has
  290 tests and the same input/artifact scopes and was human-verified on
  2026-07-27. The PROV-02 candidate has 293 tests, 43/43 mapped free registry
  entries, and unchanged input/artifact scopes; Mher verified it with a clean
  49-stage run on 2026-07-27.
  P1 also fixed the discovered provenance-window mutation: raw payloads with
  different content now receive immutable content-addressed paths, and frozen
  panel loading requires an exact query-window match plus SHA-256 verification.
- Foundation assets that Option D reuses (the AR/PortWatch pipeline is now the
  anchor, not the thesis): Hormuz AR shortfall; GFW importer exposure
  (`importer_exposure_summary.csv`); Gulf departures −93% cross-validation; donor-
  contamination screen; TSFM benchmarks (Chronos-2/TimesFM-2.5/Moirai installed).
- Bloomberg/Spark access: still pending; Option D is designed to NOT depend on it.

**Principal risk:** not model construction. It is (a) supervisor scope sign-off on
the new differential estimand, and (b) resolving the `[VERIFY]` Flexibility inputs
before the design freezes. Both gate the modelling layers.

---

## 3. Ownership model

| Role | Owns |
|---|---|
| **Researcher (Mher)** | Scope decisions; all supervisor communication; institutional/admin; final scholarly judgment; `[VERIFY]` data-source decisions; running code and pasting real output; sign-off on every freeze. |
| **Codex** | Implementation, data wiring through `registry.get_variable()`, tests, deterministic pipeline, structured drafting, consistency audits. |
| **Claude** | Methodology/design, literature & citation integrity, variable specification, gap/RQ/hypothesis drafting, robustness design, review of Codex output. |

Tasks list a **Lead**; either AI can execute coding tasks and they may be
reassigned. No AI output is "verified" until Mher runs it.

---

## 4. Layered workstreams

Layers run roughly top-to-bottom but several proceed in parallel (§7 sequences the
week). Each task: **ID · descriptive task · Lead · Depends on · Definition of done
(DoD)**.

### Layer G — Governance, scope & administration

- **G1 · Supervisor scope memo & sign-off.** Lead: Mher (Claude drafts). Depends:
  design doc. Produce a one-page memo for Prof. Li stating: the pivot from the
  freight ATT to the captivity **differential** estimand; the RQ; the primary
  outcome; the explicit non-ATT limitation; and a recommended default. DoD:
  written decision from Prof. Li recorded in the decision log.
- **G2 · Rewrite proposal title/RQ/gap to Option D.** Lead: Claude (Mher approves).
  Depends: G1 direction. Replace the three-stream/triad freight-mediation gap prose
  with the captivity differential gap (`GAP_VALIDATION.md §4`). DoD: proposal text
  internally consistent with this file; no residual ton-mile/mediation framing.
- **G3 · Decision log.** Lead: Mher. Ongoing. Each scope/method change records
  date, decision-maker, rationale, affected files. DoD: log current as of last
  change.
- **G4 · Backward milestone plan from real deadline.** Lead: Joint. Depends: Mher
  supplies the submission deadline. Build a dated backward plan with review
  buffers, supervisor-response time, formatting, submission. DoD: dated plan with
  explicit slack.
- **G5 · Confirm formal submission requirements.** Lead: Mher. Authoritative TUM
  checklist: template, word/page limits, declaration, data/code appendix, upload
  process. DoD: checklist captured in repo.

### Layer L — Literature & citation integrity

- **L1 · Institutional database search.** Lead: Mher (runs Scopus/WoS) +
  Claude (screens). Depends: TUM login. Run the planned Boolean queries; export
  RIS/BibTeX; dedupe; screen; backward/forward citation chase. DoD:
  `LITERATURE_SEARCH_LOG.md` records found/dedup/screened/excluded/retained counts
  and a frozen final search date.
- **L2 · Resolve full-text △ flags.** Lead: Claude. Depends: PDF access. Confirm
  the audit-flagged specifics: Nguyen taxonomy categories; Polemis weekly-data +
  ARFIMA + abnormal-returns method; Wan "spatial vs ship-type" heterogeneity;
  artifact/openness claims (Zenodo, replication packages). DoD: each △ in
  `LITERATURE_MATRIX.md` resolved to ✓ with a page reference, or the claim softened.
- **L3 · Captivity/energy-security literature deepening.** Lead: Claude. Add and
  verify sources specific to importer vulnerability, regas/storage buffers, supplier
  diversity, and energy-security indices that the Flexibility construct leans on.
  DoD: new verified entries in the bib; matrix rows added.
- **L4 · Keep bib clean & in-sync.** Lead: Codex. Every in-text key resolves; every
  bib entry is cited; one citation style. DoD: cite-key/bib reconciliation passes
  (the `grep` check used 2026-06-22 returns no orphans).

### Layer D — Design freeze & pre-registration

- **D1 · Freeze unit set & panel frequency.** Lead: Joint. Depends: V1 coverage
  probe. Lock the importer panel and monthly/other frequency. DoD: frozen list in
  the design doc §6.1 with a coverage justification.
- **D2 · Freeze Exposure_i & Flexibility_i.** Lead: Claude + Mher. Depends: L3, V2,
  V3, and resolution of `[VERIFY]` inputs. Lock components, pre-shock window,
  weights, normalization. DoD: design doc §6.4–6.5 marked FROZEN with a dated note.
- **D3 · Freeze outcomes & controls.** Lead: Joint. Lock Y1 primary; Y2–Y4
  secondary; `X_it`; the `δ_t` absorption logic. DoD: §6.3 & §6.6 FROZEN.
- **D4 · Freeze falsification cascade & inference.** Lead: Claude. Lock §10 tests
  and §9 inference (wild cluster bootstrap; multiple-outcome handling). DoD: §9–10
  FROZEN; pre-registration checklist (§12) all-checked.
- **D5 · Pre-registration freeze record.** Lead: Mher. Depends: D1–D4 + G1. Commit
  a timestamped frozen spec BEFORE any estimator runs. DoD: tagged commit; no
  modelling code merged before this tag.

### Layer V — Variable construction / data layer (NO modelling)

- **V1 · By-source coverage probe & panel assembly.** Lead: Codex. Depends: D-layer
  not required to start the probe. Confirm 2026 monthly by-source coverage per
  importer (Comtrade 271111; Eurostat `nrg_ti_gasm`; PPAC; MOF/e-Stat); identify
  gaps; design the GFW terminal-arrival reconstruction to fill them. DoD: a panel
  coverage report (units × months × source-availability) frozen with provenance.
- **V2 · Outcome module (build ALL four).** Lead: Codex. Depends: V1. Construct Y1
  Gulf-source share/volume (primary) and Y2 total, Y3 substitution intensity, Y4
  composite index — through `registry.get_variable()`; declare series in
  `config/sources.yaml`. DoD: four reproducible outcome series with provenance
  logged; primary defined by the estimand, not by inspecting results.
- **V3 · Exposure_i construction.** Lead: Codex. Pre-shock Gulf-source share +
  reuse `importer_exposure_summary.csv` GFW index; standardized composite. DoD:
  predetermined Exposure_i per unit with convergent-validity check (official share
  vs GFW index) and provenance.
- **V4 · Flexibility_i construction + [VERIFY] resolution.** Lead: Mher (sourcing
  decisions) + Codex (wiring). Resolve regas slack, storage, supplier-diversity HHI,
  contract flexibility, pipeline alternative, alt-supplier distance. DoD: every
  component sourced from a confirmed primary source (no [VERIFY] left); standardized
  composite with component-sensitivity documented.
- **V5 · Controls X_it.** Lead: Codex. Region/bloc, degree-days, IP proxy, season,
  common price control. DoD: control matrix assembled with provenance.
- **V6 · Frozen analysis dataset + manifest.** Lead: Codex. Depends: V2–V5 + D5.
  Assemble the panel; hash-freeze it. DoD: analysis dataset with a manifest hash
  added to the reproducibility manifest.

### Layer E — Estimation & ML (only after D5 freeze)

- **E1 · Headline 2WFE interaction estimator.** Lead: Codex. Depends: V6, D5. Fit
  the §2 specification with importer & period FE. DoD: β, γ with wild cluster
  bootstrap inference; event-study lead/lag coefficients produced.
- **E2 · DML robustness arm.** Lead: Codex. Cross-fitted double ML with ML nuisance
  for `X_it`, recovering the low-dimensional interaction parameter. DoD: DML
  estimate reported as robustness with explicit small-N power caveat.
- **E3 · Causal-forest / GRF variable importance.** Lead: Codex. Rank which
  captivity components drive heterogeneity. DoD: variable-importance output framed
  as ranking, not CATE proof.
- **E4 · Estimation leakage & information-set audit.** Lead: Claude. Confirm
  Exposure/Flexibility are strictly pre-shock; no post-treatment leakage; chrono
  discipline holds. DoD: written audit matching code to the design doc.

### Layer M — Mechanism & spillover (Chapter B)

- **M1 · Spillover/propagation diagnostics.** Lead: Codex. Depends: V6. Test whether
  alternative chokepoints/routes/vessel classes show abnormal post-shock activity
  (reuse donor-contamination screen + PortWatch/GFW). DoD: propagation map with
  pre/post abnormality measures.
- **M2 · Interference bound for the headline.** Lead: Claude. Use M1 to bound the
  cross-importer SUTVA contamination of the main estimate. DoD: documented bound;
  if small → headline clean; if large → bias range reported.
- **M3 · (Optional) exploratory structure learning.** Lead: Codex. PCMCI/Granger as
  explicitly exploratory, assumptions stated. DoD: clearly labelled exploratory
  figure; not used for confirmatory claims.

### Layer C — Counterfactual validation (Chapter C)

- **C1 · TSFM vs AR counterfactual benchmark.** Lead: Codex. Depends: foundation
  assets. Evaluate Chronos-2/TimesFM-2.5/Moirai vs AR for the no-disruption
  benchmark with rolling-origin discipline. DoD: benchmark table; agreement/
  disagreement with AR documented.
- **C2 · Conformal interval calibration.** Lead: Codex. Apply distribution-free
  (EnbPI-style) intervals to the shortfall/benchmark. DoD: calibrated intervals;
  coverage diagnostics. **Framing:** validation of the counterfactual, never a
  causal claim.

### Layer R — Robustness & falsification (executes the §10 cascade)

- **R1 · Pre-trend / event-study leads.** Lead: Codex. DoD: flat leads or documented
  violation.
- **R2 · Placebo-exposure (permutation).** Lead: Codex. DoD: permuted Exposure_i ⇒
  null gradient distribution.
- **R3 · Placebo-timing.** Lead: Codex. False cutoff before 2026-02-28 ⇒ null. DoD:
  reported.
- **R4 · Leave-one-importer-out.** Lead: Codex. DoD: no single unit drives β.
- **R5 · Outcome-composition (H3).** Lead: Codex. Source-mix shift vs defended
  totals. DoD: reported.
- **R6 · Sensitivity to Flexibility weights.** Lead: Codex. DoD: component-weight
  sensitivity band.

### Layer W — Writing (chapters; drafting can begin pre-results, results-led parts wait)

- **W1 · Chapter outline tied to RQ/evidence chain.** Lead: Joint. DoD: section-level
  outline mapping each claim to a method, artifact, limitation, citation.
- **W2 · Literature review chapter.** Lead: Claude drafts, Mher reviews. Depends: L1.
  DoD: verified-citation prose from `LITERATURE_REVIEW_FOUNDATION_DRAFT.md` + gap.
- **W3 · Data chapter.** Lead: Codex drafts. Source selection, access, coverage,
  provenance, transformations, bias (incl. AIS darkening caveat). DoD: matches V-layer.
- **W4 · Methods chapter.** Lead: Codex drafts, Claude reviews. Estimand, identification,
  the three threat-defenses, estimator hierarchy, inference. DoD: matches design doc.
- **W5 · Results chapter.** Lead: Joint. Depends: E/M/C/R. Claim-led, frozen tables/
  figures, no causal overstatement. DoD: every number traceable to an artifact.
- **W6 · Discussion & limitations.** Lead: Joint. Carry the §11 "cannot claim" list
  verbatim; alternative explanations; external validity. DoD: claims within design
  and data bounds.
- **W7 · Contribution & conclusion.** Lead: Mher, Claude edits. DoD: contribution
  proportional to the differential estimand; no "first study."

### Layer P — Reproducibility & integrity

- **P1 · Re-verify pipeline & manifest. [DONE 2026-06-22]** Lead: Codex. Re-run the suite and the
  deterministic pipeline; confirm test count and the 94-hash manifest (or document
  drift). DoD: dated re-verification replacing the 2026-06-21 baseline.
- **P2 · Claim-to-artifact ledger.** Lead: Joint. Every headline claim → file, field,
  script, interpretation, caveat. DoD: machine-readable ledger.
- **P3 · Figure/table provenance audit.** Lead: Codex. Each thesis candidate has a
  generating script, source artifact, caption boundary, stable filename. DoD: audit
  table.
- **P4 · Thesis export layer.** Lead: Codex. One command exports approved tables/
  figures without rerunning optional models. DoD: export runs clean.
- **P5 · Cross-document consistency audit (C7 of integrity).** Lead: Codex. Title,
  abstract, RQ, hypotheses, methods, tables, captions, conclusion use consistent
  terms/numbers and the Option D estimand. DoD: no contradictions found.
- **P6 · Reproducibility package.** Lead: Codex. README, env locks, provenance,
  manifest, run instructions, license, exclusions coherent. DoD: independent-env
  reproduction or documented deviations.

---

## 5. Dependency gates (hard)

1. **G1 (supervisor sign-off)** gates D5 freeze and all of Layer E/M/C/R from being
   the *final* thesis result (exploratory runs may precede, clearly labelled).
2. **D5 (pre-registration freeze)** gates Layer E — no estimator is fit for the
   confirmatory result before the spec is frozen.
3. **V4 ([VERIFY] resolution)** gates D2 (Flexibility freeze).
4. **L1 (institutional search)** gates calling the review "systematic" and gates W2
   final.

---

## 6. Definition of thesis-ready (Option D)

Scope is approved (G1); the spec was frozen before estimation (D5); Exposure and
Flexibility have no unresolved `[VERIFY]`; the headline differential is reported
with wild-cluster-bootstrap inference and survives the falsification cascade (R);
spillover bias is bounded (M2); every reported number is traceable (P2); chapters,
figures, captions, and abstract agree on the Option D estimand (P5); citations are
verified (L); and the TUM submission checklist is complete (G5).

---

## 7. This week's working queue (mirrors into the task tracker)

Dependency-aware order. Parallel tracks marked.

1. **G1** — supervisor scope memo (Claude drafts → Mher sends). *Unblocks the most.*
2. **G2** — rewrite proposal title/RQ/gap to Option D (Claude). Parallel with G1.
3. **L2** — resolve full-text △ flags (Claude), as PDF access allows. Parallel.
4. **V1** — by-source coverage probe & panel assembly (Codex). Parallel; no gate.
5. **V4 sourcing** — Mher decides Flexibility `[VERIFY]` sources; Claude specifies
   construction. Gates D2.
6. **P1 — DONE 2026-06-22** — suite + deterministic pipeline re-verified; dated
   baseline refreshed in §2.
7. **D1–D4 drafting** — begin freezing the spec sections as V1/V4 land (do not set
   D5 until G1 returns).

Everything in Layer E/M/C/R waits on **D5**. Writing W1–W2 may start now.

---

## 8. Collaboration rules

- The researcher owns scope, supervisor communication, institutional requirements,
  and final judgment.
- AIs inspect, implement, test, trace, draft, and audit; drafts stay drafts until
  Mher reviews.
- No model output is "verified" until its generating command has run and output is
  pasted back.
- A new analysis enters the thesis only after its estimand, data requirement,
  limitation, and role are explicit.
- Optional Bloomberg/Spark access continues in parallel and cannot silently
  redefine the critical path.
- Edits to this file are logged in §9.

---

## 9. Change log

- **2026-06-22** — Rewrote the map as the single source of truth for the **Option D**
  captivity/adaptive-capacity event study. Retired the freight-ATT / ton-mile /
  mediation framing and the throughput-shortfall-as-destination plan (now the
  foundation layer). Added layered workstreams G/L/D/V/E/M/C/R/W/P. Prior plan
  preserved in git history (commit `bfe15ba` and earlier).
- **2026-06-22** — Completed P1: fixed provenance snapshot immutability and exact-
  window frozen loading, added two regression tests, regenerated/refroze the
  pipeline, and verified 216 tests plus all 94 deterministic artifact hashes.
- Earlier history: see git log and `PROJECT_POSTMORTEM_2026-06-21.md`.
