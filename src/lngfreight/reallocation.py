"""Scenario-conditional LNG reallocation stress tests.

This module builds a transparent basin-level transport model from existing
observed-route artifacts. It is a lower-bound mechanism stress test, not
observed cargo matching, global liquefaction capacity, or causal identification.
"""
from __future__ import annotations

from dataclasses import dataclass
import math

import networkx as nx
import pandas as pd

CAPACITY_SCALE_M3 = 1_000.0
UNMET_SOURCE = "__unmet_replacement__"
SURPLUS_SINK = "__unused_observed_supply__"
RESIDUAL_SUPPLY_SCENARIO = "observed_post_residual_after_commitments"

DEMAND_COLUMNS = [
    "destination_basin",
    "pre_hormuz_exposed_capacity_m3",
    "post_hormuz_exposed_capacity_m3",
    "lost_hormuz_capacity_m3",
    "lost_hormuz_k_m3",
    "baseline_hormuz_route_nm",
    "baseline_route_note",
]

SUPPLY_COLUMNS = [
    "scenario",
    "source_project_id",
    "source_terminal_name",
    "source_country",
    "gross_post_capacity_m3",
    "committed_post_capacity_m3",
    "committed_destination_count",
    "supply_capacity_m3",
    "gross_post_k_m3",
    "committed_post_k_m3",
    "supply_k_m3",
    "supply_basis",
]

COST_COLUMNS = [
    "source_project_id",
    "source_terminal_name",
    "source_country",
    "destination_basin",
    "route_nm",
    "route_cost_note",
]

SOLUTION_COLUMNS = [
    "scenario",
    "source_project_id",
    "source_terminal_name",
    "source_country",
    "destination_basin",
    "flow_k_m3",
    "route_nm",
    "baseline_hormuz_route_nm",
    "transport_k_m3_nm",
    "baseline_equivalent_k_m3_nm",
    "additional_k_m3_nm",
    "flow_type",
]

SUMMARY_COLUMNS = [
    "scenario",
    "demand_k_m3",
    "gross_observed_post_k_m3",
    "committed_observed_post_k_m3",
    "residual_supply_k_m3",
    "allocated_residual_k_m3",
    "unmet_k_m3",
    "unmet_share",
    "transport_k_m3_nm",
    "baseline_equivalent_k_m3_nm",
    "additional_k_m3_nm",
    "mean_route_nm",
    "mean_additional_nm",
    "n_supply_nodes",
    "n_cost_edges",
    "coverage_note",
]


@dataclass(frozen=True)
class TransportInputs:
    demands: pd.DataFrame
    supplies: pd.DataFrame
    costs: pd.DataFrame


def _as_bool(series: pd.Series) -> pd.Series:
    if series.dtype == bool:
        return series
    return series.astype(str).str.lower().isin({"true", "1", "yes"})


def _weighted_mean(frame: pd.DataFrame, value: str, weight: str) -> float:
    valid = frame[[value, weight]].dropna()
    valid = valid[valid[weight] > 0]
    if valid.empty:
        return float("nan")
    return float((valid[value] * valid[weight]).sum() / valid[weight].sum())


def basin_reallocation_demands(voyages: pd.DataFrame) -> pd.DataFrame:
    """Lost Hormuz-exposed capacity by destination basin."""
    frame = voyages.copy()
    frame["hormuz_exposed_leg"] = _as_bool(frame["hormuz_exposed_leg"])
    frame["expanded_route_available"] = _as_bool(frame["expanded_route_available"])

    rows: list[dict[str, object]] = []
    for basin, group in frame.groupby("destination_basin"):
        exposed = group[group["hormuz_exposed_leg"]]
        pre_capacity = float(
            exposed.loc[exposed["sample_period"].eq("pre"), "capacity_m3"].sum()
        )
        post_capacity = float(
            exposed.loc[exposed["sample_period"].eq("post"), "capacity_m3"].sum()
        )
        lost = max(0.0, pre_capacity - post_capacity)
        baseline_pool = exposed[
            exposed["sample_period"].eq("pre")
            & exposed["expanded_route_available"]
            & exposed["modeled_terminal_to_terminal_nm"].notna()
        ]
        baseline_nm = _weighted_mean(
            baseline_pool, "modeled_terminal_to_terminal_nm", "capacity_m3"
        )
        note = (
            "pre_hormuz_exposed_weighted_route"
            if not math.isnan(baseline_nm)
            else "missing_pre_hormuz_route"
        )
        rows.append({
            "destination_basin": basin,
            "pre_hormuz_exposed_capacity_m3": pre_capacity,
            "post_hormuz_exposed_capacity_m3": post_capacity,
            "lost_hormuz_capacity_m3": lost,
            "lost_hormuz_k_m3": lost / CAPACITY_SCALE_M3,
            "baseline_hormuz_route_nm": baseline_nm,
            "baseline_route_note": note,
        })
    out = pd.DataFrame(rows, columns=DEMAND_COLUMNS)
    return out[out["lost_hormuz_k_m3"] > 0].sort_values(
        "destination_basin"
    ).reset_index(drop=True)


