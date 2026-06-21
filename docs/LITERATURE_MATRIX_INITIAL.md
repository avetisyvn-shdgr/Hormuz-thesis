# Initial literature matrix for the throughput-counterfactual thesis

**Prepared:** 2026-06-21  
**Status:** Initial verified search, not a systematic-review completion claim.  
**Working question:** How large and persistent was the disruption-associated
shortfall in observable Hormuz tanker throughput relative to paths estimated only
from pre-disruption data, and what descriptive evidence shows LNG contraction or
reallocation?

## Screening dimensions

Each source is assessed on: event/problem, outcome, data access, method, causal
claim, reproducibility, relevance, and the boundary it leaves open. "Open access"
does not necessarily mean that the underlying AIS data or code are public.

## Closest substantive and measurement literature

| Study | Type and setting | Data and outcome | Method | Relevance to this thesis | Gap left open / caution |
|---|---|---|---|---|---|
| *Assessing impacts to maritime shipping from marine chokepoint closures* (2023), DOI `10.1016/j.commtr.2022.100083` | Peer-reviewed; scenarios for 11 chokepoints | GIS shipping lanes + 2019 bilateral trade | Shortest-route closure scenarios | Establishes rerouting linkages and country dependence, including Hormuz | Scenario analysis, not an observed-event counterfactual or daily throughput shortfall |
| *Analysis of the impact of Suez Canal blockage on the global shipping network* (2023), DOI `10.1016/j.ocecoaman.2023.106868` | Peer-reviewed; Ever Given blockage | AIS-derived global shipping network | Before/after network analysis | Demonstrates event-specific AIS measurement and heterogeneous ship-type impacts | Does not, from the available abstract, establish a pre-event forecast counterfactual with placebo inference |
| *Modeling the dynamic impacts of maritime network blockage on global supply chains* (2024), DOI `10.1016/j.xinn.2024.100653` | Peer-reviewed/open access; maritime blockage simulation | Vessel movements + BACI cargo estimates | Adaptive multi-agent simulation | Connects vessel blockage to daily supply-chain consequences | Simulation estimand and inferred cargo losses differ from observed-minus-forecast throughput |
| *Unrevealing the adaptivity of container shipping network during disruption events by AIS trajectory data* (2025), DOI `10.1016/j.ocecoaman.2025.107862` | Peer-reviewed; Russia-Ukraine conflict | Large proprietary/assembled AIS trajectory set; container network | Event-specific subnetwork and complex-network analysis | Direct precedent for measuring maritime-system adaptation during geopolitical disruption | Container-network adaptivity, not a transparent single-chokepoint counterfactual; data/code openness must be checked in full text |
| *Resilience analysis from the perspective of global container shipping network evolution* (2025), DOI `10.1016/j.jtrangeo.2025.104415` | Peer-reviewed; COVID-19, Russia-Ukraine, Suez | AIS networks at weekly/monthly frequency | Complex-network resilience metrics | Strong resilience and temporal-network background | Measures network evolution rather than the missing throughput relative to a forecast baseline |
| *Mediterranean container port reconfiguration under geopolitical disruption* (2026) | Peer-reviewed/open access; Red Sea disruption | AIS-derived port and service indicators | Multi-scale before/after analysis | Very close precedent for AIS as strategic monitoring and for cautious inference | Port reconfiguration and container services; not Hormuz tanker shortfall or the same falsification cascade |
| *SAR-based monitoring of shipping reorganization under a maritime chokepoint disruption: Evidence from the Strait of Hormuz crisis* (2026), DOI `10.1016/j.ocecoaman.2026.108265` | Peer-reviewed; the same 2026 Hormuz episode | Sentinel-1 SAR ship detections; IMF transit data for validation | Pre/post time-series monitoring and regional comparison | **Closest event-specific competitor.** Independently observes traffic collapse, congestion, and Cape rerouting without cooperative AIS | Means the event and observable-data angle are not novel alone. Available abstract does not show an AR no-disruption counterfactual, long-horizon forecast-error interval, or time/space placebo cascade |
| *How big data enriches maritime research: a critical review of AIS data applications* (2019), DOI `10.1080/01441647.2019.1649315` | Peer-reviewed critical review | AIS applications across trade, emissions, and vessel performance | Literature review | Foundation for benefits and limits of AIS-based maritime research | Broad review; does not establish an event-study design or the validity of any particular proxy |
| *Nowcasting Global Trade from Space* (2025), IMF WP 2025/093, DOI `10.5089/9798229009294.001` | Official working paper; PortWatch methodology | Satellite vessel movements, port calls, shipment estimates | Global/regional trade nowcasting | Authoritative basis for PortWatch as a timely public economic-monitoring instrument | Working paper and modeled trade estimates; not ground truth and not a causal Hormuz study |

