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

## 2026-08-08 · Provenance-limited Bloomberg transcription branch authorized

- **Decision-maker:** Mher (researcher); implementation by AI (Codex).
- **Decision:** After the strict Phase 0 admission audit returned NO_GO
  (0 admitted / 5 blocked: transcriptions rather than original exports; missing
  Bloomberg identifiers, extraction receipts, methodology, definition history,
  and rights), implement the five user-supplied workbooks (three weekly
  Fearnleys LNG assessments, daily TTF, daily VLSFO) as a dormant
  `provenance_limited_secondary` branch instead of activating them: provider
  `bloomberg_transcription`, `status: restricted` in `config/sources.yaml`,
  opt-in only via `ENABLE_BLOOMBERG_LAYER=1` + `BLOOMBERG_EXPORT_DIR`.
- **Rationale:** The files are the complete evidence currently available and
  supply the thesis's missing monetary freight-market layer; limited-use
  processing preserves that evidence while the NO_GO gate, the locked PortWatch
  primary, the 2026-02-28 cutoff, and the free-data default remain unchanged.
  Permitted claim: disruption-associated counterfactual deviation in assessed
  rates. Prohibited: ATT, causal freight effect, identified mediation.
- **Affected files:** `config/bloomberg_exports.yaml`, `config/sources.yaml`,
  `config/settings.yaml`, `src/lngfreight/bloomberg_admission.py`,
  `src/lngfreight/bloomberg_market.py`, `src/lngfreight/freight_counterfactual.py`,
  `src/lngfreight/freight_integration.py`,
  `src/lngfreight/sources/bloomberg_transcription.py`, seven
  `scripts/*bloomberg*` commands, generated `data/processed/*` artifacts,
  `docs/BLOOMBERG_MARKET_LAYER_IMPLEMENTATION_PLAN.md`, `docs/INFERENCE_NOTES.md`,
  `docs/DATA_SOURCES.md`.
- **Status:** Recorded retroactively on 2026-08-09 (the implementation predated
  this entry). Branch remains dormant pending original exports and rights
  confirmation per `docs/BLOOMBERG_EXTRACTION_CHECKLIST.md`.

## 2026-08-09 · Bloomberg raw-bearing artifacts quarantined from version control

- **Decision-maker:** Mher (researcher); implementation by AI (Claude).
- **Decision:** Gitignore the derived artifacts that embed verbatim licensed
  assessment histories (`data/processed/lng_freight_weekly_panel.csv`,
  `data/processed/lng_freight_descriptive_weekly.csv`,
  `data/processed/freight_market_context.csv`, plus `.work/` inspection
  screenshots) and add `tests/test_bloomberg_quarantine.py` as a regression
  guard. Version control retains aggregates, QA tables, manifests, and
  post-period derived artifacts only. Corrected the contradictory closing
  paragraph of the implementation plan ("no proprietary values enter
  modelling"), which misdescribed the limited-use branch.
- **Rationale:** All `rights` fields in `config/bloomberg_exports.yaml` are
  null/unverified; committing the full assessment histories would risk exactly
  the redistribution the branch's own governance prohibits. The files remain
  locally pinned by `scripts/freeze_bloomberg_layer.py`.
- **Affected files:** `.gitignore`, `tests/test_bloomberg_quarantine.py`,
  `docs/BLOOMBERG_MARKET_LAYER_IMPLEMENTATION_PLAN.md` (§8 correction, new §9),
  `docs/DECISION_LOG.md`.
- **Status:** Recorded; pending Mher's own verification run per guardrail G4.

## 2026-08-09 · Candidate review acted on (chronology, Damietta, literature, tickers)

- **Decision-maker:** Mher (researcher; blanket approval of the
  `DATA_REGISTRY_REVIEW_2026-08.md` recommendations); implementation by AI
  (Claude).
- **Decisions:**
  1. **Damietta 2026-07-29 classified as a distinct non-Hormuz confound**, not
     an extension of the Hormuz treatment, because attribution is unresolved
     (Egyptian Cabinet attributes the fire to a UAV; no claim of
     responsibility). Logged as a chronology context event and a dedicated
     SUTVA-audit section. **Reclassification reopens automatically if
     attribution to Iran is established** — that changes wording, not the
     estimator (the within-unit AR primary is unaffected either way).
  2. **Chronology extended through 2026-08-01** with verified April–July
     context events (ceasefire 04-07/08, MoU 06-17, attack resumption 07-07,
     escalation 07-19/20 flagged single-sourced, Iran–Oman proposals
     07-27/29, Damietta 07-29). No treatment candidate added; cutoff
     2026-02-28 unmoved.
  3. **WTO `wto_departure_validation.comparison_windows` stay at the v1
     matched windows** (conservative default), even though the live tracker
     now reaches August; any extension of the matched YoY design would be a
     separate documented decision.
  4. **IEA = citations only, no tracked source class.** EIA Today in Energy
     items likewise citations/corroboration only — no new registry variables
     (underlying freight rates are proprietary Argus; GIIGNL is annual).
  5. **Bloomberg identifiers filled** for the three Fearnleys series
     (`FLNGEASZ`/`FLNGWTSZ`/`FLNG1YTC` Index) on the strength of user-supplied
     Bloomberg Charts PDFs plus a six-anchor exact extreme-value/date match
     against the transcriptions (run 2026-08-09, all six MATCH; see
     `data/raw/bloomberg_transcription/originals/charts/README.md`). Rights
     remain unverified/null; series stay `restricted`; the FLNGWTSZ chart
     shows the 2025-01-31 zero in Bloomberg's own series, so the masked zeros
     are not transcription artifacts (mask unchanged).
  6. **v3 window extension approved in principle** (target `full_end` ≥
     2026-08-01 via the runbook rule max − 5 days). **Execution remains
     Mher's** (fresh PortWatch browser download, WTO re-fetch via
     `scripts/fetch_wto_hormuz_lng.py`, rebuild/refreeze per
     `WINDOW_EXTENSION_V2_RUNBOOK.md`); `study_window.full_end` is NOT
     changed until the new snapshot's max date is known.
- **Rationale:** documented in `DATA_REGISTRY_REVIEW_2026-08.md` (verification
  trail, source list, and flags; two items remain unverified and unlogged:
  the exact date of the first post-MoU strike, and a discrete late-July
  "Iran considering a new ship ban" story).
- **Affected files:** `docs/EVENT_CHRONOLOGY.md`,
  `docs/SUTVA_CONTAMINATION_AUDIT.md`, `config/settings.yaml` (comment block
  only), `docs/LITERATURE_MATRIX.md`, `references/literature_seed.bib`,
  `docs/LITERATURE_SEARCH_LOG.md`, `config/bloomberg_exports.yaml`,
  `config/sources.yaml` (comment only), `docs/DATA_SOURCES.md`,
  `data/raw/bloomberg_transcription/originals/charts/` (3 PDFs + README),
  `docs/WINDOW_EXTENSION_V2_RUNBOOK.md`, `docs/DATA_REGISTRY_REVIEW_2026-08.md`.
- **Status:** Done except v3 execution (open gate: Mher's terminal run) and
  the two unverified items above.

## 2026-08-09 · v3 execution: vintage kept pinned, extension delivered as sensitivity

- **Decision-maker:** Mher (researcher, both choices made explicitly);
  implementation by AI (Claude).
- **Context:** executing the approved v3 window extension surfaced two facts
  the runbook had not anticipated.
  1. **PortWatch max date is 2026-08-02**, so the v1/v2 rule
     (`full_end = max − 5`) yields 2026-07-28 — before the 2026-08-01 target
     and, decisively, **before the 2026-07-29 Damietta event** the extension
     existed to capture.
  2. A fresh capture revises **2,680/2,750 (97.45%) of all overlapping Hormuz
     days** and **1,514/1,519 (99.67%) of configured training days**. The
     2019–cutoff overlap mean is `54.10 → 44.98` (−16.9%), while the configured
     2022–cutoff training mean is `57.09 → 47.00` (−17.68%);
     `capacity_tanker` −15.0%), following PortWatch's July/August 2026
     AIS-spoofing revisions and its March 2026 Hormuz boundary refinement.
