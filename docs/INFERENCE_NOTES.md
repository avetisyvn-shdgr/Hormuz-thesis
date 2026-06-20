# Inference Notes — uncertainty & robustness layers

**Status:** Updated 2026-06-17 after diagnostic review of
`scripts/run_placebo_inference.py`, `scripts/run_spatial_placebo.py`, and
`scripts/run_interval_calibration.py`. Covers placebo-in-time, placebo-in-space,
and residual-calibrated intervals.

## What the placebo-in-time result says

The actual post-treatment Hormuz throughput loss is much larger than losses from
earlier pre-treatment placebo windows of the same calendar horizon. For the
clean headline target, `hormuz_tanker_transits`, the route-only ARX result is:

| Statistic | Value |
|---|---:|
| Actual cumulative throughput loss | 5,176.35 tanker transits |
| Actual mean daily throughput loss | 55.07 tanker transits/day |
| Placebo loss p95 | 1,306.89 tanker transits |
| Actual / placebo p95 | 3.96x |
| Corrected one-sided placebo p-value | 0.027 |

This supports the statement: **the observed Hormuz transit collapse is far
outside the pre-treatment forecast-error distribution under the transparent
baseline models.**

## How to report the p-value

Do **not** over-read `p = 0.027` as a precise tail probability. The 36 placebo
windows overlap heavily: the window length is 94 days and the step is 30 days, so
adjacent placebo windows share 64 days. A greedy non-overlap count gives only
about **9 effectively independent horizon-length windows**.

The corrected empirical p-value is still a useful design-floor diagnostic:

```text
p = (number of placebo losses >= actual loss + 1) / (number of placebos + 1)
  = 1 / 37
  = 0.027
```

But because this is the smallest value the design can produce, it cannot
distinguish "barely larger than all placebos" from "much larger than all
placebos." Therefore the writeup must report **separation ratios** such as
actual loss divided by placebo p95.

## Treatment-date robustness — donut design

Updated 2026-06-17: `scripts/run_treatment_robustness.py` writes
`data/processed/treatment_robustness_summary.csv` and
`data/processed/treatment_robustness_daily.csv`.

This is deliberately **not a cutoff sweep**. The training cutoff remains fixed at
the earliest defensible disruption date, **2026-02-28**, so every model trains
only on rows strictly before the disruption. Later chronology dates define
post-period scoring windows only. Moving the cutoff to 2026-03-02 or 2026-03-04
would put disrupted days into training and would poison the counterfactual
baseline.

Donut sensitivity: treat **2026-02-28 through 2026-03-04** as the transition
window through QatarEnergy's force-majeure declaration and exclude it from
effect scoring. The recursive forecast still begins on 2026-02-28 as an
unscored bridge. Only rows from **2026-03-05 onward** are scored in the donut
result.

Methodological justification: this separates the identification-safe training
rule from uncertainty about exactly when the operational regime fully hardened.
The robustness question is whether the estimated daily loss persists after
dropping the ambiguous transition period, not whether models can be improved by
training on already-disrupted observations.

Data requirement: no new data. The script reuses `panel_aligned.csv`, the same
transparent seasonal-naive / route-only ARX / route+energy ARX baselines and the
verified treatment-date candidates in `config/settings.yaml`.

For the primary transit-count target and route-only ARX, the locally generated
artifact shows:

| Window | Scored post window | Valid days | Cumulative loss | Mean daily loss |
|---|---:|---:|---:|---:|
| Donut clean post | 2026-03-05 to 2026-06-01 | 89 | 4,942 tanker transits | 55.5/day |
| Kinetic-trigger anchored | 2026-02-28 to 2026-06-01 | 94 | 5,176 tanker transits | 55.1/day |
| Closure-declaration anchored | 2026-03-02 to 2026-06-01 | 92 | 5,112 tanker transits | 55.6/day |
| Force-majeure anchored | 2026-03-04 to 2026-06-01 | 90 | 4,999 tanker transits | 55.5/day |

Interpretation: the cumulative loss changes mechanically with the number of
scored days, but the mean daily route-only ARX transit loss remains stable across
the donut and named anchored windows. This supports persistence of the measured
throughput collapse after the ambiguous transition period is removed from
scoring.

Expected limitation: this still estimates observed AIS-based tanker throughput
loss, not LNG-specific freight-rate transmission. It does not solve
treatment-correlated AIS dark activity, donor contamination, or energy-price
mediation. The route+energy ARX remains a sensitivity model because post-shock
energy prices may absorb part of the treatment path.

