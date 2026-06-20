# Estimand realignment — proposal-reconciliation note

**Status:** Decision-ready reconciliation, 2026-06-20. **Pending Prof. Li
approval.** This note does **not** edit the formal proposal (`Thesis_Proposal_MA`,
unchanged) and does not enact a change. It maps the approved proposal item-by-item
to the staged realignment in `PENDING_ESTIMAND_REALIGNMENT_DRAFT.md` so the
outcome-variable change can be approved as one explicit decision. Until then the
formal proposal remains in force (AGENTS.md).

## One-paragraph summary

The supervisor green light (Z. Wang relaying Prof. Li, 2026-06-16) to "proceed on
the fallback with another suitable dataset" lets the thesis run end-to-end on free
data now. The **only** change this forces is the **outcome variable**: from
proprietary daily LNG spot freight (Spark25S/30S) to free daily Strait-of-Hormuz
tanker **throughput** (IMF PortWatch). Everything that constitutes the proposal's
actual contribution — the identification *protocol* (falsification cascade,
dose-response intent, donor synthetic control, placebo-in-time/space, leakage-safe
counterfactual forecasting, foundation-model-as-benchmark discipline) — is
**preserved**. The freight-rate magnitude and the AIS ton-mile mechanism are
**demoted to descriptive/optional** and **partially recovered for free** by the
Phase-3A GFW vessel branch (inferred capacity-nautical-miles) or the Phase-3B
simulation.

## Item-by-item reconciliation

| Proposal element (approved) | Realignment (staged) | Status |
|---|---|---|
| **Title:** "Causal Identification of the Ton-Mile Multiplier Effect…" | "Counterfactual Estimation of Tanker-Throughput Disruption at the Strait of Hormuz…" | **Replace** (outcome + claim strength) |
| **DV:** daily LNG spot freight (Spark25S Pacific, Spark30S Atlantic) | daily Hormuz tanker transit count (PortWatch `n_tanker`); DWT capacity as robustness twin | **Replace** (different adjacent outcome, *not* a proxy) |
| **Estimand:** ATT of the disruption on LNG freight (dose-response coefficient θ) | cumulative & mean-daily **observed−counterfactual throughput shortfall** | **Replace + weaken** (association, not ATT) |
| **Sub-Q1** magnitude/persistence vs explicit counterfactual, ≥2 generators | identical, on throughput; AR-only primary + seasonal-naive/ARX/TSFM generators | **Preserve** |
| **Sub-Q2** inter-basin regime switch (Atlantic vs Pacific lead-lag) | not testable without freight series | **Demote → optional** (returns if Spark/Bloomberg arrives) |
| **Sub-Q3** AIS-derived laden ton-miles as primary mechanism proxy | inferred LNG **capacity**-nautical-miles (GFW, Phase-3A) or simulation (3B); not observed cargo ton-miles | **Preserve in weakened form** (free recovery) |
| **Sub-Q4** modern TSFM (PatchTST/iTransformer) improve forecasting w/o losing interpretability | foundation-model benchmark gate (Chronos-2 / TimesFM 2.5 / Moirai 2.0), kept as admitted *benchmark*, never primary | **Preserve, updated models** |
| **H1** significant positive freight treatment effect | H1 throughput shortfall below pre-disruption counterfactual | **Replace** (outcome) |
| **H2** inter-basin regime switch | H2 persistence + capacity robustness | **Replace** |
| **H3/H4** mechanism + donor falsification | placebo-in-time/space separation; clean-donor synthetic control corroboration | **Preserve** (H3/H4 in draft) |
| **Methodology:** falsification cascade (event study → dose-response → ML counterfactual → synthetic control → mechanism) | same cascade, throughput DV; dose-response on continuous exposure deferred to mechanism layer (3A/3B) | **Preserve protocol** |
| **Contribution:** causal ton-mile transmission into freight | reproducible throughput-shortfall estimate + transparent triangulation under explicit AIS/donor limits; freight/ton-mile contextual/optional | **Reframe** (method contribution intact, magnitude claim softened) |
| **Transformer stance:** demoted to diagnostic, not a claim | identical; locked AR-only primary, Transformer prohibited unless it improves fit *and* calibration | **Preserve exactly** |

## What is preserved, replaced, added

- **Preserved (the contribution):** the identification protocol and its discipline
  — leakage-safe chronological validation, counterfactual-as-contrast, placebo
  inference, donor synthetic control as corroboration not anchor, forecast-skill ≠
  causal-validity, multiplicity caution, and the foundation-model benchmark gate.
- **Replaced (the outcome):** freight rate → tanker throughput; ATT → disruption-
  associated counterfactual shortfall. This is honestly a **change of estimand,
  not a proxy swap** — throughput is a different, adjacent outcome on the cause/
  route side, not a stand-in for a freight price.
- **Added (free upside):** the GFW vessel-feasibility branch that recovers a
  weakened, LNG-specific version of the original ton-mile mechanism for free, and
  its simulation fallback — neither of which the original proposal had.

## Decision items requiring Prof. Li's explicit sign-off

1. Approve the **outcome-variable change** (freight → throughput) and the title/RQ.
2. Approve **"disruption-associated counterfactual shortfall"** as the reporting
   term (no ATT/causal-effect language under the free-data branch).
3. Confirm **freight + inter-basin regime switch are demoted to optional**,
   reactivated only if Spark/Bloomberg access lands (registry flip, no redesign).
4. Confirm the **updated TSFM roster** (2025 foundation models) satisfies the
   original PatchTST/iTransformer sub-question as a benchmark.

On approval, transfer the staged language from
`PENDING_ESTIMAND_REALIGNMENT_DRAFT.md` into the formal proposal; until then both
documents remain non-binding drafts and the formal proposal is untouched.
