# Project Post-Mortem & Zero-Trust Scope Review
**Date:** 2026-06-21 · **Scope:** full `lng_freight_thesis` repository · **Method:** read-only audit of source, tests, processed artifacts, docs, and the original `Thesis_Proposal_MA`. All numbers below were re-read from the committed/processed files, not from memory. The test suite (214 tests) was executed in a clean Linux sandbox and **all passed**.

---

## TASK 1 — Architectural Mapping & Deep Code Audit

### 1.1 High-level structural map

The repository is a disciplined Python package (`src/lngfreight`, ~7.6k LOC) with a thin script layer (`scripts/`, ~7.0k LOC), a no-network test suite (`tests/`, 214 tests), a config-driven data registry, immutable raw data with SHA-256 provenance, and an unusually large `docs/` governance trail. It is **far past a "baseline"** — it is a multi-layer counterfactual event-study pipeline with corroboration and mechanism branches.

**Abstract workflow logic (the spine):**

```
config/sources.yaml  ──►  registry.get_variable(name)  ──►  provider modules (EIA / FRED / PortWatch / WTO / GFW / [Spark dormant])
        │                         │                                  │
   settings.yaml            provenance.jsonl (SHA-256)         data/raw/** (immutable)
        │                                                            │
        ▼                                                            ▼
  specification.py (validates outcome + estimator roles)      clean.py → panel.py → aligned daily panel
        │                                                            │
        ▼                                                            ▼
  validation.py (rolling-origin, leakage-safe folds, cutoff = 2026-02-28 LOCKED)
        │
        ├─► baselines.py  (seasonal-naive, AR-only [PRIMARY], route/energy ARX)
        ├─► inference.py  (observed−counterfactual gap, placebo-in-time)
        ├─► spatial.py    (28-chokepoint spatial placebo + leave-one-out)
        ├─► synthetic.py  (donor synthetic control, Abadie placebo)  ── corroboration only
        ├─► bsts.py       (univariate Bayesian state-space)          ── corroboration only
        ├─► tsfm.py       (Chronos-2 / TimesFM-2.5 / Moirai-2.0)     ── ISOLATED benchmark, weights-gated
        └─► [mechanism branch] gfw → terminal_matching → routes → capacity_miles → vessel_days
                                  → wto_validation → exposure → transmission_chain
        │
        ▼
  scripts/run_all.py  ──►  regenerate artifacts → run tests → diff 94 artifact hashes vs manifest (fails on drift)
        │
        ▼
  reports/*.md + reports/figures/*  (generated, not hand-written)
```

**Directory roles:**

| Path | Role | State |
|---|---|---|
| `src/lngfreight/*.py` (49 modules) | Core package; one concern per module | Healthy, tested |
| `src/lngfreight/sources/` | One adapter per provider over `base.BaseSource` | Healthy; `spark.py` dormant by design |
| `scripts/` (56 scripts) | Runnable, one concern each | Healthy; TSFM scripts isolated |
| `config/` | `sources.yaml` (swap layer), `settings.yaml` (locked spec), 2 corridor YAMLs | `corridor_*.yaml` untracked |
| `data/raw/` | Immutable pulls + `provenance.jsonl` | Healthy |
| `data/processed/` | All numeric outputs (the results live here) | Several modified/untracked |
| `tests/` (35 files) | No-network suite | 214 pass |
| `docs/` (36 docs) | Governance, methodology, audits | Several untracked |
| `reports/` | Generated summaries + figures + 1 .pptx | Healthy |

### 1.2 Mermaid.js dependency & health graph

> **How to view:** copy the fenced ```mermaid``` block below into <https://mermaid.live> (paste on the left, the diagram renders on the right). It also renders inline in this file in any Mermaid-aware Markdown viewer. A standalone copy is saved as `docs/pipeline_health_graph.mermaid`.

