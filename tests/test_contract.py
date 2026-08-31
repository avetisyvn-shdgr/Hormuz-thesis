"""Tests that need NO network and NO API key. These guard the contract that
keeps the provider abstraction honest. Run: pytest -q
"""

import pandas as pd
import pytest


from hormuz_throughput.sources.base import BaseSource


def test_validate_enforces_columns():
    bad = pd.DataFrame({"date": ["2026-01-01"], "price": [1.0]})
    with pytest.raises(ValueError):
        BaseSource._validate(bad)


def test_validate_sorts_dedupes_and_types():
    raw = pd.DataFrame(
        {"date": ["2026-01-02", "2026-01-01", "2026-01-02"], "value": ["2", "1", "2"]}
    )
    out = BaseSource._validate(raw)
    assert list(out["date"]) == [pd.Timestamp("2026-01-01"), pd.Timestamp("2026-01-02")]
    assert out["value"].tolist() == [1.0, 2.0]
    assert str(out["value"].dtype) == "float64"


def test_validate_drops_missing():
    raw = pd.DataFrame({"date": ["2026-01-01", "2026-01-02"], "value": [1.0, None]})
    out = BaseSource._validate(raw)
    assert len(out) == 1


def test_registry_loads_and_has_target():
    from hormuz_throughput import config
    reg = config.registry()
    assert "spark30s_atlantic_freight" in reg
    assert reg["spark30s_atlantic_freight"]["role"] == "target"
