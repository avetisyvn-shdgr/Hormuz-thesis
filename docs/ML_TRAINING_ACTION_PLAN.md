# ML training action plan — multi-event chokepoint propagation

**Branch:** `ml/multi-event-propagation`
**Created:** 2026-08-26
**Status:** proposed, nothing run, no results claimed
**Relationship to existing plan:** additive. This does NOT modify the accepted
no-third-layer integration path in `CURRENT_PLAN.md`, the locked cutoff
`2026-02-28`, the frozen corridor spec, or any committed artifact.

---

## 0. How to use this file

This file is written to be executed by a human with assistant support, split
across two assistants working in parallel. Every phase ends in a
**STOP-AND-REPORT** block. Per `CLAUDE.md` rule 4, no assistant may state that a
phase works until Mher has run it and pasted real output back.

Suggested split:

| Track | Owner | Phases |
|---|---|---|
| A — data admission and darkness model | assistant 1 | P1, P3 |
| B — propagation model | assistant 2 | P2, P4 |
| Merge, held-out test, write-up | Mher | P5, P6 |

The two tracks are independent until P5. They must not both edit
`config/sources.yaml` in the same session.

---

## 1. Feasibility assessment against the repository as it stands

Checked on 2026-08-26 against the working tree, not against documentation.

### 1.1 What already exists and is directly reusable

| Asset | Location | Relevance |
|---|---|---|
| Full 28-chokepoint daily panel, **2019-01-01 to 2026-07-12**, 77,001 rows, 2,750 days per chokepoint | `data/raw/portwatch/Daily_Chokepoints_Data.csv` | This is the entire training set for the propagation model. Already frozen and hashed. No new download required. |
| Per-vessel-type counts and capacity (`n_tanker`, `n_container`, `n_dry_bulk`, `n_general_cargo`, `n_roro`, `capacity_*`) | same file | Allows the model to be fitted per vessel class, and cross-class transfer to be tested. |
| `wide_chokepoint_panel(value_col, start, end, exclude)` | `src/lngfreight/spatial.py` | Returns the date x chokepoint matrix. Already parameterised by `start`/`end`, so extending history is a keyword argument, not a refactor. |
| `load_portwatch_snapshot()` with schema check | `src/lngfreight/spatial.py` | Registry-routed, provenance-logged. |
| `spatial_placebo_summary`, `leave_one_donor_out_summary` | `src/lngfreight/spatial.py` | Cross-sectional placebo machinery already written. |
| `rolling_origin_splits` | `src/lngfreight/validation.py` | Chronological splitting, `CLAUDE.md` rule 5 already enforced. |
| Model roster | `src/lngfreight/tsfm.py`, `baselines.py`, `bsts.py` | Becomes the baseline the new model must beat. No new architectures. |
| GFW client hitting `/v3/events` with pagination | `src/lngfreight/sources/gfw.py` | Adding a second event dataset is a constant plus a normaliser, not a new integration. |
| Credentials present | `.env` | `GFW_API_TOKEN`, `GIE_ALSI_KEY`, `EIA_API_KEY`, `COMTRADE_API_KEY`, `ESTAT_API_KEY` all set. |

### 1.2 The finding that makes multi-event training possible

`study_window.full_start` in `config/settings.yaml` is `2022-01-01`, annotated
"generous pre-history for baselines/seasonality". **The raw snapshot goes back to
2019-01-01.** 1,096 days per chokepoint are being discarded by a modelling
choice, not by a data limitation.

The discarded history contains chokepoint disruption events that the propagation
model needs as training data:

| Event | Approx. window | Mechanism | In current window? |
|---|---|---|---|
| Ever Given / Suez grounding | Mar 2021 | Total closure, ~6 days, sharp start and end | **No — excluded** |
| Pandemic demand shock | 2020 | Global, not chokepoint-specific | **No — excluded** |
| Black Sea / Kerch / Bosporus | From Feb 2022 | Sanctions, conflict, grain corridor | Yes |
| Panama Canal drought | 2023–2024 | Capacity rationing, not danger | Yes |
| Bab el-Mandeb / Red Sea | From late 2023 | Attacks, voluntary avoidance | Yes |
| Suez Canal | Same period | Same route as Bab el-Mandeb — one event, not two | Yes |
| Strait of Hormuz | From Feb 2026 | **Held out. Never enters training.** | Yes |

