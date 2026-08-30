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

## 2026-08-27 · Hormuz revision-robust ML Phase 0 design freeze

- **Decision-maker:** Mher (researcher).
- **Technical plan:** `docs/HORMUZ_TECHNICAL_EXECUTION_PLAN.md`, version 1.1.
- **Plan commit:** `87bd3464b8074ab769030473689cb5e46dbac24e`.
- **Code foundation:** `6ef6191aa8340928ca439a02244dfec68439f2b3`.
- **Primary outcome:** `n_tanker`.
- **Development population:** 27 non-Hormuz chokepoints.
- **Full data start:** 2019-01-01.
- **Model-development period:** 2019-01-01 through 2023-12-31.
- **Hyperparameter-validation period:** 2024-01-01 through 2024-12-31.
- **Detector calibration:** multi-year out-of-fold/prequential residuals from
  the 27 non-Hormuz units, excluding pre-declared exposed unit-days. Hormuz is
  excluded from calibration.
- **Hormuz pre-onset surveillance:** 2025-12-01 through 2026-02-27, scoring
  only.
- **Locked operational onset:** 2026-02-28.
- **Common scoring end:** 2026-07-07.
- **Forecast horizons:** 1, 7, and 30 days.
- **Detector forms:** raw-level and scale-invariant.
- **Measurement states:** July and August remain separate and are never
  averaged.
- **Core scope:** B1 and A1--A4.
- **Gated extension:** B2 positive control; B3 opens only if B2 passes its
  design and support gate.
- **Outside committed scope:** B4 LNG-darkness pilot and any new causal layer.
- **Model-loss rule:** global-model underperformance against AR or
  seasonal-naive benchmarks is a valid negative result and does not authorize
  post-hoc tuning.
- **Claim boundary:** predictive and descriptive evidence is not a causal ATT
  or structural effect.
- **Post-Hormuz tuning:** prohibited.
- **Input hashes:**
  - Plan:
    `480ccd5ca9b7e8d70c75c19f9aa60974e3fd5adc2ec06a5ac33c380f94d17ef9`.
  - July PortWatch state:
    `66f3a54afb042103f3e0afc9670568cb7be245394ec04eba55ebd158593f579d`.
  - August PortWatch state:
    `0bc806a4c384723debff08053d6fcbb915a03ee9fdf7b23c73d76d9bcb885bcb`.
- **Executable configuration status:** design frozen now; executable
  configurations will be hash-frozen after A1 and B1 create them and before
  any real-data run.
- **Status:** Phase 0 design **FROZEN**. Changes require Mher's explicit
  approval and a new plan/configuration version.

## 2026-08-27 · Technical execution plan amended to v1.2; A2 accepted; A3 frozen

- **Decision-maker:** Mher (researcher). **Entry written by Claude under Mher's
  explicit bounded assignment to append this amendment**; the log otherwise
  remains Mher's alone.
- **Supersedes a hash in the Phase 0 entry above.** That entry records the plan
  at `480ccd5ca9b7e8d70c75c19f9aa60974e3fd5adc2ec06a5ac33c380f94d17ef9`. The
  amended plan is
  `3f94689495dab052d5fb802fa9695ba620b254b821143c4437a6053324eb804e`. The Phase 0
  design itself is unchanged; only the plan document moved.
- **Plan v1.2, two corrections**, both from Mher's review of the completed A2 run:
  1. **A4 baseline scope.** Mode 4 said "all predeclared baselines". A local
     AR(1,7) needs a unit-specific fit and the leave-Hormuz-out contract forbids
     fitting on Hormuz, so no Hormuz local AR can exist. Mode 4 now scores the
     global model and seasonal naive on Hormuz; local AR stays a
     development-population comparator on the 27 units. `hormuz_training_prohibited`
     is unchanged, and fitting a local AR on pre-surveillance Hormuz history was
     considered and declined.
  2. **Track ownership.** Section 5 assigned Track A to ChatGPT. Mher reassigned
     Track A to Claude on 2026-08-27, accepting on the record that the section 8
     cross-review of Track A is unavailable for work Claude wrote itself. The
     section 5 file lists are unchanged; only the owner is.
- **Config pin moved:** `config/hormuz_detection.yaml` now pins plan v1.2 and its
  new hash, and `validate_detection_spec` requires v1.2. The A1 audit returns
  PASS against the amended document.
- **A2 accepted.** Pooled 17-feature ridge beat both declared baselines on the
  frozen 2024 tasks: mean MASE about 0.74-0.78, against about 0.82-0.83 for local
  AR(1,7) and about 1.0 for seasonal naive, winning at 22/27, 23/27 and 20/27
  chokepoints across the three horizons. Mher's review struck three overclaims
  from the interpretation: that pooling as such produced the gain (the models
  differ by 17 features against two), that a share of variance was "learned" (the
  pooled R-squared is dominated by cross-unit scale; within units the mean
  correlations are about 0.14, 0.13 and 0.05 and R-squared against each unit's own
  2024 mean is about 0.01, -0.01 and -0.09), and that "no Hormuz row was read"
  (Hormuz is loaded with the 28-unit panel but never materialised into a task,
  fitted, selected on, or scored). Penalty selection was insensitive across the
  grid: at most 0.000391 MASE, about 0.05%.
- **A3 design FROZEN** at config
  `2e96df590fbc8ab4df80cf1d0c59bb251a1e769f8ad76299d871d1950ebb4b32`. One
  transferable threshold per model, horizon and detector form; per-unit thresholds
  prohibited because Hormuz never enters calibration and would have no threshold to
  receive. Macro-average episode rate as the calibration target, not a pooled
  row-level quantile. `threshold_loco` and `end_to_end_loco` named and run
  separately, the latter withholding only cross-unit objects while the held-out
  unit keeps its own context scale. Unstandardised raw score `s_raw = yhat - y`.
  Masked gaps are segment boundaries with right-censored episodes. The frozen
  object is the scaling algorithm, not a constant: context scales refit per fold
  and horizon through each fold's `fit_end`, with Hormuz fixed at 2025-11-30 for
  A4 and a per-unit drift diagnostic reported. Strict greater-than exceedance, the
  conservative discrete-tie rule and eligible-days-over-365.25 exposure were
  proposed by Claude and explicitly ratified by Mher.
- **Why the config pin above is not `9163449d…`.** That earlier hash was recorded
  before a reconciliation pass Mher directed on 2026-08-27, and no run was ever
  made under it. The pass changed no design clause. It moved the phase-status
  token from `phase_a2_candidate_for_mher_freeze` to `phase_a2_accepted_by_mher`
  (with the matching `PHASE_LADDER` entry in `src/lngfreight/global_forecaster.py`),
  because the old token contradicted A2 having been accepted; and it rewrote the
  narrative comment above the `detector:` block, which still read "NOT FROZEN",
  described the block as "PROPOSED", and pointed at an `unresolved` key that had
  already been renamed `resolved`. `phase` stays `A2` and
  `detector_contract.calibration_status` stays `deferred_to_A3`, so the A2
  contract the accepted run was made under is unchanged. Two matching
  contradictions were cleared in `docs/HORMUZ_DETECTION_MODEL_CARD.md`: a header
  claiming A2 was "pending Mher's verification run" and citing plan v1.1, and an
  A3 paragraph still describing the three Claude items as "reviewed without
  objection" under a veto clause the config no longer carries.
- **A2 gate cleared.** The validation rerun from the clean checkpoint returned
  `PASS`, `git.dirty: false`, and both artefact hashes unchanged (`efcbf724…`,
  `5b38cb08…`). That was the condition on starting A3.
- **A3 implemented, not accepted.** `--phase calibrate` and
  `src/lngfreight/detector_calibration.py` execute the frozen design; the phase
  refuses to start unless the accepted A2 manifest is PASS, made under the
  current config hash, made from a clean tree, and still matching its artefact
  hashes. Claude's run: 110,121 admissible residual rows over 60 folds,
  2021-01-01 to 2025-11-30, 5,628 unit-days event-masked, all sealing assertions
  in their required state. **Mher has not run or accepted this**, and A4 stays
  closed until he does.
- **Two items await Mher's ruling.**
  1. **`discrete_ties.rule` is degenerate as written.** The episode rate is not
     monotone in the threshold; at the bottom of the range every day exceeds and
     a unit's record becomes one unending episode per segment, so the rate falls
     back below target. Read literally the rule selects a threshold firing on
     99.997% of unit-days that still "passes". The run uses the smallest
     threshold from which the rate stays at or below target for every higher
     threshold, which is what the block's own stated reason ("the attainable
     threshold on the conservative side") asks for. Both are reported per row.
     Claude proposes the second reading; the ruling is Mher's.
  2. **The context scale is quantised for 15 of 27 units.** `n_tanker` is an
     integer count, so a low-volume unit's MAD is an integer and its scale is a
     small integer multiple of 1.4826 that a longer history does not move. The
     per-fold refit is real and runs through each fold's own `fit_end`; the
     estimate is coarse. This narrows the intended contrast between the two
     detector forms on those units.
- **Status:** superseded by the 2026-08-28 entry below. At the time of writing:
  plan v1.2, A2 accepted, A3 implemented and run by Claude under detector design
  version 1, acceptance pending Mher's ruling on the two items above.

## 2026-08-28 · A3 detector design version 2; tie rule amended and ratified

- **Decision-maker:** Mher (researcher), on his own run of `--phase calibrate`
  at commit `6dc39c8`. **Entry written by Claude under Mher's explicit
  instruction to record the ratification**; the log otherwise remains Mher's.
- **Mher's verification of the version-1 run.** `A3 CALIBRATE PASS` from a clean
  commit, A2 gate reproduced, 110,121 admitted residuals and 5,628 event-masked
  unit-days over 60 folds, every leakage and sealing assertion in its required
  state, no Hormuz or August data in calibration, output hashes reproduced. The
  numerical warnings are the known Apple Accelerate BLAS artefact and did not
  produce invalid results; the only `NaN` are the deliberately blank held-out
  columns on operational rows.
- **Ratified: the stable-tail tie rule.** `discrete_ties.rule` becomes *the
  smallest candidate threshold whose macro-average episode rate is at or below
  two episodes per chokepoint-year and remains at or below that target for every
  higher candidate threshold*. Strict greater-than exceedance is unchanged.
  Version 1's rule — "smallest threshold whose achieved rate is at or below
  target" — read word by word selected a threshold firing on 99.997% of
  unit-days, because the episode rate is not monotone in the threshold and at
  the bottom of the range every day exceeds, collapsing each unit's record into
  one unending episode per segment. **No A3 result was ever accepted under
  version 1.**