```mermaid
flowchart TD
    %% ===== INPUTS =====
    subgraph INPUTS["Data inputs (registry-mediated)"]
        PW["IMF PortWatch<br/>tanker transits + capacity"]:::ok
        EIA["EIA / FRED<br/>Henry Hub, Brent"]:::ok
        WTO["WTO/AXSMarine<br/>LNG outbound index"]:::ok
        GFW["Global Fishing Watch<br/>identity + port visits"]:::ok
        SPARK["Spark25S/30S freight<br/>(proprietary DV)"]:::missing
        AIS["AIS laden ton-miles<br/>(proprietary mechanism)"]:::missing
    end

    REG{{"registry.get_variable()<br/>+ provenance SHA-256"}}:::ok
    PW --> REG
    EIA --> REG
    WTO --> REG
    GFW --> REG
    SPARK -. dormant adapter, status:unavailable .-> REG
    AIS -. not accessible .-> REG

    REG --> CLEAN["clean.py / panel.py<br/>aligned daily panel"]:::ok
    CLEAN --> VAL["validation.py<br/>rolling-origin, cutoff 2026-02-28 LOCKED"]:::ok

    %% ===== PRIMARY =====
    subgraph PRIMARY["Primary estimate (load-bearing)"]
        VAL --> BASE["baselines.py<br/>AR-only PRIMARY"]:::ok
        BASE --> CF["inference.py<br/>observed - counterfactual gap"]:::ok
        CF --> RESULT["AR-only loss = 5,121 transits<br/>94-day band 3,934-5,722"]:::ok
    end

    %% ===== CORROBORATION =====
    subgraph CORROB["Corroboration layers (not the anchor)"]
        CF --> PT["placebo-in-time<br/>sep 3.9x"]:::ok
        CF --> SP["spatial placebo<br/>28 chokepoints, sep 5.0x"]:::ok
        CF --> SC["synthetic control<br/>ratio 4.77, 3.87x placebo"]:::ok
        CF --> BSTS["BSTS univariate<br/>median 4,982"]:::ok
    end

    %% ===== BENCHMARK (GATED) =====
    subgraph BENCH["TSFM benchmark (isolated, excluded from run_all)"]
        VAL -. pre-cutoff only .-> TSFM["tsfm.py adapters"]:::gated
        WEIGHTS["HF weights + .venv-bench / .venv-timesfm<br/>macOS-only, not in repo"]:::gated
        WEIGHTS -. required .-> TSFM
        TSFM --> ADM["admission test<br/>Chronos-2 +2.4% transits"]:::gated
    end

    %% ===== MECHANISM =====
    subgraph MECH["Open-data LNG mechanism (descriptive)"]
        GFW --> TM["terminal_matching.py"]:::ok
        TM --> RT["routes.py (searoute)"]:::ok
        RT --> CM["capacity_miles.py<br/>948->726 voyages, +10.2% m3-nm/voyage"]:::ok
        CM --> VD["vessel_days.py"]:::ok
        CM --> WV["wto_validation.py<br/>-98.6% index agreement"]:::ok
        WV --> EXP["exposure.py<br/>importer/basin"]:::warn
    end

    %% ===== EXPLORATORY / UNCOMMITTED =====
    subgraph EXPL["Newest exploratory branch (UNCOMMITTED)"]
        VAL -. .-> CTP["corridor_transmission.py<br/>+ corridor_panel / inference / admission"]:::uncommitted
        CTP --> TC["transmission_chain.py<br/>5-layer cascade summary"]:::uncommitted
        SC -.-> DON["donor_screen.py<br/>contamination stress"]:::uncommitted
    end

    %% ===== UNUSED FALLBACK =====
    SIM["synthetic.py / run_basin_interval_simulation.py<br/>Phase-3B trade-network sim"]:::dormant
    CLEAN -. built but UNUSED fallback .-> SIM

    %% ===== AGGREGATION =====
    RESULT --> RUNALL["run_all.py<br/>diff 94 hashes vs manifest"]:::warn
    PT --> RUNALL
    SC --> RUNALL
    CM --> RUNALL
    RUNALL --> REP["reports/*.md + figures"]:::ok

    classDef ok fill:#d4edda,stroke:#28a745,color:#155724;
    classDef warn fill:#fff3cd,stroke:#ffc107,color:#856404;
    classDef gated fill:#cce5ff,stroke:#007bff,color:#004085;
    classDef dormant fill:#e2e3e5,stroke:#6c757d,color:#383d41;
    classDef uncommitted fill:#f8d7da,stroke:#dc3545,color:#721c24;
    classDef missing fill:#f5c6cb,stroke:#dc3545,color:#491217,stroke-dasharray: 5 5;
```

**Legend.** Green = built, tested, connected. Yellow = built but carries a stated caveat or process risk. Blue = gated benchmark (needs external weights/venvs not in the repo; excluded from `run_all`). Grey = built but deliberately unused fallback. Red solid = recent work **not yet committed to git**. Red dashed = proprietary input the pipeline is designed around but cannot access.