## Closest LNG-specific literature

| Study | Type and setting | Data and method | Relevance to this thesis | Gap left open / caution |
|---|---|---|---|---|
| *Disruption of maritime trade chokepoints and the global LNG trade: An agent-based modeling approach* (2022), DOI `10.1016/j.martra.2022.100071` | Peer-reviewed/open access; simulated Panama, Suez/Bab el-Mandeb, and Malacca closures | Historical calibration + agent-based LNG trade model | Direct precedent for chokepoint-driven LNG trade reallocation and alternative sourcing | Simulated closures, not an observed-event throughput counterfactual; rules out claiming that LNG chokepoint reallocation is itself novel |
| *Structure and resilience changes of global liquefied natural gas shipping network during the Russia-Ukraine conflict* (2024), DOI `10.1016/j.ocecoaman.2024.107102` | Peer-reviewed; geopolitical shock | 2021-2022 AIS LNG network + resilience and attack simulations | Shows that geopolitical events alter LNG flow direction, volume, community structure, and resilience | Network-level before/after and simulation analysis; underlying AIS openness and reproducibility require full-text checking |
| *LNG vessels transits through Suez Canal under the changing geopolitical context* (2025), DOI `10.1186/s41072-025-00205-3` | Peer-reviewed/open access; Red Sea disruption | Commercial shipping intelligence + descriptive transit/rerouting analysis | Close precedent for LNG diversions, cargo swaps, and portfolio substitution around a chokepoint | Uses a commercial source and descriptive analysis; does not estimate a public-data no-disruption counterfactual |
| *Implications of interrupting the Hormuz Strait in the LNG trade* (2026), DOI `10.1007/s12198-026-00350-1` | Peer-reviewed; Hormuz closure scenarios | Agent-based LNG market model with stylized exporter/importer, fleet, route, and demand assumptions | Closest LNG-specific Hormuz scenario precedent; directly models alternative supply and importer losses | Scenario result, not evidence from the observed 2026 traffic path; strong simplifying assumptions and no event-study falsification |

## Core methodological literature

| Study | Role in the current thesis | What it supports | What it does not license |
|---|---|---|---|
| Synthetic-control comparative-case method (2010), DOI `10.1198/jasa.2009.ap08746` | Donor-weighted corroboration and unit placebos | Transparent construction of a comparison path and placebo logic | Causal language when donors may be affected by rerouting |
| Synthetic-control feasibility review (2021), DOI `10.1257/jel.20191450` | Design and reporting discipline | Pre-treatment fit, data requirements, transparency, failure conditions | Treating any good-fitting synthetic series as automatically causal |
| Bayesian structural time-series counterfactual (2015), DOI `10.1214/14-AOAS788` | Univariate Bayesian corroboration | Posterior predictive counterfactual paths and joint uncertainty | Removing concurrent-event bias when no clean controls or design assumptions identify the intervention |
| Interrupted-time-series model-selection framework (2018), DOI `10.1016/j.jclinepi.2018.05.026` | General counterfactual framing | Counterfactual trend choice and impact-model specification | Direct transfer of health-policy causal claims to an uncontrolled geopolitical event |

## Cross-field expansion (2026-06-22): institutional fields beyond maritime networks

The initial matrix clustered in maritime/shipping-network journals. The
following streams broaden coverage to the other institutional fields the
redefined thesis rests on. All metadata verified against Crossref / publisher.

