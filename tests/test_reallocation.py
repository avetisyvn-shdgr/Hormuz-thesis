
import pandas as pd


from lngfreight import config  # noqa: E402
from lngfreight.reallocation import (  # noqa: E402
    RESIDUAL_SUPPLY_SCENARIO,
    SUMMARY_COLUMNS,
    SOLUTION_COLUMNS,
    SUPPLY_COLUMNS,
    TransportInputs,
    build_transport_inputs,
    non_gulf_supply_nodes,
    solve_reallocation_scenarios,
)


def test_transport_solver_allocates_cheapest_real_supply_before_unmet():
    demands = pd.DataFrame({
        "destination_basin": ["Pacific"],
        "pre_hormuz_exposed_capacity_m3": [2_000_000.0],
        "post_hormuz_exposed_capacity_m3": [0.0],
        "lost_hormuz_capacity_m3": [2_000_000.0],
        "lost_hormuz_k_m3": [2_000.0],
        "baseline_hormuz_route_nm": [1_000.0],
        "baseline_route_note": ["synthetic"],
    })
    supplies = pd.DataFrame({
        "scenario": ["synthetic"],
        "source_project_id": ["S1"],
        "source_terminal_name": ["Cheap LNG"],
        "source_country": [None],
        "gross_post_capacity_m3": [1_500_000.0],
        "committed_post_capacity_m3": [0.0],
        "committed_destination_count": [0],
        "supply_capacity_m3": [1_500_000.0],
        "gross_post_k_m3": [1_500.0],
        "committed_post_k_m3": [0.0],
        "supply_k_m3": [1_500.0],
        "supply_basis": ["synthetic"],
    }, columns=SUPPLY_COLUMNS)
    costs = pd.DataFrame({
        "source_project_id": ["S1"],
        "source_terminal_name": ["Cheap LNG"],
        "source_country": [None],
        "destination_basin": ["Pacific"],
        "route_nm": [1_250.0],
        "route_cost_note": ["synthetic"],
    })

    solution, summary = solve_reallocation_scenarios(
        TransportInputs(demands=demands, supplies=supplies, costs=costs)
    )
    assert list(solution.columns) == SOLUTION_COLUMNS
    assert list(summary.columns) == SUMMARY_COLUMNS
    by_type = solution.groupby("flow_type")["flow_k_m3"].sum().to_dict()
    assert by_type["residual_route_supply"] == 1500.0
    assert by_type["unmet"] == 500.0
    row = summary.iloc[0]
    assert row["unmet_share"] == 0.25
    assert row["mean_additional_nm"] == 250.0


def test_observed_post_voyages_are_not_reoffered_as_spare_supply():
    voyages = pd.DataFrame({
        "sample_period": ["post", "post", "pre"],
        "origin_group": ["non_gulf", "non_gulf", "non_gulf"],
        "project_id": ["S1", "S1", "S1"],
        "terminal_name": ["Source LNG", "Source LNG", "Source LNG"],
        "capacity_m3": [100_000.0, 150_000.0, 90_000.0],
        "destination_project_id": ["D1", "D2", "D1"],
        "destination_basin": ["Atlantic", "Pacific", "Atlantic"],
    })

    supplies = non_gulf_supply_nodes(voyages)

    assert len(supplies) == 1
    row = supplies.iloc[0]
    assert row["scenario"] == RESIDUAL_SUPPLY_SCENARIO
    assert row["gross_post_capacity_m3"] == 250_000.0
    assert row["committed_post_capacity_m3"] == 250_000.0
    assert row["committed_destination_count"] == 2
    assert row["supply_capacity_m3"] == 0.0
    assert row["supply_k_m3"] == 0.0


def test_real_reallocation_inputs_and_solution_contract():
    paths = config.settings()["paths"]
    voyages = pd.read_csv(config.ROOT / paths["importer_exposure_voyages_csv"])
    routes = pd.read_csv(config.ROOT / paths["maritime_route_distances_csv"])

    inputs = build_transport_inputs(voyages, routes)
    solution, summary = solve_reallocation_scenarios(inputs)

    assert not inputs.demands.empty
    assert not inputs.supplies.empty
    assert not inputs.costs.empty
    assert set(summary["scenario"]) == {RESIDUAL_SUPPLY_SCENARIO}
    assert (solution["flow_k_m3"] > 0).all()
    assert ((summary["unmet_share"] >= 0) & (summary["unmet_share"] <= 1)).all()
    row = summary.set_index("scenario").loc[RESIDUAL_SUPPLY_SCENARIO]
    assert row["gross_observed_post_k_m3"] > 0
    assert row["gross_observed_post_k_m3"] == row["committed_observed_post_k_m3"]
    assert row["residual_supply_k_m3"] == 0
    assert row["allocated_residual_k_m3"] == 0
    assert row["unmet_share"] == 1
    assert row["n_supply_nodes"] == 0
    assert "no_uncommitted_observed_supply" in row["coverage_note"]
    assert "observed_post_voyages_reserved_for_recorded_destinations" in row[
        "coverage_note"
    ]
