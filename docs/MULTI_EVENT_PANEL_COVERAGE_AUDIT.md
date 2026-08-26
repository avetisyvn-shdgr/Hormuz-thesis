# Phase 1 coverage audit — multi-event chokepoint panel

**Date:** 2026-08-26 · **Branch:** `ml/multi-event-propagation`
**Spec:** `config/multi_event_propagation.yaml` (status: `draft_not_frozen`)
**Gate:** Phase 1 of `ML_TRAINING_ACTION_PLAN.md`

> **Provenance of the numbers below.** They were computed directly from
> `data/raw/portwatch/Daily_Chokepoints_Data.csv` with a standalone read, NOT by
> running `scripts/build_multi_event_panel.py`. That script has been written and
> compiles, but it has not been executed: the repository venv is not runnable
> from the assistant's environment, and CLAUDE.md rule 4 reserves execution to
> Mher. **Run the script and confirm these figures reproduce before freezing the
> spec.**

## 1. Gate question

Is the pre-2022 history usable, or does its measurement definition differ from
the 2022+ window the primary path already uses?

**Answer: usable.** Coverage is complete and no year boundary shows a shift
attributable to definition change rather than to a real event.

## 2. Completeness

| Property | Value |
|---|---|
| True snapshot coverage | **2019-01-01 → 2026-07-12** |
| Current primary `study_window.full_start` | 2022-01-01 |
| History discarded by the primary window | **1,096 days per chokepoint** |
| Chokepoints | 28 |
| Days per chokepoint | 2,750, identical for all 28 |
| Missing days | **none** |

Days per year: 2019 365 · 2020 366 · 2021 365 · 2022 365 · 2023 365 · 2024 366 ·
2025 365 · 2026 193 (partial to 07-12). Every year is exactly complete.

## 3. Year-boundary screen

> **Correction, 2026-08-26.** An earlier version of this section claimed six
> moves exceeded +/-60%. That was wrong. The figure came from a scratch check
> using asymmetric thresholds (ratio >1.6 or <0.625), and <0.625 is -37.5%, not
> -60%. The committed script applies a symmetric +/-60% and finds **two** on
> `n_tanker`. The substantive conclusion is unchanged: every flagged move is a
> known event and none sits at a 2019/2020, 2020/2021 or 2021/2022 boundary.

Confirmed by `scripts/build_multi_event_panel.py`, run by Mher 2026-08-26.

**`n_tanker` — 2 jumps beyond +/-60%:**

| Chokepoint | Boundary | Mean -> mean | Change | Adjudication |
|---|---|---|---|---|
| Cape of Good Hope | 2023->2024 | 9.2 -> 18.9 | +104% | Red Sea rerouting destination |
| Kerch Strait | 2022->2023 | 6.0 -> 2.2 | -64% | Black Sea closure |

**`n_container` — 2 jumps beyond +/-60%:**

| Chokepoint | Boundary | Mean -> mean | Change | Adjudication |
|---|---|---|---|---|
| Bab el-Mandeb | 2023->2024 | 18.4 -> 5.4 | -71% | Red Sea attacks |
| Cape of Good Hope | 2023->2024 | 6.2 -> 19.0 | +209% | Red Sea rerouting destination |

Moves between -37.5% and -60% that the symmetric screen does not flag, but which
are real and matter for Phase 2: Bab el-Mandeb tanker -55%, Suez tanker -44%,
Suez container -54%, Kerch tanker -45% (2021->2022) and -45% (2023->2024).

2020 shows no tanker-transit collapse. The largest 2019->2020 move is Bohai
Strait, 29.7 -> 41.0 (+38%), consistent with Chinese crude stockpiling during the
2020 price collapse. Treat 2020 as usable with a period indicator rather than
excluding it.

## 4. Event-by-event verification

### 4.1 Ever Given — recovered, and it earns the history extension on its own

Suez Canal, `n_tanker`:

| Window | Mean/day |
|---|---|
| Baseline 2021-02-01 → 03-22 | 16.7 |
| Blockage 2021-03-24 → 03-29 | **4.0** |
| Rebound 2021-03-30 → 04-10 | 21.1 |

Daily trough: 4, 4, **0**, 2, 3, 3 on 23–28 March, back to 12 on the 29th. A
clean 76% drop with an unambiguous start, end, and post-clearance overshoot.

**Cape of Good Hope did not respond**: 12.1 → 13.3 → 14.7 across the same three
windows. A six-day closure is shorter than the decision horizon for a Cape
reroute, so no substitution occurs.

