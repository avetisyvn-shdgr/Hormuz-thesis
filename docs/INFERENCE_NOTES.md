# Inference Notes — uncertainty & robustness layers

**Status:** Updated 2026-06-17 after diagnostic review of
`scripts/run_placebo_inference.py`, `scripts/run_spatial_placebo.py`, and
`scripts/run_interval_calibration.py`. Covers placebo-in-time, placebo-in-space,
and residual-calibrated intervals.

## Provenance-limited LNG freight forecast layer — 2026-08-08

The three Fearnleys assessment workbooks are implemented as dormant secondary
outcomes. The design is weekly and entirely separate from the daily PortWatch
model: 104 initial pre-treatment weeks, 4-week validation folds, 4-week steps,
and the locked first post-assessment week of 2026-03-06. Candidate models are a
last-observation benchmark, a 52-week seasonal naive, and two parsimonious AR
lag sets. Selection uses only pre-treatment rolling-origin MASE, with a 5%
simplicity rule. Missing weeks are not filled and post forecasts never use
observed post-treatment lags.

The last-observation benchmark is selected for East spot, West spot, and the
one-year charter. This is a deliberately weak counterfactual: it carries the
final pre-cutoff assessment ($15k, $29k, and $24k/day respectively) flat across
all 18 post weeks, so the reported deviations largely restate the fact that
assessed rates rose after late February and stayed elevated. Pre-treatment
validation MASE is 0.78 (East spot), 1.02 (West spot), and 0.84 (one-year
charter); a MASE near 1 means the selected benchmark is about as accurate as
the in-sample naive scale, i.e. these series were barely forecastable even
pre-treatment. Quote the deviation magnitudes only with this framing attached.

Across 18 post weeks, the generated artifacts report average
observed-minus-counterfactual assessment deviations of approximately
$45.8k/day, $54.8k/day, and $26.7k/day, respectively. All 18 observations for
each series lie above its pre-calibrated 90% pointwise conformal band — but
that band understates uncertainty by construction: its radius is calibrated on
pooled 1-to-4-week-ahead validation residuals, while the post forecast extends
recursively to 18 weeks ahead, where errors are mechanically larger. Treat the
band as an illustrative short-horizon reference, not a test. The primary
uncertainty statement is the horizon-matched placebo comparison: the
finite-sample-corrected two-sided ranks against overlapping historical
18-week pseudo-cutoffs are 0.043, 0.091, and 0.087. Because pseudo-cutoff
windows overlap, these are descriptive reference ranks rather than
independent-sample p-values.

**Disposition under the Phase 4 stop/go rule** (which demotes a series to
descriptive evidence when its uncertainty diagnostics are not decisive): the
East-of-Suez spot deviation, whose placebo rank of 0.043 falls below the 0.05
reference threshold, is reportable as supplementary forecast-deviation
evidence. The West-of-Suez spot and one-year-charter deviations (ranks 0.091
and 0.087) are retained as **descriptive evidence only** and must not be
presented as significant deviations. The conformal-band exceedances do not
upgrade any series past this disposition, for the calibration reason above.

Interpretation is deliberately narrow: these are
**disruption-associated counterfactual deviations in assessed rates**, not ATT
estimates or structural causal effects. The immediately preceding 12-week means
roughly double after the cutoff, but the full-history figures show that high
freight-rate regimes also occurred in 2022-23. TTF and VLSFO are plotted as
context and excluded from the headline freight counterfactuals because they may
reflect common shocks or treatment pathways.

Strict source admission is still blocked by missing original-export,
methodology, identifier, definition-history, and rights evidence. This limits
the layer to supplementary reporting and prevents activation in the locked
working specification.

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
| Overlapping-window reference rank (not a p-value) | 0.027 |

This supports the statement: **the observed Hormuz transit collapse is far
outside the pre-treatment forecast-error distribution under the transparent
baseline models.**

## How to report the overlapping-window reference rank

Do **not** report `0.027` as a p-value. The 36 placebo
windows overlap heavily: the window length is 94 days and the step is 30 days, so
adjacent placebo windows share 64 days. A greedy non-overlap count gives only
about **9 disjoint horizon-length windows** in this historical 94-day run.

The overlapping-window reference rank is descriptive:

```text
r = (number of placebo losses >= actual loss + 1) / (number of placebos + 1)
  = 1 / 37
  = 0.027
```

Because the windows overlap, this is not an independent-sample tail probability.
Formal rank inference must use disjoint blocks. In the active 130-day run, seven
disjoint blocks give `p = 0.125`, and the nominal 95% block-conformal interval
is unbounded. The writeup also reports **separation ratios** such as actual loss
divided by placebo p95.

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

