import pandas as pd
import pytest

from hormuz_throughput.exposure import attach_exposure_metadata, exposure_summary


def _voyages() -> pd.DataFrame:
    return pd.DataFrame({
        "event_id": ["pre_gulf", "pre_other", "post_other"],
        "imo": ["1", "2", "3"],
        "sample_period": ["pre", "pre", "post"],
        "project_id": ["gulf", "other", "other"],
        "destination_project_id": ["import"] * 3,
        "endpoint_status": ["resolved_liquefaction_to_regasification"] * 3,
        "capacity_m3": [100.0, 200.0, 250.0],
        "terminal_match_radius_km": [30] * 3,
        "inferred_nominal_m3_nm_expanded": [1000.0, 2000.0, 3000.0],
        "route_passages": ['["ormuz"]', "[]", "[]"],
    })


def _audit() -> pd.DataFrame:
    return pd.DataFrame({
        "project_id": ["import"], "country": ["Japan"],
        "terminal_role": ["regasification"],
    })


def test_attach_exposure_metadata_fails_on_unclassified_country():
    with pytest.raises(ValueError, match="Unclassified"):
        attach_exposure_metadata(
            _voyages(), _audit(), terminal_match_radius_km=30,
            gulf_export_project_ids=["gulf"], destination_basin_by_country={},
        )


def test_importer_exposure_separates_gulf_loss_and_non_gulf_gain():
    enriched = attach_exposure_metadata(
        _voyages(), _audit(), terminal_match_radius_km=30,
        gulf_export_project_ids=["gulf"],
        destination_basin_by_country={"Japan": "Pacific"},
    )
    result = exposure_summary(enriched, "destination_country")
    assert result.loc[0, "pre_hormuz_exposure_capacity_share_pct"] == pytest.approx(100 / 300 * 100)
    assert result.loc[0, "hormuz_exposed_capacity_absolute_change_m3"] == -100.0
    assert result.loc[0, "non_gulf_capacity_absolute_change_m3"] == 50.0
    assert result.loc[0, "descriptive_non_gulf_offset_ratio"] == 0.5


def test_country_exposed_estimates_are_suppressed_below_post_support():
    enriched = attach_exposure_metadata(
        _voyages(), _audit(), terminal_match_radius_km=30,
        gulf_export_project_ids=["gulf"],
        destination_basin_by_country={"Japan": "Pacific"},
    )
    result = exposure_summary(
        enriched, "destination_country", min_post_exposed_voyages=5
    )
    assert not bool(result.loc[0, "country_hormuz_exposed_estimate_estimable"])
    assert pd.isna(result.loc[0, "hormuz_exposed_capacity_absolute_change_m3"])
