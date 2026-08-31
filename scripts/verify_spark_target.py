"""Verify what the Spark freight-target API actually returns for THIS account.

The single open question on the dependent variable (see docs/TARGET_ACCESS_STATUS.md)
is empirical: does your Spark OAuth2 client return Spark25S / Spark30S across the
thesis study window at daily granularity, or only the trial-limited recent slice?
This script answers it with real data and reports, per contract:

    earliest date, latest date, observation count, missing dates within the
    window, and whether the study window is FULLY COVERED.

Discipline:
  * Uses the real adapter (`SparkSource`) for auth + data collection.
  * Deliberately calls the adapter's collection layer rather than `fetch()`:
    `fetch()` raises on a truncated history (correct for the pipeline), but here
    we must *observe and report* a truncated range, not abort on it.
  * Does NOT write to data/raw unless you pass --save-raw.
  * Exits non-zero and prints a clear FAIL if the window is not fully covered
    (e.g. the account only exposes the ~2-week trial history).

Run from repo root, with SPARK_CLIENT_ID / SPARK_CLIENT_SECRET in .env:
    python scripts/verify_spark_target.py
    python scripts/verify_spark_target.py --save-raw     # also persist raw pulls
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from hormuz_throughput import config, provenance
from hormuz_throughput.sources.spark import (
    MAX_BOUNDARY_GAP_BUSINESS_DAYS,
    SparkSource,
    business_day_coverage,
)

TRIAL_SPAN_DAYS = 21


def _write_report(path: str, payload: dict) -> None:
    report_path = Path(path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"\nWrote access report -> {report_path}")


def _frame(rows: list[tuple[str, str]]) -> pd.DataFrame:
    """(date_str, price_str) tuples -> tidy, sorted, deduped (date, value)."""
    if not rows:
        return pd.DataFrame(columns=["date", "value"])
    df = pd.DataFrame(rows, columns=["date", "value"])
    df["date"] = pd.to_datetime(df["date"])
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df = (df.dropna(subset=["value"])
            .drop_duplicates(subset="date")
            .sort_values("date")
            .reset_index(drop=True))
    return df


def _report_contract(name: str, code: str, df: pd.DataFrame,
                     start: pd.Timestamp, end: pd.Timestamp) -> dict:
    """Print and return diagnostics for one contract."""
    print(f"\n=== {name}  (code {code}) ===")
    if df.empty:
        print("  NO DATA returned. Check the contract is in your subscription "
              "scope (read:lng-freight-prices) and the ticker is correct.")
        return {"name": name, "code": code, "usable_coverage": False,
                "error": "no_data"}

    earliest, latest = df["date"].min(), df["date"].max()
    in_window = df[(df["date"] >= start) & (df["date"] <= end)]
    span_days = (latest - earliest).days

    print(f"  earliest available : {earliest.date()}")
    print(f"  latest available   : {latest.date()}")
    print(f"  observations (all) : {len(df)}   (within window: {len(in_window)})")

    coverage = business_day_coverage(in_window["date"], start, end)
    missing = coverage["missing_business_days"]
    print(f"  expected business days: {coverage['expected_business_days']}")
    print(f"  observed business days: {coverage['observed_business_days']}")
    print(f"  business-day coverage : {coverage['coverage_ratio']:.1%}")
    print(f"  missing business days : {len(missing)}")
    if len(missing):
        sample = ", ".join(d.date().isoformat() for d in missing[:10])
        more = " ..." if len(missing) > 10 else ""
        print(f"    e.g. {sample}{more}   (includes public holidays)")

    leading = coverage["leading_missing_business_days"]
    trailing = coverage["trailing_missing_business_days"]
    longest = coverage["longest_missing_business_day_run"]
    if leading > MAX_BOUNDARY_GAP_BUSINESS_DAYS and span_days <= TRIAL_SPAN_DAYS:
        print(f"  >> TRIAL-LIMITED: only a {span_days}-day recent slice is exposed, "
              f"starting {earliest.date()}. This account does NOT have historical "
              f"access to the study window.")
    elif leading > MAX_BOUNDARY_GAP_BUSINESS_DAYS:
        print(f"  >> TRUNCATED: history starts {earliest.date()}, after the study "
              f"start {start.date()}.")
    if trailing > MAX_BOUNDARY_GAP_BUSINESS_DAYS:
        print(f"  >> latest data {latest.date()} does not reach window end "
              f"{end.date()}.")

    print(f"  longest missing business-day run: {longest}")
    covered = bool(coverage["usable_coverage"])
    print(f"  STUDY WINDOW USABLY COVERED: {'YES' if covered else 'NO'}")
    return {
        "name": name,
        "code": code,
        "earliest_available": earliest.date().isoformat(),
        "latest_available": latest.date().isoformat(),
        "observations_all": int(len(df)),
        "observations_in_window": int(len(in_window)),
        "expected_business_days": coverage["expected_business_days"],
        "observed_business_days": coverage["observed_business_days"],
        "coverage_ratio": coverage["coverage_ratio"],
        "missing_business_days": [d.date().isoformat() for d in missing],
        "longest_missing_business_day_run": longest,
        "leading_missing_business_days": leading,
        "trailing_missing_business_days": trailing,
        "usable_coverage": covered,
    }


def main(save_raw: bool = False, report_json: str | None = None) -> int:
    settings = config.settings()
    win = settings["study_window"]
    start, end = pd.Timestamp(win["full_start"]), pd.Timestamp(win["full_end"])
    start_s, end_s = win["full_start"], win["full_end"]

    reg = config.registry()
    targets = {n: s for n, s in reg.items() if s.get("role") == "target"}
    if not targets:
        print("No role=target variables found in config/sources.yaml.")
        return 2

    print(f">>>> Verifying Spark freight targets for [{start_s}, {end_s}]")
    if save_raw:
        print(">>>> --save-raw set: raw pulls WILL be written to data/raw/.")

    src = SparkSource()
    try:
        client_id = config.api_key("SPARK_CLIENT_ID")
        client_secret = config.api_key("SPARK_CLIENT_SECRET")
        token = src._get_access_token(client_id, client_secret)
    except Exception as exc:  # noqa: BLE001 - turn into a clear operator message
        print(f"\nCannot authenticate to Spark: {type(exc).__name__}: {exc}")
        print("Add SPARK_CLIENT_ID and SPARK_CLIENT_SECRET to .env (create an "
              "OAuth2 client at "
              "https://app.sparkcommodities.com/freight/data-integrations/api).")
        if report_json:
            _write_report(report_json, {
                "window_start": start_s,
                "window_end": end_s,
                "authenticated": False,
                "all_targets_usable": False,
                "error": f"{type(exc).__name__}: {exc}",
            })
        return 2
    print(">>>> Authenticated.")

    all_covered = True
    reports = []
    for name, spec in targets.items():
        code = spec["primary"]["code"]
        ticker = code.strip().lower()
        try:
            rows = src._collect_spot_prices(ticker, token, start_s, end_s)
        except Exception as exc:  # noqa: BLE001 - report, don't crash the probe
            print(f"\n=== {name}  (code {code}) ===")
            print(f"  ERROR fetching: {type(exc).__name__}: {exc}")
            all_covered = False
            reports.append({"name": name, "code": code,
                            "usable_coverage": False,
                            "error": f"{type(exc).__name__}: {exc}"})
            continue

        df = _frame(rows)
        report = _report_contract(name, code, df, start, end)
        reports.append(report)
        covered = report["usable_coverage"]
        all_covered = all_covered and covered

        if save_raw and not df.empty:
            in_window = df[(df["date"] >= start) & (df["date"] <= end)]
            path = provenance.save_raw(
                in_window,
                provider="spark",
                variable=name,
                code=code,
                query={"start": start_s, "end": end_s, "channel": "primary",
                       "role": "target", "probe": "verify_spark_target"},
                license_note=spec["primary"].get("license", "unspecified"),
            )
            print(f"  saved raw -> {path.relative_to(config.ROOT)}")

    if report_json:
        _write_report(report_json, {
            "window_start": start_s,
            "window_end": end_s,
            "authenticated": True,
            "contracts": reports,
            "all_targets_usable": all_covered,
        })

    print("\n" + "=" * 60)
    if all_covered:
        print("VERDICT: PASS — both targets fully cover the study window.")
        print("Next: flip the spark* targets to `status: primary` in "
              "config/sources.yaml to activate them in the pipeline.")
        return 0
    print("VERDICT: FAIL — at least one target does not fully cover the study "
          "window (see notes above). Do NOT flip to `status: primary` yet.")
    return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--save-raw", action="store_true",
                        help="persist the fetched in-window data to data/raw/ "
                             "(off by default).")
    parser.add_argument("--report-json",
                        help="write non-price coverage diagnostics as JSON")
    args = parser.parse_args()
    sys.exit(main(save_raw=args.save_raw, report_json=args.report_json))
