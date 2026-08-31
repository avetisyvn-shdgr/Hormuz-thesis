import pandas as pd
import pytest

from hormuz_throughput.sources.wto_hormuz import WTOHormuzLNGSource


def test_frozen_wto_lng_snapshot_contract():
    frame = WTOHormuzLNGSource().fetch(
        "lng_outbound_volume_index", "2025-01-01", "2025-01-10"
    )
    assert list(frame.columns) == ["date", "value"]
    assert len(frame) == 10
    assert pd.api.types.is_datetime64_ns_dtype(frame["date"])
    assert frame["value"].notna().all()


def test_wto_lng_source_rejects_unknown_code():
    with pytest.raises(ValueError, match="Only"):
        WTOHormuzLNGSource().fetch("lng_count", "2025-01-01", "2025-01-10")
