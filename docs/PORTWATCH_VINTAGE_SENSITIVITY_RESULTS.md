# PortWatch vintage & window sensitivity — results

**Run:** 2026-08-09 · `scripts/run_portwatch_vintage_sensitivity.py`
**Output:** `data/processed/portwatch_vintage_sensitivity.csv`
**Status:** Sensitivity layer. The pinned vintage and the v2 window
(`full_end: 2026-07-07`) remain the reporting basis; nothing here re-pins or
supersedes a headline number.

## Why this exists

The v3 window extension attempt (2026-08-09) found that a fresh PortWatch
capture does not merely append days — it revises **2,680/2,750 (97.45%) of all
overlapping Hormuz days** and **1,514/1,519 (99.67%) of configured training
days**. Over the configured 2022–cutoff training support, the mean falls 17.68%
(`PORTWATCH_VINTAGE_REGISTER.md`). PortWatch's own changelog attributes this
to July and August 2026 AIS-spoofing / incomplete-transit revisions and a
March 2026 boundary refinement to chokepoint6 (Strait of Hormuz). Because the
AR counterfactual is fitted on pre-treatment data, adopting that capture
silently would move the headline magnitude on a vendor methodology change.
Mher's decision (2026-08-09, `DECISION_LOG.md`): keep the pinned vintage
primary, quantify the exposure here.

## Method

The project's own working-specification primary (`ar_lag1_7` via
`arx_forecast`, locked 2026-02-28 cutoff) is **reused, not reimplemented**, so
any difference is attributable to inputs alone. The vintage is read through
`registry.get_variable("portwatch_chokepoints_vintage_20260809_snapshot")`,
checksum-verified (CLAUDE.md rule 7). The capacity outcome applies the
project's `capacity_zero_with_transits: mask` policy.

**Harness self-check (gating).** Before reporting any comparison, the script
rebuilds the pinned-vintage result from raw and must match the committed
`counterfactual_post_treatment_summary.csv`. Both outcomes reproduced exactly
(transits rel. diff 1.34e-16; capacity 0.00e+00). The script raises and
refuses to report if this fails — it did fail on first run, correctly catching
that the harness had omitted the capacity mask.

## Results

| Outcome | Scenario | Window end | Post days | Pre-mean | Mean daily loss | Cumulative loss |
|---|---|---|---:|---:|---:|---:|
| transits (primary) | pinned primary | 2026-07-07 | 130 | 57.09 | **52.84** | 6,869 |
| transits | vintage, same window | 2026-07-07 | 130 | 47.00 | **43.81** | 5,696 |
| transits | vintage, extended | 2026-08-01 | 155 | 47.00 | **44.08** | 6,832 |
| capacity (robustness) | pinned primary | 2026-07-07 | 130 | 2,711,290 | 2,466,153 | 2.910e8 |
| capacity | vintage, same window | 2026-07-07 | 130 | 2,292,189 | 2,086,704 | 2.441e8 |
| capacity | vintage, extended | 2026-08-01 | 155 | 2,292,189 | 2,109,106 | 2.911e8 |

The two effects are separated deliberately: *vintage, same window* holds the
dates fixed and varies only the vintage; *vintage, extended* adds the window
change on top.

Every row above trains on `panel_aligned.csv` from 2022-01-01, so this table
varies the data vintage and the scoring window but not the training window. The
training window is a third sensitivity axis and is reported separately in
`experiments/network_adaptation/outputs/hormuz_shortfall_specification_sensitivity.csv`:
on the full PortWatch history from 2019-01-01 the same AR model over the same 130
pinned-primary days gives 6,496 rather than 6,869.

## Reading

**1. The vintage moves the magnitude by about a sixth.** Holding dates fixed,
the primary daily shortfall falls 52.84 → 43.81 transits/day (**−17.1%**);
capacity falls −15.4%. The AR shift is close to the **−17.68% configured
training-mean revision** (the separate −16.9% figure uses the longer 2019–
cutoff overlap). This is consistent with the mechanical channel: a lower fitted baseline yields a
lower implied counterfactual, hence a smaller loss. **This is a measurement
revision, not an economic finding.**

**2. The cumulative average conceals a rebound and relapse.** Extending the
window 25 days changes the cumulative daily rate only 43.81 → 44.08 (+0.6%)
while cumulative loss grows 5,696 → 6,832 transits. That aggregate comparison
is non-diagnostic about within-window dynamics. In the 2026-08-09 vintage, the
matched 20-day observed mean rises from 0.85/day before the 06-17 MoU to
10.45/day during 06-17–07-06 (12.57/day in the final week), then falls to
1.56/day over 07-08–08-01 after renewed attacks. The pinned vintage confirms
the first movement (1.25 → 12.45/day). Its trusted reporting endpoint is
07-07; five later raw buffer days are excluded, so it cannot estimate the
relapse interval. The defensible conclusion is **temporary partial rebound,
then relapse; no sustained recovery through 2026-08-01**, not “no rebound.”
See `PORTWATCH_REBOUND_RELAPSE_PROFILE.md`.

**3. The endpoint shortfall is large in both vintages; the path and magnitude
must be separated.** The point estimate changes materially with vintage, and
the observed path is non-monotonic. The defensible reporting posture is to
quote the pinned-vintage figure as primary, cite this table for vintage
exposure, cite the phase profile for the temporary rebound/relapse, and never
present a magnitude without naming its vintage.

## Limits — what this does not establish

- **Not a full pipeline re-run.** Only the AR primary was recomputed. Placebo
  inference, synthetic control, BSTS, intervals, and every figure remain on
  the pinned vintage. No p-value or interval here is revised.
- **The extended window is a regime mixture**, not more of the same closure:
  it spans closure → 06-17 MoU / attempted reopening → renewed attacks from
  07-07. A flat daily rate across a mixed regime is an average over
  heterogeneous sub-periods.
- **It contains the 2026-07-29 Damietta confound** (non-Hormuz LNG
  supply-side shock; `SUTVA_CONTAMINATION_AUDIT.md`). The within-unit AR
  primary is structurally immune to it, but the extended-window result should
  not be described without naming the event.
- **A 1-day trailing buffer** was used (`full_end` 2026-08-01 on a 2026-08-02
  max) instead of the v1/v2 5-day rule, justified by a tail-completeness check
  and documented in `PORTWATCH_VINTAGE_REGISTER.md`. The 5-day rule would have
  ended at 2026-07-28 and excluded Damietta.
- Revisions concentrate pre-treatment because post-onset values sit near zero;
  a future vintage that revises the *post* period would not behave this way.
