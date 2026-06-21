# Proposal citation audit for the redefined thesis

**Prepared:** 2026-06-21  
**Purpose:** Reassess the bibliography in `Thesis_Proposal_MA` against the working
throughput-counterfactual scope. This is a bibliographic audit, not a completed
literature review.

## Audit rule

A citation is retained only when it supports a method, data source, measurement
boundary, or substantive claim used by the current design. Correct metadata does
not by itself make a source relevant. Provider journalism can document chronology
or market context, but it cannot establish the academic gap.

## Summary verdict

The proposal provides a useful methodological seed bibliography, but it cannot be
carried over unchanged. It was assembled around LNG freight prices, continuous
exposure, mediation, causal discovery, and proprietary AIS ton-miles. The current
study instead needs four balanced streams:

1. maritime chokepoint disruption and network reallocation;
2. AIS/public satellite data as an economic measurement instrument;
3. interrupted-time-series and forecast-counterfactual design;
4. synthetic-control and placebo inference under donor contamination.

## Proposal references: retain, demote, or replace

| Proposal reference group | Verification status | Decision for revised review | Reason |
|---|---|---|---|
| Original synthetic control (2010) | Metadata and DOI verified | **Retain, core method** | Establishes the comparative-case design and placebo logic used as corroboration. |
| Synthetic-control methodological review (2021) | Metadata and DOI verified | **Retain, core method** | Supports feasibility, pre-fit, transparency, and failure-condition discussion. |
| Augmented synthetic control (2021) | Metadata and DOI verified | **Background only** | The implemented estimator is donor-weighted synthetic control, not augmented SCM. Do not imply implementation. |
| Synthetic difference-in-differences (2021) | Metadata and DOI verified | **Remove from core methods** | Discussed in the original design but not used in the working pipeline. |
| Double/debiased machine learning (2018) | Metadata and DOI verified | **Remove from core methods** | The proprietary-data dose-response design was abandoned; DML is not implemented. |
| Generalized random forests (2019) | Proposal metadata appears complete; not needed by current design | **Remove** | No heterogeneous-treatment estimator is used. |
| Time-series causal discovery (2019) | Proposal metadata appears complete; not needed by current design | **Remove** | PCMCI/causal-direction analysis belongs to the abandoned coupled-freight design. |
| PatchTST, iTransformer, TimeXer | Proposal gives plausible full citations | **Demote to historical proposal context** | These models are not the working benchmark roster. Their presence would confuse proposed and implemented methods. |
| Chronos and TimesFM foundation-model papers | Proposal citations are plausible; model releases must be cited separately from papers | **Retain narrowly** | They justify forecasting benchmarks only, not identification. Chronos-2 and TimesFM-2.5 release metadata require exact release citations. |
| Port economics textbook | Proposal itself says chapter/edition must be confirmed | **Retain only after chapter-level verification** | Potential background for transport work and shipping-rate formation, not evidence of the new empirical gap. |
| IMF Red Sea/PortWatch item | Incomplete citation in proposal | **Replace** | Use the verified PortWatch methodology/nowcasting paper and exact IMF disruption publications. |
| News/provider items: Argus, Lloyd's List, S&P Global, Kpler | URLs/titles supplied; access and archival stability vary | **Chronology/context only** | Not peer-reviewed evidence for novelty or method validity. |
| EIA, ICE, Spark documentation | Official/provider sources | **Data and institutional context only** | Appropriate for definitions, access, methodology, and event chronology. |
| Placeholder energy counterfactual paper (`Peter, Li, Li & Ketter`) | Incomplete author names, year, title, and venue | **Delete unless identified** | It is not a citable reference in its current form. |

## Verified method records

- *Synthetic Control Methods for Comparative Case Studies* (2010),
  DOI `10.1198/jasa.2009.ap08746`.
- *Using Synthetic Controls: Feasibility, Data Requirements, and Methodological
  Aspects* (2021), DOI `10.1257/jel.20191450`.
- *The Augmented Synthetic Control Method* (2021),
  DOI `10.1080/01621459.2021.1929245`.
- *Synthetic Difference-in-Differences* (2021),
  DOI `10.1257/aer.20190159`.
- *Double/debiased machine learning for treatment and structural parameters*
  (2018), DOI `10.1111/ectj.12097`.
- *Inferring causal impact using Bayesian structural time-series models* (2015),
  DOI `10.1214/14-AOAS788`. This was absent from the proposal bibliography but is
  required because BSTS is now implemented as corroboration.

## Immediate citation risks

1. The original proposal's literature-gap prose is tied to an estimand that no
   longer exists. It must not be reused with nouns simply replaced.
2. The proposal overweights advanced causal and forecasting methods that are not
   part of the current primary design.
3. The current repository has no saved scholarly-paper library or reference-manager
   database. The proposal contains references, not archived source texts.
4. At least one proposal citation is a literal placeholder, and several entries
   contain their own verification warnings.
5. The academic gap cannot be "AIS has not been used for disruption analysis";
   multiple verified studies already do this.

## Recommended core bibliography architecture

- **Substantive core:** observed chokepoint closures, rerouting, network resilience,
  and LNG/maritime reallocation.
- **Measurement core:** AIS, SAR, PortWatch, public-data limitations, and trade
  nowcasting.
- **Design core:** interrupted time series, AR forecast counterfactuals,
  horizon-matched errors, and measurement-error limits.
- **Corroboration core:** synthetic control, placebo inference, BSTS, and donor
  contamination.
- **Benchmark appendix:** foundation-model forecasting papers and exact software/
  model-release citations.

## Sources used for this audit

- American Economic Association records for synthetic control review and synthetic
  difference-in-differences.
- Taylor & Francis/JASA records for original and augmented synthetic control.
- Oxford Academic record for double/debiased machine learning.
- Institute of Mathematical Statistics record for Bayesian structural time series.
- IMF publication record for `Nowcasting Global Trade from Space`.

