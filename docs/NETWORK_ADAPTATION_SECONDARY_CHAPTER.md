# Secondary analysis: selective maritime-network adaptation after the Hormuz disruption

## Empirical status and claim boundary

This chapter reports an executed exploratory analysis. All forecasts, bootstrap
draws and robustness checks described below were generated from the pinned IMF
PortWatch snapshot. The analysis supports a claim about **positive abnormal
tanker activity compatible with network adaptation or alternative-source
substitution**. It does not identify physical rerouting, displaced Hormuz
volume, an LNG-specific response or a causal treatment effect.

The five-corridor analysis set is a retrospective restriction, not a
preregistration. An earlier all-corridor AR analysis had already exposed
post-event results, including positive deviations at the Cape of Good Hope,
Panama Canal and Yucatan Channel. The resampling p-values below are therefore
descriptive measures of separation from historical forecast errors; they must
not be presented as confirmatory discoveries selected independently of the
data.

## 1. Research question and contribution

The primary throughput analysis asks how far observed tanker traffic at the
Strait of Hormuz fell below a normal-conditions counterfactual. That result is
important for measurement, but its direction is mechanically unsurprising.
This secondary analysis asks a less direct question:

> During the 130 days following 28 February 2026, did selected non-Hormuz
> maritime corridors exhibit positive tanker-count deviations relative to
> leakage-safe counterfactual forecasts, and were those deviations specific to
> tankers rather than common to unrelated vessel classes?

The broad empirical territory is not empty. Yang et al. (2026) use Sentinel-1
synthetic-aperture radar to examine shipping reorganization during the same
crisis and report an approximately 30% increase in traffic around the Cape of
Good Hope. Their comparison covers 28 February–27 March and has the major
advantage of not relying on cooperative AIS transmission. The present analysis
does not claim to discover rerouting first. Its narrower addition is a 130-day,
multi-corridor counterfactual design that compares an admitted time-series
foundation model with a transparent autoregression, calibrates the network
statistics on genuinely out-of-sample historical forecast errors, and subjects
the apparent tanker signal to vessel-class negative controls.

This distinction is substantive. A model that forecasts normal operations more
accurately may add little to the estimated magnitude of an overwhelming closure,
yet still matter for detecting weaker secondary adjustments elsewhere in the
network.

## 2. Data and measurement

The data are the pinned IMF PortWatch `Daily_Chokepoints_Data` snapshot
(SHA-256 `66f3a54a...93f579d`). It contains a complete daily grid of 28
chokepoints from 1 January 2019 through 12 July 2026: 77,000 unique
chokepoint-day observations, with no duplicate keys or missing values in the
three outcomes used here. PortWatch derives maritime indicators from AIS data
provided through the United Nations Global Platform. The IMF documentation
notes both the value of daily coverage and limitations arising from reception,
coverage and methodological revisions.

The primary outcome is `n_tanker`, the daily number of tanker transits. It is
stationary enough for the forecasting geometry used here according to the
separate panel diagnostics, but it aggregates tanker types. It is neither an LNG
carrier count nor a cargo-volume measure.

The event window begins at the operational cutoff of 28 February 2026 and ends
on 7 July 2026, giving exactly 130 daily observations. Five non-Hormuz corridors
form the restricted tanker family:

| Corridor | Ex-ante economic role used for interpretation |
|---|---|
| Cape of Good Hope | Atlantic–Indian Ocean long-haul and supply-reorganization screen |
| Malacca Strait | Asia-bound energy gateway and destination-side screen |
| Gibraltar Strait | Atlantic–Mediterranean and European alternative-supply screen |
| Panama Canal | Americas-to-Pacific fleet-deployment and alternative-supply screen |
| Yucatan Channel | US Gulf/Caribbean export-gateway screen |

Strait of Hormuz, Suez Canal and Bab el-Mandeb are retained as descriptive
context series. They are not donors: Hormuz is the disruption anchor, while Suez
and Bab el-Mandeb may be affected by concurrent regional shocks. Ro-Ro
(`n_roro`) and dry-bulk (`n_dry_bulk`) activity at the same five candidate
corridors constitute a ten-series negative-control family. A positive result in
those controls would weaken a tanker-specific interpretation; a null control
cannot, by itself, prove the tanker mechanism.