- **Decisions:**
  1. **The pinned vintage stays the reporting basis.** The 2026-08-09 capture
     is archived and registered as a sensitivity-only artifact
     (`portwatch_chokepoints_vintage_20260809_snapshot`), never promoted.
     `study_window.full_end` remains **2026-07-07**; no primary artifact was
     regenerated and no headline number changed.
  2. **The extension is delivered as a sensitivity layer** at
     `full_end = 2026-08-01` (1-day buffer, documented departure from the
     5-day rule, justified by a tail-completeness check) so that Damietta
     falls inside the analysed window.
  3. **The WTO core input was restored to its v2 bytes** after the refresh was
     found to revise one in-window day (2026-07-06: 0.0 → 29.21). The
     2026-08-09 normalized derivative is preserved for sensitivity reading, but
     the intermediate original source payload was not preserved; that gap is
     now recorded in `provenance_source_payload_exceptions.json` rather than
     reconstructed. `data/raw/SHA256SUMS` (core) is therefore
     **unchanged from git HEAD**, proving v2 primary inputs are intact;
     the later integration-hardening pass moved the PortWatch candidate into
     `SHA256SUMS.sensitivity` and retained the WTO derivative in the broad
     non-core scope.
- **Findings recorded:** `docs/PORTWATCH_VINTAGE_SENSITIVITY_RESULTS.md`.
  Vintage revision moves the primary daily shortfall 52.84 → 43.81 (−17.1%)
  at identical dates; extending to 2026-08-01 moves the cumulative average only
  43.81 → 44.08 (+0.6%). **Correction:** that aggregate average concealed a
  temporary partial post-MoU tanker-count rebound followed by relapse after
  renewed attacks. The defensible conclusion is no sustained recovery through
  August 1, not “no rebound” or “no reopening dynamic.” See
  `PORTWATCH_REBOUND_RELAPSE_PROFILE.md`.
- **Correction issued:** an earlier claim in this session that the WTO LNG
  index was "0.0 throughout" the post-cutoff period was **wrong** and has been
  corrected in `EVENT_CHRONOLOGY.md`, `config/settings.yaml`,
  `WINDOW_EXTENSION_V2_RUNBOOK.md`, and `DATA_REGISTRY_REVIEW_2026-08.md`.
  Actual: zero on 155 of 163 post-cutoff days with eight isolated
  partial-loading days (2026-03-01 68.3 … 07-06 29.2; 2025 base = 100). The
  defensible claim is **no sustained resumption**, not "no loadings".
- **Affected files:** `config/sources.yaml` (new sensitivity artifact entry),
  `config/settings.yaml` (comment correction),
  `scripts/run_portwatch_vintage_sensitivity.py` (new),
  `data/processed/portwatch_vintage_sensitivity.csv` (new),
  `docs/PORTWATCH_VINTAGE_REGISTER.md`,
  `docs/PORTWATCH_VINTAGE_SENSITIVITY_RESULTS.md` (new),
  `docs/WINDOW_EXTENSION_V2_RUNBOOK.md`, `docs/EVENT_CHRONOLOGY.md`,
  `docs/DATA_REGISTRY_REVIEW_2026-08.md`, `data/raw/SHA256SUMS.vessel`,
  `data/raw/provenance.jsonl`,
  `data/raw/portwatch/vintages/` (new archival vintage).
- **Status:** Done. 324 tests pass; all three input-hash scopes pass.
  **Open for Mher:** whether the thesis reports the vintage-sensitivity table
  in Limitations (recommended) or as a robustness appendix.

## 2026-08-09 · Integration-hardening order recorded

- **Decision-maker:** Mher (researcher), requesting an ordered program and
  task-by-task implementation; dependency audit and implementation by AI.
- **Decision:** Treat the new work as a dated refinement of the accepted
  no-third-layer integration plan. Freeze the model-admission rule before
  completing the August model matrix; then freeze the August vintage's
  sensitivity-only provenance scope before generating new results from it.
  Core inference hardening precedes LNG mechanism extensions. The formal
  proposal, locked cutoff, working estimand, and pinned primary vintage do not
  change.
- **Known-results disclosure:** July results for four unconditional models and
  the August AR result were already visible. The admission rule is therefore
  “frozen before completion of the August matrix,” not preregistered or ex ante.
- **Rationale:** This order removes the strongest defence vulnerability: an
  apparently convenient model set or silently promoted data vintage. It also
  preserves the dirty worktree and the G4 human-verification requirement.
- **Affected files:**
  `docs/INTEGRATION_HARDENING_EXECUTION_ORDER_2026-08-09.md`,
  `docs/CURRENT_PLAN.md`, `docs/DECISION_LOG.md`.
- **Status:** AI-recorded; **NEEDS-VERIFY** under G4 before being treated as
  completed governance work.

## 2026-08-09 · Model-admission rule frozen before August matrix completion

- **Decision-maker:** Methodological implementation by AI under Mher's ordered
  task request; human acceptance remains subject to G4 verification.
- **Decision:** The primary sensitivity range is a four-specification
  representative same-information comparison: seasonal naive, locked AR(1,7),
  preselected Chronos-2, and BSTS. Eligibility holds the outcome, actual-transit
  unit, 2022-01-01–2026-02-27 training support, 2026-02-28 cutoff, and common
  130-day scoring window fixed and prohibits observed post-cutoff covariates.
  The cross-model statistic is the mean daily point-or-marginal-median
  shortfall. BSTS's joint cumulative posterior median remains a secondary
  model-native statistic.
- **Visible exclusions:** TimesFM and Moirai remain information-eligible but are
  unselected additional members of the already represented foundation-model
  family. ARX rows are excluded from the same-information range because they
  use observed post-cutoff covariates; synthetic control is excluded because it
  uses post-period donors and mean-scaled transit-equivalent units. Every row
  remains published with a machine-readable reason.
- **Known-results disclosure:** July results and the August AR result were
  visible before this freeze. The rule is not described as preregistered or ex
  ante. The existing July native-summary range is 5.278 transits/day; the
  harmonized daily-point range is 5.175/day because the BSTS daily marginal
  median (49.625/day) differs slightly from its joint cumulative median
  (49.522/day).
- **Protocol identity:**
  `db83d857c910954a10e63ce02ad4204e2934ab8ec5e2ba53120740098689e891`.
- **Affected files:** `config/model_admission_protocol.yaml`,
  `scripts/build_model_admission_protocol.py`,
  `data/processed/model_admission_protocol.csv`,
  `data/processed/model_admission_known_results.csv`,
  `docs/MODEL_ADMISSION_PROTOCOL_2026-08-09.md`, focused tests, and this log.
- **Assistant verification:** protocol known values reconcile to their source
  artifacts; 10 focused tests pass; `git diff --check` passes.
- **Status:** AI implemented; **NEEDS-VERIFY** under G4. No new August seasonal,
  Chronos, or BSTS result was generated during this phase.

## 2026-08-09 · August PortWatch snapshot moved to an explicit sensitivity scope

- **Decision-maker:** Methodological implementation by AI under Mher's ordered
  task request; human acceptance remains subject to G4 verification.
- **Decision:** Freeze the 2026-08-09 PortWatch full-panel snapshot in the
  dedicated `SHA256SUMS.sensitivity` scope, label it `sensitivity_only` in the
  registry, and enforce a no-promotion guard. The pinned July source and
  `study_window.full_end: 2026-07-07` remain unchanged. Add a deterministic
  sensitivity-input manifest and run its gate near the start of `run_all.py`.
- **Reproducibility boundary:** The August bytes pass local hash verification
  but remain Git-ignored; a permitted replication-archive deposit is still
  required before claiming clone-level reproduction.
- **Separate provenance correction:** The full audit exposed that WTO ledger
  line 190 labels an overwritten intermediate raw payload “preserved.” The
  ledger was not rewritten and missing bytes were not invented. A
  machine-readable exception now labels the historical source payload
  unavailable, verifies the restored pinned source, and identifies the
  preserved normalized derivative.
- **Affected files:** `data/raw/SHA256SUMS.sensitivity`, registry and freeze
  code, `scripts/verify_sensitivity_inputs.py`,
  `data/processed/portwatch_sensitivity_input_manifest.json`,
  `config/provenance_source_payload_exceptions.json`, provenance audit code and
  outputs, `docs/PORTWATCH_SENSITIVITY_INPUT_GATE.md`, tests, and orchestration.
- **Assistant verification:** 8 core, 1 sensitivity, 146 vessel/open-data, and
  1 interim input hashes pass; 25 focused tests pass; full provenance audit
  passes with the disclosed historical WTO source gap; `git diff --check`
  passes.
- **Status:** AI implemented; **NEEDS-VERIFY** under G4 and replication archive
  deposit remains open.

## 2026-08-09 · “No rebound” claim corrected to rebound then relapse

- **Decision-maker:** Correction required by the frozen data; implementation by
  AI under Mher's ordered task request.
- **Decision:** Replace “no rebound,” “no recovery trend,” and “no post-MoU
  reopening dynamic” with the narrower observed-data conclusion: temporary
  partial PortWatch tanker-count rebound during the post-MoU interval, followed
  by relapse after renewed attacks; no sustained recovery through 2026-08-01.
  Keep the separate WTO statement as “no sustained LNG resumption.”
