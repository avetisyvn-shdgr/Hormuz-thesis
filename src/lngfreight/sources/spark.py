"""Spark Commodities API provider — the PRIMARY freight-target backend.

Supplies the proposal's dependent variable: the daily Spark25S (Pacific) and
Spark30S (Atlantic) LNG spot-freight assessments, in USD/day. This is the real
assessment, not a proxy.

Access status (see docs/TARGET_ACCESS_STATUS.md, decision 2026-06-14):
  - Spark is PRIMARY. Full history needs a Spark subscription; a free-trial /
    academic OAuth2 client may cover the study window — this is being verified.
  - This adapter REQUIRES OAuth2 client credentials and FAILS LOUDLY without
    them. It never fabricates, interpolates or synthesises freight values.
  - Because the registry still marks the spark* targets `status: unavailable`,
    get_variable() will NOT route here yet (it falls back to the proxy, which
    raises). Once access is confirmed, flip those targets to `status: primary`
    in config/sources.yaml and this adapter activates with no other change.

Auth + response shape are taken verbatim from Spark's official sample code
(github.com/spark-commodities/api-code-samples, python3/spark_price_releases.py
and the contracts notebook), not guessed.

Credentials (create an OAuth2 client at
https://app.sparkcommodities.com/freight/data-integrations/api), then in .env:
    SPARK_CLIENT_ID=...
    SPARK_CLIENT_SECRET=...
"""
from __future__ import annotations

import json
from base64 import b64encode

import requests
import pandas as pd

from .base import BaseSource
from .. import config

_BASE = "https://api.sparkcommodities.com"
_TOKEN_URI = "/oauth/token/"
# Only the two SPOT freight assessments are supported as targets. The registry
# `code` (e.g. "Spark30S") maps case-insensitively to the API ticker.
_SUPPORTED = {"spark25s", "spark30s"}
# OAuth2 scopes needed for the freight price endpoints (per Spark sample).
_SCOPES = "read:lng-freight-prices,read:routes"
# derivedPrices unit carrying the headline USD/day freight rate, and the
# assessment field within it (vs sparkMin/sparkMax/portfolioPlayer/shipOwner).
_UNIT = "usdPerDay"
_ASSESSMENT = "spark"
# Pagination: price-releases are returned newest-first; page until we pass the
# requested start or the server runs out. The cap is a runaway-loop guard only.
_PAGE_LIMIT = 1000
_MAX_PAGES = 50
MAX_BOUNDARY_GAP_BUSINESS_DAYS = 2
MAX_INTERNAL_GAP_BUSINESS_DAYS = 5


def business_day_coverage(
    dates: pd.Series | pd.DatetimeIndex,
    start: str | pd.Timestamp,
    end: str | pd.Timestamp,
) -> dict:
    """Summarize release coverage without assuming weekend observations.

    Spark spot assessments are released on business days. Normal holidays may
    create short gaps, so access is considered usable when at least 90% of
    expected business days are present and no leading, trailing, or internal
    boundary gap exceeds two business days and no internal gap exceeds five.
    This detects a trial-limited recent slice
    without rejecting an otherwise complete history over a holiday.
    """
    start_ts, end_ts = pd.Timestamp(start), pd.Timestamp(end)
    expected = pd.bdate_range(start_ts, end_ts)
    observed = pd.DatetimeIndex(pd.to_datetime(dates)).normalize().unique().sort_values()
    observed = observed[(observed >= start_ts) & (observed <= end_ts)]
    missing = expected.difference(observed)

    missing_set = set(missing)
    longest_gap = current_gap = 0
    for dt in expected:
        if dt in missing_set:
            current_gap += 1
            longest_gap = max(longest_gap, current_gap)
        else:
            current_gap = 0

    if len(observed):
        leading_gap = int((expected < observed.min()).sum())
        trailing_gap = int((expected > observed.max()).sum())
    else:
        leading_gap = trailing_gap = int(len(expected))

    expected_count = int(len(expected))
    observed_count = int(len(expected.intersection(observed)))
    coverage_ratio = observed_count / expected_count if expected_count else 0.0
    usable = (
        expected_count > 0
        and coverage_ratio >= 0.90
        and longest_gap <= MAX_INTERNAL_GAP_BUSINESS_DAYS
        and leading_gap <= MAX_BOUNDARY_GAP_BUSINESS_DAYS
        and trailing_gap <= MAX_BOUNDARY_GAP_BUSINESS_DAYS
    )
    return {
        "expected_business_days": expected_count,
        "observed_business_days": observed_count,
        "coverage_ratio": coverage_ratio,
        "missing_business_days": missing,
        "longest_missing_business_day_run": longest_gap,
        "leading_missing_business_days": leading_gap,
        "trailing_missing_business_days": trailing_gap,
        "usable_coverage": usable,
    }


