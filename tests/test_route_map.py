import pandas as pd

from scripts.make_route_map import (
    aggregate_pair_changes,
    primary_route_sample,
    split_at_dateline,
)


def _voyages() -> pd.DataFrame:
    return pd.DataFrame({
        "project_id": ["a", "a", "a", "a"],
        "terminal_name": ["A"] * 4,
        "terminal_lat": [25.0] * 4,
        "terminal_lon": [55.0] * 4,
        "destination_project_id": ["b", "b", "b", "c"],
        "destination_terminal_name": ["B", "B", "B", "C"],
        "destination_terminal_lat": [35.0, 35.0, 35.0, 10.0],
        "destination_terminal_lon": [120.0, 120.0, 120.0, -80.0],
        "sample_period": ["pre", "pre", "post", "post"],
        "terminal_match_radius_km": [30, 30, 30, 20],
        "inferred_nominal_m3_nm_expanded": [10.0, 20.0, 45.0, 50.0],
    })


def test_primary_route_sample_uses_30km_expanded_qa_filter():
    sample = primary_route_sample(_voyages())
    assert len(sample) == 3
    assert set(sample["sample_period"]) == {"pre", "post"}


def test_aggregate_pair_changes_is_post_minus_pre():
    changes = aggregate_pair_changes(primary_route_sample(_voyages()))
    assert len(changes) == 1
    assert changes.loc[0, "pre_voyages"] == 2
    assert changes.loc[0, "post_voyages"] == 1
    assert changes.loc[0, "change_capacity_distance_m3_nm"] == 15.0


def test_split_at_dateline_prevents_cross_world_segment():
    segments = split_at_dateline(
        [
            [170.0, 0.0],
            [179.0, 1.0],
            [-179.0, 2.0],
            [-160.0, 3.0],
        ]
    )
    assert len(segments) == 2
    assert all(
        (abs(segment[1:, 0] - segment[:-1, 0]) <= 180).all()
        for segment in segments
    )
