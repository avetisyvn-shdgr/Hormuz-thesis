# Literature review foundation draft

**Status:** Working academic foundation. Citations use keys from
`references/literature_seed.bib`. This is not final thesis prose until the
institutional database search and supervisor scope decision are complete.

## 1. Maritime chokepoints as concentrated transport risk

Maritime chokepoints concentrate large trade flows in geographically constrained
corridors. Their importance is not determined only by the volume that passes through
them, but also by the availability of alternative routes, the dependence of specific
countries and commodities, and the secondary congestion created when vessels divert.
Scenario-based work maps these dependencies by combining trade and shipping-route
data and shows that closing one passage can redistribute pressure to other corridors
[@pratson2023]. More recent systemic-risk work extends this perspective across
multiple hazards and chokepoints, distinguishing trade exposure from the probability,
duration, and severity of disruption [@verschuur2025]. This literature establishes
the strategic importance of Hormuz, but its principal estimands are modeled exposure,
risk, or scenario consequences rather than the realized daily throughput missing
during one disruption. Energy-economics work sharpens this picture for the present
case: scenario modelling of a Hormuz blockade frames the shock through crude and LNG
availability and the routing, freight, and insurance costs it imposes [@an2026hormuz],
while news-based geopolitical-risk measurement shows that observable signals of such
events carry measurable economic content [@caldara2022]. These remain risk or scenario
estimands rather than an observed-throughput shortfall.

The broader resilience literature asks how maritime systems absorb, adapt to, and
recover from shocks. A systematic review catalogs disruption-management measures
in the maritime industry and examines how the literature connects them to
resilience and organizational performance [@nguyen2023review]. AIS network studies
report uneven regional impacts and differences by ship type, while also showing
that network structure can reorganize rather than simply contract [@wan2023suez;
@xiao2024lng]. These concepts are essential for interpreting post-event traffic.
Nevertheless, resilience must not be inferred merely because aggregate volume is
maintained: rerouting can preserve delivery while increasing time, cost, or exposure.

## 2. LNG networks, chokepoint disruption, and reallocation

The LNG literature already treats chokepoints as constraints on a globally connected
but route-dependent market. Agent-based models simulate how Panama, Suez/Bab
el-Mandeb, Malacca, or Hormuz closures alter supplier and importer flows
[@meza2022; @meza2026]. AIS-based network research similarly documents changes in
LNG flow direction, port importance, and resilience during geopolitical disruption
[@xiao2024lng]. Therefore, neither LNG substitution nor chokepoint vulnerability is
an unoccupied topic.

The economic foundation for why such substitution is feasible lies in the gas-market
integration literature. LNG arbitrage progressively links previously segmented basins
[@neumann2009], and recent evidence covering 2016–2022 shows that LNG trade integrates
the North American, European, and Asian markets while physical infrastructure
bottlenecks bind precisely under stress [@farag2025]. This literature explains the
descriptive pattern the thesis observes downstream — defended total intake but a
sharp contraction in Gulf-sourced volume — as "resilience through reallocation," and
it cautions that maintained aggregate volume does not imply an absence of cost.

The closest methodological precedent is the study of LNG transits through Suez by
Polemis and Bentsos [@polemis2025, pp. 5–6 and 8–10]. Using weekly Clarksons
Shipping Intelligence Network data, that study compares actual and anticipated LNG
transits through event-study abnormal returns and ARFIMA models for several
geopolitical episodes. It demonstrates that forecast-based event analysis of canal
transit volumes already exists. The present thesis can only differentiate itself
more narrowly: daily public observations, a longer pre-event validation design,
horizon-matched cumulative forecast errors, explicit time and space placebos, and a
deliberately non-causal estimand.

## 3. AIS and satellite data as economic observation instruments

AIS has expanded maritime research from navigation studies into trade estimation,
emissions, network construction, and vessel-performance analysis [@yang2019ais]. Its
high temporal resolution is particularly valuable when official trade statistics
arrive slowly. This use sits within a broader tradition in economics of treating
remotely sensed observation as a measurement instrument: night-lights data have been
used to proxy income growth with explicit attention to proxy error [@henderson2012],
and a methodological review sets out both the opportunities and the measurement-error
pitfalls of satellite data in economics [@donaldson2016]. PortWatch extends this
tradition into a public system for nowcasting maritime trade from satellite vessel
movements [@arslanalp2025]. Public observability is valuable because a reader can
inspect the measurement process and reproduce transformations without access to a
commercial terminal.

