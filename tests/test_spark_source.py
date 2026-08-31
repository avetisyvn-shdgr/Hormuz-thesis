"""Tests for the Spark freight-target adapter (sources/spark.py).

NO network, NO real credentials: every API response is mocked. These lock in
the adapter's contract — require credentials, fail loudly, never fabricate a
freight value, enforce the (date, value) shape, and refuse a silently
truncated history. Run: pytest -q
"""
import types

import pandas as pd
import pytest


from hormuz_throughput.sources import spark as spark_mod
from hormuz_throughput.sources.spark import SparkSource, business_day_coverage


def _release(date: str, price):
    """One price-release dict, matching the real Spark response shape. `price`
    is the raw usdPerDay 'spark' string, or None to simulate a missing one."""
    return {
        "id": int(date.replace("-", "")),
        "contractId": "spark30s",
        "releaseDate": date,
        "data": [
            {
                "revisionNumber": 0,
                "dataPoints": [
                    {
                        "index": 0,
                        "deliveryPeriod": {"type": "days", "startAt": date,
                                           "name": "SparkS"},
                        "derivedPrices": {
                            "usdPerDay": {"spark": price, "sparkMin": "0",
                                          "sparkMax": "0"},
                            "usdPerMMBtu": {"spark": "0.5"},
                        },
                    }
                ],
            }
        ],
    }


class _FakeResp:
    def __init__(self, payload, status=200):
        self._payload = payload
        self.status_code = status

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise spark_mod.requests.HTTPError(f"HTTP {self.status_code}")


def _patch_releases(monkeypatch, releases):
    """Make fetch() use a fixed access token and a single mocked page of
    releases, bypassing all HTTP."""
    monkeypatch.setattr(SparkSource, "_get_access_token",
                        lambda self, cid, sec: "tok")
    monkeypatch.setattr(SparkSource, "_get_json",
                        lambda self, uri, token: {"data": releases})
    monkeypatch.setenv("SPARK_CLIENT_ID", "id")
    monkeypatch.setenv("SPARK_CLIENT_SECRET", "secret")


def test_missing_credentials_fails_loudly(monkeypatch):
    monkeypatch.delenv("SPARK_CLIENT_ID", raising=False)
    monkeypatch.delenv("SPARK_CLIENT_SECRET", raising=False)
    with pytest.raises(RuntimeError, match="SPARK_CLIENT_ID"):
        SparkSource().fetch("Spark30S", "2026-02-01", "2026-03-01")


def test_unsupported_code_rejected():
    with pytest.raises(ValueError, match="spot targets"):
        SparkSource().fetch("Spark30FFA", "2026-02-01", "2026-03-01")


def test_fetch_returns_tidy_contract(monkeypatch):
    releases = [
        _release("2026-03-30", "40000"),
        _release("2026-02-03", "31000"),
        _release("2026-02-02", "30000"),
        _release("2026-01-10", "12000"),
    ]
    _patch_releases(monkeypatch, releases)

    out = SparkSource().fetch("Spark30S", "2026-02-02", "2026-03-31")

    assert list(out.columns) == ["date", "value"]
    assert str(out["value"].dtype) == "float64"
    assert list(out["date"]) == [pd.Timestamp("2026-02-02"),
                                 pd.Timestamp("2026-02-03"),
                                 pd.Timestamp("2026-03-30")]
    assert out["value"].tolist() == [30000.0, 31000.0, 40000.0]


def test_code_maps_case_insensitively(monkeypatch):
    _patch_releases(monkeypatch, [_release("2026-02-01", "30000")])
    out = SparkSource().fetch("spark25s", "2026-02-01", "2026-02-28")
    assert out["value"].tolist() == [30000.0]


def test_weekend_window_start_is_not_treated_as_truncation(monkeypatch):
    releases = [_release("2022-01-04", "31000"),
                _release("2022-01-03", "30000")]
    _patch_releases(monkeypatch, releases)
    out = SparkSource().fetch("Spark30S", "2022-01-01", "2022-01-07")
    assert out["date"].min() == pd.Timestamp("2022-01-03")


def test_business_day_coverage_tolerates_holiday_sized_gap():
    dates = pd.bdate_range("2026-01-01", "2026-01-31").delete([4])
    coverage = business_day_coverage(dates, "2026-01-01", "2026-01-31")
    assert coverage["usable_coverage"] is True
    assert coverage["longest_missing_business_day_run"] == 1


def test_business_day_coverage_rejects_recent_trial_slice():
    dates = pd.bdate_range("2026-01-20", "2026-01-31")
    coverage = business_day_coverage(dates, "2022-01-01", "2026-01-31")
    assert coverage["usable_coverage"] is False
    assert coverage["leading_missing_business_days"] > 5


def test_null_assessment_is_skipped_not_imputed(monkeypatch):
    releases = [
        _release("2026-02-03", None),
        _release("2026-02-02", "30000"),
    ]
    _patch_releases(monkeypatch, releases)
    out = SparkSource().fetch("Spark30S", "2026-02-02", "2026-02-28")
    assert out["date"].tolist() == [pd.Timestamp("2026-02-02")]
    assert out["value"].tolist() == [30000.0]


def test_truncated_history_fails_loudly(monkeypatch):
    releases = [_release("2026-02-06", "31000"), _release("2026-02-05", "30000")]
    _patch_releases(monkeypatch, releases)
    with pytest.raises(ValueError, match="starts at"):
        SparkSource().fetch("Spark30S", "2026-02-01", "2026-02-28")


def test_no_releases_in_window_raises(monkeypatch):
    _patch_releases(monkeypatch, [])
    with pytest.raises(ValueError, match="no price releases"):
        SparkSource().fetch("Spark30S", "2026-02-01", "2026-02-28")


def test_get_access_token_parses_token(monkeypatch):
    fake = types.SimpleNamespace(
        post=lambda *a, **k: _FakeResp({"accessToken": "abc123", "expiresIn": 1799}),
        HTTPError=spark_mod.requests.HTTPError,
    )
    monkeypatch.setattr(spark_mod, "requests", fake)
    assert SparkSource()._get_access_token("id", "secret") == "abc123"


def test_get_access_token_without_token_raises(monkeypatch):
    fake = types.SimpleNamespace(
        post=lambda *a, **k: _FakeResp({"expiresIn": 1799}),
        HTTPError=spark_mod.requests.HTTPError,
    )
    monkeypatch.setattr(spark_mod, "requests", fake)
    with pytest.raises(ValueError, match="no accessToken"):
        SparkSource()._get_access_token("id", "secret")


def test_get_json_returns_payload(monkeypatch):
    fake = types.SimpleNamespace(
        get=lambda *a, **k: _FakeResp({"data": [{"releaseDate": "2026-02-02"}]}),
        HTTPError=spark_mod.requests.HTTPError,
    )
    monkeypatch.setattr(spark_mod, "requests", fake)
    payload = SparkSource()._get_json("/v1.0/contracts/spark30s/price-releases/", "tok")
    assert payload["data"][0]["releaseDate"] == "2026-02-02"
