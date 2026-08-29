# PortWatch panel bake-off: executed result

Date: 2026-08-29

## Bottom line

The technical benchmark rejects two opposite claims:

1. It rejects the claim that the existing AR(1,7) pipeline was already as
   predictive as a modern foundation model. Chronos-2 materially improves
   pre-event forecasts across the global panel.
2. It also rejects the claim that adding every available layer is useful.
   Multivariate Chronos is not consistently better than univariate Chronos, and
   neither Interactive Fixed Effects nor nuclear-norm completion clears the
   frozen admission rule against ordinary synthetic control.

The recommended technical core is therefore **univariate Chronos-2 as the
accuracy model, AR(1,7) as the transparent baseline, and the donor models as
sensitivity analyses**. This closes the technical-option question, but it does
not by itself solve the thesis's academic-triviality problem. A better estimate
of an obvious physical collapse remains an obvious physical collapse.

## Geometry correction

The advertised 28 x 6 panel does not exist as six independent vessel classes.
PortWatch has five mutually exclusive classes:

- container
- dry bulk
- general cargo
- Ro-Ro
- tanker

`n_cargo` is exactly the first four summed, and `n_total` is exactly all five
summed on every one of the 77,000 rows. Including either aggregate as a sixth
row family would create an exact linear dependency and artificially help a
low-rank estimator. The benchmark therefore uses a 28 x 5 composition panel
(140 series) and evaluates total transits separately as a 28-series robustness
outcome.

The standardized composition matrix is not naturally very low rank: 108
components are needed for 90% of singular-value energy and its entropy effective
rank is 133.5 out of 140. This makes matrix completion a genuine test rather
than a designed success.

## Frozen evaluation

- Eight origins, 130 days apart, beginning 2023-01-01.
- Both 30-day and 130-day horizons at each origin.
- All scoring ends before the 2026-02-28 event cutoff.
- A separate 2022 block selects IFE rank and nuclear-norm penalty once.
- Complete chokepoints, including all five classes, are spatially masked
  together for donor-assisted methods.
- MASE and bias are macro-averaged over unit-series.
- Common 95% intervals use lead-specific standardized errors from earlier outer
  folds only. Coverage is an empirical spatial-pooling diagnostic, not a formal
  exchangeability guarantee.
- Uncertainty in paired error reductions uses 5,000 bootstrap draws that
  resample chokepoints and origins.

Forecast-only and donor-assisted methods are reported in separate leagues.
Synthetic control, IFE, and matrix completion observe contemporaneous spatial
donors; seasonal naive, AR, and Chronos do not.

## Primary composition-panel performance

| Model | Information set | 30d MASE | 130d MASE | 30d abs. bias | 130d abs. bias | Common 95% coverage (30/130) |
|---|---|---:|---:|---:|---:|---:|
| Seasonal naive | past only | 0.989 | 1.029 | 0.321 | 0.367 | 95.6% / 95.4% |
| AR(1,7) | past only | 0.878 | 0.918 | 0.408 | 0.418 | 95.3% / 95.1% |
| Chronos-2 univariate | past only | **0.724** | 0.785 | **0.240** | 0.289 | 95.5% / 95.3% |
| Chronos-2 multivariate | past only | 0.725 | **0.762** | 0.245 | **0.264** | 95.7% / 95.4% |
| Synthetic control | current spatial donors | 0.904 | 0.918 | 0.393 | 0.366 | 94.7% / 94.8% |
| IFE, selected rank 1 | current spatial donors | **0.864** | 0.878 | **0.365** | 0.340 | 94.7% / 94.8% |
| Nuclear-norm MC | current spatial donors | 0.870 | **0.871** | 0.380 | **0.330** | 95.1% / 95.2% |

Bias is the absolute mean signed error divided by the training seasonal-naive
scale. The two leagues are not directly ranked because they have different
post-origin information.

Chronos-2's own native 95% intervals cover 95.8%/96.0% for univariate and
95.4%/95.8% for multivariate forecasts. The common conformal intervals are also
about 8% narrower than AR's on the same scaled-width definition.

## Paired decisions

### Chronos versus AR(1,7): admitted

- Univariate Chronos reduces macro MASE by 17.6% at 30 days and 14.5% at
  130 days, winning 72.4% and 74.1% of matched unit-windows.
- The clustered 95% reduction intervals are [11.4%, 25.0%] and [1.4%, 23.7%].
  The 130-day improvement is clearly positive, although the lower confidence
  bound does not establish the frozen 5% materiality threshold at 95%
  confidence; 94.7% of bootstrap draws exceed 5%.
- Improvements are positive for every vessel class at both horizons. At
  30 days Chronos beats AR at all eight origin-level macro averages. At 130
  days it loses at one of eight origins.
