
import pandas as pd
import pytest


from lngfreight import config  # noqa: E402
from lngfreight.importer_outcomes import build_outcomes  # noqa: E402
from lngfreight.network_rewiring import (  # noqa: E402
    ANOMALY_MONTHLY_COLUMNS,
    ANOMALY_SUMMARY_COLUMNS,
    GRAPH_METRIC_COLUMNS,
    MONTHLY_METRIC_COLUMNS,
    NETWORK_COLUMNS,
    POST_MONTH_SENSITIVITY_COLUMNS,
    RESILIENCE_TYPOLOGY_COLUMNS,
    REWIRING_SUMMARY_COLUMNS,
    TREATMENT_MONTH,
    TYPOLOGY_THRESHOLD_SENSITIVITY_COLUMNS,
    TYPOLOGY_THRESHOLD_SENSITIVITY_GRID,
    TYPOLOGY_THRESHOLD_SENSITIVITY_GRID_SIZE,
    _mean_edges_by_origin,
    _portfolio_vector,
    build_rewiring_network,
    dynamic_network_graph_metrics,
    graph_anomaly_scores,
    monthly_rewiring_metrics,
    post_month_typology_sensitivity,
    resilience_typology,
    typology_threshold_sensitivity,
    rewiring_prepost_summary,
)


def test_origin_period_averages_zero_fill_disappearing_origins():
    group = pd.DataFrame(
        {
            "period": ["2025-03", "2025-03", "2025-04"],
            "origin_code": ["A", "B", "A"],
            "origin_share": [0.5, 0.5, 1.0],
            "edge_value": [10.0, 10.0, 20.0],
        }
    )

    shares = _portfolio_vector(group, ["A", "B", "C"])
    edges = _mean_edges_by_origin(group, ["A", "B", "C"])

    assert shares.to_dict() == {"A": 0.75, "B": 0.25, "C": 0.0}
    assert edges.to_dict() == {"A": 15.0, "B": 5.0, "C": 0.0}
    assert shares.sum() == 1.0


def _network() -> pd.DataFrame:
    probe_dir = config.path("data_raw") / "backup_pathway_probe_20260621"
    eurostat_path = config.ROOT / config.settings()["paths"][
        "eurostat_lng_eu27_by_partner_json"
    ]
    return build_rewiring_network(
        probe_dir, config.path("importer_customs_dir"), eurostat_path
    )


def test_network_edge_list_contract_and_units():
    frame = _network()
    assert list(frame.columns) == NETWORK_COLUMNS
    assert sorted(frame["destination_unit"].unique()) == [
        "China", "EU27", "India", "Japan", "Korea", "Taiwan",
    ]
    assert (frame["edge_value"] > 0).all()
    assert not frame.duplicated(
        subset=["destination_unit", "period", "origin_code", "source_file"]
    ).any()
    assert not frame["origin_code"].isin(["0", "TOTAL", "World"]).any()


def test_oman_is_explicitly_flagged_but_never_gulf():
    frame = _network()
    oman = frame[frame["is_oman_excluded_from_gulf"]]
    assert not oman.empty
    assert not oman["is_gulf_origin"].any()
    assert set(oman["origin_group"]) == {"oman_excluded_from_gulf"}


def test_india_rows_are_value_basis_and_flagged():
    india = _network()[lambda df: df["destination_unit"] == "India"]
    assert set(india["unit_of_measure"]) == {"kUSD"}
    assert set(india["measurement_basis"]) == {"value_kusd"}
    assert india["admissibility_note"].str.contains("value basis").all()


def test_gulf_edge_sums_match_existing_outcome_frame():
    probe_dir = config.path("data_raw") / "backup_pathway_probe_20260621"
    eurostat_path = config.ROOT / config.settings()["paths"][
        "eurostat_lng_eu27_by_partner_json"
    ]
    outcomes = build_outcomes(
        probe_dir,
        customs_dir=config.path("importer_customs_dir"),
        eurostat_path=eurostat_path,
    )
    expected = (
        outcomes[outcomes["outcome"] == "y1_gulf_volume"]
        .set_index(["unit", "month"])["value"]
        .sort_index()
    )
    actual = (
        _network()[lambda df: df["is_gulf_origin"]]
        .groupby(["destination_unit", "period"])["edge_value"]
        .sum()
        .sort_index()
    )
    joined = pd.concat([actual, expected], axis=1, keys=["actual", "expected"])
    joined = joined.dropna()
    assert len(joined) > 0
    assert (joined["actual"] - joined["expected"]).abs().max() < 1e-6


