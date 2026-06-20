# Reproducibility & AR-only Leakage Audit

**Status:** Engineering audit, 2026-06-20. Covers the four "make the ML code
properly done" items: (1) independent-venv suite run, (2) TSFM run provenance
freeze, (3) deterministic end-to-end reproducibility, (4) AR-only leakage and
code-quality audit. Does not alter the estimand, the locked AR-only primary, or
the Transformer prohibition.

## 1. Suite run in a clean, independent venv — PASS

A fresh interpreter (`/opt/homebrew/bin/python3.14` → `3.14.4`, matching the
frozen manifest) was created at `.venv-claude` from `requirements.txt` only. The
exact pinned versions resolved (numpy 1.26.4, pandas 2.3.3, pytest 8.4.2, PyYAML
6.0.3, requests 2.34.2, searoute 1.6.0, matplotlib 3.11.0) — identical to the
manifest's `packages` block, so `requirements.txt` reproduces the frozen core
environment from scratch.

```
PYTHONHASHSEED=0 OMP_NUM_THREADS=1 .venv-claude/bin/python -m pytest -q
156 passed in ~7s
```

All 156 tests pass with no network access. No code changes were needed to make
the suite green in a clean environment.

## 2. TSFM run frozen into a manifest — DONE (isolated)

`docs/MODERN_TSFM_BENCHMARK.md` required that the exact package versions, model
revisions, device, and output hashes be frozen before any TSFM number is cited.
Because the TSFM benchmark is deliberately isolated (excluded from `run_all.py`
and the frozen core requirements; two separate Python-3.11 venvs), its provenance
is frozen by a **separate** script, `scripts/freeze_tsfm_run.py`, into
`data/processed/tsfm_run_manifest.json` rather than bolted onto the core freeze.

Captured (verified on disk 2026-06-20):

| Env | Python | Key versions |
|---|---|---|
| `.venv-bench` (Chronos-2 + Moirai 2.0) | 3.11.15 | chronos-forecasting 2.3.0, torch 2.4.1, uni2ts 2.0.0, gluonts 0.14.x, transformers 5.12.1 |
| `.venv-timesfm` (TimesFM 2.5) | 3.11.15 | timesfm 2.0.1, torch 2.12.1 |

Model revisions (HF snapshot commits): `amazon/chronos-2`
`29ec3766…`, `google/timesfm-2.5-200m-pytorch` `1d952420…`,
`Salesforce/moirai-2.0-R-small` `30f43ff0…`. Device: `cpu`, macOS arm64. The four
`tsfm_*` benchmark CSV hashes recorded in the TSFM manifest match the core
`reproducibility_manifest.json` byte-for-byte, confirming the on-disk benchmark
outputs are the ones cited.

**Two hygiene flags to clear before citing the numbers in the thesis:**
- `.venv-bench` reports inconsistent pandas metadata: `pip freeze` says 2.3.3 but
  `importlib.metadata` (what the code actually imports) resolves 2.1.4. Rebuild
  `.venv-bench` cleanly so the resolved version is unambiguous.
- The TSFM numbers remain the user's **first recorded run** (CLAUDE.md rule 4).
  Re-run `scripts/freeze_tsfm_run.py` on the same machine immediately after the
  benchmark to certify the manifest matches the cited table. Admission verdict on
  the matched subset is unchanged: all six model×target cells `ADMITTED`, but
  `ADMITTED` means *eligible as a cross-check only* — never the locked primary.

## 3. Deterministic end-to-end reproducibility — PROVEN, with a stale-manifest fix required

**Determinism is proven.** The full core pipeline was regenerated in
`.venv-claude` under the `run_all.py` environment flags (`PYTHONHASHSEED=0`,
single-thread BLAS, fixed `MPLCONFIGDIR`). Against the frozen manifest:

- **All 13 figure artifacts (PNG/PDF) are byte-identical.** matplotlib output is
  reproducible once `MPLCONFIGDIR` is pinned.
- **50 of 53 data/text artifacts are byte-identical.**
- The panel build was run **twice**; the two fresh `panel_aligned.csv` outputs
  are byte-identical to each other → the pipeline itself is deterministic.

**Three artifacts differ from the frozen manifest, and the cause is a stale
manifest, not non-determinism:**

