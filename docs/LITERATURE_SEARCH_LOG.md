# Literature search log

**Search date:** 2026-06-21  
**Purpose:** Maintain an auditable record of searches supporting the redefined
throughput-counterfactual thesis. This log covers the initial web-accessible search.
Institutional Scopus and Web of Science searches remain required.

## Scope and eligibility

### Include

- Peer-reviewed studies of maritime chokepoints, shipping disruptions, rerouting,
  port/network resilience, LNG trade reallocation, AIS/SAR measurement, interrupted
  time series, forecast counterfactuals, synthetic control, or placebo inference.
- Authoritative working papers describing PortWatch or public maritime measurement.
- Recent same-event studies of the 2026 Hormuz disruption.
- Reviews that organize a relevant literature stream.

### Exclude from academic-gap evidence

- News, consultancy commentary, marketing pages, and provider blogs.
- Pure vessel-trajectory prediction without an intervention or disruption question.
- Studies whose only relationship to the thesis is generic supply-chain language.
- Papers that cannot be distinguished from similarly titled records or whose basic
  metadata cannot be verified.

Official and industry sources may still be retained separately for event chronology,
data definitions, or market context.

## Searches executed

Searches were run through web-indexed publisher, DOI, institutional, and repository
records. Quoted strings indicate exact-title or exact-concept searches.

| Stream | Representative query | Main records retained |
|---|---|---|
| Chokepoint event studies | `maritime chokepoint disruption AIS vessel traffic counterfactual event study` | Suez AIS network analysis; Hormuz SAR monitoring; Mediterranean port reconfiguration |
| Chokepoint scenarios | `assessing impacts maritime shipping marine chokepoint closures` | Pratson closure scenarios; systemic chokepoint risk study |
| Maritime resilience | `maritime supply chain resilience systematic review chokepoint disruption` | Maritime disruption-management review; port resilience review |
| Public AIS measurement | `AIS data limitations missingness spoofing maritime research review` | AIS critical review; PortWatch nowcasting methodology |
| LNG-specific disruption | `LNG shipping network resilience chokepoint AIS trade reallocation` | LNG agent-based closure model; LNG network resilience; Suez LNG event study; Hormuz LNG simulation |
| Forecast counterfactuals | `forecasting counterfactual time series intervention autoregressive model` | ITS tutorial/framework; C-ARIMA; BSTS |
| Synthetic control | Exact-title searches for original SCM, feasibility review, augmented SCM, and synthetic DiD | Publisher records and DOIs verified |
| Same-event collision check | `Hormuz synthetic control shipping AIS`, `Hormuz interrupted time series tanker throughput` | Same-event SAR paper found; no indexed matching placebo-counterfactual study found in this pass |

## Search discoveries that changed the proposed gap

1. AIS and satellite observation of disruption is already a substantial literature.
2. LNG chokepoint substitution is already addressed with agent-based models.
3. AIS-based LNG network resilience is already studied around geopolitical events.
4. A 2026 SAR study examines the same Hormuz episode using a pre/post comparison.
5. A 2025 Suez LNG paper uses event-study abnormal returns and ARFIMA models to
   compare actual with anticipated transits. Therefore, neither "forecast-based
   maritime event study" nor "LNG chokepoint reallocation" is a defensible gap.
6. Some leading chokepoint studies already provide public code and data. Therefore,
   openness alone cannot be claimed as unique; the contribution must concern the
   reproducible combination of measurement, validation, falsification, and bounded
   interpretation.

## Access and screening status

| Status | Meaning |
|---|---|
| Full text screened | Publisher page exposed methods/results sufficiently for comparison |
| Abstract screened | Only abstract/highlights were accessible; no claim about omitted procedures |
| Metadata verified | Title, year, venue, and DOI verified only |
| Institutional access needed | Full comparison requires TUM library access |

The same-event Hormuz SAR paper is currently **abstract screened / institutional
access needed**. The Suez LNG event-study paper and the systemic chokepoint-risk
paper were **full text screened** through open publisher pages.

## Cross-field expansion pass (2026-06-22)

The first pass (2026-06-21) was institutionally narrow: almost every retained
record sat in maritime/shipping-network journals (e.g. *Ocean & Coastal
Management*, *Maritime Transport Research*). That covers stream 1 (chokepoint
disruption) and part of stream 2 (AIS measurement) but under-represents the
other institutional fields the redefined thesis actually rests on. A second
pass was run on 2026-06-22 to balance the bibliography across those fields.
All records below were metadata-verified against Crossref or the publisher; the
LNG/energy and remote-sensing items were full-text or abstract screened.