- **Verified profile:** In the August vintage, inclusive matched 20-day means
  rise 0.85 → 10.45 transits/day (12.57/day in the final seven days), then fall
  to 1.56/day over 07-08–08-01. The post-MoU mean is only 22.2% of the
  configured pre-treatment mean. The pinned vintage confirms the rebound
  (1.25 → 12.45/day) but is right-censored after 07-12, so its full relapse
  contrast is not estimated.
- **Claim boundary:** These are descriptive calendar partitions around context
  events, not causal estimates of the MoU or renewed attacks. PortWatch's
  `n_tanker` is all-tanker, not LNG-specific, and does not count unobserved
  AIS-dark vessels.
- **Affected files:** frozen windows in `config/settings.yaml`,
  `scripts/run_rebound_relapse_profile.py`, two processed CSVs,
  `docs/PORTWATCH_REBOUND_RELAPSE_PROFILE.md`, the vintage results note, data
  review, external-review prompt, this log, orchestration, and focused tests.
- **Assistant verification:** exact phase totals, denominators, censoring, and
  contrasts are locked by tests; 26 focused tests pass; all four input scopes
  pass; stale-claim search returns only explicit corrections; `git diff
  --check` passes.
- **Status:** AI implemented; **NEEDS-VERIFY** under G4.

## 2026-08-09 · Correction: admission protocol v2 supersedes the initial local lock

- **Why this correction is appended:** The preceding admission entry remains a
  historical record, but its timing disclosure, Chronos rationale, and hashes
  are superseded here rather than silently rewritten.
- **Decision:** Treat the rule as a **local ex-post governance lock before the
  remaining August cells**, not as preregistration, blinded selection, or an
  ex-ante model choice. The selected comparison is a four-specification
  representative range (seasonal naive, AR, Chronos, BSTS), not the range of
  all information-eligible models. TimesFM and Moirai remain visible as
  pre-period-admitted models without frozen 130-day matrix cells; ARX and
  synthetic-control rows remain visible but outside this same-information,
  same-unit range for their recorded reasons.
- **Known-information disclosure:** All pinned-vintage model results, the
  August outcome path, all six saved August AR vintage/window results, and the
  TSFM validation table were known. During independent hardening, unpersisted
  audit computations also exposed August seasonal-naive (43.700000/day) and
  BSTS (40.167457/day using summed daily marginal medians; 40.110773/day using
  the native joint statistic). These are disclosed known values, not frozen
  thesis artifacts. No August Chronos result has been run or saved.
- **Chronos rationale:** Chronos is retained as the historically implemented
  TSFM representative and calibration anchor, not the universal performance
  winner. TimesFM had lower transit MASE (0.781724 versus 0.800037); Chronos
  had the smallest absolute coverage error, native requested 95% intervals,
  and the already-integrated default robustness path.
- **Corrected identities:** protocol SHA-256
  `bb050aa041e8fc1c8391b908baeab529aaf2e9944d5f35b07af661349176adce`;
  matrix-design SHA-256
  `297908c214a0afab30a377854585cb1788922334c3bba976f8e2a1141c6ed73e`.
  Fourteen known-result rows are reconciled to hashed source artifacts with
  explicit date, unit, support, formula, and observed-vector checks.
- **Gate:** The matrix remains blocked until the corrected bytes are anchored
  and Mher completes the G4 verification. Never average the vintages.
- **Status:** AI implemented; **NEEDS-VERIFY** under G4.

## 2026-08-09 · Correction: August sensitivity is separate from the core pipeline

- **Why this correction is appended:** The preceding sensitivity entry says
  the August gate runs near the start of `run_all.py`. That integration was
  removed after a clean-clone audit showed it would make the core thesis rerun
  depend on Git-ignored optional bytes.
- **Decision:** Keep the pinned July pipeline and core reproducibility manifest
  independent of the August input. The August work now has a standalone
  `run_portwatch_sensitivity.py` runner, explicit registry opt-in and consumer
  allowlist, separate input and branch manifests, and a separate provenance
  projection. Optional reads of the pinned comparator are also labelled
  sensitivity-scope so they cannot change core provenance hashes.
- **Boundary:** The August raw bytes are locally hash-verified but still need a
  permitted replication-archive deposit before clone-level sensitivity
  reproduction can be claimed. The core runner does not promote or require
  them.
- **Status:** AI implemented; **NEEDS-VERIFY** under G4; archive deposit open.

## 2026-08-09 · Correction: pinned post-attack buffer is excluded, not analyzed

- **Why this correction is appended:** The preceding rebound entry describes
  the pinned vintage as right-censored after 07-12. Its raw source does extend
  through 07-12, but the locked trusted reporting endpoint is 07-07; those five
  later rows are a buffer and are excluded from analysis.
- **Decision:** Use the pinned vintage only to corroborate the matched rebound
  (1.25 → 12.45/day). Estimate the 07-08–08-01 relapse only in the August
  vintage, where all 25 trusted days are present (mean 1.56/day; 21/25 days are
  nonzero). Describe the calendar partitions as fixed after exploratory
  inspection and before artifact generation, never as preregistered or
  pre-frozen.
- **Claim boundary:** The result is a temporary partial observed-count rebound
  followed by relapse and no sustained recovery toward the configured
  pre-treatment level through 08-01. It is descriptive, not an event effect,
  and missing modeled/AIS support is never evidence that no vessel sailed.
- **Status:** AI implemented; **NEEDS-VERIFY** under G4.

## 2026-08-09 · Mher completed the phase 1–3 G4 verification

- **Decision-maker and evidence:** Mher ran the five requested command blocks
  locally and pasted the complete terminal transcript in Codex. Transcript
  SHA-256: `6b405f72db5315a6e7f9b5b044ed46e0091abdb89fe33964834f4d8665e0075c`.
- **Admission/rebound evidence:** The sensitivity gate reproduced the August
  source SHA `0bc806a4…bcb`; the pinned transit and capacity AR cells reproduced;
  admission protocol SHA `bb050aa…adce` reconciled 14 known-result rows; and
  the trusted-endpoint rebound/relapse tables regenerated with no pinned
  post-07-07 relapse estimate.
- **Test and fixity evidence:** 43/43 selected tests passed; 8 core, 146 vessel,
  and 1 interim input hashes matched; the provenance audit passed with the
  disclosed historical source gaps; and all 6 prepared sensitivity artifacts
  matched their separate manifest.
- **Decision:** Phases 1–3 satisfy G4 and the frozen matrix phase is unblocked.
  This does not waive the pending replication-archive deposit, promote the
  August vintage to primary, authorize vintage averaging, alter the formal
  proposal, or authorize optional third-layer extensions.
- **Status:** Phase 1–3 verification **DONE**; matrix phase authorized under its
  frozen design and sensitivity-only interpretation.

## 2026-08-09 · Frozen model–vintage matrix generated; post-run G4 pending

- **Trigger:** Mher's preceding transcript satisfied the phase 1–3 human gate,
  so the anchored matrix design was authorized to run without changing its
  roster, dates, units, information sets, revisions, or seeds.
- **Completed cells:** The matrix contains exactly 8 model–vintage cells and
  1,040 daily rows over 2026-02-28–07-07. Observed sums are 529 in the pinned
  vintage and 401 in the August vintage. All four pinned cells reconcile to
  their existing artifacts.
- **Common-statistic results (pinned → August, transits/day):** seasonal naive
  54.800 → 43.700; AR 52.838 → 43.814; Chronos 50.884 → 42.177; BSTS
  daily marginal median 49.625 → 40.167. The BSTS joint-native secondary
  values are 49.522 → 40.111 and do not enter the cross-model range.
- **Sensitivity-budget result:** The selected pinned four-specification range
  is 5.175/day; same-model vintage shifts span 8.707–11.100/day. The AR vintage
  shift is 9.025/day, 1.744 times the selected pinned model range. This is a
  case-local sensitivity comparison, not a variance decomposition, pooled
  estimate, ATT, all-admissible-model range, or general AIS claim.
- **Lifecycle correction:** The original complete-freeze path would have
  overwritten the prepared manifest hashed by the pre-run checkpoint. The
  prepared file was preserved unchanged. A separate post-run freezer now
  writes `portwatch_sensitivity_complete_manifest.json`, verifies the prepared
  hash, requires all seven matrix artifacts, and freezes 13 branch artifacts.
  No forecast code, frozen design, or result was changed by this correction.
- **Assistant verification:** 9/9 matrix-specific tests independently
  recompute summary totals from the 1,040 daily rows, validate support and
  metadata, exercise corruption failures, and reconcile both manifests. The
  combined selected suite passes 52/52, the full repository suite passes
  358/358, and the complete 13-artifact manifest matches live bytes. Core input
  hashes still pass and the provenance audit still passes with the disclosed
  historical source gaps.
