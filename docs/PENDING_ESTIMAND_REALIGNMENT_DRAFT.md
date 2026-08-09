# ADVISOR ACCEPTED — DIRECT PROF. LI RATIFICATION UNRECORDED

## Estimand change from LNG freight rates / ton-mile multiplier to tanker-throughput shortfall

**Governance update, 2026-07-23:** Zhenyu Wang explicitly confirmed in writing
that the revised title, research question, estimand, claim strength, and
completed empirical scope are acceptable. This is recorded as advisor-side
acceptance. It is not attributed to Prof. Li because no direct confirmation from
Prof. Li is on record. The existing formal proposal remains unchanged until that
distinction is resolved.

## Proposed title

**Counterfactual Estimation of Tanker-Throughput Disruption at the Strait of
Hormuz: Forecasting and Synthetic-Control Evidence from the 2026 Episode**

## Proposed research question

How large and persistent was the disruption-associated shortfall in observable
daily tanker throughput through the Strait of Hormuz relative to counterfactual
paths estimated exclusively from pre-disruption data?

## Proposed outcomes and estimand

- Primary outcome: daily tanker transit count through the Strait of Hormuz,
  measured by IMF PortWatch `n_tanker`.
- Robustness outcome: daily deadweight capacity of transiting tankers, measured
  by IMF PortWatch `capacity_tanker`.
- Estimand: cumulative and mean-daily observed-minus-counterfactual throughput
  gaps over a pre-specified post-disruption window.
- Reporting language: **disruption-associated counterfactual shortfall**. This is
  not labelled a causal ATT because a single treated time series cannot eliminate
  all concurrent-event and treatment-correlated measurement explanations.

## Proposed hypotheses

**H1, primary shortfall.** Observed post-disruption Hormuz tanker transit counts
are lower than the AR-only counterfactual trained exclusively on pre-disruption
observations.

**H2, persistence and measurement robustness.** The shortfall persists across
pre-specified treatment windows and is directionally consistent for deadweight
capacity after documented artifact masking.

**H3, falsification evidence.** The observed shortfall is unusually large relative
to pre-period placebo intervention windows and same-date placebo chokepoints.
Temporal evidence is evaluated primarily by separation from the placebo p95
rather than the overlapping-window reference rank, which is descriptive rather
than a p-value. Seven disjoint horizon-length blocks are available for rank
inference, giving a one-sided rank p-value of 0.125.

**H4, donor corroboration.** A clean-donor synthetic control shows a materially
larger post/pre RMSPE deterioration for Hormuz than for donor-placebo units.
This corroborates the forecast counterfactual but does not independently prove
the absence of concurrent shocks or AIS measurement changes.

## Proposed methodology

1. Construct a daily calendar panel from immutable PortWatch, EIA, and FRED
   snapshots with cell-level imputation and masking audits.
2. Train all forecasting models on observations strictly before the earliest
   candidate disruption date and select models using chronological rolling-origin
   validation.
3. Use AR(1,7) with deterministic weekly seasonality as the primary
   counterfactual generator because it requires no observed post-treatment
   covariates. Retain seasonal naive as a benchmark and Panama/energy ARX models
   as conditional sensitivities.
4. Report daily, cumulative, and mean-daily counterfactual shortfalls with
   long-horizon intervals calibrated from realized pre-period placebo-window
   errors.
5. Run placebo-in-time, same-date spatial placebo, donor leave-one-out, treatment
   window, and deadweight-capacity robustness checks.
6. Use donor-weighted synthetic control as corroboration rather than the anchor
   estimator because donor contamination and SUTVA violations remain plausible.

No Transformer is included in the working specification. It may re-enter only
if it materially improves both pre-treatment forecast performance and interval
coverage, or if Prof. Li requires it as an architecture benchmark.

## Proposed contribution

The proposed empirical contribution is a reproducible estimate of the observable
tanker-throughput shortfall associated with the 2026 Hormuz disruption. The
methodological contribution is transparent triangulation of a target-only
forecast counterfactual, horizon-matched temporal placebos, spatial placebos, and
synthetic-control corroboration under explicit AIS and donor-contamination
limitations. LNG freight and ton-mile transmission remain contextual or optional
secondary-outcome analyses unless suitable proprietary data become available.
