# Literature matrix (complete)

**Prepared:** 2026-06-22
**Supersedes:** `LITERATURE_MATRIX_INITIAL.md` (kept for history; this file is the
working matrix).
**Scope:** The 26 references verified in `references/literature_seed.bib` (all
metadata confirmed live against Crossref / arXiv — see
`CITATION_INTEGRITY_AUDIT.md`), plus two 2026-08-09 additions
([fontagne2024matrix], [halkiewicz2026exact]; metadata verified against arXiv
abstract pages on 2026-08-09 — see `DATA_REGISTRY_REVIEW_2026-08.md` §6).
**Reading note:** This matrix is built under the **revised throughput scope**
(supervisor-approved 2026-06-16): the outcome is observable Hormuz tanker
throughput and an explicitly non-causal "disruption-associated shortfall," not
the original LNG-freight ATT. Relevance is judged against that scope.

## Conventions

Each empirical study is scored on nine dimensions: **question, event/setting,
data, outcome, method, findings, limitations, openness, relevance**.

Integrity flags (consistent with the citation audit):
- **✓** finding/attribute confirmed from the verified abstract or record.
- **△** plausible but **requires full-text confirmation** before it is used as
  evidence in the thesis. Do not cite a △ specific as settled.

Openness is split into **data access** (Public / Mixed / Proprietary /
Methodological) and **artifact** (code/replication availability). Per the audit,
several artifact claims inherited from the first-pass screening are marked △ and
must be checked, not asserted.

---

## A. Public-data and modelled/simulation studies

These rely on public, frozen, or fully simulated inputs — the same evidentiary
register the thesis commits to.

