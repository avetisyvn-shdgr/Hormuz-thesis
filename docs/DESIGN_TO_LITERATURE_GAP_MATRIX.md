# Design-to-literature gap validation matrix

**Status:** Working comparison based on the initial verified search. This narrows
the contribution; it does not yet prove exhaustive novelty.

## Closest-study comparison

| Design element | Chokepoint closure scenarios (2023) | Suez LNG event study (2025) | Systemic chokepoint risk (2025) | Hormuz SAR study (2026) | Current thesis |
|---|---|---|---|---|---|
| Observed disruption episode | No; simulated closures | Yes; multiple geopolitical events | No; cross-hazard risk model | Yes; same Hormuz episode | Yes; same Hormuz episode |
| Primary operational outcome | Modeled trade/rerouting | Weekly LNG volume through Suez | Expected trade value disrupted | SAR ship density/count patterns | Daily PortWatch tanker transits |
| Commodity specificity | Multiple goods | LNG-specific | Multiple goods | Broad shipping | Primary broad tanker; LNG corroboration separate |
| Core data accessibility | Public inputs + replication package | Commercial Clarkson data | Public data + Zenodo code/data | Sentinel-1 public; full processing availability unconfirmed | Public/frozen PortWatch, WTO; GFW access and modeled branch documented |
| Counterfactual construction | Closure scenarios | Event-study expected transits + ARFIMA | Hazard probability/risk model | Short pre/post comparison | Recursive AR(1,7), strictly pre-cutoff |
| Pre-event validation | Scenario validation | ARFIMA model checks; exact fold discipline differs | Model/data validation | Detection validation against IMF data | Rolling-origin forecast validation |
| Long-horizon forecast-error diagnostics | No | Not identified in screened methods | No | No in accessible abstract | Yes; descriptive overlapping-window quantile bands plus disjoint-block inference |
| Placebo dates | No | Not identified in screened methods | No | No in accessible abstract | Yes |
| Same-date placebo locations | No | No | Cross-chokepoint risk comparison, not event placebo | Regional comparison, not formal placebo in accessible abstract | Yes; 28 chokepoints |
| Donor synthetic control | No | No | No | No in accessible abstract | Yes, corroboration only |
| Donor-contamination stress | Not applicable | No | Models joint hazards, different problem | No in accessible abstract | Yes; rerouting-aware screens |
| Alternative forecasting benchmark | Not central | ARFIMA specifications | Not central | Not in accessible abstract | Seasonal naive, ARX, BSTS, Chronos-2 |
| Causal claim | Scenario consequences | Uses effect language; assumptions require review | Expected risk, not event ATT | Descriptive monitoring | Explicitly non-causal shortfall |
| Reproducible end-to-end artifact checks | Replication package | Data are commercial | Zenodo code/data | Unconfirmed | Hash-frozen pipeline and generated reports |

## What is not a gap

- Studying maritime chokepoints.
- Using AIS, SAR, or public satellite observations.
- Measuring traffic changes around a disruption.
- Simulating LNG substitution following chokepoint closure.
- Applying time-series/event-study models to LNG canal transits.
- Publishing a reproducible chokepoint model.

## Narrow gap hypothesis

The defensible hypothesis is a **protocol gap**, not a topic or algorithm gap:

> The screened literature contains simulations, descriptive pre/post monitoring,
> network-resilience studies, and a weekly LNG event study with ARFIMA expected
> transits. It has not yet revealed a same-event study that combines a daily,
> target-only no-disruption forecast with chronological pre-event validation,
> descriptive full-horizon quantile bands, disjoint-block inference, temporal
> and spatial falsification,
> donor-contamination stress, independent LNG corroboration, and end-to-end public
> artifact provenance while explicitly limiting the result to an associated
> throughput shortfall.

Every component exists somewhere in the broader methodological literature. The
potential contribution is their disciplined integration for this measurement
problem. The thesis must not call this a new estimator.

## Re-validation against the broadened institutional search (2026-06-22)

The first-pass gap was derived almost entirely from maritime-network journals. A
gap that survives only because adjacent fields were not searched is not credible,
so the protocol gap was re-tested against the five newly searched fields. Each
field below is a place the gap *could* have been falsified; none of them did, but
several narrow the framing.

| Field added | Could it falsify the protocol gap? | Verdict | Effect on the contribution |
|---|---|---|---|
| Energy economics (LNG integration, Hormuz blockade) [@neumann2009; @farag2025; @an2026hormuz] | Only if it estimated an observed daily Hormuz throughput shortfall vs a pre-event forecast | **Does not falsify.** These are price-integration or scenario/continuity estimands, not an observed-throughput event study | Strengthens the *interpretation* layer ("resilience through reallocation"); does not occupy the protocol space |
| Measurement-from-space economics [@henderson2012; @donaldson2016] | Only if a satellite-proxy event study already applied this falsification cascade to a chokepoint | **Does not falsify.** Establishes the measurement tradition and proxy-error discipline, not a chokepoint counterfactual | Supplies the canonical justification for treating PortWatch as economic measurement; reframes the thesis as inside an established tradition rather than novel data use |
| TS foundation models + conformal intervals [@ansari2024chronos; @das2024timesfm; @woo2024moirai; @xu2023conformal] | Only if a better forecaster constituted identification | **Does not falsify** — and *must not*, by the prediction≠identification rule | Makes the benchmark/uncertainty appendix citable; the contribution is explicitly not "a better forecaster" |
| AIS dark-fleet measurement [@fernandezvillaverde2025dark] | Only if it already bounded a Hormuz tanker-throughput estimate for darkening | **Does not falsify.** Sanctioned-crude focus; supplies a measurement caution, not the design | Tightens the measurement-bound limitation (apparent shortfall may partly be darkening) |
| Causal inference under interference [@hudgens2008] | Only if it resolved donor contamination into a clean control for this setting | **Does not falsify.** It names the SUTVA problem; the thesis responds by demoting donors to screened corroboration | Gives the donor-contamination screen a formal vocabulary; reinforces "corroboration, not estimate" |

**Conclusion of the re-validation:** the narrow protocol gap stated above survives
a search across six institutional fields, not one. The broadened search does not
open a "first study" claim anywhere — on the contrary it adds precedent — but it
also locates no prior work combining a daily target-only forecast counterfactual,
chronological validation, descriptive full-horizon quantile bands,
disjoint-block inference, temporal and spatial placebos, rerouting-aware donor
stress, LNG cross-source corroboration, and
frozen public-data provenance for the 2026 Hormuz episode. The contribution remains
a disciplined integration for this measurement problem, now defensible against the
fields most likely to have pre-empted it.

## Falsification conditions for the gap

The gap must be weakened or abandoned if further screening finds a prior study that:

1. estimates observed chokepoint throughput against a strictly pre-event forecast;
2. calibrates uncertainty at the actual cumulative post-event horizon;
3. combines time and spatial placebos with donor-contamination checks; and
4. provides comparable public data/code provenance.

If only some elements are found, the contribution should be reframed as an
application and extension rather than a previously absent protocol.
