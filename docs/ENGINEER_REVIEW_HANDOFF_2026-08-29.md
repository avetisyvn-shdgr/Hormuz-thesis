# Engineer review handoff — 29 August 2026

## Purpose

This is a private technical review of a Bachelor-thesis research repository.
Please help with two separate questions:

1. Can another person understand, install, test and reproduce the current work?
2. Do the code and artifacts support the claims made in the result summaries?

Do not treat this directory as a public release. No software licence has been
selected, some local inputs have redistribution restrictions, and the current
working tree is not clean.

## Start here

Read these files in order:

1. `README.md` — scope, data boundaries, installation and intended pipeline.
2. `reports/current_results_summary.md` — current primary result table.
3. `experiments/panel_bakeoff/RESULTS.md` — forecasting benchmark and its limits.
4. `docs/NETWORK_ADAPTATION_SECONDARY_CHAPTER.md` — newest exploratory network
   analysis and claim boundary.
5. `config/settings.yaml`, `config/model_admission_protocol.yaml` and
   `config/network_adaptation.yaml` — locked design choices.
6. `src/lngfreight/`, `scripts/`, `experiments/` and `tests/` — implementation.

`AGENTS.md` is useful as a short statement of the methodological guardrails,
but it is not evidence that the implementation obeys them. Please verify the
code and artifacts independently.

## Current repository state

- Repository: `lng_freight_thesis/`
- Branch: `ml/hormuz-revision-robust`
- Current committed HEAD: `339f97b`
- No Git remote is configured.
- The live tree has 51 changed paths: 27 modified tracked files and 24
  untracked files. The newest robustness work is therefore not represented by
  HEAD alone.
- The surrounding workspace is about 3.5 GB and is not the repository. It
  contains manuscripts, virtual environments, generated PDF previews, backups,
  restricted-data quarantine and scratch material.

### Live verification on 29 August 2026

Command:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 \
  .venv-claude/bin/python -m pytest -p no:cacheprovider -q
