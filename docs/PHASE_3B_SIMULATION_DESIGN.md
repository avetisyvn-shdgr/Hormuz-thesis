# Phase 3B — constrained LNG trade-network simulation (fallback-of-the-fallback)

**Status:** Design, 2026-06-20. Not yet built. Phase 3A (the GFW inferred
capacity-nautical-miles branch) **passed** its feasibility gate
(`VESSEL_DATA_FEASIBILITY.md`), so 3B is not currently triggered. This document
designs it to the same rigor the original proposal's cascade got, so that if the
3A empirical product proves too thin to carry a mechanism layer, a transparent
simulation is ready rather than improvised.

## When 3B triggers (pre-committed)

3A is retained as the empirical mechanism layer **unless** any of these hold on
the frozen GFW sample, in which case the inferred capacity-mile product is judged
too thin and 3B replaces the *mechanism* layer (never the PortWatch primary):

- Fewer than **8** complete post-period export→import LNG sequences after terminal
  resolution (currently only **3** for the Q-Flex benchmark; 1,770 global non-
  censored sequences but with thin post-period support — this is the live risk).
- Post-period census coverage below the pre-committed **80%** for matched carriers.
- Endpoint resolution below **90%** at the 20 km terminal radius.
- Median unexplained AIS gap exceeding **24 h** where track-derived distance is
  attempted.

Triggering 3B is a documented methodological decision, logged like the PortWatch
substitution, not a silent swap (CLAUDE.md rule 8).

## What 3B is

A **constrained reallocation simulation** of LNG flows under partial/complete
removal of Hormuz-dependent exports. It is **scenario simulation, not observed
rerouting and not causal inference** — outputs are labelled as such throughout. It
answers: *given public capacities, demand, and explicit vessel assumptions, how
many additional vessel-days and capacity-nautical-miles would replacing Hormuz-
dependent LNG require, and which importers/basins absorb the exposure?*

## Methodological justification

The proposal's mechanism is the **ton-mile multiplier / fleet-vacuum**: when Gulf
LNG is removed, importers must be served from more distant origins, multiplying
transport work per unit delivered and tightening effective fleet capacity. When
AIS cannot *measure* the realised reallocation with enough post-period support, a
physically constrained simulation can still quantify the *mechanism's logical
magnitude* under stated assumptions — exactly the role the proposal reserved for a
"transparent, assumption-explicit" model. It complements, and is triangulated
against, the PortWatch throughput collapse and the WTO LNG-index direction.

## Data requirements (all free / already frozen where noted)

| Input | Source | State |
|---|---|---|
| Liquefaction capacity by terminal/country | GEM GGIT LNG terminals (2025-09) | **frozen** `data/raw/gem/` |
| Regasification capacity by terminal/country | GEM GGIT LNG terminals | **frozen** |
| Bilateral LNG trade (origin→destination, baseline) | GIIGNL annual / UN Comtrade (HS 271111) / EIA | to acquire via registry |
| Maritime route distances (incl. Hormuz vs Cape/Suez detours) | `searoute` method already built | **frozen** method |
| Eligible LNG carrier census + nominal capacities | GEM carrier tracker (2025-12), 624 carriers | **frozen** |
| Vessel assumptions (laden/ballast speed, port turnaround, boil-off) | published vessel specs; explicit ledger | to specify |

All external pulls go through `registry.get_variable()` with provenance logging.

## The model

A baseline **transportation/assignment** of supply origins to demand sinks that
reproduces observed pre-disruption bilateral flows, then re-solved under shock
scenarios:

1. **Sets.** Export origins `o` (liquefaction terminals/basins), import sinks `i`
   (regas terminals/basins), the carrier fleet with nominal capacities.
2. **Baseline calibration.** Fit the origin→sink assignment to observed pre-shock
   bilateral flows (GIIGNL/Comtrade) subject to liquefaction and regas capacity
   limits and route distances. **Pre-shock fit error is the credibility metric**,
   mirroring the synthetic-control pre-RMSPE discipline — a simulation that cannot
   reproduce the observed baseline is not trusted to extrapolate the shock.
3. **Shock scenarios.** Remove a fraction `φ ∈ {0, 0.5, 1.0}` of Hormuz-dependent
   (Qatar + UAE) export capacity and re-solve, reallocating displaced demand to
   the next-cheapest feasible origins under the same constraints.
4. **Outputs per scenario.** Additional **vessel-days** and **capacity-nautical-
   miles** (Δ distance × nominal capacity × voyages), **unmet demand** where no
   feasible reallocation exists, and **importer/destination-basin exposure** —
   the same exposure schema as the 3A branch so the two are directly comparable.

The objective is least-cost (distance- or vessel-time-weighted) assignment; a
linear program suffices and keeps the model transparent and inspectable, as the
proposal demands of the ML layer.

## Falsification / robustness (the cascade discipline)

Matching the original design, each check eliminates a specific rival explanation
rather than re-estimating the headline:

1. **Baseline-fit gate.** Report pre-shock assignment error vs observed bilateral
   flows; if the baseline is not reproduced, the scenario outputs are not reported
   as quantitative.
2. **Assumption sensitivity ledger.** Sweep vessel speed (±15%), port turnaround,
   boil-off, and the Hormuz-removal fraction `φ`; report output ranges, not points.
3. **Demand-response sensitivity.** Compare fixed-demand vs partial demand
   destruction (price-rationed) reallocation — the upper/lower envelope on
   additional vessel-days.
4. **Cross-method triangulation.** Check the simulated additional-vessel-day
   *direction and order of magnitude* against (a) the PortWatch throughput
   collapse and (b) the WTO LNG outbound-index decline. Agreement in direction is
   corroboration; disagreement is reported as measurement/scenario uncertainty,
   **not forced into agreement** (CURRENT_PLAN.md Phase-3A rule 6).
5. **Placebo origin.** Re-run the removal on a non-Hormuz origin of similar scale
   to confirm the additional-vessel-day signal is specific to the Gulf removal.

## Estimand and reporting language

- Estimand: scenario-conditional **additional vessel-days, capacity-nautical-
  miles, unmet demand, and importer/basin exposure** under stated Hormuz-removal
  fractions.
- Reporting term: **"simulated reallocation under explicit assumptions."** Never
  "observed rerouting," "ATT," or "ton-mile causal effect." It does not establish
  actual cargo quantity or laden state.

## Limitations to state plainly

- A constrained optimisation is a *normative* reallocation; real markets reroute
  with frictions, contracts, and storage the model omits — so it bounds the
  *mechanism's scale*, it does not predict realised flows.
- Public bilateral flows are annual/coarse; sub-annual reallocation is inferred,
  not observed.
- Capacities are nameplate; utilisation and maintenance are not modelled.
- It shares the PortWatch limitation that "tanker" ≠ "LNG carrier" only where it
  cross-checks throughput; the simulation itself is LNG-specific by construction.

## Relationship to the rest of the design

3B is the **mechanism-layer fallback** if 3A is too thin. It never displaces the
PortWatch counterfactual primary, and Spark/Bloomberg freight remains the
preferred downstream validation if access arrives (`SPARK_REENTRY.md`). The
PortWatch throughput result stands regardless of whether the mechanism layer is
3A (measured) or 3B (simulated).
