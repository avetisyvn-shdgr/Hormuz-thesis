"""Daily panel assembly.

Merges registry variables into one DataFrame on a CALENDAR-day index.

Decisions (documented 2026-06, step 3 of the data-foundation phase):

1. CALENDAR-day index, not trading-day. The treatment is a physical
   disruption that does not respect exchange calendars: PortWatch is a
   genuine 7-day series and the Hormuz transit collapse includes weekend
   days (2026-03-01 was a Sunday). A trading-day index would discard ~29%
   of the operational data. Energy prices hold NaN on non-trading days.

2. NO gap-filling here. Assembly returns the honest merged state of the
   sources; any imputation is a separate, documented step-4 policy applied
   downstream. This keeps the missingness map meaningful and avoids
   smuggling forward-fill (and its leakage discussions) into the data layer.

3. FREE-ONLY by default. Only registry variables with status free/primary
   are included unless `allow_proxies=True`; proxy-resolved columns are
   renamed `<name>__proxy` so they can never masquerade as the real series
   (CLAUDE.md rule 8).
"""
from __future__ import annotations

import json

import pandas as pd

from . import config
from .registry import get_variable, _resolve_entry


def free_variables() -> list[str]:
    """Registry variables whose primary backend is genuinely free."""
    return [n for n, s in config.registry().items()
            if s.get("status") in ("free", "primary")]


def build_panel(
    variables: list[str] | None = None,
    start: str | None = None,
    end: str | None = None,
    allow_proxies: bool = False,
) -> pd.DataFrame:
    """Return a (calendar-date x variable) panel. Index name 'date'.

    Raises if a requested variable would resolve through its proxy and
    `allow_proxies` is False. Proxy columns are suffixed '__proxy'.
    """
    win = config.settings()["study_window"]
    start = start or win["full_start"]
    end = end or win["full_end"]

    reg = config.registry()
    names = variables if variables is not None else free_variables()

    index = pd.date_range(start, end, freq="D", name="date")
    cols: dict[str, pd.Series] = {}
    for name in names:
        _, channel = _resolve_entry(reg[name])
        if channel == "proxy" and not allow_proxies:
            raise ValueError(
                f"{name!r} resolves via its PROXY backend. Pass "
                "allow_proxies=True to include it explicitly (column will be "
                f"named '{name}__proxy'), or drop it from `variables`."
            )
        df = get_variable(name, start, end)
        col = name if channel == "primary" else f"{name}__proxy"
        s = df.set_index("date")["value"]
        # Series must align 1:1 onto the master index; duplicate dates were
        # already rejected by the provider contract.
        cols[col] = s.reindex(index)

    panel = pd.DataFrame(cols, index=index)
    return panel


def build_panel_from_frozen_raw(
    variables: list[str] | None = None,
    start: str | None = None,
    end: str | None = None,
) -> pd.DataFrame:
    """Rebuild the free panel from local immutable raw snapshots only.

    The latest provenance record for each requested variable identifies its
    tidy `(date, value)` raw file. No provider or network call is made.
    """
    win = config.settings()["study_window"]
    start = start or win["full_start"]
    end = end or win["full_end"]
    names = variables if variables is not None else free_variables()

    log_path = config.ROOT / config.settings()["paths"]["provenance_log"]
    if not log_path.exists():
        raise FileNotFoundError(f"Frozen provenance log not found: {log_path}")
    latest: dict[str, dict] = {}
    for line in log_path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            record = json.loads(line)
            latest[record["variable"]] = record

    index = pd.date_range(start, end, freq="D", name="date")
    cols: dict[str, pd.Series] = {}
    for name in names:
        if name not in latest:
            raise FileNotFoundError(
                f"No frozen provenance record for {name!r}; cannot run offline."
            )
        path = config.ROOT / latest[name]["file"]
        if not path.exists():
            raise FileNotFoundError(f"Frozen raw file for {name!r} not found: {path}")
        frame = pd.read_csv(path, parse_dates=["date"])
        if list(frame.columns) != ["date", "value"]:
            raise ValueError(
                f"Frozen raw file {path} must have columns ['date', 'value'], "
                f"got {list(frame.columns)}."
            )
        if frame["date"].duplicated().any():
            raise ValueError(f"Frozen raw file {path} contains duplicate dates.")
        values = pd.to_numeric(frame["value"], errors="coerce")
        series = pd.Series(values.to_numpy(), index=frame["date"], name=name)
        cols[name] = series.reindex(index)
    return pd.DataFrame(cols, index=index)


def coverage_summary(panel: pd.DataFrame) -> pd.DataFrame:
    """Per-column coverage diagnostics (no mutation)."""
    out = []
    for c in panel.columns:
        s = panel[c]
        obs = s.dropna()
        wd = obs.index.dayofweek
        out.append({
            "column": c,
            "non_null": int(obs.size),
            "null": int(s.isna().sum()),
            "null_share": round(float(s.isna().mean()), 4),
            "first_obs": obs.index.min().date() if obs.size else None,
            "last_obs": obs.index.max().date() if obs.size else None,
            "weekend_obs_share": round(float((wd >= 5).mean()), 4) if obs.size else None,
            "zeros": int((obs == 0).sum()),
        })
    return pd.DataFrame(out).set_index("column")
