# Network rewiring extension

**Status:** Active staged extension. The origin-edge table, pre/post summary,
and dynamic graph metrics are now built as reproducible artifacts. This
extension does not change the locked PortWatch working primary, the treatment
cutoff, the importer-panel NO_GO decision, or the rule that prediction is not
identification.

## Purpose

The current pipeline answers the first-stage question: **what happened?** It
documents a severe Hormuz tanker-throughput collapse, validates the LNG-specific
direction with the WTO/AXSMarine index, and shows descriptive importer and vessel
mechanism evidence.

The next valuable question is: **how did the LNG trade network adapt?**

This extension formalizes the "Invisible Shock" and "Ton-Mile Tax" ideas as a
network-rewiring problem. The goal is to measure whether aggregate import
stability, where observed, was achieved by changing the origin mix, increasing
source distance, concentrating replacement supply, and consuming more vessel
time. The extension is designed as mechanism and resilience analysis, not as a
new causal ATT estimator.

## Research questions

1. **Network rewiring:** How far did importer origin portfolios move away from
   their pre-disruption structure after `2026-02-28`?
2. **Substitution burden:** Which importers or destination basins carried the
   largest increase in non-Gulf sourcing, source distance, vessel-days, or
   capacity-distance?
3. **Adaptation cost:** What is the minimum additional distance or vessel-time
   required to replace lost Hormuz-dependent LNG under transparent capacity and
   route constraints?
4. **Resilience typology:** Which importers were high-exposure but resilient,
   high-exposure and constrained, low-exposure and stable, or not estimable?

## Methodological justification

The existing result is strongest when framed as a **measurement and mechanism
chain**:

1. PortWatch and WTO measure the physical disruption.
2. Customs outcomes show origin-composition changes where by-origin data exist.
3. GFW terminal sequences show longer retained LNG voyages and higher
   capacity-distance per voyage.

What is missing is a formal object connecting these layers: a changing LNG trade
network. Network analysis and constrained reallocation are appropriate because
the mechanism is not a point outcome alone; it is a system response. The shock
removes or suppresses a set of edges from Hormuz-dependent exporters, and the
network adapts through alternative edges with different distances, capacities,
and frictions.

The extension should therefore estimate **adaptation cost** rather than causal
effect. It should report edge reweighting, replacement burden, and scenario
bounds under explicit assumptions.

## Claim boundaries

Allowed language:

- "Network rewiring"
- "Descriptive replacement burden"
- "Observed origin-composition change"
- "Inferred capacity-distance among retained terminal sequences"
- "Scenario-conditional minimum reallocation cost"
- "Mechanism-consistent evidence"

Disallowed language:

- "ATT"
- "Causal substitution coefficient"
- "Observed cargo ton-miles"
- "Observed freight-rate effect"
- "Exact welfare loss"
- "Proof that a specific non-Gulf cargo replaced a specific Gulf cargo"

Prediction models may help score anomalies or stress scenarios, but a more
accurate forecaster still does not identify a causal effect.

## Data inputs

### Already available

| Input | Current artifact | Role |
|---|---|---|
| Daily Hormuz throughput | `data/processed/panel_aligned.csv` | Stage-1 shock measurement |
| WTO LNG outbound index | `data/raw/wto_hormuz/` and validation outputs | LNG-specific direction check |
| By-origin importer outcomes | `data/processed/importer_outcomes.csv` | Monthly origin-composition evidence |
| GFW inferred LNG voyages | `data/processed/inferred_capacity_nautical_miles_voyages.csv` | Terminal-sequence mechanism layer |
| Route distances | `data/processed/maritime_route_distances.csv` | Distance/cost weights |
| Basin exposure | `data/processed/basin_exposure_summary.csv` | Destination-basin aggregation |
| Vessel-day estimates | `data/processed/vessel_day_comparison.csv` | Vessel-time burden |

### Optional additional inputs

| Input | Potential source | Admission condition |
|---|---|---|
| Public freight-rate indicator | Baltic Exchange public gas weekly reports; Fearnleys only if stable and archiveable | Source URL, capture date, terms, and SHA-256 snapshot recorded |
| Additional monthly importer totals | JODI-Gas or national sources | Aggregate-stability appendix only; not origin-split confirmatory panel |
| Additional origin splits | National customs sources | Must preserve source-native country names and by-origin monthly data |

All external additions must go through the registry/provenance pattern. No ad-hoc
analysis downloads.

## Core outputs

### 1. Monthly origin-portfolio metrics

Build a long monthly table:

`data/processed/lng_rewiring_importer_monthly.csv`

Candidate columns:

- `unit`
- `month`
- `total_volume`
- `gulf_volume`
- `non_gulf_volume`
- `gulf_share`
- `non_gulf_share`
- `source_count`
- `source_hhi`
- `source_entropy`
- `mean_source_distance_nm`
- `atlantic_share`
- `pacific_share`
- `snapshot_sha256`
- `basis` (`tonnes`, `kg`, `MIO_M3`, `kUSD`)
- `admissibility_note`

Important: India remains value-basis (`kUSD`) unless a usable quantity series is
found. Its shares may be reported, but they embed origin price differentials.