### Energy economics: LNG / gas-market integration and Hormuz energy security

| Study | Type and setting | Data and method | Relevance to this thesis | Gap left open / caution |
|---|---|---|---|---|
| *Linking Natural Gas Markets — Is LNG Doing its Job?* (2009), DOI `10.5547/ISSN0195-6574-EJ-Vol30-NoSI-12` | Peer-reviewed; *The Energy Journal* | Price-convergence/cointegration tests of LNG arbitrage across basins | Foundational economics for *why* LNG flexibility lets importers substitute Gulf supply — underpins the "resilience through reallocation" reading | Pre-shale, pre-2026; price-integration estimand, not an event throughput shortfall |
| *Global Natural Gas Market Integration: The Role of LNG Trade and Infrastructure Constraints* (2025), DOI `10.1111/twec.13699` | Peer-reviewed; *The World Economy* | 2016–2022 integration across NA/EU/Asia incl. Russian-supply shock | Recent evidence that LNG trade integrates regional markets and that infrastructure bottlenecks bind under stress — the economic logic behind importer substitution | Integration/price estimand; not Hormuz-specific and not a daily-throughput design |
| *Energy Supply Resilience and Industrial Continuity Under a Strait of Hormuz Blockade* (2026), DOI `10.3390/en19112719` | Peer-reviewed; *Energies* | Resilience/continuity modelling of crude + LNG under a Hormuz blockade | Same chokepoint, energy-economics framing of routing/freight/insurance cost and supply availability | Scenario/modelling of a blockade, not the observed 2026 path; no public-data event-study counterfactual |
| *Measuring Geopolitical Risk* (2022), DOI `10.1257/aer.20191823` | Peer-reviewed; *AER* | News-based GPR index; macro-financial effects | Validates news/observable signals as economic measurement and frames the event as a geopolitical-risk shock | Macro index, not a maritime-throughput measure; context not mechanism |

### Economics of measurement from space (the lineage behind PortWatch)

| Study | Type and setting | Data and method | Relevance to this thesis | Gap left open / caution |
|---|---|---|---|---|
| *Measuring Economic Growth from Outer Space* (2012), DOI `10.1257/aer.102.2.994` | Peer-reviewed; *AER* | Night-lights satellite data as a proxy for income growth | Canonical precedent for using satellite observation as an *economic* measurement instrument, with explicit proxy-error treatment | Night lights ≠ vessel transits; establishes the method tradition, not the specific proxy validity |
| *The View from Above: Applications of Satellite Data in Economics* (2016), DOI `10.1257/jep.30.4.171` | Peer-reviewed review; *JEP* | Survey of satellite data uses and measurement-error pitfalls in economics | Authoritative framing that satellite proxies are observation, not ground truth — directly supports the thesis's measurement-bounding discipline | Review, not an event study; does not address chokepoint throughput |

### Forecasting methods: foundation models and distribution-free intervals (benchmark/uncertainty appendix)

| Study | Role in the current thesis | What it supports | What it does not license |
|---|---|---|---|
| *Chronos: Learning the Language of Time Series* (2024), arXiv:2403.07815, *TMLR* | Zero-shot TS-foundation-model benchmark | Tokenized probabilistic forecasting as an alternative comparison forecaster | Any identification claim; forecasting accuracy is not a causal effect |
| *A Decoder-Only Foundation Model for Time-Series Forecasting* (TimesFM, 2024), arXiv:2310.10688, *ICML* | Zero-shot benchmark forecaster | Patch-decoder forecasting baseline for the corridor/Hormuz series | Same — benchmark only; not the locked AR-only primary |
| *Unified Training of Universal Time Series Forecasting Transformers* (Moirai, 2024), arXiv:2402.02592, *ICML* | Zero-shot benchmark forecaster | Masked-encoder any-variate forecasting baseline | Same — benchmark only |
| *Conformal Prediction for Time Series* (EnbPI, 2023), DOI `10.1109/TPAMI.2023.3272339` | Distribution-free interval calibration | Sequential, exchangeability-free prediction intervals for the shortfall band | A calibrated interval is not a causal confidence statement about an ATT |

