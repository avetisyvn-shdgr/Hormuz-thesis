# Study-window extension (v2) runbook — 2026-07-15

> **Execution status (updated 2026-07-15, Claude session):**
> - Phase 0 DONE except git: the critical raw-v1 rollback files and original
>   provenance manifests are archived at
>   `../Archive/Technical_Recovery/Raw_Vintages/2026-07-15_v1/`;
>   Option D files moved to `data/raw_staging/` (gitignored); `.DS_Store` neutralized
>   by patching `vessel_raw_hashes` to ignore OS junk (sandbox cannot delete files);
>   `freeze_reproducibility.py --check` passes 3/3; reproducibility tests pass.
> - Git could NOT be done from the sandbox (mount blocks unlink; stale
>   `.git/stale.lock.old{,2,3}` files left behind — DELETE these locally, they are
>   renamed dead lock files, harmless but junk).
> - CORRECTION: the "live WTO source is a rolling window" warning below is
>   UNVERIFIED — it came from a masked provenance copy, not a live fetch. The
>   canonical snapshot already reaches **2026-06-18** (index still 0.0 = strait
>   still fully closed). `fetch_wto_hormuz_lng.py` prints the live range — check
>   its `start=` output to settle the rolling-window question.
> - All API keys present in `.env`. Remaining steps for Mher: §"Remaining steps"
>   at the bottom.

**Goal:** extend `study_window.full_end` from 2026-06-01 to ~mid-July to measure
persistence. **v1 (2026-06-01) remains the pre-registered primary window; v2 is
an extension analysis.** The treatment cutoff 2026-02-28 does not move. Nothing
is re-tuned after seeing v2 data.

## Phase 0 — protect v1 (do this before downloading anything)

Raw CSVs are **not git-tracked** (only SHA256SUMS is). Git cannot restore them.

1. Back up the entire raw dir outside the repo, ideally also to cloud. Use a new
   dated directory under `../Archive/Technical_Recovery/Raw_Vintages/` for each
   snapshot. The 2026-07-15 local archive was later pruned to the two changing
   source snapshots plus its original provenance and checksum manifests.
   The WTO snapshot is the urgent one — the live source is a rolling window
   that has already dropped Jan–Feb 2025; your copy is irreplaceable.
2. Fix the P1 staging problem so freeze checks can pass again:
   - `mkdir data/raw_staging`
   - move into it: `data/raw/gem/GEM-GGIT-Gas-Pipelines-2025-11.xlsx`,
     `data/raw/gem/Global-Energy-Ownership-Tracker-May-2026-V1.xlsx`,
     `data/raw/ppac/`, `data/raw/taiwan/`
   - `find data/raw -name .DS_Store -delete`
   - add `data/raw_staging/` to `.gitignore`
   - confirm: `python scripts/freeze_reproducibility.py --check` → 3× PASSED
3. Clean tree + branch:
   - commit or discard `.env.example` and `scripts/check_enrichment_keys.py`
   - `git checkout -b extension/post-window-v2`

## Phase 1 — gather

| # | What | Where | Key needed | Replaces |
|---|---|---|---|---|
| 1 | Daily Chokepoint Transit Calls (full CSV, all chokepoints) | portwatch.imf.org → Data → Daily Chokepoint Transit Calls dataset | none | `data/raw/portwatch/Daily_Chokepoints_Data.csv` |
| 2 | WTO Hormuz LNG outbound index | `https://wtomais.blob.core.windows.net/strait-of-hormuz-tracker/voy_intake_index_lng_export.csv` | none | `data/raw/wto_hormuz/voy_intake_index_lng_export.csv` |
| 3 | Brent + Henry Hub | auto via EIA API on rebuild | `EIA_API_KEY` in `.env` | eia snapshots (rewritten by build) |

**Checks before replacing anything:**

- PortWatch: open the new CSV, find the max date for `strait_of_hormuz`.
  Trailing days can be incomplete. **Set the new `full_end` = max date − 5
  days** (same buffer as v1: snapshot reached 06-07, window ended 06-01).
