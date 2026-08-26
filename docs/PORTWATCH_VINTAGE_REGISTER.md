# PortWatch vintage register

**Status:** Active vintage pinned on 2026-07-23 under remediation item
`DATA-01`.

## Active analysis vintage

The active `hormuz_tanker_transits` series for the configured
`2022-01-01` through `2026-07-07` window is:

- File:
  `data/raw/portwatch/hormuz_tanker_transits__chokepoint_strait_of_hormuz_n_tanker__6631382171dc.csv`
- SHA-256:
  `6631382171dc7f19450516a404138cf529647acf246be68c5c9f80dedfb5b3bb`
- Source aggregate:
  `data/raw/portwatch/Daily_Chokepoints_Data.csv`
- Aggregate SHA-256:
  `66f3a54afb042103f3e0afc9670568cb7be245394ec04eba55ebd158593f579d`
- Provenance record:
  `data/raw/provenance.jsonl`, retrieved at
  `2026-07-15T12:51:54.642193+00:00`.

An execution of
`registry.get_variable("hormuz_tanker_transits", start="2022-01-01",
end="2026-07-07")` on 2026-07-23 returned the same tidy SHA-256 and left the
provenance ledger unchanged. The treatment-window observations are:

| Date | Pinned transit count |
|---|---:|
| 2026-02-27 | 35 |
| 2026-02-28 | 35 |
| 2026-03-01 | 10 |
| 2026-03-02 | 2 |
| 2026-03-04 | 0 |

`config/settings.yaml` pins this exact derived file and checksum.
`build_panel_from_frozen_raw()` enforces the pin instead of relying on the last
matching provenance record.

## Quarantined historical vintage

The following earlier snapshot is retained unchanged for auditability but is
excluded from both the core and vessel input scopes:

- File:
  `data/raw/portwatch/hormuz_tanker_transits__chokepoint_strait_of_hormuz_n_tanker.csv`
- SHA-256:
  `c763eab5a6c039800d56728b5f4ae0add884cc8cfaf139097869d1669515424d`
- Historical window: `2022-01-01` through `2026-06-01`.
- Conflicting observations: 53 on 27 February, 44 on 28 February, and 7 on
  1 March 2026.

“Quarantined” means preserved for provenance but impossible to select as the
active configured series. It is not deleted or overwritten because raw
historical vintages are audit evidence.

## Candidate sensitivity vintage — captured 2026-08-09 (NOT the reporting basis)

A fresh PortWatch snapshot was captured on 2026-08-09 during the v3 window-
extension attempt. **It is deliberately not promoted to the active vintage.**
Mher's decision of 2026-08-09 keeps the pinned vintage above as the primary
reporting basis and admits this capture only as a documented
vintage-sensitivity layer (`DECISION_LOG.md`).

- File:
  `data/raw/portwatch/vintages/Daily_Chokepoints_Data__vintage_2026-08-09.csv`
- SHA-256:
  `0bc806a4c384723debff08053d6fcbb915a03ee9fdf7b23c73d76d9bcb885bcb`
- Fixity scope: `data/raw/SHA256SUMS.sensitivity`; verified manifest at
  `data/processed/portwatch_sensitivity_input_manifest.json`. The source bytes
  are locally fixed but Git-ignored, so replication-archive deposit remains
  pending (`PORTWATCH_SENSITIVITY_INPUT_GATE.md`).
- Coverage: `2019-01-01` through **`2026-08-02`** (28 chokepoints, 77,588 rows;
  pinned aggregate has 77,000 rows through 2026-07-12).
- Retrieval: the portal's own published CSV export endpoint, discovered from
  the "Access API" page of dataset `3da2b9ca97684916b75c4013f95d18ab`
  ("Daily Chokepoints Data"), backed by
  `services9.arcgis.com/weJ1QsnbMYJlCHdG/.../Daily_Chokepoints_Data/FeatureServer/0`.
  The endpoint was **discovered, not guessed** — the source module forbids
  guessing a URL. Schema verified identical to the pinned 21-column schema.

### Why it is not promoted: the revision is large and pre-treatment

PortWatch's own Data & Methodology changelog records a **March 2026 boundary
refinement to chokepoint6 (Strait of Hormuz)** and **July 2026 + August 2026
methodological revisions** for AIS spoofing and incomplete transits. Measured
against the pinned vintage over the 2,750 overlapping Hormuz days:

| Quantity | Pinned vintage | 2026-08-09 vintage | Change |
|---|---:|---:|---:|
| `n_tanker` days revised, all overlapping dates | — | 2,680 / 2,750 | **97.45%** |
| `n_tanker` days revised, all pre-cutoff overlap | — | 2,607 / 2,615 | **99.69%** |
| `n_tanker` days revised, configured training support | — | 1,514 / 1,519 | **99.67%** |
| 2019–cutoff overlap mean `n_tanker` | 54.104 | 44.982 | **−16.9%** |
| Configured 2022–cutoff training mean `n_tanker` | 57.093 | 47.001 | **−17.68%** |
| `capacity_tanker` days revised | — | 2,568 / 2,750 | 93.4% |
| Pre-treatment mean `capacity_tanker` | 2,533,871 | 2,153,782 | −15.0% |

Revisions concentrate **before** the cutoff (2,607 of 2,615 pre-treatment days
changed, mean absolute change 9.15 transits/day) and are minor after it (73 of
135 post days, mean absolute change 1.82) — expected, because post-onset
values sit near zero and there is little left to revise.

**Consequence:** because the AR counterfactual is fitted on pre-treatment data,
this vintage lowers the counterfactual baseline and therefore the
disruption-associated shortfall. Adopting it silently would move the headline
magnitude by roughly a sixth on a vendor methodology change alone. That is a
disclosure-and-sensitivity matter, not a silent refresh — hence this register
entry and the sensitivity layer.

### Trailing-day completeness (buffer evidence)

The v1/v2 rule set `full_end = max date − 5 days` because trailing days can be
incomplete. In this vintage that is not visible: all-chokepoint daily totals
for 2026-07-22 → 2026-08-02 run 1,761–1,940 against a 1,918 mean for
2026-06-01 → 2026-07-20, and the final day (2026-08-02) totals 1,885. The
sensitivity layer therefore uses a **1-day buffer (`full_end = 2026-08-01`)**,
recorded as a documented departure from the 5-day rule, so that the
2026-07-29 Damietta event falls inside the analysed window.

## Treatment-date implication

The pinned vintage does not fall between 27 and 28 February; its sharp decline
begins on 1 March. Therefore PortWatch is not used to select the
`2026-02-28` cutoff.

The unchanged cutoff follows an external rule: the U.S. Department of Defense
records CENTCOM commencing Operation Epic Fury at 01:15 on 28 February 2026.
Training ends strictly before that external operational onset. The outcome was
inspected during the chronology audit, so this is not described as an ex ante
preregistered date choice. The pinned PortWatch series is a measurement
cross-check only.