- **Open boundaries:** August source-byte archive deposit remains pending; the
  historical WTO source gap remains disclosed; core runtime output records
  Python and implementation hashes but not separate NumPy/Pandas fields.
- **Status:** AI implemented; **NEEDS-VERIFY** under G4. Mher must rerun the
  three matrix phases and post-run checks before phase 4 is `DONE`.

## 2026-08-10 · Mher completed the matrix phase G4 verification

- **Decision-maker and evidence:** Mher reran the three isolated matrix phases,
  separate completion freeze, focused and full tests, core input check,
  provenance audit, and `git diff --check`, then pasted the complete terminal
  transcript in Codex. Transcript SHA-256:
  `f35137526a1e106d6adc5f6eff42a8f63d317ccce2665e7851fb5c703fedf40b`.
- **Result reproduction:** The transcript reproduces all eight frozen cells,
  including the previously unknown August Chronos result of 42.176725 lost
  transits/day. Both vintages retain 130 scored days and observed sums 529 and
  401. The interpretation guard printed during finalization.
- **Verification evidence:** Matrix tests pass 9/9; the complete repository
  suite passes 358/358; all 13 complete sensitivity artifacts match; 8 core,
  146 vessel, and 1 interim input hashes match; provenance passes with the
  disclosed historical source gaps; and `git diff --check` returns no output.
- **Decision:** Phase 4 satisfies G4 and is `DONE`. Task 5 may build reporting
  artifacts from the frozen matrix without changing its models, values,
  manifests, or interpretation. The August source-byte archive deposit remains
  a separate open reproducibility boundary.
- **Status:** Matrix phase **DONE**; sensitivity-budget reporting phase opened.

## 2026-08-10 · Separate sensitivity-budget reporting card implemented

- **Parent and lifecycle:** The card reads only the G4-verified model–vintage
  matrix and exact parent hashes. It has a new design, builder, freezer,
  five reporting outputs, and manifest. The phase-4 complete manifest remains
  unchanged at SHA-256
  `2d6daf153d4fe73224533cbd39c64631a1156c44f4907959283c2550ca651fa7`
  with 13 artifacts; the card is absent from `run_all.py`, `settings.yaml`, and
  the core reproducibility manifest.
- **Absolute result:** On the harmonized mean-daily common-point statistic,
  selected-model ranges are 5.174835/day (pinned) and 3.646049/day (August),
  while same-model vintage differences are 8.707032–11.100000/day. The locked
  AR difference is 9.024925/day, 1.744002 times the pinned selected-model
  range. BSTS uses daily marginal medians (49.625165 and 40.167457), not its
  joint-native cumulative medians.
- **Metric qualification:** Using each cell's own model counterfactual as the
  denominator, all eight shortfall shares cluster at 92.421498%–93.422731%.
  Within-vintage spreads are 0.666180 and 0.554448 percentage points, and
  same-model vintage changes are 0.319096–0.589809 points. The card therefore
  says absolute magnitude is vintage-sensitive while model-relative shortfall
  shares are numerically clustered. Because the denominators are cell-specific
  and near a ceiling, this normalization is descriptive scale context, not
  independent robustness evidence or a third budget axis.
- **Admission challenge:** The disclosed conditional ARX route-energy result
  is 62.857859/day. Mixing it into the pinned numeric range yields 13.232694/day
  and defeats the broad headline. It remains outside the selected range because
  it consumes observed post-cutoff covariates. The conclusion is explicitly
  conditional on the ex-post, unblinded same-observed-local-information rule;
  TimesFM and Moirai lack matched 130-day cells.
- **Claim boundary:** The vintages are neither averaged nor ranked for truth.
  Changing vintage alters the saved pre-treatment training history and scored
  observations. The result is a case-local counterfactual sensitivity, not a
  variance decomposition, uncertainty interval, ATT, all-model result, or
  general AIS claim.
- **Assistant verification:** 19/19 focused tests recompute every absolute and
  normalized value, enforce information and unit boundaries, reject ten
  corruptions, validate PNG/PDF signatures, reconcile the separate manifest,
  and confirm the phase-4 parent is unchanged. The full suite passes 377/377;
  both optional manifests verify; 8 core, 146 vessel, and 1 interim input hashes
  match; provenance passes with the disclosed historical gaps; and `git diff
  --check` is clean.
- **Status:** AI implemented; **NEEDS-VERIFY** under G4.

## 2026-08-10 · Mher completed the sensitivity-budget card G4 verification

- **Decision-maker and evidence:** Mher reran the phase-4 parent check, card
  builder and freezer, focused and full tests, both optional-manifest checks,
  core input checks, provenance audit, and `git diff --check`, then pasted the
  complete terminal output in Codex.
- **Reproduced results:** Selected-model ranges remain 5.174835/day (pinned)
  and 3.646049/day (August); same-model vintage differences remain
  8.707032–11.100000/day; model-relative shortfall shares remain
  92.421498%–93.422731%.
- **Verification evidence:** 19/19 focused tests and 377/377 full tests pass;
  all five card outputs match the separate manifest; the unchanged 13-artifact
  phase-4 manifest verifies; 8 core, 146 vessel, and 1 interim input hashes
  match; provenance passes with disclosed historical source gaps; and the
  silent return to the shell prompt after `git diff --check` records success.
- **Decision:** Task 5 satisfies G4 and is `DONE`. Task 6, the separately frozen
  horizon/resolution inference frontier, may begin. This does not close the
  August source-byte archive gap, authorize vintage averaging, reopen a third
  empirical layer, or change the formal proposal.
- **Status:** Sensitivity-budget reporting task **DONE**; task 6 opened.

## 2026-08-10 · Horizon/resolution inference frontier frozen and generated

- **Decision-maker:** Mher (scope owner); implementation by AI, `NEEDS-VERIFY`.
- **Freeze timing:** The design is frozen in
  `config/horizon_resolution_frontier.yaml` (SHA-256
  `8fa1a980971dbcc5fbe3d2d8cb401e64c0cddfe053a4931fc4b06a6804999730`) before any
  block statistic was computed. It is **not** preregistered: the audit had
  already disclosed the expected eight-block, 1/9-floor pattern, and that prior
  disclosure is recorded in the design file.
- **Held fixed:** Outcome `hormuz_tanker_transits`, AR(1,7) with no exogenous
  regressors, expanding training from 2022-01-01, exclusive cutoff 2026-02-28,
  transits/day, and the 2026-02-28 to 2026-07-07 treated window. Only the
  reference partition and its resolution vary.
- **Outcome-independent origins:** Three rules are declared before generation and
  each is a pure function of the calendar, the cutoff, and the 365-day minimum
  training length: `forward_anchored_direct` (primary),
  `backward_anchored_from_cutoff` (sensitivity), and `legacy_greedy_step30`
  (audit reproduction). No rule can read the outcome; a test asserts geometry is
  invariant to the outcome path.
- **Complete enumeration:** The phase enumerates every feasible daily origin and
  reports the maximum-cardinality disjoint packing instead of greedily
  subsampling a 30-day origin lattice. Direct tiling attains the packing bound
  at every resolution; the legacy lattice forgoes 1 block at 130 days, 3 at 91,
  and 4 at 65.
- **Audit expectation reproduced:** Under `forward_anchored_direct` at 130 days
  there are 8 reference blocks, the rank p-value floor is 1/9 = 0.111111, the
  maximum attainable conformal coverage is 8/9 = 0.888889, the 80% radius is
  finite at 2095.043433 transits (interval 4773.953 to 8964.039 around a
  6868.996006 cumulative shortfall), and the 90% and 95% bands are necessarily
  unbounded because their order statistic is 9 > 8. All five recorded checks
  reproduce.
- **Locked-artifact cross-check:** `legacy_greedy_step30` at 130 days recovers
  the locked primary row exactly — 7 blocks, floor 1/8, radius 1670.171346 —
  which confirms the reproduction rule and localizes the difference to candidate
  coarsening rather than to any change of model, window, or units.
- **Disclosed resolution finding:** The 30-day resolution carries 38 blocks and a
  1/39 = 0.025641 floor, below 0.05. This is reported for completeness and is
  **not** used as evidence: a shorter block adds no observation, changes the
  quantity each block measures, and weakens block independence. The reporting
  resolution is fixed at 130 days by the frozen design, so no 5% significance is
  claimed at any resolution and a structural guard fails the build if the primary
  cell is ever described as 5%-capable.
