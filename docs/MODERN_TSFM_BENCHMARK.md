# Modern Time-Series Foundation Model Benchmark Gate

Status: engineering research note, checked 2026-06-18. This does not alter the
formal proposal, estimand, hypotheses, locked AR-only primary, or Transformer
prohibition. A foundation model remains an isolated benchmark until it improves
both pre-treatment fit and interval calibration.

## Ranked candidates

1. **Chronos-2 (Amazon, released 2025-10-20; 120M parameters).** First choice.
   The official package supports zero-shot univariate, multivariate, and
   covariate-informed probabilistic forecasts. Use univariate input here: future
   route or energy values observed after treatment can absorb the disruption and
   invalidate the counterfactual. Official source:
   <https://github.com/amazon-science/chronos-forecasting>
2. **TimesFM 2.5 (Google, released 2025-09-15; 200M parameters).** Second choice.
   It supports 16k context and continuous quantile forecasts to a 1k horizon.
   Its long context is unnecessary for the four-year PortWatch history, but its
   quantile head makes interval calibration directly testable. Official source:
   <https://github.com/google-research/timesfm>
3. **Moirai 2.0 R-small (Salesforce, released 2025-08).** Probabilistic
   zero-shot cross-check with flexible context/horizon through Uni2TS. It is a
   useful third model, not the first integration because its GluonTS stack is
   heavier than the Chronos DataFrame interface. Official source:
   <https://github.com/SalesforceAIResearch/uni2ts>
4. **Tiny Time Mixers R2 / Granite TSFM (IBM, 2025 generation).** Useful when
   CPU cost and few-shot tuning matter. Lower priority for this thesis because
   the main need is an independent probabilistic counterfactual, not deployment
   efficiency. Official source: <https://github.com/ibm-granite/granite-tsfm>

Kairos, TiRex, Sundial, and Time-MoE are research-watch candidates. Adding many
models would inflate multiple-comparison risk without improving identification.

## Admission test

Every candidate must use the existing expanding, chronological, strictly
pre-treatment folds. Report mean/median MASE, RMSE, empirical 95% interval
coverage, interval width, and runtime. It enters the post-treatment comparison
only if it materially improves AR-only MASE **and** interval coverage without
using post-treatment observed covariates. The fixed treatment date and folds may
not be tuned after seeing the disruption window.

The isolated Chronos-2 harness is:

```bash
python scripts/run_chronos2_benchmark.py --acknowledge-benchmark-only
```

It is deliberately excluded from `scripts/run_all.py` and the frozen core
requirements because model weights and the PyTorch stack are optional external
artifacts. Benchmark hashes, package versions, device, and model revision must
be frozen before any thesis result is reported.