## 3. Counterfactual models

The primary forecaster is the frozen univariate Chronos-2 model, revision
`29ec3766...50e8498c`, used zero-shot with a maximum 2,048-day context and no
cross-series learning. Chronos-2 was chosen before this extension because the
global 28-by-5 panel bake-off found that it reduced 130-day MASE by 14.5% relative
to AR(1,7), with positive gains across every vessel class. The recursive AR(1,7)
model, using lags one and seven, remains the transparent robustness benchmark.
Neither model observes contemporaneous post-cutoff donor outcomes.

For model (m), corridor (i) and day (t), define the forecast residual as

\[
e^{(m)}_{it}=y_{it}-\widehat y^{(m)}_{it}.
\]

The corridor statistic is the mean 130-day residual scaled by that corridor's
own pre-event mean:

\[
D^{(m)}_i=
\frac{H^{-1}\sum_{t=1}^{H}e^{(m)}_{it}}
{\bar y_{i,\mathrm{pre}}}, \qquad H=130.
\]

Positive values denote above-counterfactual activity. Scaling permits
comparison across corridors with different traffic levels. It does not convert
the statistics into reallocatable shares: the same voyage may cross multiple
chokepoints, so corridor gaps must never be summed as displaced traffic.

## 4. Dependence-aware historical reference

Normal-theory standard errors based on
\(\widehat\sigma\sqrt{H}\) would incorrectly treat daily residuals as
independent. Instead, the analysis reuses the executed bake-off's genuinely
out-of-sample 130-day residuals. Eight common, disjoint rolling origins cover
1,040 consecutive pre-event dates from 1 January 2023 through 5 November 2025.
No calibration date reaches the event cutoff.

The primary reference distribution uses 10,000 synchronized circular
moving-block draws with 14-day blocks. Within each draw, identical time indices
are selected for every corridor and vessel class. This preserves short-run
serial dependence as well as contemporaneous cross-corridor dependence. Seven-
and 28-day blocks test sensitivity to the dependence horizon. These are
historical forecast-error reference distributions, not causal confidence
intervals.

Inference proceeds in two stages. First, an equally weighted global statistic
averages the five scaled tanker deviations. Second, corridor-level one-sided
tests use the Romano–Wolf step-down procedure within the five-corridor family.
The resampling distribution is studentized and centered on each model's
historical forecasting bias. The ten negative controls form a separate
Romano–Wolf family. Using separate families is justified by their distinct role:
the first screens the proposed mechanism, while the second attempts to falsify
its vessel-class specificity.

## 5. Results

### 5.1 Global adaptation screen

The Chronos-based global tanker statistic is 0.107. Its historical reference
distribution has mean −0.039 and a 95% range from −0.174 to 0.032. The one-sided
bootstrap separation measure is 0.0001. The corresponding AR statistic is
larger at 0.216, but AR has a positive historical bias for this corridor set: its
reference mean is 0.111 and its 95% range is 0.074–0.147. The event remains
outside that range, again with a bootstrap separation measure of 0.0001.

| Model | Event global statistic | Historical mean | Historical 95% reference | Bootstrap p |
|---|---:|---:|---:|---:|
| Chronos-2 | 0.107 | −0.039 | [−0.174, 0.032] | 0.0001 |
| AR(1,7) | 0.216 | 0.111 | [0.074, 0.147] | 0.0001 |

This establishes that the restricted set is collectively more positive than
the models' own historical long-horizon errors. It does not establish that the
additional observations are vessels displaced from Hormuz.

### 5.2 Corridor heterogeneity

The global result is not a uniform network increase. Under the primary Chronos
model, Cape of Good Hope, Panama Canal and Yucatan Channel are above
counterfactual; Malacca and Gibraltar are below it.

