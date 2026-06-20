import pandas as pd
import pytest

from lngfreight.capacity_miles import (
    attach_capacity_nautical_miles,
    capacity_period_summary,
    capacity_pre_post_comparison,
    validate_carrier_capacity_frame,
)
from lngfreight.routes import PAIR_COLUMNS


def _voyages() -> pd.DataFrame:
    rows = []
    for period, event in (("pre", "e1"), ("post", "e2")):
        rows.append({
            "imo": "1234567", "sample_period": period, "event_id": event,
            "endpoint_status": "resolved_liquefaction_to_regasification",
            "terminal_match_radius_km": 30,
            "project_id": "export", "terminal_name": "Export",
            "terminal_lat": 0.0, "terminal_lon": 0.0,
            "destination_project_id": "import",
            "destination_terminal_name": "Import",
            "destination_terminal_lat": 1.0,
            "destination_terminal_lon": 1.0,
        })
    return pd.DataFrame(rows)


def _routes() -> pd.DataFrame:
    row = _voyages().iloc[0][PAIR_COLUMNS].to_dict()
    row.update({
        "modeled_route_nm": 90.0,
        "modeled_terminal_to_terminal_nm": 100.0,
        "great_circle_nm": 80.0,
        "origin_snap_nm": 5.0,
        "destination_snap_nm": 5.0,
        "route_to_geodesic_ratio": 1.25,
        "route_passages": "[]",
        "route_status": "accepted_modeled_shortest_sea_route",
        "distance_accepted": True,
        "distance_accepted_expanded": True,
    })
    return pd.DataFrame([row])


def _carriers() -> pd.DataFrame:
    return pd.DataFrame({
        "imo": ["1234567"], "capacity_m3": [150000.0],
        "capacity_reference_missing": [False],
    })


def test_carrier_validation_rejects_duplicate_imo():
    carriers = pd.concat([_carriers(), _carriers()], ignore_index=True)
    with pytest.raises(ValueError, match="duplicate IMOs"):
        validate_carrier_capacity_frame(carriers)


def test_capacity_product_uses_nominal_m3_and_terminal_distance():
    result = attach_capacity_nautical_miles(_voyages(), _routes(), _carriers())
    assert result["inferred_nominal_m3_nm_strict"].tolist() == [15_000_000.0] * 2
    assert result["capacity_join_status"].eq("strict_route_accepted").all()


def test_period_and_comparison_summaries_keep_pre_post_separate():
    enriched = attach_capacity_nautical_miles(_voyages(), _routes(), _carriers())
    summary = capacity_period_summary(enriched)
    comparison = capacity_pre_post_comparison(summary)
    assert len(summary) == 2
    assert comparison.loc[0, "expanded_percent_change"] == 0.0
    assert comparison.loc[0, "expanded_mean_per_voyage_percent_change"] == 0.0
    assert comparison.loc[0, "strict_pre_routed_voyages"] == 1
