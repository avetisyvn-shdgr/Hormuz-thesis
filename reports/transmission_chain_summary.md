# Transmission chain — cross-source evidence cascade

**Status:** Exploratory synthesis, updated 2026-07-18. Packages frozen results;
computes nothing new. This chain uses the **94-day mechanism/corridor-aligned
window** so Layer 1 lines up with the GFW/WTO and corridor-validation branches.
It is **descriptive triangulation**, not a causal ton-mile multiplier. The active
primary PortWatch headline remains the 130-day AR-only counterfactual in
`reports/run_output.md` and `reports/current_results_summary.md`.

## The one-paragraph argument

A Strait-of-Hormuz disruption shows up as a **cascade across five independent
evidence layers** in the 94-day mechanism-aligned window. (1) Hormuz tanker
throughput collapses ~95% below its own pre-treatment counterfactual, and the
gap separates from a clean donor pool even under a pessimistic contamination
screen. (2) The collapse is **commodity-specific and cross-validated**:
GFW-inferred Gulf LNG departures and the
independent WTO/AXSMarine outbound index both fall ~93–99% with no calibration.
(3) The LNG fleet **contracts**: resolved Gulf voyages and aggregate inferred
capacity-distance both decline. (4) Among voyages that still complete, mean
capacity-distance **rises ~10%**, but a Kitagawa/Oaxaca decomposition shows this
is overwhelmingly a **route-composition shift, not route elongation**. (5)
Consistent with substitution, **alternative corridors rise** (Cape of Good Hope,
Yucatan, Panama). The honest reading is **contraction plus substitution**, not an
aggregate ton-mile multiplier — the strong freight-multiplier claim is not
supported on free data and is explicitly retired.

## The cascade

| step | layer | independent_source | metric | pre_value | post_value | percent_change | corroboration | interpretation_boundary |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Chokepoint disruption | IMF PortWatch (satellite AIS) | Strait of Hormuz tanker transits, 94-day mechanism-aligned window | 5366.3 | 245.0 | -95.4 | mean-scaled corridor statistic -95.5%; donor synthetic control 4.2x separation (survives pessimistic screen); Romano-Wolf p=0.10 | 94-day corridor synthesis; not the 130-day primary headline or an identified ATT |
| 2 | Commodity-specific export collapse | GFW port visits + WTO/AXSMarine index (two sources) | Gulf LNG departures: GFW calls / WTO outbound index | 171.0 | 12.0 | -93.0 | WTO index 101.5->1.7 (-98.3%), no calibration applied | inferred departures, not observed cargo tonnage |
| 3 | Fleet-activity contraction | GFW voyage reconstruction (624-carrier census) | Resolved Gulf LNG voyages (30km, expanded route QA) | 948.0 | 726.0 | -23.4 | aggregate inferred capacity-distance -15.6% (also a decline) | terminal-sequence inference; right-censoring present |
| 4 | Routing composition shift | GFW capacity-nautical-mile reconstruction | Mean capacity-distance per retained voyage |  |  | 10.2 | BCa 95% CI [+4.4%, +17.0%]; 98% of common-route change from route composition; entry/exit residual separate | common-route composition effect plus entry/exit residual; NOT observed laden ton-miles |
| 5 | Destination substitution | IMF PortWatch corridor map | Alternative corridors above counterfactual |  |  |  | risers: cape_of_good_hope +46%, yucatan_channel +23%, panama_canal +21% | descriptive; no voyage-level flow tracing |

## Interpretation boundaries (load-bearing)

- Window discipline matters: this table is the 94-day corridor/GFW-WTO-aligned
  synthesis window. Do not cite its 5,366 counterfactual or 245 observed transits
  as the active 130-day primary headline.
- Every layer is descriptive; none establishes a causal ATT or observed cargo
  ton-miles or freight rates (those need proprietary access that is unavailable).
- Layers 2–4 rest on terminal-sequence inference (laden state not observed) and
  carry right-censoring and AIS-coverage caveats.
- The cross-source agreement in layer 2 is the strongest single result and should
  anchor the narrative; the foundation-model work is a forecasting cross-check
  only.
