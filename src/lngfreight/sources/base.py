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

import pandas as pd


class BaseSource(abc.ABC):
    """Abstract data provider.

    Contract for fetch(): return a tidy DataFrame with EXACTLY these columns
        date   : pandas datetime64[ns] (UTC, tz-naive)
        value  : float
    sorted ascending by date, no duplicate dates. Provider-specific quirks
    (units, column names, missing-data markers) are resolved INSIDE the
    provider, so downstream code sees one uniform shape.
    """

    #: short stable id used in config/sources.yaml `provider:` field
    name: str = "base"

    @abc.abstractmethod
    def fetch(self, code: str, start: str, end: str) -> pd.DataFrame:
        """Pull one series. Must return the tidy (date, value) contract."""
        raise NotImplementedError

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
