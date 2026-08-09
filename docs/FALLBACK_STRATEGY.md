# Fallback Strategy — working primary implementation

**Status:** PortWatch dataset substitution authorized and working implementation
locked. Formal estimand/title/RQ/hypothesis realignment remains **pending Prof.
Li confirmation**. This is the load-bearing engineering document for Phase 2's
go/no-go gate ([DATA_ACCESS_CHECKLIST.md](DATA_ACCESS_CHECKLIST.md)). It records
*what was decided, why it is safe, and what is built on it* — so the choice is a
documented methodological decision, not a silent gap (CLAUDE.md rule 8).

## What changed

The finance professorship (via Zhenyu Wang, relaying Prof. Dr. Ziyue Li,
2026-06-16) gave two sanctioned options: keep waiting for Bloomberg access, **or**
proceed on the fallback with another suitable dataset. That second clause is a
**supervisor green light for the fallback branch.** It removes the only thing that
made waiting necessary.

## The decision

1. **Commit to the free-data fallback now as the working primary.** Do not idle
   waiting on access we do not control.
2. **Working model outcome = chokepoint throughput** (Strait of Hormuz tanker
   transits / capacity, IMF PortWatch) — a free, real, already-assembled series.
   The freight-rate / ton-mile-multiplier claim is **reframed as descriptive**,
   supported by context and any indicative public figures, not estimated as the
   primary DV. **This is a change of estimand, not a proxy.** Tanker throughput is
   *not* a substitute for an LNG freight rate; it is a different adjacent outcome.
   Proposed title, RQ, hypothesis, and contribution changes are staged in
   `PENDING_ESTIMAND_REALIGNMENT_DRAFT.md` and are not approved. The implementation
   reports a disruption-associated counterfactual shortfall, not a causal ATT.
3. **Spark / Bloomberg is a dormant optional extension, never a dependency.** The repo's
   provider-agnostic registry means that if access lands at any point, flipping
   `status` in `config/sources.yaml` *adds* the freight target as a second DV
   without disturbing the throughput thesis. We lose nothing by committing now and
   gain everything if access arrives later.

### Why this inverts the risk (the point of the whole exercise)

Before: the thesis depended on access that TUM/Spark might never grant — an
open-ended external dependency. After: the thesis runs end-to-end on data already
in hand, and proprietary access can only *improve* it. The worst case is now
bounded and known, not catastrophic and unknown.

## The dependent variable, operationalized

The proposal's rule (no vague "geopolitical risk" targets) applies here: the DV
must be a measurable daily series. Candidate operationalizations of "chokepoint
throughput", ranked by feasibility:

| Rank | Target series | Definition | Source | Status |
|---|---|---|---|---|
| **1 (primary)** | `hormuz_tanker_transits` | Daily tanker transit COUNT through the Strait of Hormuz | PortWatch (in panel) | **Ready** |
| **2 (robustness twin)** | `hormuz_tanker_capacity` | Daily deadweight CAPACITY of transiting tankers | PortWatch (in panel) | **Ready** |
| 3 (transform) | log / baseline-normalized throughput | Variance-stabilized or %-of-pre-period form of #1/#2 | derived | trivial to derive in modeling |

Transit **count** is the headline DV; deadweight **capacity** is its robustness
twin (a result that holds on both is far stronger). A log or pre-period-normalized
transform remains an optional modeling choice; the implemented headline stays in
auditable level units.

### Research framing — what kind of question this is

The working implementation is a **forecast-based counterfactual event study**,
not prediction for its own sake. Until the formal estimand is approved and its
identifying assumptions defended, outputs are described as disruption-associated
counterfactual shortfalls rather than causal treatment effects.

