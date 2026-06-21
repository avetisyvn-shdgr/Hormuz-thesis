import pandas as pd
import pytest

from lngfreight.capacity_miles import (
    attach_capacity_nautical_miles,
    capacity_period_summary,
    capacity_pre_post_comparison,
    cluster_bootstrap_mean_change,
    route_shift_share_decomposition,
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


def test_carrier_cluster_bootstrap_returns_reproducible_interval():
    frame = pd.DataFrame({
        "imo": ["a", "a", "b", "b", "c", "c"],
        "sample_period": ["pre", "post"] * 3,
        "value": [10.0, 12.0, 20.0, 22.0, 30.0, 36.0],
    })
    result = cluster_bootstrap_mean_change(frame, "value", n_draws=200, seed=7)
    assert result["point_estimate_percent_change"] == pytest.approx(70 / 60 * 100 - 100)
    assert result["n_clusters"] == 3
    assert result["ci_lower"] <= result["point_estimate_percent_change"] <= result["ci_upper"]
    assert result["interval_method"] == "carrier_cluster_bca_bootstrap"
    assert result["n_jackknife_clusters"] == 3
    assert result["bca_ci_lower"] == result["ci_lower"]
    assert result["percentile_ci_lower"] <= result["percentile_ci_upper"]


def test_route_decomposition_has_exact_common_support_identity():
    frame = pd.DataFrame({
        "sample_period": ["pre", "pre", "post", "post"],
        "project_id": ["a", "b", "a", "b"],
        "destination_project_id": ["x", "y", "x", "y"],
        "value": [10.0, 20.0, 12.0, 30.0],
    })
    result = route_shift_share_decomposition(frame, "value")
    assert result["n_common_routes"] == 2
    assert result["identity_error"] == pytest.approx(0.0)
    assert result["entry_exit_route_residual"] == pytest.approx(0.0)