class SparkSource(BaseSource):
    name = "spark"

    def fetch(self, code: str, start: str, end: str) -> pd.DataFrame:
        ticker = code.strip().lower()
        if ticker not in _SUPPORTED:
            raise ValueError(
                f"SparkSource supports only the spot targets {sorted(_SUPPORTED)} "
                f"(got code {code!r}). Forward/FFA tickers are out of scope for the "
                f"dependent variable."
            )

        # Credentials are mandatory. config.api_key raises a clear, actionable
        # RuntimeError if either is absent — this is the fail-loud contract.
        client_id = config.api_key("SPARK_CLIENT_ID")
        client_secret = config.api_key("SPARK_CLIENT_SECRET")

        token = self._get_access_token(client_id, client_secret)
        rows = self._collect_spot_prices(ticker, token, start, end)

        if not rows:
            raise ValueError(
                f"Spark returned no price releases for {ticker} in [{start}, {end}]."
            )

        out = pd.DataFrame(rows, columns=["date", "value"])
        out["date"] = pd.to_datetime(out["date"])
        out["value"] = pd.to_numeric(out["value"], errors="coerce")
        out = out.loc[
            (out["date"] >= pd.Timestamp(start)) & (out["date"] <= pd.Timestamp(end))
        ]
        if out.empty:
            raise ValueError(
                f"Spark returned releases for {ticker} but none inside "
                f"[{start}, {end}]."
            )

        # A weekend/holiday at the literal boundary is not truncation. Refuse
        # only when more than a normal holiday-length business-day prefix is
        # absent; the full access probe performs the stricter coverage audit.
        coverage = business_day_coverage(out["date"], start, end)
        if coverage["leading_missing_business_days"] > MAX_BOUNDARY_GAP_BUSINESS_DAYS:
            earliest = out["date"].min()
            raise ValueError(
                f"Spark history for {ticker} starts at {earliest.date()}, after the "
                f"requested business-day boundary for {start} "
                f"({coverage['leading_missing_business_days']} missing business days). "
                f"The free-trial/academic tier likely "
                f"truncates history — verify your subscription depth (see "
                f"docs/TARGET_ACCESS_STATUS.md) or request a later start."
            )

        return self._validate(out)

    # -- HTTP boundary (isolated so tests can mock requests.post/.get) --------

    def _get_access_token(self, client_id: str, client_secret: str) -> str:
        """OAuth2 client-credentials grant. Returns a bearer access token."""
        payload = f"{client_id}:{client_secret}".encode()
        headers = {
            "Authorization": b64encode(payload).decode(),
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        body = {"grantType": "clientCredentials", "scopes": _SCOPES}
        resp = requests.post(
            _BASE + _TOKEN_URI, data=json.dumps(body), headers=headers, timeout=60
        )
        resp.raise_for_status()
        content = resp.json()
        token = content.get("accessToken")
        if not token:
            raise ValueError(
                "Spark auth succeeded but no accessToken was returned. "
                f"Response keys: {sorted(content)}."
            )
        return token

    def _get_json(self, uri: str, token: str) -> dict:
        headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
        resp = requests.get(_BASE + uri, headers=headers, timeout=60)
        resp.raise_for_status()
        return resp.json()

    # -- data extraction ------------------------------------------------------

    def _collect_spot_prices(
        self, ticker: str, token: str, start: str, end: str
    ) -> list[tuple[str, str]]:
        """Page through price releases (newest-first), returning (releaseDate,
        usdPerDay spark) tuples. Stops once a page predates `start` or the server
        returns a short/empty page. Releases with a null assessment are skipped,
        never imputed."""
        start_ts = pd.Timestamp(start)
        rows: list[tuple[str, str]] = []
        offset = 0
        for _ in range(_MAX_PAGES):
            uri = (
                f"/v1.0/contracts/{ticker}/price-releases/"
                f"?limit={_PAGE_LIMIT}&offset={offset}"
            )
            releases = self._get_json(uri, token).get("data", [])
            if not releases:
                break

            page_min = None
            for release in releases:
                rel_date = release["releaseDate"]
                price = self._extract_spot_price(release)
                if price is not None:
                    rows.append((rel_date, price))
                ts = pd.Timestamp(rel_date)
                page_min = ts if page_min is None else min(page_min, ts)

            offset += len(releases)
            # Newest-first: once a whole page predates the window, or the page is
            # short (no more data), stop.
            if (page_min is not None and page_min < start_ts) or len(releases) < _PAGE_LIMIT:
                break
        return rows

    @staticmethod
    def _extract_spot_price(release: dict) -> str | None:
        """Pull the USD/day spark assessment from one price release. Returns the
        raw string (cast downstream) or None if the field is absent/null. Spot
        contracts carry a single data point (the 'S' delivery period)."""
        data = release.get("data") or []
        if not data:
            return None
        data_points = data[0].get("dataPoints") or []
        if not data_points:
            return None
        derived = data_points[0].get("derivedPrices", {})
        return derived.get(_UNIT, {}).get(_ASSESSMENT)