| Artifact | Why it differs |
|---|---|
| `panel_aligned.csv` | Now carries a `wto_hormuz_lng_outbound_index` column (8 cols) integrated *after* the last freeze. Deterministic across reruns. |
| `model_input_coverage.csv` | Reflects the panel's column set; changed for the same reason. |
| `vessel_data_feasibility.json` | Phase-3A vessel-branch artifact regenerated after the last freeze; not produced by `run_all.py`. |

**`run_all.py` currently aborts at step 1.** The raw-hash check
(`freeze_reproducibility.py --check`) globs the *entire* `data/raw/` tree and
finds 23 files, but the frozen `SHA256SUMS` records only the 9 core PortWatch
inputs. The extra 14 are Phase-3A vessel-branch raw files (GFW/GEM) plus a few
transient download `.zip`s that landed after the last freeze. So the "frozen
PortWatch run" cannot self-verify, which blocks a clean end-to-end pass.

### Required decision before re-freezing (see open question)

The fix is a **scope** decision on the raw-hash check, with thesis-framing
consequences:

- **(A) Core-scoped (recommended).** Restrict the raw-hash check to the core
  PortWatch inputs `run_all.py` actually consumes (the existing 9), and freeze the
  vessel-branch raw inputs separately (excluding transient `.zip`s). This keeps
  the architecture's branch separation — `run_all.py` stays a self-verifying,
  PortWatch-only pipeline independent of the optional vessel branch.
- **(B) Whole-tree.** Re-freeze all current raw files into one `SHA256SUMS`. This
  couples the core run's precheck to the presence/identity of vessel-branch files
  and would canonicalize transient `.zip`s — contrary to the documented branch
  isolation.

Either way the manifest must then be re-frozen so `panel_aligned.csv`,
`model_input_coverage.csv`, and `vessel_data_feasibility.json` hashes are current.
**Because the manifest is described as "frozen" but was found stale, and it is a
load-bearing record, the re-freeze is held pending your scope choice rather than
silently overwritten.**

## 4. AR-only primary — leakage and code-quality audit — CLEAN

The AR-only estimator (`ar_lag1_7`) is the locked primary precisely because it
consumes no post-treatment covariates. Audit of `validation.py`, `baselines.py`,
`ar_intervals.py`, and `run_counterfactual.py`:

**Leakage controls — sound.**
- `rolling_origin_splits` enforces two guards *by construction and re-asserts them
  independently* in `_assert_no_leakage`: every test fold is strictly after its
  train window, and every fold lies strictly before the treatment cutoff. The
  cutoff resolves from `study_window.primary_treatment_cutoff` (2026-02-28) and an
  added later milestone cannot silently move it (`resolve_cutoff`,
  `validation.py:56`).
- The recursive AR forecast fills the test horizon with its **own prior
  predictions**, never held-out observed target values (`arx_forecast`,
  `baselines.py:203-214`). Verified for both the validation folds and the
  post-treatment counterfactual fold.
- The post-treatment fold seeds the recursion from `y.loc[:train_end]`, i.e. the
  last *pre-cutoff* observed values as legitimate initial lags; the first test
  day's lag-1/lag-7 read pre-cutoff observations only, and every later lag reads
  predictions. **No post-treatment observed target enters as a predictor.**
- Standardization statistics (`x_mean`, `x_std`) are computed on the training rows
  only and applied to the test rows (`_standardized_ridge_fit`,
  `baselines.py:128`). Weekly seasonality is deterministic `dow_sin/cos` — no
  future information.
- AR-only passes `exog_cols=[]`, so the contemporaneous-exog read in `_design_row`
  (`panel.at[ts, col]`) is never exercised for the primary. That path is the
  documented post-treatment-bias channel for the route/route+energy ARX
  *sensitivities*, correctly kept out of the primary.

**Code quality — good, minor notes.**
- NaN forecasts are excluded from metrics rather than silently filled
  (`n_scored`), and folds with an empty side are skipped, not emitted — honest.
- Ridge uses an augmented least-squares system (numerically stable for the
  millions-scale capacity target) and never penalizes the intercept — correct.
- Suggested hardening (optional): add a unit test asserting that, for the
  post-treatment fold, the AR design matrix for the primary never references a
  row index `>= cutoff` except through prior predictions. The behaviour is already
  correct; the test would lock it against future refactors, mirroring the
  defensive `_assert_no_leakage` pattern.

**Verdict: no leakage found in the AR-only primary path.** The estimator is
leakage-safe end-to-end, and the surrounding fold geometry is the shared,
re-asserted guard for every downstream estimator.