- **Robust qualitative result:** In all 12 rule-by-resolution cells the observed
  rank sits exactly at its floor — the treated statistic exceeds every
  pre-treatment reference block under every rule and resolution. This is a rank
  position among earlier forecast errors, not an ATT and not causal
  identification.
- **Boundary preserved:** The locked block artifacts
  (`block_conformal_summary.csv`, `block_placebo_effects.csv`) are hash-verified
  read-only inputs and were not rewritten. The layer is absent from
  `run_all.py`, `settings.yaml`, and the core reproducibility manifest.
- **Affected files:** `config/horizon_resolution_frontier.yaml`,
  `src/lngfreight/horizon_frontier.py`,
  `scripts/run_horizon_resolution_frontier.py`,
  `scripts/freeze_horizon_resolution_frontier.py`,
  `tests/test_horizon_resolution_frontier.py`,
  `docs/HORIZON_RESOLUTION_FRONTIER.md`, six frozen
  `data/processed/horizon_frontier_*` artifacts plus their manifest, and this log.
- **Assistant verification:** 41/41 focused tests and 418/418 full tests pass
  locally; the manifest verifies its 6 outputs against a live rebuild.
- **Status:** AI implemented; **NEEDS-VERIFY** under G4. Task 7 does not open
  until Mher records the real terminal output.

## 2026-08-10 · Mher completed the horizon/resolution frontier G4 verification

- **Decision-maker and evidence:** Mher reran the frontier builder, the manifest
  verifier, the focused and full test suites, the core input check, the
  provenance audit, and `git diff --check`, then pasted the complete terminal
  output.
- **Reproduced results:** The primary cell reproduces exactly — 8 reference
  blocks at the packing bound of 8, rank p 0.111111 at the 1/9 floor, maximum
  attainable coverage 0.888889, a finite 80% radius of 2095.043433, and
  unbounded 90%/95% bands. The audit expectation prints `REPRODUCED`. The
  `legacy_greedy_step30` row recovers the locked primary numbers exactly (7
  blocks, floor 0.125, radius 1670.171346), confirming that the difference is
  candidate coarsening and not a change of model, window, or units.
- **Verification evidence:** 41/41 focused tests and 418/418 full tests pass;
  the frontier manifest verifies its 6 outputs and reports the locked primary
  block artifacts unchanged; `freeze_reproducibility.py --check` passes 8 core,
  146 vessel, and 1 interim input hashes; the provenance audit passes with the
  disclosed historical source gaps; `git diff --check` returns no output.
- **Correction to the issued command list:** The assistant's G4 list wrongly
  named `freeze_reproducibility.py --verify`. That mode compares every
  regenerated artifact against the committed run manifest and fails on this
  branch for reasons that predate task 6: the baseline records 77 pre-existing
  changed paths, and all 23 drifting artifacts plus `config/settings.yaml`,
  `config/sources.yaml`, and `SHA256SUMS.vessel` carry modification times
  earlier than the start of the task-6 session. Task 6 adds nothing to the core
  manifest — `freeze_reproducibility.py` contains no reference to the frontier
  layer and `CONFIG_INPUTS` is an explicit four-file tuple that excludes
  `config/horizon_resolution_frontier.yaml`. The correct input gate, used by
  every earlier G4 entry, is `--check`, and it passes.
- **Open item deferred, not repaired:** The committed core run manifest is stale
  relative to this branch. Refreezing it is out of scope here under stop rule 5
  and belongs to task 10's full-pipeline and manifest pass. It is recorded as an
  open reproducibility boundary alongside the August source-byte archive gap.
- **Decision:** Task 6 satisfies G4 and is `DONE`. The 130-day reporting
  resolution stands as frozen; the disclosed 30-day sub-5% floor remains a
  partition property and is not evidence. Task 7, the selective network-support
  frontier, may begin. This does not authorize a causal or 5% claim, a third
  empirical layer, or any change to the formal proposal.
- **Status:** Horizon/resolution frontier **DONE**; task 7 unblocked.

## 2026-08-10 · Selective network-support frontier frozen and generated

- **Decision-maker:** Mher (scope owner); implementation by AI, `NEEDS-VERIFY`.
- **Freeze timing:** Design frozen in `config/network_support_frontier.yaml`
  before any denominator was read. Not preregistered: the audit had already
  disclosed the 30 km benchmark, and that disclosure is recorded in the file.
- **Construct:** *Modeled resolved terminal-sequence support* — how many
  liquefaction-to-regasification sequences remain resolvable in the panel. Not
  observed voyages, not cargo, not physical throughput.
- **Audit benchmark reproduced:** At 30 km, Hormuz-crossing support moves
  145 → 2 sequences while all resolved sequences move 971 → 746. All four
  recorded checks reproduce.
- **Definition investigated and recorded:** A Hormuz-crossing sequence is
  resolved AND originates at a registered Gulf export project AND transits the
  strait on its modeled route — the `hormuz_exposed_leg` flag already used by
  the importer/basin exposure layer, reused rather than redefined. Counting
  every resolved sequence whose route merely transits Hormuz gives 152 pre-period
  sequences instead of 145; the seven extra originate at Oman Qalhat (3, outside
  the strait by the settings.yaml definition), Nigeria (3), and Sabine Pass (1),
  and are reported in the `non_gulf` cohort.
- **Selectivity result:** At 30 km the panel retains 76.83% of overall support
  against 1.38% of Hormuz-crossing support, a retention-share ratio of 0.017953.
  The direction is consistent at all three radii (ratios 0.012343 at 10 km,
  0.009327 at 20 km, 0.017953 at 30 km), so radius choice moves the level of
  both denominators, not the sign of the contrast.
- **Balanced cohort:** Restricting to IMOs resolved in both periods, 30 km
  support retention is 92.20% overall against 5.41% Hormuz-crossing (37 → 2), so
  the contrast is not produced by carriers entering or leaving the panel.
- **Census coverage:** The eligible fleet census holds 624 IMOs under the
  `eligible_fleet_census` design. At 30 km, 476 pre and 404 post IMOs appear in
  the resolved panel (76.3% and 64.7%); Hormuz-crossing coverage falls from 64
  IMOs to 2. These are support-observation shares, never fleet utilisation.
- **Thin-denominator guard added:** Cells with 10 or fewer pre-period sequences
  are flagged and footnoted. Without it the balanced `inside_hormuz_non_crossing`
  row reads as "300% retention" off a base of one sequence.
- **Claim boundary:** A missing modeled edge is a missing observation. The
  failure modes that remove a sequence — AIS lapse, terminal attribution
  failure, route non-resolution — are themselves plausibly correlated with the
  disruption, so no AIS-dark physical throughput may be inferred and the
  contrast is not an ATT. Every selective count is emitted with its overall
  denominator by construction; a structural guard fails the build otherwise.
- **Boundary preserved:** All four registered upstream artifacts are
  hash-verified read-only inputs and unchanged. The layer is absent from
  `run_all.py`, `settings.yaml`, and the core reproducibility manifest.
- **Affected files:** `config/network_support_frontier.yaml`,
  `src/lngfreight/network_support.py`,
  `scripts/run_network_support_frontier.py`,
  `scripts/freeze_network_support_frontier.py`,
  `tests/test_network_support_frontier.py`,
  `docs/NETWORK_SUPPORT_FRONTIER.md`, five frozen
  `data/processed/network_support_*` artifacts plus their manifest, and this log.
- **Assistant verification:** 36/36 focused tests and 454/454 full tests pass
  locally; the manifest verifies its 6 outputs against a live rebuild; the input
  gate passes 8 core, 146 vessel, and 1 interim hashes.
- **Status:** AI implemented; **NEEDS-VERIFY** under G4. Task 8 does not open
  until Mher records the real terminal output.

## 2026-08-10 · Mher completed the network-support frontier G4 verification

- **Decision-maker and evidence:** Mher reran the support builder, the manifest
  verifier, and the focused and full test suites, then pasted the terminal
  output.
- **Reproduced results:** At 30 km, all-resolved support moves 971 → 746
  (retention 0.7683) and Hormuz-crossing support moves 145 → 2 (retention
  0.0138), a retention-share ratio of 0.017953. The audit expectation prints
  `REPRODUCED`. The radius grid reproduces 10 km (567 → 396 against 116 → 1) and
  20 km (920 → 685 against 144 → 1), so the selectivity direction holds at every
  frozen radius.
- **Verification evidence:** 36/36 focused tests and 454/454 full tests pass;
  the manifest verifies its 6 outputs and reports the registered upstream
  artifacts unchanged.