- **Also ratified:** the superseded reading stays computed and written to every
  row for audit, and the selected operational threshold's **unit-day exceedance
  share** is now reported alongside it. Shares are counted over unit-days rather
  than distinct score values, which differ materially because integer counts
  make scores tie.
- **Accepted as a documented limitation, not corrected:** the context scale is
  quantised for 15 of the 27 units, because `n_tanker` is an integer count so a
  low-volume unit's MAD is an integer and its scale is a small integer multiple
  of 1.4826 that longer history does not move. **Mher did not authorise changing
  the scaling algorithm**, and `evaluation.context_scale_timing` is untouched.
- **Config pin moved.** Detector `design_version: 2`, config
  `7e877911652d8492aa6bcefd75aea219debcd707323550603b0388f5b151aff1`,
  superseding `2e96df59…`. `validate_detector_spec` refuses to run against
  version 1 or against the superseded rule name, so the degenerate reading
  cannot silently execute again. Because the configuration hash moved, A2 was
  re-verified under it and returned unchanged score and prediction hashes.
- **Status:** superseded by the entry below. At the time of writing: A3 design
  version 2 complete and running with no outstanding ratification item,
  acceptance still resting with Mher.

## 2026-08-28 · A3 ACCEPTED; August authorised for A4 only; A4 implemented

- **Decision-maker:** Mher (researcher). **Entry written by Claude under Mher's
  explicit instruction to record the acceptance**; the log otherwise remains his.
- **A3 ACCEPTED.** Mher accepted detector design version 2 and its confirming
  artefacts, by hash:
  - config `7e877911652d8492aa6bcefd75aea219debcd707323550603b0388f5b151aff1`
  - calibration `b2f04b233c1a700d10a780423b5ef130b09bcf8f53018e0fd4ae329983f181f2`
  - false alarms `7468d40322f5e6526ea7338c20a872a0ec76d3149cff7e1aa5408016d570deee`
- **A3 thresholds FROZEN.** The twelve operational thresholds are recorded in
  `a3_acceptance.operational_thresholds`. Two independent sources must now agree
  before A4 runs: the accepted CSV, verified by hash, and that record. A4
  refuses on any drift and never recalibrates.
- **August authorised, narrowly.** `scripts/run_hormuz_detection.py` is added to
  `allowed_consumers` for `portwatch_chokepoints_vintage_20260809_snapshot`,
  **solely for A4**, on Mher's instruction that this "does not promote or average
  the August vintage". `never_join_or_average` stays true and A4 asserts it at
  runtime; July remains the pinned primary, so `promotion_policy` is not engaged.
  The entry authorises no other phase.
- **A4 implemented, not run.** `--phase final` and
  `src/lngfreight/hormuz_stress.py` execute plan v1.2 section 6 A4: the four
  frozen modes, alarm date, delay, 7- and 30-day severity, within-state severity
  rank, cross-state agreement, and the proportional/residual decomposition of the
  July-to-August revision. **Claude did not execute final Hormuz scoring and did
  not inspect any Hormuz outcome**, per Mher's instruction. Only the gate check
  (`--check-only`), which opens no panel, and synthetic-data tests were run.
- **No tuning after A4, enforced rather than promised.** Every estimated object
  is built from pre-surveillance data and the system is digested before any
  Hormuz surveillance outcome is read. Reading those outcomes trips a one-way
  latch; any fit, calibration or threshold load attempted afterwards raises. The
  run makes that attempt deliberately and records that it was refused. After
  scoring the digest is recomputed and must equal the sealed one. Both the
  refused attempt and the digest equality are sealing assertions.
- **One A4 design point the frozen config did not pin, and how it was settled.**
  Nothing pinned which fit window the "frozen global model" uses at deployment.
  A4 uses **the last frozen rolling fold's fit** rather than inventing a window:
  the fold geometry is frozen, the final fold is the most recent system it
  defines, and its residuals sit inside the calibration the accepted thresholds
  were set on. Using the 2023-frozen A2 coefficients instead would pair a stale
  model with thresholds calibrated on per-fold refits. This is declared in
  `final.frozen_system` and in the manifest; **Claude chose it and it is
  reversible if Mher disagrees.**
- **Status:** Plan **v1.2**. A2 **ACCEPTED**. A3 **ACCEPTED**, thresholds frozen.
  A4 **implemented and tested, not executed**. B3 untouched.

## 2026-08-28 · A4 EXECUTED, corrected without tuning, and FROZEN

- **Decision-maker:** Mher (researcher). **Entry written by Claude under Mher's
  explicit instruction to record the A4 result**; the log otherwise remains his.
- **A4 EXECUTED.** The frozen system was scored on Hormuz under both measurement
  states. Manifest status **PASS**, no sealing failures, all 22 sealing
  assertions in their required state, system digest `1606c568…` identical before
  and after scoring, model fit `fold_060` (the last frozen rolling fold).
- **Corrected without tuning.** The first run's outputs carried six execution
  artefacts. **No model, threshold, scale, prediction, alarm date or severity
  value was changed to fix any of them**, and the accepted A3 objects were not
  touched:
  1. Mode 3 evaluated both detector forms, though plan v1.2 declares a
     scale-invariant transport only, producing **six raw-level transport cells
     no declaration named**. A raw-level score is not invariant to the
     proportional component of the vintage revision, so such a cell confounds
     the transport with the rescaling the decomposition exists to separate.
     Each mode now declares `evaluated_forms`; the runner reads the declaration.
  2. Nothing checked that what ran was what was declared. The run now asserts
     **exact set equality over (mode, model, horizon, form) in both directions**
     and fails on any difference.
  3. The git checkpoint was captured *after* the outputs were written, so it
     reported the run's own untracked artefacts as working-tree dirt and `dirty`
     was necessarily true. It is now captured before the phase writes anything.
  4. Only the configuration hash was recorded. The manifest now records the plan
     hash, verified against the plan on disk, and the observed hash of every
     input read.
  5. The cross-vintage revision file was written to a path derived from another
     output's stem, so no declaration named it and no hash covered it. It is now
     declared in `final.outputs` and hashed.
  6. Pre-onset alarms were implicit in the summary. They are now counted and
     listed in the manifest, with `final.pre_onset_alarms.suppress: false`
     asserted at runtime.
- **Verified effect of the correction.** Summary rows 36 → 30. On the 30 that
  remain, `threshold`, `fired`, `alarm_date`, `detection_delay_days`,
  `episodes`, `exceedance_days`, `scored_days`, `severity_7_day` and
  `severity_30_day` are **bit-identical** to the pre-correction run. Exactly
  **four ranks move** — `global_ridge` at h=1, 7 and 30 and `seasonal_naive` at
  h=30, all raw-level, all in the `august` group — mechanically, because
  `severity_rank_within_state` ranks within the evaluated set and six cells left
  it. No rank in any other group moves. The daily, cross-vintage and revision
  artefacts are byte-identical, and mode 3's raw-level score remains recorded
  for all 1,314 of its scored days: **out of the evaluated set, not out of the
  record.**
- **Coverage: exact.** 30 declared cells = 30 evaluated cells; no missing cell,
  no undeclared cell. Two same-state modes at both forms plus one transport at
  one form, over two models and three horizons.
- **RESULT, and the caveat that travels with it.** All 30 evaluated cells fire.
  **Sixteen of the thirty fire before the operational onset** of 2026-02-28, the
  earliest on 2025-12-01 — the first day of the surveillance window, 89 days
  early. **These are pre-onset false alarms, not early detection of the event.**
  They are the cost side of a threshold calibrated to a development-unit episode
  rate, and A3 had already shown that transfer is uneven. They are recorded as a
  finding and **must not prompt any post-A4 tuning**: no threshold, window,
  scale or model change in response to them. The plan's stop condition stands.
- **A4 is a one-unit stress test.** It scores one unit over one event. Nothing
  here estimates detection power; no confidence statement about the detector
  follows from a single alarm; no causal reading of an alarm, a delay or a
  severity value is authorised; and a cross-state difference is not a
  measurement-error estimate. `severity_rank_within_state` orders cells inside
  this run only — A3 does not persist per-day development residuals, so ranking
  Hormuz against the development distribution would need a recalibration A4 must
  not do. Severity is in each form's own units and is not comparable between the
  raw-level and scale-invariant forms.
- **Hashes. Configuration pin moved** to
  `8eed44731628b1db613e4722e764b0236134018803bf7e9d40c301fc662e2d23`,
  superseding `477fe803…`; this is the value `--confirm-frozen-spec` requires.
  **Plan v1.2 hash moved** to
  `5dea3cb784c4a06adbbeb511daf64efbca22d4d89715b1ffedde8967c347b884`,
  superseding `3f946894…` — the plan gained an addendum under its amendment
  record, **not a version bump**: the design is unchanged and the loader still
  requires plan 1.2. This supersedes the plan hash in the Phase 0 freeze entry
  above.
- **Output hashes, from the final manifest:**
  - daily `67a349a3ab10c2e0fd67e1cfc1965dd9c3f154964a83eaa9e06d5a134af1812c`
  - summary `c9a2af17a01b3eed48cc27a5b353972fa1c7730792652809ca52618781063508`
  - cross-vintage `85f6230ee2edb9af4f10cfa734f3bd41d57511d48b0fd1cd768414babce20761`
  - cross-vintage revision
    `4aae80087ed19f161ca3f1d6ab17fbf0670e5b1a813f1b10b61ad90194619776`
- **Commits.** Correction `ead5500`; artefacts from the clean-checkpoint rerun
  `e080b49`. The run was made from `ead5500` with an **empty working tree**, so
  the manifest's checkpoint reads `dirty: false` and describes the checkout the
  run was actually made from.
- **Documented provenance imperfection, accepted rather than corrected.** The
  A3 calibration manifest is recorded in `inputs` with observed hash
  `3331c978a1b7dda3…` and a **null declared hash**: the configuration pins the
  two A3 artefacts that carry the thresholds (`calibration`, `false_alarms`) but
  never pinned the manifest itself. `all_declared_hashes_match` skips null
  entries rather than claiming a match it cannot check. The exposure is small:
  `verify_accepted_a3` still gates on that manifest's `status`, its
  `detector_design_version` and its ratification flag, the two threshold-bearing
  artefacts *are* hash-verified against acceptance, and the clean git checkpoint
  pins the file's contents at `ead5500`. **Mher's decision: document it here
  rather than move the configuration hash again and rerun.**
