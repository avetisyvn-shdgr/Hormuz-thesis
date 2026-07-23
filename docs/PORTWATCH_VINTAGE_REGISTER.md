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
