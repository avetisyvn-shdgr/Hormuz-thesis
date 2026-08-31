"""Connectivity/auth smoke test for the Option D enrichment API keys.

Reads keys from the environment (.env via config), pings each provider with a
minimal request, and reports PASS / FAIL / SKIP. It NEVER prints a key value and
NEVER stores data -- this only confirms a key authenticates before adapters are
built on it. Not part of the analysis pipeline.

Run:  .venv/bin/python scripts/check_enrichment_keys.py
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from hormuz_throughput import config  # noqa: E402  (import triggers load_dotenv)

_ = config.settings

TIMEOUT = 30
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15) AppleWebKit/537.36"


def _get(url: str, headers: dict[str, str]) -> tuple[int, str]:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, **headers})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            return resp.status, resp.read(4000).decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read(2000).decode("utf-8", "replace")
    except Exception as exc:  # noqa: BLE001  network/DNS/timeout
        return -1, f"{type(exc).__name__}: {exc}"


def check_gie(key: str) -> tuple[str, str]:
    code, _body = _get("https://agsi.gie.eu/api?country=DE", {"x-key": key})
    if code == 200:
        return "PASS", "200 OK, key accepted"
    if code in (401, 403):
        return "FAIL", f"{code} -- key rejected"
    return "WARN", f"reachable but unexpected ({code})"


def check_estat(key: str) -> tuple[str, str]:
    url = (
        "https://api.e-stat.go.jp/rest/3.0/app/json/getStatsList"
        f"?appId={key}&limit=1&searchWord=LNG"
    )
    code, body = _get(url, {})
    if code != 200:
        return "WARN", f"HTTP {code}"
    try:
        status = json.loads(body)["GET_STATS_LIST"]["RESULT"]["STATUS"]
    except Exception:  # noqa: BLE001
        return "WARN", "200 but unparseable response"
    return ("PASS", "RESULT.STATUS=0, key accepted") if status == 0 else (
        "FAIL", f"RESULT.STATUS={status} -- appId rejected"
    )


def check_comtrade(key: str) -> tuple[str, str]:
    url = (
        "https://comtradeapi.un.org/data/v1/get/C/A/HS"
        "?reporterCode=392&period=2022&cmdCode=271111&flowCode=M&partnerCode=0"
    )
    code, _body = _get(url, {"Ocp-Apim-Subscription-Key": key})
    if code == 200:
        return "PASS", "200 OK, key accepted"
    if code in (401, 403):
        return "FAIL", f"{code} -- key rejected"
    return "WARN", f"reachable but unexpected ({code}); key may still be valid"


def check_kosis(key: str) -> tuple[str, str]:
    url = (
        "https://kosis.kr/openapi/statisticsList.do?method=getList"
        f"&apiKey={key}&vwCd=MT_ZTITLE&parentListId=A&format=json&jsonVD=Y"
    )
    code, body = _get(url, {})
    if code != 200:
        return "WARN", f"HTTP {code}"
    if '"err"' in body or "errMsg" in body:
        return "FAIL", "error response -- key rejected"
    return "PASS", "200 OK, key accepted"


CHECKS = {
    "GIE_API_KEY": ("GIE AGSI+/ALSI", check_gie),
    "ESTAT_API_KEY": ("Japan e-Stat", check_estat),
    "COMTRADE_API_KEY": ("UN Comtrade Plus", check_comtrade),
    "KOSIS_API_KEY": ("Korea KOSIS", check_kosis),
}


def main() -> int:
    print(f"{'KEY':<20}{'SOURCE':<22}{'RESULT':<8}DETAIL")
    print("-" * 78)
    any_fail = False
    for env_name, (label, fn) in CHECKS.items():
        key = os.environ.get(env_name, "").strip()
        if not key:
            print(f"{env_name:<20}{label:<22}{'SKIP':<8}no key set in .env")
            continue
        result, detail = fn(key)
        any_fail = any_fail or result == "FAIL"
        print(f"{env_name:<20}{label:<22}{result:<8}{detail}")
    print("-" * 78)
    print("PASS = key authenticates. WARN = reachable, inspect manually. "
          "SKIP = not set. No data was stored.")
    return 1 if any_fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
