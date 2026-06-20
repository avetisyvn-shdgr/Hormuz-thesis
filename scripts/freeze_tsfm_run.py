"""Freeze the modern-TSFM benchmark run's provenance into an isolated manifest.

``docs/MODERN_TSFM_BENCHMARK.md`` requires that, before any TSFM number is cited
in the thesis, the exact package versions, model revisions, device, and output
hashes be frozen. The TSFM benchmark is deliberately ISOLATED from the core
PortWatch pipeline (excluded from ``run_all.py`` and the frozen core
requirements, run in two separate Python-3.11 venvs), so its provenance is frozen
HERE rather than inside ``freeze_reproducibility.py``.

This script does not run any model and does not download weights. It only
introspects what is already installed and cached, plus the benchmark CSV outputs
already on disk, and records them with a capture timestamp. Re-run it on the same
machine that produced the cited TSFM numbers; if a venv or the HF cache is absent
the corresponding block is recorded as ``unavailable`` rather than fabricated.

Run from the repo root (core venv is fine — no model weights are touched):
    python scripts/freeze_tsfm_run.py
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import platform
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lngfreight import config  # noqa: E402


OUT = "data/processed/tsfm_run_manifest.json"

# The two isolated benchmark environments and the packages whose versions fix the
# numerical result (see docs/MODERN_TSFM_BENCHMARK.md "Two benchmark environments").
BENCH_ENVS = {
    ".venv-bench": (
        "chronos-forecasting", "torch", "uni2ts", "gluonts", "transformers",
        "accelerate", "numpy", "pandas",
    ),
    ".venv-timesfm": (
        "timesfm", "torch", "transformers", "huggingface-hub", "numpy", "pandas",
    ),
}

# Model repos pulled by the adapters in src/lngfreight/tsfm.py.
MODEL_REPOS = (
    "models--amazon--chronos-2",
    "models--google--timesfm-2.5-200m-pytorch",
    "models--Salesforce--moirai-2.0-R-small",
)

# Benchmark + counterfactual-cross-check outputs whose identity is the cited
# result. The counterfactual files are the Chronos-2 ADMITTED cross-check
# (run_tsfm_counterfactual.py) and are model results, so they are frozen too.
BENCH_OUTPUTS = (
    "data/processed/tsfm_benchmark_scores.csv",
    "data/processed/tsfm_benchmark_forecasts.csv",
    "data/processed/tsfm_benchmark_summary.csv",
    "data/processed/tsfm_admission_test.csv",
    "data/processed/tsfm_counterfactual_summary.csv",
    "data/processed/tsfm_counterfactual_daily.csv",
)


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _venv_provenance(root: Path, venv: str, packages: tuple[str, ...]) -> dict:
    py = root / venv / "bin" / "python"
    if not py.exists():
        return {"status": "unavailable", "reason": f"{venv}/bin/python not found"}
    probe = (
        "import json,platform\n"
        "from importlib.metadata import version, PackageNotFoundError\n"
        f"pkgs={list(packages)!r}\n"
        "out={}\n"
        "for p in pkgs:\n"
        "    try: out[p]=version(p)\n"
        "    except PackageNotFoundError: out[p]='not-installed'\n"
        "info={'python':platform.python_version(),'platform':platform.platform(),"
        "'packages':out}\n"
        "print(json.dumps(info))\n"
    )
    try:
        res = subprocess.run(
            [str(py), "-c", probe], capture_output=True, text=True, check=True
        )
    except subprocess.CalledProcessError as exc:  # pragma: no cover - env probe
        return {"status": "error", "reason": exc.stderr.strip()[:500]}
    data = json.loads(res.stdout)
    data["status"] = "captured"
    return data


def _model_revisions(hub: Path) -> dict:
    if not hub.exists():
        return {"status": "unavailable", "reason": f"{hub} not found"}
    revisions = {}
    for repo in MODEL_REPOS:
        snap = hub / repo / "snapshots"
        if snap.exists():
            commits = sorted(p.name for p in snap.iterdir() if p.is_dir())
            revisions[repo] = commits
        else:
            revisions[repo] = ["unavailable"]
    return {"status": "captured", "hf_hub": str(hub), "snapshots": revisions}


def main() -> int:
    root = config.ROOT
    hub = Path.home() / ".cache" / "huggingface" / "hub"

    outputs = {}
    for rel in BENCH_OUTPUTS:
        p = root / rel
        outputs[rel] = _sha256(p) if p.exists() else "missing"

    manifest = {
        "captured_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "capture_host_platform": platform.platform(),
        "note": (
            "Provenance of the isolated TSFM benchmark run. NOT part of the frozen "
            "PortWatch run_all.py pipeline. Re-run on the machine that produced the "
            "cited numbers; verify these versions/revisions match docs/"
            "MODERN_TSFM_BENCHMARK.md before citing any TSFM result. Foundation "
            "models are an ADMITTED benchmark cross-check only, never the locked "
            "AR-only primary (CLAUDE.md rule 2)."
        ),
        "device": "cpu",
        "benchmark_environments": {
            venv: _venv_provenance(root, venv, pkgs)
            for venv, pkgs in BENCH_ENVS.items()
        },
        "model_revisions": _model_revisions(hub),
        "benchmark_output_sha256": outputs,
    }

    path = root / OUT
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {path}")
    for venv, prov in manifest["benchmark_environments"].items():
        if prov.get("status") == "captured":
            torch_v = prov["packages"].get("torch", "n/a")
            print(f"  {venv}: python {prov['python']}, torch {torch_v}")
        else:
            print(f"  {venv}: {prov['status']} ({prov.get('reason', '')})")
    rev = manifest["model_revisions"]
    if rev.get("status") == "captured":
        for repo, commits in rev["snapshots"].items():
            print(f"  {repo}: {','.join(commits)}")
    missing = [k for k, v in outputs.items() if v == "missing"]
    if missing:
        print(f"  WARNING: missing benchmark outputs: {missing}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
