# A number on the AIS-dark-vessel bound

**Status:** Updated 2026-07-18 for the active v2 130-day primary window. Turns
the previously qualitative "observed throughput is a conditional upper bound on
the true reduction" caveat (FALLBACK_STRATEGY.md, INFERENCE_NOTES.md) into an
auditable sensitivity calculation. Reproduced by
`scripts/run_ais_dark_bound.py` from the frozen
counterfactual summary; outputs
`data/processed/ais_dark_bound_{sensitivity,critical_rates}.csv`.

## Why a bound, not a point correction

In a conflict episode, AIS dark activity / GPS jamming / spoofing may be
**correlated with the treatment**, rather than random noise. The calculation
therefore imposes a one-sided measurement-error model: treatment-period
observability error may hide true transits but does not create false-positive
observed transits, and the fitted counterfactual `C` is treated as the reference
path. Under those assumptions, observed transits fall by more than true transits
and the naive observed-minus-counterfactual loss is biased **away from zero**.
It is therefore a **conditional upper bound** on the true throughput reduction.
Without an admitted external dark-rate series, the calculation does not identify
a realised correction or an empirical lower bound; it reports how large the
assumed dark rate would have to be to cross stated reduction thresholds.

## The identity

For the primary estimator (`ar_lag1_7`, no post-treatment covariates) on
`hormuz_tanker_transits`, post-period 2026-02-28 to 2026-07-07:

- Observed transits `O = 529`
- Counterfactual transits `C = 7,398`
- Naive observed reduction `R_obs = 1 - O/C = 92.8%`, the conditional upper
  bound within the one-sided model (dark rate `d = 0`)

Let `d` = the **incremental** treatment-period dark rate: the fraction of the
period's *true* transits that PortWatch fails to observe, **over and above** the
baseline AIS gap-fill already embedded in the pre-treatment counterfactual. Then
true transits `T(d) = O/(1 - d)` and the true reduction is

```
R_true(d) = 1 - O / ((1 - d) * C),   with R_true(0) = R_obs.
```

## The numbers

**Sensitivity — true reduction if a fraction `d` of true transits went dark:**

| Assumed dark rate `d` | Implied true transits | True reduction |
|---:|---:|---:|
| 0.00 (naive) | 529 | **92.8%** |
| 0.10 | 588 | 92.1% |
| 0.20 | 661 | 91.1% |
| 0.30 | 756 | 89.8% |
| 0.40 | 882 | 88.1% |
| 0.50 | 1,058 | 85.7% |
| 0.70 | 1,763 | 76.2% |
| 0.90 | 5,290 | 28.5% |

**Critical dark rate `d*` needed to pull the true reduction down to `R`:**

| Target reduction `R` | Required dark rate `d*` |
|---:|---:|
| 95% | infeasible: above the naive upper bound |
| 90% | 28.5% |
| 75% | 71.4% |
| 50% | **85.7%** |

## Headline for the thesis

The observed **92.8%** AIS-based transit collapse is a conditional upper bound
on the true reduction under the one-sided undercount model above. AIS-dark
measurement error can change threshold wording, so the thesis should not claim
a 95% true collapse in the active 130-day window. A claim of a true reduction of
at least 90% would require an admitted external dark-rate bound below about
28.5%. Within the declared sensitivity grid:

- Even at an extreme **d = 50%** — half of all tankers truly transiting Hormuz
  going dark, beyond the normal gap-fill — the true reduction is still **85.7%**.
- To make the true collapse *merely 50%*, **about 86% of all tankers actually
  transiting Hormuz would have had to be simultaneously AIS-dark** for the
  130-day post window.

The 85.7% threshold is an algebraic sensitivity result, not evidence about the
realised dark rate. The repository has no admitted dark-rate series and therefore
does not assert whether such a rate occurred or whether outside observers would
have detected it. Report **92.8% as the observed AIS-based reduction and the
conditional upper bound within this model**. Report a lower bound only if `d` is
anchored to an admitted and cited external dark-rate source through
`--plausible-dark-rate`; do not assume one internally.

## What this does and does not do

- It **bounds** treatment-correlated measurement error in the observed series. It
  is not a causal correction and makes no claim about the realised dark rate.
- `d` is *incremental* to the baseline gap-fill the counterfactual already
  encodes, so it is not double-counting normal AIS coverage gaps.
- It addresses only the **treated unit's** measurement. Donor contamination and
  SUTVA are separate and are handled in `SUTVA_CONTAMINATION_AUDIT.md`.
- The deadweight-capacity outcome is a related robustness series, not an
  independent lower-bound anchor; it shares AIS observability risk.
- The WTO/AXSMarine LNG outbound index is a distinct cross-source comparison,
  not methodologically independent confirmation, and may share maritime-
  observation failure modes.
