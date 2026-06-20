"""Conservative spatial crosswalk from GFW anchorages to GEM LNG terminals."""
from __future__ import annotations

import json
import math
from pathlib import Path

import pandas as pd


COUNTRY_ISO3 = {
    "Algeria": "DZA", "Angola": "AGO", "Argentina": "ARG",
    "Australia": "AUS", "Bahrain": "BHR", "Bangladesh": "BGD",
    "Belgium": "BEL", "Brazil": "BRA", "Brunei": "BRN",
    "Cameroon": "CMR", "Canada": "CAN", "Chile": "CHL", "China": "CHN",
    "Colombia": "COL", "Croatia": "HRV", "Dominican Republic": "DOM",
    "Egypt": "EGY", "El Salvador": "SLV", "Equatorial Guinea": "GNQ",
    "Finland": "FIN", "France": "FRA", "Germany": "DEU", "Ghana": "GHA",
    "Gibraltar": "GIB", "Greece": "GRC", "Hong Kong": "HKG",
    "India": "IND", "Indonesia": "IDN", "Italy": "ITA", "Jamaica": "JAM",
    "Japan": "JPN", "Jordan": "JOR", "Kuwait": "KWT", "Lithuania": "LTU",
    "Malaysia": "MYS", "Malta": "MLT", "Mauritania": "MRT",
    "Mexico": "MEX", "Mozambique": "MOZ", "Netherlands": "NLD",
    "Nigeria": "NGA", "Norway": "NOR", "Oman": "OMN", "Pakistan": "PAK",
    "Panama": "PAN", "Papua New Guinea": "PNG", "Peru": "PER",
    "Philippines": "PHL", "Poland": "POL", "Portugal": "PRT", "Qatar": "QAT",
    "Republic of the Congo": "COG", "Russia": "RUS", "Singapore": "SGP",
    "South Korea": "KOR", "Spain": "ESP", "Sweden": "SWE", "Taiwan": "TWN",
    "Thailand": "THA", "Trinidad and Tobago": "TTO", "Turkmenistan": "TKM",
    "Türkiye": "TUR", "United Arab Emirates": "ARE", "United Kingdom": "GBR",
    "United States": "USA", "Vietnam": "VNM",
}


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    lat1r, lon1r, lat2r, lon2r = map(math.radians, (lat1, lon1, lat2, lon2))
    dlat, dlon = lat2r - lat1r, lon2r - lon1r
    value = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1r) * math.cos(lat2r) * math.sin(dlon / 2) ** 2
    )
    return 2 * 6371.0 * math.asin(math.sqrt(value))


def load_operating_terminals(path: Path) -> pd.DataFrame:
    payload = json.loads(path.read_text())
    rows = []
    for feature in payload["features"]:
        item = feature["properties"]
        if item.get("Status") != "operating":
            continue
        if item.get("FacilityType") not in {"import", "export"}:
            continue
        total_key = (
            "TotImportLNGTerminalCapacityinMtpa"
            if item["FacilityType"] == "import"
            else "TotExportLNGTerminalCapacityinMtpa"
        )
        rows.append({
            "project_id": item["ProjectID"],
            "terminal_name": item["TerminalName"],
            "terminal_role": (
                "regasification" if item["FacilityType"] == "import"
                else "liquefaction"
            ),
            "country": item["Country/Area"],
            "terminal_lat": float(item["Latitude"]),
            "terminal_lon": float(item["Longitude"]),
            "capacity_mtpa": item.get(total_key) or item.get("CapacityinMtpa"),
            "source": item.get("Wiki"),
        })
    frame = pd.DataFrame(rows)
    return frame.drop_duplicates(
        subset=["project_id", "terminal_role"]
    ).reset_index(drop=True)


def build_terminal_crosswalk(
    visits: pd.DataFrame,
    terminals: pd.DataFrame,
    *,
    max_distance_km: float,
    min_capacity_mtpa: float,
) -> pd.DataFrame:
    ports = visits.groupby(
        ["port_id", "port_name", "port_country", "lat", "lon"],
        dropna=False,
    ).size().reset_index(name="visit_count")
    rows = []
    for port in ports.itertuples(index=False):
        candidates = terminals.copy()
        candidates["distance_km"] = candidates.apply(
            lambda terminal: haversine_km(
                port.lat, port.lon, terminal["terminal_lat"], terminal["terminal_lon"]
            ),
            axis=1,
        )
        nearest = candidates.sort_values(
            ["distance_km", "project_id", "terminal_role"]
        ).iloc[0]
        country_match = COUNTRY_ISO3.get(nearest["country"]) == port.port_country
        capacity_ok = (
            pd.notna(nearest["capacity_mtpa"])
            and float(nearest["capacity_mtpa"]) >= min_capacity_mtpa
        )
        if nearest["distance_km"] > max_distance_km:
            status = "outside_distance_threshold"
        elif not country_match:
            status = "country_mismatch"
        elif not capacity_ok:
            status = "small_or_unknown_capacity"
        else:
            status = "provisional_spatial_match"
        rows.append({
            "port_id": port.port_id,
            "port_name": port.port_name,
            "port_country": port.port_country,
            "port_lat": port.lat,
            "port_lon": port.lon,
            "visit_count": int(port.visit_count),
            **nearest.to_dict(),
            "country_match": country_match,
            "match_status": status,
        })
    return pd.DataFrame(rows).sort_values(
        ["match_status", "distance_km", "port_id"]
    ).reset_index(drop=True)