def test_monthly_rewiring_metrics_are_mass_balanced():
    monthly = monthly_rewiring_metrics(_network())
    assert list(monthly.columns) == MONTHLY_METRIC_COLUMNS
    assert (
        monthly["edge_total_value"]
        - monthly["gulf_edge_value"]
        - monthly["non_gulf_edge_value"]
    ).abs().max() < 1e-9
    assert ((monthly["gulf_share"] >= 0) & (monthly["gulf_share"] <= 1)).all()
    assert ((monthly["source_hhi"] > 0) & (monthly["source_hhi"] <= 1)).all()
    assert (monthly["source_entropy"] >= 0).all()


def test_prepost_summary_flags_coverage_and_basis():
    summary = rewiring_prepost_summary(monthly_rewiring_metrics(_network()))
    assert list(summary.columns) == REWIRING_SUMMARY_COLUMNS
    notes = summary.set_index("destination_unit")["coverage_note"]
    assert "value_basis" in notes.loc["India"]
    assert "aggregate_comparator" in notes.loc["EU27"]
    assert notes.loc["Japan"] == "descriptive_coverage_ok"
    assert summary.set_index("destination_unit").loc["China", "pre_months"] == 12
    assert summary.set_index("destination_unit").loc["China", "post_months"] == 3
    assert summary.set_index("destination_unit").loc["Japan", "pre_months"] == 12
    assert summary.set_index("destination_unit").loc["Japan", "post_months"] == 3


def test_prepost_summary_includes_same_calendar_robustness():
    summary = rewiring_prepost_summary(monthly_rewiring_metrics(_network()))
    indexed = summary.set_index("destination_unit")
    china = indexed.loc["China"]
    assert china["same_calendar_post_months"] == china["post_months"]
    assert china["same_calendar_pre_months"] == china["post_months"]
    assert china["same_calendar_edge_total_pct_change"] < 0
    assert china["same_calendar_edge_total_pct_change"] > china["edge_total_pct_change"]
    assert indexed["same_calendar_gulf_share_change_pp"].dropna().lt(0).all()


def test_summary_captures_gulf_share_collapse_direction():
    summary = rewiring_prepost_summary(monthly_rewiring_metrics(_network()))
    assert (summary["gulf_share_change_pp"] < 0).all()
    taiwan = summary.set_index("destination_unit").loc["Taiwan"]
    assert taiwan["gulf_share_change_pp"] < -25.0


def test_dynamic_network_graph_metrics_contract_and_bounds():
    graph = dynamic_network_graph_metrics(_network())
    assert list(graph.columns) == GRAPH_METRIC_COLUMNS
    assert sorted(graph["destination_unit"].unique()) == [
        "China", "EU27", "India", "Japan", "Korea", "Taiwan",
    ]
    assert ((graph["edge_turnover_rate"] >= 0) & (graph["edge_turnover_rate"] <= 1)).all()
    assert (
        (graph["jensen_shannon_divergence"] >= 0)
        & (graph["jensen_shannon_divergence"] <= 1)
    ).all()
    assert (graph["jensen_shannon_distance"] >= 0).all()
    assert (
        graph["retained_origin_count"]
        + graph["new_origin_count"]
        == graph["post_origin_count"]
    ).all()
    assert (
        graph["retained_origin_count"]
        + graph["dropped_origin_count"]
        == graph["pre_origin_count"]
    ).all()


def test_dynamic_network_graph_metrics_preserve_caution_flags_and_movement():
    graph = dynamic_network_graph_metrics(_network()).set_index("destination_unit")
    assert "value_basis" in graph.loc["India", "coverage_note"]
    assert "aggregate_comparator" in graph.loc["EU27", "coverage_note"]
    assert graph.loc["Japan", "coverage_note"] == "descriptive_coverage_ok"
    assert graph.loc["India", "edge_turnover_rate"] > 0.45
    assert graph.loc["Taiwan", "jensen_shannon_distance"] > 0.25
    assert graph.loc["Japan", "jensen_shannon_distance"] > 0.15
    assert graph.loc["China", "non_gulf_offset_ratio"] == pytest.approx(
        -0.0840437791
    )
    assert graph.loc["EU27", "non_gulf_offset_ratio"] == pytest.approx(
        2.0104270609
    )
    assert graph.loc["India", "edge_turnover_rate"] == pytest.approx(
        0.5552862631
    )


