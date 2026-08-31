# Route-burden decomposition

**Design id:** `lng_route_burden_decomposition_v1`  
**Design SHA-256:** `e7bd883111abef19f9c419f9a4e3277583694803b6a61a3b2e11b182fcc10410`  
**Frozen (UTC):** 2026-08-09T23:45:44Z  
**Freeze status:** frozen_before_generation_not_preregistered  
**Verification status:** `NEEDS-VERIFY` until the complete pipeline is run.

**Construct:** modeled distance per nominal vessel-capacity m3 among retained inferred voyages.  
**Unit:** nominal m3 x modeled nautical miles per retained sequence.

Both factors are modeled. Nominal vessel capacity is a design property of the carrier, not a measured cargo quantity, and the distance is a shortest-sea-route network estimate, not an observed AIS track. A change in this mean describes **which sequences remain observable and how their modeled attributes are distributed**. It is not observed cargo ton-miles, not physical rerouting, and not evidence that any individual ship sailed farther.

## Decomposition identity

The pre-to-post change in the mean splits into three parts:

- **`common_pair_share_reweighting`** — shift of retained-sequence mass across terminal pairs present in both periods.
- **`within_common_pair_capacity_mix`** — change in mean nominal capacity carried on the same terminal pair.
- **`entry_exit_residual`** — contribution of terminal pairs supported in only one period.

The residual is defined as the remainder, so the three sum to the total exactly. It is independently cross-checked against its conditional-mean identity `(Y_post - Y_common_post) - (Y_pre - Y_common_pre)`, and the build fails if the two disagree.

## Primary cell (30 km, symmetric weighting, all retained)

| Quantity | Value (million m³-nm per retained sequence) | Share |
|---|---:|---:|
| Pre-period mean | 662.706 | |
| Post-period mean | 730.291 | |
| **Total change** | **67.585** | **100.0%** |
| Common-pair share reweighting | 37.112 | 54.9% |
| Entry/exit residual | 29.628 | 43.8% |
| Within-common-pair capacity mix | 0.845 | 1.3% |

Support: 948 pre and 726 post retained sequences across 189 common terminal pairs, with 216 pairs leaving and 173 entering.

Read together with the components, this says the increase is almost entirely **compositional**: mass moving between terminal pairs (54.9%) plus pairs entering and leaving support (43.8%). Carrying larger vessels on an unchanged terminal pair explains only 1.3%.

## Index-number sensitivity

Only the split between share reweighting and within-pair capacity mix depends on the weighting choice. The entry/exit residual is invariant.

| Weighting scheme | Role | Share reweighting | Entry/exit | Within-pair |
|---|---|---:|---:|---:|
| `laspeyres_share_paasche_within` | sensitivity | 54.4% | 43.8% | 1.7% |
| `paasche_share_laspeyres_within` | sensitivity | 55.4% | 43.8% | 0.8% |
| `symmetric_marshall_edgeworth` | primary | 54.9% | 43.8% | 1.3% |

## The component split does not generalise

The 54.9 / 43.8 / 1.3 split above is specific to the 30 km all-retained cell. **It is not stable across the radius grid or the carrier restriction**, and it must never be quoted as if it were a general property of the mechanism.

Two facts establish that:

1. At 10 km the entry/exit residual carries 79.8% against 22.4% for share reweighting — close to the reverse of the primary cell — and the within-pair term turns negative.
2. Under the both-period carrier restriction the shares move again, to 96.8% / 9.4% / -6.2% at 30 km.

Some cells are worse than unstable: their components largely offset, so the percentage shares divide by a near-zero total and become meaningless. Those cells are flagged `percent_decomposition_is_unstable` and their percentages are not interpreted here.

| Cohort | Radius (km) | Total change | max\|component\|/\|total\| |
|---|---:|---:|---:|
| `both_period_carriers` | 10 | -2.073 | 5.95 |

Across the 6 radius-by-cohort cells, 5 show a rise in the modeled burden per retained sequence and 1 do not.

- `both_period_carriers` at 10 km gives -2.073 million m³-nm per retained sequence — the opposite sign to the primary cell. The direction of the headline is therefore **not** universal across the sensitivity grid.

What does hold in every interpretable cell is the weaker, qualitative statement: whatever change occurs is **compositional** rather than within-pair. Carrying different vessels on an unchanged terminal pair never accounts for a large share of the movement. The apportionment between mass moving across pairs and pairs entering or leaving support is not identified by this design.

## Radius sensitivity (symmetric weighting, all retained)

| Radius (km) | Pre mean | Post mean | Total change | Share | Entry/exit | Within-pair | Pre seq. | Post seq. |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 10 | 679.213 | 734.357 | 55.144 | 22.4% | 79.8% | -2.2% | 549 | 384 |
| 20 | 657.498 | 716.557 | 59.059 | 59.0% | 40.1% | 0.9% | 897 | 667 |
| 30 | 662.706 | 730.291 | 67.585 | 54.9% | 43.8% | 1.3% | 948 | 726 |

## Both-period carrier restriction

Restricting to IMOs with a retained sequence in both periods holds the observed carrier set fixed, so composition cannot be produced purely by carrier turnover.

| Radius (km) | Total change | Share | Entry/exit | Within-pair | Pre seq. | Post seq. |
|---:|---:|---:|---:|---:|---:|---:|
| 10 | -2.073 | 595.5% ‡ | -528.0% ‡ | 32.6% ‡ | 299 | 283 |
| 20 | 27.546 | 97.3% | 10.6% | -7.8% | 629 | 589 |
| 30 | 31.672 | 96.8% | 9.4% | -6.2% | 709 | 653 |

‡ Components largely offset, so these percentages divide by a near-zero total and carry no interpretation.

At 30 km the restricted cohort gives a total change of 31.672 million m³-nm per retained sequence across 709 pre and 653 post sequences.

## Censoring and support bounds

At 30 km, 23 pre and 20 post resolved sequences are excluded from the complete case because no expanded-specification route distance or nominal capacity could be joined.

Excluded and vanished sequences are **not** assigned a burden of zero and are **not** assumed to carry the pre-period average. The total is conditional on the support documented by the task-7 network-support frontier, where Hormuz-crossing support falls from 145 to 2 sequences at 30 km. A decomposition computed on a panel that lost its Hormuz-crossing mass will attribute much of the change to entry/exit for exactly that reason, and the entry/exit share here (43.8%) should be read as that support fact, not as a behavioural finding.

## Interpretation limits

- The construct is `modeled distance per nominal vessel-capacity m3 among retained inferred voyages`. It is not observed cargo ton-miles.
- It is not physical rerouting and not evidence that individual ships sailed farther. No vessel-level distance change is measured anywhere in this artifact.
- The change is compositional. It reflects which terminal pairs retain modeled support and how retained sequences distribute across them.
- No AIS-dark physical throughput may be inferred, and nothing here is an average treatment effect or a causal identification.
- The upstream capacity, comparison, and task-7 artifacts are hash-verified read-only inputs to this phase.

