# LNG freight disruption thesis pipeline

This repository contains the reproducible analysis code and frozen evidence
used to study the 2026 Strait of Hormuz disruption. The working primary outcome
is daily IMF PortWatch tanker transit count. The main estimand is the
**disruption-associated counterfactual shortfall** over a locked 130-day window,
estimated with a transparent pre-treatment AR model and checked with temporal,
spatial, interval, synthetic-control, Bayesian, and admitted Chronos-2
robustness layers.

The design is explicitly non-causal. It measures a counterfactual shortfall in
an AIS-based chokepoint observation, not actual LNG cargo lost, welfare loss,
freight-price incidence, or a structural treatment effect. LNG-specific public
sources support a separate descriptive mechanism layer.

## Repository status and release boundary

The codebase is intended for thesis assessment and reproducibility. A public
software licence has not yet been selected, so no general reuse permission
should be inferred from the presence of source code.

The default pipeline uses public or redistributable inputs. Proprietary or
provenance-limited Bloomberg, Fearnleys, ClearLynx, Spark, Platts, Kpler, and
similar inputs are not required and must not be included in a public release.
The optional Bloomberg branch is disabled by default and remains local-only.

The active LaTeX manuscript and literature review are maintained outside this
repository in `Bachelor Thesis Final/` within the clean thesis workspace. Its
machine-specific parent path is deliberately not part of this portable repository
contract. Project-management notes, personal defence material, credentials,
virtual environments, raw licensed inputs, and historical backups are outside the
public code-release boundary.

## Research design at a glance

| Layer | Quantity | Role and boundary |
|---|---|---|
| Working primary | PortWatch Hormuz tanker transit count | AIS-derived aggregate chokepoint throughput; not LNG-specific cargo |
| Capacity robustness | PortWatch `capacity_tanker` | AIS-derived tanker transit-volume/capacity proxy in metric tonnes; not observed loaded cargo |
| Primary counterfactual | AR(1,7), trained strictly before 2026-02-28 | Transparent, leakage-controlled benchmark |
| Optional model check | Admitted matched-horizon Chronos-2 | Robustness only; never replaces the primary estimator |
| LNG mechanism | GFW terminal sequences, WTO/AXSMarine index, modeled sea routes | Inferred and modeled evidence, kept separate from identification |
| Network adaptation | Monthly by-origin customs/source panels | Descriptive recomposition with mixed source-native measurement bases |

The 130-day PortWatch estimation window and the 94-day LNG mechanism window are
different by design and must not be pooled or described as one sample.

## Data sources and access

| Source | Contribution | Access/key | Important limitation |
|---|---|---|---|
| IMF PortWatch | Hormuz and donor-chokepoint transit series | Public; no key for the frozen snapshots | AIS coverage and provider processing; aggregate, not vessel-level ground truth |
| EIA | Henry Hub and Brent covariates | Free API key for refetching | Energy context, not LNG freight |
| FRED | Independent energy-series cross-check | Free API key for refetching | Same boundary as EIA |
| WTO/AXSMarine Hormuz tracker | LNG-only outbound shipment index | Public frozen CSV | Index, not physical tonnage or freight rate |
| Global Fishing Watch | Terminal calls and voyage-sequence evidence | Token needed only to refetch | Inferred calls; no laden-state or continuous-track guarantee |
| GEM, Natural Earth, searoute | Terminals, boundaries, modeled routes | Public/local package assets | Routes are modeled shortest-sea paths, not observed sailed tracks |
| Customs/Eurostat/e-Stat/KOSIS/Comtrade | Monthly importer-origin composition | Source-specific; some refetches need free keys | Mixed mass, volume, and value bases; reporting lags and thin post samples |

Exact variables, licences, frozen-vintage roles, and unavailable proprietary
targets are documented in `config/sources.yaml`, `docs/DATA_SOURCES.md`, and
`docs/DATA_SOURCE_DEEP_DIVE.md`. Do not replace an unavailable target silently
with a convenient proxy.

## Installation

