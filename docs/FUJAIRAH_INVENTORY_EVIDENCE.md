# Fujairah FEDCom inventory evidence

**Added:** 2026-08-28. **Status:** evidence collected and validated.
**Licensing: ADJUDICATED 2026-08-28 — admissible on a cite-do-not-redistribute
basis.** Individual weekly figures are cited to their own freely-readable
articles; the assembled series stays local and gitignored; the bunker
assessment file is excluded outright. See
`data/raw/fujairah_fedcom/SOURCES.md` and the decision log entry of
2026-08-28.

## What this is

Weekly oil product inventories at Fujairah, published by the Fujairah Energy Data
Committee, 19 observed weeks from 2026-02-16 to 2026-08-10, with 7 gaps carried
explicitly. Build and validation: `scripts/build_fujairah_inventory_panel.py`.

It is a **physical, non-AIS** measurement at the port that ADCOP makes the
designated outside-Hormuz outlet. It shares no sensor, no transponder and no
processing pipeline with PortWatch. That independence is the entire reason it is
worth having.

## Headline movements

| | date | total mn bbl |
|---|---|---:|
| peak | 2026-03-02 | 20.786 |
| trough | 2026-06-15 | 5.145 |

Peak to trough **−75.2%**; against the last pre-onset reading (2026-02-23,
20.528) **−74.9%**. Nine consecutive weekly draws from the peak.

## Bearing on Open Defect A — the undiscussed pre-event run-up

Defect A in `Archive/Planning_Superseded_2026-08-30/THESIS_STATE_OF_RECORD_2026-08-28.md` is the pre-collapse
run-up to roughly 85 transits/day in mid-February that no chapter discusses, and
which — if anticipatory — biases the AR(1,7) counterfactual upward and inflates
the 6,869 shortfall (AR(1,7), trained on `panel_aligned.csv` from 2022-01-01;
the figure is specification-dependent, see
`experiments/network_adaptation/outputs/hormuz_shortfall_specification_sensitivity.csv`).
It is ranked the highest examiner risk and currently has no answer.

This series bears on it directly:

- Light distillates reached **9.888 mn bbl in the week to 2026-02-16, +24%
  week-on-week and the highest since June 2019**.
- Total stocks held at 20.5–20.8 mn bbl across 16 Feb, 23 Feb and 2 Mar, peaking
  the day before the FOIZ fire.

A physical stock build at the region's principal storage hub in the fortnight
before the operational onset is the observable signature anticipatory behaviour
would leave. It does not remove the bias. What it does is convert *an
undiscussed anomaly inside our own AIS-derived series* into *a documented
pre-event build corroborated by an independent physical source*, and it licenses
Chapter 9 to state the **direction** of the bias — counterfactual biased upward,
6,869 therefore upper-leaning — as an evidenced claim rather than a concession.

**Honest limit:** only two pre-onset weekly observations were collected. This is
suggestive, not established. Testing whether a +24% weekly jump in light
distillates is unusual requires the pre-2026 history — see Extension below.

## Bearing on Chapter 11 — why the bypass did not function

`Research Record/decision-outcome-variable.md` concludes from the chokepoint panel
that "Hormuz has no bypass. The ships did not reroute; they did not sail."

This series supplies the mechanism, and the source states it outright. From the
report for the week ended 2026-05-04: *ships carrying products have largely been
unable to pass through the Strait of Hormuz to unload at Fujairah.*

ADCOP carries Abu Dhabi crude to Fujairah without transiting the strait, so for
**crude export** Fujairah is a genuine bypass. But Fujairah's storage and
bunkering function depends on **seaborne product arriving through the strait**.
When the strait closed, the export bypass held and the import function failed:
light distillates −86%, heavy −73% from onset to trough, and ships began
bunkering in India and West Africa instead.

**A bypass that cannot be resupplied is not a bypass.** This corroborates an
existing conclusion with a mechanism. It introduces no new estimand and no
causal claim, so it is compatible with the manuscript's non-causal rule.

## What this evidence does NOT support

- It does **not** isolate AIS undercount. A drawdown shows outflow exceeded
  inflow; the reports attribute that to blocked *inbound* resupply, not to
  unobserved dark exports. A mass balance would additionally need imports and
  bunker sales, and would still not separate real disruption from measurement
  loss. Any claim that this quantifies the dark-vessel bound is unsupported.
- It does **not** establish causality, and must not be written as if it does.
- There was a **real physical shock at the port**: a FOIZ fire on 2026-03-03 from
  intercepted-drone debris, after which Fujairah Oil Tanker Terminals suspended
  operations and sent vessels to anchorage, plus at least seven attacks. Part of
  the observed collapse is genuine disruption, not measurement failure.

## Extension

`https://www.hellenicshippingnews.com/?s=FUJAIRAH+DATA` is walkable back to the
series start in January 2017 (~490 weekly observations, roughly one page fetch
per week). Collecting 2023–2025 would give the pre-period needed to test whether
the February 2026 build is anomalous against its own history. That is the single
highest-value extension of this file and it is mechanical.
