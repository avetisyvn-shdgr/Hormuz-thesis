# DRAFT - Estimand ladder

This draft is thesis-integration prose, not a generated result. Every empirical
number below is cited to a processed or report artifact next to the sentence
that uses it.

## Measurement

The first rung is measurement: the thesis measures the observed AIS-based tanker
throughput break at the Strait of Hormuz after the locked cutoff
`2026-02-28` (`reports/run_output.md`). At this rung, the claim is that the
observed PortWatch tanker-throughput series records a large physical disruption
in a chokepoint flow. It is not yet a causal effect, not LNG-specific cargo
volume, not freight pricing, and not a vessel-level laden-state reconstruction.

## Disruption-associated counterfactual shortfall

The second rung asks how much observed tanker throughput fell short of a
pre-treatment counterfactual generated from the same series. The AR-only working
primary estimates a shortfall of `6,869.0` tanker transits, with a
horizon-matched `95%` interval from `5,430.3` to `8,088.9` transits
(`reports/run_output.md`). At this rung, the thesis claims a
disruption-associated counterfactual shortfall under explicit forecasting and
placebo assumptions. It does not claim that forecast accuracy identifies a
causal ATT, and it does not claim to price the disruption in LNG freight markets.

## Physical mechanism

The third rung links the aggregate chokepoint result to LNG-specific physical
mechanism evidence. The WTO/AXSMarine LNG outbound index falls by `98.3%`, the
inferred Gulf departure-call count falls by `93.0%`, expanded nominal
capacity-nautical-miles fall by `15.6%`, and modeled sailing vessel-days at
`15` knots fall by `17.2%` (`data/processed/mechanism_evidence_summary.csv`).
At this rung, the thesis claims mechanism-consistent triangulation: the
LNG-specific direction of the shock and the retained-voyage capacity-distance
pattern move in ways consistent with a disruption and reallocation story. It
does not claim observed cargo ton-miles, observed sailed AIS tracks, or actual
replacement cargo matching.

## Descriptive network rewiring

The fourth rung describes importer-origin portfolio movement in source-native
monthly customs data. The network table covers `5` importer cases plus the
`EU27` aggregate comparator, with post-month support of `3` months for China,
EU27, India, and Japan, and `4` months for Korea and Taiwan
(`data/processed/lng_rewiring_summary.csv`). At this rung, the thesis claims
descriptive network rewiring: Gulf-origin shares, source concentration, and
origin portfolios moved after the shock in the observed by-origin tables. It
does not claim that one non-Gulf cargo physically replaced one Gulf cargo, and
it does not pool India's value-basis customs evidence with physical
weight/volume-basis import evidence.

## Scenario-conditional feasibility

The fifth rung asks whether transparent reallocation scenarios can bound
replacement feasibility. Under the incremental non-Gulf growth-only scenario,
`21,425` k m3 of demand is compared with `8,045` k m3 allocated observed growth,
leaving `13,380` k m3 unmet, or `62.5%` of demand
(`data/processed/lng_reallocation_summary.csv`). Under the post non-Gulf pool
scenario, the same `21,425` k m3 demand is fully allocated but the output is
flagged as an unroutable-supply-excluded lower-bound short-route pool
(`data/processed/lng_reallocation_summary.csv`). At this rung, the thesis claims
scenario-conditional feasibility diagnostics under stated route and supply
assumptions. It does not claim observed rerouting, welfare loss, freight-rate
pass-through, or an identified structural capacity shadow price.
