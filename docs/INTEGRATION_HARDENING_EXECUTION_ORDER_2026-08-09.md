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
  do not enter the same-information envelope.
- Exploratory inspection had already revealed a temporary post-MoU tanker-count
  rebound followed by relapse. The phase windows are fixed in
  `config/settings.yaml` before the descriptive artifact is generated.

The protocol below is therefore described as **frozen before completion of the
August matrix**, not preregistered.

## Dependency-ordered actions

| Order | Action | Completion gate | Current state |
|---:|---|---|---|
| 0 | Governance and dirty-tree baseline | Preserve the accepted scope, record ownership and known results, touch neither the formal proposal nor unrelated changes | AI recorded; `NEEDS-VERIFY` |
| 1 | Freeze the model-admission protocol | Same outcome, units, training dates, cutoff, scoring dates, and strictly pre-treatment information; publish every included and excluded row with a reason | Corrected ex post lock implemented; Git checkpoint and G4 verification pending |
| 2 | Freeze the August sensitivity input | Explicit hash/provenance scope, sensitivity-only label, registered consumers, and separate optional orchestration that cannot promote it to primary | Separation corrections in progress; archive deposit and G4 verification pending |
| 3 | Correct rebound/relapse claims | Reproducible phase table; replace “no rebound” with “temporary partial rebound followed by relapse; no sustained recovery”; keep the separate WTO LNG wording | Trusted-endpoint correction in progress; `NEEDS-VERIFY` |
| 4 | Complete the 2-vintage × 4-model matrix | Seasonal naive, AR, Chronos, and BSTS under a common 130-day window; only vintage changes; revisions, environments, seeds, and hashes recorded | **Blocked pending phases 1–3 checkpoint and G4 verification** |
| 5 | Build the sensitivity-budget reporting card | Report vintage swing and the selected four-specification range as separate axes; never call it a variance decomposition, all-admissible-model range, or general AIS result | Pending |
| 6 | Build the horizon/resolution frontier | Outcome-independent origin rule, all feasible disjoint origins, finite-sample p-value floors, and unbounded intervals stated explicitly | Pending |
| 7 | Build the selective network-support frontier | Overall and Hormuz-specific denominators, radius and balanced-cohort checks; missing modeled edge described as missing observation, not proof of no sailing | Pending |
| 8 | Freeze route-burden decomposition | Complete-case composition/entry-exit/within-pair components plus radius and censoring sensitivity; descriptive construct labels only | Pending |
| 9 | Decide optional public-data gates | ERA5 only after an explicit scope-reopening decision; SAR post-submission and scene-level only; JODI blocked pending rights and adequate reporting lag | Pending |
| 10 | Final reproducibility and defence pass | Full pipeline, tests, provenance audit, manifest verification, stale-claim search, artifact citation check, then Mher's G4 verification | Pending |

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

## Immediate next action

Finish the separate sensitivity-branch manifest, regenerate the trusted-endpoint
rebound artifact, anchor the corrected protocol/design in a path-scoped Git
checkpoint, and have Mher run the phase 1–3 verification commands. Only then
start the missing August Chronos cell and finalize the matrix.