Downstream status: treatment robustness and donor-weighted synthetic control
have both been run and are included in the verified end-to-end pipeline.

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

Capacity is a **directional secondary, model-sensitive outcome**, not a second
co-primary. On the exact same 118 valid post-treatment dates, with both models
trained on `panel_aligned.csv` from 2022-01-01, the AR-only shortfall is 291.0M
and Chronos-2 gives 260.0M (−10.6%). On the exact same 130 transit dates and the
same training window, the corresponding comparison is 6,869.0 versus 6,614.9
(−3.7%). This is consistent with the heavier-tailed count × per-vessel-capacity
construction. Report direction and separation, not a precise capacity effect
magnitude.

Both percentages are conditional on that 2022-01-01 training start and must not
be quoted without it. Retraining the same two models on the full PortWatch
history from 2019-01-01 (Chronos on the trailing 2,048 days) and scoring the
identical 130 transit dates gives 7,042.3 for Chronos against 6,496.4 for AR, so
Chronos moves from 3.7% below AR to 8.4% above it. The stable quantity across all
four cells is the shortfall itself: observed Hormuz traffic is 92.5-93.0% below
counterfactual (529 observed against 7,571.3 Chronos and 7,025.4 AR under the
expanded history). The full table is generated by
`experiments/network_adaptation/specification_sensitivity.py` into
`hormuz_shortfall_specification_sensitivity.csv`.

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

Downstream status: leave-one-out spatial sensitivity and the donut treatment-
window robustness are complete. The training cutoff remains fixed at
2026-02-28; later event dates are scoring windows only.

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

## Historical full-horizon (94-day) empirical quantile bands

Updated 2026-06-17: `scripts/run_long_horizon_intervals.py` recalibrates the band
at the **true ~94-day horizon**, resolving the caveat above. Rather than
block-bootstrapping ≤30-day-fold residuals, it reuses the **placebo-in-time
windows** — each is a full 94-day pre-treatment recursive forecast, so its
cumulative gap is a realised 94-day cumulative forecast error that already
includes long-horizon recursive compounding. The descriptive band is the point
loss plus the mean-centered empirical 2.5/97.5 quantiles of those errors
(`overlapping_placebo_quantile_band`). Because the windows overlap, the band
has no nominal coverage and is not a confidence, prediction, or conformal
interval.

For `hormuz_tanker_transits`, route-only ARX:

| Statistic | ≤30-day-fold band | 94-day-horizon band |
|---|---:|---:|
| Point cumulative loss | 5,176 | 5,176 |
| Descriptive 2.5/97.5% band | 4,816 to 5,497 | 3,960 to 5,762 |
| Width | 681 | 1,801 (≈2.6× wider) |
| Excludes zero | yes | yes |

The empirical band is ~2.6× wider than the short-fold band — that gap is the
understatement the caveat warned about. Across all six model×target combinations
the descriptive band widens by 2.5–3.3×. Its endpoints are scale diagnostics,
not coverage statements.

An independent 10,000-draw circular block bootstrap now resamples the ordered
out-of-fold AR residual path in 14-day blocks. For the locked-primary AR transit
shortfall it gives **[4,649, 5,516]**, compared with the preferred
placebo-window **[3,934, 5,722]**. The cross-check is materially narrower, so the
methods do not agree on width. Report the placebo-window band descriptively and
the block-bootstrap band as method sensitivity; neither replaces disjoint-block
rank and conformal support limits.

Limitations: the placebo windows overlap (94-day windows stepped by 30 days, ~9
effectively independent), so the 2.5/97.5 quantiles are coarse, and the placebo
models train on expanding windows smaller than the actual full-pre-period model,
which widens the observed error spread. Width alone does not establish
conservative coverage.
For capacity, read the mean-daily interval columns rather than cumulative, because
valid-day counts differ (79 actual vs 94 placebo). This descriptive band
summarizes observed forecast-error dispersion only; it does not fix measurement bias, donor
contamination, or energy mediation.

## Donor-weighted synthetic control (corroboration)

Updated 2026-07-23: `scripts/run_synthetic_control.py` (helpers in
`src/lngfreight/synthetic.py`) fits a convex donor-weighted synthetic Hormuz on
the **clean donor pool** (the five rerouting corridors — Panama, Suez,
Bab-el-Mandeb, Cape of Good Hope, Gibraltar — are excluded for the same SUTVA
reason). To avoid the convex-hull problem (Hormuz is one of the largest
chokepoints and cannot be reproduced by a convex mix of smaller ones at raw
scale), every series is divided by its own pre-period mean, so the fit matches
**shape, not size**. Weights are fit by Frank-Wolfe on the simplex over the
pre-period; **pre-period RMSPE is the fit-credibility metric**. Inference is
Abadie-style: each clean donor is re-treated as a placebo and its post/pre RMSPE
ratio forms the reference distribution. The remediation-primary eligibility rule
requires placebo pre-RMSPE no greater than **2x the treated pre-RMSPE**. Results
are also reported at 1.5x, 5x, 10x, and with no screen so the interpretation does
not depend on one threshold. This is **corroboration, not the anchor estimator**
(consistent with `FALLBACK_STRATEGY.md`).

