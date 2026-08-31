"""Centralised configuration loading.

Loads YAML settings + the series registry and resolves API keys from the
environment (never from code, never committed). One import, used everywhere,
so paths and windows are defined in exactly one place.
"""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = ROOT / "config"

load_dotenv(ROOT / ".env")


@lru_cache(maxsize=1)
def settings() -> dict:
    with open(CONFIG_DIR / "settings.yaml") as fh:
        return yaml.safe_load(fh)


@lru_cache(maxsize=1)
def registry() -> dict:
    with open(CONFIG_DIR / "sources.yaml") as fh:
        return yaml.safe_load(fh)["variables"]


def path(key: str) -> Path:
    """Resolve a configured path key to an absolute Path, creating it."""
    p = ROOT / settings()["paths"][key]
    if not p.suffix:
        p.mkdir(parents=True, exist_ok=True)
    return p


def api_key(name: str) -> str:
    """Fetch a required API key or fail loudly with a fix-it message."""
    val = os.environ.get(name)
    if not val:
        raise RuntimeError(
            f"Missing environment variable {name!r}. "
            f"Copy .env.example to .env and add your key. "
            f"See docs/DATA_SOURCES.md for where to register."
        )
    return val