The core package supports Python 3.10 or newer. `pyproject.toml` and
`requirements.txt` declare the direct compatibility constraints;
`requirements.txt` also includes pytest for local verification. A normal
development install lets pip resolve the transitive versions within those
constraints:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -e .
```

For an exact reconstruction of the canonical core/test environment, use the
complete transitive lock and install the local package without re-resolving its
dependencies:

```bash
python3.14 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-core.lock.txt
python -m pip install --no-deps -e .
```

`requirements-core.lock.txt` is locked and verified for Python 3.14.4 on macOS
arm64 (`macosx-26.0-arm64`). Other supported Python versions and platforms may
require a fresh resolution from the direct constraints rather than this exact
platform lock.

The transparent baseline and admitted inference code use NumPy/Pandas directly;
SciPy, statsmodels, and scikit-learn are not core dependencies. `networkx` is a
direct dependency of the reallocation module and is therefore declared in both
the package metadata and core requirements.

The self-contained interactive TSFM benchmark figure is optional. Install its
declared extra before running that script:

```bash
python -m pip install -e '.[interactive]'
python scripts/make_tsfm_benchmark_interactive.py
```

Optional real-weight foundation-model checks use separate Python 3.11
environments and exact reproducibility lockfiles:

- `requirements-benchmark.lock.txt` for Chronos-2/Moirai;
- `requirements-timesfm.lock.txt` for TimesFM;
- `data/processed/tsfm_run_manifest.json` for model revisions and run identity.

The main workflow expects `.venv-bench/bin/python` when regenerating the
admitted Chronos-2 check. The core test suite does not require those weights.

## Credentials and frozen inputs

For source refetches, copy the placeholder template and add only the keys you
need:

```bash
cp .env.example .env
```

Never commit `.env`. Frozen-input verification and most tests run offline. A
release that omits raw snapshots must provide them through a separate cleared
artifact bundle; otherwise the full end-to-end workflow cannot be reproduced
from source alone.

## Validation and tests

Run the no-network test suite from the repository root:

```bash
PYTHONHASHSEED=0 python -m pytest -q
```

Useful bounded checks include:

```bash
python scripts/freeze_reproducibility.py --check
python scripts/audit_provenance.py
python scripts/render_thesis_figures.py --check
```

Chronological splits are mandatory. The primary AR path uses no post-treatment
target or contemporaneous post-treatment covariate. Missingness, donor
contamination, reporting bias, temporal leakage, overlapping placebo windows,
small reference sets, and model-selection sensitivity are treated as explicit
limitations rather than hidden by a passing test suite.

## Reproduce the complete pipeline

From a correctly provisioned repository containing the frozen inputs and the
isolated Chronos-2 environment:

```bash
PYTHONHASHSEED=0 python scripts/run_all.py
```

`run_all.py`:

1. verifies frozen inputs before computation;
2. rebuilds and audits the aligned panel;
3. runs chronological validation and all admitted model/inference layers;
4. rebuilds the LNG mechanism and network evidence;
5. renders the numbered technical figure catalog and result summaries;
6. runs the full tests;
7. compares regenerated artifacts with the frozen allowlist without rewriting
   the reference manifest; and
8. writes `reports/reproducibility_run_transcript.txt`.

The optional proprietary-data branch runs only when both
`ENABLE_BLOOMBERG_LAYER=1` and `BLOOMBERG_EXPORT_DIR` are supplied. It is not
part of the public or default thesis pipeline.

## Reproduce the numbered technical figure catalog

The renderer currently preserves 13 numbered technical figures from the prior
manuscript mapping. They remain reproducible evidence assets, but inclusion and
numbering in the clean manuscript must be decided during reconstruction.
Rendering from existing processed artifacts does not refit models or download
data:

```bash
python scripts/render_thesis_figures.py
python scripts/render_thesis_figures.py --list
python scripts/render_thesis_figures.py --check
python scripts/render_thesis_figures.py --figure 6.1
python scripts/render_thesis_figures.py --figure 8.2 --figure 8.3
```

Canonical renderer settings are:

| Setting | Value |
|---|---|
| Python | 3.14.4 in the current macOS verification environment |
| Matplotlib | 3.11.0 |
| Backend | `Agg` through the public renderer |
| Hash seed | `PYTHONHASHSEED=0` |
| Matplotlib cache | `/tmp/lngfreight-matplotlib` |
| Primary font preference | P052/URW Palladio/Palatino/TeX Gyre Pagella; DejaVu Serif fallback |
| Vector font mode | TrueType (`pdf.fonttype=42`) |
| PNG previews | 300 dpi |

Outputs are paired PDFs and PNG previews in `reports/figures/`. PDF creation
and modification timestamps are removed. Font availability can still change
glyph metrics and therefore hashes; the release verification transcript must
record the resolved font and environment before figure hashes are treated as
canonical.

## Main outputs

| Path | Purpose |
|---|---|
| `reports/run_output.md` | Inspectable primary and uncertainty results |
| `reports/current_results_summary.md` | Working thesis result table |
| `reports/mechanism_results_summary.md` | LNG mechanism evidence summary |
| `reports/network_rewiring_summary.md` | Importer/network results and scenario diagnostics |
| `reports/reproducibility_run_transcript.txt` | Complete end-to-end console record |
| `data/processed/run_spec_comparison.csv` | Admitted estimator comparison |
| `data/processed/reproducibility_manifest.json` | Frozen allowlisted output identities |
| `data/processed/tsfm_admission_test.csv` | Model/outcome admission decisions |
| `data/processed/tsfm_run_manifest.json` | Isolated model and environment provenance |
| `data/raw/provenance.jsonl` | Append-only source/access provenance ledger |

Generated output is evidence only when its source inputs, command, environment,
and hash are recorded. A regenerated file must not be accepted merely because
its filename matches an older artifact.

## Repository layout

| Path | Purpose |
|---|---|
| `config/settings.yaml` | Locked windows, outcomes, methods, seeds, and thresholds |
| `config/sources.yaml` | Data registry, access status, units, licences, and checksums |
| `src/lngfreight/` | Reusable data, validation, model, inference, and audit code |
| `scripts/` | Acquisition, build, model, audit, freeze, and rendering entry points |
| `experiments/` | Robustness benchmarks and descriptive network-adaptation experiments |
| `tests/` | No-network unit and integration tests |
| `data/processed/` | Frozen model inputs, outputs, diagnostics, and manifests |
| `reports/` | Human-readable results, transcripts, and figures |
| `docs/` | Method, source, provenance, and limitation documentation |
| `references/` | Bibliographic seed data |

## Reproducibility contract

- Every external analysis input must pass through the source/artifact registry.
- Frozen source bytes and normalized snapshots have separate provenance roles.
- Pre-treatment selection and chronological evaluation are enforced in code.
- The primary estimator remains AR-only; complex models are robustness checks.
- A real TSFM run requires an admitted model/outcome record before execution.
- The verification command compares against, but does not casually refresh,
  the frozen manifest.
- News- or AIS-derived observations are measurement systems, not ground truth.
- No causal interpretation is permitted without a causal identification design.

See `docs/PROVENANCE_CONTRACT.md`, `docs/INFERENCE_NOTES.md`,
`docs/SUTVA_CONTAMINATION_AUDIT.md`, and
`docs/REPRODUCIBILITY_AND_LEAKAGE_AUDIT.md` for the detailed audit trail.

## Known limitations

- The original Spark25S/30S freight-price target is unavailable in the default
  public-data branch.
- PortWatch does not identify LNG cargo, laden state, vessel identity, or
  per-voyage ton-miles.
- LNG route and capacity-distance quantities are inferred/modelled.
- Customs panels use different native units and short post-event windows.
- AIS darkness and provider gap filling may be treatment-correlated.
- Donor-placebo and block-reference sets have finite inferential resolution.
- The optional Chronos-2 result is host-bound and subordinate to the primary.
- Full raw-source response evidence was not retained for every historical pull;
  those gaps are disclosed rather than reconstructed.

## Citation and responsible use

If this repository accompanies the thesis, cite the thesis and the original
data/method providers rather than treating this code as the primary scholarly
source. Respect each provider's terms. Do not redistribute restricted inputs,
checksums that disclose private source identity, credentials, or derived
licensed charts. Do not describe scenario outputs as forecasts, classifications
as causal effects, or AIS observations as complete physical ground truth.
