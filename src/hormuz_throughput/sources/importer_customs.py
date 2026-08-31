"""National-customs LNG imports by origin (V-layer providers).

Serves the frozen, hash-verified importer customs snapshots (captured
2026-07-17: Korea KCS, Taiwan MOF Customs, China GACC, India DGCI&S
Tradestat, Japan e-Stat/Japan Customs) through the registry contract,
closing the "live registry/provider
wiring" gap that `importer_outcomes.py` documented as a later increment.

Registry codes are "<unit>:<series>" with
    unit   in {kr, tw, cn, in, jp}
    series in {total, gulf}
returning monthly national LNG imports summed over origin countries; `gulf`
restricts to the Hormuz-dependent exporter set of
docs/CAPTIVITY_EVENT_STUDY_DESIGN.md 6.3. Oman is deliberately EXCLUDED
everywhere: Omani LNG loads at Qalhat/Sur on the Gulf of Oman, outside the
Strait of Hormuz.

Measurement basis is PER UNIT and deliberately not mixed:
    kr, tw, cn, jp : weight_ton  (metric tonnes, customs tonnage)
    in         : value_kusd  (thousand USD — Tradestat's HS-6 monthly
                 'Quantity' field is unpopulated/zero, verified 2026-07-17,
                 so India is value-basis; its Gulf SHARE therefore embeds
                 origin price differentials and must be flagged as such)
The returned date is the first day of the month. Country names in the
snapshots are SOURCE-NATIVE (Korean, Chinese, English) — classification
lives here in code, not in the data files.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from .base import BaseSource, SourcePayload
from .. import config

SNAPSHOT_SCHEMA = ["period", "country", "hs", "weight_ton", "value_kusd"]

UNITS = ("kr", "tw", "cn", "in", "jp")

GULF_BY_UNIT: dict[str, frozenset[str]] = {
    "kr": frozenset({
        "카타르",
        "아랍에미리트 연합",
        "쿠웨이트",
        "이라크",
        "사우디아라비아",
        "바레인",
        "이란",
    }),
    "tw": frozenset({
        "卡達",
        "阿拉伯聯合大公國",
        "科威特",
        "伊拉克",
        "沙烏地阿拉伯",
        "巴林",
        "伊朗",
    }),
    "cn": frozenset({
        "Qatar", "United Arab Emirates", "Kuwait", "Iraq",
        "Saudi Arabia", "Bahrain", "Iran",
    }),
    "in": frozenset({
        "QATAR", "U ARAB EMTS", "KUWAIT", "IRAQ",
        "SAUDI ARAB", "BAHARAIN IS", "IRAN",
    }),
    "jp": frozenset({
        "Qatar", "United Arab Emirates", "Kuwait", "Iraq",
        "Saudi Arabia", "Bahrain", "Iran",
    }),
}

OMAN_BY_UNIT: dict[str, str] = {
    "kr": "오만",
    "tw": "阿曼",
    "cn": "Oman",
    "in": "OMAN",
    "jp": "Oman",
}

SNAPSHOT_FILES: dict[str, str] = {
    "kr": "kr_lng_imports_by_origin.csv",
    "tw": "tw_lng_imports_by_origin.csv",
    "cn": "cn_lng_imports_by_origin.csv",
    "in": "in_lng_imports_by_origin.csv",
    "jp": "jp_lng_imports_by_origin.csv",
}

SOURCE_LABELS: dict[str, str] = {
    "kr": "Korea Customs Service (tradedata.go.kr) HS 2711110000",
    "tw": "Taiwan MOF Customs Administration (portal.sw.nat.gov.tw) HS 271111",
    "cn": "China GACC (stats.customs.gov.cn) HS 27111100",
    "in": "India DGCI&S Tradestat meidb HS 271111",
    "jp": "Trade Statistics of Japan / e-Stat HS 271111000",
}

MEASURE_BY_UNIT: dict[str, str] = {
    "kr": "weight_ton",
    "tw": "weight_ton",
    "cn": "weight_ton",
    "in": "value_kusd",
    "jp": "weight_ton",
}


def snapshot_path(unit: str, base_dir: Path | None = None) -> Path:
    if unit not in UNITS:
        raise ValueError(f"Unknown importer-customs unit {unit!r}; expected {UNITS}.")
    root = base_dir if base_dir is not None else config.path("importer_customs_dir")
    return root / SNAPSHOT_FILES[unit]


def load_by_origin(unit: str, base_dir: Path | None = None) -> pd.DataFrame:
    """Load and validate one unit's full (period, country) snapshot."""
    path = snapshot_path(unit, base_dir=base_dir)
    if not path.exists():
        raise FileNotFoundError(
            f"Importer-customs snapshot missing: {path}. "
            "Run scripts/ingest_importer_customs_snapshots.py."
        )
    frame = pd.read_csv(path)
    if list(frame.columns) != SNAPSHOT_SCHEMA:
        raise ValueError(
            f"{unit}: snapshot schema drift: expected {SNAPSHOT_SCHEMA}, "
            f"got {list(frame.columns)}."
        )
    if frame.duplicated(subset=["period", "country"]).any():
        raise ValueError(f"{unit}: duplicate (period, country) rows in snapshot.")
    periods = pd.to_datetime(frame["period"], format="%Y-%m", errors="coerce")
    if periods.isna().any():
        raise ValueError(f"{unit}: unparseable period values (expected YYYY-MM).")
    measure = MEASURE_BY_UNIT[unit]
    if frame[measure].isna().all():
        raise ValueError(f"{unit}: measure column {measure!r} is entirely empty.")
    if (frame[measure].dropna() < 0).any():
        raise ValueError(f"{unit}: negative {measure} values.")
    pre = frame[frame["period"] < "2026-03"]
    if not (set(pre["country"]) & set(GULF_BY_UNIT[unit])):
        raise ValueError(
            f"{unit}: no Hormuz-dependent partner found pre-2026-03; "
            "country-name mapping in GULF_BY_UNIT has drifted from the snapshot."
        )
    return frame


