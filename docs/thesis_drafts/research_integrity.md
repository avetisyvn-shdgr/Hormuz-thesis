# DRAFT - Research integrity subsection

This draft is affirmative research-governance prose. Every empirical number is
cited to the artifact that supplies it.

The thesis treats unavailable proprietary inputs as a design constraint rather
than as a reason to substitute unlabelled proxies. The working pipeline uses the
free PortWatch fallback for the primary throughput shortfall and keeps Spark as
dormant rather than silently fabricating a freight-rate outcome; the generated
run report labels the reporting estimand as a disruption-associated
counterfactual shortfall and explicitly states that it is not an LNG freight-rate
estimate (`reports/run_output.md`). This is a scope discipline choice: the
pipeline answers what the admitted data can answer and leaves the proprietary
freight extension outside the confirmed result.

The confirmatory importer-panel branch is also governed by an admission rule.
The frozen coverage audit admits `0` importers against a required minimum of
`15` importers, with `12` contiguous pre-months and `3` post months required by
the audit metadata (`data/processed/importer_source_coverage_summary.json`).
The resulting status is `no_go`, so the model is not frozen or estimated
(`data/processed/importer_source_coverage_summary.json`). Reporting this
negative result protects the thesis from converting an under-supported panel
into a false confirmatory design.

The mechanism branch applies the same standard to low-support country estimates.
Country-level Hormuz-exposed changes are suppressed below the minimum of `5`
post-period exposed voyages, and `39` country-level estimates are suppressed in
the current exposure diagnostic (`data/processed/importer_basin_exposure_diagnostics.json`).
The diagnostic also states that replacement causality is not supported and that
non-Gulf pre/post changes are descriptive composition shifts, not identified
replacement cargoes (`data/processed/importer_basin_exposure_diagnostics.json`).

Measurement caveats are carried through the pipeline instead of being hidden.
For the capacity robustness outcome, the post period contains `12` masked
Hormuz capacity values, all `12` of which are audit-confirmed zero-capacity with
positive-transit artifacts, with `0` unexplained missing capacity values
(`data/processed/capacity_missingness_diagnostics.csv`). This makes capacity a
directional secondary outcome rather than a precise magnitude to lean on.

Finally, the accepted no-third-layer decision is a governance constraint on
scope expansion. The active plan records that the next work is integration,
pre-declared sensitivity checking, and writing, not a new GEM, Baltic, or
persistence layer (`docs/CURRENT_PLAN.md`). This limits researcher degrees of
freedom: the thesis strengthens the admitted chain and documents blocked
extensions rather than adding an unconstrained layer late in the project.