- **Affected files:** `config/hormuz_detection.yaml`,
  `docs/HORMUZ_TECHNICAL_EXECUTION_PLAN.md` (addendum under the amendment
  record), `scripts/run_hormuz_detection.py`, `tests/test_hormuz_stress.py`
  (45 tests, 17 new and all on scope and provenance rather than on any scored
  quantity), and the five declared A4 artefacts in `data/processed/`.
- **Status:** **A4 FROZEN.** Plan v1.2; A2 **ACCEPTED**; A3 **ACCEPTED**,
  thresholds frozen; A4 **EXECUTED, CORRECTED AND FROZEN**. Track A is complete.
  Next work is thesis interpretation and write-up. **The detector is not to be
  tuned from these results.** B3 remains untouched and still requires the B2
  gate to be accepted.

## 2026-08-28 · Frontier artifacts restored; Defect B resolved in favour of the locked partition

- **Decision-maker:** Mher (researcher); implementation by AI (Claude).
- **Finding that prompted it.** `data/processed/horizon_frontier_summary.csv` is
  cited by `\src{}` in Chapters 5, 6, 9 and 11 and in the source line of
  Figure 6.3, and was **absent from the working tree**.
  `git log --all --diff-filter=A` confirms it was never committed on any of the
  seven branches, so Figure 6.3 could not have been regenerated by anyone. The
  numbers survived only in the tracked `docs/HORIZON_RESOLUTION_FRONTIER.md`.
- **Restoration.** `scripts/run_horizon_resolution_frontier.py` was re-run. All
  four upstream artifacts hash-verified against
  `config/horizon_resolution_frontier.yaml`
  (`block_conformal_summary` `431c6c61…`, `block_placebo_effects` `5565c063…`,
  `placebo_time_effects` `6659c710…`, `panel_aligned` `4d26dbe0…`). The
  regenerated `docs/HORIZON_RESOLUTION_FRONTIER.md` is **byte-identical** to the
  tracked copy, so the artifact reproduces exactly. Five files rewritten:
  `horizon_frontier_summary.csv`, `_blocks.csv`, `_block_geometry.csv`,
  `_diagnostics.json`, `_audit_expectation.json`. This also discharges the G4
  verification the document was waiting on.
- **Decision on the two constructions.** The **locked seven-block partition**
  (`legacy_greedy_step30`, floor 0.125, maximum coverage 87.5%, 80% interval
  5,198.8–8,539.2) remains the reported primary. The **exhaustive eight-block
  packing** (`forward_anchored_direct`, floor 0.111, maximum coverage 88.9%,
  80% interval 4,774.0–8,964.0) is reported beside it as a declared partition
  sensitivity. The treated statistic is 6,868.996 transits under both, and under
  `backward_anchored_from_cutoff` as well.
- **Rationale.** The eight-block rule attains a *lower* p-value floor. Promoting
  it after the treated statistic was known would be a partition choice made in
  the direction of a smaller floor — the selection this design forbids. The
  frontier artifact's own `role: primary` label designates the primary cell of
  *its* sensitivity grid, not the thesis's reporting partition; that ambiguity is
  what let Figure 6.3b disagree with Table 6.2 in print.
- **Manuscript changes.** `make_thesis_figure_supplements.py` now reads both
  130-day rules and draws both, labelled "locked partition / 7 blocks" and
  "exhaustive packing / 8 blocks", with a single shared unbounded 90/95% row;
  panel (b) carries seven bands, four of them claiming nominal coverage.
  Table 6.2's single `Block conformal` row is split into the two partitions.
  Methods gains `\label{sec:uncertainty-falsification}` and a paragraph stating
  the anti-selection rationale and the arithmetic behind the two partitions
  (1,154 reference days from the 2023-01-01 anchor; the 30-day lattice puts
  consecutive retained blocks 150 rather than 130 days apart, forgoing 20 days
  at each of six joins; contiguous tiling attains ⌊1,154/130⌋ = 8).
- **Corrected while there.** Chapter 6 claimed "the entire disagreement between
  estimators fits inside the narrowest of the six bands". The bracket the figure
  actually draws spans **all** points, 1,997 transits, against a narrowest band
  of 1,105 — the claim was false as drawn. It now states that the admitted-
  specification spread of 949 is smaller than the narrowest band and that the
  span exceeds it only once the two conditional sensitivities are included.
- **Affected files:** `scripts/make_thesis_figure_supplements.py`,
  `reports/figures/thesis_estimator_interval_agreement.{pdf,png}`,
  `TUM_Bachelor_Thesis/figures/thesis_estimator_interval_agreement.{pdf,png}`,
  `TUM_Bachelor_Thesis/chapters/05_methods.tex`,
  `TUM_Bachelor_Thesis/chapters/06_results_throughput_shortfall.tex`,
  `data/processed/horizon_frontier_*`, `docs/DECISION_LOG.md`.
- **Status:** **Recorded. NOT BUILD-VERIFIED.** Neither the device nor the
  container TeX installation has `biblatex.sty` or `ngerman.ldf`, and CTAN is
  blocked by the egress allowlist in both, so the manuscript could not be
  compiled in this session. Structural checks only: begin/end environments
  balanced, braces balanced, all seven rows of Table 6.2 carry three columns.
  **A clean `latexmk` run is required before submission.**

## 2026-08-28 · FEDCom inventories admitted on a cite-do-not-redistribute basis

- **Decision-maker:** Mher (researcher); implementation by AI (Claude).
- **Decision:** The Fujairah FEDCom weekly inventory series is **admissible**.
  Individual weekly figures may be cited in the manuscript, each to its own
  freely-readable article. The assembled series is **not** redistributed. The
  companion bunker-assessment file is **excluded outright**.
- **Rationale — why the Bloomberg precedent does not transfer.** The Bloomberg
  layer was not quarantined for its acquisition mode. T23 records the trigger as
  "Vendor did not authorise thesis use; the entire layer is excluded, not
  pending" — a rights refusal, recorded 2026-08-19. No refusal exists here and
  none is needed, because nothing is being licensed: the underlying statistic is
  an official Fujairah Energy Data Committee publication, running since January
  2017. Citing a published official figure to the freely-readable article
  reporting it is ordinary secondary-source practice.
- **Where the exposure actually is.** S&P Global Commodity Insights is FEDCom's
  appointed distributor, so the compiled 19-week series is a different object
  from any single cited number. It is bounded the same way the Bloomberg-derived
  processed artifacts were on 2026-08-09: `data/processed/fujairah_weekly_stocks.csv`
  added to `.gitignore`; raw rows already covered by `data/raw/*`;
  `scripts/build_fujairah_inventory_panel.py` stays version-controlled so the
  series is rebuildable rather than shipped. Manuscript use is limited to
  bounded aggregates and individually cited observations, per the public/private
  split already ruled in T23.
- **Bunker file excluded.** `data/raw/fujairah_fedcom/fujairah_bunker_assessments_2026.csv`
  holds Platts price assessments quoted inside those articles. Assessments are an
  authored proprietary product, not a government statistic, and the distinction
  above does not reach them. Not to be cited, plotted, or built on. Nothing in
  the repository reads it; it is retained so the exclusion is visible.
- **Standing and residual risk.** This is a research-data governance judgement on
  the project's own conservative boundary, not legal advice. The weakest link is
  that the transcription index republishes the S&P weekly reports in full; the
  decision relies on the cited *figures* being official public statistics rather
  than on that republication being authorised. A one-line disclosure to Zhenyu
  Wang is recommended.
- **Affected files:** `.gitignore`, `data/raw/fujairah_fedcom/SOURCES.md`,
  `docs/FUJAIRAH_INVENTORY_EVIDENCE.md`, `docs/DECISION_LOG.md`.
- **Status:** **Settled.** Unblocks Fujairah citation in Chapters 9 and 11.
  Advisor disclosure outstanding.

## 2026-08-29 · Tier 0 of the technical remediation plan: five integrity corrections

- **Decision-maker:** Mher (researcher); implementation by AI (Claude).
- **Scope.** `Research Record/plan-technical-remediation.md`, Tier 0 only.
  Each item is a place where a document asserted something the artifacts do not
  support. No estimator, no gate and no frozen result was changed.

- **T0.1 — the "3.7% apart" claim is retired as an unconditional statement.**
  The legacy counterfactual pipeline reads `data/processed/panel_aligned.csv`,
  which begins at the `analysis_start: "2022-01-01"` of
  `config/model_admission_protocol.yaml`. The network-adaptation event forecasts
  read the raw PortWatch snapshot through
  `experiments.panel_bakeoff.protocol.load_raw_panel`, which applies no such
  filter and begins 2019-01-01, with Chronos then seeing the trailing 2,048 days.
  The two runs score the identical 130 days and the identical 529 observed
  transits, so the difference is a training-information difference, not a defect.
  Under the legacy window Chronos is 3.7% **below** AR (6,615 against 6,869);
  under the expanded history it is 8.4% **above** AR (7,042 against 6,496). The
  sign reverses, so the sentence "the two models agree to within 3.7%" is a
  property of the legacy training window and cannot be quoted without it. The
  headline is now the quantity that is stable across both specifications:
  **observed Hormuz traffic is 92.5–93.0% below counterfactual**. Signal
  dominance survives unchanged; the percentage sentence does not.
- **T0.2 — the sensitivity is now an artifact, not a hand-typed table.**
  `experiments/network_adaptation/specification_sensitivity.py` writes
  `hormuz_shortfall_specification_sensitivity.csv` and its manifest. It refits
  nothing: it reads four frozen forecast artifacts and recomputes their sums on
  the common scored window, and it fails loudly if the two specifications do not
  score the same observed total. `config/network_adaptation.yaml` gained the two
  output paths and now exposes the declared Chronos `context_length`, which
  `run_event_forecasts.py` checks against the code constant so the config and the
  run cannot drift apart.
- **T0.3 — the specificity claim is corrected.**
  `docs/NETWORK_ADAPTATION_SECONDARY_CHAPTER.md` sections 5.3, 6 and 8 read as
  though model choice determined whether the network effect exists. It does not:
  both models reject the global null, both put Panama and Yucatan below adjusted
  p=0.003 at every block length, and they agree on four of five corridor signs.
  What model choice materially changes is the apparent **vessel-class
  specificity**, and therefore the credibility of the substitution reading. That
  is not evidence that Chronos found a true signal AR missed. There is no ground
  truth for network substitution here, and the Chronos control family may be
  underpowered — the global control statistic is an equal-weighted mean over
  scaled series, so Cape Ro-Ro at a 1.77/day pre-event mean moves it as much as
  Malacca dry bulk at 50.5/day, and Cape Ro-Ro's own Chronos reference range at
  the primary 14-day block is [−8.62, 0.37] in units of its own mean. The chapter
  now states the specificity conclusion as conditional on the control-power check
  that plan item T1.1 specifies. **That check has not been run.**