Next action: after the user reruns `scripts/run_treatment_robustness.py` and
confirms the artifacts, proceed to donor-weighted synthetic control as
corroboration only. Exclude the five contaminated corridors and assess fit with
pre-period RMSPE before interpreting any post/pre placebo ratios.

## Capacity target caveat

For `hormuz_tanker_capacity`, the actual post-treatment window has fewer valid
scored days because alignment masks capacity artifacts where transit count is
positive but capacity is zero. The actual capacity statistic currently has 79
valid days, while placebo capacity windows have 94 valid days.

Therefore:

- Use **mean daily throughput loss** as the primary placebo statistic for
  capacity.
- Treat cumulative capacity loss as conservative and descriptive unless the
  observation counts are aligned.
- The `placebo_time_summary.csv` output now includes both cumulative and
  mean-daily p-values and separation ratios.

## Training-window asymmetry

The actual model trains on the full pre-treatment history (`n_train = 1519`).
Placebo models use expanding pre-treatment windows, from 365 to 1415 training
days, with median 890. This can widen placebo forecast errors because early
placebo models are less trained. That asymmetry is conservative for the present
result, but it should be stated.

## What placebo-in-time does not cover

This layer is only placebo-in-time evidence. It does **not** solve:

- AIS dark activity, GPS jamming, spoofing, or treatment-correlated measurement
  error.
- Panama/control contamination from rerouting and SUTVA violations.
- Energy-price mediation if route+energy ARX is used.

Placebo-in-space (below) and residual-calibrated intervals (below) extend this
layer but do not resolve the measurement-error or contamination issues above.

## Same-date spatial placebo check

Updated 2026-06-17: `scripts/run_spatial_placebo.py` applies the same
seasonal-naive counterfactual to all 28 PortWatch chokepoints at the Hormuz
treatment date. This is **not synthetic control**; it is a same-date donor-pool
diagnostic.

For the primary transit-count target, report both raw scale and normalized
severity. Lead with normalized severity because raw losses are mechanically
scale-confounded across chokepoints.

| Statistic | All donors | Low-contamination donors |
|---|---:|---:|
| Hormuz cumulative loss | 5,234 tanker transits | 5,234 tanker transits |
| Hormuz normalized loss | 95.5% of expected transits | 95.5% of expected transits |
| Donor p95 loss | 636.6 | 601.95 |
| Hormuz / donor p95 | 8.22x | 8.70x |
| Donor p95 normalized loss | 19.3% | 20.3% |
| Hormuz / donor normalized p95 | 4.96x | 4.71x |
| Descriptive donor p-value | 0.036 | 0.043 |
| Largest donor loss | Malacca Strait, 1,680 | Malacca Strait, 1,680 |
| Largest normalized donor loss | Ombai Strait, 29.8% | Ombai Strait, 29.8% |

Interpretation: the Hormuz transit collapse is not reproduced across the
PortWatch chokepoint cross-section in the same window. It is #1 by raw loss and
#1 by normalized loss. Malacca Strait is the largest raw donor loss (1,680
transits), but this is only **20.3%** of its own expected flow (8,282), so it is
better read as a large-volume forecast miss than as a comparable disruption. The
largest normalized donors are Ombai Strait (29.8%, tiny/noisy), Malacca Strait
(20.3%), and Bohai Strait (16.2%). Do not over-read small-chokepoint percentages;
present raw and normalized results side by side.

For capacity, the spatial helper now applies the same artifact-masking policy as
the processed panel (`capacity_tanker == 0` while `n_tanker > 0` becomes missing).
Capacity therefore has 79 valid Hormuz post-treatment observations. As before,
use mean-daily capacity loss as the cleaner comparison when valid day counts
differ.

## Leave-one-donor-out spatial sensitivity

Updated 2026-06-17: `scripts/run_spatial_placebo.py` now also writes
`data/processed/spatial_placebo_leave_one_out.csv`. This is a sensitivity check
on the **existing unweighted spatial placebo pool**, not a new model. The script
drops each donor chokepoint one at a time, recomputes donor p95 values,
separation ratios and descriptive donor p-values, and leaves the Hormuz treated
series fixed.

Methodological justification: the same-date spatial placebo result should not be
driven by a single influential donor. This check is especially important for
Malacca Strait, which is the largest raw donor loss. If removing Malacca caused
the normalized Hormuz separation to collapse, the spatial placebo evidence would
be fragile.

