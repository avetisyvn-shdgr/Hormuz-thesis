# Final evidence-to-claim audit

**Design id:** `final_evidence_to_claim_integration_audit_v1`  
**Design SHA-256:** `f98b0f1a3fc5e0483431b73890ff618a29b797efb81ec97df9fdca6d19be3330`  
**Frozen (UTC):** 2026-08-10T00:07:57Z  
**Verification status:** `NEEDS-VERIFY` until the complete pipeline is run.

This document binds every headline empirical claim to a frozen artifact and its stated limitation, and records the stale-claim scan over thesis-facing prose. It edits no manuscript and does not touch the formal proposal.

## Claim-to-artifact ledger

| Claim | Value | Frozen artifact | Layer | Limitation |
|---|---|---|---|---|
| Finite-sample inference capacity at the primary 130-day block resolution. | 8 disjoint reference blocks; rank p 0.111111 at the 1/9 floor; 80% radius finite, 90% and 95% unbounded | `data/processed/horizon_frontier_summary.csv` | `portwatch_all_tanker` | A rank position among pre-treatment reference blocks. A 5% claim is arithmetically unavailable at this resolution. |
| LNG-specific Hormuz outbound activity from the WTO/AXSMarine index. | nonzero on 2026-06-28 and 2026-07-05, then zero through the available endpoint 2026-07-15 | `data/raw/wto_hormuz/voy_intake_index_lng_export.csv` | `wto_lng_specific` | Aggregate index. It cannot identify vessels or destinations and must stay separate from the PortWatch all-tanker series. |
| Modeled resolved terminal-sequence support, overall and Hormuz-crossing, at 30 km. | all resolved 971 to 746; Hormuz-crossing 145 to 2 | `data/processed/network_support_radius_sensitivity.csv` | `modeled_vessel_branch` | A missing modeled edge is a missing observation, never evidence that no ship sailed. No AIS-dark throughput may be inferred. |
| Optional third-layer public datasets considered and their gate status. | 5 candidates; JODI NO_GO; remainder deferred; no GO status permitted | `data/processed/public_data_gate_decisions.csv` | `governance` | A criteria table. It grants no admission and no third layer is admitted. |
| Post-MoU tanker-count movement across the frozen phase windows. | 10.45/day after the MoU, then 1.56/day after renewed attacks through 2026-08-01 | `data/processed/portwatch_regime_phase_profile.csv` | `portwatch_all_tanker` | Descriptive phase contrasts only. The windows are context scoring, not a treatment date. |
| Complete-case change in modeled distance per nominal vessel-capacity m3 among retained inferred voyages at 30 km. | +67.585 million m3-nm per retained sequence; 54.9 / 43.8 / 1.3 component split | `data/processed/route_burden_decomposition.csv` | `modeled_vessel_branch` | Compositional and support-conditional. The split does not generalise across radius or cohort, and the sign is not universal. |
| Counterfactual throughput shortfall over the 130-day treated window under the locked AR(1,7) specification. | 52.838 lost transits/day (6868.996 cumulative) | `data/processed/model_vintage_matrix_summary.csv` | `portwatch_all_tanker` | A forecast shortfall, not a treatment effect. PortWatch counts all tankers and has no LNG class. |
| Same-model shortfall difference between the pinned July and August PortWatch vintages. | 9.025 transits/day for AR(1,7) | `data/processed/portwatch_sensitivity_budget_card.csv` | `portwatch_all_tanker` | A case-local measurement-state sensitivity. Not a variance decomposition and vintages are never averaged. |

All 8 claims cite an artifact that exists on disk, and each artifact's SHA-256 is recorded in `final_claim_artifact_ledger.csv`.

## Layer separation

PortWatch counts **all tankers** and carries no LNG class. The WTO/AXSMarine index is **LNG-specific** but aggregate. They are reported as separate layers and never merged into a single figure.

| Layer | Claims | What it can support |
|---|---:|---|
| `governance` | 1 | Scope and admission decisions. No empirical content. |
| `modeled_vessel_branch` | 2 | Modeled sequence support and composition. Never observed cargo. |
| `portwatch_all_tanker` | 4 | All-tanker transit counts. Never an LNG-specific quantity. |
| `wto_lng_specific` | 1 | LNG-specific outbound activity. Never vessel or destination identification. |

The scan found 0 unhedged line(s) attributing an LNG-specific reading to a PortWatch figure.

## Stale-claim scan

Scanned 9 thesis-facing documents for 19 retired phrases, finding 20 occurrences.

Occurrences are classified by context. A retired phrase appearing inside a negation, a quotation, a prohibition list, or a correction notice is **cleared** -- those are the places such phrases are supposed to appear. Only an asserted occurrence is **flagged**.

| Category | Cleared | Flagged |
|---|---:|---:|
| `ais_dark` | 2 | 0 |
| `causal_language` | 10 | 0 |
| `physical_rerouting` | 6 | 0 |
| `sensitivity_framing` | 2 | 0 |

**No asserted stale claim was found.** Every occurrence sits in a negating, quoting, prohibiting, or correcting context.

### Deliberately excluded from the assertion check

These documents record retired claims as their function, so scanning them for assertion yields only noise. The exclusion is explicit:

- `reports/audit/final_evidence_to_claim_audit.md`
- `reports/audit/defence_preparation.md`

## Open reproducibility boundaries

These are reported rather than hidden. None blocks submission, and one requires explicit approval before it can be closed.

| Boundary | Status | Description |
|---|---|---|
| `august_raw_byte_archive` | `OPEN` | The August PortWatch source bytes are gitignored and not yet deposited in a replication archive. The derived sensitivity artifacts are frozen and hashed, but a third party cannot re-derive them from source without the deposit. |
| `historical_source_payload_gaps` | `OPEN_AND_DISCLOSED` | The provenance audit passes with disclosed historical source gaps: 6 fixity-only metadata records lack a stored source payload. These predate the provenance v2 schema and are reported rather than back-filled. |
| `core_run_manifest_refresh` | `CONTROLLED_BY_RUN_ALL` | The complete pipeline refreshes the reproducibility manifest only after regenerating all declared artifacts, then runs the test suite and verifies the manifest again. The earlier stale-manifest condition is therefore an explicit pipeline stage rather than an unresolved exception. |

## Regeneration order

This scan reads the live repository and records line numbers in the scanned documents. Editing any scanned document shifts those numbers and correctly invalidates the frozen scan. **Regenerate this phase last**, after every other documentation edit, then re-freeze.

## Governance boundaries preserved

- The **formal proposal is unedited**. Direct Prof. Li authorization is not on record, and Zhenyu Wang's 2026-07-23 written acceptance does not substitute for it.
- **No restricted material** appears in any thesis-facing artifact. JODI is `NO_GO` on already-triggered criteria; the Fearnleys series remain dormant registry entries with no data.
- **No third empirical layer** is admitted. The public-data gate table records criteria only and grants no admission.
- The locked specification, the 2026-02-28 operational-onset cutoff, and the pinned July reporting vintage are unchanged.

