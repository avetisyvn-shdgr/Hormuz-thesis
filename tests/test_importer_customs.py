"""Tests for the importer_customs provider and the extended outcome build.

Value pins below are from the frozen 2026-07-17 snapshot vintage; if a
snapshot is legitimately re-captured, re-pin with a comment (same policy as
the spatial-panel pins in test_spatial.py).
"""

import pandas as pd
import pytest


from hormuz_throughput import config  # noqa: E402
from hormuz_throughput.importer_outcomes import build_outcomes, outcomes_summary  # noqa: E402
from hormuz_throughput.sources.importer_customs import (  # noqa: E402
    GULF_BY_UNIT,
    MEASURE_BY_UNIT,
    OMAN_BY_UNIT,
    SNAPSHOT_FILES,
    UNITS,
    ImporterCustomsSource,
    load_by_origin,
)

WINDOW = ("2024-01-01", "2026-07-07")


def _series(code: str) -> pd.Series:
    frame = ImporterCustomsSource().fetch(code, *WINDOW)
    return frame.set_index("date")["value"]


def test_provider_returns_tidy_monthly_contract():
    for unit in UNITS:
        s = _series(f"{unit}:total")
        assert s.index.is_monotonic_increasing
        assert not s.index.duplicated().any()
        assert (s.index.day == 1).all()
        assert (s >= 0).all()


def test_gulf_is_subset_of_total_and_never_negative():
    for unit in UNITS:
        total, gulf = _series(f"{unit}:total"), _series(f"{unit}:gulf")
        joined = pd.concat([total, gulf], axis=1, keys=["t", "g"]).dropna()
        assert (joined["g"] <= joined["t"] + 1e-9).all()


def test_gulf_collapse_pins_2026_snapshot_vintage():
    for unit in ("kr", "tw"):
        gulf = _series(f"{unit}:gulf")
        for month in ("2026-04-01", "2026-05-01", "2026-06-01"):
            assert gulf.loc[pd.Timestamp(month)] == 0.0, (unit, month)
    cn = _series("cn:gulf")
    assert cn.loc[pd.Timestamp("2026-04-01")] == pytest.approx(9571.1, abs=0.1)
    ind = _series("in:gulf")
    assert ind.loc[pd.Timestamp("2026-04-01")] == 0.0
    assert ind.loc[pd.Timestamp("2026-05-01")] == pytest.approx(27500.0, abs=0.1)
    jp = _series("jp:gulf")
    assert jp.loc[pd.Timestamp("2026-04-01")] == 0.0
    assert jp.loc[pd.Timestamp("2026-05-01")] == pytest.approx(60715.0, abs=0.1)


def test_pre_shock_gulf_share_pins_2026_snapshot_vintage():
    expected = {"kr": 0.152, "tw": 0.349, "cn": 0.304, "in": 0.581, "jp": 0.065}
    for unit, pin in expected.items():
        total, gulf = _series(f"{unit}:total"), _series(f"{unit}:gulf")
        share = (gulf / total).loc["2025-03-01":"2026-02-01"]
        assert float(share.mean()) == pytest.approx(pin, abs=0.002), unit


def test_oman_is_excluded_from_every_gulf_set():
    for unit in UNITS:
        assert OMAN_BY_UNIT[unit] not in GULF_BY_UNIT[unit]


def test_india_is_value_basis_and_others_are_weight():
    assert MEASURE_BY_UNIT["in"] == "value_kusd"
    frame = load_by_origin("in")
    assert frame["weight_ton"].isna().all()
    for unit in ("kr", "tw", "cn", "jp"):
        assert MEASURE_BY_UNIT[unit] == "weight_ton"
        assert load_by_origin(unit)["weight_ton"].notna().any()


def test_registry_declares_all_ten_importer_variables():
    reg = config.registry()
    for prefix in ("korea", "taiwan", "china", "india", "japan"):
        for series in ("total", "gulf"):
            name = f"{prefix}_lng_import_{series}"
            assert name in reg, name
            spec = reg[name]
            assert spec["role"] == "importer"
            assert spec["status"] == "free"
            assert spec["primary"]["provider"] == "importer_customs"


def test_provider_rejects_unknown_codes():
    src = ImporterCustomsSource()
    with pytest.raises(ValueError):
        src.fetch("xx:total", *WINDOW)
    with pytest.raises(ValueError):
        src.fetch("kr:bogus", *WINDOW)
    with pytest.raises(ValueError):
        src.fetch("krtotal", *WINDOW)


def test_extended_outcomes_cover_six_units_and_stay_consistent():
    probe_dir = config.path("data_raw") / "backup_pathway_probe_20260621"
    eurostat_path = config.ROOT / config.settings()["paths"][
        "eurostat_lng_eu27_by_partner_json"
    ]
    frame = build_outcomes(
        probe_dir,
        customs_dir=config.path("importer_customs_dir"),
        eurostat_path=eurostat_path,
    )
    summary = outcomes_summary(frame)
    assert summary["units_with_gulf_outcome"] == [
        "China", "EU27", "India", "Japan", "Korea", "Taiwan",
    ]
    shares = frame[frame["outcome"] == "y1_gulf_share"]["value"].dropna()
    assert ((shares >= 0) & (shares <= 1)).all()
    kr_apr = frame[
        (frame["unit"] == "Korea")
        & (frame["outcome"] == "y1_gulf_share")
        & (frame["month"] == "2026-04")
    ]
    assert float(kr_apr["value"].iloc[0]) == 0.0
    probe_only = build_outcomes(probe_dir)
    assert sorted(probe_only["unit"].unique()) == ["EU27", "Japan"]


def test_outcome_builder_honors_explicit_customs_dir(tmp_path):
    source_dir = config.path("importer_customs_dir")
    for filename in SNAPSHOT_FILES.values():
        frame = pd.read_csv(source_dir / filename)
        if filename == SNAPSHOT_FILES["kr"]:
            mask = (frame["period"] == "2026-03") & (frame["country"] == "카타르")
            assert mask.any()
            frame.loc[mask, "weight_ton"] = 12345.0
        frame.to_csv(tmp_path / filename, index=False)

    probe_dir = config.path("data_raw") / "backup_pathway_probe_20260621"
    frame = build_outcomes(probe_dir, customs_dir=tmp_path)
    kr_mar = frame[
        (frame["unit"] == "Korea")
        & (frame["outcome"] == "y1_gulf_volume")
        & (frame["month"] == "2026-03")
    ]
    assert float(kr_mar["value"].iloc[0]) == 12345.0
