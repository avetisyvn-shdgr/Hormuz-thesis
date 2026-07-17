# Current thesis implementation plan

**Status:** Phase 3A implementation complete as of 2026-06-20. As of
2026-07-17, the active implementation path is the accepted no-third-layer plan:
integrate the existing results, add only pre-declared sensitivity checks, and
write thesis-facing drafts from committed artifacts. This document records the
completed branch, the current integration phases, and the remaining non-blocking
Spark option.

## Active implementation decision

The accepted implementation decision is **no third layer before thesis
integration**. The current evidence is strongest as a measurement and mechanism
chain: preserve the PortWatch counterfactual foundation, preserve the open-data
LNG mechanism branch, sensitivity-check the Layer-2 network-rewiring typology,
and then write.

This plan deliberately does not change the operational-onset cutoff
(`2026-02-28`), the estimand family, the raw-data freeze, the reproducibility
manifests, or the claim vocabulary in `NETWORK_REWIRING_EXTENSION.md`. Spark
remains a dormant optional secondary-outcome path, not a blocker.

## Candidate extensions and kill criteria

These extensions are not active work under the no-third-layer plan. They may be
reopened only if the stated admission criteria are met before the relevant
analysis freeze.

| Candidate | Admission / kill criterion | Current status |
|---|---|---|
| GEM capacity | Workbook before analysis freeze + nameplate mapped to >=90% of observed non-Gulf supply + headroom grid, never nameplate-as-available | Gated; do not start under the active plan |
| Baltic freight | >=52 pre / >=12 post weeks of one consistently-defined series, <=10% missing, reproducible extraction, no subjective text coding | Gated; defer until source admissibility is established |
| Persistence / recovery | 6 complete post months for >=4 quantity-basis importers | **NO_GO** under current support |

## Current accepted work plan

No phase begins until the prior phase is confirmed. The human runs the pipeline;
implementation phases end with a stop-and-report block rather than a claim that
new outputs work.

### Phase 1 - Layer-2 sensitivity code

Add pre-declared network-rewiring sensitivity artifacts:

- Leave-one-post-month sensitivity for the pre/post summary and typology.
- Typology-threshold sensitivity over the declared threshold grid.
- Structural tests for column contracts and invariants, not result labels.
- Build scripts registered before report generation in `scripts/run_all.py`.

### Phase 2 - reporting upgrades

After Phase-1 artifacts exist and have been pasted back from a real run:

- Separate the quantity-basis headline table from India's value-basis customs
  evidence.
- Report per-unit typology stability, separating coverage-induced
  non-estimability from admissible substantive label changes.
- Add a side-by-side Layer-1 inference table with equal prominence for the
  interval, bootstrap, placebo, honest-rank, and conformal rows.
- State anomaly evidence with the required caveats and aggregate-comparator
  language.

### Phase 3 - manuscript drafts

After Phase-2 regeneration is confirmed, search for any existing manuscript
directory. If none exists, draft markdown under `docs/thesis_drafts/` only:

- `estimand_ladder.md`
- `construct_renaming.md`
- `population_boundary.md`
- `research_integrity.md`
- `future_work.md`

Every empirical number in those drafts must carry an artifact-path citation.

## Research direction

Keep the completed PortWatch counterfactual as the first-stage measurement of
the Hormuz operational shock. The completed extension shows that accessible
vessel data support a scope-limited LNG terminal-sequence and capacity-distance
measure. The transparent LNG trade-network simulation remains an unused fallback.

The intended chain is:

1. Measure the observed Hormuz throughput disruption (completed foundation).
2. Identify replacement LNG origin-destination patterns where data permit.
3. Estimate additional voyage distance and vessel-time as capacity-nautical
   miles, with uncertainty and explicit inference assumptions.
4. Translate the physical reallocation into importer and basin exposure.
5. Add LNG freight-rate evidence if Spark access becomes available.

The physical mechanism is global replacement-supply reallocation. A rise in
Cape of Good Hope traffic alone is not treated as proof that Qatari LNG rerouted
around Hormuz, because LNG loaded inside the Gulf has no maritime bypass around
the strait.

## Phase 1 - completed foundation

- Free-data acquisition, provenance, cleaning, and aligned daily panel.
- Leakage-safe chronological validation and transparent baselines.
- Counterfactual throughput gaps, temporal/spatial placebos, intervals, and
  synthetic-control corroboration.
