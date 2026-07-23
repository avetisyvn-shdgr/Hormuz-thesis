# Gap validation

**Prepared:** 2026-06-22
**Purpose:** Test the proposal's hypothesized gaps against the verified
literature (`LITERATURE_MATRIX.md`, all citations confirmed in
`CITATION_INTEGRITY_AUDIT.md`); reject any gap already addressed elsewhere; and
state the narrowest surviving contribution **without "first study" overclaims**.
**Companion:** `DESIGN_TO_LITERATURE_GAP_MATRIX.md` (design-element comparison).

## 0. Critical precondition: the estimand pivoted

The proposal's gaps were written for the **original** estimand — the effect of
the 2026 Hormuz disruption on **LNG spot freight rates**, identified via a
debiased dose-response + donor synthetic control + **mediation decomposition**
(g-formula) + war-risk equivalence test + **causal-direction-reversal** (PCMCI)
cascade, targeting a **ton-mile / fleet-vacuum** logistics channel.

That design was **abandoned / demoted** (supervisor-approved pivot 2026-06-16;
see `ESTIMAND_PROPOSAL_RECONCILIATION.md`, `PROPOSAL_CITATION_AUDIT.md`). The
working study estimates a **disruption-associated shortfall in observable Hormuz
tanker throughput** (PortWatch), explicitly **non-causal**, with freight-rate
dose-response, mediation, and causal discovery removed.

**Consequence for gap validation:** any part of the proposal's gap that depends
on freight rates, a destructive mediator, dose-response, or the ton-mile channel
is testing a study the thesis **no longer performs**. Those parts are not
"surviving gaps"; they are out of scope. This is flagged here because the title,
RQ, hypotheses, and gap prose must be reconciled to the pivot (academic
consistency — see §5 and task C7).

## 1. The three hypothesized gaps (as written in the proposal)

The proposal (`Thesis_Proposal_MA`, §"three streams") frames the gap as three
streams that "each approach the problem and stop short of it":

- **G1 — Chokepoint & energy-security economics.** Establishes the phenomenon
  but "studies prices and quantities rather than transport-work."
- **G2 — Causal inference for single-event interventions** (ITS, synthetic
  control + augmented/doubly-robust variants, debiased ML, causal discovery).
  Supplies identification scaffolds but "has not been applied to a coupled-basin
  freight setting with no clean control."
- **G3 — Modern time-series machine learning.** Supplies flexible counterfactual
  generators but "treats prediction as if it were identification."

Synthesized "triad" gap: *"no existing design can identify a logistics-channel
effect when the control unit is itself treated and a destructive mediator sits on
the causal path."*

## 2. Testing each gap against the verified literature

Verdicts: **REJECTED** (literature already addresses it), **PARTIAL/REFRAMED**
(survives only in narrowed, non-causal form), **OUT OF SCOPE** (depends on the
abandoned freight/mediation estimand), **SURVIVES**.

| Gap | What it claimed was missing | Verified literature that bears on it | Verdict | Reason |
|---|---|---|---|---|
| **G1** | Chokepoint/energy econ studies prices & quantities, not the realized event | Pratson 2023; Verschuur 2025; An 2026; Neumann 2009; Farag 2025; Meza 2022/2026 | **PARTIAL/REFRAMED** | Correct that these are scenario/risk/price/integration estimands — none estimates the **realized daily throughput shortfall**. But the gap is *not* "transport-work has never been studied"; it survives only as "no public-data observed-shortfall estimate for this event." |
| **G1 (observation sub-claim)** | The 2026 Hormuz event is unobserved in public data | **Yang 2026 SAR** (same event, Sentinel-1, IMF-validated) | **REJECTED** | The event is already observed with public satellite data. "First observable-data analysis of the 2026 Hormuz event" is **false**. |
| **G2** | Identification scaffolds not applied to a coupled-basin freight setting with no clean control | Abadie 2010/2021; Brodersen 2015; Hudgens 2008 | **OUT OF SCOPE (as written) → REFRAMED** | The "coupled-basin **freight**" target is abandoned. The genuine, surviving methodological point is narrower and non-causal: donor chokepoints are **interference-contaminated** (Hudgens-Halloran), so synthetic control can only **corroborate**, not identify. This is a design *discipline*, not an empty gap. |
| **G3** | ML supplies counterfactual generators but treats prediction as identification | Polemis 2025 (ARFIMA event study); Chronos/TimesFM/Moirai; Xu-Xie 2023 | **REJECTED (as a gap)** | Forecast-based maritime event analysis already exists (Polemis). Foundation models + conformal intervals are established. "Treating prediction as identification" is a **mistake to avoid**, not an unoccupied gap to claim. The thesis's stance (forecast = counterfactual generator, never identification) is a correct *position*, not a contribution. |
| **Triad** | No design identifies a logistics channel with a treated control + destructive mediator | — | **OUT OF SCOPE** | The destructive mediator (Qatar force majeure on the freight causal path), the ton-mile logistics channel, and the causal ATT were all dropped in the pivot. The triad describes the abandoned study. It must not appear as the thesis's gap. |