| Institutional field | Representative query | Records retained (verified) |
|---|---|---|
| Energy economics: LNG / gas-market integration | `global LNG market integration flexibility security of supply energy economics` | Neumann 2009 *Energy Journal* (10.5547/ISSN0195-6574-EJ-Vol30-NoSI-12); Farag, Jeddi & Kopp 2025 *World Economy* (10.1111/twec.13699) |
| Energy security: Hormuz blockade economics | `Strait of Hormuz energy security economics chokepoint disruption` | An, Ren, Liu & Cui 2026 *Energies* (10.3390/en19112719) |
| Geopolitical-risk measurement | `Caldara Iacoviello Measuring Geopolitical Risk AER 2022` | Caldara & Iacoviello 2022 *AER* (10.1257/aer.20191823) |
| Economics of measurement-from-space | `Donaldson Storeygard satellite data economics`; `Henderson Storeygard Weil night lights AER` | Donaldson & Storeygard 2016 *JEP* (10.1257/jep.30.4.171); Henderson, Storeygard & Weil 2012 *AER* (10.1257/aer.102.2.994) |
| Time-series foundation models | `Chronos Ansari 2024`; `TimesFM decoder-only`; `Moirai unified training Woo 2024` | Ansari et al. 2024 *TMLR* (arXiv:2403.07815); Das, Kong, Sen & Zhou 2024 *ICML* (arXiv:2310.10688); Woo et al. 2024 *ICML* (arXiv:2402.02592) |
| Conformal / distribution-free forecast intervals | `conformal prediction time series EnbPI Xu Xie` | Xu & Xie 2023 *IEEE TPAMI* (10.1109/TPAMI.2023.3272339) |
| AIS data quality / dark-fleet measurement | `AIS dark fleet spoofing gaps sanctions evasion detection` | Fernández-Villaverde, Li, Xu & Zanetti 2025 *NBER WP 33486* (10.3386/w33486) |
| Causal inference under interference / SUTVA | `Hudgens Halloran causal inference interference spillover SUTVA` | Hudgens & Halloran 2008 *JASA* (10.1198/016214508000000292) |

### What the expansion changes

1. The bibliography now spans six institutional fields instead of one, so the
   gap statement can be tested against energy economics, measurement economics,
   the forecasting-methods literature, and the interference/SUTVA literature —
   not only the maritime-network field where the first pass clustered.
2. The remote-sensing-economics lineage (Henderson-Storeygard-Weil 2012;
   Donaldson-Storeygard 2016) supplies the canonical justification for treating
   PortWatch as an *economic* observation instrument, which the maritime-network
   citations did not.
3. The TS foundation-model and conformal-interval records make the
   benchmark/uncertainty appendix citable instead of asserted.
4. Hudgens-Halloran 2008 names the exact theoretical problem the donor-
   contamination screen addresses (interference / SUTVA violation), strengthening
   the corroboration-core framing in the citation audit.
5. None of the new records pre-empts the narrow protocol gap; several (Hormuz
   blockade economics, dark-fleet measurement) reinforce why a transparent,
   public-data, explicitly non-causal shortfall estimate is worth reporting.

### Caveats on the expansion pass

- This remains a **web-indexed** search. Scopus/Web of Science Boolean runs are
  still required before calling any stream exhaustive.
- The TS foundation-model papers are cited for the *benchmark appendix only*;
  per the citation audit they justify forecasting comparisons, never
  identification. Exact deployed model-release versions (Chronos-2, TimesFM-2.5)
  still require separate release citations distinct from these method papers.
- The dark-fleet NBER paper is a working paper, retained for the AIS measurement
  bound (signal gaps / darkening), not as peer-reviewed ground truth.
- *Energies* Hormuz-blockade and *World Economy* integration papers are
  energy-economics context, not event-study evidence for the 2026 shortfall.

## Remaining database work

1. Run all seven planned Boolean queries in Scopus and Web of Science.
2. Export RIS/BibTeX records including abstracts, keywords, citation counts, and
   references.
3. Deduplicate by DOI, then by normalized title.
4. Screen titles/abstracts against the inclusion rules above.
5. Conduct backward and forward citation searches from:
   - the 2019 AIS critical review;
   - the 2022 LNG agent-based model;
   - the 2023 chokepoint closure-scenario study;
   - the 2025 Suez LNG event study;
   - the 2025 systemic chokepoint-risk study;
   - the 2026 same-event Hormuz SAR study.
6. Freeze the final search date and record the number found, deduplicated, screened,
   excluded, and retained before describing the review as systematic.

