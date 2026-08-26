# External review request: which pathway should this thesis take?

*Paste everything below this line into the reviewing model, together with the
repository.*

---

## Your role

You are an independent methodological reviewer. I am a TUM Bachelor student in
Transportation Analytics. My thesis is due **1 September 2026**. Today is
**9 August 2026**, so roughly three weeks remain, including writing.

I have been working with an AI assistant that has produced several competing
recommendations for how to frame the thesis. I cannot judge between them. Your
job is to read the repository yourself, verify the load-bearing claims, and
tell me which single pathway to commit to.

**Do not defer to the assistant's conclusions.** It has already been wrong
twice in this project and corrected itself both times: once claiming an index
was "0.0 throughout" when it had eight non-zero days, and once claiming
Atlantic corridors "all rose" when a proper counterfactual showed two of them
were below forecast. Treat its summaries as hypotheses to check, not findings.
If the right answer is a pathway nobody has proposed, say so.

## Non-negotiable project rules

Read `CLAUDE.md` first and apply it throughout. In particular:

- Never fabricate. If something has not been run, it is a hypothesis.
- Prediction is not identification. Forecast accuracy is never causal evidence.
- The treatment cutoff `2026-02-28` is locked and externally anchored to the
  US DoD operation start. It does not move.
- Chronological splits only. Training uses pre-cutoff data.
- Bloomberg/Fearnleys inputs are **restricted, provenance-limited** data. Their
  permitted uses exclude ATT, causal freight claims, and identified mediation.
  Raw values may not be published. See `docs/DATA_SOURCES.md`.
- PortWatch has **no LNG vessel class**. `n_tanker` bundles gas carriers with
  oil and chemical tankers.

## What the thesis currently is

A single-event study of the 2026 Strait of Hormuz closure. The working
specification (`config/settings.yaml`, `modeling.working_specification`) uses
`hormuz_tanker_transits` from IMF PortWatch as the primary outcome and an
`ar_lag1_7` counterfactual, reported as a "disruption-associated counterfactual
shortfall" rather than a causal effect. Supporting layers: synthetic control,
BSTS, placebo-in-time, placebo-in-space, donor-contamination screening.

A June 2026 scope pivot toward importer-level heterogeneity ("captivity",
`docs/CAPTIVITY_EVENT_STUDY_DESIGN.md`) was approved but may not be viable
(see finding 5 below).

## The candidate pathways

**Pathway A. Throughput plus measurement robustness.**
Headline stays the throughput collapse. The distinguishing contribution
becomes measurement instability in satellite-derived chokepoint indicators,
built from three separately frozen PortWatch snapshots the repo holds and that
cannot be reconstructed from the public web today.

**Pathway B. LNG basin ton-mile mechanism.**
Headline becomes the LNG-specific finding that Pacific-basin importers had to
sail materially further per unit of gas after the closure while Atlantic
importers did not, with the freight-price basin inversion as corroboration.

**Pathway C. A as spine, B as mechanism chapter.**

**Pathway D. Something else you identify.**

Also advise on whether to demote the captivity/heterogeneity layer.

## Findings to verify independently

Each of these is load-bearing. Check the ones that matter for your
recommendation rather than trusting the numbers.

1. **Headline result.** Mean daily AR counterfactual shortfall 52.838
   transits/day over 130 days. The AR shortfall is 92.849% of its
   counterfactual total; the raw configured pre/post mean decline through July
   7 is 92.873%. Do not attach the separate 92.90% figure to this artifact.
   See `data/processed/counterfactual_post_treatment_summary.csv`.

2. **Data revision.** A PortWatch capture on 2026-08-09 revises 97.45% of all
   overlapping Hormuz days and 99.67% of configured training days; the
   configured training mean falls 17.68%. The mean-level revision is
   **overwhelmingly localized to Hormuz**, not literally Hormuz-only: every
   non-Hormuz count-class mean moved less than 0.1%, but other chokepoints have
   individual revised days. See `docs/PORTWATCH_VINTAGE_REGISTER.md`,
   `scripts/run_revision_and_basin_exploration.py`.