| Corridor | Chronos scaled deviation | Chronos cumulative gap | Chronos RW p | AR scaled deviation | AR cumulative gap | AR RW p |
|---|---:|---:|---:|---:|---:|---:|
| Cape of Good Hope | 0.435 | +732 | 0.0285 | 0.551 | +928 | 0.0067 |
| Panama Canal | 0.172 | +277 | 0.0002 | 0.212 | +340 | 0.0001 |
| Yucatan Channel | 0.215 | +646 | 0.0001 | 0.333 | +999 | 0.0001 |
| Gibraltar Strait | −0.118 | −662 | 1.0000 | 0.042 | +234 | 1.0000 |
| Malacca Strait | −0.170 | −1,670 | 1.0000 | −0.060 | −587 | 1.0000 |

The two models agree on the sign for four of five corridors. Their only sign
disagreement is Gibraltar, where neither model finds a positive anomaly after
multiplicity correction. The strongest model-robust findings are Panama and
Yucatan. Both remain below adjusted p=0.003 under 7-, 14- and 28-day block
lengths. The Cape result is weaker: its Chronos adjusted value moves from 0.0032
to 0.0285 and then 0.0974 as the block length increases. Cape should therefore
be described as directionally corroborative and dependence-sensitive, not as
equally robust evidence.

![Event statistics and historical reference ranges](../reports/figures/network_adaptation_counterfactuals.png)

*Figure: Points show the 130-day event statistic. Grey segments show the central
95% of synchronized 14-day block-bootstrap historical forecast errors. These
segments are reference ranges, not causal confidence intervals. Both panels use
the same horizontal scale.*

### 5.3 Negative controls

The primary Chronos model passes the planned specificity check. Its global
Ro-Ro/dry-bulk statistic is 0.027 compared with a broad historical reference
range of −0.802 to 0.089; the one-sided bootstrap value is 0.337. None of the ten
individual controls has a Romano–Wolf adjusted value below 0.05.

AR does not pass the same check. Its control-family statistic is 0.198 against a
historical range of 0.061–0.166, with p=0.0007, and Cape Ro-Ro is individually
flagged after correction (adjusted p=0.0127). This does not prove that Chronos
has identified tanker substitution. It shows that the AR network anomaly is
partly shared by non-tanker activity, while the Chronos result is more
vessel-class-specific. That distinction is precisely where the advanced model
adds empirical value: not by making the obvious Hormuz collapse larger, but by
reducing ambiguity in weaker secondary signals.

### 5.4 Context series

The context series further reject a blanket global-growth interpretation.
Hormuz is extremely negative under both models (Chronos −1.001; AR −0.924).
Suez is also below counterfactual (−0.106 and −0.069). Bab el-Mandeb is close to
zero under Chronos (+0.036) and negative under AR (−0.181). The combination of a
severe origin shock, weakness in the Red Sea/Suez context and positive anomalies
at selected western-hemisphere and Cape corridors is compatible with selective
network adjustment, but the aggregate data cannot determine its exact route or
cargo mechanism.

## 6. Interpretation and relation to the ML question

The findings do not support the simple statement that traffic was rerouted
everywhere. Two of the five candidate corridors are not positive, and the Cape
result is sensitive to conservative dependence assumptions. The evidence is
better summarized as a concentrated, tanker-specific anomaly at Panama and
Yucatan, with weaker corroboration at the Cape.

This produces a more useful answer to the thesis's over-engineering concern.
For the massive Hormuz shortfall, Chronos and AR reach substantively similar
conclusions because the signal dominates model error. For secondary network
effects, model quality matters: the AR result is larger but fails the
non-tanker falsification test, whereas Chronos yields a smaller and more
selective anomaly. The foundation model is therefore justified as a measurement
tool for subtle propagation, not as decoration around an obvious first-order
effect.

The same result also imposes restraint. Because the corridor set was restricted
after earlier post-event inspection, it cannot by itself serve as a clean
confirmatory test. The defensible contribution is methodological and
descriptive: it demonstrates how model benchmarking, joint dependence-aware
resampling and negative controls change the credibility of a maritime-network
anomaly claim.

## 7. Limitations

1. **Retrospective restriction.** The analysis set was frozen after post-event AR
   results existed. Adjusted p-values quantify historical separation but do not
   erase selection risk.
