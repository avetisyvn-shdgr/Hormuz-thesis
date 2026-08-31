import json
from pathlib import Path

import pandas as pd

from hormuz_throughput.terminal_matching import (
    build_terminal_crosswalk,
    haversine_km,
    load_operating_terminals,
)


def test_haversine_zero_and_known_scale():
    assert haversine_km(0, 0, 0, 0) == 0
    assert 110 < haversine_km(0, 0, 1, 0) < 112


def test_loader_keeps_operating_lng_and_collapses_units(tmp_path: Path):
    base = {
        "ProjectID": "t1", "TerminalName": "A", "FacilityType": "import",
        "Country/Area": "Italy", "Latitude": 45, "Longitude": 12,
        "Status": "operating", "TotImportLNGTerminalCapacityinMtpa": 5,
        "Wiki": "source",
    }
    payload = {"features": [
        {"properties": base},
        {"properties": {**base, "UnitID": "second"}},
        {"properties": {**base, "ProjectID": "t2", "Status": "proposed"}},
    ]}
    path = tmp_path / "terminals.geojson"
    path.write_text(json.dumps(payload))
    result = load_operating_terminals(path)
    assert len(result) == 1
    assert result.loc[0, "terminal_role"] == "regasification"


def test_crosswalk_requires_distance_country_and_capacity():
    visits = pd.DataFrame({
        "port_id": ["near", "wrong-country", "far"],
        "port_name": ["A", "B", "C"],
        "port_country": ["ITA", "MYS", "ITA"],
        "lat": [45.01, 45.01, 40.0],
        "lon": [12.01, 12.01, 12.0],
    })
    terminals = pd.DataFrame({
        "project_id": ["t1"], "terminal_name": ["Terminal"],
        "terminal_role": ["regasification"], "country": ["Italy"],
        "terminal_lat": [45.0], "terminal_lon": [12.0],
        "capacity_mtpa": [5.0], "source": ["source"],
    })
    result = build_terminal_crosswalk(
        visits, terminals, max_distance_km=30, min_capacity_mtpa=1,
    ).set_index("port_id")
    assert result.loc["near", "match_status"] == "provisional_spatial_match"
    assert result.loc["wrong-country", "match_status"] == "country_mismatch"
    assert result.loc["far", "match_status"] == "outside_distance_threshold"