```

Result: **754 passed, 13 failed, 64 skipped, 333 warnings** in 114.66 seconds.

The 13 failures are concentrated in the repository-integrity layer:

- eight final-integration-audit failures caused by missing upstream artifacts;
- two public-data-gate failures caused by a pinned `config/sources.yaml` hash
  no longer matching the live registry; and
- three PortWatch-sensitivity gate failures caused by missing manifests and a
  declared-consumer mismatch.

The current experiment-focused tests pass:

```text
tests/test_network_adaptation.py
tests/test_panel_bakeoff.py
tests/test_positive_control.py
39 passed
```

Additional checks:

- core frozen inputs: pass;
- vessel raw-snapshot hash verification: **fail**;
- interim frozen inputs: pass;
- 13 manuscript PDF/PNG figure pairs: present;
- `git diff --check`: pass.

These failures do not by themselves refute the numerical results, but they do
block a claim that the current tree is a clean, frozen, end-to-end reproducible
release.

## What the results currently support

### Primary result: strong descriptive signal, limited formal inference

The working primary outcome is IMF PortWatch daily tanker-transit count at the
Strait of Hormuz. It is an AIS-derived aggregate and is not LNG-specific cargo,
freight price, welfare loss or ground truth.

- AR(1,7) chronological validation: mean MASE 0.92 versus 1.00 for the
  seven-day seasonal naive model; mean sMAPE 23.31%.
- On 28 February–7 July 2026, the AR model reports 529 observed transits against
  7,397.996 counterfactual transits: a 6,868.996-transit shortfall, or 52.838 per
  day.
- Across the legacy and expanded-history AR/Chronos specifications, observed
  traffic is 92.47%–93.01% below counterfactual. The direction and broad
  magnitude are stable even though the AR-versus-Chronos difference changes
  sign when the training window changes.
- Only seven disjoint 130-day historical reference blocks are available. The
  one-sided rank p-value is 0.125, the nominal 95% block-conformal interval is
  unbounded, and maximum finite coverage is 87.5%.

The defensible conclusion is therefore a very large
**disruption-associated counterfactual shortfall** in observed tanker traffic.
It is not a 5%-level causal effect and should not be presented as one.

### Forecast benchmark: useful, but not decisive for the event conclusion

Chronos-2 improves macro MASE over AR(1,7) by 17.6% at 30 days and 14.5% at the
event-matched 130-day horizon. The clustered 95% interval for the 130-day
reduction is [1.4%, 23.7%], so the gain is positive but imprecisely bounded.
The event signal remains overwhelming under either model. The newest diagnostic
does not prove that Chronos pretraining was uncontaminated; it only shows that
the advantage does not decay at the latest rolling origin as a simple overlap
story would predict.

### Network analysis: technically interesting, exploratory evidence

The newest network-adaptation work supports positive abnormal tanker activity
at Panama Canal and Yucatan Channel across the declared model/block variants.
It does not prove physical rerouting, displaced Hormuz volume, LNG-specific
movement or causality.

Important qualifications:

- the five-corridor family was selected retrospectively after earlier results
  had been inspected;
- all-28-corridor disclosure finds other corridors that clear some cells;
- Cape of Good Hope residuals show pre-event drift, so Cape is context rather
  than reliable corroboration;
- family-level and vessel-class-specific conclusions change with control
  weighting, although Panama and Yucatan do not; and
- a Red Sea positive-control exercise is encouraging for the machinery, but it
  also demonstrates why non-tanker movement is not a simple falsifier of a
  network-wide disruption.

## Questions for the engineering review

Please return issues ranked as blocking, important or cosmetic. For each issue,
cite a path and, where possible, a line or reproducible command.

### Repository and reproducibility

1. What is the smallest coherent public-data package boundary?
2. Can the four virtual environments and five requirements files be reduced or
   mapped clearly? Which requirements file is actually authoritative?
3. Does `scripts/run_all.py` reproduce the current bake-off, network,
   positive-control, robustness and figure artifacts in dependency order?
4. Which outputs are true source-controlled evidence, which are regenerable
   build products, and which should move to a separate artifact bundle?
5. Are provenance and hash checks internally consistent? Explain the vessel
   snapshot mismatch before refreshing any manifest.
6. Are there dead scripts, duplicate pipelines, stale documents or conflicting
   entry points that can be removed after a safe archive/commit?
7. Are random seeds, environment identity, model revision and generated-file
   hashes sufficient to reproduce the reported results?
8. Do the numerical overflow/invalid-value warnings indicate a real production
   path risk, or only deliberately pathological test fixtures?

### Result validity

1. Verify that every model is trained strictly before 28 February 2026 and that
   rolling-origin evaluation is chronological.
2. Recalculate the main 529 observed, 7,397.996 counterfactual and 6,868.996
   shortfall figures from the underlying daily artifact.
3. Check target definitions, missingness, duplicate keys, time alignment and
   data-vintage selection.
4. Check whether any post-event or donor information enters a forecast that is
   described as forecast-only.
5. Review MASE/sMAPE denominators, clustered bootstrap units, moving-block
   resampling, centering/studentization and Romano–Wolf family construction.
6. Confirm that the AR/Chronos training-window sensitivity is generated rather
   than typed and that summaries do not quote the legacy 3.7% comparison without
   its 2022 training start.
7. Assess whether the network negative-control weighting and the Cape residual
   drift treatment are methodologically adequate.
8. Identify any sentence that implies causality, LNG specificity, observed
   rerouting or statistical significance beyond what the artifacts support.

## What to share, and what not to share

Preferred transfer: a **private, read-only repository** or a password-protected
archive shared directly with the reviewer. Preserve the current Git branch and
history, but first commit the intended work or provide an explicit working-tree
snapshot; sharing only HEAD would omit the newest robustness analysis.

Include:

- repository root metadata and this handoff;
- `config/`, excluding proprietary-source configuration;
- `src/`, public-data `scripts/`, `tests/` and the three current experiment
  directories;
- the result summaries and the exact generated artifacts they cite; and
- a cleared, separate input-artifact bundle only if redistribution rights have
  been checked.

Do not include:

- `.env`, credentials, tokens or private local settings;
- `.venv*`, caches, `__pycache__`, IDE files or `.work/`;
- ignored `data/raw/`, `data/interim/` or local staging directories without an
  explicit rights review;
- `bloomberg_quarantine/`, workspace `data/bloomberg/`, Bloomberg/Fearnleys/
  ClearLynx-derived files or licensed-source figures;
- approval evidence, personal defence material, internal prompts or private
  correspondence;
- LaTeX build auxiliaries, rendered page scratch, historical backups or the
  surrounding 3.5 GB workspace.

The current `.env` exists locally and is correctly ignored. Verify its absence
from any archive rather than relying on a broad copy command.

## Requested deliverable

Please provide:

1. a one-page architecture map;
2. a proposed clean repository tree and migration plan;
3. a minimal reproducibility command with exact environment requirements;
4. a table mapping each headline claim to source data, generator, output and
   test;
5. independent recalculation of the headline results; and
6. a prioritized issue list separating code/reproducibility defects from
   methodological limitations.

Do not rewrite manifests, delete outputs, change the treatment date, tune models
or reorganize the live tree before reporting what those changes would affect.