Public availability does not make AIS-derived measures ground truth. Coverage varies,
transponders can be disabled or manipulated, classifications can be imperfect, and
provider pipelines may model missing observations. The sanctions and dark-fleet
literature makes this bias concrete: tankers serving sanctioned trades disable AIS
transponders, so observed traffic systematically understates true flows, and recovering
the hidden volume requires dedicated modelling [@fernandezvillaverde2025dark]. This is
a direct caution for interpreting any drop in observed Hormuz tanker transits, since
part of an apparent shortfall could reflect darkening rather than absent voyages. The 2026 Hormuz SAR study is an
important same-event comparator because it observes ships independently of cooperative
AIS and validates detection against IMF transit data [@yang2026sar]. It confirms that
observable-data monitoring of this episode is already present in the literature. The
current thesis therefore treats PortWatch as a medium of observation and bounds the
interpretation of its tanker category rather than claiming direct observation of LNG
cargo, laden state, or economic welfare.

## 4. Counterfactual time-series designs

Interrupted time-series designs construct an expected post-intervention path by
extrapolating pre-intervention behavior. Their credibility depends on the stability
of that process, the treatment timing, concurrent shocks, seasonality, serial
dependence, and uncertainty over longer forecast horizons. An accurate forecast is
not automatically a valid causal counterfactual. In the present design, the AR model
therefore generates a transparent no-disruption comparison path but does not identify
a causal ATT.

Bayesian structural time-series models provide an alternative probabilistic
counterfactual generator [@brodersen2015]. Synthetic control constructs a comparison
from weighted donor units and offers transparent pre-fit and placebo diagnostics
[@abadie2010; @abadie2021]. Both approaches impose substantive assumptions. Other
chokepoints can be contaminated when traffic reroutes, which is formally an
interference (SUTVA) violation: a donor's outcome depends on the treated unit's
shock once vessels divert onto it [@hudgens2008]. This is exactly why the donor layer
is restricted to corroboration and screened for rerouting contamination rather than
treated as a clean control. A univariate model, meanwhile, cannot eliminate concurrent
shocks. The current architecture therefore assigns these models different roles:
AR-only is the target-only primary estimate; BSTS is univariate corroboration;
synthetic control and spatial comparisons are falsification evidence rather than
independent proof of causality.

Uncertainty and benchmarking draw on two further methodological strands. Distribution-
free conformal methods construct prediction intervals for sequential, non-exchangeable
time series without assuming a correct error model [@xu2023conformal], which is the
appropriate discipline for calibrating the shortfall band. Time-series foundation
models — Chronos, TimesFM, and Moirai [@ansari2024chronos; @das2024timesfm;
@woo2024moirai] — provide zero-shot benchmark forecasters. Consistent with the
identification principle that prediction is not identification, these models serve only
as alternative comparison forecasters and benchmark robustness checks; they never carry
the causal claim, which rests on the design rather than on which model fits best.

## 5. Provisional gap and contribution

The literature does not leave an empty space around maritime disruption, LNG
reallocation, public satellite data, or forecast-based event studies. The provisional
gap is instead methodological integration. The initial search has not found a study
of the 2026 Hormuz episode that estimates a daily tanker-throughput shortfall using a
strictly pre-event target-only forecast and combines chronological model validation,
long-horizon cumulative error calibration, temporal and spatial placebos,
rerouting-aware donor stress, LNG-specific cross-source corroboration, and frozen
public-data provenance.

The proposed contribution is consequently an auditable measurement and falsification
protocol, not a new forecasting algorithm and not causal identification of the shock.
Its substantive output is a bounded estimate of observable throughput shortfall plus
descriptive evidence about LNG contraction and route/source reallocation. Its broader
value is transferability: the same disciplined separation of observation,
counterfactual prediction, falsification, and mechanism evidence can be applied to
other chokepoints when proprietary intelligence is unavailable.
