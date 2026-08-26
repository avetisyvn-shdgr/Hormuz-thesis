# PortWatch rebound/relapse profile

**Outcome:** IMF PortWatch `n_tanker` at the Strait of Hormuz (all tankers, not
an LNG vessel class).  
**Design:** Descriptive calendar partitions fixed after exploratory inspection
revealed the phase change and before this artifact was generated; neither a
preregistered design nor causal estimates of the MoU or renewed attacks.  
**Artifacts:** `data/processed/portwatch_regime_phase_profile.csv` and
`data/processed/portwatch_regime_contrasts.csv`.

## Why the correction is necessary

The earlier vintage note compared one cumulative 130-day AR shortfall average
with a cumulative 155-day average (43.81 → 44.08 transits/day). A nearly
unchanged cumulative average cannot establish a flat path inside the added
window. It concealed a pronounced phase change and therefore could not support
“no rebound” or “no reopening dynamic.”

## Frozen windows and observed counts

All dates are inclusive. The 2026-07-07 renewed-attacks date is reported as its
own context-event day and excluded from both adjacent intervals.

| PortWatch vintage | Phase | Days observed / planned | Transit total | Mean/day | Non-zero days | Complete? |
|---|---|---:|---:|---:|---:|---:|
| Pinned primary | 2026-05-28–06-16, pre-MoU reference | 20 / 20 | 25 | **1.25** | 13 | Yes |
| Pinned primary | 2026-06-17–07-06, post-MoU interval | 20 / 20 | 249 | **12.45** | 20 | Yes |
| Pinned primary | 2026-06-30–07-06, nested final week | 7 / 7 | 109 | **15.57** | 7 | Yes |
| Pinned primary | 2026-07-07 event day | 1 / 1 | 12 | 12.00 | 1 | Yes |
| Pinned primary | 2026-07-08–08-01, post-attacks interval | 0 / 25 | — | — | — | **No: beyond trusted 07-07 endpoint; five raw buffer days excluded** |
| 2026-08-09 | 2026-05-28–06-16, pre-MoU reference | 20 / 20 | 17 | **0.85** | 10 | Yes |
| 2026-08-09 | 2026-06-17–07-06, post-MoU interval | 20 / 20 | 209 | **10.45** | 19 | Yes |
| 2026-08-09 | 2026-06-30–07-06, nested final week | 7 / 7 | 88 | **12.57** | 7 | Yes |
| 2026-08-09 | 2026-07-07 event day | 1 / 1 | 10 | 10.00 | 1 | Yes |
| 2026-08-09 | 2026-07-08–08-01, post-attacks interval | 25 / 25 | 39 | **1.56** | 21 | Yes |

The matched post-MoU mean exceeds the immediately preceding matched mean in
both measurement vintages. In the August vintage it rises by 9.60 transits/day
(0.85 → 10.45), then falls by 8.89/day (−85.1%) in the complete post-July-7
interval. The pinned vintage confirms the initial rebound but cannot estimate
the full 25-day relapse contrast. Its trusted reporting endpoint is July 7:
although the raw source has five additional July 8–12 rows, those rows belong
to the predeclared five-day source buffer and are excluded rather than treated
as eligible observations.

This was only a **partial** rebound. The August post-MoU mean equals 22.2% of
its configured pre-treatment mean (47.001/day); the post-July-7 interval equals
3.3%. It is not a return to baseline.

## Defensible interpretation

Observed PortWatch tanker throughput shows a temporary partial rebound
coinciding with the post-MoU period, followed by relapse after renewed attacks.
Twenty-one of the 25 post-attack days were nonzero, so “relapse” describes the
low mean relative to the configured pre-treatment level, not a literal absence
of traffic. The extension supports **no sustained recovery toward that
pre-treatment level through 2026-08-01**, not “no rebound.” These calendar
partitions do not identify either context event's causal effect.

Keep the outcome distinction explicit:

- **PortWatch all-tanker count:** temporary partial rebound, then relapse; no
  sustained recovery through August 1.
- **WTO LNG outbound index:** no sustained LNG resumption; isolated partial
  loading days do not establish a durable restart.

Neither series proves physical absence of unobserved AIS-dark vessels.

## Reproduction and guards

`scripts/run_rebound_relapse_profile.py` reads both snapshots through the
registry with explicit sensitivity opt-in, verifies their frozen hashes,
rejects internal calendar gaps, records trusted endpoints and excluded source
buffer days, and estimates only contrasts whose two windows are complete. The
runner belongs to the separate PortWatch sensitivity branch, not the locked
primary `run_all.py` path. Focused tests lock the 20/20/7/1/25-day denominators,
exact eligible totals and means, and the inadmissibility of the pinned relapse
contrast.
