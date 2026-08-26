"""Stale-claim detection and artifact-citation checking for the final audit.

A naive grep for a retired phrase is useless in this repository, because the
phrase appears constantly in exactly the places it should: correction notices,
prohibition lists, reporting guards, and the decision log's record of what was
retired and why. Flagging those would bury a real violation under dozens of
false positives, and a scanner that cries wolf gets switched off.

So the scanner classifies each hit by the *context* it sits in:

``cleared``
    The surrounding sentence negates, quotes, prohibits, or historicises the
    phrase -- "not a variance decomposition", "replace 'no rebound' with...",
    "never call this an ATT".
``flagged``
    The phrase is asserted. This is a real stale claim and must be fixed.

Context is taken as a window of lines around the hit rather than the single
matched line, because in prose the negation frequently lands on the line before
or after ("These are sensitivity ranges, not / variance decompositions.").

The second half of the module checks the opposite failure: an empirical number
stated without a frozen artifact to cite. It looks for numeric claims in
thesis-facing prose and asks whether an artifact path or explicit citation
marker appears nearby.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

import pandas as pd


# Markers that turn an occurrence into a legitimate mention rather than a claim.
NEGATION_MARKERS = (
    "not ",
    "never",
    "neither",
    "no longer",
    "nor ",
    "cannot",
    "can not",
    "must not",
    "may not",
    "does not",
    "do not",
    "is not",
    "are not",
    "was not",
    "were not",
    "without",
    "avoid",
    "forbid",
    "prohibit",
    "prohibited",
    "banned",
    "retire",
    "retired",
    "replace",
    "replaced",
    "supersede",
    "superseded",
    "corrected",
    "correction",
    "stale",
    "instead of",
    "rather than",
    "exclude",
    "excludes",
    "excluded",
    "guard",
    "false",
    "wrong",
    "incorrect",
    "misread",
    "misreading",
    "would be",
    "if any",
    "claim boundary",
    "interpretation limit",
    "kill criteri",
    # Retirement and comparison language: the phrase names what was moved away
    # from, or another study's scope, rather than asserting it here.
    "weaker than",
    "stronger than",
    "moving from",
    "move from",
    "moved from",
    "pivot",
    "away from",
    "non-",
    "limitation",
    "out of scope",
    "no longer used",
)

# Immediate-prefix negations that a sentence-level marker scan misses, because
# the negation is fused to the phrase itself ("no ATT", "non-ATT").
INLINE_NEGATION_PREFIXES = (
    "no ",
    "non-",
    "non ",
    "non",
    "not ",
    "anti-",
    "sans ",
)
INLINE_PREFIX_LOOKBACK = 16

# Machine-readable guard keys and schema fields are configuration, not prose.
STRUCTURAL_MARKERS = (
    "is_att",
    "is_causal",
    "_permitted",
    "prohibited_labels",
    "reporting_guards",
    "claim_vocabulary",
    "not_equivalent_to",
    "stale_phrases",
    "banned",
    "pattern",
)

NUMBER_PATTERN = re.compile(r"(?<![\w.])\d{1,3}(?:[,\d]*)(?:\.\d+)?(?![\w])")
CITATION_MARKERS = (
    "data/processed/",
    "data/raw/",
    "data/interim/",
    "reports/",
    "config/",
    "docs/",
    ".csv",
    ".json",
    ".md",
    "sha256",
    "manifest",
)

AUDIT_COLUMNS = [
    "path",
    "line_number",
    "category",
    "pattern",
    "verdict",
    "clearing_marker",
    "line",
]


@dataclass(frozen=True)
class StalePattern:
    """One retired phrase, with the category it belongs to."""

    category: str
    pattern: str
    regex: bool = False

    def compiled(self) -> re.Pattern:
        source = self.pattern if self.regex else re.escape(self.pattern)
        return re.compile(source, re.IGNORECASE)


def context_window(lines: list[str], index: int, radius: int = 2) -> str:
    """Lines around ``index``, joined, lowercased.

    Prose negation often lands on an adjacent line, so a single-line test
    produces false positives on correctly-hedged text.
    """
    lo = max(0, index - radius)
    hi = min(len(lines), index + radius + 1)
    return " ".join(lines[lo:hi]).lower()


def inline_negation(line: str, match_start: int) -> str | None:
    """Detect a negation fused to the phrase itself, e.g. 'no ATT', 'non-ATT'.

    A sentence-level marker scan misses these: the negating token sits
    immediately before the match with no other cue in the surrounding prose.
    """
    lookback = line[max(0, match_start - INLINE_PREFIX_LOOKBACK):match_start]
    lowered = lookback.lower()
    for prefix in INLINE_NEGATION_PREFIXES:
        if lowered.endswith(prefix):
            return prefix.strip() or prefix
    return None


def clearing_marker(
    context: str, line: str, match_start: int | None = None
) -> str | None:
    """Return the marker that clears this hit, or None if it is asserted."""
    lowered_line = line.lower()
    for marker in STRUCTURAL_MARKERS:
        if marker in lowered_line:
            return f"structural:{marker}"
    if match_start is not None:
        prefix = inline_negation(line, match_start)
        if prefix:
            return f"inline_negation:{prefix}"
    # A phrase inside quotation marks is being mentioned, not asserted.
    if any(quote in line for quote in ('"', "“", "”", "'", "`")):
        return "quoted"
    for marker in NEGATION_MARKERS:
        if marker in context:
            return f"negated:{marker.strip()}"
    return None


def scan_text(
    path: str,
    text: str,
    patterns: list[StalePattern],
    *,
    context_radius: int = 2,
) -> list[dict]:
    """Classify every stale-pattern occurrence in one document."""
    lines = text.splitlines()
    rows = []
    for pattern in patterns:
        regex = pattern.compiled()
        for index, line in enumerate(lines):
            found = regex.search(line)
            if not found:
                continue
            context = context_window(lines, index, context_radius)
            marker = clearing_marker(context, line, found.start())
            rows.append({
                "path": path,
                "line_number": index + 1,
                "category": pattern.category,
                "pattern": pattern.pattern,
                "verdict": "cleared" if marker else "flagged",
                "clearing_marker": marker or "",
                "line": line.strip()[:300],
            })
    return rows


def scan_documents(
    documents: dict[str, str],
    patterns: list[StalePattern],
    *,
    context_radius: int = 2,
) -> pd.DataFrame:
    """Scan a mapping of path -> text and return one row per occurrence."""
    rows: list[dict] = []
    for path in sorted(documents):
        rows.extend(
            scan_text(
                path, documents[path], patterns, context_radius=context_radius
            )
        )
    frame = pd.DataFrame(rows, columns=AUDIT_COLUMNS)
    return frame.sort_values(
        ["path", "line_number", "pattern"], kind="stable"
    ).reset_index(drop=True)


def flagged(scan: pd.DataFrame) -> pd.DataFrame:
    """Only the occurrences that assert a retired claim."""
    return scan.loc[scan["verdict"].eq("flagged")].reset_index(drop=True)


def uncited_numeric_lines(
    text: str,
    *,
    context_radius: int = 3,
    ignore_prefixes: tuple[str, ...] = ("#", "|---", ">"),
    min_digits: int = 3,
) -> list[dict]:
    """Lines stating a substantive number with no artifact citation nearby.

    Deliberately conservative: short numbers (years, counts under three digits,
    list markers) are ignored, because flagging every "3" would make the check
    unusable. The purpose is to catch a headline empirical value quoted with no
    frozen artifact behind it.
    """
    lines = text.splitlines()
    rows = []
    for index, line in enumerate(lines):
        stripped = line.strip()
        if not stripped or stripped.startswith(ignore_prefixes):
            continue
        numbers = [
            match.group(0)
            for match in NUMBER_PATTERN.finditer(stripped)
            if len(match.group(0).replace(",", "").replace(".", "")) >= min_digits
        ]
        if not numbers:
            continue
        context = context_window(lines, index, context_radius)
        if any(marker.lower() in context for marker in CITATION_MARKERS):
            continue
        rows.append({
            "line_number": index + 1,
            "numbers": ", ".join(numbers[:5]),
            "line": stripped[:300],
        })
    return rows


def source_confusion_hits(
    documents: dict[str, str],
    *,
    portwatch_terms: tuple[str, ...] = ("portwatch", "tanker transit", "n_tanker"),
    lng_specific_terms: tuple[str, ...] = ("lng-specific", "lng specific", "lng volume"),
) -> pd.DataFrame:
    """Lines that read a PortWatch all-tanker number as LNG-specific.

    PortWatch counts all tankers and has no LNG class. Attributing an
    LNG-specific meaning to a PortWatch figure is a substantive error, distinct
    from a retired phrase, so it gets its own check.
    """
    rows = []
    for path in sorted(documents):
        for index, line in enumerate(documents[path].splitlines()):
            lowered = line.lower()
            has_pw = any(term in lowered for term in portwatch_terms)
            has_lng = any(term in lowered for term in lng_specific_terms)
            if has_pw and has_lng:
                context = context_window(
                    documents[path].splitlines(), index, 2
                )
                # Co-occurrence on one line is not conflation. A contrast
                # word or an enumeration separator means the two layers are
                # being distinguished or merely listed side by side.
                cleared = any(
                    marker in context
                    for marker in (
                        "not ", "never", "distinct", "separate", "unlike",
                        "while", "whereas", "versus", " vs ", "rather than",
                        "ranking", "optional", "→", "->", "|",
                    )
                )
                rows.append({
                    "path": path,
                    "line_number": index + 1,
                    "verdict": "cleared" if cleared else "flagged",
                    "line": line.strip()[:300],
                })
    return pd.DataFrame(
        rows, columns=["path", "line_number", "verdict", "line"]
    )