- **Partial-gate disclosure:** The fifth issued command — `--check` input gate,
  provenance audit, and `git diff --check` — was not pasted in this round. Those
  three passed in the assistant run and in Mher's own task-6 G4 an hour earlier
  (8 core, 146 vessel, 1 interim), and task 7 touches no raw input, so the risk
  of drift is negligible. It is recorded here as an assistant-run-only gate for
  this phase rather than silently counted as human-verified.
- **Decision:** Task 7 satisfies G4 on its substantive outputs and is `DONE`.
  Task 8, the route-burden decomposition, may begin. The support construct and
  its missing-observation boundary carry forward unchanged.
- **Status:** Selective network-support frontier **DONE**; task 8 opened.

## 2026-08-10 · Route-burden decomposition frozen and generated

- **Decision-maker:** Mher (scope owner); implementation by AI, `NEEDS-VERIFY`.
- **Freeze timing:** Design frozen in `config/route_burden_decomposition.yaml`
  before any component was computed. Not preregistered: the audit had already
  disclosed the 30 km total and the 54.9 / 43.8 / 1.3 split.
- **Construct, fixed verbatim:** *modeled distance per nominal vessel-capacity
  m3 among retained inferred voyages*. A structural guard fails the build if the
  label drifts. Nominal capacity is a carrier design property, not measured
  cargo, and the distance is a shortest-sea-route estimate, not an AIS track.
- **Audit benchmark reproduced:** At 30 km under symmetric weighting the total
  change is 67,585,181.554 m³-nm per retained sequence (+67.585 million),
  decomposed 54.911687% common-pair share reweighting, 43.837321% entry/exit
  residual, and 1.250992% within-common-pair capacity mix. All four checks
  reproduce, and the pre/post means (662.706 and 730.291 million) match the
  locked radius-comparison artifact exactly.
- **Exact reconciliation:** The three components sum to the total change to
  within 1e-6 in every cell. The entry/exit residual is independently
  cross-checked against its conditional-mean identity
  `(Y_post - Y_common_post) - (Y_pre - Y_common_pre)`; the build fails if the
  two disagree, so the residual is the support term and not arithmetic slack.
- **Index-number disclosure:** The entry/exit residual is invariant at 43.837%
  across all three weighting schemes. Only the share/within split moves
  (Laspeyres 54.4/1.7, Paasche 55.4/0.8, symmetric 54.9/1.3). The symmetric
  Marshall-Edgeworth scheme is primary on the methodological ground that it
  privileges neither period, chosen before the components were read.
- **The split does not generalise — recorded as a limitation:** At 10 km the
  all-retained split is 22.4 / 79.8 / -2.2, close to the reverse of the primary
  cell. Under the both-period carrier restriction it is 96.8 / 9.4 / -6.2 at
  30 km. The reproduced 54.9 / 43.8 / 1.3 is therefore specific to the 30 km
  all-retained cell and may not be quoted as a general property.
- **Direction is not universal either:** 5 of the 6 radius-by-cohort cells show
  a rise; the both-period carrier cohort at 10 km gives **-2.073 million** m³-nm
  per retained sequence, the opposite sign. That cell is additionally flagged
  `percent_decomposition_is_unstable` (max component / total = 5.95), so its
  percentage shares (595 / -528 / +33) divide by a near-zero total and are not
  interpreted. A frozen stability threshold of 2.0 governs the flag.
- **What survives the grid:** only the weaker qualitative statement that
  whatever change occurs is compositional rather than within-pair; the
  within-pair capacity term is never a large share in any interpretable cell.
  The apportionment between mass moving across pairs and pairs entering or
  leaving support is not identified by this design.
- **Censoring and support:** At 30 km, 23 pre and 20 post resolved sequences are
  excluded from the complete case for want of an expanded-specification route or
  a joined capacity. Excluded and vanished sequences are never assigned a burden
  of zero and never imputed at the pre-period average. The total is conditional
  on the support documented in task 7, where Hormuz-crossing support falls from
  145 to 2 sequences, which is why the entry/exit share is large.
- **Claim boundary:** Not observed cargo ton-miles, not physical rerouting, not
  evidence that individual ships sailed farther, not an ATT, and no AIS-dark
  throughput inference. No vessel-level distance change is measured anywhere in
  the artifact.
- **Boundary preserved:** All five registered upstream artifacts, including the
  G4-verified task-7 support manifest, are hash-verified read-only inputs and
  unchanged. The layer is absent from `run_all.py`, `settings.yaml`, and the
  core reproducibility manifest.
- **Affected files:** `config/route_burden_decomposition.yaml`,
  `src/lngfreight/route_burden.py`,
  `scripts/run_route_burden_decomposition.py`,
  `scripts/freeze_route_burden_decomposition.py`,
  `tests/test_route_burden_decomposition.py`,
  `docs/ROUTE_BURDEN_DECOMPOSITION.md`, five frozen
  `data/processed/route_burden_*` artifacts plus their manifest, and this log.
- **Assistant verification:** 39/39 focused tests and 493/493 full tests pass
  locally; the manifest verifies its 6 outputs against a live rebuild.
- **Status:** AI implemented; **NEEDS-VERIFY** under G4. Task 9 does not open
  until Mher records the real terminal output.

## 2026-08-10 · Mher completed the route-burden decomposition G4 verification

- **Decision-maker and evidence:** Mher reran the decomposition builder, the
  manifest verifier, the focused and full test suites, the input gate, the
  provenance audit, and `git diff --check`, then pasted the complete terminal
  output. All five issued commands were run this round.
- **Reproduced results:** At 30 km under symmetric weighting the total change is
  67,585,181.554 m³-nm per retained sequence, split 54.911687% common-pair share
  reweighting, 43.837321% entry/exit residual, and 1.250992% within-pair
  capacity mix. The audit expectation prints `REPRODUCED`. The full
  radius-by-cohort grid reproduces, including the negative -2,072,561 m³-nm cell
  for both-period carriers at 10 km.
- **Verification evidence:** 39/39 focused tests and 493/493 full tests pass;
  the manifest verifies its 6 outputs and reports the registered upstream
  artifacts unchanged; the input gate passes 8 core, 146 vessel, and 1 interim
  hashes; the provenance audit passes with the disclosed historical source gaps;
  and `git diff --check` returns no output.
- **Limitations carried forward, not resolved:** the component split is specific
  to the 30 km all-retained cell, the direction of the total change is not
  universal across the grid, and one cell's percentage shares are formally
  uninterpretable. These are recorded as reporting constraints for task 10.
- **Decision:** Task 8 satisfies G4 and is `DONE`. Task 9, the optional
  public-data gate decision, may begin. It authorizes no download, no new
  dataset, and no third empirical layer.
- **Status:** Route-burden decomposition **DONE**; task 9 opened.

## 2026-08-10 · Optional public-data gates decided; no third layer admitted

- **Decision-maker:** Mher (scope owner); implementation by AI, `NEEDS-VERIFY`.
- **Nature of the phase:** Governance only. Nothing was downloaded, registered,
  or analysed. The phase scripts import no HTTP client, and a test parses their
  ASTs to enforce that. The source registry is hash-pinned at 53 variables and
  verified byte-identical on every run, as are the three G4-verified upstream
  manifests.
- **Decision table (5 candidates, no GO status permitted):**
  - **ERA5** — `DEFER_PENDING_SCOPE_REOPENING`. Admissible only as a weather
    falsification check after an explicit reopening. Never a regressor in the
    locked specification and never a mechanism.
  - **Sentinel-1 SAR** — `DEFER_POST_SUBMISSION`. Scene-level vessel-occupancy
    validation only, after submission. Never a daily AIS-dark throughput
    multiplier. Yang et al. 2026 already observe this event with Sentinel-1, so
    no first-observation claim is available.
  - **GFW hourly presence** — `DEFER_PENDING_SCOPE_REOPENING`. Coarse loitering
    or dwell proxies only. Never continuous track reconstruction and never a
    recomputation of the frozen route-distance construct. It cannot repair the
    missing-edge problem, because the same AIS gaps degrade presence.
  - **JODI-Gas** — **`NO_GO`**. Two kill criteria are already triggered: the
    free bulk series ends 2018-12, and redistribution rights for any derived
    series are unresolved. Post-event reporting lag is inadequate regardless.
    This is a block on facts, not a preference.
  - **MARAD advisories** — `DEFER_PENDING_SCOPE_REOPENING`. Operational
    chronology corroboration only. Never identification and never a
    treatment-date selector; the 2026-02-28 cutoff does not move.
- **Governance property:** the design permits no GO status at all, and a
  structural guard fails the build if one appears. Every candidate requires
  Mher's explicit written scope reopening recorded here before acquisition. The
  table records criteria; it cannot grant admission.
- **Accepted plan preserved:** no third empirical layer is admitted, the locked
  specification and operational-onset cutoff are untouched, and the formal
  proposal is unchanged.
