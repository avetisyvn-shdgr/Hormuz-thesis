# SUTVA / contamination single-point-of-failure audit

**Status:** 2026-06-20. Audits where the design depends on SUTVA (no
interference / stable units) and contamination-screening assumptions, and
identifies the single point of failure shared across the "independent"
corroboration layers. Matches the rigor of the original falsification cascade.

## The structural point

A Hormuz disruption causes **rerouting**, which is interference between units: the
treatment on Hormuz mechanically changes throughput on bypass chokepoints (Cape of
Good Hope rises; Suez / Bab-el-Mandeb already carry Red Sea shocks). That is a
textbook SUTVA violation for any cross-unit comparison. The design's response is to
**screen** five corridors as "contaminated" and treat the rest as a clean donor
pool. This audit asks: *what happens if that screen is wrong, and which layers
fail together?*

## Layer-by-layer SUTVA exposure

| Layer | Cross-unit (SUTVA) dependence? | Failure direction if contamination leaks in |
|---|---|---|
| **AR-only primary (within-unit ITS)** | **None.** Counterfactual is Hormuz's own pre-treatment path; no donor units. | Immune to donor contamination. This is the firewall. |
| **Placebo-in-time** | None across units; uses Hormuz pre-period windows only. | Immune to donor contamination (separate caveats: overlap, training-window asymmetry). |
| **Placebo-in-space (spatial donor pool)** | **Yes.** Donor chokepoints assumed unaffected by the Hormuz shock. | A contaminated donor mis-screened as clean has an *understated* loss → smaller donor p95 → Hormuz separation **overstated** (anti-conservative). |
| **Synthetic control (corroboration)** | **Yes.** Clean-donor convex fit assumes donors are untreated. | Same direction: a leaked donor inflates the post/pre RMSPE separation. |
| **Capacity-mile mechanism (3A) / simulation (3B)** | Fleet-vacuum *is* the interference — here it is the mechanism, not a violation. | Measurement assumes voyage independence; STS transfers/floating storage break it (flagged, excluded). |

## The single point of failure

The two corroboration layers — **spatial placebo** and **synthetic control** — are
presented as independent cross-checks, but they **share one assumption**: the
partition of chokepoints into "contaminated" (5 excluded) vs "clean" (the donor
pool). Both layers draw their reference distribution from the *same* clean pool.

**Therefore their failures are correlated, not independent.** If the contamination
screen is wrong — a corridor that actually absorbs rerouted Gulf traffic is left in
the clean pool — **both** corroboration layers are biased in the **same
anti-conservative direction at once** (donor losses understated → Hormuz looks
more extreme in both). The apparent "two independent corroborations" is, against
this specific failure mode, **one corroboration counted twice.**

This is the load-bearing single point of failure. It does **not** touch the AR-only
primary or the placebo-in-time layer (both within-unit), which is exactly why the
primary must remain the anchor and the donor layers must remain labelled
corroboration, not the estimate (consistent with FALLBACK_STRATEGY.md).

## Severity and mitigations already in place

- **Leave-one-donor-out** (`spatial_placebo_leave_one_out.csv`): the near-5×
  normalized Hormuz separation survives dropping any single donor (min 4.6–4.9×),
  so no *single* leaked donor can be driving it. This bounds, but does not
  eliminate, the failure: it does not protect against *several* mildly leaked
  donors biasing the pool together.
- **Normalized severity** (loss as % of a donor's own expected flow): removes the
  scale-confounding that would otherwise let large donors (Malacca) masquerade as
  comparable disruptions.
- **Direction of bias is known and adverse:** mis-screening inflates separation, so
  the screen must be defended, not assumed benign.

## Recommended hardening (pre-committed, cheap)

1. **Contamination stress test.** ✅ DONE (2026-06-21,
   `scripts/run_donor_contamination_stress.py`,
   `docs/DONOR_CONTAMINATION_STRESS_RESULTS.md`). Re-ran the synthetic control
   under four screens (none / a-priori / data-driven / pessimistic union). Under
   the pessimistic screen (11 donors removed, 16 remaining) Hormuz separation
   stays at 4.17× (transits) and 2.10× (capacity), both above the 2.0× floor →
   **SPOF contained**, with capacity flagged as the weaker, screen-sensitive leg.
2. **Donor-influence diagnostic.** ✅ DONE (same runner). Each donor's post-period
   directional deviation is computed from the AR counterfactual; donors whose
   traffic rose are flagged. This caught **six rerouting suspects the a-priori
   screen missed** (Lombok, Mindoro, Mona Passage, Sunda, Tsugaru, Yucatan).
3. **State the non-independence explicitly in the thesis.** Do not claim the
   spatial placebo and synthetic control are independent corroborations without the
   caveat that they share the donor-partition assumption.
4. **Anchor on the firewall.** Keep the AR-only within-unit ITS as the headline; it
   is structurally immune to this SPOF. The donor layers answer "is the gap unusual
   across space?", which is corroborative, not identifying.

## Non-Hormuz LNG supply-side shocks inside the extended window (added 2026-08-09)

The contamination screen above handles **transit-corridor interference**:
rerouted Hormuz flows contaminating donor chokepoints. The window extension
past 2026-07-07 admits a different shock class that the screen's language does
not describe and cannot absorb: **terminal-side attacks on LNG infrastructure
outside the Hormuz/Red Sea corridors.**

**Instance: Damietta, Egypt, 2026-07-29.** A drone struck the FSRU Energos
Winter alongside at the Damietta LNG terminal; fire spread to the LNG carrier
GasLog Salem. Egyptian Cabinet attributes the fire to a UAV; no claim of
responsibility; attribution unresolved (press naming of Iran is inference).
Details and sources: `EVENT_CHRONOLOGY.md` post-March table and
`DATA_REGISTRY_REVIEW_2026-08.md` §1.

Layer-by-layer exposure of this shock class:

| Layer | Exposed? | Mechanism |
|---|---|---|
| AR-only primary (within-unit Hormuz ITS) | **No** | A Mediterranean terminal attack does not mechanically move Hormuz transit counts; the firewall holds |
| Placebo-in-time | No | Pre-period windows predate the event |
| Spatial placebo / synthetic control donors | **Potentially** | East-Med/Suez war-risk perception can shift Suez-corridor traffic; Suez is already in the excluded contaminated set, but the event strengthens the case that the *exclusion* was right and adds a reason to re-check the "clean" Mediterranean-adjacent donors in any v3 re-run |
| Fearnleys secondary freight series (restricted) | **Yes** | War-risk premia, especially West-of-Suez; 18 post-cutoff weeks are in scope — post-2026-07-29 observations carry this confound |
| Importer panel (Option D) | **Yes** | Egypt is a panel unit (`destination_basin_by_country`); its import capability was shocked mid-window by a non-Hormuz event. Flag Egypt observations after 2026-07-29 or handle explicitly |

**Classification (per `DECISION_LOG.md` 2026-08-09):** treated as a
**distinct confound**, not an extension of the Hormuz treatment, because
attribution is unresolved. If attribution to Iran is later established, the
classification question reopens — that would move it toward "same conflict
complex," which changes wording, not the estimator (the within-unit primary is
unaffected either way). Any v3 write-up that scores post-2026-07-29 windows
must name this event and this classification.

## One-line verdict

The design's cross-unit corroboration rests on a **single shared assumption (the
contamination screen)** whose failure biases both donor layers together and
anti-conservatively; it is contained by leave-one-out and normalization but should
be stress-tested with a pessimistic screen and reported as non-independent. The
within-unit primary and placebo-in-time are immune and must remain the anchor.