**Broken branches / empty boxes / incomplete plumbing (explicitly isolated):**
- **`SPARK` / `AIS` (red dashed):** the original proposal's dependent variable and primary mechanism. Not connected — by design the registry leaves dormant adapters in place. This is the single largest "missing input," but it is disconnected *cleanly*, not broken.
- **`SIM` Phase-3B (grey):** the trade-network simulation is fully built but **never wired into the reported results** — a parked fallback, not dead code, but currently an unconsumed box.
- **`EXPL` branch (red solid):** `corridor_transmission`, `transmission_chain`, `donor_screen`, `basin_coverage`, `corridor_*` and their 7 tests/7 docs are **untracked in git**. They run and are tested, but they are outside the committed reproducibility manifest — the most real "plumbing not fully connected" finding.
- **`EXP` exposure (yellow):** country-level importer exposure is **suppressed** because post-period voyage support drops to ~2 voyages; only basin aggregates survive. The box exists but its country-level output is intentionally empty.
- **`RUNALL` (yellow):** `README.md` still says it diffs **87** hashes; the committed manifest now holds **94**. Doc drift, not a logic break.

### 1.3 Deep-dive implementation audit (functional verification)

I scanned all of `src/` and `scripts/` for stubs, half-written functions, `TODO/FIXME/HACK`, bare `pass`, and `...` placeholders. **No genuine stubs were found** — every `NotImplementedError` is a correct abstract-base-class contract (`sources/base.py`, `sources/__init__.py`, `tsfm.TSFMAdapter`, and `registry` for unknown variables). The grep hits were Python type hints (`tuple[str, ...]`), not ellipsis placeholders.

Functional spot-checks of the load-bearing code:
- **`baselines.arx_forecast`** — recursive AR correctly feeds *prior predictions* (not held-out observed values) into in-window lags, so the validation horizon is leakage-safe. Ridge fit uses an augmented least-squares system (numerically stable for the millions-scale capacity target). Input guards on lags/alpha/columns are present. **Correct.**
- **`inference.placebo_time_folds` / `fixed_train_post_fold`** — each placebo fold trains strictly before its own start and tests strictly before the real cutoff; fixed-train folds assert geometry (`train_end < cutoff <= post_start`). **Leakage-safe.**
- **`corridor_transmission`** (newest) — preserves the same expanding-history, univariate, no-cross-corridor-leakage discipline; basin layer is point-only and never sums corridors. **Consistent with the locked discipline.**
- **Numbers reconcile to source.** Every headline figure in the report `.md` files was re-derived from `data/processed/*.csv`: AR-only transit loss 5,121.3 and capacity 206.9M (`counterfactual_post_treatment_summary.csv`); synthetic-control pre-RMSPE 0.175 / ratio 4.77 / 3.87× placebo (`synthetic_control_summary.csv`); capacity-miles 948→726 voyages and mean m³-nm/voyage 662.7M→730.3M = +10.2% (`inferred_capacity_nautical_miles_period_summary.csv`); WTO index 101.78→1.38 = −98.6% and GFW departures 171→12 = −93.0% (`gulf_departure_wto_validation_summary.json`). **No discrepancy between prose and data.**

**Items needing attention (none block the primary result):**

1. **Uncommitted exploratory branch (process risk, Medium).** ~9 source modules, 7 test files, 9 docs, and many processed CSVs are untracked/modified. They are tested and run, but they sit outside the committed manifest, so the reproducibility guarantee currently covers an older tree than what's on disk. *Fix:* review and commit (or stash) the corridor/transmission/donor work; regenerate and re-freeze the manifest.
2. **README "87 hashes" vs 94 in the manifest (Low).** Stale count after the manifest grew. *Fix:* one-line README edit.
3. **TSFM provenance is host-bound (Low–Medium, already disclosed).** `tsfm_run_manifest.json` records macOS-arm64 venvs (`.venv-bench` torch 2.4.1; `.venv-timesfm` torch 2.12.1, `timesfm` package 2.0.1). These cannot be reproduced in a fresh/Linux environment, and the bundled `.venv*` folders have macOS symlinks (their `python` is broken off-host). Because the TSFM layer is isolated and excluded from `run_all`, this does **not** affect the core result — but the benchmark numbers are only as reproducible as that one machine. *Fix:* keep the lockfiles as the citable record and state in-thesis that TSFM is a one-host robustness check.
4. **Capacity outcome is window- and model-sensitive (Low, already disclosed).** Its counterfactual covers 79 days vs 94 for transits and moves −5.2% under Chronos-2. Correctly demoted to "directional secondary." No change needed beyond keeping that framing.