This is the finding that justifies extending the window. Ever Given supplies the
**no-substitution** end of a duration axis that the 2022+ window cannot provide,
and without it the model has only long events and cannot learn that shock
duration governs whether traffic reroutes or simply waits.

### 4.2 Red Sea — the sanity-gate edge is unambiguous

Monthly means, `n_tanker`:

| Month | Bab el-Mandeb | Suez | Cape of Good Hope |
|---|---|---|---|
| 2023-01 | 25.0 | 24.5 | 8.6 |
| 2023-10 | 26.9 | 25.5 | 10.0 |
| 2024-01 | 14.1 | 16.2 | 15.6 |
| 2024-10 | 10.2 | 14.1 | 20.5 |

Cape roughly doubles as the other two roughly halve. The Bab el-Mandeb → Cape
edge required by the spec's `sanity_gate` is plainly present in the raw data, so
a fitted kernel that misses it is a bug in the fit, not an absence in the world.

### 4.3 Panama drought — weak, and NOT a container story

> **Correction, 2026-08-26.** An earlier version of this section asserted the
> drought hit container and gas carriers harder than tankers, and recommended
> fitting Panama on `n_container`. The data says the opposite. That
> recommendation was wrong and is withdrawn.

Panama Canal daily means by vessel type:

| Period | `n_tanker` | `n_container` | `n_total` |
|---|---|---|---|
| 2023 H1 (pre) | 12.7 | 7.4 | 32.1 |
| 2023 H2 (restrictions) | 12.1 | 7.7 | 28.2 |
| 2024 H1 (trough) | **9.9** | **7.2** | **22.9** |
| 2024 H2 (recovery) | 12.2 | 8.1 | 30.0 |
| 2025 (normal) | 12.6 | 7.9 | 31.0 |

Trough against pre-period: **tanker -22%, container -2%, total -29%.**

Container traffic was essentially unaffected while total transits fell 29%. The
most plausible reading is that slot rationing protected contracted liner
services, which hold long-term booked slots, and pushed the entire cut onto
spot, bulk and tanker traffic. That is a priority-allocation mechanism, and it is
worth a sentence in the thesis on its own.

**Consequences for Phase 2.** Fit Panama on `n_total` and `n_tanker`, not
`n_container`. Even then the response is roughly a fifth of the Red Sea's, so
Panama stays a secondary training event and a null result there is expected.

### 4.4 Signal strength differs by vessel type, so fit both

Red Sea, 2023 against 2024 annual means:

| Chokepoint | `n_tanker` | `n_container` |
|---|---|---|
| Bab el-Mandeb | 25.9 -> 11.6 (-55%) | 18.4 -> 5.4 (**-71%**) |
| Suez Canal | 25.5 -> 14.3 (-44%) | 19.1 -> 8.7 (**-54%**) |
| Cape of Good Hope | 9.2 -> 18.9 (+104%) | 6.2 -> 19.0 (**+209%**) |

The Red Sea is a stronger container signal than tanker signal. Panama is a
tanker and total signal with no container signal. Hormuz is a tanker event. The
three training events therefore do not share a single best outcome column, and
fitting the kernel across `n_tanker`, `n_container` and `n_total` becomes a
genuine cross-outcome transfer test rather than a robustness afterthought.

## 5. Verdict and residual risks

**Phase 1 gate: PASS.** Extend the training window to 2019-01-01 for the
secondary estimator. Leave `study_window.full_start` at 2022-01-01.

Residual risks to carry into Phase 2:

1. **2020 confounding.** A global demand shock inflates apparent cross-chokepoint
   correlation. Carry a period indicator; report fits with and without 2020.
2. **Red Sea onset date is a draft.** `2023-12-15` in the spec must be reconciled
   against `EVENT_CHRONOLOGY.md` and frozen before fitting.
3. **Event count is still small.** Four usable events, one of them weak on the
   primary outcome. Leave-one-event-out is mandatory, not optional.
4. **Suez appears in two events** (Ever Given 2021, Red Sea 2023–24). Ensure the
   design matrix does not let one unit's two episodes act as independent draws.

## 6. Next actions

1. DONE 2026-08-26 - script run by Mher; figures confirmed, threshold claim corrected.
2. DONE 2026-08-26 - Panama is not a container story; see 4.3.
3. Adjudicate the Red Sea onset date against `EVENT_CHRONOLOGY.md`.
4. Record the 2020 handling decision in `DECISION_LOG.md`.
5. Set `status: frozen` and `frozen_on` in `config/multi_event_propagation.yaml`.
6. Only then begin Phase 2.