- WTO: check the max date FIRST. As of 2026-07-14 the live blob still ended
  **2026-06-01** (tracker frozen or lagging). If it has not advanced past your
  planned `full_end`, the WTO corroboration and the
  `wto_departure_validation.comparison_windows` in settings.yaml **stay at the
  v1 window** — do not stretch a matched 94-day YoY design to unequal windows.
  Only PortWatch-based layers extend. State this in the write-up.
- Do not overwrite the old files in place until the backup in Phase 0 exists.

## Phase 2 — repo changes and re-run

1. `config/settings.yaml`: set `study_window.full_end` to the chosen date.
   Touch nothing else: cutoff, sensitivity dates, and (unless WTO advanced)
   the `wto_departure_validation` windows stay as they are.
2. Rebuild from live/refreshed inputs: `python scripts/build_panel.py`
   (NO `--frozen-raw`) — re-pulls EIA, re-extracts PortWatch series, writes new
   provenance snapshots.
3. Re-freeze inputs: `python scripts/freeze_reproducibility.py` (no flag).
4. Full pipeline: `python scripts/run_all.py`. Expected changes, all normal:
   - post-period grows 94 → ~130+ days; placebo-in-time window count DROPS
     (longer horizon fits fewer pre-period windows) — the p-value floor
     changes accordingly; report it as the v2 floor, not an improvement/decline
   - BSTS and placebo steps run noticeably longer
   - all summaries regenerate; do not hand-edit any v1 number — v1 values
     remain quotable from the v1 branch/commit
5. If any test fails, stop and paste the error (candidates: anything with a
   hard-coded 94-day horizon, e.g. `test_corridor_inference.py:93`).
6. Commit on `extension/post-window-v2` with the re-frozen manifest.

## Out of scope tonight

- GFW mechanism branch stays at the v1 window (needs token pulls + terminal
  re-matching; separate night).
- No model changes, no new generators, no cutoff or window tuning. The GBM
  generator is a separate increment.

## Remaining steps (Mher, local terminal, in order)

```bash
cd lng_freight_thesis
# 1. Git cleanup + housekeeping commit + branch (sandbox couldn't do this)
rm .git/stale.lock.old .git/stale.lock.old2 .git/stale.lock.old3
git add .gitignore .env.example scripts/freeze_reproducibility.py \
        scripts/check_enrichment_keys.py docs/VALIDATION_REPORT_2026-07-15.md \
        docs/WINDOW_EXTENSION_V2_RUNBOOK.md
git commit -m "Housekeeping: validation report, v2 runbook, staging quarantine, junk-file-proof input hashing"
git checkout -b extension/post-window-v2

# 2. WTO refresh (also answers the rolling-window question — note the start= line)
.venv/bin/python scripts/fetch_wto_hormuz_lng.py

# 3. PortWatch: browser download from portwatch.imf.org
#    -> Daily Chokepoint Transit Calls dataset -> full CSV
#    -> replace data/raw/portwatch/Daily_Chokepoints_Data.csv
#    Then check the max complete date:
.venv/bin/python - <<'EOF'
import pandas as pd
df = pd.read_csv("data/raw/portwatch/Daily_Chokepoints_Data.csv")
date_col = [c for c in df.columns if "date" in c.lower()][0]
print("max date overall:", df[date_col].max())
EOF

# 4. Edit config/settings.yaml: study_window.full_end = (max date - 5 days)
#    Touch nothing else.

# 5. Rebuild, freeze, run, re-freeze (the freeze->run->freeze dance is expected:
#    the first run_all's final --verify step FAILS because artifacts legitimately
#    changed; the second freeze locks the new state, then verify passes)
.venv/bin/python scripts/build_panel.py
.venv/bin/python scripts/freeze_reproducibility.py
.venv/bin/python scripts/run_all.py          # expect ONLY the final verify step to fail
.venv/bin/python scripts/freeze_reproducibility.py
.venv/bin/python scripts/run_all.py          # must pass all 36 steps
git add -A && git commit -m "v2: extend study window, refreshed PortWatch/WTO/EIA snapshots, re-frozen manifest"
```

Paste back: the `fetch_wto_hormuz_lng.py` output, the PortWatch max date, and
the tail of each `run_all.py` run. Do not report v2 numbers into any document
until the second run passes clean.

## What v2 buys

Persistence: does the shortfall rate (~55/day) hold through July, decay, or
show reopening dynamics? This answers the dropped `regime_consolidation`
question with data instead of a design workaround, and pre-empts the obvious
defense question ("your data ends June 1 — what happened after?").