- Multivariate Chronos reduces MASE versus AR by 17.5% and 17.1%; both clustered
  intervals remain above 10%, and it improves at all eight origins at both
  horizons.

### Multivariate versus univariate Chronos: not admitted

Multivariate Chronos is 0.18% worse at 30 days and 3.04% better at 130 days.
It fails the rule requiring improvement at both horizons. Its long-horizon
stability is worth reporting as a sensitivity, but the aggregate evidence does
not justify making it the default architecture.

### Latent-factor methods versus synthetic control: not admitted

- IFE improves on synthetic control by 4.43% and 4.38%, below the 5% rule at
  both horizons.
- Nuclear-norm completion improves by 3.75% and 5.10%, passing only the
  130-day cell.
- Rank 1 was selected for IFE on both calibration horizons. Nuclear-norm
  completion retained many dimensions (about 13 at the selected 30-day penalty
  and 62 at 130 days), consistent with the panel's weak low-rank geometry.

This is not a matrix-completion failure caused by omitting a fair comparator:
regularized completion and Bai-style hard-rank IFE were both run, and neither
earned a primary role.

## Stationarity and random-walk risk

The count panel does not resemble a price random walk under diagnostics tied to
the model geometry:

- An approximate ADF regression with an intercept, weekday controls, and seven
  lagged differences rejects a unit root at the conventional 5% critical value
  for all 140 composition series and all 28 total series.
- The fitted AR(1,7) companion spectral radius has median 0.755 and maximum
  0.969 for the composition panel; none is at or above 0.995. For totals, the
  median is 0.822 and maximum 0.974.

These are diagnostics, not proof of global stationarity: structural breaks and
measurement revisions still matter. They do rule out the immediate concern
that the benchmark's advantage is merely an AR mean-reversion artifact applied
to near-unit-root levels.

## What this says about the over-engineering problem

The problem is **partly, not fully, closed**.

- Technically, the safe AR choice left substantial forecast accuracy unused.
  The executed global-panel result is much stronger evidence than the old
  single-Hormuz comparison.
- Architecturally, further complexity is mostly unnecessary. The simple
  univariate foundation model captures almost all of the defensible gain.
- Substantively, the old result remains: the 130-day Hormuz tanker-transit
  shortfall is 6,615 under Chronos and 6,869 under AR, only 3.7% apart. The shock
  is so large that better normal-regime forecasting does not change the basic
  conclusion.

That last fact can become an academically interesting *result* only if the
literature supports the question: when does forecast sophistication alter
disruption inference, and when does signal dominance make model complexity
irrelevant? It cannot yet be called the thesis gap.

## Literature constraint before narrative selection

The broad claim “Chronos is a strong transportation baseline” is already in the
2026 literature. Pulido and Rodrigues benchmark Chronos-2 on ten highway,
urban-speed, bike, and EV datasets and argue TSFMs should become standard
transportation baselines. The plausible remaining scope is narrower: maritime
chokepoint telemetry, long 30/130-day horizons, donor-assisted counterfactuals,
and the gap between predictive gains and disruption-estimate sensitivity. A
systematic literature review must establish whether that combination is novel
before the thesis is framed around it.

Chronos-2's model card discloses training from subsets of Chronos Datasets,
GIFT-Eval Pretrain, and synthetic data. PortWatch is not named in the disclosed
sources, but exact absence from all transformed pretraining data has not been
proven. The result should therefore be described as inference-only/zero-shot,
with pretraining-overlap risk acknowledged rather than dismissed.

## Recommended next action

Stop adding architectures. The next phase should be a focused literature review
and scope decision with three candidate questions:

1. **Forecast benchmark:** Do zero-shot TSFMs improve long-horizon forecasting
   of global maritime chokepoint flows over transparent and spatial baselines?
2. **Inference robustness:** Does better pre-event forecasting materially alter
   estimated disruption shortfalls, or do large shocks dominate estimator
   choice?
3. **Network adaptation:** Can model residuals reveal cross-corridor or
   cross-vessel-class substitution after disruption, which is less trivial than
   documenting the treated corridor's collapse?

Question 3 has the most substantive tension but needs a defensible operational
definition and literature support before another dataset or model is built.

## Reproducibility

The raw PortWatch snapshot hash is
`66f3a54afb042103f3e0afc9670568cb7be245394ec04eba55ebd158593f579d`.
The run produced 18,368 unit-window score rows and 1,469,440 daily predictions,
with zero duplicate keys and zero disagreement in observed outcomes across
models. Five isolated benchmark tests pass. The broader repository remains
polluted and was not treated as a clean release artifact.

Primary source links:

- Chronos-2 paper: https://arxiv.org/abs/2510.15821
- Chronos-2 model card and training-data disclosure:
  https://huggingface.co/amazon/chronos-2
- Transportation TSFM benchmark: https://arxiv.org/abs/2602.24238

