# Corridor-transmission results (exploratory)

**Status:** Exploratory, generated 2026-06-21. The panel, admission gate and
shared-placebo inference contract were frozen **before** any post-cutoff value
was viewed (Tasks 2–4). The author chose to proceed to results without waiting
for supervisor sign-off, to support an upcoming discussion. Nothing here is an
"admitted-model" or "statistically significant" claim — the nine-window design
has a finite-sample p-value floor of **0.10**, so a 5% rejection is impossible by
construction, not by software defect.

Reproduce: `python scripts/run_corridor_transmission.py` (kept outside
`run_all.py`). Source module `src/lngfreight/corridor_transmission.py`; tests
`tests/test_corridor_transmission.py`. Outputs:
`data/processed/corridor_transmission_results.csv`,
`..._basin_point_summary.csv`, `..._ar_baseline_mase.csv`, `..._manifest.json`.

## Method (one paragraph)

For each of the 48 eligible corridor–target hypotheses (28 tanker-count + 20
tanker-capacity), the locked AR-only baseline (`ar_lag1_7`, lags 1 and 7, weekly
seasonality) is trained on that corridor's own pre-cutoff history (expanding from
2022-01-01, ending 2026-02-27) and forecast over the 94-day post-cutoff window
from 2026-02-28. The statistic is the mean scaled signed deviation
`D = mean(observed − counterfactual) / pre-period mean`. The identical procedure
on nine disjoint pre-cutoff placebo windows forms the shared joint null for a
Romano–Wolf step-down correction across all 48 hypotheses. Each corridor is
forecast univariately, so the result is leakage-safe by construction (verified:
a corridor's deviation is invariant when every other corridor's post-cutoff data
is perturbed).

## Baseline credibility

AR-only median MASE across the 23 frozen pre-cutoff folds is **0.743** (median
over corridors), and **92%** of corridors have MASE < 1.0 — i.e. the baseline
beats a seasonal-naive forecast on the large majority of corridors. This is a
forecasting-quality statement only; it is not evidence of a causal effect.

## Headline result

The **Strait of Hormuz** shows the largest below-counterfactual deviation on both
targets, and is the only corridor at the p-value floor on both:

| Target | Signed deviation | Observed (94d) | Counterfactual (94d) | Raw p | RW p |
|---|---:|---:|---:|---:|---:|
| n_tanker | −0.955 | 245 transits | ≈5,366 | 0.10 | 0.10 |
| capacity_tanker | −0.953 | 10.5 M | ≈217.4 M | 0.10 | 0.10 |

Hormuz tanker transits fall from ~55/day pre-cutoff to ~2.6/day across the post
window, beginning the day after the 2026-02-28 cutoff. 32 of 48 hypotheses are
below counterfactual; 18 sit at the raw-p floor and 14 hold at the adjusted floor
after the multiplicity correction.

The largest **above-counterfactual** corridors are Cape of Good Hope (n_tanker
+0.46), Tsugaru (+0.40), Yucatan Channel (+0.23/+0.29) and Panama Canal
(+0.21) — a spatial pattern consistent with traffic appearing on long-haul
alternatives. **No routing/absorption/causal language is asserted**: these are
univariate descriptive deviations, and the contract forbids reallocation claims.

## Basin point summary

Reported point-only and **never summed** (`aggregation_allowed = false`; a voyage
can cross several chokepoints in a region). The `red_sea_arabian_gulf` region has
the most negative central tendency on both targets (mean deviation −0.46 counts,
−0.50 capacity), driven by Hormuz with Suez and Bab-el-Mandeb also below
counterfactual. See `corridor_transmission_basin_point_summary.csv`.

## Limitations (read before quoting)

- **Exploratory, not approved.** Specification was frozen pre-results, but no
  supervisor sign-off; treat every number as provisional.
- **p-floor 0.10.** With nine joint placebo draws, adjusted p-values are coarse
  reference measures. Report separation and rank, not significance.
- **Prediction ≠ identification.** AR forecast accuracy is not evidence of a
  causal effect; the ton-mile mechanism rests on the donor/dose-response design,
  not on this descriptive map.
- **Media/observation data.** PortWatch transits are satellite-AIS observations
  with reporting bias and missingness; capacity carries masked artifact-zeros
  that the AR input forward-fills (deviation still scored on observed days only).
- **Foundation-model robustness pending.** Tasks 5–6 (TSFM feasibility +
  admission benchmark) would add a robustness layer; they need the pinned
  `.venv-timesfm`/`.venv-bench` environments and are not run here. AR-only remains
  the locked primary estimator regardless of any later TSFM result.
