# Foundation-model selection for the corridor-transmission layer

**Status:** Decision note, 2026-06-21. For supervisor review (Prof. Li). Selects
the time-series foundation models for the basin/corridor throughput-transmission
extension. Does **not** change the locked AR-only primary estimator or the
estimand; foundation models serve the descriptive transmission map and the
benchmark gate only (CLAUDE.md rule 2: prediction ≠ identification).

## What the new layer needs from a model

The transmission layer forecasts counterfactual daily throughput for ~28
PortWatch chokepoints, groups them by basin, and maps each corridor's signed
**above- or below-counterfactual throughput deviation** over the post window.
The map describes deviations only; it does not assert that traffic flowed from
one corridor to another. Hard requirements:

1. **Probabilistic output** — the map needs intervals, not point forecasts, so
   corridor deviations carry uncertainty.
2. **Leakage-safe, pre-cutoff-only** — counterfactual generators train strictly
   before `2026-02-28` and must not consume post-treatment values of *other*
   corridors (the SUTVA contamination that already forces AR-only, not ARX, as
   the Hormuz primary).
3. **Per-series scale robustness** — corridors differ by orders of magnitude in
   absolute throughput; the model must normalise per series.
4. **Licence-compatible with academic use + CPU-feasible + version-pinnable** —
   record the code and checkpoint licences separately, preserve attribution and
   non-commercial restrictions, and verify panel-scale runtime before admission
   (CLAUDE.md rules 5, 7).

## Candidates (verified from primary sources, June 2026)

| Model | Released | Params | Checkpoint licence | Probabilistic | Multivariate / covariates | Documented / tested context |
|---|---|---|---|---|---|---|
| **Chronos-2** (`amazon/chronos-2`) | 20 Oct 2025 | 120M | Apache-2.0 | Arbitrary requested quantile levels in the tested adapter | **Native** univariate + multivariate + covariate, in-context | No hard numeric limit claimed here; ~1,500 tested locally |
| **TimesFM 2.5** (`google/timesfm-2.5-200m-pytorch`) | 15 Sep 2025 (covariates 29 Oct 2025) | 200M | Apache-2.0 | Fixed decile quantile grid in the tested adapter (80% widest central band) | Univariate; covariates via XReg | Up to **16,384**; ~1,500 used locally |
| **Moirai 2.0** (`Salesforce/moirai-2.0-R-small`) | Aug–Nov 2025 | small | **CC-BY-NC-4.0** | Fixed decile quantile head (80% widest central band) | Dynamic real covariates supported by GluonTS; disabled in our adapter | 1,680 in the official example; ~1,500 tested locally |

Licence boundary: the **Uni2TS code repository** is Apache-2.0, but the Moirai
2.0 checkpoint is CC-BY-NC-4.0. The checkpoint is therefore an academic,
non-commercial cross-check only. Record its attribution and use restriction in
the manifest and verify the licence before distributing the checkpoint or using
it outside this research setting; it must not be described as an Apache-licensed
model.

Benchmark context: Chronos-2 reports best-among-pretrained on GIFT-Eval,
fev-bench and Chronos Benchmark II, with the largest margins on covariate tasks.
Disclosure: the GIFT-Eval leaderboard is maintained by the Moirai authors
(Salesforce), so it is not cited here as a neutral ranking of their own model.

## Recommendation

The justification rests on **our own pre-cutoff validation**, not release date or
any external leaderboard. External benchmarks (GIFT-Eval, fev-bench) and recency
motivate which models to *test*; they do not select the anchor. Selection is by
local rolling-origin MASE and interval calibration on strictly pre-`2026-02-28`
folds.

- **Anchor: Chronos-2 — on calibration.** In our existing tsfm benchmark
  Chronos-2 is the best-calibrated admitted model and holds strong (not always
  first) MASE. Calibration is decisive here because the deliverable is an
  interval map, and it is already the default in
  `scripts/run_tsfm_counterfactual.py`. **Caveat to state plainly:** TimesFM
  slightly wins *transit* MASE locally, so Chronos-2 is not "universally best" —
  it is the best-calibrated, which is the property this layer needs.
- **Cross-checks: TimesFM 2.5 and Moirai 2.0.** TimesFM 2.5 earns its place on
  local transit MASE. Its 16k context provides headroom if the corridor runner
  later uses the full 2019-onward PortWatch history, but it is **not** a selection
  advantage in the existing ~1,500-day benchmark (which also fits inside the old
  2,048 limit). Moirai 2.0 supplies a distinct decoder architecture and training
  recipe. Do not call the pretraining corpora independent: Moirai's disclosed
  mixture includes data derived from the Chronos dataset. Robustness here means
  agreement across distinct model implementations, not independent evidence.

All three are already in `MODEL_REGISTRY`; only Chronos-2 and TimesFM 2.5 carry
Apache-2.0 checkpoint licences. Recency/leaderboard facts explain why these three
are the candidate set; the provisional anchor choice is made on local evidence
and remains conditional on the panel gate below.

## Discipline this layer inherits (non-negotiable)

1. **Counterfactual = univariate per corridor.** For the leakage-safe
   counterfactual, run each foundation model univariate on each corridor's own
   pre-cutoff history. Do **not** feed other corridors' post-treatment values as
   covariates — that re-imports the SUTVA contamination AR-only is designed to
   exclude. Chronos-2's multivariate/covariate mode is reserved for a separate,
   explicitly-labelled *descriptive* cross-corridor-structure view, never the
   counterfactual generator.