- **Primary identification = within-unit interrupted time series.** Baselines
  forecast the *counterfactual* Hormuz throughput — what traffic would have been
  absent the disruption — trained on **pre-treatment data only** via the
  rolling-origin harness (`src/lngfreight/validation.py`, cutoff = locked
  `study_window.primary_treatment_cutoff`, 2026-02-28). The gap is the contrast (observed −
  counterfactual) over the post-period. The credibility of this association rests on
  pre-treatment fit quality and placebo behaviour, not on which model forecasts
  best. The AR-only model is the working primary because it consumes no observed
  post-treatment covariates.
- **Inference = placebo / permutation, not point forecasts alone.** Report
  forecast *intervals* (block bootstrap or conformal), in-time placebo (fake
  treatment dates in the pre-period) and in-space placebo (the same procedure on
  control chokepoints). The shortfall must survive these, not just produce a
  visible gap.
- **Synthetic control is a robustness check, not the anchor.** **Panama Canal** is
  one candidate donor, not a "natural" control: it carries its own shocks (drought
  / draft restrictions, seasonality, different cargo mix) and — more seriously — a
  Hormuz disruption causes *rerouting* that contaminates plausible donors
  (Cape of Good Hope traffic rises; Suez / Bab-el-Mandeb already carry Red Sea
  disruptions), a SUTVA problem for a chokepoint donor pool. Use a **donor pool
  with leave-one-out and donor-sensitivity checks**, and treat any SCM result as
  corroboration of the ITS counterfactual rather than the primary estimate.
- **Energy covariates are conditional sensitivities and are never interpreted
  causally.** Henry Hub and Brent (both free, in panel) can help forecast fit,
  but contemporaneous post-shock energy prices are likely *mediators* of the
  Hormuz effect (shock → Brent → shipping behaviour), so feeding them into the
  post-period counterfactual would absorb part of the effect (post-treatment
  bias). Rule: AR-only carries the primary estimate; report models **with and
  without** energy covariates as sensitivities and do not read coefficients as causal. Note
  also that Henry Hub is a weak *global* LNG proxy (JKM / TTF would be preferable
  if accessible); Brent is the relevant series for oil-tanker economics.

This keeps the proposal's identification *protocol* — its actual contribution —
fully intact while resting it on a target we can observe.

## Safe-now vs. access-gated

**Completed without proprietary access:** rolling-origin validation, transparent
baselines, the within-unit counterfactual, temporal/spatial inference, BSTS and
synthetic-control corroboration, and the open-data GFW/WTO mechanism branch.

**Still access-gated:** the freight-rate magnitude (Spark25S/30S) and the
proposal's original observed laden-cargo ton-mile mechanism. The completed free
branch is a weaker inferred nominal capacity-nautical-mile measure from terminal
sequences and modeled routes; it is empirical but descriptive, not qualitative
and not a substitute for proprietary cargo/track data.

## Still do this — the free test that could upgrade the target for free

Committing to the fallback does **not** retire the Spark question; it just stops it
blocking us. Independently of TUM/Bloomberg, create a **free-trial OAuth2 client**
at <https://app.sparkcommodities.com/freight/data-integrations/api>, put the
credentials in `.env`, and run:

```bash
python scripts/verify_spark_target.py
```

This is already built and reports, per contract, the earliest/latest dates the
account exposes and whether they cover the configured study window
(`study_window` in settings.yaml, currently **2022-01-01 → 2026-06-01**) at daily
granularity. Outcomes:

- **Covers the window** → you have the real freight series for free. Flip the
  `spark*` targets to `status: primary` in `config/sources.yaml` and add freight
  as a second DV. The throughput thesis stands; freight becomes a bonus chapter.
- **Trial-limited / truncated** → recorded in
  [TARGET_ACCESS_STATUS.md](TARGET_ACCESS_STATUS.md); nothing lost, we proceed on
  throughput. (The same applies if Bloomberg later comes through.)

## Sequenced next steps

1. **(Mher, ~1 hr, anytime)** Run the Spark free-trial test above; record the
   result. Parallel, non-blocking.