- **T0.4 — the forecasting claim is split by horizon.** Chronos improves on AR at
  both horizons, but the clustered 95% reduction interval is [11.4%, 25.0%] at
  30 days and [1.4%, 23.7%] at 130 days. "Substantially improves forecasting" is
  a 30-day statement. **130 days is the horizon the event window uses**, so the
  weaker interval is the one that must be quoted wherever the benchmark is used
  to license the event analysis.
- **T0.5 — what the admission rule gates is stated explicitly.** Every gate in
  `experiments/panel_bakeoff/admission_rule.json` is a point estimate: macro mean
  MASE reduction ≥ 0.05 per horizon, win rate > 0.50, coverage error ≤ 0.05,
  width ratio ≤ 1.10. The clustered bootstrap intervals and the
  `cluster_bootstrap_probability_meets_threshold` column were never gates. The
  94.7% figure was being reported as a near-miss against a threshold it was not
  measured against; `RESULTS.md` now says so, and notes that the 130-day point
  reduction of 14.5% clears 0.05 outright.

- **Affected files:** `config/network_adaptation.yaml`,
  `experiments/network_adaptation/{protocol.py,run_event_forecasts.py,specification_sensitivity.py,README.md}`,
  `experiments/panel_bakeoff/RESULTS.md`,
  `docs/{ADVANCED_ML_RECONSIDERATION,CORRIDOR_TRANSMISSION_WORK_PLAN,INFERENCE_NOTES,MODERN_TSFM_BENCHMARK,NETWORK_ADAPTATION_SECONDARY_CHAPTER}.md`,
  `scripts/make_results_summary.py`, `reports/current_results_summary.md`
  (regenerated), `tests/test_network_adaptation.py`.
- **Status:** **Settled.** Tier 0 is complete; the project is internally
  consistent and write-up may begin. Tier 1 is untouched — in particular the
  control-power check (T1.1) that the corrected specificity wording now defers
  to, and the Chronos pretraining-contamination diagnostic (T1.5).

## 2026-08-29 · Tier 1 items T1.5 and T1.3: contamination bounded, Cape demoted

- **Decision-maker:** Mher (researcher); implementation by AI (Claude).
- **Scope.** `Research Record/plan-technical-remediation.md`, the two Tier 1
  items that run on already-executed artifacts. Both refit nothing. No estimator,
  gate, threshold or frozen result was changed.

### T1.5 — Chronos pretraining overlap is bounded, not cleared

- **Bound.** Chronos-2 was released 2025-10-20
  (`docs/MODERN_TSFM_BENCHMARK.md`), so the event window 2026-02-28 to
  2026-07-07 lies **provably outside** any pretraining corpus. The shortfall
  estimate carries no overlap risk. The generalisable "Chronos forecasts this
  panel better" claim does, because its eight rolling origins score 2023-01-01
  to 2025-11-05.
- **Test.** `experiments/panel_bakeoff/pretraining_contamination.py` looks for
  the signature contamination would leave — an advantage concentrated in the
  earliest origins, decaying toward the release — and does not find it. The
  latest origin (2025-06-29, the only window reaching past the release, by 16 of
  its 130 days) keeps a 16.4% advantage at 30 days and 16.7% at 130 days, with
  clustered 95% intervals of [11.5%, 21.2%] and [10.8%, 22.3%], and the highest
  130-day win rate of the eight origins. Against the other seven pooled the
  difference is −1.3 and +2.5 points, intervals [−6.5, +3.1] and [−6.6, +19.3].
  The fitted trend across origins is positive at both horizons.
- **The confound runs the same way.** Context length grows with the origin and
  caps at 2,048 days from origin 6, so later origins are advantaged, not the
  early ones a contamination story needs.
- **Limit, stated in the write-up rather than waiting to be asked.** This bounds
  the risk; it does not prove a clean corpus. Amazon's disclosure does not permit
  verifying absence, and "latest origin" is a proxy for "least ingested", not a
  clean/dirty split.

### T1.3 — Cape of Good Hope is demoted from corroboration to context

- **Finding.** The hypothesis in the plan is confirmed, and it explains both
  facts it was raised to explain. Cape tanker traffic roughly doubled with the
  December 2023 Red Sea diversion (annual daily means 9.24 in 2023 → 18.89 in
  2024 → 16.89 in 2025 → 18.62 in 2026). Across the eight pre-event origins the
  mean residual, scaled by the pre-event mean, shifts by **+0.578 for AR and
  −0.555 for Chronos** at the onset, against a largest non-Cape shift of 0.136 —
  more than four times larger, in both models, in opposite directions.
- **How each model fails.** AR under-predicts the Cape from the diversion onward
  and never catches up (+0.43 at the last origin, ending 2025-11-05), which
  inflates its Cape event statistic. Chronos catches up but read the ramp as a
  trend and extrapolated it at the origin sitting on the ramp: at 2024-01-26 it
  over-predicts by 2.17 times the pre-event mean across 130 days, with a
  residual-on-lead slope of −0.57/day.
- **Consequence for the bake-off headline.** That corridor alone produces the one
  origin where Chronos loses the 130-day panel. Origin 4's macro MASE reduction
  is **−6.5% with Cape and +16.6% without it**, and the worst cell in the whole
  bake-off is Cape Ro-Ro there (Chronos MASE 28.9 against AR 2.0).
- **Consequence for the chapter.** The Cape reference distribution pools two
  regimes and is centred on a mean describing neither. Re-centring on the last
  three origins cuts AR's excess from 0.303 to 0.196 and Chronos's from 0.668 to
  0.410, while Panama and Yucatan are indifferent to the choice (Chronos 0.161 →
  0.147 and 0.184 → 0.193). **Cape is reported as context and is not counted
  toward the finding, which now rests on Panama and Yucatan.** Cape is *not*
  dropped from the frozen set: removing a corridor after seeing its result is the
  selection problem this design exists to avoid.
- **Limit.** The re-centring is descriptive, not a re-estimated test; it supplies
  no corrected p-value, and the recent regime it centres on is three origins long.
  The chapter's limitation 6 now records that the bootstrap's weak-stationarity
  assumption is *violated* at Cape and merely *not visibly violated* elsewhere.

- **Affected files:** `experiments/panel_bakeoff/{pretraining_contamination.py,RESULTS.md,README.md}`,
  `experiments/network_adaptation/{cape_residual_drift.py,analyze.py,README.md}`,
  `config/network_adaptation.yaml`,
  `docs/{MODERN_TSFM_BENCHMARK,NETWORK_ADAPTATION_SECONDARY_CHAPTER}.md`,
  `tests/{test_panel_bakeoff,test_network_adaptation}.py`, plus regenerated
  artifacts under both `outputs/` directories and
  `reports/figures/cape_residual_drift.png`.
- **Status:** **Settled.** Remaining Tier 1: T1.1 (control-family hardening,
  highest value, may change the headline), T1.2 (Red Sea/Cape positive control),
  T1.4 (all-28 Romano-Wolf, retrospective). T0.3's conditional wording still
  awaits T1.1.

## 2026-08-29 · T1.1: the control family is hardened, and a claim is withdrawn

- **Decision-maker:** Mher (researcher); implementation by AI (Claude).
- **Scope.** `Research Record/plan-technical-remediation.md` item T1.1, the
  plan's highest-value item and the one flagged as able to change the headline.
  It did. `experiments/network_adaptation/control_robustness.py` refits nothing:
  every variant reuses the executed forecasts, the same residual vectors, the
  same seeds and the same synchronized bootstrap.
- **Pre-declaration.** The volume threshold of 5 transits/day was named in the
  remediation plan before the run and written into
  `config/network_adaptation.yaml` before execution, with
  `computed_on: pre_event_observations_only`. It excludes Cape Ro-Ro (1.77/day),
  Panama Ro-Ro (2.12) and Yucatan Ro-Ro (0.96) and retains seven controls. **No
  control was removed on the basis of a post-event result**, and the full
  ten-control family is retained and reported under every block length.

### What the plan expected, and what is actually true

- **The plan's stated mechanism is wrong, and the check corrected it.** The worry
  was that Cape Ro-Ro's wide reference range inflates the global control
  distribution. It does not: dropping Cape Ro-Ro *widens* the Chronos reference
  (95th percentile 0.0815 → 0.0832). A wide single column matters for that
  column's own Romano–Wolf test, not for a ten-column mean, which damps it. The
  widest single contributor is Gibraltar dry bulk (+0.0125).
- **The control family is not underpowered.** In all 42 control cells the
  reference 95th percentile (0.075–0.094 for Chronos at 14-day blocks) sits below
  the equal-weighted tanker global statistic of 0.107, so a control-class
  movement the size of the tanker anomaly would have been flagged.
- **The Chronos specificity result is robust.** Its control p-value exceeds 0.05
  in **41 of 42** cells. Under every weighted or volume-eligible variant the
  control statistic turns negative: −0.047 inverse-variance, −0.067 volume,
  −0.077 volume-eligible. The one exception is a leave-one-out refit at the
  non-primary 7-day block dropping Malacca Ro-Ro, p=0.0496.

### The claim that is withdrawn

- **AR's control-family failure is an equal-weighting artifact.** Equal-weighted
  full family p=0.0007; volume-eligible p=0.4305; inverse-variance p=0.4919;
  volume-weighted p=0.5691. Dropping Cape Ro-Ro alone moves it from 0.0007 to
  0.0772. The failure is carried by three series averaging 0.96 to 2.12 transits
  a day being weighted equally with series fifty times their size.
- **Therefore the secondary chapter can no longer claim that the foundation model
  was needed to see the network pattern.** Both models find the anomaly, and both
  pass the non-tanker falsification test once the family is measured rather than
  assumed. Chronos stays primary for its declared pre-event accuracy reason; it is
  not doing identification work AR could not do here. This resolves the
  conditional wording T0.3 introduced, against the model-comparison reading.
- **The substantive finding is stronger for it.** Vessel-class specificity at
  Panama and Yucatan now holds under *both* forecasters and every control
  specification tested, instead of depending on which model a reader trusts.

### A second sensitivity, disclosed rather than waited for

- The same hardening applied to the restricted tanker family shows the **global
  screen is weighting-sensitive**. Chronos: equal 0.107 (p=0.0001),
  inverse-variance −0.089 (p=1.000), volume −0.031 (p=0.792). AR: 0.216
  (p=0.0001), 0.052 (p=1.000), 0.088 (p=0.9998). Cause: the two largest corridors
  in the family, Malacca (75.5/day) and Gibraltar (43.0/day), moved *below*
  counterfactual, so volume weighting drives the aggregate negative.
