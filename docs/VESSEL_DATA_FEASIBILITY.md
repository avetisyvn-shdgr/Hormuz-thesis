# LNG vessel-data feasibility status

**Audit date:** 2026-06-19  
**Machine-readable report:** `data/processed/vessel_data_feasibility.json`  
**Current verdict:** **Global port-sequence feasibility passed, scope limited**

## What was tested

`scripts/run_vessel_data_feasibility.py` inspected the frozen local sources,
credential availability, pre-committed acceptance criteria, and presence/schema
of the four inputs required for a GFW sample. It did not call a credentialed API
or expose secret values.

## Evidence available now

- WTO/AXSMarine LNG outbound-volume index: 534 daily rows from 2025-01-01
  through 2026-06-18. This is LNG-specific but aggregate.
- IMF PortWatch chokepoint file: aggregate transit counts/capacity by vessel
  class. Its tanker class does not isolate LNG carriers.
- A `GFW_API_TOKEN` is configured and authenticated without storing it in any
  output or Git-tracked file.
- The locked benchmark is the complete 31-vessel Q-Flex class. All 31 IMO
  numbers passed checksum and duplicate validation; GFW matched all 31, with 40
  historical GFW vessel IDs retained.
- The equal-length 94-day port-visit samples contain 192 pre-period and 107
  post-period events. IMO coverage is 28/31 (90.3%) pre and 30/31 (96.8%) post,
  above the pre-committed 80% threshold in both periods.
- The September 2025 Global Energy Monitor LNG terminal dataset is frozen
  locally. A conservative spatial crosswalk retains operating facilities only,
  requires country agreement, excludes facilities below 1 mtpa, and records all
  unmatched or ambiguous ports in `data/processed/lng_terminal_matching_audit.csv`.
- Of 46 non-censored Q-Flex export-origin sequences, 46 have a subsequent
  regasification endpoint in the provisional terminal crosswalk. The 100% rate
  passes the 90% endpoint-resolution rule, but post-period support is thin: only
  three complete post-period export-to-import sequences are observed.
- The December 2025 GEM carrier tracker supplies 1,100 carrier records. The
  eligibility rules retain a census of 624 active conventional or icebreaker
  LNG carriers with capacity of at least 125,000 m3. GFW resolves all 624 IMO
  numbers to 922 current or historical vessel IDs.
- The global equal-length samples contain 4,023 pre-period and 3,412 post-period
  visits. Census coverage is 600/624 (96.2%) pre and 560/624 (89.7%) post; 549
  carriers appear in both periods, 62 in one, and 13 in neither.
- The global terminal audit contains 891 observed ports and 460 provisional LNG
  terminal matches under the 30 km rule. Rejected candidates remain in
  `data/processed/global_lng_terminal_matching_audit.csv`.
- Global export-to-import endpoint resolution is 1,717/1,770 (97.0%) among
  non-censored sequences. It remains above the 90% rule at stricter terminal
  radii: 93.4% at 10 km and 96.5% at 20 km. Another 455 export calls are
  right-censored at a sample boundary and are reported separately.
- Spark credentials are absent; Spark remains preserved as a dormant extension.

## Source-capability finding

Global Fishing Watch documents an all-vessel identity dataset and port-visit
events for all vessel types. These could support port-sequence reconstruction
after registration for a personal API token. GFW also documents that its AIS
vessel-presence product is gridded hourly presence and **not an individual raw
vessel track**. The available fields do not establish actual LNG cargo quantity
or authoritative laden/ballast state.

Sources:

- [GFW API documentation](https://globalfishingwatch.org/our-apis/documentation)
- [GFW API registration and access](https://globalfishingwatch.org/our-apis/)
- [GFW ports and voyages](https://globalfishingwatch.org/datasets-and-code-anchorages/)

## Maximum defensible empirical product

The sample passed the thresholds in `config/settings.yaml`; the resulting
defensible measure is **inferred LNG capacity-nautical miles**. A likely laden leg may be
inferred from a liquefaction-terminal departure followed by a regasification-
terminal visit, multiplied by nominal vessel capacity and route distance.

It must not be labelled observed laden cargo ton-miles. Terminal sequencing can
misclassify ballast movements, floating storage, reloads, partial cargoes,
ship-to-ship transfers, and AIS gaps.

## Frozen inputs and outputs

| File | Required minimum fields | Current state |
|---|---|---|
| `data/interim/global_lng_carrier_frame.csv` | eligible carrier census | Complete: 624 IMO numbers |
| `data/raw/gfw/global_vessel_identity.csv` | GFW identity crosswalk | Complete: 922 IDs, 624 IMO numbers |
| `data/raw/gfw/global_port_visits.csv` | equal-window port visits | Complete: 7,435 visits |
| `data/raw/gem/global_lng_terminals.csv` | provisional terminal crosswalk | Complete: 460 ports |
| `data/processed/global_candidate_voyage_endpoints.csv` | export-origin sequences | Complete: 2,225 rows |
| `data/processed/global_voyage_feasibility_summary.json` | coverage and sensitivity results | Complete |

The GFW token belongs in `.env` as `GFW_API_TOKEN`; it must never be committed.

## Decision taken after the sample

- **Passed with limited scope:** registered GFW adapters, voyage reconstruction,
  exclusion/coverage diagnostics, WTO validation, modeled capacity-distance,
  vessel-days, and importer exposure are implemented.
- **Simulation fallback not activated:** it remains documented in
  `CURRENT_PLAN.md` if the empirical branch later fails external validation.
- **Spark path remains open:** continue the optional access path in
  `SPARK_REENTRY.md`.

## Scope of the pass

The global pass establishes that GFW can support identity matching and
port-to-port sequence reconstruction for the eligible carrier census. It does
not establish observed cargo quantity, authoritative laden state, or sailed
track distance. The completed downstream steps use a pre-committed reproducible
maritime route-distance method and construct nominal capacity-nautical miles
with terminal-distance and censoring sensitivities. The interpretation boundary
remains unchanged: modeled route distances must not be described as observed AIS
tracks.
