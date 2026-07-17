"""Normalize the 2026-07-17 importer-customs captures into frozen snapshots.

Reads the staged captures in data/raw_staging/ (Korea KCS, Taiwan MOF Customs,
China GACC, India DGCI&S Tradestat) plus the 2026-07-17 public Japan e-Stat
snapshot, normalizes each into the canonical
snapshot schema

    period (YYYY-MM), country (source-native), hs, weight_ton, value_kusd

and writes them into data/raw/importer_customs/ via provenance.save_raw so
every snapshot gets a provenance.jsonl record and a content hash. Unmodified
source downloads are copied to data/raw/importer_customs/originals/ with a
README documenting the capture method (several required manual browser steps:
Taiwan is captcha-gated, China is WAF-gated).

Idempotent: identical payloads are deduplicated by save_raw; rerunning after
an upstream refresh writes content-addressed variants instead of overwriting.
Run once, then: python scripts/freeze_reproducibility.py
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lngfreight import config, provenance  # noqa: E402
from lngfreight.sources.importer_customs import (  # noqa: E402
    GULF_BY_UNIT,
    MEASURE_BY_UNIT,
    SNAPSHOT_FILES,
    SNAPSHOT_SCHEMA,
    load_by_origin,
)

STAGING = config.ROOT / "data" / "raw_staging"

PUBLIC_SNAPSHOT = config.ROOT / "data" / "raw" / "public_snapshots_20260717"

LICENSES = {
    "kr": "Korea Open Government Data (tradedata.go.kr)",
    "tw": "Taiwan Open Government Data License (portal.sw.nat.gov.tw)",
    "cn": "GACC public customs statistics (stats.customs.gov.cn)",
    "in": "Government of India open data (tradestat.commerce.gov.in)",
    "jp": "Trade Statistics of Japan / e-Stat public statistics portal",
}

ORIGINALS_README = """\
# Importer-customs capture provenance (2026-07-17)

Normalized snapshots one level up were produced by
scripts/ingest_importer_customs_snapshots.py from the captures below.
Method notes (what a re-capture requires):

- kr: Korea Customs Service, tradedata.go.kr -> 수출입통계 > 수출입 실적,
  통계항목 품목별+국가별, HS 2711110000, 월별, queried in three <=12-month
  windows (portal cap), rendered table scraped (100 rows/page). No original
  file exists: the scrape IS the capture; kr rows were captured 2026-07-15
  (June 2026 finals published that day).
- tw: Taiwan MOF Customs, portal.sw.nat.gov.tw/APGA/GA30 綜合查詢, 進口總值,
  按月 113年1月-115年6月, 貨品號列 271111, 全部國家, 重量(公噸)+金額(美元),
  下載CSV. CAPTCHA-gated: downloaded manually by the author 2026-07-17.
  Original: tw_original_big5.csv (Big5 encoding, ROC calendar).
- cn: China GACC, stats.customs.gov.cn interactive tables (WAF-gated;
  manual browser session by the author 2026-07-17), monthly imports of
  HS 27111100 by trading partner, US dollar, "By month", three 1-year
  queries. Originals: cn_original_2024.csv / _2025.csv / _2026.csv
  (Quantity in kilograms; normalized to metric tonnes).
- in: India DGCI&S Tradestat meidb commodity_wise_all_countries_import,
  scripted capture via scripts/fetch_india_tradestat_lng.py (calendar-year
  basis, US $ Million; the HS-6 monthly Quantity field is unpopulated, so
  the value series is the usable one). Original: in_original_long.csv.
- jp: Trade Statistics of Japan / e-Stat, monthly imports of HS 271111000
  by partner country, captured 2026-07-17 from public e-Stat CSV downloads
  plus the Japan Customs country-code list. Originals:
  jp_estat_2024_raw.csv / _2025_raw.csv / _2026_raw.csv, the country-code
  HTML page, search-result HTML pages, and jp_original_lng271111_with_jpy.csv.
  The canonical provider snapshot is weight-basis. The source JPY-thousand
  value is preserved in jp_original_lng271111_with_jpy.csv and is not relabeled
  as USD.

