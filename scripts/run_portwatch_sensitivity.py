"""Regenerate the optional PortWatch sensitivity branch through phase 3.

This runner deliberately excludes the missing model-vintage matrix. That phase
requires a separate anchored checkpoint and Mher's G4 verification first.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PHASE_0_3_STEPS = (
    ("verify optional August input", "scripts/verify_sensitivity_inputs.py"),
    ("regenerate known AR vintage/window table", "scripts/run_portwatch_vintage_sensitivity.py"),
    ("validate and materialize admission lock", "scripts/build_model_admission_protocol.py"),
    ("regenerate trusted-endpoint rebound profile", "scripts/run_rebound_relapse_profile.py"),
    ("freeze prepared sensitivity branch", "scripts/freeze_portwatch_sensitivity.py", "--mode", "prepared"),
)


def main() -> int:
    for label, *args in PHASE_0_3_STEPS:
        print(f"\n=== {label} ===", flush=True)
        completed = subprocess.run([sys.executable, *args], cwd=ROOT, check=False)
        if completed.returncode:
            print(f"stopped at {label}")
            return completed.returncode
    print("\nPrepared sensitivity branch complete; matrix remains gated.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
