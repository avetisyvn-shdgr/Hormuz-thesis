import json

import pandas as pd


import fetch_wto_hormuz_lng  # noqa: E402


class _Response:
    content = (
        b"voy_load_date,voy_intake_index\n"
        b"2025-01-02,101.5\n"
        b"2025-01-01,100.0\n"
    )

    def raise_for_status(self) -> None:
        return None


def test_fetch_wto_hormuz_lng_logs_provenance(tmp_path, monkeypatch):
    settings = {
        "paths": {
            "data_raw": "data/raw",
            "provenance_log": "data/raw/provenance.jsonl",
            "wto_hormuz_lng_csv": "data/raw/wto_hormuz/voy_intake_index_lng_export.csv",
        },
        "study_window": {
            "full_start": "2022-01-01",
            "full_end": "2026-07-07",
        },
    }
    registry = {
        "wto_hormuz_lng_outbound_index": {
            "role": "mechanism",
            "primary": {
                "provider": "wto_hormuz",
                "code": "lng_outbound_volume_index",
                "license": "WTO Strait of Hormuz Trade Tracker",
            },
        }
    }

    monkeypatch.setattr(fetch_wto_hormuz_lng.config, "ROOT", tmp_path)
    monkeypatch.setattr(fetch_wto_hormuz_lng.config, "settings", lambda: settings)
    monkeypatch.setattr(fetch_wto_hormuz_lng.config, "registry", lambda: registry)
    monkeypatch.setattr(
        fetch_wto_hormuz_lng.requests,
        "get",
        lambda url, timeout: _Response(),
    )

    fetch_wto_hormuz_lng.main()

    raw_snapshot = tmp_path / settings["paths"]["wto_hormuz_lng_csv"]
    assert raw_snapshot.read_bytes() == _Response.content

    provenance_log = tmp_path / settings["paths"]["provenance_log"]
    records = [json.loads(line) for line in provenance_log.read_text().splitlines()]
    assert len(records) == 1
    record = records[0]
    assert record["variable"] == "wto_hormuz_lng_outbound_index"
    assert record["provider"] == "wto_hormuz"
    assert record["code"] == "lng_outbound_volume_index"
    assert record["query"]["source_url"] == fetch_wto_hormuz_lng.URL
    assert record["columns"] == ["date", "value"]
    assert record["registry_variables"] == [
        "wto_hormuz_lng_outbound_index"
    ]
    assert record["source_payload_status"] == "preserved"
    assert record["source_payloads"][0]["file"] == str(
        raw_snapshot.relative_to(tmp_path)
    )

    provenance_frame = pd.read_csv(tmp_path / record["file"])
    assert provenance_frame["date"].tolist() == ["2025-01-01", "2025-01-02"]
    assert provenance_frame["value"].tolist() == [100.0, 101.5]
