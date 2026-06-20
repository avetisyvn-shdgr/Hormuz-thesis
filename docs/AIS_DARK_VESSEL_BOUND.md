# A number on the AIS-dark-vessel bound

**Status:** 2026-06-20. Turns the previously qualitative "observed throughput is
an upper bound on the true reduction" caveat (FALLBACK_STRATEGY.md,
INFERENCE_NOTES.md) into an auditable bound. Reproduced by
`scripts/run_ais_dark_bound.py` from the frozen counterfactual summary; outputs
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
`hormuz_tanker_transits`, post-period 2026-02-28 → 2026-06-01:

- Observed transits `O = 245`
- Counterfactual transits `C = 5,366`
- Naive observed reduction `R_obs = 1 − O/C = 95.4%`  ← the upper bound (dark rate `d = 0`)

Let `d` = the **incremental** treatment-period dark rate: the fraction of the
period's *true* transits that PortWatch fails to observe, **over and above** the
baseline AIS gap-fill already embedded in the pre-treatment counterfactual. Then
true transits `T(d) = O/(1−d)` and the true reduction is

```
R_true(d) = 1 − O / ((1 − d) · C),   with R_true(0) = R_obs.
```

## The numbers

**Sensitivity — true reduction if a fraction `d` of true transits went dark:**

| Assumed dark rate `d` | Implied true transits | True reduction |
|---:|---:|---:|
| 0.00 (naive) | 245 | **95.4%** |
| 0.10 | 272 | 94.9% |
| 0.20 | 306 | 94.3% |
| 0.30 | 350 | 93.5% |
| 0.50 | 490 | 90.9% |
| 0.70 | 817 | 84.8% |
| 0.90 | 2,450 | 54.3% |

**Critical dark rate `d*` needed to pull the true reduction down to `R`:**

| Target reduction `R` | Required dark rate `d*` |
|---:|---:|
| 95% | 8.7% |
| 90% | 54.3% |
| 75% | 81.7% |
| 50% | **90.9%** |

## Headline for the thesis

The observed **95.4%** transit collapse is an upper bound on the true reduction.
Under any defensible incremental dark rate the conclusion is unchanged:

- Even at an extreme **d = 50%** — half of all tankers truly transiting Hormuz
  going dark, beyond the normal gap-fill — the true reduction is still **≥ 91%**.
- To make the true collapse *merely 50%*, **≈ 91% of all tankers actually
  transiting Hormuz would have had to be simultaneously AIS-dark** for ~3 months —
  a near-total blackout that would itself be a separately detectable anomaly
  (PortWatch deadweight capacity, third-party satellite/Kpler-LSEG trackers, port-
  call records), and which no source reports.

So AIS-dark measurement error moves the *magnitude* by a few percentage points
within any plausible range and cannot touch the *qualitative* finding of a severe
throughput collapse. Report the result as a **range with 95.4% as the upper
bound**, and set the lower bound by anchoring `d` to a cited external dark-fleet
figure via `--plausible-dark-rate` (e.g. IEA / UNCTAD / Kpler-LSEG reporting),
not by assuming `d` internally.

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