def test_resilience_typology_contract_and_expected_categories():
    monthly = monthly_rewiring_metrics(_network())
    summary = rewiring_prepost_summary(monthly)
    graph = dynamic_network_graph_metrics(_network())
    typology = resilience_typology(summary, graph)
    assert list(typology.columns) == RESILIENCE_TYPOLOGY_COLUMNS

    labels = typology.set_index("destination_unit")["primary_typology"]
    assert labels.loc["India"] == "high_exposure_high_offset"
    assert labels.loc["Taiwan"] == "high_exposure_high_offset"
    assert labels.loc["China"] == "high_exposure_constrained"
    assert labels.loc["Korea"] == "high_exposure_constrained"
    assert labels.loc["Japan"] == "low_exposure_stable"
    assert labels.loc["EU27"] == "aggregate_comparator"


def test_resilience_typology_preserves_cautions_and_thresholds():
    monthly = monthly_rewiring_metrics(_network())
    typology = resilience_typology(
        rewiring_prepost_summary(monthly),
        dynamic_network_graph_metrics(_network()),
    ).set_index("destination_unit")
    assert "value_basis_caution" in typology.loc["India", "caution_flags"]
    assert "aggregate_comparator" in typology.loc["EU27", "caution_flags"]
    assert typology.loc["Japan", "caution_flags"] == "none"
    assert "high_exposure_pre_gulf_share_min" in typology.loc["China", "rule_thresholds"]
    assert (
        typology.loc["China", "typology_total_change_basis"]
        == "same_calendar_prior_year"
    )
    assert pd.notna(
        typology.loc["China", "seasonality_adjusted_edge_total_pct_change"]
    )


def test_resilience_evidence_strength_rubric_is_not_caution_only():
    monthly = monthly_rewiring_metrics(_network())
    typology = resilience_typology(
        rewiring_prepost_summary(monthly),
        dynamic_network_graph_metrics(_network()),
    ).set_index("destination_unit")

    assert typology.loc["Taiwan", "primary_typology"] == "high_exposure_high_offset"
    assert typology.loc["Taiwan", "caution_flags"] == "none"
    assert typology.loc["Taiwan", "evidence_strength"] == "high"

    assert typology.loc["India", "primary_typology"] == "high_exposure_high_offset"
    assert "value_basis_caution" in typology.loc["India", "caution_flags"]
    assert typology.loc["India", "evidence_strength"] == "medium"

    assert typology.loc["China", "primary_typology"] == "high_exposure_constrained"
    assert typology.loc["China", "caution_flags"] == "none"
    assert typology.loc["China", "evidence_strength"] == "medium"

    assert typology.loc["Japan", "primary_typology"] == "low_exposure_stable"
    assert typology.loc["Japan", "caution_flags"] == "none"
    assert typology.loc["Japan", "evidence_strength"] == "medium"

    assert typology.loc["EU27", "evidence_strength"] == "context_only"


def test_post_month_typology_sensitivity_contract_and_unit_month_grid():
    network = _network()
    monthly = monthly_rewiring_metrics(network)
    sensitivity = post_month_typology_sensitivity(network)

    assert list(sensitivity.columns) == POST_MONTH_SENSITIVITY_COLUMNS
    units = sorted(monthly["destination_unit"].unique())
    post_months = sorted(
        monthly.loc[monthly["period"] >= TREATMENT_MONTH, "period"].unique()
    )
    assert len(sensitivity) == len(units) * len(post_months)
    assert sorted(sensitivity["destination_unit"].unique()) == units
    assert sorted(sensitivity["dropped_month"].unique()) == post_months
    assert (
        sensitivity.groupby("destination_unit")["dropped_month"].nunique()
        == len(post_months)
    ).all()
    assert (
        sensitivity.groupby("dropped_month")["destination_unit"].nunique()
        == len(units)
    ).all()


def test_post_month_typology_sensitivity_flags_are_structural():
    network = _network()
    monthly = monthly_rewiring_metrics(network)
    sensitivity = post_month_typology_sensitivity(network)

    base_post_counts = (
        monthly[monthly["period"] >= TREATMENT_MONTH]
        .groupby("destination_unit")["period"]
        .nunique()
    )
    for row in sensitivity.to_dict("records"):
        expected = base_post_counts.loc[row["destination_unit"]] - int(
            row["unit_had_dropped_month"]
        )
        assert row["post_months_after_drop"] == expected

    expected_any = sensitivity.groupby("destination_unit")[
        "changed_under_drop"
    ].transform("any")
    assert (
        sensitivity["any_primary_typology_change"].reset_index(drop=True)
        == expected_any.reset_index(drop=True)
    ).all()


