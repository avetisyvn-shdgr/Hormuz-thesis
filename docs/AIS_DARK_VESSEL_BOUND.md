# A number on the AIS-dark-vessel bound

**Status:** Updated 2026-07-18 for the active v2 130-day primary window. Turns
the previously qualitative "observed throughput is an upper bound on the true
reduction" caveat (FALLBACK_STRATEGY.md, INFERENCE_NOTES.md) into an auditable
bound. Reproduced by `scripts/run_ais_dark_bound.py` from the frozen
counterfactual summary; outputs
`data/processed/ais_dark_bound_{sensitivity,critical_rates}.csv`.

## Why a bound, not a point correction

In a conflict episode, AIS dark activity / GPS jamming / spoofing (IEA-flagged for
this Middle East context) is **correlated with the treatment**, not random noise.
Observed transits fall by *more* than true transits, concentrated in the treated
window. So the naive observed-minus-counterfactual loss is biased **away from
zero**: it is an **upper bound** on the true throughput reduction. We cannot point-
correct it without an external dark-rate series, but we can bound it and, more
usefully, compute how large the dark rate would have to be to overturn the
qualitative conclusion.

## The identity

For the primary estimator (`ar_lag1_7`, no post-treatment covariates) on
`hormuz_tanker_transits`, post-period 2026-02-28 to 2026-07-07:

- Observed transits `O = 529`
- Counterfactual transits `C = 7,398`
- Naive observed reduction `R_obs = 1 - O/C = 92.8%`, the upper bound (dark rate `d = 0`)

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

The observed **92.8%** transit collapse is an upper bound on the true reduction.
AIS-dark measurement error can change threshold wording, so the thesis should not
claim a 95% true collapse in the active 130-day window, and a claim of a true
reduction of at least 90% requires an external dark-rate bound below about
28.5%. The severe-collapse conclusion is still difficult to erase:

- Even at an extreme **d = 50%** — half of all tankers truly transiting Hormuz
  going dark, beyond the normal gap-fill — the true reduction is still **85.7%**.
- To make the true collapse *merely 50%*, **about 86% of all tankers actually
  transiting Hormuz would have had to be simultaneously AIS-dark** for the
  130-day post window,
  a near-total blackout that would itself be a separately detectable anomaly
  (PortWatch deadweight capacity, third-party satellite/Kpler-LSEG trackers, port-
  call records), and which no source reports.

So AIS-dark measurement error moves the exact magnitude and threshold labels, but
it cannot by itself turn the event into an ordinary fluctuation unless the
incremental treatment-period dark rate is extraordinarily large. Report the
result as a **range with 92.8% as the upper bound**, and set the lower bound by
anchoring `d` to a cited external dark-fleet figure via
`--plausible-dark-rate` (e.g. IEA / UNCTAD / Kpler-LSEG reporting), not by
assuming `d` internally.

## What this does and does not do

- It **bounds** treatment-correlated measurement error in the observed series. It
  is not a causal correction and makes no claim about the realised dark rate.
- `d` is *incremental* to the baseline gap-fill the counterfactual already
  encodes, so it is not double-counting normal AIS coverage gaps.
- It addresses only the **treated unit's** measurement. Donor contamination and
  SUTVA are separate and are handled in `SUTVA_CONTAMINATION_AUDIT.md`.
- The deadweight-capacity outcome gives a partly independent lower-bound anchor
  (a dark vessel still removes its observed DWT); the WTO/AXSMarine LNG outbound
  index is a methodologically independent series whose co-movement further
  constrains a pure-observability explanation.
