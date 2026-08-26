# Phase 2 results — multi-event chokepoint propagation

**Date:** 2026-08-26 · **Branch:** `ml/multi-event-propagation`
**Spec:** `config/multi_event_propagation.yaml` (frozen 2026-08-26)
**Code:** `src/lngfreight/propagation.py`, `scripts/run_propagation_model.py`

> **Provenance.** Figures below come from a prototype fit run directly against
> `data/processed/multi_event_panel.csv`, NOT from
> `scripts/run_propagation_model.py`. That script is written and compiles but has
> not been executed; CLAUDE.md rule 4 reserves execution to Mher. **Run it and
> confirm before quoting any number here.**

## 1. Headline

Two outputs were sought. **One works and one does not**, and the second is the
more important finding.

| Output | Verdict |
|---|---|
| Substitution map — which chokepoints respond to a disruption elsewhere | **Works.** Sanity gate passed at rank 1 of 28 |
| Reallocation share, summed over all 27 receivers | **Does not work.** Indistinguishable from the placebo null |
| Reallocation at a single pre-registered receiver | **Works.** Red Sea to Cape of Good Hope recovers 89% of the loss at the 100th percentile |

## 2. Model

    Delta[e, c, h]  ~  a_e * v_e[c] * f(h)

Per-event amplitude `a_e`, per-event receiver loadings `v_e[c]` at unit norm, and
a response profile `f(h)` shared across all events. Fitted by alternating least
squares on weekly responses, rank 1, horizon 8 weeks. Each chokepoint is scaled
by its own 365-day pre-onset baseline, and a common factor — the cross-sectional
median over units with no active disruption — is removed before responses are
measured.

This is an out-of-sample **predictive** object. It is not a causal spillover
parameter and `v_e` describes co-movement after an event, not proof that any
vessel rerouted.

**Training events (Hormuz sealed):** Ever Given 2021-03-23 · Black Sea
2022-02-24 · Panama 2023-12-19 · Red Sea 2024-01-13. Onsets are data-derived by
the pre-registered rule recorded in the spec, because `EVENT_CHRONOLOGY.md`
covers the Hormuz event only.

Variance explained by rank 1 across four events: **0.53**.

## 3. Sanity gate — passed

The spec requires the fit to recover the Bab el-Mandeb to Cape of Good Hope
substitution, which is known to be real.

| Quantity | Value |
|---|---|
| Loading, `v_red_sea[cape_of_good_hope]` | **0.738** |
| Rank among 28 receivers | **1** |
| Gate | **PASSED** |

The model was not told that Cape of Good Hope is the Red Sea's substitute. It
recovered it as the single strongest receiver out of 28.

Panama also returns Cape of Good Hope at rank 1 (0.577), which is plausible.
Black Sea returns Suez Canal at rank 1 (0.355), also plausible.

**Ever Given returns noise.** Its top receivers are Magellan Strait (0.545) and
Strait of Hormuz (0.456), which are not credible substitutes for a six-day Suez
blockage. This is consistent with the Phase 1 finding that Cape of Good Hope did
not respond to Ever Given at all: a shock shorter than the reroute decision
horizon produces no substitution, so the fit has only noise to describe. Treat
Ever Given's loadings as an informative negative, not as a result.

The shared profile `f(h)` rises monotonically from 0.20 at week 0 to 0.49 at
week 8: response builds over roughly two months rather than arriving at once.

## 4. Reallocation share — the negative result

The aggregate accounting was run against a placebo null: the identical procedure
at 120 random pseudo-onsets in quiet periods, avoiding a one-year guard band
around every real event.

| Event | Observed gross gain (transits/day) | Null median | Null p95 | Percentile of observed |
|---|---|---|---|---|
| Ever Given | 26.2 | 13.2 | 23.9 | 98% |
| Black Sea | 17.7 | 15.2 | 26.5 | 59% |
| Panama | 16.0 | 15.0 | 31.7 | 53% |
| **Red Sea** | **18.4** | **13.9** | **35.3** | **64%** |