### Measurement bound: AIS data quality and dark-fleet darkening

| Study | Type and setting | Data and method | Relevance to this thesis | Gap left open / caution |
|---|---|---|---|---|
| *Charting the Uncharted: The (Un)Intended Consequences of Oil Sanctions and Dark Shipping* (2025), NBER WP 33486, DOI `10.3386/w33486` | Working paper; global crude fleet | ML ship-clustering to recover trade hidden by AIS gaps/darkening + STS transfers | Quantifies how AIS signal-gaps bias observed traffic downward — the exact measurement risk bounding the PortWatch tanker series | Working paper; crude-oil/sanctions focus, not LNG or Hormuz throughput; estimates are modelled, not ground truth |

### Identification core: causal inference under interference (donor contamination)

| Study | Role in the current thesis | What it supports | What it does not license |
|---|---|---|---|
| *Toward Causal Inference With Interference* (2008), DOI `10.1198/016214508000000292` | Names the theoretical problem behind the donor screen | Formal direct/indirect (spillover) effects when SUTVA fails — i.e. when rerouting contaminates donor chokepoints | Treating rerouting-contaminated donors as clean controls; reinforces "corroboration, not estimate" |

## What the initial search rules out

The thesis should **not** claim any of the following:

- first use of AIS or satellite data to study a maritime disruption;
- first study of chokepoint closure, rerouting, or maritime resilience;
- first study of LNG reallocation or resilience under chokepoint disruption;
- first observable-data analysis of the 2026 Hormuz event;
- first use of complex models for maritime-network disruption;
- causal identification of the Hormuz effect from a single treated time series.

## Candidate gap surviving the initial search

The most defensible working gap is narrower:

> Existing studies establish chokepoint dependence, simulate closure consequences
> and LNG substitution, or describe observed maritime-network reconfiguration using
> AIS/SAR. A 2025 Suez study also estimates expected LNG transits with event-study
> abnormal returns and ARFIMA models, so forecast-based maritime event analysis is
> not itself new. The initial search has not yet located a study of the 2026 Hormuz
> episode that estimates a
> daily tanker-throughput shortfall against a strictly pre-event, target-only
> forecast counterfactual and subjects that gap to horizon-matched temporal
> placebos, same-date spatial placebos, donor stress tests, and explicitly
> non-causal reporting, while making the core inputs and transformation pipeline
> reproducible from public sources.

This statement remains a **search hypothesis** until Scopus/Web of Science searches,
backward/forward citation chasing, and full-text screening are complete.

## Possible academic value proposition

The likely contribution is not a new forecasting algorithm. It is an auditable
measurement and falsification protocol for high-frequency maritime disruption when
clean controls and proprietary intelligence are unavailable. The protocol assigns
different roles to prediction, uncertainty, placebo comparison, donor corroboration,
and measurement-error analysis instead of allowing one sophisticated model to carry
all inferential claims.

The empirical layer then distinguishes three observables that are often collapsed:
aggregate tanker throughput, LNG-specific departure activity, and modeled route/
capacity composition. This separation makes the result weaker than an identified
freight or welfare effect, but clearer and more reproducible as evidence.

## Search work still required

- Run the seven documented queries in Scopus and Web of Science using institutional
  access; export full records and cited-reference counts.
- Obtain and screen the full text and supplementary material of the same-event SAR
  paper before freezing the gap.
- Compare the exact validation, event-window, uncertainty, and placebo procedures
  in the 2025 Suez ARFIMA study against the implemented Hormuz design.
- Check data/code availability for every AIS-based empirical paper; do not infer
  reproducibility from open-access publication status.
- Search citations to/from the 2023 closure-scenario paper and the 2019 AIS review.
- Expand the LNG-specific set through backward/forward citation chasing from the
  2022 agent-based model and 2024 AIS LNG-network study.
- Maintain separate ledgers for peer-reviewed research, working papers, official
  data methodology, and event chronology/news.