Implemented artifacts:

- `data/processed/lng_rewiring_network.csv`
- `data/processed/lng_rewiring_monthly_metrics.csv`

### 2. Pre/post network rewiring summary

Build:

`data/processed/lng_rewiring_summary.csv`

Compare the 12-month pre window (`2025-03` through `2026-02`) with available
post months (`2026-03` onward). Report:

- Gulf-share change
- Total-volume change
- Non-Gulf-volume change
- Supplier-concentration change
- Source-entropy change
- Mean source-distance change where distances are available
- Number of post months available
- Whether the unit is importer, aggregate comparator, or value-basis

Do not force all units into a balanced panel if source publication lags differ.
Use coverage columns rather than fabricating missing months.

Implemented artifact:

- `data/processed/lng_rewiring_summary.csv`

### 3. Dynamic network graph

Represent the LNG trade system as a weighted directed graph:

- Nodes: exporters, importers, or basins.
- Edges: monthly origin-to-destination LNG flows.
- Weights: volume/value, Gulf/non-Gulf label, and optional route-distance weight.

Candidate metrics:

- Edge turnover rate.
- Jensen-Shannon divergence between pre and post origin shares.
- Importer source entropy.
- Supplier concentration (`HHI`).
- Weighted average source distance.
- Share of lost Gulf exposure offset by non-Gulf growth.

This turns "Invisible Shock" into a measurable claim: aggregate totals may be
stable while edge composition changes sharply.

Implemented artifact:

- `data/processed/lng_rewiring_graph_metrics.csv`
- `data/processed/lng_network_anomaly_monthly.csv`
- `data/processed/lng_network_anomaly_summary.csv`

Current anomaly scope:

- Monthly origin-share vectors are scored against each unit's pre-shock
  portfolio centroid using Jensen-Shannon distance. Pre-period calibration uses
  leave-one-month-out centroids to avoid scoring a month against a centroid that
  was fit using that same month.
- Z-scores and empirical pre-period percentiles are exploratory mechanism
  diagnostics only. They are not part of the primary causal inference family.

### 4. Constrained reallocation / optimal transport model

Build a transparent transportation model:

- Demand nodes: importers or destination basins.
- Supply nodes: liquefaction origins or origin basins.
- Cost: nautical miles or modeled vessel-days.
- Constraints: pre-shock demand, available non-Hormuz supply, liquefaction
  capacity where available, regas capacity where available.
- Shock: partial or complete removal of Qatar/UAE Hormuz-dependent supply.

Outputs:

- Minimum additional nautical miles.
- Minimum additional vessel-days.
- Unmet demand if constraints bind.
- Shadow-price style indicators of constrained importers/origins, if the solver
  exposes them.
- Sensitivity over removal fraction, speed, turnaround time, and demand
  destruction.

Reporting term: **scenario-conditional minimum reallocation cost**. This is a
stress-test model, not observed rerouting.

Implemented artifacts:

- `data/processed/lng_reallocation_basin_demands.csv`
- `data/processed/lng_reallocation_supply_nodes.csv`
- `data/processed/lng_reallocation_cost_matrix.csv`
- `data/processed/lng_reallocation_solution.csv`
- `data/processed/lng_reallocation_summary.csv`

Current implementation scope:

- Demand nodes are destination basins with lost observed Hormuz-exposed LNG
  vessel capacity.
- Supply nodes are observed non-Gulf source terminals under two scenarios:
  `incremental_non_gulf_growth_only` and `post_non_gulf_pool`.
- Costs are audited expanded maritime route distances from source terminal to
  the cheapest observed terminal in each destination basin.
- The `post_non_gulf_pool` scenario is intentionally a lower-bound stress test:
  it allows the model to choose the shortest observed non-Gulf routes and should
  not be read as observed cargo replacement or global liquefaction capacity.

### 5. Resilience typology

Classify units into descriptive categories:

- **High exposure, high offset:** large pre Gulf share, non-Gulf growth absorbs
  much of the lost Gulf volume.
- **High exposure, constrained:** large pre Gulf share, total volume falls or
  non-Gulf offset is weak.
- **Low exposure, stable:** small pre Gulf share, limited composition change.
- **Aggregate comparator:** EU27-style aggregate, useful context but not a
  single importer.
- **Value-basis caution:** India unless quantity-basis data are added.
- **Not estimable:** insufficient post support or missing origin split.

ML may be used for clustering only if the feature table has enough units.
Otherwise the typology should be rule-based and transparent.

Implemented artifact:

- `data/processed/lng_resilience_typology.csv`

Current implementation scope:

- Rule-based thresholds classify importer-style units into high-offset,
  constrained, stable/intermediate, or non-estimable categories.
- EU27 is retained as an aggregate comparator, not an importer.
- India receives a value-basis caution because its strict origin split is
  currently `kUSD`, not physical quantity.

## Role of modern ML

Modern ML belongs in this extension only if it answers a new question.

### Useful

1. **Graph anomaly detection:** quantify how unusual the post-shock network is
   relative to pre-shock monthly network variation.