| # | Study | Question | Event / setting | Data | Outcome | Method | Findings | Limitations | Openness | Relevance to revised scope |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | Pratson 2023 [pratson2023] | How do chokepoint closures redistribute shipping pressure and expose countries/commodities? | Hypothetical closure of 11 marine chokepoints (incl. Hormuz) | GIS shipping lanes + 2019 bilateral trade (public) | Re-routing distance/exposure by country & commodity | Shortest-route closure scenarios | Closing one passage redistributes pressure to others; quantifies dependence incl. Hormuz ✓ | Scenario, not an observed event; no daily throughput series | Data: Public; Artifact: replication package △ | Establishes chokepoint dependence framing; **not** an observed-shortfall design |
| 2 | Verschuur, Lumma & Hall 2025 [verschuur2025] | What is the systemic economic risk of chokepoint disruptions across hazards? | Cross-hazard/geopolitical risk to global chokepoints | Trade + hazard exposure (public) | Expected annual trade value & loss at risk | Systemic risk model | ~USD 192bn trade at risk; ~USD 10.7bn losses + USD 3.4bn freight; Taiwan Strait & Suez top geopolitical risks ✓ | Risk/expectation estimand, not one realized event | Data: Public; Artifact: Zenodo code/data △ | Strategic-importance & cost framing; not an event counterfactual |
| 3 | Nguyen et al. 2023 [nguyen2023review] | How does the literature manage maritime-industry disruptions? | Systematic literature review | Published corpus | Disruption-management measures and resilience/performance links | Systematic review | Catalogs maritime disruption-management measures and examines their relationship to resilience and organizational performance ✓ | Review; no primary event data | Data: n/a (review); Artifact: n/a | Background for resilience vocabulary; no unverified four-category taxonomy is attributed |
| 4 | Meza et al. 2022 [meza2022] | How do chokepoint closures reallocate global LNG flows? | Simulated Panama, Suez/Bab-el-Mandeb, Malacca closures | Historical calibration + agent-based model | Supplier/importer flow reallocation | Agent-based simulation | Chokepoint closures shift LNG sourcing & flows ✓ | Simulated closures, not the observed 2026 event | Data: Public/modelled; Artifact: △ | Precedent for LNG chokepoint reallocation — rules out novelty of the topic |
| 5 | Meza et al. 2026 [meza2026] | What are the implications of interrupting Hormuz for LNG trade? | Hormuz closure scenarios | Agent-based LNG market model | Alternative supply & importer losses | Agent-based simulation | Models exporter/importer losses under Hormuz interruption ✓ | Strong stylized assumptions; scenario, not observed path | Data: Public/modelled; Artifact: △ | Closest LNG-specific Hormuz precedent — but scenario, not event-study |
| 6 | Arslanalp et al. 2025 (IMF) [arslanalp2025] | Can maritime trade be nowcast from satellite vessel movements? | PortWatch methodology | Satellite vessel movements, port calls (public outputs) | Nowcast trade & port-call indices | Global/regional nowcasting | PortWatch produces timely public trade indicators ✓ | Modeled estimates, not ground truth | Data: Public (outputs); Artifact: public portal | **Authoritative basis for the thesis's primary instrument** |
| 7 | Yang et al. 2026 (SAR) [yang2026sar] | Can SAR independently monitor shipping reorganization at Hormuz? | Same 2026 Hormuz episode | Sentinel-1 SAR detections + IMF transit data | Ship density/count, congestion, rerouting | Pre/post time-series + regional comparison | Independently observes traffic collapse & Cape rerouting; validates vs IMF ✓ | Abstract-screened; no AR forecast counterfactual / placebo cascade in accessible abstract △ | Data: Public (Sentinel-1) + IMF; Artifact: △ | **Closest same-event competitor** — defines what must be differentiated |
| 8 | Henderson, Storeygard & Weil 2012 [henderson2012] | Can satellite night lights proxy economic growth? | Cross-country growth measurement | Night-lights satellite data (public) | Income-growth proxy | Statistical proxy framework with measurement-error model | Night lights augment official growth measures ✓ | Proxy ≠ direct measure | Data: Public; Artifact: replication (openICPSR) ✓ | Canonical lineage: satellite data as **economic** measurement |
| 9 | Donaldson & Storeygard 2016 [donaldson2016] | How is satellite data used in economics, and what are its pitfalls? | Methodological review | Survey of applications | — | Review | Maps applications + measurement-error cautions ✓ | Review, not an event study | Data: n/a (review); Artifact: n/a | Justifies treating PortWatch as observation, not ground truth |
| 10 | Caldara & Iacoviello 2022 [caldara2022] | Can geopolitical risk be measured from news text? | Macro-financial GPR index | News-text corpus (public index) | GPR index; macro effects | News-based index construction | GPR spikes around conflicts; foreshadows lower investment/employment ✓ | News-text macro index, not a maritime measure | Data: Public; Artifact: public index | **Event context only** — analogical support for observable-signal measurement (audit flag) |
| 11 | An, Ren, Liu & Cui 2026 [an2026hormuz] | How resilient is energy supply/industry under a Hormuz blockade? | Hormuz blockade scenario | Energy-system model | Crude/LNG availability; cost impacts | Resilience/continuity modelling | Blockade reduces crude+LNG availability; raises routing/freight/insurance cost ✓ | Scenario/modelling, not observed 2026 path | Data: Modelled; Artifact: △ | Energy-economics framing of the same chokepoint; not an event counterfactual |

## B. Proprietary- or commercial-data studies

These depend on commercial intelligence (Clarksons, commercial AIS aggregators)
that the thesis deliberately does **not** rely on. Listed separately per the
matrix requirement so the evidentiary boundary is explicit.