def test_post_month_typology_sensitivity_separates_coverage_from_substance():
    sensitivity = post_month_typology_sensitivity(_network())
    available_changes = sensitivity[
        sensitivity["unit_had_dropped_month"].astype(bool)
        & sensitivity["changed_under_drop"].astype(bool)
    ]

    for unit in ["China", "India", "Japan"]:
        rows = available_changes[available_changes["destination_unit"] == unit]
        assert set(rows["dropped_primary_typology"]) == {
            "not_estimable_coverage_limited"
        }
        assert set(rows["post_months_after_drop"]) == {2}

    assert "Taiwan" not in set(available_changes["destination_unit"])
    assert "Korea" not in set(available_changes["destination_unit"])
    assert "EU27" not in set(available_changes["destination_unit"])


def test_typology_threshold_sensitivity_contract_and_grid_size():
    monthly = monthly_rewiring_metrics(_network())
    summary = rewiring_prepost_summary(monthly)
    graph = dynamic_network_graph_metrics(_network())
    sensitivity = typology_threshold_sensitivity(summary, graph)

    assert list(sensitivity.columns) == TYPOLOGY_THRESHOLD_SENSITIVITY_COLUMNS
    assert TYPOLOGY_THRESHOLD_SENSITIVITY_GRID_SIZE == 81
    assert sensitivity["grid_id"].nunique() == TYPOLOGY_THRESHOLD_SENSITIVITY_GRID_SIZE
    assert (
        sensitivity.groupby("destination_unit")["grid_id"].nunique()
        == TYPOLOGY_THRESHOLD_SENSITIVITY_GRID_SIZE
    ).all()
    assert set(sensitivity["high_exposure_pre_gulf_share_min"]) == set(
        TYPOLOGY_THRESHOLD_SENSITIVITY_GRID["high_exposure_pre_gulf_share_min"]
    )
    assert set(sensitivity["high_offset_ratio_min"]) == set(
        TYPOLOGY_THRESHOLD_SENSITIVITY_GRID["high_offset_ratio_min"]
    )
    assert set(sensitivity["constrained_total_pct_max"]) == set(
        TYPOLOGY_THRESHOLD_SENSITIVITY_GRID["constrained_total_pct_max"]
    )
    assert set(sensitivity["stable_band_abs"]) == set(
        TYPOLOGY_THRESHOLD_SENSITIVITY_GRID["stable_band_abs"]
    )


def test_typology_threshold_sensitivity_stability_summary_is_per_unit():
    monthly = monthly_rewiring_metrics(_network())
    summary = rewiring_prepost_summary(monthly)
    graph = dynamic_network_graph_metrics(_network())
    sensitivity = typology_threshold_sensitivity(summary, graph)

    assert (
        (sensitivity["unit_grid_agreement_share"] >= 0)
        & (sensitivity["unit_grid_agreement_share"] <= 1)
    ).all()
    for unit, group in sensitivity.groupby("destination_unit"):
        assert group["unit_grid_points"].nunique() == 1
        assert group["unit_grid_agreement_count"].nunique() == 1
        assert group["unit_grid_agreement_share"].nunique() == 1
        assert group["unit_grid_points"].iloc[0] == len(group)
        assert group["unit_grid_agreement_count"].iloc[0] == int(
            group["agrees_with_headline"].sum()
        )

    headline_grid = sensitivity[
        (sensitivity["high_exposure_pre_gulf_share_min"] == 0.15)
        & (sensitivity["high_offset_ratio_min"] == 0.8)
        & (sensitivity["constrained_total_pct_max"] == -5.0)
        & (sensitivity["stable_band_abs"] == 10.0)
    ]
    assert sorted(headline_grid["destination_unit"].unique()) == sorted(
        sensitivity["destination_unit"].unique()
    )
    assert headline_grid["agrees_with_headline"].all()


def test_graph_anomaly_scores_contract_bounds_and_coverage():
    monthly, summary = graph_anomaly_scores(_network())
    assert list(monthly.columns) == ANOMALY_MONTHLY_COLUMNS
    assert list(summary.columns) == ANOMALY_SUMMARY_COLUMNS
    assert sorted(summary["destination_unit"].unique()) == [
        "China", "EU27", "India", "Japan", "Korea", "Taiwan",
    ]
    assert (monthly["portfolio_js_distance"] >= 0).all()
    assert (
        (monthly["pre_empirical_tail_p"] > 0)
        & (monthly["pre_empirical_tail_p"] <= 1)
    ).all()
    assert (
        (monthly["pre_empirical_percentile"] >= 0)
        & (monthly["pre_empirical_percentile"] <= 1)
    ).all()
    notes = summary.set_index("destination_unit")["coverage_note"]
    assert "value_basis" in notes.loc["India"]
    assert "aggregate_comparator" in notes.loc["EU27"]
    assert notes.loc["Japan"] == "descriptive_anomaly_ok"


