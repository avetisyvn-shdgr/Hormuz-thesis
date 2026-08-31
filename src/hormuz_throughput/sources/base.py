"""Provider abstraction.

Every data provider (EIA, FRED, PortWatch, and later Spark/Bloomberg)
implements this one interface. Analysis code never imports a specific
provider - it asks the registry for a logical variable and gets back a
tidy, identically-shaped DataFrame regardless of who supplied it.

This is the mechanism that lets you swap the free fallback for proprietary
feeds later by editing config/sources.yaml alone.
"""
from __future__ import annotations

import abc
from dataclasses import dataclass
from pathlib import Path

import pandas as pd


@dataclass(frozen=True)
class SourcePayload:
    """Unmodified source bytes or an existing file that contains them."""

    filename: str
    media_type: str
    role: str = "original_source_payload"
    source_url: str | None = None
    content: bytes | None = None
    path: Path | None = None

    def __post_init__(self) -> None:
        if (self.content is None) == (self.path is None):
            raise ValueError("SourcePayload requires exactly one of content or path.")


class BaseSource(abc.ABC):
    """Abstract data provider.

    Contract for fetch(): return a tidy DataFrame with EXACTLY these columns
        date   : pandas datetime64[ns] (UTC, tz-naive)
        value  : float
    sorted ascending by date, no duplicate dates. Provider-specific quirks
    (units, column names, missing-data markers) are resolved INSIDE the
    provider, so downstream code sees one uniform shape.
    """

    name: str = "base"
    _source_payload: SourcePayload | None = None

    @abc.abstractmethod
    def fetch(self, code: str, start: str, end: str) -> pd.DataFrame:
        """Pull one series. Must return the tidy (date, value) contract."""
        raise NotImplementedError

    @property
    def source_payload(self) -> SourcePayload | None:
        """Original payload captured by the most recent ``fetch`` call."""
        return self._source_payload

    def _capture_source_payload(self, payload: SourcePayload) -> None:
        self._source_payload = payload

    @staticmethod
    def _validate(df: pd.DataFrame) -> pd.DataFrame:
        """Enforce the output contract. Fail loudly rather than pass bad data on."""
        expected = {"date", "value"}
        if set(df.columns) != expected:
            raise ValueError(f"Source returned columns {set(df.columns)}, expected {expected}")
        df = df.dropna(subset=["value"]).copy()
        df["date"] = pd.to_datetime(df["date"]).dt.tz_localize(None)
        df["value"] = df["value"].astype(float)
        df = df.drop_duplicates(subset="date").sort_values("date").reset_index(drop=True)
        return df
