# DRAFT - Construct renaming ledger

This draft is a manuscript find-and-replace ledger. It does not perform the
replacement automatically, because several old terms are still load-bearing in
historical design notes, proposal-reconciliation files, and negative-result
documentation.

## Replacement ledger

| Old construct | Replacement | Integration caveat |
|---|---|---|
| `ton-mile multiplier` | `nominal capacity-distance per routed LNG voyage` | Use only for the GFW terminal-sequence mechanism branch. Add the compositional shift-share caveat whenever interpreting the per-voyage increase: route composition, not necessarily elongation, drives the retained-voyage pattern (`reports/transmission_chain_summary.md`). |
| `adaptation cost` | `conditional distance burden` | Use when discussing modeled distance or vessel-time burdens, and pair it with the scenario label. Do not imply welfare cost, freight-rate incidence, or observed cargo replacement. |
| `LNG freight markets` framing | `Hormuz tanker throughput and LNG shipping-network adaptation` | Use for the thesis frame unless Spark freight access is actually admitted later. The current generated run report states the working estimand as disruption-associated counterfactual shortfall, not freight-rate effect (`reports/run_output.md`). |

## Files still using old terms

The following doc/report files still contain at least one of `ton-mile`,
`ton-mile multiplier`, `adaptation cost`, or `LNG freight markets` in a grep over
`docs/` and `reports/`. Mher should decide whether each use is historical,
negative-result context, or live thesis branding before replacing it.

- `docs/AFFECTED_IMPORTER_FINDINGS.md`
- `docs/BACKUP_DATA_PATHWAY.md`
- `docs/CAPTIVITY_EVENT_STUDY_DESIGN.md`
- `docs/COLLABORATION_TASK_MAP.md`
- `docs/CORRIDOR_TRANSMISSION_RESULTS.md`
- `docs/CURRENT_PLAN.md`
- `docs/DATA_ACCESS_CHECKLIST.md`
- `docs/DATA_SOURCES.md`
- `docs/DECISION_LOG.md`
- `docs/ESTIMAND_PROPOSAL_RECONCILIATION.md`
- `docs/FALLBACK_STRATEGY.md`
- `docs/GAP_VALIDATION.md`
- `docs/GULF_DEPARTURE_WTO_VALIDATION_RESULTS.md`
- `docs/INFERRED_CAPACITY_NAUTICAL_MILES_METHOD.md`
- `docs/INFERRED_CAPACITY_NAUTICAL_MILES_RESULTS.md`
- `docs/MODERN_TSFM_BENCHMARK.md`
- `docs/NETWORK_REWIRING_EXTENSION.md`
- `docs/PENDING_ESTIMAND_REALIGNMENT_DRAFT.md`
- `docs/PHASE_3B_SIMULATION_DESIGN.md`
- `docs/PROJECT_POSTMORTEM_2026-06-21.md`
- `docs/PROPOSAL_CITATION_AUDIT.md`
- `docs/SUPERVISOR_DECISION_MEMO.md`
- `docs/SUPERVISOR_SCOPE_MEMO_OPTION_D.md`
- `docs/VALIDATION_REPORT_2026-07-15.md`
- `docs/VESSEL_DATA_FEASIBILITY.md`
- `docs/pipeline_health_graph.html`
- `docs/pipeline_health_graph.mermaid`
- `reports/transmission_chain_summary.md`

## Suggested manuscript rule

Use the replacement terms in live chapter prose. Keep old terms only when
explaining the proposal history, proprietary-data fallback, or negative result
that the free-data implementation does not support an aggregate ton-mile
multiplier (`reports/transmission_chain_summary.md`).