def test_graph_anomaly_scores_flag_large_post_portfolio_movements():
    _, summary = graph_anomaly_scores(_network())
    flags = summary.set_index("destination_unit")["anomaly_flag"]
    assert flags.loc["China"]
    assert flags.loc["India"]
    assert flags.loc["Korea"]
    assert flags.loc["Taiwan"]
    assert flags.loc["EU27"]
    assert flags.loc["Japan"]


def test_graph_anomaly_pre_calibration_uses_leave_one_out_centroid():
    network = pd.DataFrame([
        {
            "period": "2025-03",
            "destination_unit": "Synthetic",
            "destination_unit_type": "importer",
            "origin_code": "A",
            "origin_country": "A",
            "origin_group": "non_gulf",
            "is_gulf_origin": False,
            "is_oman_excluded_from_gulf": False,
            "hs": "271111",
            "edge_value": 100.0,
            "unit_of_measure": "t",
            "measurement_basis": "weight_ton",
            "source": "synthetic",
            "source_file": "synthetic",
            "snapshot_sha256": "synthetic",
            "post_treatment": False,
            "admissibility_note": "synthetic",
        },
        {
            "period": "2025-03",
            "destination_unit": "Synthetic",
            "destination_unit_type": "importer",
            "origin_code": "B",
            "origin_country": "B",
            "origin_group": "non_gulf",
            "is_gulf_origin": False,
            "is_oman_excluded_from_gulf": False,
            "hs": "271111",
            "edge_value": 1.0,
            "unit_of_measure": "t",
            "measurement_basis": "weight_ton",
            "source": "synthetic",
            "source_file": "synthetic",
            "snapshot_sha256": "synthetic",
            "post_treatment": False,
            "admissibility_note": "synthetic",
        },
        {
            "period": "2025-04",
            "destination_unit": "Synthetic",
            "destination_unit_type": "importer",
            "origin_code": "A",
            "origin_country": "A",
            "origin_group": "non_gulf",
            "is_gulf_origin": False,
            "is_oman_excluded_from_gulf": False,
            "hs": "271111",
            "edge_value": 1.0,
            "unit_of_measure": "t",
            "measurement_basis": "weight_ton",
            "source": "synthetic",
            "source_file": "synthetic",
            "snapshot_sha256": "synthetic",
            "post_treatment": False,
            "admissibility_note": "synthetic",
        },
        {
            "period": "2025-04",
            "destination_unit": "Synthetic",
            "destination_unit_type": "importer",
            "origin_code": "B",
            "origin_country": "B",
            "origin_group": "non_gulf",
            "is_gulf_origin": False,
            "is_oman_excluded_from_gulf": False,
            "hs": "271111",
            "edge_value": 100.0,
            "unit_of_measure": "t",
            "measurement_basis": "weight_ton",
            "source": "synthetic",
            "source_file": "synthetic",
            "snapshot_sha256": "synthetic",
            "post_treatment": False,
            "admissibility_note": "synthetic",
        },
        {
            "period": "2026-03",
            "destination_unit": "Synthetic",
            "destination_unit_type": "importer",
            "origin_code": "A",
            "origin_country": "A",
            "origin_group": "non_gulf",
            "is_gulf_origin": False,
            "is_oman_excluded_from_gulf": False,
            "hs": "271111",
            "edge_value": 50.0,
            "unit_of_measure": "t",
            "measurement_basis": "weight_ton",
            "source": "synthetic",
            "source_file": "synthetic",
            "snapshot_sha256": "synthetic",
            "post_treatment": True,
            "admissibility_note": "synthetic",
        },
        {
            "period": "2026-03",
            "destination_unit": "Synthetic",
            "destination_unit_type": "importer",
            "origin_code": "B",
            "origin_country": "B",
            "origin_group": "non_gulf",
            "is_gulf_origin": False,
            "is_oman_excluded_from_gulf": False,
            "hs": "271111",
            "edge_value": 50.0,
            "unit_of_measure": "t",
            "measurement_basis": "weight_ton",
            "source": "synthetic",
            "source_file": "synthetic",
            "snapshot_sha256": "synthetic",
            "post_treatment": True,
            "admissibility_note": "synthetic",
        },
    ])
    monthly, _ = graph_anomaly_scores(
        network,
        pre_start="2025-03",
        pre_end="2025-04",
        thresholds={"min_pre_calibration_months": 2, "min_post_months": 1},
    )
    pre = monthly[~monthly["post_treatment"]]
    assert pre["portfolio_js_distance"].min() > 0.75
