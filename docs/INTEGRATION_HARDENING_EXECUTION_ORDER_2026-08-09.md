# Integration-hardening execution order — 2026-08-09

**Owner:** Mher Avetisyan.  
**Implementation support:** AI assistants, subject to human verification.  
**Status:** Dated refinement of the accepted no-third-layer integration plan;
not a replacement for `CURRENT_PLAN.md` and not authorization to edit the
formal proposal.

## Scope that does not change

- The working title, throughput research question, non-causal estimand family,
  and 2026-02-28 operational-onset cutoff stay fixed.
- The pinned July PortWatch vintage remains the reporting basis. The 2026-08-09
  capture is sensitivity-only and must never silently replace it.
- This work hardens claims, provenance, inference, and reporting. It does not
  add a third confirmatory empirical layer.
- The formal proposal remains untouched until the governance distinction
  between Zhenyu Wang's written acceptance and direct Prof. Li ratification is
  resolved.
- Per guardrail G4 in `AUDIT_REMEDIATION_REGISTER.md`, an assistant-run phase is
  `NEEDS-VERIFY` until Mher runs the stated checks and records the real output.

## Baseline before this refinement

Baseline captured at `2026-08-09T20:23:14Z` on branch
`codex/audit-remediation-through-bug-02`, commit
`dacbdb22b2492ed58d2a561baf402f6d7f491ed8`. The working tree already contained
77 changed paths (63 modified/staged and 14 untracked). These pre-existing
changes are preserved; no broad cleanup, reset, or overwrite is authorized.

## Results already visible before the admission rule is frozen

This disclosure prevents the next model table from being described as ex ante
or preregistered.

- Pinned-July, same-outcome model results were already available for seasonal
  naive (54.80 transits/day), AR(1,7) (52.838), Chronos-2 (50.884), and BSTS
  (49.522). Their four-model range is about 5.28 transits/day. The narrower
  AR/Chronos/BSTS range is about 3.32 and may be supplemental only.
- The August-vintage AR(1,7) same-window result was already available at about
  43.814 transits/day, and the complete August outcome path was visible. During
  the independent review of the earlier unanchored protocol draft, approximate
  August seasonal-naive and BSTS values were also observed in memory. No
  persisted eight-cell matrix or August Chronos artifact existed.
- The conditional route/energy ARX result (about 62.858) and mean-scaled
  synthetic-control transit equivalent were already visible. They must remain
  in the published audit table, with machine-readable exclusion reasons, but
  do not enter the selected same-information comparison range.
- Exploratory inspection had already revealed a temporary post-MoU tanker-count
  rebound followed by relapse. The phase windows are fixed in
  `config/settings.yaml` before the descriptive artifact is generated.

The protocol below is therefore described as **frozen before completion of the
August matrix**, not preregistered.

## Dependency-ordered actions