2. **Prediction ≠ identification.** Foundation models power the descriptive
   transmission map and act as robustness on the Hormuz shortfall. The causal
   claim stays on AR-only. A better forecaster never identifies an effect.
3. **Re-run admission across the panel — pre-registered, not corridor-by-corridor.**
   Hormuz admission does **not** generalise to 28 heterogeneous corridors.
   Freeze the common history window, shared fold origins, forecast horizon,
   minimum MASE improvement, common nominal interval level, calibration metric,
   tolerance, missingness rule and minimum corridor count **before running any
   panel benchmark or viewing post-period deviations**. Admission is one
   panel-level decision, never corridor-by-corridor. The exact proposed rule is
   frozen in `config/corridor_transmission.yaml` and documented in
   `docs/CORRIDOR_PANEL_ADMISSION_PROTOCOL.md`. Its implementation tests pass,
   but the thresholds still require supervisor approval; until then, Chronos-2
   is only the provisional anchor.
4. **Multiplicity needs a joint null from shared placebo dates — not forecast
   quantiles.** Forecast quantiles alone cannot produce adjusted p-values.
   Construct the joint null from **placebo dates shared across all corridors**:
   each shared placebo origin yields one aligned vector of corridor statistics,
   and that stacked matrix is the joint resampling input to the studentized
   Romano–Wolf step-down in `src/lngfreight/inference.py` (which requires aligned
   joint draws by design). Independently shuffled per-corridor placebos would
   invent the cross-corridor dependence and must not be used. The proposed
   primary contract in `docs/CORRIDOR_INFERENCE_PROTOCOL.md` uses nine disjoint
   94-day shared windows across one 48-hypothesis AR-only family; its finite-
   sample adjusted-p-value floor is therefore 0.10.
5. **Do not sum corridor quantiles into basin intervals.** Univariate per-corridor
   forecasts have no joint predictive paths across corridors, so summing their
   quantiles fabricates a basin interval. Shared-placebo statistics preserve
   cross-corridor dependence and can support joint resampling p-values and a
   labelled **placebo reference distribution**. They are not automatically a
   predictive or confidence interval. A basin interval may be reported only if
   a separately specified and tested inversion/calibration procedure justifies
   it; absent that, report basin figures as **point estimates with no
   probabilistic band** and say so explicitly.
6. **Frozen and pinned.** Pin each model's Hugging Face revision hash and seed;
   freeze corridor forecasts into a dedicated run manifest, exactly as
   `tsfm_run_manifest.json` does today. Foundation-model inference runs in the
   isolated `.venv-bench` / `.venv-timesfm` environments, not the core env.
7. **Lead with normalised deviations.** Corridor maps report mean-scaled
   deviation first (raw counts are scale-confounded), mirroring the existing
   spatial-placebo treatment.

## Honesty boundary on the map (CLAUDE.md)

An above-counterfactual deviation at another corridor is **not** evidence that
traffic flowed there from Hormuz. Terms like "absorption" and "reallocation" are
avoided throughout because they assert a flow mechanism that only vessel-level
routing could establish; the layer reports **above- / below-counterfactual
throughput deviations** and nothing stronger. Gulf-loaded LNG in particular has
no maritime bypass around Hormuz, so a positive deviation at Cape of Good Hope or
Suez is predominantly non-Gulf, non-LNG traffic. The map describes corridor-level
**tanker-throughput deviations**; any LNG-specific interpretation remains at
**basin aggregate only**, with country rows suppressed (n = 2 post-period
Hormuz-exposed voyages).

## Integration path (engineering, separate from this decision)

**Keep this entirely outside `run_all.py`.** The core pipeline must not depend on
the optional heavyweight foundation-model environments. The corridor layer gets
its **own runner and its own frozen manifest**, exactly like the existing TSFM
benchmark — runnable on demand, never a core-pipeline dependency.

1. Build a basin-keyed corridor panel from the existing PortWatch chokepoint
   pulls (same data the spatial placebo already loads). **Complete:** the frozen
   input audit is `docs/CORRIDOR_PANEL_AUDIT.md`; basin groups are non-additive
   operational map facets, not flow or origin/destination classifications.
2. New `scripts/run_corridor_transmission.py` (isolated env): reuse
   `tsfm.counterfactual_shortfall` univariate per corridor, looping the three
   models over the panel; AR-only per corridor as the transparent baseline.
3. Build the shared-placebo joint-null matrix (aligned across corridors); attach
   studentized Romano–Wolf adjusted p-values and basin-grouped separation ratios.
4. Aggregate basin point estimates. Keep the shared-placebo distribution labelled
   as a reference/null distribution; add a basin interval only if the separate
   uncertainty task establishes a valid construction.
5. Freeze outputs into a dedicated `corridor_transmission_manifest.json`. Do
   **not** add a step to `run_all.py`.

Sources: [Chronos-2 (amazon-science/chronos-forecasting)](https://github.com/amazon-science/chronos-forecasting),
[Chronos-2 report (arXiv 2510.15821)](https://arxiv.org/abs/2510.15821),
[TimesFM (google-research/timesfm)](https://github.com/google-research/timesfm),
[Moirai / uni2ts (SalesforceAIResearch)](https://github.com/SalesforceAIResearch/uni2ts),
[Moirai 2.0 checkpoint licence and model card](https://huggingface.co/Salesforce/moirai-2.0-R-small).
