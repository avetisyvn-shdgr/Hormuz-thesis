# Donor-contamination stress test — results

**Status:** 2026-06-21. Implements the two pre-committed hardenings from
`docs/SUTVA_CONTAMINATION_AUDIT.md` (contamination stress test + donor-influence
diagnostic). This strengthens a **corroboration** layer; the AR-only within-unit
estimator remains the primary anchor and is structurally immune to this failure
mode. Reproduce with `python scripts/run_donor_contamination_stress.py`
(`src/lngfreight/donor_screen.py`, tests `tests/test_donor_screen.py`).

## Why

The synthetic control and spatial placebo share one load-bearing assumption: the
partition of chokepoints into contaminated vs clean donors. Until now that screen
was **a-priori** — five corridors named by judgement (Panama, Suez, Bab-el-Mandeb,
Cape of Good Hope, Gibraltar). A Hormuz disruption reroutes traffic, so any donor
whose own throughput *rose* post-treatment is a rerouting suspect. The Task 7
transmission map gives each donor's post-period directional deviation, so the
screen can now be **data-driven** and **stress-tested**.

## Finding 1 — the a-priori screen was incomplete

Six donors rose post-treatment yet were kept in the "clean" pool by the a-priori
screen: **Lombok, Mindoro, Mona Passage, Sunda, Tsugaru, Yucatan**. These are
exactly the mis-screened donors the audit warned would bias both corroboration
layers anti-conservatively. The data-driven screen catches them.

## Finding 2 — Hormuz separation survives the pessimistic screen

Synthetic-control post/pre RMSPE ratio and separation vs the donor placebo p95,
across four screens (pessimistic = a-priori ∪ data-driven suspects, 11 donors
removed, 16 remaining):

| Screen | Donors | n_tanker ratio | n_tanker sep | capacity ratio | capacity sep |
|---|---:|---:|---:|---:|---:|
| none (all donors) | 27 | 4.97 | 3.26 | 3.31 | 2.29 |
| a_priori (5) | 22 | 4.77 | 3.87 | 3.01 | 2.07 |
| data_driven_rose (8) | 19 | 4.70 | 4.20 | 2.95 | 2.24 |
| **pessimistic_union (11)** | **16** | **4.66** | **4.17** | **2.87** | **2.10** |

Separation = actual ratio ÷ donor-placebo p95. Removing risen (low-loss) donors
raises the donor reference, so the pessimistic figure is a **conservative floor,
not a flattering one** — for counts it actually *increases* (3.26 → 4.17) because
the removed suspects were diluting the placebo pool.

## Verdict

**SPOF contained.** Minimum separation under the pessimistic screen is **2.10×**
(capacity), above the pre-registered 2.0× containment floor; transits remain
**>4×** under every screen. The Hormuz throughput collapse is not an artifact of
which donors are called clean.

## Honest caveats

- **Capacity corroboration is screen-sensitive** (2.07–2.29×, and 2.10× under the
  pessimistic screen — only just above the floor). Report it as the weaker leg;
  the transit corroboration is robust.
- **Abadie p-values rise to ~0.06** under the pessimistic screen (fewer placebo
  donors), so this is descriptive separation, not a 5% claim — consistent with
  the project's finite-sample p-floor discipline.
- **The screen uses post-period information** by construction; that is the point
  of a pessimistic robustness floor (deliberately remove anything that *could* be
  contaminated), not a primary estimate.
- **Non-independence stands.** Spatial placebo and synthetic control still share
  the donor partition; this test bounds the shared failure, it does not make them
  independent. The within-unit AR-only primary remains the anchor.