The Red Sea — the strongest and cleanest event in the sample — sits at the 64th
percentile of its own null. **The aggregate reallocation figure is not separable
from noise.** Ever Given's 98% is almost certainly a false positive from
post-clearance queue rebound, since that event demonstrably produced no
reallocation.

**Why.** Summing residual gains across 27 chokepoints integrates a great deal of
noise. Each unit's few-percent wobble is multiplied back up by its own baseline,
and the large chokepoints dominate the sum. Total baseline traffic across the
panel is several hundred transits per day, so noise of a few percent is worth
more than the 7.9 transits/day the Red Sea actually lost.

**Consequence.** The panel-wide sum is dead. It is not the only route to a
"moved" term, and section 5 below recovers one that works.

## 5. The fix: test named pairs, not the whole panel

The aggregate failed because it summed 27 chokepoints. Testing one
**pre-registered** pair removes 26 units of noise. Same data, same windows, same
null procedure, 250 draws:

| Pair | Observed | Null p50 | Null p95 | Percentile |
|---|---|---|---|---|
| **Red Sea -> Cape of Good Hope** | **+7.03** | 0.31 | 1.73 | **100%** |
| Red Sea -> Suez Canal | **-7.21** | 1.03 | 2.87 | **0%** |
| Panama -> Cape of Good Hope | +5.31 | 0.31 | 1.59 | 100% |
| Black Sea -> Suez Canal | +3.13 | 1.23 | 3.21 | 94% |
| Ever Given -> Cape of Good Hope | +1.51 | 0.32 | 1.73 | 91% |

All figures are transits per day, averaged over the nine post-onset weeks.

**The Red Sea accounting closes.** Bab el-Mandeb lost **7.88 transits/day**. Cape
of Good Hope gained **7.03/day**. That is **89% of the loss reappearing at the
single substitute route**, four times above the 95th percentile of noise. Suez
moves the opposite way at the 0th percentile, which is correct: Suez is the same
route as Bab el-Mandeb, so it co-declines rather than absorbing.

Ever Given sits at 91%, below any sensible threshold, which is the right answer
for a six-day closure that produced no rerouting.

**The receiver must be named before the event is examined.** Choosing it after
inspecting the loadings makes this a selection statistic and voids the null. The
module enforces nothing here; the discipline is the researcher's.

**Confound to disclose.** The Panama onset (2023-12-19) and the Red Sea onset
(2024-01-13) are 25 days apart, so their post-windows overlap almost entirely.
The Panama -> Cape result cannot be separated from the Red Sea -> Cape result and
should not be reported as an independent finding.

### What this means for Hormuz

The method detects reallocation where a substitute route exists and returns
noise where one does not. Hormuz has **no maritime bypass** — that is the entire
reason it matters. So the pre-registered prediction for Phase 5 is sharp and
falsifiable:

> No receiver should show a gain outside its null after the Hormuz onset.

If that holds, the traffic did not move, and the distinction between "moved" and
"lost" is made by evidence rather than assumption. If some receiver does light
up, that is a finding worth the thesis on its own. Either way the receiver set
must be fixed and written down before the seal is broken.

## 6. Residual risks

1. **Rank 1 explains 0.53 of variance across four events.** Rank 2 and 3 are in
   the spec grid and have not been fitted. Selection must be leave-one-event-out.
2. **Four events, one of them noise-only.** Effectively three.
3. **Black Sea onset is an external anchor, not data-derived.** Kerch traffic was
   already drifting down before 2022: annual means 12.95 (2019), 12.17 (2020),
   10.93 (2021), then 6.04 (2022). The 2022-02-24 invasion date is used, and the
   pre-existing drift is a confound.
4. **Common-factor removal uses the median of unaffected units.** With several
   events active in overlapping periods the unaffected set shrinks.
5. **The placebo null has not been run at the full 200 draws** used by the
   script default; the prototype used 120.

## 7. Next actions

1. Run `python scripts/run_propagation_model.py` and confirm every figure above.
2. Run `python -m pytest tests/test_propagation.py -q`.
3. Fit ranks 2 and 3 with leave-one-event-out selection.
4. Decide what replaces the aggregate "moved" term, or accept the qualitative
   substitution map as the Phase 2 deliverable and amend the plan.
5. Only then proceed to Phase 3.