`Cape of Good Hope` is one of the 28 panel units. The Bab el-Mandeb to Cape
substitution is therefore directly observable in data already on disk, and is
the natural validation case: if the model does not learn that edge, it is wrong.

### 1.3 The gap that requires scoping down

The darkness model (Machine A) is **not** as ready as the propagation model.

- `data/raw/gfw/` contains port visits and vessel identity only. There are no gap
  events, and `sources/gfw.py` pins `PORT_VISIT_DATASET` as its only dataset.
- The vessel frame is **LNG carriers only** (GEM-derived roster, IMO-exact
  matched). There is no tanker roster of comparable quality in the repository.
- A global tanker darkness model would require building that roster first, which
  is a data acquisition project of unknown size and is **out of scope**.

**Scoping decision:** run Machine A on the existing LNG-carrier frame as a
bounded pilot. Report it as a pilot. Do not describe it as a fleet-wide MNAR
correction. If the pilot shows signal and time remains, the tanker frame becomes
a documented extension, not a promise.

Note that `observability_frontier.py` and `ais_dark_bound_sensitivity.csv`
already sweep *assumed* darkening rates. Machine A does not add a layer; it
supplies an *empirical anchor* for a parameter that is currently assumed.

### 1.4 Overall verdict

| Component | Feasible on current assets? | Main risk |
|---|---|---|
| P1 history extension | Yes, immediately | Must not disturb the Hormuz primary window |
| P2 propagation model | Yes, no new data | Few events; mechanisms differ |
| P3 darkness pilot | Yes, scoped to LNG carriers | Small frame; may lack labels |
| P4 baselines and placebo bias | Yes, code exists | None material |
| P5 held-out Hormuz test | Yes | Sealing discipline |
| P6 causal exposure layer | Optional | Do not attempt without P2 succeeding |

---

## 2. Governance constraints — read before touching anything

1. **Do not edit `config/corridor_transmission.yaml`.** It is frozen
   (`frozen_on: 2026-06-21`) and governs committed results. This work gets its
   own new spec file.
2. **Do not change `study_window.full_start`.** The Hormuz primary path depends
   on it. The extended history is a *separate* window key used only by the new
   estimator. Two windows coexist; they do not replace each other.
3. **Do not change `primary_treatment_cutoff` (`2026-02-28`).** See
   `docs/EVENT_CHRONOLOGY.md` before writing any date anywhere.
4. **All external data through `registry.get_variable()`.** No ad-hoc
   `requests.get` (`CLAUDE.md` rule 7). New sources get a `config/sources.yaml`
   entry with an honest `status` flag first.
5. **Chronological splits only.** Never random-split (`CLAUDE.md` rule 5).
6. **One phase at a time.** No assistant generates the whole pipeline
   (`CLAUDE.md` rule 3).
7. **Hormuz is sealed from P1 until P5.** Record the date and commit hash at
   which it is unsealed. The value of this design is that the prediction was
   made before the answer was seen.

---

## PHASE 1 — Extend the training history

**(a) Methodological justification.** The propagation model requires more than
one disruption to learn from. Extending the panel to the snapshot's true start
adds at least the Suez 2021 closure, which is the cleanest chokepoint closure in
the record: total, short, unambiguous in start and end.

**(b) Data requirement.** None new. `Daily_Chokepoints_Data.csv` already covers
2019-01-01 to 2026-07-12.

**(c) Expected limitations.** 2020 is contaminated by a global demand shock that
is not chokepoint-specific and will inflate apparent cross-chokepoint
correlation. It must be either excluded or carried with an explicit indicator,
and the choice recorded before fitting. PortWatch coverage and methodology may
also differ in early years; check for level shifts at year boundaries.

**(d) Next practical action.**

1. Create `config/multi_event_propagation.yaml` as a NEW frozen spec. Do not
   reuse or edit the corridor spec. Minimum contents: training window start/end,
   the event table with explicit windows, the held-out unit, the value column,
   the rank `k`, the lag horizon `H`, and a `frozen_on` date.
2. Add a `training_window` block to that file. Leave `study_window` in
   `settings.yaml` alone.
3. Write `scripts/build_multi_event_panel.py` calling
   `spatial.wide_chokepoint_panel(value_col="n_tanker", start=<new start>, end=<new end>)`.
4. Produce a coverage audit: rows per chokepoint per year, missing-day counts,
   and a year-boundary level-shift check.

