# Maritime route-distance method

**Status:** Pre-committed before inferred capacity-nautical-mile calculation.  
**Measure:** Modeled shortest navigable sea distance, not observed AIS track length.

## Research logic

The resolved GFW terminal sequence identifies a provisional origin and
destination, but the available data do not contain a continuous vessel track.
Straight-line distance is therefore retained only as a lower-bound diagnostic.
The primary distance is the shortest path through a fixed open maritime graph.

This supports a transparent exposure measure: nominal vessel capacity times a
modeled origin-destination distance. It does not establish cargo quantity,
laden state, the route actually sailed, commercial routing choices, weather
avoidance, congestion, sanctions, or causal rerouting.

## Computational specification

1. Retain only `resolved_liquefaction_to_regasification` sequences.
2. Deduplicate by origin and destination project IDs and coordinates so every
   terminal pair has one invariant distance across pre/post periods.
3. Use `searoute==1.6.0`, its bundled Marnet graph, the NetworkX backend, and
   Dijkstra shortest path. Units are nautical miles.
4. Leave ordinary commercial passages available and exclude only the Northwest
   Passage. This estimates a normal shortest maritime route, not a disruption-
   specific avoidance scenario.
5. Add terminal-to-network great-circle connectors to the graph distance and
   record both connectors separately. They approximate unrepresented local
   navigation and are not observed track segments.
6. Accept a route only when both snaps are at most 30 nm and route distance is
   at least 95% of the great-circle lower bound. Flag ratios above 3.0 for manual
   review rather than silently using them.
7. Preserve all failures and flags in the route matrix. Censored and unresolved
   sequences receive no route distance.

The first engine integration found that the original 30 nm rule accepted 452 of
600 pairs. Of 148 rejected pairs, 147 were repeated endpoint-snap failures tied
to sparse graph coverage rather than routing errors. The 30 nm rule remains the
strict specification. A data-informed 60 nm expanded sensitivity is reported
separately; pairs beyond 60 nm remain excluded. This refinement must not be
described as pre-committed.

The 30 nm snap tolerance accommodates the existing terminal/anchorage spatial
classification and graph resolution; it is not evidence that the terminal
match is correct. Results must later be repeated under the pre-committed 10,
20, and 30 km terminal matching radii.

## Outputs and downstream status

`scripts/build_maritime_route_distances.py` writes one row per unique resolved
terminal pair plus engine version, restrictions, passages, great-circle lower
bound, snap diagnostics, route ratio, status, and error text. It deliberately
does not join vessel capacity or calculate capacity-nautical miles.

The downstream join to the frozen one-row-per-IMO carrier frame is complete.
Pre/post inferred capacity-nautical miles, coverage, voyage composition, and
route sensitivities are reported in
`INFERRED_CAPACITY_NAUTICAL_MILES_RESULTS.md`. Manual review remains a validation
requirement, not an unstarted pipeline phase.

## Source and limitations

The Python package documentation describes `searoute` as a shortest-sea-route
generator and explicitly warns that it is intended for realistic visualization,
not navigation. The underlying Eurostat SeaRoute documentation describes a
frequent-shipping-lane network and nearest-network-node approximation. These
properties make it suitable for a reproducible research proxy, not an
authoritative reconstruction of sailed distance.

- https://pypi.org/project/searoute/ (version, API, Apache-2.0 license, warning)
- https://github.com/eurostat/searoute (network construction and snap-distance rationale)
