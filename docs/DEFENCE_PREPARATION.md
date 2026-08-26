# Defence preparation

**Design SHA-256:** `412024f141c093d1ee3284c9faf33f87b58c2b0a5cbd7a726308ab87b8c41a34`  
**Verification status:** `NEEDS-VERIFY` until Mher runs the G4 commands.

Prepared answers to the five challenges most likely to be pressed. Each states the answer, the supporting detail, the concession that should be made rather than defended, and the frozen artifacts to cite. Conceding the real limitation is the strongest available position; every one of these limitations is already documented.

## 1. Why is the conditional route/energy ARX result excluded from the headline range when it fits better?

**Short answer.** Because it uses information the counterfactual is not allowed to have, not because it fits worse.

The conditional route/energy ARX consumes observed post-cutoff covariates. A no-disruption counterfactual cannot condition on realised post-disruption Panama transits and energy prices, which are themselves plausibly affected by the event. Its 62.858/day result is published in the admission table with a machine-readable exclusion reason, so the choice is auditable rather than hidden. Admitting it would widen the pinned range to 13.233/day and defeat the headline, which is precisely why the rule was fixed on information grounds before the range was read.

**Concede this.** The admission rule was frozen ex post and unblinded. It is documented as such and never described as preregistered.

**Cite:**
- `data/processed/model_admission_protocol.csv`
- `data/processed/model_admission_known_results.csv`

## 2. PortWatch revises. Does your result survive the vintage changing under you?

**Short answer.** No, and the size of that exposure is measured rather than asserted.

The same AR(1,7) specification on the August vintage gives 43.814/day against 52.838/day on the pinned July vintage, a same-model difference of 9.025 transits/day for AR(1,7). That is larger than the 5.175/day spread across the four selected models on the pinned vintage. The honest statement is that vintage choice moves this number more than model choice does, so the reporting basis is pinned and disclosed, and the two axes are reported separately.

**Concede this.** Vintages are different measurement states and are never averaged or ranked for truth. The absolute magnitude is vintage-sensitive; only the pinned basis is reported as primary.

**Cite:**
- `data/processed/portwatch_sensitivity_budget_card.csv`
- `data/processed/model_vintage_matrix_summary.csv`

## 3. Hormuz-crossing sequences fall from 145 to 2. Does that not show shipping stopped?

**Short answer.** It shows the panel stopped observing those sequences. That is not the same proposition as shipping stopping.

A sequence leaves the modeled panel when AIS coverage lapses, when neither endpoint attributes to a terminal within the radius, or when no route resolves. Each failure mode is plausibly more likely during a disruption, so the bias runs in an unknown direction. The result is reported as modeled resolved terminal-sequence support: 145 to 2 Hormuz-crossing against 971 to 746 overall at 30 km, with the overall denominator always attached. The direction survives the 10, 20 and 30 km grid and the both-period carrier cohort.

**Concede this.** This layer cannot establish physical throughput and no AIS-dark throughput is inferred from it. Independent corroboration would need scene-level SAR, which is deferred post-submission.

**Cite:**
- `data/processed/network_support_radius_sensitivity.csv`
- `data/processed/network_support_denominators.csv`

## 4. Your p-value is 0.111. Is that not simply a null result?

**Short answer.** 0.111 is the smallest value the design can produce. It is a floor, not a failure to reject.

The pre-period supports 8 disjoint 130-day reference blocks, so the smallest attainable rank p-value is 1/(8+1) = 0.111. The observed statistic sits exactly at that floor: it exceeds every pre-treatment reference block, under all three origin rules and all four resolutions in the frozen grid. Reading 0.111 as weak evidence confuses the value with the resolution of the instrument. For the same reason the 90% and 95% conformal bands are reported as unbounded rather than clipped, since their order statistic (9) exceeds the 8 available blocks.

**Concede this.** No 5% claim is available at the reporting resolution, and none is made. A finer 30-day resolution does reach a 1/39 floor, but that is a partition property rather than evidence and the reporting resolution was fixed beforehand.

**Cite:**
- `data/processed/horizon_frontier_summary.csv`
- `data/processed/horizon_frontier_audit_expectation.json`

## 5. Is the route-burden increase evidence that ships sailed farther?

**Short answer.** No. It is a composition statistic, not a behaviour one.

The quantity is modeled distance per nominal vessel-capacity m3 among retained inferred voyages. Nominal capacity is a carrier design property rather than measured cargo, and the distance is a shortest-sea-route estimate rather than an AIS track. No vessel-level distance change is measured anywhere. The +67.585 million m3-nm per retained sequence at 30 km decomposes almost entirely into terminal-pair share reweighting and pairs entering or leaving support; carrying larger vessels on an unchanged pair explains about 1.3%.

**Concede this.** The component split does not generalise: 10 km gives roughly 22/80/-2 and the both-period carrier cohort gives 97/9/-6 at 30 km, where the 10 km cell even changes sign. Only the compositional-rather-than-within-pair reading survives the whole grid.

**Cite:**
- `data/processed/route_burden_decomposition.csv`
- `data/processed/route_burden_diagnostics.json`

## Standing boundaries under any question

- The estimand is a disruption-associated counterfactual shortfall. It is not an average treatment effect and prediction accuracy is never offered as evidence of a causal effect.
- No claim of 5% significance is available or made at the reporting resolution.
- PortWatch is all-tanker; the WTO index is LNG-specific. They are never merged.
- A missing modeled edge is a missing observation, never proof that no ship sailed.
- Modeled distance times nominal capacity is not observed cargo ton-miles and not evidence that any ship sailed farther.