For `hormuz_tanker_transits` (`n_tanker`):

| Quantity | Value |
|---|---:|
| Clean donors in fit | 22 |
| Pre-period fit days | 1,519 |
| Pre-period RMSPE (mean-scaled units) | 0.258 |
| Post-period RMSPE | 0.840 |
| Post/pre RMSPE ratio | 3.254 |
| Remediation-primary pre-fit screen | placebo pre-RMSPE <= 2x treated |
| Eligible / total placebos | 14 / 22 (8 excluded) |
| Eligible-placebo ratio p95 | 1.502 |
| Hormuz ratio / eligible-placebo p95 | 2.166x |
| Screened rank p-value | 0.066667 (= 1/15, design floor) |
| Effective donors (1/Σw²) | 7.4 |
| Largest single weight | korea_strait (0.22) |

Interpretation: the treated pre-period fit is usable (RMSPE 0.258 on mean-scaled
units, 7.4 effective donors, no single donor dominating), and Hormuz's post/pre
RMSPE ratio exceeds every placebo that passes the 2x pre-fit screen. Across the
1.5x, 2x, 5x, 10x, and unscreened specifications, the rank p-value ranges from
0.043478 to 0.083333; the unscreened value is 0.043478. The 2x rule is the
remediation-primary convention, not evidence that the choice is uniquely
correct. The threshold grid and treated-versus-eligible-placebo gap-path figure
make that design dependence visible. This is a corroborating diagnostic
consistent with the other falsification layers, not an independent design.

Capacity (`capacity_tanker`) corroborates more weakly, as expected: fewer complete
pre-period rows (431, after artifact masking) give a noisier fit (pre-RMSPE 0.353).
Under the 2x screen, 10/22 placebos are eligible; the treated ratio is 2.379
versus an eligible-placebo p95 of 1.689 (1.408x, rank p = 0.090909, floor 1/11).
Treat the transit result as primary and capacity as supporting.

Limitations: this is a **scaled, shape-based** diagnostic, not a level effect and
not an LNG-specific freight estimate. The screened p-value remains a small-N
design floor, eligibility depends on a threshold convention, and retained
placebos can still be cross-sectionally dependent. Report eligible counts,
threshold sensitivity, and ratio/p95 separation alongside the rank. Mean-scaling
assumes a stable pre-period level, and the clean-donor pool, while
contamination-screened, is still an imperfect control set.

## Romano-Wolf multiplicity correction

Updated 2026-06-20: `scripts/run_multiplicity_correction.py` applies a
studentized Romano-Wolf max-statistic step-down to placebo families for which
joint null draws are genuinely aligned. The placebo-in-time family contains 8
generator-by-outcome hypotheses over seven shared disjoint time blocks; its
adjusted p-values remain at the finite-design floor, 0.125. The low-contamination spatial
family contains 2 outcomes over the 21 donors with complete joint statistics;
both adjusted p-values are 0.045. These are still small-sample design floors and
must be reported as corrected cross-outcome values rather than the earlier
per-outcome 0.037-0.048 range.

The output is `data/processed/romano_wolf_stepdown.csv`, with family size and
joint-resample count on every row. Inference layers with incompatible resampling
units are not pooled by independently shuffling placebo columns, because that
would invent rather than preserve their dependence structure. Corrections are
therefore within-axis, matching the reporting rule in
`ADVANCED_ML_RECONSIDERATION.md`.

## Still not covered by any inference layer

The placebo (time and space), synthetic-control, and interval layers establish
that the Hormuz gap is far outside the model's normal forecast-error behavior.
They do **not** establish the *magnitude* as a clean causal effect, because they
do not resolve:

- Treatment-correlated measurement error (AIS dark activity, GPS jamming,
  spoofing) — the observed collapse is partly true halt, partly reduced
  observability. Under the stated one-sided undercount assumption, the loss is a
  **conditional upper bound** on the true reduction; without an admitted
  dark-rate series, no empirical lower bound is identified.
- Panama/donor contamination and SUTVA violations from rerouting (screened, not
  eliminated).
- Energy-price mediation under route+energy ARX.

Long-horizon recursive uncertainty, previously listed here, is now addressed by
the 94-day-horizon interval section above. No further inference-robustness
increment is queued; remaining work is freight-specific and gated on Spark/
Bloomberg access.
