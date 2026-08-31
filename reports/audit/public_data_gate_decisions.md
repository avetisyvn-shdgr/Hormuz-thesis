# Optional public-data gate decisions

**Design id:** `optional_public_data_gate_decisions_v1`  
**Design SHA-256:** `f6b308ff438e95b12e2389896414355d7273870d2114a599ae36a92dccc8b668`  
**Frozen (UTC):** 2026-08-09T23:59:44Z  
**Verification status:** `NEEDS-VERIFY` until the complete pipeline is run.

This is a **governance decision table**, not an empirical phase. Nothing here was downloaded, registered, or analysed. The accepted no-third-layer plan is preserved: no candidate below is admitted, and no candidate can be admitted by this document.

All 5 candidates carry a non-GO status and all require an explicit written scope reopening by the thesis author, recorded in `DECISION_LOG.md` **before** any acquisition.

## Decision summary

| Candidate | Status | Single permitted use | Reopening required |
|---|---|---|---|
| ECMWF ERA5 reanalysis | `DEFER_PENDING_SCOPE_REOPENING` | A weather falsification check only: testing whether meteorological conditions in the treated window could plausibly account for part of the observed transit decline. | yes |
| Global Fishing Watch hourly AIS presence | `DEFER_PENDING_SCOPE_REOPENING` | Coarse loitering or dwell-duration proxies only, at grid resolution, as a descriptive diagnostic on the already-registered vessel branch. | yes |
| JODI-Gas national statistics | `NO_GO` | National macro context only, and only if the blocking conditions below are ever cleared. | yes |
| US MARAD maritime advisories | `DEFER_PENDING_SCOPE_REOPENING` | Operational chronology corroboration only: cross-checking dates already recorded in EVENT_CHRONOLOGY.md against an additional official source. | yes |
| Sentinel-1 SAR ship detections | `DEFER_POST_SUBMISSION` | Post-submission, scene-level vessel-occupancy validation only: checking whether independent satellite observation is consistent with the modeled support collapse documented in the network-support frontier. | yes |

## Rights, coverage, lag, and estimand relevance

| Candidate | Required rights | Coverage | Reporting lag | Estimand relevance |
|---|---|---|---|---|
| ECMWF ERA5 reanalysis | Copernicus licence; redistribution of derived values permitted with attribution | Global hourly reanalysis covering the full study window | About five days, adequate for the treated window | Low and strictly falsificationist. A null weather result would slightly strengthen the existing counterfactual reading; a non-null result would not identify anything, because weather is not the treatment. |
| Global Fishing Watch hourly AIS presence | Existing GFW account and token; the public presence product is gridded, not raw tracks | Gridded presence; identity resolution weaker than the registered port-visit product | Product-dependent; not a binding constraint | Low. It could sharpen dwell diagnostics but cannot repair the missing-edge support problem, because the same AIS gaps that remove a sequence from the panel also degrade presence. |
| JODI-Gas national statistics | Redistribution rights UNRESOLVED for the derived series | Free bulk CSV is stale and ends 2018-12; live data sits behind a portal whose refresh path is unconfirmed | Inadequate for the post-event window even if access were resolved | Nil under current support. The series cannot cover the treated window, so it cannot inform the estimand at all. |
| US MARAD maritime advisories | US government public domain; attribution expected | Advisory text only; no vessel, terminal, or quantity fields | Near real time | Nil for identification, modest for narrative accuracy. It could corroborate the chronology already audited on 2026-06-19 but adds no estimand content. |
| Sentinel-1 SAR ship detections | Copernicus open licence; scene processing capability unconfirmed on this hardware | Scene-level, revisit-limited; not daily and not continuous | Scene-dependent; processing burden is the binding constraint, not latency | Moderate as corroboration, nil as identification. Yang et al. 2026 already observe this event with Sentinel-1, so this is a validation avenue rather than a novelty claim, and the thesis must not present it as first observation. |

## What each candidate may never be used for

- **ECMWF ERA5 reanalysis** — Not a treatment, not a control in the throughput specification, not a mechanism layer, and never a co-determinant added to the locked AR model.
- **Global Fishing Watch hourly AIS presence** — Never continuous global track reconstruction, never vessel-level distance recomputation, and never a replacement for the modeled shortest-sea-route distance used in the route-burden construct.
- **JODI-Gas national statistics** — Never an origin-split confirmatory importer panel and never a quantity-basis substitute for the customs evidence.
- **US MARAD maritime advisories** — Never identification, never a treatment-date selector, and never a quantitative input. The locked 2026-02-28 cutoff does not move on the strength of an advisory.
- **Sentinel-1 SAR ship detections** — Never a daily AIS-dark throughput multiplier, never a scaling factor applied to unobserved sequences, and never a substitute for the support-limited construct.

## Kill criteria

### ECMWF ERA5 reanalysis

- Any use that adds ERA5 as a regressor to the locked primary specification.
- Any framing in which a weather association is reported as a mechanism.
- Acquisition before an explicit written scope reopening by the thesis author.

### Global Fishing Watch hourly AIS presence

- Any attempt to reconstruct individual vessel tracks from gridded presence.
- Any recomputation of route distance that would silently change the frozen construct.
- Any use that implies AIS-dark sequences have been observed.

### JODI-Gas national statistics

- Stale coverage ending 2018-12 (already triggered).
- Unresolved redistribution rights for any derived series (already triggered).
- Post-event reporting lag longer than the treated window (already triggered).

**Blocking reason:** Two independent kill criteria are already met. This is a NO_GO on the facts, not a deferral pending preference.

### US MARAD maritime advisories

- Any use that moves or re-derives the operational-onset cutoff.
- Any subjective text coding turned into a quantitative variable.
- Any presentation of advisory language as evidence of throughput.

### Sentinel-1 SAR ship detections

- Any conversion of scene occupancy into a daily throughput estimate.
- Any use before thesis submission, which would displace writing.
- Any claim of first or independent observation of the 2026 event.

## Governance boundary

- Authority to reopen scope rests with thesis author only, by explicit written scope reopening.
- This phase performed no network access and added no registered variable. The source registry is hash-pinned at 53 variables and verified byte-identical on every run.
- The G4-verified horizon-frontier, network-support, and route-burden manifests are hash-pinned and unchanged.
- The locked specification, the 2026-02-28 operational-onset cutoff, and the formal proposal are untouched.