## 3. Overclaims the literature forces us to reject

The following must **not** be claimed (each is occupied by a verified source):

- First use of AIS/satellite data for maritime disruption — *occupied* (Yang 2019;
  Wan 2023; Xiao 2024; Arslanalp 2025).
- First observable-data analysis of the 2026 Hormuz event — *occupied* (Yang 2026
  SAR).
- First study of chokepoint closure / rerouting / resilience — *occupied*
  (Pratson 2023; Verschuur 2025; Nguyen 2023).
- First study of LNG reallocation under chokepoint disruption — *occupied*
  (Meza 2022/2026; Xiao 2024).
- First forecast-based maritime event study — *occupied* (Polemis 2025).
- A new forecasting algorithm or a better forecaster as the contribution —
  *excluded by design* (prediction ≠ identification; Chronos/TimesFM/Moirai are
  benchmarks only).
- Causal identification of the Hormuz effect from a single treated series —
  *not licensed* (interference/SUTVA; Hudgens 2008).

## 4. The narrowest surviving contribution

After rejecting the above, what remains is a **protocol-integration and
descriptive-measurement** contribution, stated without superlatives:

> For the 2026 Strait of Hormuz disruption, the thesis estimates a
> **disruption-associated shortfall in observable daily tanker throughput**
> against a strictly pre-event, target-only forecast, and subjects that estimate
> to a single integrated falsification protocol: chronological (rolling-origin)
> validation, descriptive full-horizon forecast-error quantile bands,
> disjoint-block rank/conformal inference, temporal placebos, same-date spatial
> placebos across other chokepoints, rerouting-aware
> donor-contamination screening, LNG-specific cross-source corroboration, and
> frozen public-data provenance — while reporting the result as explicitly
> **non-causal**.

Supporting empirical layer (descriptive, not identified): the disruption
propagated into **source composition, not total volume** — defended aggregate
importer intake with sharp contraction in Gulf-sourced volume ("resilience
through reallocation"; the demand-side analogue of the repo's "contraction +
substitution, not multiplier" finding).

**Why this survives the broadened, multi-field search (six institutional
fields):** every component exists *somewhere*, but no verified study combines them
for this event on public data with non-causal discipline. The closest
*methodological* precedent (Polemis 2025) uses **proprietary** weekly data and an
ARFIMA event study without the placebo/donor cascade; the closest *same-event*
precedent (Yang 2026 SAR) is **public** but does not build a forecast-counterfactual
shortfall with calibrated horizon uncertainty and placebo falsification. The
contribution sits precisely between them.

**Framing rules (anti-overclaim):**
- Call it a *protocol* / *auditable measurement-and-falsification design*, never a
  "new estimator" or "first study."
- Say "disruption-associated shortfall," never "the effect of" or "ATT."
- Present transferability (Suez, Bab-el-Mandeb, Panama, Malacca) as *potential
  reuse*, demonstrated for one case only.

## 5. Academic-consistency actions triggered by this validation

Because the gaps were written for the abandoned estimand, the following must be
reconciled before the literature chapter is final (feeds task C7 / E):

1. **Rewrite the proposal's three-stream gap prose** so G2/G3 and the triad no
   longer assert a freight/mediation/ton-mile identification gap.
2. **Align title, RQ, and hypotheses** to the throughput-shortfall, non-causal
   estimand (currently still pending Prof. Li's scope lock).
3. Ensure the contribution paragraph in `LITERATURE_REVIEW_FOUNDATION_DRAFT.md`
   §5 matches the surviving contribution in §4 above (it currently does — keep
   them synchronized).
4. Carry the §3 "must-not-claim" list into the Discussion/Limitations chapter
   verbatim so no overclaim re-enters downstream.