- **Affected files:** `config/public_data_gate_decisions.yaml`,
  `scripts/run_public_data_gate_decisions.py`,
  `scripts/freeze_public_data_gate_decisions.py`,
  `tests/test_public_data_gate_decisions.py`,
  `docs/PUBLIC_DATA_GATE_DECISIONS.md`, two frozen
  `data/processed/public_data_gate_*` artifacts plus their manifest, and this log.
- **Assistant verification:** 26/26 focused tests and 519/519 full tests pass
  locally; the manifest verifies its 3 outputs against a live rebuild and
  records 0 datasets downloaded and 0 registry variables added.
- **Status:** AI implemented; **NEEDS-VERIFY** under G4. Task 10 does not open
  until Mher records the real terminal output.

## 2026-08-10 · Mher completed the public-data gate G4 verification

- **Decision-maker and evidence:** Mher reran the gate builder, the manifest
  verifier, the focused and full test suites, the input gate, the provenance
  audit, and `git diff --check`, then pasted the complete terminal output.
- **Reproduced results:** 5 candidates, statuses
  `{DEFER_PENDING_SCOPE_REOPENING: 3, DEFER_POST_SUBMISSION: 1, NO_GO: 1}`, no
  GO status, all requiring scope reopening, 0 datasets downloaded, registry
  unchanged at 53 variables.
- **Verification evidence:** 26/26 focused and 519/519 full tests pass; the
  manifest verifies its 3 outputs; input gate 8/146/1; provenance passes with
  disclosed historical gaps; `git diff --check` clean.
- **Decision:** Task 9 satisfies G4 and is `DONE`. Task 10 may begin. No third
  layer is admitted and the accepted no-third-layer plan stands.
- **Status:** Public-data gate decision **DONE**; task 10 opened.

## 2026-08-10 · Final evidence-to-claim audit and defence integration

- **Decision-maker:** Mher (scope owner); implementation by AI, `NEEDS-VERIFY`.
- **Stale-claim scan:** 41 thesis-facing documents scanned for 19 retired
  phrases across 5 categories, yielding 82 occurrences. **0 are asserted**;
  all 82 sit in a negating, quoting, prohibiting, structural, or correcting
  context. 0 lines conflate the PortWatch all-tanker layer with the
  LNG-specific WTO layer.
- **Scanner design, and why it matters:** a naive grep is useless here, because
  the retired phrases legitimately appear throughout correction notices,
  prohibition lists, and reporting guards. The scanner classifies each hit by
  sentence-level context, inline negation (`no ATT`, `non-ATT`), quotation, and
  structural config keys. Two failure modes are tested: planted violations must
  still be flagged (5/5 caught), and hedged text must still be cleared. Without
  the first test, "0 flagged" would be unfalsifiable.
- **Deliberate exclusions, recorded not silent:** the decision log, audit
  remediation register, execution order, external-review prompt, and the two
  literature matrices are excluded from the assertion check. The registers
  record retired claims as their function; the literature matrices catalogue
  other authors' estimands. Scanning them yields only noise.
- **Claim ledger:** all 8 headline claims cite an existing frozen artifact with
  its SHA-256 recorded, and each carries an explicit limitation. Layers are kept
  distinct: `portwatch_all_tanker` (4), `modeled_vessel_branch` (2),
  `wto_lng_specific` (1), `governance` (1). A guard fails the build if the
  LNG-specific layer is dropped while the all-tanker layer is present.
- **Defence answers prepared (5):** ARX admissibility (excluded on information
  grounds, not fit; conceding the ex-post unblinded freeze), mutable vintage
  (9.025/day same-model vintage difference exceeds the 5.175/day model spread),
  missing network support (145 to 2 is loss of observation, not of sailing),
  finite-sample p-floor (0.111 is the floor, not a null result), and construct
  limitations (composition, not behaviour). Each cites frozen artifacts, and a
  test fails if any cited artifact is missing.
- **Asset verification:** 21 PNG and 18 PDF figures, with the 3 PNG-only files
  declared as report-inline diagnostics and verified as such rather than
  flagged; 28 bibliography entries; all 4 optional layer manifests present and
  verifying.
- **Open reproducibility boundaries, reported not hidden:**
  1. `august_raw_byte_archive` — **OPEN**. August source bytes are gitignored
     and undeposited; derived artifacts are frozen and hashed.
  2. `historical_source_payload_gaps` — **OPEN_AND_DISCLOSED**. 6 fixity-only
     records predate provenance v2 and are reported, not back-filled.
  3. `core_run_manifest_staleness` — **OPEN**, requires explicit approval. The
     committed core manifest predates the pre-existing worktree changes, so
     `--verify` fails for reasons unrelated to any integration phase while
     `--check` passes. Refreezing rewrites a committed manifest across 23+
     artifacts and is not done without Mher's instruction.
  None blocks submission.
- **Governance preserved:** the formal proposal is unedited (direct Prof. Li
  authorization is not on record); no restricted Fearnleys or JODI material
  appears in any thesis-facing artifact; no third empirical layer is admitted;
  the locked specification, 2026-02-28 cutoff, and pinned July vintage are
  unchanged.
- **Affected files:** `config/final_integration_audit.yaml`,
  `src/lngfreight/claim_audit.py`,
  `scripts/run_final_integration_audit.py`,
  `scripts/freeze_final_integration_audit.py`,
  `tests/test_final_integration_audit.py`,
  `docs/FINAL_EVIDENCE_TO_CLAIM_AUDIT.md`, `docs/DEFENCE_PREPARATION.md`,
  three frozen `data/processed/final_*` artifacts plus their manifest, and this
  log.
- **Assistant verification:** 34/34 focused tests and 553/553 full tests pass
  locally; all five optional manifests verify.
- **Status:** AI implemented; **NEEDS-VERIFY** under G4. This is the final
  integration phase of the execution order.

## 2026-08-10 · Mher completed the final integration G4 verification

- **Decision-maker and evidence:** Mher reran the audit builder, the manifest
  verifier, the focused and full test suites, all five optional manifest
  verifications, the input gate, the provenance audit, and `git diff --check`,
  then pasted the complete terminal output.
- **Reproduced results:** 41 documents scanned, 82 stale-phrase occurrences,
  **0 asserted**, 0 layer-confusion lines, 8 claims all citing existing frozen
  artifacts, 5 defence answers prepared, 21 png / 18 pdf figures with pairs
  complete, 28 bibliography entries, all optional manifests present.
- **Verification evidence:** 34/34 focused and 553/553 full tests pass; all five
  optional manifests verify (horizon frontier K=8, network support 971→746 and
  145→2, route burden 67.585M with the non-generalising split disclosed, public
  data gates with no GO status, final integration with 0 asserted claims); the
  input gate passes 8 core, 146 vessel, and 1 interim hash; the provenance audit
  passes with the disclosed historical source gaps; `git diff --check` is clean.
- **Decision:** Task 10 satisfies G4 and is `DONE`. The dependency-ordered
  integration-hardening execution list (orders 0-10) is complete. Writing is the
  remaining work and optional extensions must not displace it.
- **Post-verification note:** Updating `CURRENT_PLAN.md` to record this status
  edits a document the audit scans, which shifts recorded line numbers and
  invalidates the frozen scan by design. The audit was therefore regenerated and
  re-frozen after that edit, so its manifest hash differs from the one verified
  above. The content difference is line numbers only; the verdict counts
  (82 occurrences, 0 asserted) are unchanged. A single re-run of
  `freeze_final_integration_audit.py --verify` re-confirms it.
- **Status:** Final integration **DONE**. Execution order complete.

## 2026-08-10 · Remaining open items after the execution order

- **Not blocking submission.** Recorded so they are not rediscovered late.
  1. **August raw-byte replication-archive deposit** — OPEN. Derived artifacts
     are frozen and hashed; the source bytes remain gitignored and undeposited,
     so a third party cannot re-derive them from source.
  2. **Historical source-payload gaps** — OPEN and disclosed. Six fixity-only
     records predate the provenance v2 schema and are reported, not back-filled.
  3. **Core run-manifest staleness** — OPEN and awaiting Mher's explicit
     instruction. `freeze_reproducibility.py --verify` fails because the
     committed manifest predates the 77 pre-existing worktree changes recorded
     in the 2026-08-09 baseline; `--check` passes. Refreezing requires a clean
     `run_all.py` and rewrites a committed manifest across 23+ artifacts, so it
     was deliberately not performed by the assistant.
- **Governance still open:** direct Prof. Li ratification of the revised
  estimand framing is not on record, so the formal proposal remains unedited and
  `PENDING_ESTIMAND_REALIGNMENT_DRAFT.md` stays staged.
