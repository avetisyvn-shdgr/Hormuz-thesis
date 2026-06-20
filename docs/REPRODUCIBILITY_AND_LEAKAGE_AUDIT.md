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
161 passed
```

All 161 tests pass with no network access. No code changes were needed to make
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
`tsfm_*` benchmark CSV hashes are recorded in the separate TSFM manifest. They
are deliberately excluded from the core `reproducibility_manifest.json` because
the weight runs require separate environments and cached model snapshots.

**Two hygiene flags to clear before citing the numbers in the thesis:**
- `.venv-bench` reports inconsistent pandas metadata: `pip freeze` says 2.3.3 but
  `importlib.metadata` (what the code actually imports) resolves 2.1.4. Rebuild
  `.venv-bench` cleanly so the resolved version is unambiguous.
- The TSFM numbers remain the user's **first recorded run** (CLAUDE.md rule 4).
  Re-run `scripts/freeze_tsfm_run.py` on the same machine immediately after the
  benchmark to certify the manifest matches the cited table. Admission verdict on
  the matched subset is unchanged: all six model×target cells `ADMITTED`, but
  `ADMITTED` means *eligible as a cross-check only* — never the locked primary.

## 3. Deterministic end-to-end reproducibility — PASS

`scripts/run_all.py` now runs 35 offline steps spanning the PortWatch model and
the open-data LNG mechanism branch. It verifies 9 core raw snapshots, 11 vessel
raw snapshots, and one frozen carrier preprocessing input before execution. It
then regenerates the panel, models, inference outputs, event-study figures,
vessel sequences, route distances, capacity-nautical miles, WTO validation,
importer exposure, vessel-days, and both generated result reports.

The runner no longer overwrites the reference manifest. Its final step invokes
`freeze_reproducibility.py --verify`, which builds a candidate manifest in a
temporary directory and compares it with the committed manifest. Missing,
unexpected, or changed hashes fail the run. The verified run on 2026-06-20
finished with:

```text
INPUT HASH CHECK PASSED: 9 core raw files match.
INPUT HASH CHECK PASSED: 11 vessel raw files match.
INPUT HASH CHECK PASSED: 1 interim inputs match.
161 passed
ARTIFACT VERIFICATION PASSED: 87 regenerated artifacts match.
END-TO-END RUN COMPLETED CLEANLY
```

The 87-file scope is an explicit allowlist, not a directory glob. Matplotlib PDF
creation/modification dates are pinned so PDF bytes are deterministic. Rebuilding
an identical derived raw crosswalk is provenance-idempotent and does not append a
new timestamped log entry.

The guarantee deliberately excludes three artifact families that the core
environment cannot regenerate faithfully: isolated TSFM weight runs (separate
`tsfm_run_manifest.json`), the credential-gated Spark access report, and manually
assembled supervisor presentation assets. The manifest states these exclusions
explicitly rather than silently hashing them.

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
