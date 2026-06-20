# Project structure guide

This guide explains the repository for a reader with no programming or machine
learning background. It describes what is present as of 2026-06-19; it does not
change the thesis's formal research question or claim that unavailable data has
been obtained.

## The project in one sentence

The working model estimates how many tanker transits through the Strait of
Hormuz were missing relative to a pre-disruption forecast, then checks whether
that unusual drop survives several robustness tests.

This is currently a study of **aggregate tanker throughput**, not a direct model
of LNG freight rates, LNG cargoes, or causal importer losses. Spark25S and
Spark30S remain preserved as optional freight-rate outcomes if access arrives.

## Start here

1. `README.md` explains the research idea, setup, and broad pipeline.
2. `docs/CURRENT_PLAN.md` states the active next research phase.
3. `reports/current_results_summary.md` contains the current numerical results.
4. `config/settings.yaml` records the locked dates, outcomes, models, and rules.
5. `docs/VESSEL_DATA_FEASIBILITY.md` explains why the next empirical branch is
   blocked pending a vessel sample and what evidence is required to unblock it.

`AGENTS.md` and `CLAUDE.md` are operating rules for AI assistants. They are not
thesis chapters or model code.

## Folder map

| Location | Plain-language purpose | Edit by hand? |
|---|---|---|
| `config/` | The control panel: data definitions, dates, paths, and validation rules | Carefully |
| `src/lngfreight/` | The reusable calculation engine | Only with tests |
| `scripts/` | The buttons that run one pipeline task at a time | Yes, with tests |
| `tests/` | Automated checks that detect broken logic and data leakage | Add when logic changes |
| `data/raw/` | Original source snapshots and provenance | No; treat as immutable |
| `data/interim/` | A mechanically combined but not fully aligned panel | Normally generated |
| `data/processed/` | Model-ready tables, scores, forecasts, and audit outputs | Normally generated |
| `reports/` | Human-readable summaries and figures | Normally generated |
| `docs/` | Methodological decisions, access notes, limitations, and plans | Yes |
| `notebooks/` | Reserved for notebooks; currently empty | Not currently used |

## How data moves through the project

```text
external/free source or frozen snapshot
              |
              v
data/raw/  -> data/interim/panel_free.csv
              |
              v
data/processed/panel_aligned.csv
              |
              v
validation -> forecasts -> counterfactual gaps -> robustness checks
              |
              v
data/processed/ tables + reports/ figures and summaries
```

The raw layer preserves what was received. The interim layer joins series. The
processed layer applies documented alignment rules and contains derived results.
Keeping these layers separate makes it possible to audit where a value changed.

## The two configuration files

### `config/sources.yaml`

This is the data dictionary. Each logical variable has a role, provider, code,
licence/access status, and any proxy warning. Provider-specific code reads this
file, so Spark can later be activated without rewriting the model architecture.

### `config/settings.yaml`

This is the experiment rulebook. It locks the study window, the operational
treatment cutoff (`2026-02-28`), missing-data rules, chronological validation,
random seed, working outcome, estimators, and vessel-data acceptance thresholds.

## The calculation engine

The modules under `src/lngfreight/` each have one main responsibility:

| Module | What it does |
|---|---|
| `config.py` | Loads the two YAML control files and secrets from `.env` |
| `registry.py` | Resolves a logical variable to the correct data provider |
| `sources/` | Reads EIA, FRED, PortWatch, WTO, or optional Spark data |
| `provenance.py` | Saves raw pulls and records a cryptographic fingerprint |
| `panel.py` | Joins source series by date |
| `clean.py` | Aligns dates and applies the documented missing-data policy |
| `validation.py` | Creates chronological train/test windows and blocks leakage |
| `baselines.py` | Fits the transparent seasonal-naive, AR, and ARX forecasts |
| `metrics.py` | Calculates forecast errors such as MAE and RMSE |
| `inference.py` | Calculates post-event gaps, intervals, and temporal placebos |
| `spatial.py` | Compares Hormuz with other chokepoints on the same dates |
| `synthetic.py` | Builds a weighted donor comparison for Hormuz |
| `bsts.py` | Runs the Bayesian structural time-series cross-check |
| `tsfm.py` | Isolates optional foundation-model benchmarks and their gate |
| `diagnostics.py` | Reports coverage, missingness, and model information sets |
| `eventstudy.py` | Produces the descriptive figures |
| `specification.py` | Validates that configured outcomes and models have valid roles |
| `feasibility.py` | Audits whether vessel data can support the next research branch |

## Scripts and the end-to-end runner

Each file in `scripts/` is a small command-line entry point. Most names say what
they do: `run_baseline.py` validates the baseline, `run_counterfactual.py`
estimates the post-event gap, and `run_spatial_placebo.py` performs the spatial
comparison.

`scripts/run_all.py` runs the PortWatch and open-data LNG mechanism pipelines in
order, regenerates 87 declared artifacts, runs the complete test suite, and
compares a temporary candidate manifest with the committed reference manifest.
Output drift fails the run; the reference manifest is never overwritten by the
verification path.
Optional Transformer/foundation-model benchmarks are deliberately excluded from
this core runner because they require large model weights and separate software.

## Why there are three Python environments

| Folder | Purpose | Approximate size after cache cleanup |
|---|---|---:|
| `.venv/` | Core, reproducible PortWatch pipeline and tests | 135 MB |
| `.venv-bench/` | Optional Chronos-2 and Moirai benchmark stack | 2.2 GB |
| `.venv-timesfm/` | Optional TimesFM stack, isolated because of dependency conflicts | 614 MB |

These are not accidental duplicates. The benchmark libraries require
incompatible PyTorch versions, so combining them can silently break forecasts.
All three folders are ignored by Git and can be recreated from the requirements
files, but keeping them avoids expensive reinstallation and model setup.

## What the current results mean

The primary AR model learned normal Hormuz transit behavior using dates before
the disruption and forecast the post-disruption period without using observed
post-treatment controls. The difference between forecast and observation is
reported as a **disruption-associated counterfactual shortfall**.

The repository currently reports a large shortfall and supporting temporal,
spatial, interval, and synthetic-control checks. These checks make the result
more credible, but they do not by themselves prove a causal LNG freight-rate
effect. AIS reporting quality, the broad PortWatch tanker category, possible
concurrent shocks, and the limited number of independent long placebo windows
remain important limitations.

## Current phase and next gate

The PortWatch foundation is complete. The active task is a vessel-data
feasibility gate:

1. obtain a personal Global Fishing Watch token;
2. assemble a sourced roster of at least 30 LNG carriers identified by IMO;
3. obtain a short identity and port-visit sample;
4. score the pre-committed coverage thresholds;
5. proceed to inferred LNG capacity-nautical miles only if the gate passes;
6. otherwise build the documented LNG trade-network scenario simulation.

Until those inputs exist, a vessel-level result is a hypothesis, not an empirical
finding. Spark access remains a parallel optional path and its files must remain.

## Audit and cleanup record

The repository audit on 2026-06-19 found:

- the real Git repository is `lng_freight_thesis/`, not its parent folder;
- the file `../Thesis_Proposal_MA` is a Word document without a `.docx` suffix;
- Spark code, configuration, tests, documentation, and access reports are intact;
- the identical Panama-capacity and mechanism-proxy raw files are intentional
  provenance outputs with different logical names, so both were retained;
- macOS `.DS_Store`, Python `__pycache__`, and pytest cache files were removed;
- user environments, raw snapshots, processed outputs, figures, IDE settings,
  the formal proposal, and all pre-existing uncommitted work were retained;
- the local core suite passed all 124 tests after cleanup.