Data requirement: no new data. The check reuses the pinned PortWatch snapshot,
the seasonal-naive counterfactual and the same all-donor / low-contamination
donor definitions used by the spatial placebo layer.

For the primary transit-count target (`n_tanker`), the locally generated artifact
shows:

| Donor set | Minimum normalized separation after any single donor drop | Dropping Malacca normalized separation | Normalized p-value range |
|---|---:|---:|---:|
| All donors | 4.90x | 5.96x | 0.037-0.038 |
| Low-contamination donors | 4.60x | 5.64x | 0.045-0.048 |

Interpretation: the near-5x normalized Hormuz separation is not driven by any
single donor. Dropping Malacca increases the normalized separation because
Malacca is one of the larger donor losses rather than the source of the Hormuz
outlier result.

Expected limitation: this remains a descriptive donor-pool diagnostic with small
N and quantile sensitivity. It does not create a synthetic counterfactual, solve
donor contamination, or identify an LNG-specific effect. It only checks whether
the existing unweighted spatial comparison is single-donor fragile.

Next action: after the user reruns `scripts/run_spatial_placebo.py` and verifies
the leave-one-out CSV, proceed to treatment-date robustness using the donut
design. The training cutoff must remain at 2026-02-28; later cutoffs would train
the counterfactual on disrupted days and poison the baseline.

## Residual-calibrated intervals

Updated 2026-06-17: `scripts/run_interval_calibration.py` attaches an uncertainty
band to the counterfactual gap. It does **not** refit anything post-treatment.
Pointwise bands use empirical quantiles of the pre-treatment rolling-origin
residuals (`residual_quantiles`); the aggregate cumulative-loss interval is a
block bootstrap of residual sums over the post-treatment horizon
(`block_residual_sums`, length-7 blocks, 5,000 draws, mean-centered), so it
preserves short-run serial dependence. Configuration: `alpha = 0.05`,
`block_length = 7`, `n_draws = 5000`, seeded per model/target for reproducibility.

For the clean headline target, `hormuz_tanker_transits`, route-only ARX:

| Statistic | Value |
|---|---:|
| Point cumulative throughput loss | 5,176.35 tanker transits |
| 95% aggregate interval | 4,816 to 5,497 tanker transits |
| Mean daily loss | 55.07 transits/day |
| 95% mean-daily interval | 51.2 to 58.5 transits/day |
| Calibration residuals used | 1,140 (38 folds × 30 days) |
| Post-treatment horizon | 94 days |

The interval excludes zero by a wide margin, consistent with the placebo-in-time
and placebo-in-space layers. Report it as a forecast-error band, not a structural
causal interval.

**Horizon caveat — these short-fold bands understate true uncertainty (now
addressed below).** The calibration residuals come from rolling-origin folds with
a ≤30-day forecast horizon, but the post-treatment counterfactual is a single
recursive forecast over **94 days**. Recursion depths of roughly 31–94 days are
therefore not represented in the residual pool, and a recursive forecast compounds
error as the horizon lengthens. So treat the interval above as a **lower bound on
true 94-day counterfactual uncertainty**. The long-horizon interval in the next
section recalibrates at the true horizon and supersedes this band for reporting.

## Long-horizon (94-day) intervals

Updated 2026-06-17: `scripts/run_long_horizon_intervals.py` recalibrates the band
at the **true ~94-day horizon**, resolving the caveat above. Rather than
block-bootstrapping ≤30-day-fold residuals, it reuses the **placebo-in-time
windows** — each is a full 94-day pre-treatment recursive forecast, so its
cumulative gap is a realised 94-day cumulative forecast error that already
includes long-horizon recursive compounding. The interval is the point loss plus
the mean-centered empirical 2.5/97.5 quantiles of those errors
(`long_horizon_loss_interval`). This was preferred over conformal prediction,
whose finite-sample coverage guarantee assumes a pre/post exchangeability that an
event study deliberately breaks.

For `hormuz_tanker_transits`, route-only ARX:

| Statistic | ≤30-day-fold band | 94-day-horizon band |
|---|---:|---:|
| Point cumulative loss | 5,176 | 5,176 |
| 95% interval | 4,816 to 5,497 | 3,960 to 5,762 |
| Width | 681 | 1,801 (≈2.6× wider) |
| Excludes zero | yes | yes |

