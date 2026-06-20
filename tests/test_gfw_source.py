import pandas as pd

from lngfreight.registry import (
    get_gfw_port_visits,
    get_gfw_vessel_identities,
    get_gfw_vessel_identities_batched,
)
from lngfreight.sources.gfw import (
    GFWClient,
    exact_imo_vessel_ids,
    normalize_port_visits,
)


class _Response:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class _Session:
    def __init__(self, payload):
        self.payload = payload
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return _Response(self.payload)


def _entry(imo: str, vessel_id: str) -> dict:
    return {
        "registryInfo": [{"imo": imo}],
        "selfReportedInfo": [],
        "combinedSourcesInfo": [{"vesselId": vessel_id}],
    }


def test_client_uses_bearer_auth_without_putting_token_in_query():
    session = _Session({"entries": [_entry("9337705", "v1")]})
    client = GFWClient(token="secret", session=session)
    assert client.search_imo("9337705")[0]["registryInfo"][0]["imo"] == "9337705"
    _, kwargs = session.calls[0]
    assert kwargs["headers"] == {"Authorization": "Bearer secret"}
    assert "secret" not in kwargs["params"].values()


def test_batch_search_uses_where_and_rejects_truncation():
    session = _Session({"entries": [_entry("9337705", "v1")], "total": 1})
    client = GFWClient(token="secret", session=session)
    assert len(client.search_imos(["9337705", "9337717"])) == 1
    assert " OR " in session.calls[0][1]["params"]["where"]


def test_exact_match_rejects_ranked_near_match_and_keeps_multiple_ids():
    entries = [
        _entry("0000000", "wrong"),
        _entry("9337705", "new-id"),
        _entry("9337705", "old-id"),
    ]
    assert exact_imo_vessel_ids(entries, "9337705") == ["new-id", "old-id"]


def test_registry_returns_only_exact_unique_identity_rows():
    class Client:
        def search_imo(self, imo):
            return [_entry(imo, f"id-{imo}"), _entry(imo, f"id-{imo}")]

    roster = pd.DataFrame({"imo": ["9337705", "9337717"]})
    result = get_gfw_vessel_identities(roster, client=Client())
    assert result.to_dict("records") == [
        {"imo": "9337705", "vessel_id": "id-9337705"},
        {"imo": "9337717", "vessel_id": "id-9337717"},
    ]


def test_batched_registry_matches_each_imo_against_shared_entries():
    class Client:
        def search_imos(self, imos):
            return [_entry(imo, f"id-{imo}") for imo in imos]

    roster = pd.DataFrame({"imo": ["9337705", "9337717"]})
    result = get_gfw_vessel_identities_batched(roster, client=Client())
    assert result["vessel_id"].tolist() == ["id-9337705", "id-9337717"]


def _event(event_id="e1"):
    return {
        "id": event_id,
        "start": "2025-03-01T00:00:00Z",
        "end": "2025-03-02T00:00:00Z",
        "position": {"lat": 1.0, "lon": 2.0},
        "vessel": {"id": "v1"},
        "port_visit": {
            "confidence": 4,
            "intermediateAnchorage": {
                "anchorageId": "p1", "name": "Port", "flag": "QAT",
                "lat": 3.0, "lon": 4.0, "atDock": True,
            },
        },
    }


def test_port_visit_pagination_and_array_parameters():
    class Session:
        def __init__(self):
            self.calls = []

        def get(self, url, **kwargs):
            self.calls.append(kwargs["params"])
            offset = kwargs["params"]["offset"]
            payload = (
                {"entries": [_event("e1")], "nextOffset": 1}
                if offset == 0
                else {"entries": [_event("e2")], "nextOffset": None}
            )
            return _Response(payload)

    session = Session()
    events = GFWClient(token="secret", session=session).port_visits(
        ["v2", "v1"], "2025-01-01", "2025-02-01"
    )
    assert [event["id"] for event in events] == ["e1", "e2"]
    assert session.calls[0]["vessels[0]"] == "v1"
    assert session.calls[0]["vessels[1]"] == "v2"
    assert session.calls[1]["offset"] == 1


def test_normalize_port_visit_prefers_intermediate_anchorage():
    row = normalize_port_visits([_event()], "pre")[0]
    assert row["port_id"] == "p1"
    assert row["lat"] == 3.0
    assert row["confidence"] == 4
    assert row["sample_period"] == "pre"


def test_port_visit_registry_deduplicates_events():
    class Client:
        def port_visits(self, vessel_ids, start, end):
            return [_event(), _event()]

    result = get_gfw_port_visits(
        ["v1"], {"pre": ("2025-01-01", "2025-02-01")}, client=Client()
    )
    assert len(result) == 1
    assert result.loc[0, "sample_period"] == "pre"
