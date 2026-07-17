import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lngfreight import config  # noqa: E402
from lngfreight.reallocation import (  # noqa: E402
    SUMMARY_COLUMNS,
    SOLUTION_COLUMNS,
    SUPPLY_COLUMNS,
    TransportInputs,
    build_transport_inputs,
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
        "supply_capacity_m3": [1_500_000.0],
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
    assert by_type["observed_route_supply"] == 1500.0
    assert by_type["unmet"] == 500.0
    row = summary.iloc[0]
    assert row["unmet_share"] == 0.25
    assert row["mean_additional_nm"] == 250.0


def test_real_reallocation_inputs_and_solution_contract():
    paths = config.settings()["paths"]
    voyages = pd.read_csv(config.ROOT / paths["importer_exposure_voyages_csv"])
    routes = pd.read_csv(config.ROOT / paths["maritime_route_distances_csv"])

    inputs = build_transport_inputs(voyages, routes)
    solution, summary = solve_reallocation_scenarios(inputs)

    assert not inputs.demands.empty
    assert not inputs.supplies.empty
    assert not inputs.costs.empty
    assert set(summary["scenario"]) == {
        "incremental_non_gulf_growth_only",
        "post_non_gulf_pool",
    }
    assert (solution["flow_k_m3"] > 0).all()
    assert ((summary["unmet_share"] >= 0) & (summary["unmet_share"] <= 1)).all()
    assert (
        summary.set_index("scenario").loc["post_non_gulf_pool", "unmet_share"]
        <= summary.set_index("scenario").loc[
            "incremental_non_gulf_growth_only", "unmet_share"
        ]
    )
    assert summary["coverage_note"].str.contains("observed_route_transport_solution").all()
    post_pool_note = summary.set_index("scenario").loc[
        "post_non_gulf_pool", "coverage_note"
    ]
    assert "lower_bound_short_route_pool" in post_pool_note