class ImporterCustomsSource(BaseSource):
    name = "importer_customs"

    def fetch(self, code: str, start: str, end: str) -> pd.DataFrame:
        try:
            unit, series = code.split(":")
        except ValueError as exc:
            raise ValueError(
                f"importer_customs code must be '<unit>:<series>', got {code!r}."
            ) from exc
        if series not in ("total", "gulf"):
            raise ValueError(f"Unknown series {series!r}; expected total|gulf.")
        source_path = snapshot_path(unit)
        self._capture_source_payload(SourcePayload(
            filename=source_path.name,
            media_type="text/csv",
            role="normalized_provider_snapshot",
            path=source_path,
        ))
        frame = load_by_origin(unit)
        measure = MEASURE_BY_UNIT[unit]
        if series == "gulf":
            frame = frame[frame["country"].isin(GULF_BY_UNIT[unit])]
        monthly = (
            frame.groupby("period", as_index=False)[measure].sum()
            .rename(columns={"period": "date", measure: "value"})
        )
        monthly["date"] = pd.to_datetime(monthly["date"], format="%Y-%m")
        if series == "gulf":
            all_months = (
                load_by_origin(unit)["period"].drop_duplicates().sort_values()
            )
            idx = pd.to_datetime(all_months, format="%Y-%m")
            monthly = (
                monthly.set_index("date").reindex(idx).fillna(0.0)
                .rename_axis("date").reset_index()
            )
        mask = (monthly["date"] >= pd.Timestamp(start)) & (
            monthly["date"] <= pd.Timestamp(end)
        )
        monthly = monthly.loc[mask]
        if monthly.empty:
            raise ValueError(f"No {code} rows inside [{start}, {end}].")
        return self._validate(monthly[["date", "value"]])
