# Captivity & adaptive capacity: design and variable specification

**Prepared:** 2026-06-22
**Status:** Methodology design + variable-construction specification.
**HARD BOUNDARY:** This document contains **no modelling code** and no fitted
results. Outcome/covariate *construction* is specified; outcome *modelling* is
deferred until the spec is frozen and (per project rules) the scope is approved.
**Supersedes nothing yet** — this elevates the throughput-shortfall work
(`CORRIDOR_TRANSMISSION_RESULTS.md`, AR pipeline) from the *destination* to the
*foundation layer* of a heterogeneous-vulnerability event study (Option D).

## 0. What changed and why

The public-data AR/PortWatch pipeline answers a magnitude question ("how much did
Hormuz throughput fall?"). That is now the **anchor / foundation**, not the
thesis. The elevated question is heterogeneity and mechanism: *who was captive,
what structural factors explain it, and how did the shock propagate through
observable vessel flows?* This reconnects the energy-security stream and the
causal-ML heterogeneity machinery (DML / causal forests) that the original
proposal specified and then dropped. See `GAP_VALIDATION.md`.

## 1. Research question and title

**RQ:** How did the 2026 Strait of Hormuz disruption propagate through global
energy-import systems, and which importer-level **exposure** and **adaptive-
capacity** factors explain heterogeneous vulnerability?

**Working titles:**
- "Captivity and Substitution in a Maritime Energy Shock: Importer Vulnerability
  to the 2026 Strait of Hormuz Disruption."
- (technical) "Network Exposure and Adaptive Capacity in Global LNG Security:
  Evidence from the 2026 Strait of Hormuz Disruption."

## 2. Estimand (frozen before estimation)

Primary specification, importer panel `i`, period `t`:

```
Y_it = α_i + δ_t + β (Post_t × Exposure_i) + γ (Post_t × Flexibility_i) + X_it'θ + ε_it
```

- `α_i` importer fixed effects (absorbs time-invariant importer levels).
- `δ_t` period fixed effects (**absorbs the common global shock and any
  world-price/seasonal movement common to all importers**).
- `Exposure_i`, `Flexibility_i` are **pre-shock, predetermined** (Section 5–6).
- `Post_t` = 1 for t ≥ 2026-02-28 (operational-onset cutoff; locked project-wide,
  see `EVENT_CHRONOLOGY.md`).

**What is identified:** `β` (and `γ`) — the **differential** post-shock change in
the outcome associated with pre-shock captivity, conditional on common time
shocks and controls. This is a continuous-treatment / interaction
difference-in-differences gradient.

**What is NOT identified and must never be claimed:** the average/level effect of
the closure on world energy supply. `Post_t` alone is collinear with `δ_t`; the
common effect is *absorbed by design*, not estimated. The headline claim is a
**differential**, stated as "disruption-associated," not an ATT on the world.

This is the design-based causal stance you selected: a defensible differential
estimand, deliberately weaker than a randomized ATT, and much harder to dismiss
than a level effect from a single event.

## 3. Gap (reconciled with the verified literature)

> No public-data study estimates the **realized, importer-level heterogeneous
> vulnerability** to a maritime chokepoint shock as a function of pre-shock
> exposure and adaptive capacity, with the substitution mechanism traced through
> observable vessel flows.

Not occupied by: Verschuur 2025 (ex-ante systemic risk), Meza 2026 (simulated
Hormuz importer losses), Polemis 2025 / Yang 2026 SAR (aggregate / monitoring),
Farag 2025 / Neumann 2009 (price integration). No "first study" language; the
contribution is the realized, public-data, heterogeneity-plus-mechanism design.

## 4. Hypotheses

- **H1 (exposure gradient):** higher pre-shock Hormuz/Gulf exposure ⇒ larger
  post-shock fall in Gulf-sourced intake. Sign: `β < 0` on Gulf-source outcome.
- **H2 (adaptive-capacity moderation):** flexibility attenuates the exposure
  effect ⇒ captive = high exposure **and** low flexibility. Tested via the `γ`
  term and an Exposure×Flexibility interaction.
- **H3 (substitution / resilience):** total intake is defended where flexibility
  is high, even as Gulf-source intake falls — i.e. the loss shows up in *source
  composition*, not totals (the demand-side analogue of the repo's
  "contraction + substitution, not multiplier"). Tested on secondary outcomes.
- **H4 (network propagation):** alternative chokepoints/routes/vessel classes show
  abnormal post-shock activity consistent with rerouting (spillover chapter;
  also the interference robustness check for the main design).

H4 is intentionally framed as **propagation diagnostics / spillover mapping**, not
full causal-graph recovery. If PCMCI or similar is used, it is exploratory
structure-learning under explicit assumptions, anchored theoretically in the
interference framework (Hudgens & Halloran 2008).

## 5. Identification: assumptions and the three threat-defenses

**Assumptions.**
1. **Conditional parallel trends on the interaction:** absent the shock, high- and
   low-exposure importers' outcomes would have evolved in parallel after
   conditioning on `X_it`. (Not parallel *levels* — parallel *trends*.)
2. **Predetermined treatment intensity:** `Exposure_i` and `Flexibility_i` use
   strictly pre-shock windows; no post-shock information enters them.
3. **No anticipation** before the cutoff (auditable against
   `EVENT_CHRONOLOGY.md`).
4. **Stable-composition panel** over the window (handle entry/exit explicitly).

**Threat-defense 1 — exposure is confounded with region/demand.** Gulf-exposed
importers cluster in Asia; Asian demand had its own 2026 dynamics.
→ Pre-trend test on the interaction (event-study leads must be flat); region and
demand controls in `X_it`; **placebo-exposure test** (randomly permute
`Exposure_i`; the gradient must collapse).

**Threat-defense 2 — interference / SUTVA (substitution contaminates controls).**
A captive importer chasing Atlantic cargoes moves price/availability for the
low-exposure "controls."
→ The **spillover chapter (H4) doubles as the bias diagnostic**: if cross-importer
spillover is small, the differential is clean; if large, we *bound* the bias and
report it. This is the principled response interference theory licenses.

**Threat-defense 3 — small N / over-fitting.** ~20–40 importer units.
→ Transparent 2WFE interaction is the **headline**; ML estimators are confined to
nuisance control and variable-importance (Section 8). Inference by **wild cluster
bootstrap**, not asymptotic SEs. Pre-registered outcome hierarchy prevents
specification search.

## 6. Variable construction specification

All series enter through `registry.get_variable()` and are declared in
`config/sources.yaml` with provenance (per `CLAUDE.md`). Status flags below:
**[HELD]** already in repo · **[PUBLIC]** free pull, not yet wired ·
**[VERIFY]** value/source must be confirmed before use (no assertion).

### 6.1 Unit set (importers `i`)

Binding constraint = by-source import coverage. Core captive panel: Japan, South
Korea, China, Taiwan, India, Pakistan, Bangladesh. Resilient comparator: EU
(and/or member states). Extended LNG-importer pool for donor/robustness as
by-source data permits. Gulf **exporters** (Qatar, UAE, Kuwait, etc.) are modelled
on the *supply side separately*, not as panel units.

### 6.2 Treatment timing

- `Post_t`: 1 for t ≥ **2026-02-28**. Training/pre-windows strictly before it.
  Milestone dates are sensitivity windows only, never alternative cutoffs.

### 6.3 Outcomes (construct ALL; primary follows the estimand, not the result)

| Tag | Outcome `Y_it` | Construction | Sources | Status |
|---|---|---|---|---|
| **Y1 (PRIMARY)** | Gulf-sourced LNG imports — volume **and** share | Σ imports from Hormuz-dependent exporters (Qatar, UAE, Kuwait, Iraq, Saudi, Bahrain, Iran) ÷ total; and level | Comtrade HS 271111 by-partner; Eurostat `nrg_ti_gasm` by partner; PPAC (India); MOF/e-Stat (Japan); GFW terminal-arrival reconstruction where official by-source missing | [HELD]/[PUBLIC] |
| Y2 (secondary) | Total LNG (and gas) import volume | Total intake, all sources | same feeds; EIA for US export side | [PUBLIC] |
| Y3 (secondary) | Substitution intensity | Δ non-Gulf-sourced volume ÷ pre-shock total intake (Atlantic/US/African/Australian/SE-Asian growth) | by-source feeds; EIA `move/expc` for US supply | [PUBLIC] |
| Y4 (secondary) | Composite vulnerability index | standardized blend of (un-substituted Gulf-source loss) + storage drawdown + delay/days-to-deliver; weights pre-registered (equal-weight default; PCA as robustness) | combines Y1/Y3 + storage + GFW delay | [VERIFY] (construction) |

Coverage caveat already known: Comtrade 271111 has 2026 monthly only for
USA + Japan; others blank → GFW reconstruction and national stats fill the panel;
JODI-Gas free bulk CSV is stale (ends 2018) — do **not** use. Re-pull national
feeds in July (India May figure not yet in PPAC at last probe).

### 6.4 Exposure_i (pre-shock captivity)

Predetermined over a pre-shock window (default: 2023–2025 average; freeze before
estimation).

| Component | Construction | Sources | Status |
|---|---|---|---|
| Gulf-source import share | mean pre-shock share of imports from Hormuz-dependent exporters | by-source feeds (6.3) | [PUBLIC] |
| GFW exposure index | `pre_hormuz_exposure_capacity_share_pct` | `importer_exposure_summary.csv` | [HELD] |
| (optional) oil co-exposure | pre-shock Gulf crude share, if oil outcomes added | Comtrade HS 2709; EIA | [PUBLIC] |

`Exposure_i` = standardized composite of the above (primary: Gulf-source LNG
share; GFW index as convergent-validity check).

### 6.5 Flexibility_i / adaptive capacity (pre-shock)

| Component | Construction | Candidate source | Status |
|---|---|---|---|
| Regasification slack | (regas capacity − throughput) ÷ capacity, pre-shock | GIIGNL; GEM Global Gas Infrastructure Tracker | [VERIFY] |
| Storage buffer | working-gas / inventory ÷ avg monthly demand | EU: AGSI/GIE; national stats | [VERIFY] |
| Supplier diversity | 1 − HHI of import-source shares | by-source feeds (6.3) | [PUBLIC] |
| Contract flexibility | spot vs long-term / destination-free share | GIIGNL | [VERIFY] |
| Pipeline alternative | share of gas importable by pipeline (dummy/continuous) | ENTSOG; national | [VERIFY] |
| Alt-supplier distance | sea distance to nearest non-Gulf supplier | searoute/AIS-derived | [HELD]/[PUBLIC] |

`Flexibility_i` = standardized composite (equal-weight default; report component
sensitivity). **Heavily [VERIFY]** — do not enter any GIIGNL headline figure (e.g.
the 428 MT / 35% spot / 1,247 MTPA values raised in discussion) until confirmed
against the GIIGNL 2026 report.

### 6.6 Controls X_it (time-varying)

Region/bloc dummies; heating/cooling degree-days; industrial-production proxy;
seasonal terms; world LNG price level (e.g. JKM/TTF — source [VERIFY], used only as
a *common* control, since `δ_t` already absorbs common price). Controls enter the
2WFE directly and, in the DML arm, as high-dimensional nuisance.

## 7. Mapping to existing assets (foundation reuse)

- **AR/PortWatch shortfall** → the treated-series anchor and the Hormuz-side
  magnitude; also generates the `δ_t`-orthogonal "how big at the strait" number
  that motivates the importer panel.
- **GFW importer exposure + Gulf departures −93%** → Exposure_i and the supply-side
  validation.
- **Donor-contamination screen** → repurposed as the H4 spillover diagnostic.
- **TSFM benchmarks (Chronos-2/TimesFM-2.5/Moirai)** → counterfactual-validation
  chapter (Section 8, role C).

## 8. Estimator hierarchy (roles only — NOT to be coded yet)

| Layer | Method | Role | Honest limit |
|---|---|---|---|
| **Headline** | Two-way fixed-effects interaction (Section 2) | The identified differential `β`, `γ` | Linear; small-N inference needs wild cluster bootstrap |
| Robustness / nuisance | Double/debiased ML (cross-fitted) | Low-dim causal param with ML-controlled high-dim `X_it` | Underpowered as headline at N≈20–40; supportive only |
| Heterogeneity ranking | Causal forest / GRF | Rank which captivity components drive vulnerability | Not fine-grained CATEs; variable-importance, not proof |
| Mechanism (Ch. B) | Spillover/propagation diagnostics; optional PCMCI | Trace rerouting; **bias diagnostic for headline** | Exploratory structure-learning under assumptions |
| Counterfactual validation (Ch. C) | TSFM vs AR + conformal intervals | Validate the no-disruption benchmark before use | Prediction ≠ identification — benchmark discipline only |

ML is used for its real statistical job (nuisance control, variable importance),
**never as decoration and never as the causal claim**.

## 9. Inference

Wild cluster bootstrap over importer clusters (small-N); event-study lead/lag
coefficients for pre-trends; multiple-outcome control across Y1–Y4 (primary Y1
carries the confirmatory test, Y2–Y4 are mechanism/robustness, labelled as such).

## 10. Falsification cascade

1. Pre-trend (event-study leads flat on the interaction).
2. Placebo-exposure (permuted `Exposure_i` ⇒ null gradient).
3. Placebo-timing (false cutoff before 2026-02-28 ⇒ null).
4. Leave-one-importer-out (no single unit drives `β`).
5. Spillover bound (H4): cross-importer interference small, or bias bounded.
6. Outcome-composition check (loss in source mix, not totals — H3).

## 11. Limitations / what this cannot claim

- Not an ATT on world energy supply; a **differential** across importers only.
- One event ⇒ heterogeneity is design-based + predictive, not experimentally
  identified; "captive" is a structural condition associated with larger losses,
  not a proven cause.
- By-source coverage is uneven (Comtrade gaps); GFW reconstruction carries the AIS
  measurement caveats (darkening — Fernández-Villaverde et al. 2025) and is itself
  bounded, not ground truth.
- Flexibility components are partly [VERIFY]; the index is only as good as its
  weakest confirmed input.

## 12. Pre-registration freeze checklist (do before any modelling code)

- [ ] Lock the importer unit set and panel frequency.
- [ ] Lock Exposure_i window + components and Flexibility_i components/weights.
- [ ] Lock primary outcome = Y1 (Gulf-source); Y2–Y4 declared secondary.
- [ ] Lock controls and the `δ_t` absorption logic.
- [ ] Lock the falsification cascade (Section 10) and inference (Section 9).
- [ ] Resolve every [VERIFY] (esp. GIIGNL, storage, contract flexibility).
- [ ] Confirm scope with Prof. Li (estimand is a differential, not an ATT).

## 13. Consistency actions (academic-integrity audit, task C7)

- Rewrite the proposal's three-stream gap, title, and RQ to the captivity
  differential estimand (the old freight/ton-mile/mediation framing is retired).
- Keep `GAP_VALIDATION.md` §4 contribution wording synchronized with Section 3.
- Carry the §11 "cannot claim" list verbatim into Discussion/Limitations.

## 14. Data-honesty register

- GIIGNL 2026 figures (428 MT imports, 35% spot, 1,247 MTPA regas) — **user-
  provided, UNVERIFIED**; confirm against the GIIGNL 2026 report before any use.
- JODI-Gas free bulk CSV stale (ends 2018) — excluded.
- Comtrade 271111: 2026 monthly only USA + Japan at last probe — re-pull July.
- No headline number enters the thesis without a primary-source check (same
  standard as `CITATION_INTEGRITY_AUDIT.md`).