2. **Representation learning:** embed importer origin portfolios and measure
   pre/post movement in feature space. Use PCA/UMAP only as visualization unless
   sample size supports stronger claims.
3. **Probabilistic scenario ensembles:** run the reallocation model under sampled
   assumptions for speeds, capacities, and demand elasticity; report intervals
   over scenario outputs.
4. **Foundation-model anomaly scoring:** use Chronos-2/TimesFM/Moirai only as
   optional benchmarks for expected aggregate totals or route metrics, never as
   identification evidence.
5. **Explainable tree models:** if enough units are available, model resilience
   scores from pre-shock features and report feature importance as exploratory.

### Not useful enough

1. Another time-series forecaster for the locked daily panel. The project already
   has AR, ARX, BSTS, Chronos-2, TimesFM, Moirai, placebos, and synthetic
   control.
2. A hierarchical multi-chokepoint causal model. It inherits donor contamination
   and adds sophistication without new identification.
3. Black-box network forecasts without source interpretability. The thesis value
   is in transparent mechanism reconstruction.

## Validation and falsification

1. **Coverage gate:** every metric table must report post-month count and source
   basis. No hidden balanced-panel assumption.
2. **Oman exclusion check:** Gulf exporter mapping must continue to exclude Oman.
3. **Mass-balance sanity:** for each unit/month, `gulf + non_gulf = total` within
   tolerance where all three are built from the same source.
4. **Distance sanity:** route-distance joins must flag missing or ambiguous
   origin/destination mappings.
5. **Stress-test scope check:** the constrained model must report whether route
   costs are observed/accepted, whether supply is unroutable, and whether the
   scenario is a loose lower-bound route pool. It does not yet reproduce
   pre-shock observed flows as a calibrated network-flow baseline.
6. **Sensitivity ledger:** report ranges over removal fraction, vessel speed,
   turnaround, and demand destruction.
7. **No causal promotion:** any ML anomaly score or optimisation output is
   descriptive or scenario-conditional unless the formal estimand is changed and
   approved.

## Implementation phases

### Phase R1 - design lock

Deliverables:

- This memo.
- A source-admission table for each candidate data input.
- A feature dictionary for all rewiring metrics.

Decision gate:

- Proceed only with already frozen sources unless a new source has clear capture
  and license documentation.

### Phase R2 - descriptive rewiring metrics

Deliverables:

- `src/lngfreight/network_rewiring.py`
- `scripts/build_network_rewiring_metrics.py`
- `data/processed/lng_rewiring_importer_monthly.csv`
- `data/processed/lng_rewiring_summary.csv`
- Tests for mass balance, post-month coverage, Oman exclusion, and India
  value-basis flags.

This is the first implementation target.

### Phase R3 - figures and narrative

Deliverables:

- Pre/post origin-composition figure.
- Gulf-share collapse versus total-volume stability figure.
- Supplier-concentration or source-entropy figure.
- `reports/network_rewiring_summary.md`

Implemented artifacts:

- `reports/figures/network_rewiring_origin_composition.png`
- `reports/figures/network_rewiring_gulf_vs_total.png`
- `reports/figures/network_rewiring_source_structure.png`
- `reports/network_rewiring_summary.md`

Interpretation:

- This stage supports the "Invisible Shock" claim if composition changes are
  large while total volume is partly buffered.

### Phase R4 - constrained reallocation model

Deliverables:

- `src/lngfreight/reallocation.py`
- `scripts/run_reallocation_stress.py`
- Scenario output tables for additional distance, vessel-days, and unmet demand.
- Sensitivity summary.

Interpretation:

- This stage supports the "Ton-Mile Tax" as an adaptation-cost stress test.

### Phase R5 - optional ML / anomaly layer

Deliverables only if sample size and feature coverage justify them:

- Graph-distance anomaly score.
- Importer typology/clustering.
- Foundation-model aggregate-volume benchmark.

Implemented:

- Graph-distance anomaly scores are implemented as an exploratory diagnostic in
  `data/processed/lng_network_anomaly_summary.csv`.
- Importer typology is implemented as a rule-based table, not clustering, in
  `data/processed/lng_resilience_typology.csv`.

Interpretation:

- Exploratory mechanism diagnostics only. Do not add them to the primary
  inference family.

## Expected thesis contribution

If completed, this extension would move the thesis from:

> Hormuz throughput collapsed, and multiple robustness layers confirm the shock.

to:

> Hormuz throughput collapsed, and the LNG system adapted through measurable
> network rewiring: Gulf-origin edges disappeared, replacement edges expanded,
> source portfolios changed, and the system paid an adaptation cost in distance,
> vessel-days, and fleet-capacity intensity.

That is a deeper contribution because it studies the **structure of resilience**,
not only the size of the disruption.

## Next practical action

Use the implemented Phase R2-R5 artifacts for thesis synthesis. The next
highest-ROI work is to integrate `reports/network_rewiring_summary.md` with the
main results chapter and decide whether to add any optional, source-admitted
freight-rate appendix. Do not promote anomaly or reallocation outputs to causal
effects unless the formal estimand is changed and approved.
