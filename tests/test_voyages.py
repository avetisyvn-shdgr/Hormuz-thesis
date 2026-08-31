import pandas as pd

from hormuz_throughput.voyages import candidate_voyage_endpoints, endpoint_summary


def test_candidate_voyages_collapse_same_terminal_and_mark_censoring():
    visits = pd.DataFrame({
        "event_id": ["e1", "e2", "e3", "e4"],
        "vessel_id": ["v1"] * 4,
        "sample_period": ["pre"] * 4,
        "port_id": ["p_export", "p_export_2", "p_import", "p_export"],
        "start": pd.date_range("2025-01-01", periods=4, tz="UTC"),
        "end": pd.date_range("2025-01-02", periods=4, tz="UTC"),
    })
    identities = pd.DataFrame({"vessel_id": ["v1"], "imo": ["1234567"]})
    terminals = pd.DataFrame({
        "port_id": ["p_export", "p_export_2", "p_import"],
        "project_id": ["export", "export", "import"],
        "terminal_name": ["Export", "Export", "Import"],
        "terminal_role": ["liquefaction", "liquefaction", "regasification"],
        "terminal_lat": [1, 1, 2], "terminal_lon": [1, 1, 2],
    })
    result = candidate_voyage_endpoints(visits, identities, terminals)
    assert len(result) == 2
    assert result.loc[0, "endpoint_status"] == (
        "resolved_liquefaction_to_regasification"
    )
    assert result.loc[1, "endpoint_status"] == "right_censored"


def test_endpoint_summary_excludes_right_censoring_from_denominator():
    voyages = pd.DataFrame({
        "sample_period": ["pre", "pre"],
        "endpoint_status": [
            "resolved_liquefaction_to_regasification", "right_censored"
        ],
    })
    result = endpoint_summary(voyages, threshold=0.9)
    assert result["endpoint_resolution_rate"] == 1.0
    assert result["passes_threshold"] is True
    assert result["by_period"]["pre"]["right_censored_calls"] == 1
