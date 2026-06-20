# Inferred capacity-nautical miles

**Status:** Empirical mechanism proxy, not observed cargo ton-miles.  
**Unit:** Nominal LNG vessel capacity in cubic metres multiplied by modeled
terminal-to-terminal nautical miles (`m3-nm`).

## Methodological justification

For a provisional liquefaction-to-regasification sequence, nominal carrier
capacity approximates the vessel space committed over the modeled route. This
is closer to the fleet-utilization mechanism than voyage counts alone, while
remaining feasible with open data. It does not measure actual LNG volume,
utilization, cargo mass, or freight price.

## Construction

1. Reconstruct voyages independently under 10, 20, and 30 km terminal-match
   radii. Preserve unresolved and right-censored export calls.
2. Require exactly one positive nominal capacity per IMO in the frozen carrier
   frame. A duplicate IMO fails the build rather than duplicating voyage rows.
3. Route the union of resolved terminal pairs using the frozen maritime method.
4. Calculate `capacity_m3 * modeled_terminal_to_terminal_nm` only where the
   endpoint resolves, capacity exists, and route QA passes.
5. Report the original 30 nm endpoint-snap rule as strict and the data-informed
   60 nm rule as an expanded sensitivity. Never fill excluded distances.
6. Summarize equal-window pre and post totals separately for every terminal
   radius and route specification.

## Interpretation limits

Pre/post changes are descriptive. They jointly reflect voyage frequency,
vessel capacity, origin/destination composition, GFW coverage, terminal matching,
and modeled route length. They do not identify a causal Hormuz effect. A likely
laden leg remains an inference from terminal order; partial loading, reloads,
floating storage, ship-to-ship transfers, and AIS gaps remain unobserved.

The immediate validation after construction is to compare Gulf-origin departure
patterns with the aggregate WTO/AXSMarine LNG outbound index. Disagreement is a
measurement diagnostic and must not be calibrated away.