3. **Mean-level versus daily scaling.** Annual mean ratios are 0.818–0.848
   across 2019–2025, and the raw percentage decline is 92.873% versus 93.437%,
   while the absolute raw drop moves from 53.02 to 43.92/day. Daily scaling is
   not uniform: the pre-cutoff positive-denominator ratio has a 5th–95th
   percentile range of roughly 0.72–0.93, and the post mean ratio differs from
   the pre mean ratio. Percentage stability is partly near-zero-floor
   arithmetic, not proof of a common scale factor. A data-driven
   break-date search returns 2026-03-01 in all three snapshots, i.e. timing is
   vintage-robust. See `docs/PORTWATCH_VINTAGE_SENSITIVITY_RESULTS.md`.

4. **Rebound and relapse.** The cumulative AR average moves only 43.81 to 44.08
   when extended through 2026-08-01, but that average hides the observed phase
   profile. In the August vintage, matched 20-day means rise 0.85 → 10.45/day
   after the 2026-06-17 MoU (12.57/day in the final week), then fall to
   1.56/day over 2026-07-08–08-01 after renewed attacks. The supported claim is
   no sustained recovery through August 1, not “no rebound.”

5. **Heterogeneity layer may be dead.** `data/processed/importer_exposure_summary.csv`:
   **0 of 39 countries** yield an estimable Hormuz-exposure estimate, all
   suppressed for "post exposed voyages below 5". Interpretation offered: the
   closure was so complete that post-period exposure variation vanished.
   A country-level correlation between pre-shock exposure and haul-length
   change is +0.709 but collapses to −0.112 when India alone is dropped.

6. **LNG basin result (Pathway B's core).** From GFW vessel-level LNG data,
   average haul per m³ shipped: Pacific +17.2%, Atlantic −6.8%, Middle East
   +5.6%. See `data/processed/basin_exposure_summary.csv`.

7. **Corridor counterfactuals.** `data/processed/corridor_transmission_results.csv`
   already exists with Romano-Wolf stepdown p-values. Panama Canal is above
   counterfactual (+0.21, p=0.1), Cape of Good Hope has the largest positive
   deviation (+0.46) but p=1.0, and Suez and Bab el-Mandeb are **below**
   counterfactual. The finite-sample p-value floor is 0.1 (9 resamples).
   These are all-tanker, not LNG.

8. **Freight prices (restricted).** Fearnleys LNG assessments: West of Suez
   rose 220% against its own prior year versus 146% for East of Suez; the
   West/East ratio sat at 1.00 for 201 weeks across 2022–2025 and then ran at
   1.42 post-onset. Series ends 2026-07-03. Rights unverified.

9. **Confound.** A drone strike hit an FSRU and an LNG carrier at Damietta,
   Egypt on 2026-07-29, a non-Hormuz LNG supply-side shock inside the extended
   window. Attribution unresolved. See `docs/SUTVA_CONTAMINATION_AUDIT.md`.

## Questions I need answered

1. Which pathway do you recommend, and why that one rather than the others?
2. Is the measurement-revision contribution (Pathway A) genuinely novel and
   defensible at BSc level, or is it bookkeeping dressed up as a finding?
3. Is the LNG basin result (Pathway B) strong enough to carry a thesis given
   it rests on modelled route distances and vessel-level inference rather than
   observed cargo movements? Read
   `docs/INFERRED_CAPACITY_NAUTICAL_MILES_METHOD.md` before answering.
4. Should the captivity/heterogeneity layer be demoted to a reported null, or
   can it be rescued at some coarser resolution?
5. What is the single biggest threat to this thesis at the defence, and does
   the recommended pathway address it?
6. Is any current claim overstated relative to what the data supports?
7. Given three weeks, what should I explicitly **not** attempt?

## Output format

1. **Recommendation.** One pathway. One paragraph on why.
2. **Ranked alternatives.** The others, with the specific condition under which
   each would beat your pick.
3. **Verification log.** Which claims above you checked, and whether each held,
   failed, or could not be verified.
4. **Overstatements found.** Anything currently claimed more strongly than the
   evidence supports.
5. **Three-week plan.** Week by week, with an explicit "do not attempt" list.
6. **Defence preparation.** The three hardest questions an examiner will ask,
   with the strongest honest answer to each.

Be direct. If a pathway is weak, say it is weak and say why. I would rather
hear it now than at the defence.