| Order | Action | Completion gate | Current state |
|---:|---|---|---|
| 0 | Governance and dirty-tree baseline | Preserve the accepted scope, record ownership and known results, touch neither the formal proposal nor unrelated changes | Recorded and computationally verified; scope ownership remains with Mher |
| 1 | Freeze the model-admission protocol | Same outcome, units, training dates, cutoff, scoring dates, and strictly pre-treatment information; publish every included and excluded row with a reason | **DONE:** anchored in `ca925a8`; 14 rows and 43 focused tests verified by Mher |
| 2 | Freeze the August sensitivity input | Explicit hash/provenance scope, sensitivity-only label, registered consumers, and separate optional orchestration that cannot promote it to primary | **DONE locally:** input and 6-artifact manifest verified by Mher; archive deposit remains open |
| 3 | Correct rebound/relapse claims | Reproducible phase table; replace “no rebound” with “temporary partial rebound followed by relapse; no sustained recovery”; keep the separate WTO LNG wording | **DONE:** trusted-endpoint artifacts verified by Mher |
| 4 | Complete the 2-vintage × 4-model matrix | Seasonal naive, AR, Chronos, and BSTS under a common 130-day window; only vintage changes; revisions, environments, seeds, and hashes recorded | **DONE:** Mher reproduced 8 cells; 9/9 matrix and 358/358 full tests; 13-artifact manifest verified |
| 5 | Build the sensitivity-budget reporting card | Report vintage swing and the selected four-specification range as separate axes; never call it a variance decomposition, all-admissible-model range, or general AIS result | **DONE:** Mher reproduced all outputs; 19/19 focused and 377/377 full tests; both optional manifests verified |
| 6 | Build the horizon/resolution frontier | Outcome-independent origin rule, all feasible disjoint origins, finite-sample p-value floors, and unbounded intervals stated explicitly | **DONE:** Mher reproduced K=8, floor 1/9, finite 80%, unbounded 90%/95%; 41/41 focused and 418/418 full tests verified |
| 7 | Build the selective network-support frontier | Overall and Hormuz-specific denominators, radius and balanced-cohort checks; missing modeled edge described as missing observation, not proof of no sailing | **DONE:** Mher reproduced 145→2 Hormuz-crossing against 971→746 all resolved at 30 km; 36/36 focused and 454/454 full tests verified |
| 8 | Freeze route-burden decomposition | Complete-case composition/entry-exit/within-pair components plus radius and censoring sensitivity; descriptive construct labels only | **DONE:** Mher reproduced +67.585M m³-nm/sequence and the 54.9/43.8/1.3 split; non-generalising split and one uninterpretable cell disclosed; 39/39 focused and 493/493 full tests verified |
| 9 | Decide optional public-data gates | ERA5 only after an explicit scope-reopening decision; SAR post-submission and scene-level only; JODI blocked pending rights and adequate reporting lag | **DONE:** Mher reproduced 5 candidates with JODI `NO_GO`, no GO status, 0 downloads and registry unchanged at 53 variables; 26/26 focused and 519/519 full tests verified |
| 10 | Final reproducibility and defence pass | Full pipeline, tests, provenance audit, manifest verification, stale-claim search, artifact citation check, then Mher's G4 verification | **DONE:** Mher reproduced 82 occurrences with 0 asserted, 8 artifact-cited claims, 5 defence answers, and all five optional manifests; 34/34 focused and 553/553 full tests verified |

## Stop rules

1. Complete and verify one numbered phase before starting a dependent phase.
2. A failed hash, date, unit, information-set, or denominator check stops the
   affected phase; it is not repaired by silently changing the comparison.
3. Never average PortWatch vintages. They are different measurement states,
   not exchangeable draws from a latent true series.
4. No result becomes thesis-facing merely because a script ran. It must be
   frozen, reproducible, correctly scoped, and cited to its artifact.
5. Optional extensions cannot displace writing or the throughput spine unless
   Mher explicitly reopens scope.

## Verification-command note

The input gate for an assistant-run phase is
`freeze_reproducibility.py --check`, which verifies the 8 core, 146 vessel, and
1 interim input hashes. Do **not** use `--verify` as a phase gate on this
branch: it compares every regenerated artifact against the committed run
manifest, which is older than the 77 pre-existing changed paths recorded in the
baseline above, so it fails for reasons unrelated to any current phase.
Refreezing that manifest belongs to order 10.

## Execution order complete

All eleven ordered actions (0-10) are `DONE` and G4-verified by Mher. This
document is now a closed record rather than an active work list.

## What remains

**Writing.** Under stop rule 5, optional extensions must not displace it.

Three reproducibility items stay open and are documented in
`FINAL_EVIDENCE_TO_CLAIM_AUDIT.md`. None blocks submission:

1. **August raw-byte replication-archive deposit** — OPEN.
2. **Historical source-payload gaps** — OPEN and disclosed (6 fixity-only
   records predating provenance v2).
3. **Core run-manifest staleness** — OPEN, and the only item needing a decision.
   `--verify` fails because the committed manifest predates the 77 pre-existing
   worktree changes in the baseline above; `--check` passes. Refreezing needs a
   clean `run_all.py` and rewrites a committed manifest across 23+ artifacts, so
   it requires Mher's explicit instruction.

The formal proposal remains unedited pending direct Prof. Li ratification.

## Operational note for re-running the final audit

The task-10 audit reads the live repository and records line numbers in the
documents it scans. Editing any scanned document shifts those numbers and
invalidates the frozen scan by design. Regenerate and re-freeze that phase
**last**, after all other documentation edits.