- The equal-weighted and volume-weighted statistics answer different questions —
  "did the typical screened corridor move up" versus "did aggregate screened
  traffic move up" — and both are now reported. Neither is the finding.
- Leave-one-corridor-out on the tanker family: the Chronos global result is
  p=0.0001 without any corridor except the Cape, where it is p=0.174. Since T1.3
  demoted the Cape on independent pre-event grounds, the chapter states plainly
  that the global screen leans on a corridor it no longer counts. **The Cape is
  not dropped** — that would be the selection problem the design exists to avoid.
- **Where the evidence now sits:** the corridor-level Panama and Yucatan
  Romano–Wolf results. They do not use family weights at all, clear adjusted
  p=0.003 at every block length, are indifferent to re-centring the historical
  reference on the recent regime, and hold under both models.

- **Supporting change:** `global_mean_test` gained an optional pre-event
  `weights` argument and a `reference_q950` output. With `weights=None` it is
  byte-identical to before — `network_adaptation_inference.csv` reproduces to the
  same hash. Five loader helpers in `analyze.py` were renamed from private to
  public so the new script reuses the validated loaders instead of duplicating
  them; no logic changed.
- **Affected files:** `experiments/network_adaptation/{control_robustness.py,inference.py,analyze.py,protocol.py,README.md}`,
  `config/network_adaptation.yaml`,
  `docs/NETWORK_ADAPTATION_SECONDARY_CHAPTER.md` (sections 5.1, 5.3, 5.6 new, 6,
  7, 8), `tests/test_network_adaptation.py`, plus the new outputs.
- **Status:** **Settled.** Tier 1 remaining: T1.2 (Red Sea/Cape positive control)
  and T1.4 (all-28 Romano-Wolf, retrospective). T1.4 should now also report the
  weighting sensitivity, since the same objection applies to any family it forms.

## 2026-08-29 · T1.2: the Red Sea positive control, re-run under the current machinery

- **Decision-maker:** Mher (researcher), who chose the re-run over documenting the
  design gap; implementation by AI (Claude).
- **Scope.** `Research Record/plan-technical-remediation.md` item T1.2. New
  experiment `experiments/positive_control/`, new frozen spec
  `config/redsea_positive_control.yaml`. **The designation is inherited, not
  made here.** The Cape of Good Hope was named the receiver on route topology,
  and the 16-corridor eligible family frozen on pre-onset volume, in
  `config/hormuz_receiver_test.yaml` on 2026-08-27 and executed on 2026-08-28,
  before any post-onset outcome was inspected. This run changes the estimator and
  the inference and nothing else.

### Why the B2 result could not simply be cited

The frozen B2 design and the corridor design answer the same question with
different machinery: B2 uses a donor-median-adjusted baseline-normalised weekly
statistic over an 8-week horizon with a temporal pseudo-onset null and
deliberately no spatial p-value; the corridor design uses a leakage-safe forecast
counterfactual over 130 days with a synchronized block bootstrap and Romano-Wolf.
Presenting one as validating the other required making them commensurable.

### What was held identical to the corridor design

Chronos-2 univariate and recursive AR(1,7); the 130-day horizon; the scaled mean
observed-minus-counterfactual statistic; the synchronized circular moving-block
bootstrap at 7/14/28-day blocks with 10,000 draws; Romano-Wolf step-down within
explicitly named families. The historical reference is eight contiguous, disjoint
130-day out-of-sample origins ending the day before each onset — exactly 1,040
days, no post-onset information, and `_reference_matrix` refuses to run otherwise.
**Both declared onsets are reported and neither is the headline**;
`validate_protocol` refuses a configuration that names one primary, carrying the
B2 constraint forward mechanically.

### Result

- **The designated receiver ranks 1 of 16 in all four onset-by-model cells, at
  every block length, Romano-Wolf p = 0.0001.** Event statistic 0.592 to 0.759,
  cumulative gap +839 to +1,077 transits. Its studentized statistic under Chronos
  at the external onset is 20.9 against 4.7 for the runner-up.
- The family orders end to end the way a real reallocation should: designated
  receiver first at +0.715, designated emitter last at −0.650, and the emitter is
  not used to construct the receiver's statistic. Context series behave as
  designed — Bab el-Mandeb −0.317 to −0.650, Suez −0.205 to −0.555.
- **The vessel-class controls fire, and that is the finding, not a failure.**
  Cape Ro-Ro +1.77 to +2.17 and Cape dry bulk +0.29 to +0.46, adjusted p = 0.0001.
  The diversion rerouted long-haul traffic of every class around the Cape; a
  control family that stayed null here would be broken. **This is a positive
  control for the control family itself**, and it is a stronger answer to T1.1's
  power question than a quantile comparison: the same controls that fire here are
  silent at Panama and Yucatan, so that silence means something.
- **The family-level global screen is weak here too** (Chronos, external onset,
  p=0.5534 over 16 corridors), which independently corroborates T1.1's finding
  that averaging a family dilutes a single strong corridor signal. Corridor-level
  tests are where the evidence lives in both experiments.

### A model weakness the positive control exposed

At the register onset, Chronos's Cape Ro-Ro forecast climbs from 3.6 transits a
day at lead 1 to 157 at lead 130, averaging 55.4 against an actual 3.15, giving a
statistic of −48.5. Cape Ro-Ro is a low-volume series whose level was tripling
(0.92/day in 2023 to 3.25 in 2024) and the register onset's training window
includes the first month of that ramp. AR under-predicted instead, at 1.08/day.
**Same series, same event and same failure mode as the single origin at which
Chronos loses the 130-day panel bake-off (T1.3).** Two independent encounters make
it characterisable rather than an outlier: on low-volume count series at an origin
sitting on the onset of a regime change, the foundation model extrapolates the
ramp and the transparent model does not. Reported in chapter section 5.4, not
trimmed.

### What it does not license

It does not transfer its ex-ante status to the Hormuz corridor screen, and the
chapter says so in three places. What it changes is the burden: the objection to
the corridor analysis is now about which corridors were chosen, not about whether
the machinery can detect a reallocation at all.

- **Chapter restructured:** the positive control is section 5 and the Hormuz
  results moved to section 6, so the method is validated before it is applied.
  Sections 6-9 renumbered from 5-8 with all in-text cross-references updated.
- **Affected files:** `config/redsea_positive_control.yaml`,
  `experiments/positive_control/*` (new), `docs/NETWORK_ADAPTATION_SECONDARY_CHAPTER.md`,
  `tests/test_positive_control.py` (new), `reports/figures/redsea_positive_control.png`.
- **Status:** **Settled.** Tier 1 remaining: T1.4 only (all-28 Romano-Wolf,
  retrospective by label, and it should now also report the weighting sensitivity
  T1.1 found).

## 2026-08-29 · T1.4: the full 28-corridor ranking, disclosed — Tier 1 closed

- **Decision-maker:** Mher (researcher); implementation by AI (Claude).
- **Scope.** `Research Record/plan-technical-remediation.md` item T1.4, the
  last Tier 1 item. New script
  `experiments/network_adaptation/all_corridor_ranking.py`. Refits nothing: it
  reads the executed event forecasts and the executed pre-event residual vectors.
- **Label, enforced not asserted.** Every row of the artifact and the manifest
  carries `status = retrospective_disclosure_not_confirmatory`, and a contract
  test fails if it does not. Adjusting over 28 hypotheses instead of five is a
  harsher correction, not a prospective one. Romano-Wolf cannot recreate a
  selection that did not happen, and all 28 of these post-event results had
  already been inspected before the five were named.

### Where the restricted five actually sit

Primary model, primary block length, ranked by studentized statistic out of 28:
**Yucatan 2nd, Panama 4th, Cape 6th, Gibraltar 26th, Malacca 27th**, with the
treated Hormuz anchor last at −26.7.

- **Panama and Yucatan survive the widened family** — adjusted p < 0.05 in all
  six model-by-block-length cells. This is the strongest form of the corridor
  result available in this data, and it is what the chapter now rests on.