---

## TASK 2 — Academic Scope, Results, and Future Pathways

### 2.1 Current empirical results

**Headline (working primary, AR-only interrupted-time-series counterfactual on PortWatch tanker transits through Hormuz):**
- Observed post-window transits collapse to **245** vs an AR-only counterfactual of **5,366** over 94 days → **cumulative shortfall ≈ 5,121 transits (~54.5/day)**, i.e. the strait runs at roughly **4.5% of expected throughput**.
- **Honest 94-day interval: 3,934–5,722 transits** (placebo-window recalibrated; the short-fold band 4,758–5,434 is a lower bound; circular-block cross-check 4,649–5,516). All exclude zero by a wide margin.
- **Robust across treatment-window definitions** (kinetic trigger / closure declaration / force majeure / donut): mean daily loss stays ~54–55/day with the cutoff fixed at 2026-02-28.

**Corroboration (consistent, not independent identification):**
- **Placebo-in-time:** actual loss separates from the placebo p95 by **~3.9×**; p-value floor-censored at 0.027 (small-N design floor — report separation, not p).
- **Spatial placebo (28 chokepoints):** Hormuz first by raw *and* normalized loss; **95.5% of expected transits lost, ~5.0× the donor p95**; leave-one-out shows no single donor drives it (dropping Malacca *strengthens* it).
- **Synthetic control (22 clean donors):** post/pre RMSPE ratio **4.77 vs placebo p95 1.23 (3.87×)**, Abadie p≈0.043, credible pre-fit (RMSPE 0.175, 8.7 effective donors).
- **BSTS univariate:** posterior-median shortfall **4,982 [3,348, 6,711]**, P(>0)=1.0 — agrees in direction and magnitude.
- **TSFM cross-check (isolated):** Chronos-2 changes the transit shortfall by only **+2.4%** (capacity −5.2%); a stronger, better-calibrated forecaster does not overturn it. Explicitly *not* causal evidence.

**Mechanism (open-data, descriptive — the recovered, weakened ton-mile story):**
- Independent **WTO/AXSMarine LNG outbound index falls −98.6%**; GFW-inferred Gulf LNG departure calls fall **−93.0%** — cross-source directional agreement with no calibration. *This is the single strongest result and should anchor the mechanism narrative.*
- Among retained voyages, **routed voyages −23.4%** while **mean nominal capacity-distance per voyage +10.2%** (BCa 95% CI [+4.4%, +17.0%]). A Kitagawa/Oaxaca decomposition shows this is **~98% route-composition shift, not route elongation**.
- **Honest reading: contraction + substitution, not an aggregate ton-mile multiplier.** Alternative corridors rise (Cape of Good Hope +46%, Yucatan +23%, Panama +21%).

**What the results are NOT (the project states this itself):** not a causal ATT, not an LNG-specific freight rate, not observed cargo ton-miles, not sailed AIS tracks. PortWatch's "tanker" class is not LNG-specific; conflict-zone AIS dark activity biases the naive estimate *away from zero*, so the throughput drop is an **upper bound**.

### 2.2 The scope pivot

**What changed.** The original proposal (`Thesis_Proposal_MA`) is titled *"Causal Identification of the Ton-Mile Multiplier Effect"* with **daily LNG spot freight (Spark25S/30S)** as the dependent variable and **AIS-derived laden ton-miles** as the primary mechanism, estimated as a **causal ATT (θ)** via debiased dose-response + donor synthetic control. Both Spark and AIS are **proprietary and never obtained** (Bloomberg access at TUM unresolved; no AIS vendor). On 2026-06-16 the supervisor side (Z. Wang relaying Prof. Li) green-lit proceeding on a fallback dataset.