- **Spark:** remains dormant and optional. Access is considered unlikely; the
  adapters, registry entries, and re-entry documentation are preserved and no
  result depends on it.
- **Status:** Recorded as the standing open-item list.

## 2026-08-26 · Repository hygiene pass and multi-event ML branch opened

- **Decision-maker:** Mher (researcher), implementation by AI.
- **Decision:** Bring the untracked implementation layer under version control,
  clear a blocking git lock, set a repo-local commit identity, and open branch
  `ml/multi-event-propagation` for the additive ML work.
- **Root cause found:** a zero-byte `.git/index.lock` dated **2026-08-24** had
  been silently rejecting every commit. It was not a discipline failure; git had
  been jammed for two days. Removed, along with orphaned `tmp_obj_*` objects and
  a stray `.__wtest` write probe.
- **Committed (was untracked, never in git):** six modules
  (`claim_audit`, `horizon_frontier`, `network_support`, `observability_frontier`,
  `route_burden`, `vintage_matrix`), twelve test files, seven config
  specifications, ~25 run/freeze/verify scripts, and sixteen results documents
  including those cited as G4-verified in `CURRENT_PLAN.md`. Roughly 20,000 lines.
  Until today none of the committed results reproduced from a clean clone.
- **WTO vintage state clarified (no change made):** `data/raw/wto_hormuz/` holds
  five captures. `sources.yaml` pins `voy_intake_index_lng_export.csv`
  (2025-01-01 → 2026-07-15), which is in `SHA256SUMS` and verifies OK. The
  2026-08-09 capture (`…30549d8cfd3b`, → 2026-08-09) is the registry-review
  verification fetch and remains **deliberately unpromoted**, per
  `DATA_REGISTRY_REVIEW_2026-08.md`. This is a coherent governance state, not an
  inconsistency; promotion requires a registry-path refetch and Mher's sign-off.
- **Trailing zeros checked and confirmed genuine.** An independent vintage
  comparison found no date reported 0.0 in the 2026-06-01 capture and positive in
  the 2026-08-09 capture. The post-cutoff index is zero on 155 of 163 days with
  eight isolated partial-loading days, reproducing the figures already recorded
  in `WINDOW_EXTENSION_V2_RUNBOOK.md`. The one documented revision
  (2026-07-06, 0.0 → 29.21) lies outside the compared range. No endpoint
  contamination; no correction required.
- **Affected files:** `.gitignore`, `docs/ML_TRAINING_ACTION_PLAN.md`, and the
  newly tracked implementation layer.
- **Status:** Hygiene **DONE** except two items that require Mher to run code:
  (1) full `pytest` run and the manifest refreeze recorded as OPEN on 2026-08-10;
  (2) reclaiming ~2.76 GB of virtualenvs. Regenerated artifacts under
  `data/processed` and `reports/figures` are deliberately left uncommitted
  pending that test run.

## 2026-08-26 · Diagnosis of the eight standing test failures

- **Decision-maker:** Mher (researcher), diagnosis by AI.
- **Run:** `PYTHONHASHSEED=0 python -m pytest -q` → **575 passed, 8 failed**,
  identical to the 2026-08-09 baseline. The hygiene pass changed no test outcome.
- **The eight failures have exactly two root causes.**

**Cause A — `config/sources.yaml` drift (6 failures).** Pinned
`f1d1c27e8cb3…`, actual `ffd509ccdc6f…`. The registered-variable count assertion
still passes, so no variable was added or removed. The diff is the **2026-08-19
Bloomberg refusal**: five `license:` fields moved from "rights unverified …
pending confirmation" to "Bloomberg did not authorise thesis use (2026-08-19);
excluded from thesis", plus an explanatory comment block. This edit predates the
hygiene pass (worktree mtime 2026-08-25); it was committed, not created, today.

  The gate is behaving correctly. The change is real and permanent, so
  **reverting would be wrong and refreezing is the correct resolution.** It is
  not performed here for the reason already recorded on 2026-08-10: refreezing
  rewrites G4-verified manifests.

  Failures: `test_public_data_gate_decisions` (3),
  `test_portwatch_sensitivity_budget_card` (2), `test_model_vintage_matrix` (1).

  **Blocker before refreezing.** `scripts/run_all.py` and eight other modules
  still invoke the Bloomberg layer that the 2026-08-19 refusal excludes. A clean
  `run_all.py` is a precondition of the refreeze, so the Bloomberg scope decision
  must be settled first. **This is an open decision for Mher, not a mechanical
  fix.**

**Cause B — self-inflicted, and fixed (contributed 1 row).** The stale-claim
scan rebuilt to 83 rows against a written 82. The extra row was line 343 of the
new `docs/ML_TRAINING_ACTION_PLAN.md`, where the "do not write" vocabulary list
contained the literal banned token matching `\bATT\b`, so the scanner counted
the prohibition itself as a stale claim. Resolved by paraphrasing rather than
adding the file to `excluded_paths`; no frozen config touched. Confirmed by
Mher's re-run: the shape mismatch is gone (82 vs 82).

**Correction — there is only ONE root cause, not two.** After the Cause B fix,
`test_final_integration_audit` still failed, now on two shifted `line_number`
values rather than a row count: `docs/DATA_SOURCES.md` 66 -> 69 and 127 -> 135.
That file was edited by the **same 2026-08-19 Bloomberg refusal** as
`sources.yaml` (+26/-11 lines, recording that the help desk did not authorise
thesis use and the layer is excluded). The insertions pushed two long-standing
flagged lines down the file.

So **all eight failures trace to the 2026-08-19 Bloomberg decision**, which sat
uncommitted in the worktree from 2026-08-19/25 until the hygiene pass committed
it. One scope decision plus one refreeze clears all eight together.

- **Status:** **OPEN**, gated on a single decision: what happens to the Bloomberg
  layer in `scripts/run_all.py`. Remove it, or keep it as an optional branch
  skipped by default. Once settled, run a clean `run_all.py` and refreeze; the
  eight failures resolve as one.

## 2026-08-26 · Phase 2 fitted; aggregate reallocation share fails its placebo null

- **Decision-maker:** Mher (researcher), implementation by AI. **Prototype only:**
  `scripts/run_propagation_model.py` has not been executed by Mher.
- **Spec frozen** (`config/multi_event_propagation.yaml`, 2026-08-26) with onsets
  derived by a pre-registered rule rather than adjudicated against
  `EVENT_CHRONOLOGY.md`, which covers the Hormuz event only. Red Sea moves from
  the drafted 2023-12-15 to **2024-01-13**; Panama from 2023-07-01 to
  **2023-12-19**; Ever Given **2021-03-23**; Black Sea **2022-02-24** (external
  anchor, pre-2022 drift disclosed).
- **Independent check on the locked cutoff.** The same sharp rule applied to
  Hormuz returns **2026-03-01**, one day after the independently locked
  operational-onset cutoff of 2026-02-28. The cutoff is unchanged and was not
  derived this way; this is corroboration, not a re-derivation.
- **Sanity gate PASSED.** The fit recovers Bab el-Mandeb -> Cape of Good Hope at
  loading 0.738, **rank 1 of 28 receivers**, without being told the edge exists.
- **Negative result, and it changes the plan.** The aggregate reallocation share
  fails its placebo null. Red Sea observed gross gain 18.4 transits/day sits at
  the **64th percentile** of 120 pseudo-onset draws (null median 13.9, p95 35.3).
  Summing residual gains over 27 chokepoints integrates more noise than the 7.9
  transits/day the Red Sea actually lost. **The scalar "moved" term assumed by
  the moved/hidden/lost decomposition in `ML_TRAINING_ACTION_PLAN.md` is not
  estimable this way.** A per-receiver screen still selects Cape of Good Hope,
  Suez Canal and Mona Passage for the Red Sea, so the substitution map survives
  as a qualitative object.
- **Separate finding, affects the PRIMARY path not Phase 2.** Hormuz shows a
  large pre-cutoff excursion that no prior document records: monthly means fall
  from 49.7/day (2025-10) to 41.1 (2025-11) to **34.7 (2025-12, 0.62x baseline)**,
  recover to 49.4 (2026-02), and the week ending **2026-02-22 reaches 60.4/day,
  above baseline**, immediately before the collapse. The AR(1,7) counterfactual is
  trained through 2026-02-27 and therefore anchors on that rebound. This bears
  directly on the anticipation and residual-autocorrelation concerns already
  raised and should be checked before the shortfall figure is quoted again.
- **Status:** Phase 2 **fitted, pending Mher's confirming run**. Two open
  decisions: what replaces the aggregate reallocation term, and whether the
  pre-cutoff excursion changes the primary counterfactual.
