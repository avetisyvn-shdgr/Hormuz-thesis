# Importer source coverage and panel-admission report

**Generated:** 2026-06-22  
**Verdict:** **NO_GO** for the confirmatory importer panel.

## Admission rule

An importer requires an official monthly total series, an official by-source
series for predetermined exposure, at least
12 contiguous pre-treatment months, and
at least 3 post-treatment months. The proposed
panel requires at least 10 admitted importers. GFW is
a cross-validation source only; suppressed country-level Gulf estimates cannot
replace missing official observations.

## Observed coverage

| unit | official_source | official_by_source_available | contiguous_pre_months | post_months | latest_period | gfw_country_gulf_estimate_admissible | confirmatory_panel_admissible |
|---|---|---|---|---|---|---|---|
| Japan | UN Comtrade HS 271111 | True | 5 | 1 | 2026-03 | False | False |
| India | PPAC/DGCIS | False | 179 | 2 | 2026-04 | False | False |
| South Korea | none frozen | False | 0 | 0 |  | False | False |
| China | none frozen | False | 0 | 0 |  | False | False |
| Taiwan | none frozen | False | 0 | 0 |  | False | False |
| Pakistan | none frozen | False | 0 | 0 |  | False | False |
| Bangladesh | none frozen | False | 0 | 0 |  | False | False |
| EU27 | Eurostat nrg_ti_gasm | True | 62 | 2 | 2026-04 | False | False |

## Decision

**Admitted importers: 0 of the required
10.** Current frozen public data do not admit the proposed confirmatory importer panel. Do not freeze or estimate the Option D model.

The current evidence supports a descriptive EU27/Japan/India comparison, not a
confirmatory cross-importer 2WFE model. Re-run this report after additional
national-statistics snapshots are frozen. The full source paths, hashes, and
failure reasons are in `data/processed/importer_source_coverage.csv`; the summary
is in `data/processed/importer_source_coverage_summary.json`.

## Methodological boundary

This is a coverage/admission audit, not an empirical result. No missing country
is imputed, no GFW proxy is silently promoted to an official outcome, and no
estimator is fitted.