The honest band is ~2.6× wider than the short-fold band — that gap is the
understatement the caveat warned about. Across all six model×target combinations
the interval widens by 2.5–3.3× and **every one still excludes zero by a wide
margin** (route-only transit lower bound 3,960 ≫ 0), so the throughput-collapse
conclusion survives honest long-horizon uncertainty.

Limitations: the placebo windows overlap (94-day windows stepped by 30 days, ~9
effectively independent), so the 2.5/97.5 quantiles are coarse, and the placebo
models train on expanding windows smaller than the actual full-pre-period model,
which widens the errors — i.e. the band is **conservative (wide), not precise**.
For capacity, read the mean-daily interval columns rather than cumulative, because
valid-day counts differ (79 actual vs 94 placebo). This interval quantifies
forecast-error uncertainty only; it does not fix measurement bias, donor
contamination, or energy mediation.

## Donor-weighted synthetic control (corroboration)

Updated 2026-06-17: `scripts/run_synthetic_control.py` (helpers in
`src/lngfreight/synthetic.py`) fits a convex donor-weighted synthetic Hormuz on
the **clean donor pool** (the five rerouting corridors — Panama, Suez,
Bab-el-Mandeb, Cape of Good Hope, Gibraltar — are excluded for the same SUTVA
reason). To avoid the convex-hull problem (Hormuz is one of the largest
chokepoints and cannot be reproduced by a convex mix of smaller ones at raw
scale), every series is divided by its own pre-period mean, so the fit matches
**shape, not size**. Weights are fit by Frank-Wolfe on the simplex over the
pre-period; **pre-period RMSPE is the fit-credibility metric**. Inference is
Abadie-style: each clean donor is re-treated as a placebo and its post/pre RMSPE
ratio forms the reference distribution. This is **corroboration, not the anchor
estimator** (consistent with `FALLBACK_STRATEGY.md`).

For `hormuz_tanker_transits` (`n_tanker`):

| Quantity | Value |
|---|---:|
| Clean donors in fit | 22 |
| Pre-period fit days | 1,519 |
| Pre-period RMSPE (mean-scaled units) | 0.175 |
| Post-period RMSPE | 0.835 |
| Post/pre RMSPE ratio | 4.77 |
| Placebo ratio p95 | 1.23 |
| Hormuz ratio / placebo p95 | 3.87x |
| Abadie placebo p-value | 0.043 (= 1/23, design floor) |
| Effective donors (1/Σw²) | 8.8 |
| Largest single weight | korea_strait (0.18) |

Interpretation: the pre-period fit is credible (RMSPE 0.175 on mean-scaled units,
~8.8 effective donors, no single donor dominating), and Hormuz's post/pre RMSPE
ratio (4.77) is far outside the clean-donor placebo distribution (p95 = 1.23).
This independently corroborates the throughput collapse already seen in the
placebo-in-time and spatial-placebo layers, via a genuine weighted counterfactual
rather than an unweighted pool.

Capacity (`capacity_tanker`) corroborates more weakly, as expected: fewer complete
pre-period rows (428, after artifact masking) give a noisier fit (pre-RMSPE 0.282)
and a smaller separation (ratio 3.01 vs placebo p95 1.45, 2.07x, p = 0.043). Treat
the transit result as primary and capacity as supporting.

Limitations: this is a **scaled, shape-based** diagnostic, not a level effect and
not an LNG-specific freight estimate. The p-value is again a small-N design floor,
so report the ratio/p95 separation alongside it. Mean-scaling assumes a stable
pre-period level, and the clean-donor pool, while contamination-screened, is still
an imperfect control set.

## Still not covered by any inference layer

The placebo (time and space), synthetic-control, and interval layers establish
that the Hormuz gap is far outside the model's normal forecast-error behavior.
They do **not** establish the *magnitude* as a clean causal effect, because they
do not resolve:

- Treatment-correlated measurement error (AIS dark activity, GPS jamming,
  spoofing) — the observed collapse is partly true halt, partly reduced
  observability, so the loss remains an **upper bound** on the true reduction.
- Panama/donor contamination and SUTVA violations from rerouting (screened, not
  eliminated).
- Energy-price mediation under route+energy ARX.

Long-horizon recursive uncertainty, previously listed here, is now addressed by
the 94-day-horizon interval section above. No further inference-robustness
increment is queued; remaining work is freight-specific and gated on Spark/
Bloomberg access.
