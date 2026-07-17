# DRAFT - Future work

This draft separates future research from the confirmed thesis result. Empirical
numbers are cited to processed or report artifacts where available; governance
gates that are not processed/report artifacts are flagged at the end.

## Persistence and recovery

The persistence/recovery extension should remain future work until the data
support a genuine post-disruption recovery window. The current descriptive
rewiring table has `3` post months for China, EU27, India, and Japan, and `4`
post months for Korea and Taiwan (`data/processed/lng_rewiring_summary.csv`).
That support is useful for descriptive network rewiring but not for a recovery
analysis with enough complete post-shock time to separate immediate adjustment
from persistence. The proposed future gate is `6` complete post months for at
least `4` quantity-basis importers (`docs/CURRENT_PLAN.md`); until that gate is
met, persistence should be described as a research opportunity rather than a
thesis result.

## India quantity unlock

India is currently retained as customs-value evidence, not quantity-basis
evidence. The present by-origin table records India as `kUSD` and `value_kusd`,
with the note that Tradestat HS-6 monthly quantity is unpopulated
(`data/processed/lng_rewiring_summary.csv`). A future India quantity unlock
would change the population boundary by moving India from value-basis evidence
into the physical quantity-basis table, allowing its Gulf-share and non-Gulf
offset patterns to be compared more directly with China, Japan, Korea, and
Taiwan. The specific Comtrade India quantity/API-key blocker is recorded as a
planning constraint rather than as a processed result; see the unsupported
sentence ledger below.

## GEM capacity unlock

The GEM capacity branch should reopen only if it can support available-headroom
analysis rather than nameplate-as-available capacity. The active plan states the
admission rule as a workbook before analysis freeze, nameplate mapped to at
least `90%` of observed non-Gulf supply, and a headroom grid, never
nameplate-as-available (`docs/CURRENT_PLAN.md`). If admitted, this would change
the scenario-conditional feasibility rung by replacing loose supply-pool
assumptions with documented capacity-headroom constraints. It would not by
itself identify observed replacement cargoes or freight-rate effects.

## What would change

These unlocks would not revise the locked throughput shortfall. They would
change the downstream interpretation: persistence support would turn the
network-rewiring section from a short post-window description into a recovery
analysis; India quantity support would remove the value-basis caution for one
major importer; GEM headroom support would make the feasibility model less
dependent on lower-bound route-pool assumptions. Until those conditions are met,
the current thesis should preserve the confirmed chain and keep these items as
future research.

## Unsupported sentence ledger

- "The proposed future gate is `6` complete post months for at least `4`
  quantity-basis importers" is a governance rule from `docs/CURRENT_PLAN.md`,
  not a processed/report artifact.
- "The specific Comtrade India quantity/API-key blocker is recorded as a
  planning constraint" comes from the phase request and planning context, not a
  processed/report artifact.
- "The active plan states the admission rule as a workbook before analysis
  freeze, nameplate mapped to at least `90%` of observed non-Gulf supply, and a
  headroom grid" is a governance rule from `docs/CURRENT_PLAN.md`, not a
  processed/report artifact.
