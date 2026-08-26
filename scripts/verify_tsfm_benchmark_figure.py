"""Independent checks on the numbers plotted by make_tsfm_benchmark_interactive.py.

Every check recomputes from the per-fold score files and compares against the
pre-aggregated summary CSVs. A failure means either the figure or the on-disk
summaries are wrong; it does not say which, so both are printed.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"

TOL = 1e-9
failures: list[str] = []
notes: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f"  {detail}" if detail else ""))
    if not ok:
        failures.append(f"{name}: {detail}")


tsfm = pd.read_csv(PROCESSED / "tsfm_benchmark_scores.csv")
base = pd.read_csv(PROCESSED / "baseline_scores.csv")
tsfm_sum = pd.read_csv(PROCESSED / "tsfm_benchmark_summary.csv")
base_sum = pd.read_csv(PROCESSED / "baseline_summary.csv")
ar_int = pd.read_csv(PROCESSED / "ar_interval_scores.csv")
adm = pd.read_csv(PROCESSED / "tsfm_admission_test.csv")

# 1. No fold silently dropped: every model scores the same fold set.
fold_sets = pd.concat([tsfm[["model", "target", "fold"]], base[["model", "target", "fold"]]])
counts = fold_sets.groupby(["model", "target"]).fold.nunique()
check(
    "every model-target scores the same number of folds",
    counts.nunique() == 1,
    f"fold counts = {sorted(counts.unique())}",
)

# 2. Fold windows identical across families -- otherwise MASE is not comparable.
kt = tsfm[["fold", "target", "test_start", "test_end", "n_scored"]].drop_duplicates()
kb = base[["fold", "target", "test_start", "test_end", "n_scored"]].drop_duplicates()
merged = kt.merge(kb, on=["fold", "target"], suffixes=("_t", "_b"), how="outer", indicator=True)
aligned = (
    (merged._merge == "both").all()
    and (merged.test_start_t == merged.test_start_b).all()
    and (merged.test_end_t == merged.test_end_b).all()
    and (merged.n_scored_t == merged.n_scored_b).all()
)
check("TSFM and baseline fold windows are identical", aligned)

# 3. Constant scoring horizon.
horizons = set(tsfm.n_scored) | set(base.n_scored)
check("scoring horizon is constant across folds", len(horizons) == 1, f"n_scored = {horizons}")

# 4. Recomputed means reproduce the summary files.
r = tsfm.groupby(["model", "target"]).mase.mean().rename("recomputed").reset_index()
m = tsfm_sum.merge(r, on=["model", "target"])
check(
    "tsfm_benchmark_summary mase_mean reproduces from per-fold scores",
    (m.mase_mean - m.recomputed).abs().max() < TOL,
    f"max |delta| = {(m.mase_mean - m.recomputed).abs().max():.2e}",
)
rb = base.groupby(["model", "target"]).mase.mean().rename("recomputed").reset_index()
mb = base_sum.merge(rb, on=["model", "target"])
check(
    "baseline_summary mase_mean reproduces from per-fold scores",
    (mb.mase_mean - mb.recomputed).abs().max() < TOL,
    f"max |delta| = {(mb.mase_mean - mb.recomputed).abs().max():.2e}",
)

# 5. Coverage nominal levels are not pooled across incomparable levels.
nom = tsfm.groupby("model").nominal_coverage.nunique()
check(
    "each model reports a single nominal coverage level",
    (nom == 1).all(),
    f"levels: {tsfm.groupby('model').nominal_coverage.first().to_dict()}",
)
levels = sorted(tsfm.nominal_coverage.unique())
if len(levels) > 1:
    notes.append(
        f"nominal coverage differs across models ({levels}); panel C must be read "
        "against the diagonal, never as a single pooled coverage ranking"
    )

# 6. Conformal AR intervals cover only a fold subset -- confirm, do not assume.
ar_folds, all_folds = set(ar_int.fold), set(tsfm.fold)
check(
    "AR conformal interval folds are a subset of the benchmark folds",
    ar_folds <= all_folds,
    f"{len(ar_folds)} of {len(all_folds)} folds (calibration warm-up excluded)",
)

# 7. Does the frozen admission test still reconcile with the current scores?
ar_now = base[base.model == "ar_lag1_7"].groupby("target").mase.mean()
tsfm_now = tsfm.groupby(["model", "target"]).mase.mean()
stale = []
for _, row in adm.iterrows():
    key = (row.model, row.target)
    if key not in tsfm_now.index or row.target not in ar_now.index:
        continue
    if abs(row.cand_mase_mean - tsfm_now[key]) > 1e-6:
        stale.append(
            f"{row.model}/{row.target}: admission cand {row.cand_mase_mean:.4f} "
            f"vs current {tsfm_now[key]:.4f}"
        )
    if abs(row.ar_mase_mean - ar_now[row.target]) > 1e-6:
        stale.append(
            f"AR/{row.target}: admission {row.ar_mase_mean:.4f} "
            f"vs current {ar_now[row.target]:.4f}"
        )
check(
    "tsfm_admission_test.csv reconciles with current per-fold scores",
    not stale,
    "; ".join(sorted(set(stale))[:4]) + (" ..." if len(set(stale)) > 4 else ""),
)

# 8. Re-derive the admission verdicts from current data.
print("\nAdmission test recomputed from current scores (AR-only reference):")
cov_err = (
    tsfm.assign(err=tsfm.empirical_coverage - tsfm.nominal_coverage)
    .groupby(["model", "target"])
    .err.mean()
)
ar_cov_err = (
    ar_int.assign(err=ar_int.empirical_coverage - ar_int.nominal_coverage)
    .groupby("target")
    .err.mean()
)
for (model, target), mase in tsfm_now.items():
    beats = mase < ar_now[target]
    keeps = abs(cov_err[(model, target)]) <= abs(ar_cov_err.get(target, float("inf")))
    print(
        f"  {model:<14} {target:<24} MASE {mase:.4f} vs AR {ar_now[target]:.4f}"
        f"  beats={str(beats):<5} cov_err {cov_err[(model, target)]:+.4f}"
        f" vs AR {ar_cov_err.get(target, float('nan')):+.4f}  admitted={beats and keeps}"
    )

# 9. Nothing plotted falls outside its axis range (silent clipping).
sys.path.insert(0, str(Path(__file__).resolve().parent))
from make_tsfm_benchmark_interactive import build_figure, load_coverage, load_scores

scores, dropped = load_scores()
fig = build_figure(scores, load_coverage(), dropped)
clipped = []
for tr in fig.data:
    if tr.type == "scatter" and tr.mode == "markers":
        ax = "yaxis" + (tr.yaxis[1:] if len(tr.yaxis) > 1 else "")
        rng = fig.layout[ax].range
        if rng is None:
            continue
        out = [v for v in tr.y if v < rng[0] or v > rng[1]]
        if out:
            clipped.append(f"{tr.name}: {len(out)} point(s) outside {rng}")
check(
    "no calibration point falls outside the plotted axis range",
    not clipped,
    "; ".join(clipped[:3]),
)

if notes:
    print("\nCaveats carried into the figure:")
    for n in notes:
        print(f"  - {n}")

print(f"\n{len(failures)} check(s) failed.")
sys.exit(1 if failures else 0)