| # | Study | Question | Event / setting | Data | Outcome | Method | Findings | Limitations | Openness | Relevance to revised scope |
|---|---|---|---|---|---|---|---|---|---|---|
| 12 | Polemis & Bentsos 2025 [polemis2025] | Did geopolitical events change LNG transits through Suez vs expectation? | Several Red Sea / geopolitical episodes | **Weekly Clarksons Shipping Intelligence Network data** (pp. 5–6) | Actual vs anticipated LNG transits | Event-study abnormal returns + ARFIMA (pp. 8–10) ✓ | Forecast-based event analysis of canal LNG transits exists ✓ | Commercial data; weekly | Data: **Proprietary**; Artifact: data commercial | **Closest methodological precedent** — forces the narrow differentiation (daily public data + falsification cascade) |
| 13 | Wan et al. 2023 [wan2023suez] | How did the Suez blockage reshape the global shipping network? | Ever Given grounding | AIS-derived global network (provider AIS) | Network topology change | Before/after complex-network analysis | Event-specific AIS measurement; uneven regional impacts (Africa most affected) and heterogeneity by ship type (container ships and petrochemical tankers most disrupted) ✓ | Network estimand, no forecast counterfactual | Data: Proprietary/provider AIS; Artifact: △ | Precedent for event-specific AIS network measurement |
| 14 | Xiao et al. 2024 [xiao2024lng] | How did the LNG shipping network change during Russia–Ukraine? | Russia–Ukraine conflict | 2021–2022 AIS LNG network (assembled/provider) | Flow direction, community, resilience | Network + attack simulations | Geopolitics alters LNG flow direction, port importance, resilience ✓ | Network/simulation; openness needs check | Data: Proprietary/assembled AIS; Artifact: △ | Precedent for AIS LNG-network disruption analysis |

## C. Methodological & benchmark references (not empirical event studies)

Scored on role rather than event/data. These supply identification, uncertainty,
and benchmark scaffolding; per the prediction≠identification rule none carries a
causal claim.

| # | Reference | Method role in thesis | What it supports | What it does NOT license | Openness |
|---|---|---|---|---|---|
| 15 | Abadie, Diamond & Hainmueller 2010 [abadie2010] | Donor-weighted synthetic control (corroboration) | Transparent comparison path + placebo logic | Causal language when donors are rerouting-contaminated | Public method |
| 16 | Abadie 2021 [abadie2021] | SCM feasibility/reporting discipline | Pre-fit, data requirements, failure conditions | Treating good fit as automatically causal | Public method |
| 17 | Brodersen et al. 2015 [brodersen2015] | BSTS univariate counterfactual (corroboration) | Posterior predictive counterfactual + uncertainty | Removing concurrent-event bias | Open-source (CausalImpact) |
| 18 | Hudgens & Halloran 2008 [hudgens2008] | Names the donor-contamination problem | Formal direct/indirect effects under interference/SUTVA failure | Event-specific or SCM-specific evidence (conceptual borrow — audit flag) | Public method |
| 19 | Xu & Xie 2023 (EnbPI) [xu2023conformal] | Distribution-free interval calibration | Sequential, exchangeability-free prediction intervals | A causal confidence statement about an ATT | Open-source (EnbPI) |
| 20 | Yang et al. 2019 (AIS review) [yang2019ais] | AIS-as-instrument review | Benefits & limits of AIS for trade/emissions/network | An event-study design or proxy validity | Review |
| 21 | Ansari et al. 2024 (Chronos) [ansari2024chronos] | Zero-shot TS-foundation benchmark | Tokenized probabilistic forecasting baseline | Identification (benchmark only) | Open weights/code |
| 22 | Das et al. 2024 (TimesFM) [das2024timesfm] | Zero-shot TS-foundation benchmark | Patch-decoder forecasting baseline | Identification (benchmark only) | Open weights/code |
| 23 | Woo et al. 2024 (Moirai) [woo2024moirai] | Zero-shot TS-foundation benchmark | Any-variate masked-encoder baseline | Identification (benchmark only) | Open weights/code |
| 26 | Fontagné, Micocci & Rungi 2024/2026 [fontagne2024matrix] *(added 2026-08-09)* | Matrix-completion counterfactual precedent on trade data (CETA application) | Modern generalization of SCM-style counterfactuals; adjacent to the corroboration layer and the causal-ML heterogeneity arm | Any change to the thesis's estimators; it is an application paper, not the canonical method reference (that would be Athey et al.) | arXiv preprint (v5 2026-06); peer status unverified △ |
| 27 | Halkiewicz 2026 [halkiewicz2026exact] *(added 2026-08-09)* | Exact finite-sample inference under concentrated identifying variation — limitations pointer for the small-N wild-cluster-bootstrap caveat (`CAPTIVITY_EVENT_STUDY_DESIGN.md` §5/§9) | States that exact-inference alternatives exist for the one-shock, few-clusters setting | Re-implementation of inference before submission: v1 is a days-old, single-author, unrefereed preprint. Cite as pointer only | arXiv preprint (v1 2026-08-05) △ |