2. **No vessel linkage.** PortWatch does not identify individual voyages,
   origins or destinations in this panel. No positive gap can be matched to a
   missing Hormuz voyage.
3. **No LNG class.** `n_tanker` includes multiple tanker types. Any LNG-specific
   interpretation requires vessel-level classification or another source.
4. **Non-additivity.** Chokepoint counts overlap along routes. Cumulative gaps
   cannot be summed into a global displaced-volume estimate.
5. **Concurrent shocks.** Red Sea insecurity, port constraints, commodity
   demand and seasonal fleet deployment may affect the same corridors.
6. **Bootstrap assumptions.** Moving-block inference assumes that pre-event OOS
   forecast residuals supply an informative weakly stationary reference for the
   event window. Block-length sensitivity helps, but cannot verify that
   assumption.
7. **AIS observation process.** Reception gaps, dark activity and subsequent
   PortWatch revisions remain possible. SAR is an important independent
   corroboration channel.
8. **Foundation-model provenance.** The run is inference-only and uses a pinned
   open checkpoint, but absence of every possible transformed PortWatch series
   from pretraining cannot be proven from the public model disclosure.

## 8. Conclusion

The 130-day analysis finds a selective positive tanker-count pattern at Cape of
Good Hope, Panama Canal and Yucatan Channel rather than a universal increase
across candidate corridors. Panama and Yucatan are robust to both model choice
and block-length sensitivity; Cape is positive under both models but becomes
inferentially fragile under 28-day blocks. The primary Chronos result is not
replicated in Ro-Ro or dry-bulk controls, whereas the AR result is, making
Chronos the more credible detector of the secondary pattern.

The appropriate conclusion is therefore narrow: the PortWatch panel contains
evidence compatible with selective tanker-network adaptation after the Hormuz
disruption. It does not reveal where the vessels originated, what they carried,
or whether they physically replaced Hormuz flows. Vessel-level origin–destination
data or additional SAR analysis would be required to move from anomaly detection
to mechanism attribution.

## Reproducibility

```bash
.venv-bench/bin/python -m experiments.network_adaptation.run_event_forecasts
MPLBACKEND=Agg MPLCONFIGDIR=/private/tmp/thesis-network-adaptation-mpl \
  .venv/bin/python -m experiments.network_adaptation.analyze
.venv/bin/python -m pytest -q tests/test_network_adaptation.py
```

The configuration, code, model revision, data hash, generated-file hashes and
validation caveats are recorded in `config/network_adaptation.yaml` and
`experiments/network_adaptation/outputs/network_adaptation_manifest.json`.

## References used for this chapter boundary

- Ansari, A. F. et al. (2025). *Chronos-2: From Univariate to Universal
  Forecasting*. [arXiv:2510.15821](https://arxiv.org/abs/2510.15821).
- Arslanalp, S., Koepke, R. and Verschuur, J. (2025). *Nowcasting Global Trade
  from Space*. IMF Working Paper 25/93.
  [IMF publication](https://www.elibrary.imf.org/abstract/journals/001/2025/093/article-A001-en.xml).
- Künsch, H. R. (1989). *The Jackknife and the Bootstrap for General Stationary
  Observations*. *The Annals of Statistics*, 17(3), 1217–1241.
  [DOI: 10.1214/aos/1176347265](https://doi.org/10.1214/aos/1176347265).
- Romano, J. P. and Wolf, M. (2005). *Stepwise Multiple Testing as Formalized
  Data Snooping*. *Econometrica*, 73(4), 1237–1282.
  [DOI: 10.1111/j.1468-0262.2005.00615.x](https://doi.org/10.1111/j.1468-0262.2005.00615.x).
- Yang, H. et al. (2026). *SAR-based monitoring of shipping reorganization under
  a maritime chokepoint disruption: Evidence from the Strait of Hormuz crisis*.
  *Ocean & Coastal Management*, 279, 108265.
  [DOI: 10.1016/j.ocecoaman.2026.108265](https://doi.org/10.1016/j.ocecoaman.2026.108265).
