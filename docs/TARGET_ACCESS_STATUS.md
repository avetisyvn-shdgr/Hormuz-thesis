# Freight-target access status

**Scope.** One page on the dependent variable only — the LNG spot-freight target
(`spark25s_pacific_freight`, `spark30s_atlantic_freight`). Branch chosen:
**free/fallback** (no proprietary access assumed). Full verification detail and
sources live in [DATA_SOURCES.md](DATA_SOURCES.md) under
"Freight-target access decision — verified 2026-06-14"; this file is the quick
status board the code points at.

## Tiering (verified 2026-06-14)

| Tier | Source | Gives | Free historical daily feed? | Use |
|---|---|---|---|---|
| **1 — PRIMARY** | **Spark Commodities API** (Spark25S / Spark30S) | The *real* daily spot assessment, USD/day | Premium = paid. **Free-trial / academic = history depth UNVERIFIED** — must be tested empirically. | The target. Adapter built: `src/lngfreight/sources/spark.py`. |
| **2 — theoretically close, access-unverified** | **ICE LNG Freight Futures** (settle on Spark30S/25S) | Front-month future, tightly linked to the spot | **NOT confirmed free** — ICE EOD is licensed; resellers (Barchart) are premium. | Only as a documented proxy *if* a free EOD feed is later confirmed. Carries basis/roll/timing risk even then. Not built. |
| **3 — secondary, insufficient unless history confirmed** | **EEX**, **Baltic Exchange** (BLNG routes) | EEX owns Spark but freight futures trade on ICE, not EEX free pages; Baltic BLNG is an independent assessment | EEX: no free freight-futures feed found. Baltic: subscription. | Not usable for the target unless free historical access is empirically confirmed. Not built. |

## What is true vs. unverified

- **True:** Spark is the only source that gives the *actual* target series; the
  free non-authenticated endpoint is delayed ("Price Release N-4") and appears
  latest-value only, so it cannot rebuild a past window now. ICE/EEX/Baltic have
  no *confirmed* free historical daily feed.
- **Unverified (the decisive unknown):** whether a Spark **free-trial or academic**
  OAuth2 client returns Spark25S/30S over **2026-02-01 → 2026-06-01** at daily
  granularity. This is settled only by testing with real credentials.

## State of the code

- `src/lngfreight/sources/spark.py` — PRIMARY adapter. OAuth2 client-credentials
  auth and response shape taken verbatim from Spark's official sample code. It
  **requires** `SPARK_CLIENT_ID` + `SPARK_CLIENT_SECRET`, **fails loudly** without
  them, **never fabricates** a freight value, and **refuses a silently truncated
  history** (raises if the earliest available release postdates the requested
  start). Tested with mocked responses only (`tests/test_spark_source.py`).
- The `spark*` registry targets remain `status: unavailable`, so `get_variable()`
  does **not** route to the adapter yet. **Activation = a one-line swap:** once a
  trial/academic client is confirmed to cover the window, flip those targets to
  `status: primary` in `config/sources.yaml`. No code change.
- No ICE/EEX/Baltic freight fetch is implemented. They map to `None` in
  `sources/__init__.py` and raise a clear "no free backend" error if requested.

## Open action items (only the human can do these)

1. Email Spark (`info@`/`sales@sparkcommodities.com`) for academic/research access
   (TUM thesis; name Spark25S, Spark30S, daily, Feb–Jun 2026).
2. Create a free-trial OAuth2 client at
   https://app.sparkcommodities.com/freight/data-integrations/api and test the
   adapter against the study window. Record the verified history depth here.