**STOP-AND-REPORT.** Paste the coverage audit. Do not proceed to P2 until the
2019–2021 data is confirmed usable and the 2020 handling decision is recorded in
`docs/DECISION_LOG.md`.

**Kill criterion.** If pre-2022 coverage is materially different in definition
(not just level), drop the extension and run P2 on 2022+ with three events.
State that in the thesis rather than working around it.

---

## PHASE 2 — Propagation model (Machine B)

**(a) Methodological justification.** The object of interest is the response of
every chokepoint to a disruption at another chokepoint. A full 28 x 28 x H
kernel is unidentifiable from a handful of events, so low-rank structure is
imposed. The compression is not a convenience: the learned factors *are* the
scientific result, because they place chokepoints in a substitution space
estimated from observed events rather than simulated.

This is a **predictive** estimand, out-of-sample network response. It is not a
causal spillover parameter. Per `CLAUDE.md` rule 2, do not label it causal. A
causal reading requires the exposure design in P6.

**(b) Data requirement.** The P1 panel. Event windows and intensity from
`docs/EVENT_CHRONOLOGY.md` for dated events, plus published restriction
announcements for Panama. Optional: ACLED for conflict intensity, which needs a
new `sources.yaml` entry with `status: free`.

**(c) Expected limitations.**
- Three to five training events is few. Every result must carry
  leave-one-event-out sensitivity.
- Panama was a drought, the Red Sea was a war. Response mechanisms may not
  transfer. Fit with and without Panama and report both.
- Suez and Bab el-Mandeb share a route. Treat as one event or the model
  double-counts.
- Seasonality and global trend will masquerade as propagation unless absorbed by
  time effects.

**(d) Next practical action.**

1. `src/lngfreight/propagation.py`. Fit
   `K[c'->c](h) ~ sum_k u_k[c'] * v_k[c] * f_k(h)` by regularised least squares
   on stacked event windows, with chokepoint and calendar-time effects absorbed
   first.
2. Start at `k=2`, `H=60` days. Select `k` by leave-one-event-out, never by fit
   on the pooled sample.
3. Sanity gate before anything else: does the fitted kernel recover a strong
   positive Bab el-Mandeb to Cape of Good Hope edge? If not, stop and debug. That
   edge is known to be real.
4. Export the learned `u` and `v` as a CSV so the substitution map can be plotted
   and inspected by hand.

**STOP-AND-REPORT.** Paste: the Bab el-Mandeb to Cape edge weight, the
leave-one-event-out `k` selection table, and the `u`/`v` table.

**Kill criterion.** If the Cape edge is not recovered under any `k` or `H`, the
model is not learning propagation. Do not tune until it appears. Report the
failure and fall back to the hand-specified exposure map in P6.

---

## PHASE 3 — Darkness pilot (Machine A)

**(a) Methodological justification.** `observability_frontier.py` currently
sweeps assumed darkening rates. Observed AIS gap events replace the assumption
with a measurement, which converts an unanchored sensitivity range into an
anchored one.

**(b) Data requirement.** New GFW dataset
`public-global-gaps-events:latest`, and optionally
`public-global-loitering-events:latest`, over the existing LNG-carrier frame.
Requires:
- a `config/sources.yaml` entry, `status: free`, GFW API terms, honest
  `source_status` matching the existing GFW snapshot entries;
- a `GAP_EVENT_DATASET` constant and a `normalize_gap_events` function in
  `src/lngfreight/sources/gfw.py`, mirroring `normalize_port_visits`;
- a `get_gfw_gap_events` accessor in `registry.py` mirroring
  `get_gfw_port_visits`;
- a frozen snapshot written to `data/raw/gfw/gap_events.csv` with a
  `SHA256SUMS.vessel` entry.

**(c) Expected limitations.**
- The frame is 624 LNG carriers, not the tanker fleet. Label counts may be too
  low to fit anything. Check counts before modelling.
- A gap is not proof of intent. Coverage holes, receiver geometry and satellite
  revisit all produce gaps. The model predicts *observed gaps*, not deliberate
  darkening, and the write-up must say so.
- GFW's own gap detection has minimum-duration and vessel-class thresholds that
  are themselves a filter.

**(d) Next practical action.**

1. Add the source entry and client method. Pull the frame. Freeze and hash.
2. Report label counts by year and by vessel before fitting anything.
3. Only if counts support it: fit `P(gap | vessel class, capacity, flag, prior
   route history, region, time)` with chronological splits, and report
   calibration, not just AUC.
