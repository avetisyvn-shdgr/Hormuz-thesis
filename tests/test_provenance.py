import pandas as pd

from lngfreight import config, provenance


def test_identical_raw_save_does_not_duplicate_provenance(tmp_path, monkeypatch):
    settings = {
        "paths": {
            "data_raw": "data/raw",
            "provenance_log": "data/raw/provenance.jsonl",
        }
    }
    monkeypatch.setattr(config, "ROOT", tmp_path)
    monkeypatch.setattr(config, "settings", lambda: settings)
    frame = pd.DataFrame({"value": [1, 2]})
    kwargs = {
        "provider": "example",
        "variable": "series",
        "code": "v1",
        "query": {"window": "fixed"},
        "license_note": "test",
    }

    provenance.save_raw(frame, **kwargs)
    provenance.save_raw(frame, **kwargs)

    lines = (tmp_path / "data/raw/provenance.jsonl").read_text().splitlines()
    assert len(lines) == 1
