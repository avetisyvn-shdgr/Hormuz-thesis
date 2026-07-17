"""Build a basin-level LNG reallocation stress-test model.

This is a scenario-conditional minimum-cost transport exercise over observed
non-Gulf route supply and lost Hormuz-exposed basin demand. It is not observed
cargo matching, global LNG capacity, a freight-rate model, or causal ATT.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lngfreight import config  # noqa: E402
from lngfreight.reallocation import (  # noqa: E402
    build_transport_inputs,
    solve_reallocation_scenarios,
)


def main() -> None:
    paths = config.settings()["paths"]
    voyages = pd.read_csv(config.ROOT / paths["importer_exposure_voyages_csv"])
    routes = pd.read_csv(config.ROOT / paths["maritime_route_distances_csv"])
    terminals = pd.read_csv(config.ROOT / paths["global_gfw_lng_terminals_csv"])

    inputs = build_transport_inputs(voyages, routes, terminals=terminals)
    solution, summary = solve_reallocation_scenarios(inputs)

    outputs = {
        "lng_reallocation_basin_demands_csv": inputs.demands,
        "lng_reallocation_supply_nodes_csv": inputs.supplies,
        "lng_reallocation_cost_matrix_csv": inputs.costs,
        "lng_reallocation_solution_csv": solution,
        "lng_reallocation_summary_csv": summary,
    }
    for key, frame in outputs.items():
        path = config.ROOT / paths[key]
        path.parent.mkdir(parents=True, exist_ok=True)
        frame.to_csv(path, index=False)
        print(f"wrote {path}")

    print(summary[[
        "scenario",
        "demand_k_m3",
        "real_supply_k_m3",
        "allocated_real_k_m3",
        "unmet_k_m3",
        "unmet_share",
        "mean_route_nm",
        "mean_additional_nm",
        "coverage_note",
    ]].to_string(index=False))


if __name__ == "__main__":
    main()
