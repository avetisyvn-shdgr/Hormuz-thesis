# Citation integrity audit

**Prepared:** 2026-06-22
**Scope audited:** `docs/LITERATURE_REVIEW_FOUNDATION_DRAFT.md` and the 26 entries
of `references/literature_seed.bib`.
**Method:** Every citation treated as guilty until proven real. Each DOI checked
**live against the Crossref REST API** (`api.crossref.org/works/<doi>`); the three
ML papers without a journal DOI checked via live web search of their arXiv IDs.
No citation accepted from model memory.

## Headline

- **0 fabricated references. 0 broken/hallucinated DOIs.** All 26 citations are
  real with matching title/authors/year.
- The integrity risk is **not** phantom citations; it is six sentences that
  attribute a *specific* claim to a real source where the source may not support
  that specific detail (Section B).

## A. Reference verification

Status: **VERIFIED** = existence + metadata confirmed live. **VERIFIED (metadata)**
= reference real, but a specific claim drawn from it needs full-text confirmation
(see Section B).

| Citation | Status | Verification source |
|---|---|---|
| Pratson 2023 | VERIFIED | Crossref `10.1016/j.commtr.2022.100083` |
| Verschuur, Lumma & Hall 2025 | VERIFIED | Crossref `10.1038/s41467-025-65403-w` |
| Nguyen et al. 2023 | VERIFIED (metadata) | Crossref `10.1108/MABR-09-2021-0072` (online-first 2022; issue vol 8(2) 2023) |
| Wan et al. 2023 | VERIFIED (metadata) | Crossref `10.1016/j.ocecoaman.2023.106868` |
| Xiao et al. 2024 | VERIFIED | Crossref `10.1016/j.ocecoaman.2024.107102` |
| Meza et al. 2022 | VERIFIED | Crossref `10.1016/j.martra.2022.100071` |
| Meza et al. 2026 | VERIFIED | Crossref `10.1007/s12198-026-00350-1` |
| Polemis & Bentsos 2025 | VERIFIED (metadata) | Crossref `10.1186/s41072-025-00205-3` |
| Neumann 2009 | VERIFIED | Crossref `10.5547/ISSN0195-6574-EJ-Vol30-NoSI-12` |
| Farag, Jeddi & Kopp 2025 | VERIFIED | Crossref `10.1111/twec.13699` (48(6)) |
| An, Ren, Liu & Cui 2026 | VERIFIED | Crossref `10.3390/en19112719` (Energies 19(11):2719) |
| Caldara & Iacoviello 2022 | VERIFIED | Crossref `10.1257/aer.20191823` (112(4)) |
| Yang et al. 2019 (AIS review) | VERIFIED | Crossref `10.1080/01441647.2019.1649315` |
| Henderson, Storeygard & Weil 2012 | VERIFIED | Crossref `10.1257/aer.102.2.994` (102(2)) |
| Donaldson & Storeygard 2016 | VERIFIED | Crossref `10.1257/jep.30.4.171` (30(4)) |
| Arslanalp et al. 2025 (IMF, PortWatch) | VERIFIED | Crossref `10.5089/9798229009294.001` (9 authors) |
| Yang et al. 2026 (SAR) | VERIFIED | Crossref `10.1016/j.ocecoaman.2026.108265` (10 authors) |
| Brodersen et al. 2015 (BSTS) | VERIFIED | Crossref `10.1214/14-AOAS788` |
| Abadie, Diamond & Hainmueller 2010 | VERIFIED | Crossref `10.1198/jasa.2009.ap08746` |
| Abadie 2021 | VERIFIED | Crossref `10.1257/jel.20191450` (59(2):391–425) |
| Hudgens & Halloran 2008 | VERIFIED | Crossref `10.1198/016214508000000292` (103(482)) |
| Xu & Xie 2023 (EnbPI) | VERIFIED | Crossref `10.1109/TPAMI.2023.3272339` (45(10):11575–11587) |
| Fernández-Villaverde et al. 2025 (dark shipping) | VERIFIED | Crossref `10.3386/w33486` (NBER, 4 authors) |
| Ansari et al. 2024 (Chronos) | VERIFIED | Live search: arXiv:2403.07815 title match (TMLR); no journal DOI |
| Das, Kong, Sen & Zhou 2024 (TimesFM) | VERIFIED | Live search: arXiv:2310.10688 title match (ICML 2024) |
| Woo et al. 2024 (Moirai) | VERIFIED | Live search: arXiv:2402.02592 title match (ICML 2024) |

No entry rated UNVERIFIED or HIGH HALLUCINATION RISK — the truthful outcome.

## B. Claim-to-source alignment flags (require full-text confirmation)

The reference is real in each case; the flagged risk is that the draft's specific
claim may outrun what the source states. Resolve before submission (plan task L2).

1. **Nguyen et al. 2023 — fabricated-specificity risk.** Draft attributes a four-
   category response taxonomy (rerouting, capacity management, collaboration,
   technological monitoring). The exact categories are not confirmed from full
   text. Action: quote the paper's actual taxonomy or soften.
2. **Wan et al. 2023 — dimension mismatch.** Draft says effects are "spatially
   heterogeneous"; the verified record describes heterogeneity **by ship type**.
   Action: confirm which, fix the adjective.
3. **Polemis & Bentsos 2025 — detailed method attribution.** Draft attributes
   "weekly commercial shipping data … event-study abnormal returns and ARFIMA."
   This is the closest methodological competitor; an inaccurate method description
   here is the most damaging possible error. Action: attach page citations.
4. **Caldara & Iacoviello 2022 — analogical stretch.** A news-text macro index used
   to support "observable signals carry measurable economic content." Keep as event
   context, not as evidence about maritime/satellite measurement.
5. **Fernández-Villaverde et al. 2025 — out-of-scope extrapolation.** Documents AIS
   darkening for **sanctioned crude**; applied as a caution to Hormuz tanker counts.
   Hedging is honest, but the source cannot license a Hormuz-specific darkening
   claim. Keep strictly as an analogous measurement caution.
6. **Hudgens & Halloran 2008 — conceptual borrow.** Correct cite for the *formal
   concept* of interference/SUTVA violation; the paper concerns partial interference
   in randomized experiments, not maritime rerouting or SCM donor contamination.
   Use as a definitional anchor only.

## C. Bibliography hygiene

- Cite-key/bib reconciliation (2026-06-22): all 26 in-text keys resolve to a bib
  entry; no orphan entries. Re-run on every bib edit (plan task L4).