## D. Energy-economics context (price/integration, not event design)

| # | Reference | Question | Data | Findings | Relevance / boundary |
|---|---|---|---|---|---|
| 24 | Neumann 2009 [neumann2009] | Does LNG arbitrage link segmented gas markets? | Basin price series (mixed) | LNG arbitrage drives price convergence across basins ✓ | Economic logic for importer substitution; pre-shale, price estimand |
| 25 | Farag, Jeddi & Kopp 2025 [farag2025] | How integrated are global gas markets and what role does LNG/infrastructure play? | 2016–2022 NA/EU/Asia prices + flows | LNG trade integrates markets; infrastructure bottlenecks bind under stress ✓ | Underpins "resilience through reallocation"; integration estimand, not Hormuz event |

## Public vs proprietary summary

- **Public / modelled / methodological (the thesis's register):** Pratson 2023,
  Verschuur 2025, Nguyen 2023 (review), Meza 2022, Meza 2026, Arslanalp 2025,
  Yang 2026 SAR, Henderson 2012, Donaldson 2016, Caldara 2022, An 2026,
  Neumann 2009 (mixed), Farag 2025 (mixed), plus all methodological/benchmark
  references (Abadie ×2, Brodersen, Hudgens, Xu-Xie, Yang 2019, Chronos, TimesFM,
  Moirai) and the dark-fleet measurement reference (Fernández-Villaverde 2025,
  AIS-based but modelled/working paper).
- **Proprietary / commercial-data:** Polemis & Bentsos 2025 (Clarksons), Wan 2023
  (provider AIS), Xiao 2024 (assembled/provider AIS).

**Implication for the contribution:** the single closest *methodological*
precedent (Polemis 2025) and the AIS network studies sit on proprietary data,
whereas the single closest *same-event* precedent (Yang 2026 SAR) is public but
does not run the forecast-counterfactual + placebo cascade. The thesis occupies
the space between them: **public data, same event, explicit falsification
protocol.** See `GAP_VALIDATION.md`.

## Measurement-bound reference (cross-listed)

| Reference | Role | Finding | Boundary |
|---|---|---|---|
| Fernández-Villaverde, Li, Xu & Zanetti 2025 (NBER 33486) [fernandezvillaverde2025dark] | AIS measurement bound | Tankers in sanctioned trades disable AIS; ~7.8 Mt/month dark crude (~43% seaborne) recovered only by modelling ✓ | Sanctioned-crude focus; does **not** establish Hormuz/LNG darkening — analogical caution only (audit flag) |

## Outstanding for full systematic status

1. The 25 August Scopus Boolean run and capped screening are complete; the query
   strings survive in `../../Research Record/literature-search/`, but the run log
   and curated set were deleted on 2026-08-30 when the literature review was
   rebuilt — see `../../THESIS_OPEN_ITEMS_2026-08-30.md` §3. Web of Science was
   unavailable through the tested TUM/Clarivate route, so coverage remains
   explicitly Scopus-only and non-exhaustive.
2. Resolve every remaining **△** by full-text screening
   and the Nguyen taxonomy, both audit-flagged.
3. Confirm artifact/openness claims (Zenodo, replication packages) by visiting the
   repositories, not inferring from open-access status.