---

# v3 extension note — 2026-08-09 (approved in principle, execution pending)

**Goal:** extend `study_window.full_end` from 2026-07-07 to ≥ **2026-08-01**
so the July events sit in-window: the 07-07 attack resumption, the 07-19/20
escalation, the Iran–Oman proposals, and the **07-29 Damietta confound**
(see `EVENT_CHRONOLOGY.md` post-March table and `SUTVA_CONTAMINATION_AUDIT.md`
new section). Approved by Mher 2026-08-09 (`DECISION_LOG.md`); v1 and v2
remain quotable from their branches; the 2026-02-28 cutoff does not move.

**What changed since v2:**

- The WTO series was refreshed on 2026-08-09 via `fetch_wto_hormuz_lng.py`
  (registry-sanctioned): `rows=586 start=2025-01-01 end=2026-08-09`. The
  v2-era "tracker frozen at 06-01" and "rolling window dropped Jan–Feb 2025"
  concerns are both **not borne out**.
- **Correction to an earlier note in this file:** the post-cutoff LNG index is
  *not* uniformly 0.0. It is zero on 155 of 163 post-cutoff days, with eight
  isolated partial-loading days (2026-03-01 68.3, 03-02 26.6, 03-28 27.1,
  05-02 41.6, 06-13 33.5, 06-28 26.0, 07-05 25.7, 07-06 29.2; 2025 base =
  100). The correct claim is **no sustained resumption**, not "no loadings".
- The refresh also **revised one in-window historical day**: 2026-07-06 moved
  from 0.0 to 29.21 — a late-arriving partial-loading observation inside the
  v2 primary window (≤ 2026-07-07). See the v3 status note below.
- The `wto_departure_validation.comparison_windows` **stay at v1** per the
  2026-08-09 decision; only PortWatch-based layers extend.

**Interpretive obligation (write-up):** the v3 post-period is a **regime
mixture** — closure → MoU/attempted reopening (06-17) → renewed attacks
(07-07 onward) — plus the non-Hormuz Damietta confound in the tail. The
persistence numbers must be presented against that chronology, not as a
homogeneous closure regime. Donor re-check: rerun the donor-influence
diagnostic on the v3 window (Damietta may shift Mediterranean-adjacent
corridor traffic; see SUTVA addendum).

**Steps (Mher, local terminal — same dance as v2):**

```bash
cd lng_freight_thesis
git checkout -b extension/post-window-v3
# 1. Backup current raw dir outside the repo first, using a new dated directory:
cp -R data/raw ../Archive/Technical_Recovery/Raw_Vintages/YYYY-MM-DD_pre-refresh
# 2. WTO refresh (registry-sanctioned; note the start= and max lines):
.venv/bin/python scripts/fetch_wto_hormuz_lng.py
# 3. PortWatch: browser download from portwatch.imf.org -> Daily Chokepoint
#    Transit Calls -> full CSV -> replace data/raw/portwatch/Daily_Chokepoints_Data.csv
#    Then check the max date:
.venv/bin/python - <<'PYEOF'
import pandas as pd
df = pd.read_csv("data/raw/portwatch/Daily_Chokepoints_Data.csv")
date_col = [c for c in df.columns if "date" in c.lower()][0]
print("max date overall:", df[date_col].max())
PYEOF
# 4. Edit config/settings.yaml: study_window.full_end = (max date - 5 days).
#    If that lands before 2026-08-01, STOP and record why (PortWatch lag);
#    do not force the date. Touch nothing else.
# 5. Rebuild, freeze, run, re-freeze (first run_all's final verify step is
#    expected to fail once, then pass after the second freeze):
.venv/bin/python scripts/build_panel.py
.venv/bin/python scripts/freeze_reproducibility.py
.venv/bin/python scripts/run_all.py
.venv/bin/python scripts/freeze_reproducibility.py
.venv/bin/python scripts/run_all.py
git add -A && git commit -m "v3: extend study window through early August, refreshed snapshots, re-frozen manifest"
```

Paste back: the WTO fetch output, the PortWatch max date, and the tail of each
`run_all.py` run. No v3 number enters any document until the second run passes
clean.
