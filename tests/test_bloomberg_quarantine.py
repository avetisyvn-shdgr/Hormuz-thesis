"""Guard the local-only quarantine of raw-bearing Bloomberg artifacts.

The provenance-limited workbooks carry unverified Bloomberg/Fearnleys/ClearLynx
rights (every ``rights`` field in ``config/bloomberg_exports.yaml`` is null).
Derived artifacts that embed the verbatim assessment histories must therefore
never enter version control until those rights are confirmed. This test fails
if the .gitignore quarantine entries are removed or renamed.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

QUARANTINED_PATTERNS = [
    # Full verbatim weekly Fearnleys histories (raw + analysis columns).
    "data/processed/lng_freight_weekly_panel.csv",
    "data/processed/lng_freight_descriptive_weekly.csv",
    # Full verbatim daily TTF and VLSFO histories.
    "data/processed/freight_market_context.csv",
    # Raw Data sheet screenshots from workbook inspection.
    ".work/",
]


def _gitignore_lines() -> list[str]:
    text = (ROOT / ".gitignore").read_text(encoding="utf-8")
    return [line.strip() for line in text.splitlines() if line.strip()]


def test_raw_bearing_bloomberg_artifacts_are_gitignored() -> None:
    lines = _gitignore_lines()
    missing = [pattern for pattern in QUARANTINED_PATTERNS if pattern not in lines]
    assert not missing, (
        "Raw-bearing Bloomberg artifacts lost their .gitignore quarantine "
        f"entries: {missing}. These embed licensed assessment values whose "
        "rights are unverified; restore the entries or record a decision-log "
        "entry citing confirmed redistribution rights before tracking them."
    )