2. **(Done)** Rolling-origin validation harness + tests.
3. **(Done 2026-06-16)** Evaluation-metrics module (MAE, RMSE, MASE, sMAPE) —
   target-agnostic, scores any forecast against any held-out fold.
4. **(Done 2026-06-16)** Seasonal-naive baseline on `hormuz_tanker_transits`
   and `hormuz_tanker_capacity`, scored on the folds.
5. **(Done)** Dependency-free AR-only primary with lagged target values and
   deterministic weekly seasonality; route and energy ARX remain conditional
   sensitivities.
6. **(Done 2026-06-16)** Post-treatment counterfactual export from transparent
   baselines, with daily and cumulative observed-minus-predicted throughput gaps.
   Reports seasonal naive, AR-only, route-only ARX, and route+energy ARX so energy
   post-treatment bias can be inspected rather than hidden.
7. **(Done 2026-06-17)** Placebo-in-time inference for transparent
   counterfactual gaps. With 36 overlapping placebo windows (~9 non-overlapping
   horizon-length windows), the actual disruption exceeds all placebo losses
   across seasonal-naive, AR-only, route-only ARX, and route+energy ARX. The
   finite-sample one-sided p-value is therefore floor-censored at the minimum
   possible `1/(36+1) = 0.027`; report separation ratios as the main evidence
   (AR-only transit loss = 5,121 vs placebo p95 = 1,297, about 3.95x). See
   [INFERENCE_NOTES.md](INFERENCE_NOTES.md).
8. **(Done 2026-06-17)** Same-date spatial placebo / donor-pool check across
   all 28 PortWatch chokepoints. Hormuz transit loss is 5,234 raw transits
   (8.2x the all-donor raw p95) and **95.5% of expected transits** (5.0x the
   all-donor normalized p95). Malacca is the largest raw donor loss (1,680) but
   only 20.3% of its own expected flow, so normalized severity dissolves the
   scale-confounding objection. See [INFERENCE_NOTES.md](INFERENCE_NOTES.md).
9. **(Done)** Donor-weighted synthetic control, leave-one-donor-out sensitivity,
   block-residual intervals, descriptive full-horizon overlapping-placebo
   quantile bands, and disjoint-block rank/conformal inference.
10. **(Done 2026-06-20)** Event-study figures regenerated with the locked cutoff
    and audited milestone labels; hashes are covered by `run_all.py`.

## Limitations to state plainly in the thesis

- **PortWatch tanker class is not LNG-specific** — gas carriers share the
  `tanker` class with oil/chemical tankers. Throughput results are about *tanker*
  traffic; the LNG-specific reading is interpretive, supported by context.
- **Use "disruption", not "closure".** Unless the event chronology documents a
  legally or physically defined closure, the treatment is labelled a *Hormuz
  disruption episode* / *military-escalation shock*. "Closure" is a stronger claim
  that fails if traffic did not literally reach zero or if vessels transited dark.
- **Throughput is the route/cause side, not the price side.** The working study
  estimates a disruption-associated observable throughput shortfall; it does not
  claim a causal freight-rate multiplier or a causal energy-price response.
- **Measurement error under treatment is non-random and directional.** In a
  conflict zone, AIS dark activity, GPS jamming and spoofing (flagged by the IEA
  for this specific Middle East context) are *correlated with the treatment*, not
  random noise. Under the explicit one-sided assumption that treatment-period
  observability error hides true transits but does not create false-positive
  observed transits, the naive estimate is biased away from zero and is a
  **conditional upper bound on the true throughput reduction**. Report it as
  observed AIS-based throughput. The repository currently has no admitted
  dark-rate series, so do not report an empirical lower bound or range; add one
  only if an external dark-rate anchor passes the data-admission rules.
- **PortWatch is media-of-observation, not ground truth** (AIS coverage gaps, its
  own gap-filling). Treated as such throughout.
- **Short post-period** (overfitting risk) — mitigated by pre-treatment-only
  training, rolling-origin validation, placebo inference, and the donor design.
