"""Shared pytest import path setup for local, non-installed test runs."""
from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

# ROOT itself is required for `import scripts.foo`; `python -m pytest` supplies
# it via the working directory, but a bare `pytest` invocation does not.
for candidate in (ROOT, ROOT / "src", ROOT / "scripts"):
    path = str(candidate)
    if path not in sys.path:
        sys.path.insert(0, path)