- Operational-onset cutoff locked at `2026-02-28`; later event dates are scoring
  sensitivities only. See `EVENT_CHRONOLOGY.md`.

## Phase 2 - vessel-data feasibility gate completed

### Available now

- IMF PortWatch: daily aggregate tanker transit counts and capacity. It has no
  LNG class, vessel identity, terminal, voyage, or laden/ballast field.
- WTO/AXSMarine Hormuz tracker: daily LNG outbound-volume index. It is
  LNG-specific but aggregate and cannot identify vessels or destinations.
- Global Fishing Watch documentation: vessel identity and port-visit events are
  available for all vessel types after account/token registration. Its public
  AIS presence product is gridded presence, not an individual raw track, and it
  does not establish cargo quantity or laden state.

### Testable empirical product

With a GFW token and a benchmark LNG-carrier roster, test whether port-to-port
sequences can support **inferred LNG capacity-nautical miles**:

- Identify vessels by IMO number rather than mutable name/MMSI where possible.
- Infer a likely laden leg only when a vessel departs a recognized liquefaction
  terminal and next visits a recognized regasification terminal.
- Multiply route distance by nominal LNG carrying capacity; do not call this
  observed cargo ton-miles.
- Flag AIS gaps, ambiguous terminal sequences, floating storage, reloads,
  ballast legs, and vessels whose identity cannot be resolved.

### Pre-committed acceptance criteria

- Benchmark sample: at least 30 known LNG carriers.
- GFW identity match rate: at least 80%.
- Port-visit coverage in the test windows: at least 80% of matched vessels.
- Resolved liquefaction-to-regasification endpoints: at least 90% of retained
  candidate voyages.
- Median unexplained AIS gap: no more than 24 hours where track-derived distance
  is attempted.
- At least one full pre-disruption comparison window and the post-disruption
  window must be covered under the same data version.

Passing this gate permits an inferred capacity-mile robustness/mechanism layer.
It does not permit causal claims about actual cargo quantities. Failing the gate
does not invalidate the existing throughput result.

## Phase 3A - empirical branch completed

1. Add GFW identity and port-visit adapters through the source registry. **Done.**
2. Freeze a versioned LNG-vessel roster and LNG-terminal dictionary. **Done.**
3. Reconstruct candidate voyages and publish coverage/exclusion diagnostics. **Done.**
4. Calculate baseline/post capacity-nautical miles and modeled vessel-days.
   **Done.**
5. Validate aggregate departures against the WTO LNG outbound-volume index.
   **Done.**
6. Translate inferred flows into importer and destination-basin exposure.
   **Done.**
7. Treat discrepancies as measurement uncertainty, not values to be forced into
   agreement.

## Phase 3B - retained inactive simulation fallback

Do not start this branch under the active no-third-layer plan. If it is ever
reopened, it remains a constrained LNG trade-network model using public
bilateral flows, liquefaction capacity, regasification capacity, route
distances, and explicit vessel assumptions. Any outputs must be labelled
scenario simulation, not observed rerouting or causal effects.

## Spark remains open through the end

Spark25S and Spark30S remain dormant optional secondary outcomes. Continue the
academic/trial/Bloomberg access request in parallel and follow `SPARK_REENTRY.md`
if access arrives. Do not delete the adapters, registry entries, access report,
or re-entry documentation. Spark is not required for Phases 2-3, but it remains
the preferred downstream freight-rate validation layer until the thesis is
finalized.

## Completed implementation actions

1. Define and test a reproducible maritime route-distance method. **Done.**
2. Join nominal vessel capacity after one-row-per-IMO validation. **Done.**
3. Compare capacity-nautical miles under 10, 20, and 30 km radii. **Done.**
4. Validate aggregate Gulf departures against the WTO LNG index. **Done.**
5. Build importer and destination-basin exposure tables. **Done.**
6. Estimate vessel-days as an explicitly assumption-driven extension. **Done.**

## Remaining action

Complete the accepted Phase-1 through Phase-3 integration path one phase at a
time, stopping for pasted real output where required. Keep pursuing Spark access
in parallel. Formal estimand/title/RQ approval is the separate
thesis-governance decision recorded in `ESTIMAND_PROPOSAL_RECONCILIATION.md`.
