# Basin-interval coverage simulation results

**Status:** Synthetic methodology study, 2026-06-21. This closes the outstanding
Task 3 acceptance check: *"A simulation must show that any proposed basin
interval reaches its stated coverage under the tested data-generating processes;
otherwise keep basin output point-only."* No corridor panel, no post-cutoff
observation and no supervisor-gated benchmark is involved. The study answers a
statistical question about interval constructions, not an empirical question
about the 2026 disruption.

Source: `src/lngfreight/basin_coverage.py`; runner
`scripts/run_basin_interval_simulation.py` (kept outside `run_all.py`); tests
`tests/test_basin_coverage.py`. Outputs:
`data/processed/basin_interval_coverage_simulation.csv` and
`..._summary.json`.

## What was tested

A basin aggregate effect is the sum of corridor-level scaled signed deviations
(the `mean_scaled_signed_deviation` statistic of the inference contract). Four
interval constructions a researcher would plausibly reach for were evaluated by
Monte-Carlo coverage (4,000 replications, seed `20260621`, nominal 0.80 to match
the frozen interval level), measuring how often each interval contains the
**topology-aware** basin estimand:

- `independent_normal_sum` — Gaussian interval with basin variance summed across
  corridors assuming independence;
- `marginal_quantile_sum` — sum of each corridor's own placebo quantiles;
- `placebo_reference_as_interval` — the shared-placebo null range used directly
  as an interval (the anti-pattern the protocol labels
  `placebo_reference_not_interval`);
- `joint_centered_resample` — the covariance-aware interval: the estimate plus
  the empirical quantiles of the jointly-summed, centred placebo draws.

Five data-generating processes isolate one obstacle at a time, then combine them
in `realistic_design_nine_draws`, which uses the **nine** shared placebo draws
actually available in `config/corridor_transmission.yaml`, positive
cross-corridor dependence (ρ = 0.5) and 25% chokepoint double counting.

## Result (empirical coverage, nominal = 0.80)

| Scenario | independent_normal | marginal_quantile | placebo_reference | joint_resample |
|---|---:|---:|---:|---:|
| ideal_independent_large_draws | 0.80 | 1.00 | 0.00 | 0.80 |
| correlated_large_draws | 0.55 | 0.91 | 0.00 | 0.80 |
| correlated_nine_draws | 0.54 | 0.82 | 0.00 | 0.68 |
| double_counted_large_draws | 0.46 | 0.83 | 0.00 | 0.71 |
| **realistic_design_nine_draws** | **0.45** | **0.72** | **0.01** | **0.59** |

Monte-Carlo standard errors are ≤ 0.008 throughout (see the CSV).

## Reading of the result

1. **The null reference is never an interval.** `placebo_reference_as_interval`
   covers ≈0% because the null distribution is centred at zero and is never
   shifted to the estimate. This is the explicit anti-pattern the protocol bans.
2. **Ignoring dependence undercovers.** `independent_normal_sum` is calibrated
   only at ρ = 0 and collapses to 0.45–0.55 once corridors co-move, which they
   do (shared shocks across chokepoints).
3. **Marginal-quantile summation is not calibrated.** It over-covers heavily
   under low correlation (1.00, width ≈ 2.2× the joint interval) and drifts with
   ρ; a method whose coverage swings with an unknown nuisance parameter does not
   deliver its *stated* coverage.
4. **Even the correct method needs conditions the design cannot supply.** The
   covariance-aware `joint_centered_resample` reaches nominal coverage only with
   many draws **and** no double counting. With the nine real shared draws it
   falls to 0.68; with double counting to 0.71; with both — the realistic
   design — to 0.59.

Under the realistic design **no** method meets the 0.80 target within a 0.03
tolerance; the best achievable coverage is 0.72. This is decisive evidence, not
assertion, for the three theoretical reasons already stated in
`CORRIDOR_INFERENCE_PROTOCOL.md`: marginal quantiles do not supply a joint
predictive path, a null reference distribution is not an interval, and summing
chokepoints double-counts traffic so the basin-sum estimand is ill-posed.

## Decision

`basin_interval_policy: point_only` is retained, now backed by simulation. A
future basin interval would require (a) materially more independent shared
placebo windows, (b) a covariance-aware joint construction, and (c) an explicit
basin estimand and corridor topology that resolves double counting — each frozen
and re-validated by this coverage study **before** any real result is viewed.