Gulf classification is NOT in these files; it lives in
src/lngfreight/sources/importer_customs.py (design doc 6.3, Oman excluded).
"""


def _finish(unit: str, frame: pd.DataFrame) -> pd.DataFrame:
    frame = frame[SNAPSHOT_SCHEMA].copy()
    frame = frame.sort_values(["period", "country"]).reset_index(drop=True)
    measure = MEASURE_BY_UNIT[unit]
    if frame[measure].isna().all():
        raise SystemExit(f"{unit}: measure column {measure} empty after normalize")
    return frame


def normalize_kr() -> pd.DataFrame:
    src = STAGING / "kcs_korea" / "kcs_lng_imports_by_origin_2024-01_2026-06.csv"
    df = pd.read_csv(src, dtype={"period": str, "hs": str})
    return _finish("kr", pd.DataFrame({
        "period": df["period"].str.replace(".", "-", regex=False),
        "country": df["country"].str.strip(),
        "hs": df["hs"].astype(str),
        "weight_ton": df["imp_weight_ton"],
        "value_kusd": df["imp_value_kusd"],
    }))


def normalize_tw() -> pd.DataFrame:
    src = STAGING / "taiwan_customs" / "taiwan_lng_imports_by_origin_2024-01_2026-06.csv"
    df = pd.read_csv(src, dtype={"period": str, "hs": str})
    return _finish("tw", pd.DataFrame({
        "period": df["period"].str.replace(".", "-", regex=False),
        "country": df["country"].str.strip(),
        "hs": df["hs"].astype(str),
        "weight_ton": df["weight_ton"],
        "value_kusd": df["value_kusd"],
    }))


def normalize_cn() -> pd.DataFrame:
    src = STAGING / "gacc_china" / "gacc_lng_imports_by_origin_2024-01_2026-06.csv"
    df = pd.read_csv(src, dtype={"period": str, "hs": str})
    return _finish("cn", pd.DataFrame({
        "period": df["period"].str.replace(".", "-", regex=False),
        "country": df["country"].str.strip(),
        "hs": df["hs"].astype(str),
        "weight_ton": df["weight_ton"],
        "value_kusd": df["value_usd"] / 1000.0,
    }))


def normalize_in() -> pd.DataFrame:
    src = STAGING / "india_tradestat" / "india_tradestat_lng271111_by_origin.csv"
    df = pd.read_csv(src, dtype={"period": str, "hs": str})
    usd = df[df["measure"] == "usd_million"].copy()
    # Months where the source has published nothing yet appear as all-zero
    # columns (e.g. 2026-06 at capture time); an all-zero month is "not yet
    # published", not "zero trade" -- drop it rather than freeze a fake zero.
    monthly_sum = usd.groupby("period")["value"].sum()
    published = monthly_sum[monthly_sum > 0].index
    usd = usd[usd["period"].isin(published)]
    usd = usd[usd["value"] > 0]
    return _finish("in", pd.DataFrame({
        "period": usd["period"].str.replace(".", "-", regex=False),
        "country": usd["country"].str.strip(),
        "hs": "271111",
        "weight_ton": float("nan"),
        "value_kusd": usd["value"] * 1000.0,   # US $ million -> thousand USD
    }))


def normalize_jp() -> pd.DataFrame:
    src = (
        PUBLIC_SNAPSHOT
        / "japan"
        / "japan_customs_lng271111_by_origin_2024_2026.csv"
    )
    df = pd.read_csv(src, dtype={"period": str, "country_code": str, "hs": str})
    published = df[df["publication_status"].eq("published")].copy()
    return _finish("jp", pd.DataFrame({
        "period": published["period"].str.replace(".", "-", regex=False),
        "country": published["country"].str.strip(),
        "hs": published["hs"].astype(str),
        "weight_ton": pd.to_numeric(published["weight_mt"], errors="coerce"),
        "value_kusd": float("nan"),
    }))


def copy_originals(dest_dir: Path) -> None:
    dest = dest_dir / "originals"
    dest.mkdir(parents=True, exist_ok=True)
    downloads = Path.home() / "Downloads"
    copies = [
        (downloads / "%E7%B6%9C%E5%90%88%E6%9F%A5%E8%A9%A2_20260717230939.csv",
         dest / "tw_original_big5.csv"),
        (downloads / "downloadData.csv", dest / "cn_original_2024.csv"),
        (downloads / "downloadData-3.csv", dest / "cn_original_2025.csv"),
        (downloads / "downloadData-2.csv", dest / "cn_original_2026.csv"),
        (STAGING / "india_tradestat" / "india_tradestat_lng271111_by_origin.csv",
         dest / "in_original_long.csv"),
        (PUBLIC_SNAPSHOT / "japan" / "estat_japan_import_hs271111_2024_raw.csv",
         dest / "jp_estat_2024_raw.csv"),
        (PUBLIC_SNAPSHOT / "japan" / "estat_japan_import_hs271111_2025_raw.csv",
         dest / "jp_estat_2025_raw.csv"),
        (PUBLIC_SNAPSHOT / "japan" / "estat_japan_import_hs271111_2026_raw.csv",
         dest / "jp_estat_2026_raw.csv"),
        (PUBLIC_SNAPSHOT / "japan" / "japan_customs_country_code_list.html",
         dest / "jp_country_code_list.html"),
        (PUBLIC_SNAPSHOT / "japan" / "estat_trade_search_hs271111.html",
         dest / "jp_estat_search_page1.html"),
        (PUBLIC_SNAPSHOT / "japan" / "estat_trade_search_hs271111_page2.html",
         dest / "jp_estat_search_page2.html"),
        (
            PUBLIC_SNAPSHOT
            / "japan"
            / "japan_customs_lng271111_by_origin_2024_2026.csv",
            dest / "jp_original_lng271111_with_jpy.csv",
        ),
    ]
    for src, target in copies:
        if target.exists():
            continue
        if not src.exists():
            print(f"WARNING: original not found, skipped: {src}")
            continue
        shutil.copy2(src, target)
        print(f"copied original -> {target.name}")
    (dest / "README.md").write_text(ORIGINALS_README, encoding="utf-8")


def main() -> int:
    dest_dir = config.path("importer_customs_dir")
    builders = {
        "kr": normalize_kr, "tw": normalize_tw,
        "cn": normalize_cn, "in": normalize_in, "jp": normalize_jp,
    }
    for unit, build in builders.items():
        frame = build()
        path = provenance.save_raw(
            frame,
            provider="importer_customs",
            variable=f"{unit}_lng_imports_by_origin",
            code=f"{unit}:by_origin",
            query={
                "capture_date": "2026-07-17",
                "period_range": [frame["period"].min(), frame["period"].max()],
                "measure": MEASURE_BY_UNIT[unit],
                "gulf_partners_present": sorted(
                    set(frame["country"]) & set(GULF_BY_UNIT[unit])
                ),
            },
            license_note=LICENSES[unit],
            filename=SNAPSHOT_FILES[unit],
        )
        print(f"{unit}: wrote {path} ({len(frame)} rows, "
              f"{frame['period'].min()}..{frame['period'].max()})")
    copy_originals(dest_dir)
    # Final validation through the provider's own loader.
    for unit in builders:
        load_by_origin(unit)
    print("all five snapshots load and validate through the provider")
    return 0


if __name__ == "__main__":
    sys.exit(main())
