# PortWatch panel bake-off: executed result

Date: 2026-08-29

## Bottom line

The technical benchmark rejects two opposite claims:

1. It rejects the claim that the existing AR(1,7) pipeline was already as
   predictive as a modern foundation model. Chronos-2 improves pre-event
   forecasts across the global panel at both horizons, but by different margins
   and with different confidence. At 30 days the improvement is substantial and
   firmly bounded away from zero: macro MASE falls 17.6%, clustered 95% interval
   [11.4%, 25.0%]. At 130 days it falls 14.5% with a clustered interval of
   [1.4%, 23.7%] — still positive, but the lower bound is close to zero. **130
   days is the horizon the event analysis uses**, so that is the weaker of the
   two claims and the one that must be quoted when the forecasting result is
   used to license the event work.
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

The donor-assisted league never leaves this file. No event-window result in this
project uses synthetic control, IFE or nuclear-norm completion; both event
experiments are forecast-only, which is claimed as a design property in section
3.1 of `docs/NETWORK_ADAPTATION_SECONDARY_CHAPTER.md`. The admission decisions
below are point-estimate gates and contribute no p-values to the project-level
decision surface, which is counted once in section 4.1 of the same document.

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

### What the admission rule gates

Every gate in `admission_rule.json` is a **point estimate**: macro mean MASE
reduction of at least 0.05 at each horizon, paired win rate above 0.50, common
95% coverage error at most 0.05, and interval width ratio at most 1.10 against
the baseline. The clustered bootstrap intervals and the
`cluster_bootstrap_probability_meets_threshold` column are an uncertainty
diagnostic that the rule never referenced. A figure such as 94.7% is therefore
not a near-miss against a threshold — it was not measured against one — and no
admission decision in this file turns on it.

### Chronos versus AR(1,7): admitted

- Univariate Chronos reduces macro MASE by 17.6% at 30 days and 14.5% at
  130 days, winning 72.4% and 74.1% of matched unit-windows.
- The clustered 95% reduction intervals are [11.4%, 25.0%] at 30 days and
  [1.4%, 23.7%] at 130 days. The 130-day improvement is clearly positive, but
  its interval is roughly twice as wide and nearly reaches zero, so
  "substantially improves forecasting" is a 30-day statement. The 130-day
  statement is "improves forecasting, with wide uncertainty" — and 130 days is
  the horizon the event window uses.
- The 130-day lower confidence bound does not establish the frozen 5%
  materiality threshold at 95% confidence; 94.7% of bootstrap draws exceed 5%.
  Both are uncertainty diagnostics, not gates — the rule is point-estimate based
  and the 130-day point reduction of 14.5% clears 0.05 outright.
- Improvements are positive for every vessel class at both horizons. At
  30 days Chronos beats AR at all eight origin-level macro averages. At 130
  days it loses at one of eight origins, and that loss is traceable to a single
  corridor: at origin 4 (2024-01-26) the macro reduction is −6.5% across all 140
  series and **+16.6% excluding the Cape of Good Hope's five series**. Chronos
  read the December 2023 Red Sea diversion ramp as a trend and extrapolated it;
  the worst cell in the bake-off is Cape Ro-Ro there, MASE 28.9 against AR's 2.0.
  See `experiments/network_adaptation/cape_residual_drift.py`. This is a
  regime-break failure mode worth reporting, not a general long-horizon weakness.
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
- Substantively, the old result remains: the shock is so large that better
  normal-regime forecasting does not change the basic conclusion. The
  model-versus-model *comparison* behind that statement, however, is
  specification-dependent and has to be reported as such.

### Specification sensitivity of the Hormuz shortfall

Both runs score the identical 130 days and the identical 529 observed transits.
They differ only in how much training history each forecaster sees.

| Specification | Training start | Chronos shortfall | AR shortfall | Model difference |
|---|---|---:|---:|---|
| Legacy | 2022-01-01 | 6,615 | 6,869 | Chronos 3.7% below |
| Expanded history | 2019-01-01 (Chronos: trailing 2,048d) | 7,042 | 6,496 | Chronos 8.4% above |

The sign of the difference reverses, so "the two models agree to within 3.7%" is
a property of the legacy training window, not of the models. The quantity that is
stable across both specifications is the one the conclusion rests on: **observed
Hormuz traffic is 92.5-93.0% below counterfactual** on those 130 days (529
observed against 7,571 under Chronos and 7,025 under AR in the expanded-history
run). Both rows are generated by
`experiments/network_adaptation/specification_sensitivity.py` into
`hormuz_shortfall_specification_sensitivity.csv`; neither is typed by hand.

Signal dominance can become an academically interesting *result* only if the
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

## Pretraining-overlap risk, bounded

Chronos-2 was released 2025-10-20, so nothing dated after that can be in its
weights. The **event window (2026-02-28 to 2026-07-07) is therefore provably
outside the pretraining corpus** and the shortfall estimate carries no overlap
risk at all. The generalisable claim — that Chronos forecasts this panel better
than AR — does carry it, because it rests on eight rolling origins whose scored
windows run 2023-01-01 to 2025-11-05, almost entirely before the release.

If overlap were producing the advantage, the advantage should be largest at the
origins with the most opportunity for it — the early ones, whose observations had
years to reach a pretraining corpus — and should fade toward the release date. It
does not:

| Origin | Scored window ends | 30d reduction | 130d reduction | 130d win rate |
|---|---|---:|---:|---:|
| 1 (2023-01-01) | 2023-05-10 | 16.3% | 16.2% | 72.9% |
| 2 (2023-05-11) | 2023-09-17 | 16.4% | 14.8% | 69.3% |
| 3 (2023-09-18) | 2024-01-25 | 12.9% | 14.3% | 77.1% |
| 4 (2024-01-26) | 2024-06-03 | 21.4% | **−6.5%** | 67.1% |
| 5 (2024-06-04) | 2024-10-11 | 23.8% | 20.0% | 73.6% |
| 6 (2024-10-12) | 2025-02-18 | 17.0% | 20.6% | 77.1% |
| 7 (2025-02-19) | 2025-06-28 | 16.4% | 20.2% | 74.3% |
| **8 (2025-06-29)** | **2025-11-05** | **16.4%** | **16.7%** | **81.4%** |

Origin 8 is the latest and the only one whose window reaches past the release
date at all (16 of its 130 days). Its advantage is positive at both horizons with
clustered 95% intervals that exclude zero — [11.5%, 21.2%] at 30 days and
[10.8%, 22.3%] at 130 days — and its 130-day win rate is the highest of the
eight. Against the other seven pooled, the difference is −1.3 points at 30 days
and +2.5 points at 130 days, with 95% intervals of [−6.5, +3.1] and [−6.6, +19.3]
points: no detectable difference in either direction. The fitted trend across
origins is *positive* at both horizons, the opposite of the decay a
contamination-driven advantage would produce.

The confound runs the same way. Chronos's context length grows with the origin
and caps at 2,048 days from origin 6, so later origins get more context — which
would flatter them, not the early ones the contamination story needs.

**What this does and does not establish.** It bounds the risk: a contamination
story has to explain why the advantage is no larger where overlap was most
likely. It does not prove a clean corpus, because Amazon's disclosure is not
detailed enough for absence to be verified, and because "latest origin" is a
proxy for "least ingested," not a clean/dirty split — seven of eight windows
close before the release and the eighth mostly does. Generated by
`experiments/panel_bakeoff/pretraining_contamination.py` into
`chronos_by_origin_advantage.csv` and `chronos_pretraining_contamination.json`.

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