4. Feed the estimated post-event gap rate into `observability_frontier.py` as an
   anchored value alongside the existing assumed grid. Do not remove the grid.

**STOP-AND-REPORT.** Paste the label counts first. That single number decides
whether P3 is a model or a descriptive paragraph.

**Kill criterion.** Under roughly 500 gap events in the frame, do not fit a
model. Report observed gap rates descriptively and move on. That is still an
improvement on an assumed rate.

---

## PHASE 4 — Baselines and placebo bias

**(a) Methodological justification.** A new model is only interesting relative to
what already exists. Separately, running the existing roster on units where the
true effect is approximately zero measures each model's counterfactual bias
directly instead of assuming it away.

**(b) Data requirement.** P1 panel and the existing roster. Nothing new.

**(c) Expected limitations.** "Approximately zero effect" is an assumption about
low-exposure chokepoints, defensible but not free. Report sensitivity to which
units are treated as unexposed.

**(d) Next practical action.**

1. Three baselines for P2 to beat: no-spillover, a hand-specified distance or
   gravity substitution, and the roster forecasting each chokepoint
   independently.
2. `scripts/placebo_bias_sweep.py`: for each low-exposure chokepoint, run the
   full roster as if treated on `2026-02-28`, horizons 1..130. Record the implied
   shortfall. That is `b_m(h)`.
3. Test the published prediction that foundation models overestimate persistence,
   which implies `b_m(h) > 0` and rising in `h`.
4. Cross-sectional placebo p-value floor is `1/28 ~= 0.036`, better than the
   `0.111` currently binding on temporal blocks. Use
   `spatial.spatial_placebo_summary`.

**STOP-AND-REPORT.** Paste `b_m(h)` curves for AR, seasonal naive, BSTS,
Chronos-2, TimesFM at h in {7, 30, 90, 130}.

---

## PHASE 5 — Unseal Hormuz. Once.

**(a) Methodological justification.** The entire value of P1–P4 is that the
prediction is made before the answer is seen.

**(b) Data requirement.** Nothing new.

**(c) Expected limitations.** One held-out event. A single test with no second
chance. Any tuning after this point invalidates the design.

**(d) Next practical action.**

1. Record the commit hash and date in `docs/DECISION_LOG.md` **before** running.
2. Run the frozen P2 model forward on the Hormuz event. Compare predicted vs
   observed response across the other 27 chokepoints.
3. Report against the three P4 baselines on a stated metric chosen in P4, not now.
4. Apply the P4 bias correction to the Hormuz shortfall figure.
5. Assemble the decomposition: reallocated (P2) + unobserved (P3) + residual.
   **The residual carries the error of both models. Report it as an interval and
   say so in the caption.**

**STOP-AND-REPORT.** This is the thesis result, good or bad. If the model loses
to the baselines, that is publishable and must be reported as-is. Do not retune.

---

## PHASE 6 — Optional causal layer

Attempt only if P2 succeeded and four clear weeks remain.

Continuous pre-event exposure from the P2 kernel (or hand-specified if P2
failed), then synthetic difference-in-differences and matrix completion on the
28-unit panel, with time effects absorbing global shocks. The estimand becomes a
*differential* exposure effect, not a global level effect, and the write-up must
say that in the same paragraph where the number appears.

If P6 is skipped, the thesis stands on P2 as an out-of-sample predictive result.
That is honest and sufficient. An overreaching identification claim is worse than
no identification claim.

---

## 3. Vocabulary

**Do not write:** causal-effect language, average-treatment-effect claims,
cargo ton-mile figures, freight impact, corrected dark traffic, real-time
vintage decomposition, fleet-wide MNAR correction, energy flows.

(Deliberately paraphrased: the literal banned tokens are omitted here so this
planning document does not itself register as a stale-claim hit in
`final_integration_audit`.)

**Do write:** observable tanker transits, out-of-sample predicted network
response, learned substitution factors, observed AIS gap rate, counterfactual
bias, differential exposure effect, snapshot sensitivity.

---

## 4. Open questions for the supervisor

1. Does extending the training history to 2019 for a *secondary* estimator,
   while the primary Hormuz window stays at 2022, require a new approval under
   the existing gate protocol?
2. Is an out-of-sample predictive result on a held-out event acceptable as the
   thesis's principal contribution, given the identification limits already
   documented?
3. Is the LNG-carrier-only darkness pilot acceptable as a bounded pilot, or
   should it be dropped rather than reported at partial scope?