def _terminal_country_lookup(terminals: pd.DataFrame | None) -> dict[str, str]:
    if terminals is None or terminals.empty:
        return {}
    if not {"project_id", "country"}.issubset(terminals.columns):
        return {}
    return (
        terminals[["project_id", "country"]]
        .dropna()
        .drop_duplicates("project_id")
        .set_index("project_id")["country"]
        .to_dict()
    )


def non_gulf_supply_nodes(
    voyages: pd.DataFrame,
    terminals: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Observed non-Gulf source capacity after reserving completed voyages.

    The voyage input records capacity that already moved to an observed
    destination. It is therefore committed capacity, not liquefaction headroom
    that can be allocated a second time. Without a separate source of terminal
    headroom, the defensible residual supply from this dataset is zero.
    """
    frame = voyages.copy()
    non_gulf = frame[
        frame["origin_group"].eq("non_gulf")
        & frame["capacity_m3"].notna()
        & frame["project_id"].notna()
    ]
    keys = ["project_id", "terminal_name"]
    countries = _terminal_country_lookup(terminals)

    post = non_gulf.loc[non_gulf["sample_period"].eq("post")]
    gross_post_capacity = post.groupby(keys)["capacity_m3"].sum()
    destination_commitments = (
        post.groupby(keys + ["destination_project_id"], dropna=False)["capacity_m3"]
        .sum()
    )
    committed_by_source = destination_commitments.groupby(keys).agg(
        committed_post_capacity_m3="sum",
        committed_destination_count="size",
    )
    source_accounting = (
        gross_post_capacity.rename("gross_post_capacity_m3")
        .to_frame()
        .join(committed_by_source, how="left")
    )

    rows: list[dict[str, object]] = []
    for (project_id, terminal_name), record in source_accounting.iterrows():
        gross_post = float(record["gross_post_capacity_m3"])
        committed_post = float(record["committed_post_capacity_m3"])
        committed_destination_count = int(record["committed_destination_count"])
        residual_supply = max(0.0, gross_post - committed_post)
        terminal_country = countries.get(project_id)
        if gross_post > 0:
            rows.append({
                "scenario": RESIDUAL_SUPPLY_SCENARIO,
                "source_project_id": project_id,
                "source_terminal_name": terminal_name,
                "source_country": terminal_country,
                "gross_post_capacity_m3": gross_post,
                "committed_post_capacity_m3": committed_post,
                "committed_destination_count": committed_destination_count,
                "supply_capacity_m3": residual_supply,
                "gross_post_k_m3": gross_post / CAPACITY_SCALE_M3,
                "committed_post_k_m3": committed_post / CAPACITY_SCALE_M3,
                "supply_k_m3": residual_supply / CAPACITY_SCALE_M3,
                "supply_basis": (
                    "gross observed post-period voyage capacity minus capacity "
                    "committed to each voyage's recorded destination"
                ),
            })
    return pd.DataFrame(rows, columns=SUPPLY_COLUMNS).sort_values(
        ["scenario", "source_project_id"]
    ).reset_index(drop=True)


def route_cost_matrix(
    routes: pd.DataFrame,
    voyages: pd.DataFrame,
    source_nodes: pd.DataFrame,
) -> pd.DataFrame:
    """Cheapest audited route from each source terminal to each destination basin."""
    destination_basin = (
        voyages[["destination_project_id", "destination_basin"]]
        .dropna()
        .drop_duplicates()
    )
    routes = routes.copy()
    routes["distance_accepted_expanded"] = _as_bool(routes["distance_accepted_expanded"])
    accepted = routes[
        routes["distance_accepted_expanded"]
        & routes["modeled_terminal_to_terminal_nm"].notna()
    ].merge(destination_basin, on="destination_project_id", how="inner")

    source_meta = source_nodes[
        ["source_project_id", "source_terminal_name", "source_country"]
    ].drop_duplicates()
    accepted = accepted.merge(
        source_meta,
        left_on="project_id",
        right_on="source_project_id",
        how="inner",
    )
    if accepted.empty:
        return pd.DataFrame(columns=COST_COLUMNS)

    idx = accepted.groupby(["source_project_id", "destination_basin"])[
        "modeled_terminal_to_terminal_nm"
    ].idxmin()
    best = accepted.loc[idx].copy()
    best["route_nm"] = best["modeled_terminal_to_terminal_nm"].astype(float)
    best["route_cost_note"] = (
        "minimum expanded-accepted terminal route to any observed basin terminal"
    )
    return best[COST_COLUMNS].sort_values(
        ["source_project_id", "destination_basin"]
    ).reset_index(drop=True)


def build_transport_inputs(
    voyages: pd.DataFrame,
    routes: pd.DataFrame,
    terminals: pd.DataFrame | None = None,
) -> TransportInputs:
    supplies = non_gulf_supply_nodes(voyages, terminals=terminals)
    return TransportInputs(
        demands=basin_reallocation_demands(voyages),
        supplies=supplies,
        costs=route_cost_matrix(routes, voyages, supplies),
    )


def solve_reallocation_scenarios(
    inputs: TransportInputs,
    unmet_penalty_multiplier: float = 10.0,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Solve balanced min-cost transport for each supply scenario."""
    solutions: list[dict[str, object]] = []
    summaries: list[dict[str, object]] = []
    demand_map = inputs.demands.set_index("destination_basin")
    max_cost = float(inputs.costs["route_nm"].max()) if not inputs.costs.empty else 1.0
    unmet_penalty = int(math.ceil(max_cost * unmet_penalty_multiplier))

    for scenario, scenario_supply in inputs.supplies.groupby("scenario"):
        scenario_supply = scenario_supply.copy()
        scenario_supply["supply_k_m3_int"] = (
            scenario_supply["supply_k_m3"].round().astype(int)
        )
        demands = inputs.demands.copy()
        demands["lost_hormuz_k_m3_int"] = (
            demands["lost_hormuz_k_m3"].round().astype(int)
        )
        positive_supply = scenario_supply[
            scenario_supply["supply_k_m3_int"] > 0
        ]
        scenario_costs = inputs.costs.merge(
            positive_supply[["source_project_id"]].drop_duplicates(),
            on="source_project_id",
            how="inner",
        )
        demand_basins = set(
            demands.loc[demands["lost_hormuz_k_m3_int"] > 0, "destination_basin"]
        )
        routable_sources = set(
            scenario_costs.loc[
                scenario_costs["destination_basin"].isin(demand_basins),
                "source_project_id",
            ]
        )
        graph_supply = scenario_supply[
            scenario_supply["source_project_id"].isin(routable_sources)
            & scenario_supply["supply_k_m3_int"].gt(0)
        ]
        total_gross_post = float(scenario_supply["gross_post_k_m3"].sum())
        total_committed_post = float(
            scenario_supply["committed_post_k_m3"].sum()
        )
        total_residual_supply = float(scenario_supply["supply_k_m3"].sum())
        total_residual_supply_int = int(
            scenario_supply["supply_k_m3_int"].sum()
        )
        total_supply = int(graph_supply["supply_k_m3_int"].sum())
        total_demand = int(demands["lost_hormuz_k_m3_int"].sum())
        if total_demand <= 0:
            continue

        graph = nx.DiGraph()
        if total_supply > total_demand:
            graph.add_node(SURPLUS_SINK, demand=total_supply - total_demand)
        if total_demand > total_supply:
            graph.add_node(UNMET_SOURCE, demand=-(total_demand - total_supply))

        for row in graph_supply.to_dict("records"):
            supply = int(row["supply_k_m3_int"])
            if supply <= 0:
                continue
            node = str(row["source_project_id"])
            graph.add_node(node, demand=-supply)
            if total_supply > total_demand:
                graph.add_edge(node, SURPLUS_SINK, capacity=supply, weight=0)

        for row in demands.to_dict("records"):
            demand = int(row["lost_hormuz_k_m3_int"])
            if demand <= 0:
                continue
            basin = str(row["destination_basin"])
            graph.add_node(basin, demand=demand)
            if total_demand > total_supply:
                graph.add_edge(
                    UNMET_SOURCE, basin, capacity=demand, weight=unmet_penalty
                )
        for row in scenario_costs.to_dict("records"):
            source = str(row["source_project_id"])
            if source not in graph:
                continue
            basin = str(row["destination_basin"])
            if basin not in graph:
                continue
            source_supply = int(graph.nodes[source]["demand"] * -1)
            basin_demand = int(graph.nodes[basin]["demand"])
            graph.add_edge(
                source,
                basin,
                capacity=min(source_supply, basin_demand),
                weight=int(round(float(row["route_nm"]))),
            )

        _, flow = nx.network_simplex(graph)
        source_meta = scenario_supply.drop_duplicates("source_project_id").set_index(
            "source_project_id"
        )
        cost_meta = scenario_costs.set_index(["source_project_id", "destination_basin"])
        allocated_residual = 0.0
        unmet = 0.0
        transport_cost = 0.0
        baseline_cost = 0.0
        additional_cost = 0.0

        for source, destinations in flow.items():
            for basin, raw_flow in destinations.items():
                if basin == SURPLUS_SINK or raw_flow <= 0:
                    continue
                baseline_nm = float(demand_map.loc[basin, "baseline_hormuz_route_nm"])
                if math.isnan(baseline_nm):
                    baseline_nm = 0.0
                if source == UNMET_SOURCE:
                    route_nm = float("nan")
                    terminal = None
                    country = None
                    flow_type = "unmet"
                    unmet += raw_flow
                    transport = 0.0
                    baseline = 0.0
                    additional = 0.0
                else:
                    meta = source_meta.loc[source]
                    terminal = meta["source_terminal_name"]
                    country = meta["source_country"]
                    route_nm = float(cost_meta.loc[(source, basin), "route_nm"])
                    flow_type = "residual_route_supply"
                    allocated_residual += raw_flow
                    transport = raw_flow * route_nm
                    baseline = raw_flow * baseline_nm
                    additional = raw_flow * (route_nm - baseline_nm)
                    transport_cost += transport
                    baseline_cost += baseline
                    additional_cost += additional
                solutions.append({
                    "scenario": scenario,
                    "source_project_id": None if source == UNMET_SOURCE else source,
                    "source_terminal_name": terminal,
                    "source_country": country,
                    "destination_basin": basin,
                    "flow_k_m3": float(raw_flow),
                    "route_nm": route_nm,
                    "baseline_hormuz_route_nm": baseline_nm,
                    "transport_k_m3_nm": transport,
                    "baseline_equivalent_k_m3_nm": baseline,
                    "additional_k_m3_nm": additional,
                    "flow_type": flow_type,
                })

        uncovered_cost_edges = scenario_costs.empty
        note = "residual_capacity_transport_solution"
        if total_residual_supply_int == 0:
            note += (
                "; no_uncommitted_observed_supply"
                "; observed_post_voyages_reserved_for_recorded_destinations"
            )
        if unmet > 0:
            note += "; unmet_replacement_capacity"
        if total_residual_supply_int > total_supply:
            note += "; unroutable_residual_supply_excluded"
        if uncovered_cost_edges:
            note += "; no_usable_residual_route_cost_edges"
        mean_route = (
            transport_cost / allocated_residual
            if allocated_residual
            else float("nan")
        )
        mean_additional = (
            additional_cost / allocated_residual
            if allocated_residual
            else float("nan")
        )
        if pd.notna(mean_additional) and mean_additional < 0:
            note += "; lower_bound_short_route_pool"
        summaries.append({
            "scenario": scenario,
            "demand_k_m3": float(total_demand),
            "gross_observed_post_k_m3": total_gross_post,
            "committed_observed_post_k_m3": total_committed_post,
            "residual_supply_k_m3": total_residual_supply,
            "allocated_residual_k_m3": allocated_residual,
            "unmet_k_m3": unmet,
            "unmet_share": unmet / total_demand if total_demand else float("nan"),
            "transport_k_m3_nm": transport_cost,
            "baseline_equivalent_k_m3_nm": baseline_cost,
            "additional_k_m3_nm": additional_cost,
            "mean_route_nm": mean_route,
            "mean_additional_nm": mean_additional,
            "n_supply_nodes": int(
                positive_supply["source_project_id"].nunique()
            ),
            "n_cost_edges": int(len(scenario_costs)),
            "coverage_note": note,
        })

    solution_frame = pd.DataFrame(solutions, columns=SOLUTION_COLUMNS).sort_values(
        ["scenario", "flow_type", "destination_basin", "source_terminal_name"],
        na_position="last",
    ).reset_index(drop=True)
    summary_frame = pd.DataFrame(summaries, columns=SUMMARY_COLUMNS).sort_values(
        "scenario"
    ).reset_index(drop=True)
    return solution_frame, summary_frame
