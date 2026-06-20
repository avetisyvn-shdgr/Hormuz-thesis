"""Global Fishing Watch adapters for vessel identity and event data."""
from __future__ import annotations

from typing import Any

import requests

from .. import config


BASE_URL = "https://gateway.api.globalfishingwatch.org/v3"
IDENTITY_DATASET = "public-global-vessel-identity:latest"
PORT_VISIT_DATASET = "public-global-port-visits-events:latest"
MAX_EVENT_PAGES = 100


class GFWClient:
    """Small authenticated client for non-series vessel data."""

    def __init__(self, token: str | None = None, session: Any | None = None):
        self.token = token or config.api_key("GFW_API_TOKEN")
        self.session = session or requests

    def _get(self, path: str, params: dict) -> dict:
        response = self.session.get(
            BASE_URL + path,
            params=params,
            headers={"Authorization": f"Bearer {self.token}"},
            timeout=60,
        )
        response.raise_for_status()
        return response.json()

    def search_imo(self, imo: str) -> list[dict]:
        """Return raw identity candidates; downstream code enforces exact IMO."""
        payload = self._get(
            "/vessels/search",
            {
                "query": str(imo),
                "datasets[0]": IDENTITY_DATASET,
                "limit": 50,
            },
        )
        return payload.get("entries", [])

    def search_imos(self, imos: list[str]) -> list[dict]:
        """Search a small IMO batch and refuse silently truncated responses."""
        if not imos or len(imos) > 10:
            raise ValueError("GFW batch search requires between 1 and 10 IMO numbers.")
        payload = self._get(
            "/vessels/search",
            {
                "where": " OR ".join(f'imo="{imo}"' for imo in imos),
                "datasets[0]": IDENTITY_DATASET,
                "limit": 50,
            },
        )
        entries = payload.get("entries", [])
        if int(payload.get("total", len(entries))) > len(entries):
            raise RuntimeError(
                "GFW batch identity response was truncated; reduce the batch size."
            )
        return entries

    def port_visits(
        self,
        vessel_ids: list[str],
        start: str,
        end: str,
        *,
        batch_size: int = 20,
        page_size: int = 1000,
    ) -> list[dict]:
        """Collect paginated port visits; `end` follows GFW's exclusive rule."""
        events: list[dict] = []
        unique_ids = sorted(set(vessel_ids))
        for batch_start in range(0, len(unique_ids), batch_size):
            batch = unique_ids[batch_start:batch_start + batch_size]
            offset = 0
            for _ in range(MAX_EVENT_PAGES):
                params = {
                    "datasets[0]": PORT_VISIT_DATASET,
                    "types[0]": "PORT_VISIT",
                    "start-date": start,
                    "end-date": end,
                    "limit": page_size,
                    "offset": offset,
                }
                params.update({f"vessels[{i}]": value for i, value in enumerate(batch)})
                payload = self._get("/events", params)
                page = payload.get("entries", [])
                events.extend(page)
                next_offset = payload.get("nextOffset")
                if next_offset is None or not page:
                    break
                offset = int(next_offset)
            else:
                raise RuntimeError("GFW port-visit pagination exceeded safety cap.")
        return events


def exact_imo_vessel_ids(entries: list[dict], imo: str) -> list[str]:
    """Extract every GFW vessel ID attached to an exact nested IMO match."""
    wanted = str(imo).strip()
    vessel_ids: set[str] = set()
    for entry in entries:
        identity_rows = (entry.get("registryInfo") or []) + (
            entry.get("selfReportedInfo") or []
        )
        if not any(str(row.get("imo", "")).strip() == wanted for row in identity_rows):
            continue
        for combined in entry.get("combinedSourcesInfo") or []:
            vessel_id = combined.get("vesselId")
            if vessel_id:
                vessel_ids.add(str(vessel_id))
    return sorted(vessel_ids)


def normalize_port_visits(events: list[dict], sample_period: str) -> list[dict]:
    """Normalize inspectable event fields without inferring cargo state."""
    rows: list[dict] = []
    for event in events:
        port_visit = event.get("port_visit") or {}
        anchorage = (
            port_visit.get("intermediateAnchorage")
            or port_visit.get("startAnchorage")
            or port_visit.get("endAnchorage")
            or {}
        )
        position = event.get("position") or {}
        vessel = event.get("vessel") or {}
        rows.append({
            "event_id": event.get("id"),
            "vessel_id": vessel.get("id"),
            "start": event.get("start"),
            "end": event.get("end"),
            "port_id": anchorage.get("anchorageId") or anchorage.get("id"),
            "port_name": anchorage.get("name"),
            "port_country": anchorage.get("flag"),
            "lat": anchorage.get("lat", position.get("lat")),
            "lon": anchorage.get("lon", position.get("lon")),
            "confidence": port_visit.get("confidence"),
            "at_dock": anchorage.get("atDock"),
            "sample_period": sample_period,
        })
    return rows
