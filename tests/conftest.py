"""Shared pytest import path setup for local, non-installed test runs."""
from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

for rel in ("src", "scripts"):
    path = str(ROOT / rel)
    if path not in sys.path:
        sys.path.insert(0, path)