- **The Cape does not.** Flagged in three of six cells and not in the primary
  one (Chronos p=0.2304; AR's 14-day 0.0485 sits on the threshold). T1.3 demoted
  the Cape for an unrelated pre-event regime break; the widened family arrives at
  the same place independently.
- **Gibraltar and Malacca were never candidates**, 26th and 27th, flagged in none
  of the six cells. Their place in the restricted set came from route topology,
  not from the data. Topology-based selection was **partly right**: it found two
  of the three consistently-flagged corridors and also brought in two that finish
  near the bottom.
- **Three corridors nobody selected clear the threshold somewhere.** Mindoro
  Strait in all six cells, outranking every member of the five under Chronos;
  Balabac Strait in three, Chronos only; Kerch Strait in one, AR at 7-day blocks.
  Mindoro (3.64/day) and Balabac (3.51/day) sit below the 5 transits/day volume
  threshold declared for the control work — but **that threshold was declared for
  the control family, and applying it here after seeing this ranking would be
  precisely the selection this run exists to disclose.** They are reported as
  they fall. The design has no mechanism to attribute either movement.
- **Kerch illustrates why the ranking is studentized.** Its AR statistic is
  −0.579 while its studentized value is +2.18, because AR's own historical
  reference there is centred at −0.826. A corridor can sit well below its
  counterfactual and still be unusually above the errors the model normally makes
  on it.

### The network as a whole did not move

The 28-corridor global statistic fails to reject under both models and every
weighting: equal-weighted Chronos +0.017 at p=0.611, volume-eligible −0.043 at
p=0.913, p=1.000 under both weighted variants; AR negative throughout. Whatever
section 6.1 establishes about the restricted five is a statement about those five
corridors and not about the network. This also carries T1.1's weighting
sensitivity into the widest family, as that item's closing note required.

- **Affected files:** `experiments/network_adaptation/{all_corridor_ranking.py,control_robustness.py,analyze.py,README.md}`,
  `config/network_adaptation.yaml`, `docs/NETWORK_ADAPTATION_SECONDARY_CHAPTER.md`
  (new section 6.7, plus limitation 1, section 7 and the conclusion),
  `tests/test_network_adaptation.py`, `reports/figures/all_corridor_ranking.png`.
  Two helpers in `control_robustness.py` were renamed from private to public so
  the new script reuses the declared weighting and eligibility logic rather than
  restating it; the artifact reproduces to the same hash.
- **Status:** **Settled. Tier 1 is complete.** Tier 0 and Tier 1 of the
  remediation plan are both closed. Remaining: Tier 2 (documentation and framing,
  about four hours) and Tier 3 (reproducibility, citations and figures).

## 2026-08-29 · Tier 2: documentation and framing — Tier 2 closed

- **Decision-maker:** Mher (researcher); implementation by AI (Claude).
- **Scope.** `Research Record/plan-technical-remediation.md` items T2.1–T2.5.
  No code ran and no artifact changed. All five items are statements about
  already-executed results, verified against those artifacts and against the
  IMF's own published documentation.

### T2.1 — what `n_tanker` contains: the documentation does not say

Taken from IMF PortWatch's dataset documentation and platform changelog, not
inferred from the data, as the item required.

- PortWatch publishes five ship categories — container, dry bulk, general cargo,
  ro-ro, tanker — and defines `n_tanker` in one line as the number of tankers
  transiting on that date. **It does not enumerate tanker sub-types and does not
  say whether gas carriers are inside `n_tanker` or outside the classification.**
  There is no gas category, so one of the two must hold and the publisher does
  not state which.
- **Consequence: no LNG-specific framing survives, in either direction.** If gas
  carriers are inside, they are inseparable from crude, product and chemical
  tankers; if outside, LNG is invisible to this outcome. This is now the
  measurement basis of the chapter's claim boundary rather than a caveat.
- **Three versioning facts found in the changelog, two of which touch this
  design.** The five-class split is a 2024 change from two classes; the
  general-cargo/ro-ro classification was refined in 2025, inside the calibration
  window and across half the negative-control family; and the Strait of Hormuz
  chokepoint boundary was refined in March 2026. None is a break *within* the
  analysed series — revisions are applied backwards and the snapshot was taken
  2026-07-15 — so the exposure is across vintages, which
  `PORTWATCH_VINTAGE_REGISTER.md` already quantifies.
- **A citation error was corrected while sourcing this.** The chapter attributed
  *Nowcasting Global Trade from Space* (WP/25/93) to Arslanalp, Koepke and
  Verschuur. Crossref gives nine authors; those three wrote the 2021 paper
  (WP/2021/225) that PortWatch cites as the chokepoint dataset's methodology
  source. `references/literature_seed.bib` already had the correct nine-author
  entry, so only the chapter prose was wrong. Both PortWatch pages and the 2021
  paper are now cited entries.

### T2.2 — the project-level decision surface, stated once

New section 4.1. **690 resampling p-values over 56 tested series-level
hypotheses**, plus five point-estimate admission gates and 16 paired comparisons
in the bake-off that contribute no p-values at all.

- 486 corridor-level Romano–Wolf p-values (30 restricted tanker, 60 negative
  controls, 168 all-28 disclosure, 228 positive control) and 204 family-level
  bootstrap p-values (12 + 132 robustness re-runs + 24 + 36).
- **What Romano–Wolf covers is one family at one cell**, and the section says
  explicitly that it does not span models, block lengths, onsets, families, the
  two events, or the weighting variants.
- **The all-cells reporting rule is stated as a rule so it cannot be relaxed.**
  Its bite is now visible: 17 of 30 restricted-family cells are individually
  flagged but only Panama and Yucatan clear all six; 42 of 192 receiver-family
  cells are flagged but only the ex-ante designated receiver clears all twelve.
  Reporting flagged cells alone would have given three positive corridors in
  section 6 and six in section 5. Labelled a discipline, not a joint level.

### T2.3 — the window end is a data boundary, and says so

New section 2.2. **7 July 2026 is the snapshot's last date (12 July) minus the
declared five-day trailing-completeness buffer.** The 130-day horizon is a
*consequence* of that boundary, not an independent choice that happened to fit.
A longer window exists — a fresh capture reaches 1 August — but adopting it swaps
the vintage: 25 more days move the shortfall +0.6% while the vintage change moves
it −17.1% at identical dates, which is why the extension stays a sensitivity.
Also disclosed: 7 July 2026 is itself a dated escalation in
`EVENT_CHRONOLOGY.md`, so the analysis stops on the day of an escalation whose
consequences fall outside the window.

### T2.4 — the forecast-only property, now claimed

New section 3.1. Every counterfactual in both event experiments comes from a
model that sees only the treated series' own past; synthetic control, IFE and
nuclear-norm completion exist only in the pre-event bake-off league and are not
imported by either event experiment (verified by grep as well as by design).

- **The claim worth making is structural.** A donor design for a chokepoint
  disruption fails exactly when this chapter's hypothesis is true: if traffic
  reallocated, the donors are treated, and the counterfactual absorbs the
  response. The more successful the reallocation, the worse the bias. That
  failure mode is absent here by construction, as is interference from the
  anchor, since Hormuz, Suez and Bab el-Mandeb are context and not donors.
- **The cost is stated with it:** no contemporaneous information is used at all,
  so limitation 5 is the price of the guarantee rather than a separate problem.

### T2.5 — what the negative control tests, reframed

New section 6.3.1, plus a corrected framing at the top of 6.3 and in section 2.

- **The declared symmetric reading was wrong in one direction.** Given Yang et
  al.'s SAR evidence of general reorganization — and given that section 5.3 shows
  the Red Sea diversion moving every vessel class — control-class movement would
  *not* have been an automatic falsification. The family is a one-sided test for
  a corridor-wide traffic artifact, and could only have failed informatively in
  one direction. Stated as a limitation (new item 10) rather than left in the
  frozen config, which is deliberately not edited: the freeze records what was
  declared, the chapter records what it licenses.
- **A materially wrong sentence was caught and replaced during drafting.** The
  first draft said non-tanker traffic at Panama and Yucatan does not sit above
  counterfactual. It does: two of the four control series carry positive scaled
  deviations, and under Chronos **Yucatan Ro-Ro at +0.218 is numerically larger
  than the Yucatan tanker deviation of +0.215**. Specificity rests entirely on
  the reference distributions — Yucatan Ro-Ro averages 0.96 transits a day and
  its 95% range is about three times the tanker range, so the same deviation
  studentizes to +1.35 against +6.96. The section now says this, and says that a
  reader who rejects the historical-error reference for small series should treat
  the specificity claim as unsupported rather than weakly supported.
- **What the null rules out:** a corridor-wide traffic artifact common to all
  classes — boundary, observation-process or counting artifacts, and fleet-wide
  or seasonal uplift. **What it does not:** that the anomaly is displaced Hormuz
  volume. Every tanker-market driver that does not pass through Hormuz remains
  live, and the design has no vessel identity to separate them.

- **Affected files:** `docs/NETWORK_ADAPTATION_SECONDARY_CHAPTER.md` (new
  sections 2.1, 2.2, 3.1, 4.1, 6.3.1; revised section 2 control framing, section
  6.3 opening, section 7, limitations 3, 8 and new 10–12; references),
  `experiments/network_adaptation/README.md`, `experiments/panel_bakeoff/RESULTS.md`
  (pointers only, so the surface is stated once), `references/literature_seed.bib`
  (three new verified entries).
- **Verification:** `tests/test_network_adaptation.py`,
  `tests/test_positive_control.py`, `tests/test_panel_bakeoff.py` — 39 passed.
  A dangling cross-reference to a non-existent section 5.6 was also fixed.
- **Status:** **Settled. Tier 2 is complete.** Remaining: Tier 3
  (reproducibility, citations and figures), whose figure list is already partly
  satisfied by the Tier 1 artifacts.

## 2026-08-30 · Public-data gate registry pin re-pinned; the pin was stale, not the registry

- **Decision-maker:** Mher (researcher), implementation by AI (Claude).
- **Symptom.** Thirteen tests failed across
  `tests/test_final_integration_audit.py` (8),
  `tests/test_public_data_gate_decisions.py` (2) and
  `tests/test_sensitivity_input_gate.py` (3).
  `scripts/run_public_data_gate_decisions.py:77` raised
  `integrity pin drift for sources_registry`: the gate design expected
  `f1d1c27e8cb3…` for `config/sources.yaml`, the file hashes to `f53e9fa7cf2d…`.
  `config/sources.yaml` was clean against `HEAD`, so the question was which side
  had gone stale.

- **Finding: the pin is stale, and had been stale since the day it was written.**
  `f1d1c27e8cb3…` matches **no committed state of `config/sources.yaml` on any of
  the seven branches**. It is a working-tree state from 2026-08-09 that sat
  uncommitted until the hygiene pass, preserved elsewhere only in the tracked
  `data/processed/model_admission_pre_run_checkpoint.json`. The design was frozen
  at `2026-08-09T23:59:44Z`, hours after `a164276` was committed that same day
  with 52 variables; the pin captured the tree *after* the August PortWatch
  vintage became the 53rd variable but *before* anything else landed.

- **Three edits separate the pin from `HEAD`. None was made by this phase.**

  | Δ | Date | Commit | Registry change | In this log? |
  |---|------|--------|-----------------|--------------|
  | `f1d1c27e` → `ffd509cc` | 2026-08-19 | `9a07f4f` (committed 08-26) | Bloomberg declined thesis use: five `license:` fields moved from "rights unverified … pending confirmation" to "did not authorise thesis use (2026-08-19); excluded from thesis", plus a comment block | **Yes** — 2026-08-26 diagnosis |
  | `ffd509cc` → `77cf12d6` | 2026-08-27 | `20111b5` | `scripts/run_hormuz_measurement_audit.py` added to `allowed_consumers` for `portwatch_chokepoints_vintage_20260809_snapshot` (Track B phase B1) | **No** — inline comment in `sources.yaml` only |
  | `77cf12d6` → `f53e9fa7` | 2026-08-28 | `97856b1` | `scripts/run_hormuz_detection.py` added to the same `allowed_consumers`, for A4 only | **Yes** — 2026-08-28 A3/A4 entry |

- **The invariant the pin exists to protect never broke.** The pin's stated
  purpose is to prove the gate phase registered nothing. The variable set is
  **byte-for-byte the same 53 entries** at the pin state, at `9a07f4f`, and at
  `HEAD` — verified by diffing the parsed `variables` keys across all three. No
  variable was added, removed or renamed; the August vintage was never promoted;
  `never_join_or_average` and `promotion_policy` are untouched. Only the
  byte-level proxy moved, and it moved under three edits this phase did not make.

- **Decision: re-pin to `f53e9fa7cf2d…`.** Reverting would undo a licence
  refusal and two authorised consumer declarations — it would be a data-governance
  regression dressed up as a test fix. This also executes the resolution the
  2026-08-26 entry had already reached and deferred: *"the change is real and
  permanent, so reverting would be wrong and refreezing is the correct
  resolution."* The superseded hash is retained in the design as
  `superseded_sha256`, with the full chain in a comment, so the audit trail
  survives the re-pin rather than being overwritten by it.

- **Why the 2026-08-26 blocker does not apply.** That entry gated the fix on a
  clean `run_all.py` because refreezing rewrites G4-verified manifests. It does
  not bind here: this gate's own freezer declares
  `core_run_all_dependency: "none"` and
  `core_reproducibility_manifest_dependency: "none"`, and the pin is a
  hand-declared value in a design config, not a derived manifest. No manifest was
  rewritten. Separately, the Bloomberg steps have been opt-in behind
  `ENABLE_BLOOMBERG_LAYER=1` since `a164276` (2026-08-09), so the default
  pipeline is already free of the excluded layer.

- **Gap closed while here.** The 2026-08-27 Track B consumer addition (Δ2 above)
  was recorded only as an inline comment in `config/sources.yaml` and appears
  nowhere in this log — "Track B" does not occur in it at all. It is entered into
  the record above.

- **The re-pin uncovered a second, unrelated defect it had been masking.** With
  `sources_registry` verifying, the pin loop advances and now fails on
  `FileNotFoundError: integrity pin missing: horizon_frontier_manifest`. Three
  pinned upstream manifests —
  `horizon_frontier_manifest.json`, `network_support_frontier_manifest.json`,
  `route_burden_decomposition_manifest.json` — plus
  `public_data_gate_decisions_manifest.json`,
  `portwatch_sensitivity_input_manifest.json` and
  `portwatch_sensitivity_manifest.json` **are absent from the working tree and
  were never committed on any branch** (`git log --all` returns zero commits for
  each). This is the same class of defect as the 2026-08-28 frontier-artifact
  restoration, and it is **not** pin drift. It is left open deliberately:
  regenerating them means running the freeze write path, and if the output does
  not reproduce `aa981b06…`, `08221460…` and `b3065f96…` exactly, that is a
  second re-pin against G4-verified artifacts, which
  `final_integration_audit.yaml` marks
  `requires_explicit_approval: true`. **Mher's call, not a mechanical fix.**

- **A third failure is also not pin drift.**
  `test_sensitivity_manifest_enforces_non_promotion_guards` fails because
  `_discover_consumers` in `scripts/verify_sensitivity_inputs.py` scans only
  `scripts/**/*.py` and `src/**/*.py` for the literal string
  `portwatch_chokepoints_vintage_20260809_snapshot`. The two consumers added in
  Δ2 and Δ3 reach the vintage through `config/hormuz_measurement_audit.yaml` and
  `config/hormuz_detection.yaml` instead, so the declared-equals-discovered
  invariant now reports a false positive. The declarations are correct; the
  scanner does not read configs. **Open.**
  **— Superseded 2026-08-30.** "The declarations are correct" is wrong. See the
  entry "Consumer-scanner diagnosis corrected" below: `allowed_consumers` is
  defined in this design as *direct registry call sites*, and neither script is
  one. Fixing the scanner alone would not have made this test pass.

- **Affected files:** `config/public_data_gate_decisions.yaml`
  (`integrity_pins.sources_registry`: `sha256` re-pinned, `superseded_sha256` and
  `repinned_local_date` added, provenance comment), `docs/DECISION_LOG.md`.
- **Verification.** Full suite `PYTHONHASHSEED=0 python -m pytest -q` →
  **754 passed, 13 failed, 64 skipped** (105s). All thirteen remain inside the
  same three files; nothing else moved. Within the pin tests the count is
  unchanged at 13 but the composition is not, and the swap was confirmed by
  A/B-ing the stale and re-pinned configs:
  - `test_registry_variable_count_is_pinned_and_unchanged` — **now passes.**
  - `test_integrity_pins_hold` — still fails, but on
    `FileNotFoundError: integrity pin missing: horizon_frontier_manifest`, having
    advanced past `sources_registry`. Different defect, recorded above.
  - `test_upstream_manifest_drift_stops_the_phase` — **newly fails, and this is a
    real defect surfacing, not a regression.** It injects a corrupt
    `route_burden_manifest` hash and expects `ValueError: integrity pin drift`.
    `sources_registry` is first in iteration order, so while the pin was stale it
    raised that exact `ValueError` before the injected corruption was ever
    reached: the test was **passing for the wrong reason** and asserting nothing.
    With the pin correct it fails on the genuine missing-manifest defect, and
    cannot pass until those manifests exist.
- **Status:** **Pin drift SETTLED.** Two independent defects remain open and are
  recorded above: the six never-committed manifests (needs Mher's approval) and
  the config-blind consumer scanner (mechanical, unblocked).

## 2026-08-30 · Six missing manifests: read-only reproduction probe; none can be rebuilt, for four different reasons

- **Decision-maker:** Mher (researcher). Investigation by AI (Claude).
  **Nothing was written.** Every result below comes from calling each freeze
  script's `build_manifest()` in-process and serialising the result the way
  `write_manifest()` would (`json.dumps(m, indent=2, sort_keys=True) + "\n"`,
  utf-8), without touching disk. Confirmed afterwards: none of the six manifests
  exists, and no `data/processed` artifact was created.
- **Why this ran.** The 2026-08-30 re-pin of `sources_registry` cleared the drift
  that was masking these failures. Eleven of the thirteen remaining failures come
  from six frozen manifests that are absent from the working tree and were
  **never committed on any of the seven branches**. The question put was whether
  they can simply be regenerated, as the 2026-08-28 frontier artifacts were.

- **Answer: no. Not one of the six builds today.** The blockers form a chain, and
  only one of them is the "missing artifact, re-run it" case that 2026-08-28 was.

  | Manifest | Blocked by | Kind |
  |---|---|---|
  | `horizon_frontier_manifest` | recompute vs. on-disk CSVs exceeds `atol=1e-12` | **unsatisfiable gate** |
  | `network_support_frontier_manifest` | all six declared outputs absent; upstream inputs present | re-runnable |
  | `route_burden_decomposition_manifest` | needs `network_support_frontier_manifest.json` | cascade |
  | `public_data_gate_decisions_manifest` | its builder calls `verify_integrity_pins` first | cascade |
  | `portwatch_sensitivity_manifest` (prepared) | needs `portwatch_sensitivity_input_manifest.json` | **cascade via a known bug** |
  | `portwatch_sensitivity_manifest` (complete) | all seven `model_vintage_matrix_*` artifacts absent | re-runnable |

- **The horizon manifest is the substantive finding, and it is not a missing
  file.** Every input is present and hash-verifies. `validate_written_outputs`
  compares the CSVs on disk against a live recompute at **`rtol=0.0,
  atol=1e-12`** (`scripts/freeze_horizon_resolution_frontier.py:78-85`). The
  worst disagreement is **7.5602e-12 absolute, 4.1470e-13 relative**
  (`blocks_csv:cumulative_throughput_loss`; worst cell
  `128.02743035488248` on disk against `128.02743035487492` recomputed). Four
  candidate explanations were tested and three were ruled out:
  - **Not run-to-run nondeterminism.** Two rebuilds in one process are
    bit-identical for all three frames.
  - **Not CSV precision loss.** `to_csv` is called with no `float_format`, the
    stored text round-trips exactly (`float(raw) == parsed`), and
    `csv->df->csv->df` is stable. The difference is computed, not stored.
  - **Not a run/freeze code-path mismatch.** `freeze_horizon_resolution_frontier`
    imports `load_verified_inputs`, `build_geometry`, `build_blocks` and
    `build_summary` directly from `run_horizon_resolution_frontier`. Same code.
  - **What remains: the numeric environment.** All four virtualenvs on this
    machine were probed — `.venv` and `.venv-claude` (py3.14, pandas 2.3.3),
    `.venv-timesfm` (py3.11, pandas 2.3.3), `.venv-bench` (py3.11, pandas 2.1.4).
    **None reproduces the CSVs**, and the py3.11 and py3.14 builds disagree with
    each other about which column is worst (7.276e-12 at `summary:interval_lower`
    against 7.560e-12 at `blocks:cumulative_throughput_loss`). The pipeline runs
    through `np.linalg.lstsq` (`src/lngfreight/baselines.py:153`), which is
    LAPACK-backed — Apple Accelerate here. The 2026-08-29 00:17 artifacts were
    computed under a numeric environment this machine no longer offers.

  **The gate, not the data, is what is wrong.** An absolute tolerance of 1e-12
  applied to unnormalised cumulative sums demands bit-exactness from a
  BLAS-dependent pipeline, which is not a property any environment can promise.
  The agreement is 4.1e-13 relative — the two artifacts are the same numbers.
  `rtol=1e-12` (or `atol=1e-11`) passes with margin; `rtol=1e-13` does not.

- **One cascade is a bug, not a missing artifact, and it is already tracked.**
  `verify_sensitivity_inputs.main()` writes
  `portwatch_sensitivity_input_manifest.json` **only after**
  `build_sensitivity_manifest()` returns, and that call raises on the
  declared-versus-discovered consumer check — the config-blind scanner recorded
  as open in the 2026-08-30 re-pin entry. **Fixing that scanner unblocks this
  manifest**, and with it two of the thirteen failures. The two defects are not
  independent.

- **On whether regeneration would reproduce the pinned hashes: it almost
  certainly would not, and this should be assumed rather than discovered.** The
  pins `aa981b06…`, `08221460…` and `b3065f96…` were computed on 2026-08-10. The
  horizon probe establishes that this machine does not reproduce even
  **2026-08-28** artifacts bit-exactly. Any regenerated manifest should therefore
  be expected to differ from a 2026-08-10 pin, which makes adoption a re-pin
  against G4-verified artifacts —
  `open_reproducibility_boundaries.core_run_manifest_staleness`,
  `requires_explicit_approval: true`. **No write was attempted for that reason.**

- **Affected files:** none. `docs/DECISION_LOG.md` only.
- **Status:** **OPEN, awaiting Mher's decision.** The four options put to him are
  (1) relax the horizon reproducibility gate from an absolute to a relative
  tolerance and re-run the chain; (2) regenerate the artifacts under the current
  environment and re-pin, accepting last-digit changes to numbers already cited
  in Chapters 5, 6, 9 and 11; (3) fix the consumer scanner first, which is
  unblocked and clears two failures on its own; (4) leave all six as a declared
  open reproducibility boundary and ship with the failures documented.

## 2026-08-30 · Horizon reproducibility gate relaxed to a relative tolerance; consumer-scanner diagnosis corrected

- **Decision-maker:** Mher (researcher), who chose both options below from the
  findings in the preceding entry. Implementation by AI (Claude).

### Done: the horizon gate now expresses "same numbers", not "same bits"

- **Change.** `scripts/freeze_horizon_resolution_frontier.py:78-85`, the
  `assert_frame_equal` in `validate_written_outputs`, moves from
  **`rtol=0.0, atol=1e-12`** to **`rtol=1e-9, atol=1e-9`**, with the reasoning
  recorded inline at the call site.
- **Why 1e-9.** The observed cross-environment disagreement is 4.15e-13
  relative. 1e-9 sits about three orders of magnitude above that noise floor and
  about three below any change that would mean something. `rtol=1e-12` would
  also have passed, but only with 2.4x margin on a single machine's evidence,
  and cross-environment robustness is the whole point of the change.
  `scripts/freeze_route_burden_decomposition.py:82` already uses a relative
  tolerance (`rtol=1e-12, atol=1e-6`), so this is the house pattern, not a new
  one.
- **Result.** The horizon manifest **now builds**, and
  `audit_expectation_fully_reproduced` is **True** — the substantive check
  passes, which is the claim the artifact actually makes.
- **Not written, deliberately.** The manifest would hash to
  `63228311c567f64d67e731ebcad0844a8fb2044e0f48f55188e13a8c1a5577cb` against the
  pinned `aa981b0696a738ff…`. Adopting it is a re-pin against a G4-verified
  artifact, which was explicitly held back for a separate decision.
- **Same latent defect elsewhere, not touched.**
  `scripts/freeze_network_support_frontier.py:86` and
  `scripts/freeze_portwatch_sensitivity_budget_card.py:56` carry the identical
  `rtol=0.0, atol=1e-12`. The budget-card test currently passes, and the
  network-support freeze cannot run at all yet, so neither was changed on
  speculation. Both should be expected to trip the moment their artifacts are
  regenerated in a different environment.
- **Verification.** `tests/test_horizon_resolution_frontier.py` passes; the three
  gate test files are unchanged at 13 failures, none of them horizon-related.

### Corrected: the consumer scanner is not the whole story, and fixing it alone would not have worked

- **What the previous entry said.** That `_discover_consumers` is config-blind,
  that "the declarations are correct", and that repairing the scanner was a
  mechanical, unblocked fix that would clear two failures. **The second and third
  of those are wrong**, and the earlier entry now carries a pointer here.
- **What `allowed_consumers` actually means in this design.**
  `scripts/verify_sensitivity_inputs.py:134-141` runs a second, stricter loop
  over every declared consumer and raises `sensitivity consumer bypasses the
  registry` unless the file contains **all three** of `registry.get_variable`,
  the literal variable name, and `allow_sensitivity`. The manifest field is named
  `direct_registry_call_sites`. The invariant is therefore not "files that use
  this data" but **"files that make a direct, opted-in registry call for it."**
- **Measured against that definition:**

  | declared consumer | `registry.get_variable` | literal | `allow_sensitivity` | |
  |---|---|---|---|---|
  | `run_hormuz_detection.py` | no | no | no | **raises** |
  | `run_hormuz_measurement_audit.py` | no | no | yes | **raises** |
  | `run_portwatch_vintage_sensitivity.py` | yes | yes | yes | ok |
  | `run_rebound_relapse_profile.py` | yes | yes | yes | ok |
  | `run_revision_and_basin_exploration.py` | yes | yes | yes | ok |
  | `verify_sensitivity_inputs.py` | yes | yes | yes | ok |
  | `src/lngfreight/vintage_matrix.py` | yes | yes | yes | ok |

  The five original consumers satisfy the definition. The two added on 2026-08-27
  and 2026-08-28 satisfy none and one. **Repairing `_discover_consumers` would
  have moved the failure to the next loop, not removed it.**
- **No textual discovery rule fits, either.** Four rules were tested against the
  declared set: literal-only (misses both), plus-any-spec-config (13 false
  positives), minus `settings.yaml` (5), minus `model_vintage_matrix.yaml` (3).
  The irreducible residue is `detector_calibration.py`, `global_forecaster.py`
  and `instrument_shift.py` — helpers that name the hormuz configs but resolve no
  registry variable. Filtering on "resolves the registry" does not rescue it
  either, because `run_hormuz_detection.py` itself does not resolve: it delegates
  to `src/lngfreight/hormuz_stress.py`.
- **So this is a design question, not a bug fix.** The two Track A/B scripts
  reach the vintage through a config-declared `registry_variable` resolved
  elsewhere — a fourth access pattern alongside the existing
  `SENSITIVITY_ENTRYPOINTS`, `DERIVED_SENSITIVITY_CONSUMERS` and
  `FIXITY_ONLY_RAW_REFERENCES` vocabulary, and one the design never named.
  **Nothing was changed.** The three plausible resolutions, for Mher:
  1. Make the two scripts genuine direct call sites, so the existing invariant
     holds unchanged — but this edits analysis code frozen for A4.
  2. Add a declared category (`config_mediated_consumers`) with its own check,
     leaving `allowed_consumers` to mean exactly what it means today.
  3. Withdraw the two entries from `allowed_consumers` and record the
     authorisation elsewhere, since neither is a direct call site.
- **Affected files:** `scripts/freeze_horizon_resolution_frontier.py`,
  `docs/DECISION_LOG.md`.
- **Status:** Horizon gate **SETTLED**. Consumer-scanner semantics **OPEN**,
  awaiting Mher's choice between the three options above. Five manifests remain
  unwritten pending the separate re-pin decision.
  **— Superseded 2026-08-30.** The reading above is itself wrong: it treated the
  two declarations as not being genuine opt-ins. They are, they are enforced at
  runtime, and option 3 would have broken A4. See "Consumer guard taught the
  config-mediated opt-in" below.

## 2026-08-30 · Consumer guard taught the config-mediated opt-in; a second wrong diagnosis corrected

- **Decision-maker:** Mher (researcher), who authorised fixing the consumer
  scanner. Implementation by AI (Claude).

- **Correction, and it runs the other way from the last one.** The preceding
  entry concluded that `allowed_consumers` means *direct registry call sites*,
  that the two Track A/B declarations therefore did not qualify, and that
  withdrawing them was a live option. **That was wrong.** `allowed_consumers` is
  **enforced at runtime**: `src/lngfreight/registry.py:153-158` reads the
  presented consumer string, splits it on `:`, and raises
  `PermissionError: undeclared sensitivity consumer` unless it appears in the
  list. Both scripts do present themselves and do opt in:
  - `src/lngfreight/hormuz_stress.py:67` sets
    `CONSUMER = "scripts/run_hormuz_detection.py"` and calls `get_variable(...,
    query={"consumer": CONSUMER}, allow_sensitivity=state != JULY)` on A4's
    behalf.
  - `config/hormuz_measurement_audit.yaml:60` carries
    `consumer: "scripts/run_hormuz_measurement_audit.py:b1_instrument_revision_audit"`
    and `allow_sensitivity: true`, which
    `scripts/run_hormuz_measurement_audit.py:97` passes straight through.

  **Withdrawing the two entries would have broken A4 and B1 at runtime.** The
  declarations are not merely correct, they are load-bearing.

- **What was actually wrong: both static guards, not one.** The original chip
  blamed `_discover_consumers`. That was closer to right than the last entry, but
  incomplete — proved by handing the scanner a *perfect* answer through a
  monkeypatch, after which the gate still failed at the second guard with
  `sensitivity consumer bypasses the registry: scripts/run_hormuz_detection.py`.
  Both guards assumed a consumer hardcodes the variable name. The newer pattern
  deliberately does not: the name lives in a hash-pinned config, so the code
  **cannot widen its own access**. That is stronger governance than the
  convention the guards encoded, and the guards had not caught up.

- **The fix.** `scripts/verify_sensitivity_inputs.py` now recognises two access
  patterns. A file is a consumer if it names the variable itself, **or** if it
  reads a config carrying `registry_variable: <the vintage>` **and** its own path
  is bound as the consumer string presented to the registry. Both conditions are
  required for the second: reading such a config alone is not consumption
  (`config/settings.yaml` names the vintage and is read almost everywhere), and
  being named somewhere is not either. The binding must attach to a `consumer`
  key or `CONSUMER` constant, since matching a bare quoted path would sweep in
  step lists and docstrings.
- **Rule validated before it was written.** Four candidate rules were tested
  against the declared set: literal-only missed both scripts; any-spec-config
  produced 13 false positives; two narrowings left 5 and 3. The rule adopted
  reproduces the declared set **exactly** — seven in, seven out, no residue.
- **The manifest now distinguishes the two, rather than conflating them.**
  `direct_registry_call_sites` keeps its literal meaning and its original five
  entries; a new `config_mediated_call_sites` carries the two. Merging them would
  have made a governance artifact misdescribe its own contents.
- **The guard came out stronger, not weaker.** Negative-tested: an undeclared
  file naming the variable is still caught, and an undeclared **config-mediated**
  consumer is *now* caught — a case the old scanner could not see at all, because
  it never looked past the literal. Runtime enforcement in `registry.py` is
  untouched.

- **One consequence, not acted on.** With the gate passing,
  `verify_sensitivity_inputs.main()` would now write
  `data/processed/portwatch_sensitivity_input_manifest.json`. It was **not
  written**: it would hash to `f42e3ffb26fa7dfc…` against the
  `3a65a8e1ac080c08…` pinned in the committed
  `data/processed/model_admission_pre_run_checkpoint.json`. The mismatch is
  **not** caused by the field split — reconstructing the manifest with only the
  original five consumers reproduces `3a65a8e1ac080c08…` **bit-exactly**, which
  both confirms the rebuild is faithful and locates the cause squarely in the
  authorised 2026-08-27 and 2026-08-28 consumer additions. (Unlike the horizon
  artifact, this one is byte-reproducible; it carries no floating-point
  exposure.) Writing it therefore needs the same re-pin decision as the other
  five manifests.

- **Affected files:** `scripts/verify_sensitivity_inputs.py`,
  `tests/test_sensitivity_input_gate.py`, `docs/DECISION_LOG.md`.
- **Verification.** Full suite **755 passed, 12 failed, 64 skipped** — down from
  13. `test_sensitivity_manifest_enforces_non_promotion_guards` passes. All 12
  remaining failures are the missing-manifest blocker.
- **Status:** **SETTLED.** The consumer guard is correct for both access
  patterns. Six manifests remain unwritten pending the re-pin decision, which is
  now the only thing standing between this branch and a green suite.
