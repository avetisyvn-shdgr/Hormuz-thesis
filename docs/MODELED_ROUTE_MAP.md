# Modeled Route-Network Change Map

Run from the evidence-repository root:

```bash
.venv/bin/python scripts/make_route_map.py
```

## Estimand and sample

The figure visualizes the post-minus-pre change in aggregate nominal
capacity-distance by terminal pair. It uses equal 94-day windows
(2025-02-28--2025-06-01 and 2026-02-28--2026-06-01) and the primary mechanism
filter:

- `terminal_match_radius_km == 30`
- `inferred_nominal_m3_nm_expanded` is non-null

This yields 948 pre-period and 726 post-period routed voyages, with 405 and 362
unique terminal pairs, respectively. The union contains 578 terminal pairs.

## Construction

The script aggregates nominal capacity-distance by terminal pair and period,
computes the post-minus-pre change, and recomputes each pair's route geometry
with the configured `searoute==1.6.0` graph. The route-engine settings match the
frozen distance artifact: nautical-mile units, the `northwest` restriction,
NetworkX backend, and Dijkstra routing. The script fails if a recomputed route
distance differs from the persisted value by more than 0.1 nautical mile.

Red lines indicate pair-level decreases and blue lines indicate increases.
Widths scale with the absolute nominal capacity-distance change and are capped
at the 95th percentile for legibility. The four diamonds are a separate,
observed PortWatch layer reporting mean-scaled corridor deviations for Hormuz,
the Cape of Good Hope, Panama, and the Yucatán Channel.

## Interpretation boundary

- The lines are modeled shortest-sea-route geometries, not sailed AIS tracks.
- Terminal-sequence inference and right-censoring propagate into the map.
- Line width represents nominal capacity-distance change, not cargo.
- PortWatch corridor markers do not trace or validate the routed voyages.
- The map introduces no new estimand or causal inference; it visualizes the
  frozen mechanism artifacts.

## Outputs

- `reports/figures/modeled_route_network_change.png`
- `reports/figures/modeled_route_network_change.pdf`
- `data/processed/modeled_route_network_change_pairs.csv`
- `data/processed/modeled_route_network_change_manifest.json`

The Natural Earth 110m land layer is vendored under
`data/raw/natural_earth/`; its public-domain license, retrieval URL, and SHA-256
hash are recorded in `data/raw/provenance.jsonl`.