**The pivot (staged in `PENDING_ESTIMAND_REALIGNMENT_DRAFT.md`, reconciled item-by-item in `ESTIMAND_PROPOSAL_RECONCILIATION.md`):**
- **Outcome:** LNG spot freight → **Hormuz tanker throughput** (PortWatch). This is honestly labelled a **change of estimand, not a proxy swap** — throughput is a different, adjacent outcome on the cause/route side, not a stand-in for a price.
- **Claim strength:** causal ATT → **"disruption-associated counterfactual shortfall"** (association, not identified effect).
- **Mechanism:** observed AIS laden ton-miles → **inferred nominal capacity-nautical-miles** from GFW terminal sequences (weaker, free).
- **Sub-Q2 (inter-basin regime switch):** not testable without the freight series → **demoted to optional**, reactivated only if Spark/Bloomberg arrives.
- **Sub-Q4 (modern TSFM):** preserved as a benchmark gate with updated 2025 models (Chronos-2 / TimesFM-2.5 / Moirai-2.0).

**Why the pivot is necessary — and it is, but be precise about the reason.** The driver is **data access, not model performance or a data-driven failure.** The models did not "fail"; the proprietary inputs the original estimand requires were never available, and the supervisor authorized proceeding on free data rather than waiting on an open-ended external dependency. The intellectual core the proposal actually claims as its contribution — the **identification *protocol*** (falsification cascade, leakage-safe counterfactual, placebo-in-time/space, donor synthetic control as corroboration-not-anchor, prediction≠identification discipline, multiplicity ledger) — is **preserved intact** and simply runs on an observable target. This framing was anticipated in the proposal's own fallback branch, so the pivot is a *planned degradation*, not an improvised rescue.

**Governance status (important):** the realignment is **drafted and decision-ready but NOT yet approved.** The formal proposal is unchanged and remains in force. Until Prof. Li signs off on (1) the outcome-variable change, (2) the "counterfactual shortfall" (no-ATT) language, (3) demoting freight/inter-basin to optional, and (4) the updated TSFM roster, all causal/ATT language stays out and the work is reported as a working pipeline.

### 2.3 Future pathways

| Pathway | What it is | Pros | Cons | Required next steps |
|---|---|---|---|---|
| **A. Lock the throughput thesis (recommended default)** | Finalize the current PortWatch counterfactual-shortfall study + open-data mechanism as the thesis; freight/AIS stay optional. | Runs end-to-end on data in hand; rigor already built; risk fully bounded; defensible *today*. | Weaker claim (association, not ATT); outcome is "adjacent" to the proposal's freight DV; needs supervisor sign-off on estimand. | Get Prof. Li approval; transfer staged language into the proposal; commit the exploratory branch; freeze manifest; write empirical chapters. |
| **B. Throughput thesis + free Spark trial upside** | Pathway A, plus run the already-built `verify_spark_target.py` against a free Spark OAuth trial; if the window is covered, add freight as a *second* DV by flipping `config/sources.yaml`. | Could recover the original freight DV for free with zero redesign; pure upside. | Trial likely truncated/insufficient for the 2022–2026 window; non-blocking but uncertain. | Create free Spark client; run the probe; record coverage in `TARGET_ACCESS_STATUS.md`; only then promote freight. |
| **C. Full original proposal (Bloomberg/AIS)** | Wait for/obtain TUM Bloomberg + an AIS vendor; execute the dose-response ATT + true ton-mile mechanism. | Delivers the strongest, original causal claim; highest scholarly value. | Open-ended external dependency that may never resolve; the exact risk the pivot was designed to remove; schedule risk. | Confirm Bloomberg access date; secure AIS license; only switch the critical path back if access is *guaranteed* within the timeline. |
| **D. Methodology-forward framing** | Foreground the *transferable identification protocol* (Suez/Bab-el-Mandeb/Panama/Malacca reuse) as the headline contribution; Hormuz is the worked example. | Most durable contribution; survives any data outcome; matches the proposal's stated "most durable" claim. | Less of a single empirical "number"; needs a clear methods narrative. | Frame the cascade as the contribution; package `transmission_chain` cleanly; demonstrate portability conceptually. |

---

## TASK 3 — Zero-Trust Hallucination & Fabrication Audit

I actively hunted for invented libraries, fabricated data, synthetic metrics dressed as real, and assumptions substituted for evidence. **The headline finding is reassuring:** the suspect items checked out as real, and the reported numbers trace to the processed data. The genuine risks are about *provenance and process*, not fabricated content.

**Verified clean (do not attack — these passed zero-trust):**
- **Foundation-model releases are real, and the code's descriptions are accurate.** Web verification confirms **Chronos-2** (amazon/chronos-2, released 2025-10-20, encoder-only, 120M params — matches the docstring exactly) and **TimesFM 2.5** (google/timesfm-2.5-200m-pytorch, 200M params, quantile head — matches). These are *not* hallucinated version numbers. The `chronos-forecasting`, `timesfm`, `uni2ts`, and `searoute==1.6.0` libraries all exist (`searoute` installed cleanly in the sandbox).
- **Reported metrics are faithful to the artifacts.** Every spot-checked headline number in the `.md` summaries matches the source CSV/JSON to the decimal (see Task 1.3). The results are generated by scripts, not typed by hand.
- **Leakage discipline is real, not claimed.** Cutoff locked at 2026-02-28; training strictly pre-cutoff; placebo folds and recursive AR verified leakage-safe in code.
- **Caveats are stated, not smoothed.** PortWatch tanker≠LNG, AIS-dark upper-bound bias, capacity model-sensitivity, route shift being composition (not elongation), p-value floor-censoring — all disclosed by the project itself.

**Flagged risks:**

| # | Severity | Risk | Evidence | Required fix |
|---|---|---|---|---|
| 1 | **High** | **Causal language could outrun the design if the pivot ships unreviewed.** The repo is rigorous about saying "association, not ATT," but the *approved* proposal still says "Causal Identification." If chapters are written before Prof. Li signs the realignment, the thesis title/claims and the actual estimand diverge — an integrity exposure at submission, not a code bug. | `ESTIMAND_PROPOSAL_RECONCILIATION.md` (pending), `FALLBACK_STRATEGY.md` ("pending Prof. Li confirmation"), proposal unchanged. | Do not write any ATT/causal-effect language until sign-off; keep "disruption-associated counterfactual shortfall" everywhere; get the approval in writing. |
| 2 | **Medium** | **Reproducibility manifest does not cover the newest work.** A large exploratory branch (corridor transmission, transmission chain, donor stress, basin coverage) is untracked/modified in git and outside the committed 94-hash manifest. Results in `transmission_chain_summary.md` are real but not yet under the drift-detection guarantee. | `git status` shows ~9 untracked modules + 7 tests + 9 docs + many processed CSVs; manifest modified, uncommitted. | Commit (or stash) the branch; rerun `run_all.py`; re-freeze the manifest so every reported figure is hash-covered. |
| 3 | **Medium** | **TSFM benchmark is reproducible on exactly one machine.** The admission/counterfactual CSVs depend on macOS-arm64 venvs not in the repo; bundled `.venv*` have host-specific (broken off-host) symlinks. Numbers can't be independently regenerated elsewhere. Not load-bearing (isolated from `run_all`), but it is the least-verifiable layer. | `tsfm_run_manifest.json` (platform macOS-arm64, torch 2.12.1/2.4.1, timesfm 2.0.1); `.venv/bin/python` broken in Linux sandbox. | Treat TSFM as a single-host robustness check in the text; rely on the lockfiles as the citable record; never let a TSFM number carry a conclusion. |
| 4 | **Low** | **Doc drift.** README claims `run_all.py` diffs "87 artifact hashes"; the manifest holds 94. Harmless but the kind of small inconsistency a zero-trust reader notices. | `README.md` vs `reproducibility_manifest.json` (`artifact_sha256` = 94). | One-line README correction; consider auto-generating the count. |
| 5 | **Low** | **Capacity outcome precision could be over-read.** Capacity shortfall (206.9M) has a 79-day window vs 94 for transits and a −5.2% Chronos-2 swing. Already demoted, but a casual reader of the table might quote its magnitude. | `counterfactual_post_treatment_summary.csv` (n_days 79 vs 94); `ADVANCED_ML_RECONSIDERATION.md`. | Keep "directional secondary, magnitude not load-bearing" label adjacent to every capacity figure. |
| 6 | **Low** | **`searoute` distances are modeled, not sailed.** Capacity-nautical-miles use a bundled route graph, correctly labelled "nominal," but the word "ton-mile" near these figures invites misreading as observed cargo ton-miles. | `routes.py` (searoute), `capacity_miles.py`, mechanism summary boundary note. | Keep "nominal / inferred / not observed cargo ton-miles" qualifier on every such figure (already mostly done). |

**Net verdict.** No fabricated libraries, no invented data, no phantom metrics. The mathematically substantive code (AR recursion, ridge LS, placebo geometry, synthetic control, Oaxaca decomposition) is sound and faithfully reported. The real exposure is **governance and reproducibility hygiene** — an unapproved estimand pivot and a newest branch sitting outside the committed manifest — both fixable before writing, neither a sign of hallucinated results.
