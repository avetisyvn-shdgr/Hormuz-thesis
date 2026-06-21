"""Nominal LNG capacity-nautical miles from inferred terminal sequences."""
from __future__ import annotations

from statistics import NormalDist
from typing import Any

import numpy as np
import pandas as pd

from .routes import PAIR_COLUMNS, RESOLVED_STATUS


def validate_carrier_capacity_frame(carriers: pd.DataFrame) -> dict[str, Any]:
    """Fail on ambiguous IMO joins or unusable nominal capacity values."""
    required = {"imo", "capacity_m3"}
    missing = required.difference(carriers.columns)
    if missing:
        raise ValueError(f"Carrier frame missing columns: {sorted(missing)}")
    if carriers["imo"].isna().any():
        raise ValueError("Carrier frame contains missing IMO values.")
    duplicates = carriers["imo"].astype(str).duplicated(keep=False)
    if duplicates.any():
        duplicate_imos = sorted(carriers.loc[duplicates, "imo"].astype(str).unique())
        raise ValueError(f"Carrier frame contains duplicate IMOs: {duplicate_imos[:10]}")
    capacity = pd.to_numeric(carriers["capacity_m3"], errors="coerce")
    invalid = capacity.isna() | capacity.le(0)
    if invalid.any():
        raise ValueError(f"Carrier frame contains {int(invalid.sum())} invalid capacities.")
    return {
        "carrier_rows": int(len(carriers)),
        "unique_imos": int(carriers["imo"].astype(str).nunique()),
        "invalid_capacity_rows": 0,
        "duplicate_imos": 0,
    }


def attach_capacity_nautical_miles(
    voyages: pd.DataFrame,
    routes: pd.DataFrame,
    carriers: pd.DataFrame,
) -> pd.DataFrame:
    """Join audited route and capacity data without dropping excluded voyages."""
    required_voyage = set(PAIR_COLUMNS + [
        "imo", "sample_period", "event_id", "endpoint_status",
        "terminal_match_radius_km",
    ])
    missing = required_voyage.difference(voyages.columns)
    if missing:
        raise ValueError(f"Voyages missing columns: {sorted(missing)}")
    required_route = set(PAIR_COLUMNS + [
        "modeled_terminal_to_terminal_nm", "route_status",
        "distance_accepted", "distance_accepted_expanded",
    ])
    missing_routes = required_route.difference(routes.columns)
    if missing_routes:
        raise ValueError(f"Routes missing columns: {sorted(missing_routes)}")

    validate_carrier_capacity_frame(carriers)
    output = voyages.copy()
    output["imo"] = output["imo"].astype(str)
    carrier_subset = carriers.copy()
    carrier_subset["imo"] = carrier_subset["imo"].astype(str)
    output = output.merge(
        carrier_subset[["imo", "capacity_m3", "capacity_reference_missing"]],
        on="imo",
        how="left",
        validate="many_to_one",
    )
    output = output.merge(
        routes[PAIR_COLUMNS + [
            "modeled_route_nm", "modeled_terminal_to_terminal_nm",
            "great_circle_nm", "origin_snap_nm", "destination_snap_nm",
            "route_to_geodesic_ratio", "route_passages", "route_status",
            "distance_accepted", "distance_accepted_expanded",
        ]],
        on=PAIR_COLUMNS,
        how="left",
        validate="many_to_one",
    )
    resolved = output["endpoint_status"].eq(RESOLVED_STATUS)
    strict_route = output["distance_accepted"].eq(True)
    expanded_route = output["distance_accepted_expanded"].eq(True)
    output["capacity_join_status"] = np.select(
        [
            output["capacity_m3"].isna(),
            ~resolved,
            output["route_status"].isna(),
            strict_route,
            expanded_route,
        ],
        [
            "missing_carrier_capacity",
            "endpoint_not_resolved",
            "missing_route_pair",
            "strict_route_accepted",
            "expanded_route_accepted",
        ],
        default="route_excluded",
    )
    strict = (
        resolved
        & output["capacity_m3"].notna()
        & strict_route
    )
    expanded = (
        resolved
        & output["capacity_m3"].notna()
        & expanded_route
    )
    product = output["capacity_m3"] * output["modeled_terminal_to_terminal_nm"]
    output["inferred_nominal_m3_nm_strict"] = product.where(strict)
    output["inferred_nominal_m3_nm_expanded"] = product.where(expanded)
    return output


def capacity_period_summary(voyages: pd.DataFrame) -> pd.DataFrame:
    """Summarize coverage and capacity-distance totals by radius and period."""
    rows: list[dict[str, Any]] = []
    for (radius, period), group in voyages.groupby(
        ["terminal_match_radius_km", "sample_period"], sort=True
    ):
        resolved = group["endpoint_status"].eq(RESOLVED_STATUS)
        right_censored = group["endpoint_status"].eq("right_censored")
        unresolved = ~(resolved | right_censored)
        strict = group["inferred_nominal_m3_nm_strict"].notna()
        expanded = group["inferred_nominal_m3_nm_expanded"].notna()
        rows.append({
            "terminal_match_radius_km": int(radius),
            "sample_period": str(period),
            "export_origin_calls": int(len(group)),
            "resolved_voyages": int(resolved.sum()),
            "right_censored_export_calls": int(right_censored.sum()),
            "unresolved_role_sequences": int(unresolved.sum()),
            "right_censoring_rate": float(right_censored.mean()),
            "unique_resolved_imos": int(group.loc[resolved, "imo"].nunique()),
            "strict_routed_voyages": int(strict.sum()),
            "expanded_routed_voyages": int(expanded.sum()),
            "strict_route_coverage_rate": (
                float(strict.sum() / resolved.sum()) if resolved.any() else 0.0
            ),
            "expanded_route_coverage_rate": (
                float(expanded.sum() / resolved.sum()) if resolved.any() else 0.0
            ),
            "strict_total_nominal_m3_nm": float(
                group["inferred_nominal_m3_nm_strict"].sum(min_count=1)
            ),
            "expanded_total_nominal_m3_nm": float(
                group["inferred_nominal_m3_nm_expanded"].sum(min_count=1)
            ),
            "strict_mean_nominal_m3_nm_per_voyage": float(
                group["inferred_nominal_m3_nm_strict"].mean()
            ),
            "expanded_mean_nominal_m3_nm_per_voyage": float(
                group["inferred_nominal_m3_nm_expanded"].mean()
            ),
        })
    return pd.DataFrame(rows)


def capacity_pre_post_comparison(period_summary: pd.DataFrame) -> pd.DataFrame:
    """Compare equal-window pre/post totals without attaching a causal label."""
    rows: list[dict[str, Any]] = []
    for radius, group in period_summary.groupby("terminal_match_radius_km"):
        indexed = group.set_index("sample_period")
        if not {"pre", "post"}.issubset(indexed.index):
            raise ValueError(f"Radius {radius} does not contain pre and post periods.")
        row: dict[str, Any] = {"terminal_match_radius_km": int(radius)}
        for specification in ("strict", "expanded"):
            total = f"{specification}_total_nominal_m3_nm"
            voyages = f"{specification}_routed_voyages"
            mean = f"{specification}_mean_nominal_m3_nm_per_voyage"
            pre_total = float(indexed.loc["pre", total])
            post_total = float(indexed.loc["post", total])
            pre_voyages = int(indexed.loc["pre", voyages])
            post_voyages = int(indexed.loc["post", voyages])
            pre_mean = float(indexed.loc["pre", mean])
            post_mean = float(indexed.loc["post", mean])
            row.update({
                f"{specification}_pre_total_nominal_m3_nm": pre_total,
                f"{specification}_post_total_nominal_m3_nm": post_total,
                f"{specification}_absolute_change_nominal_m3_nm": post_total - pre_total,
                f"{specification}_percent_change": (
                    (post_total / pre_total - 1.0) * 100 if pre_total else np.nan
                ),
                f"{specification}_pre_routed_voyages": pre_voyages,
                f"{specification}_post_routed_voyages": post_voyages,
                f"{specification}_routed_voyage_percent_change": (
                    (post_voyages / pre_voyages - 1.0) * 100
                    if pre_voyages else np.nan
                ),
                f"{specification}_pre_mean_nominal_m3_nm_per_voyage": pre_mean,
                f"{specification}_post_mean_nominal_m3_nm_per_voyage": post_mean,
                f"{specification}_mean_per_voyage_percent_change": (
                    (post_mean / pre_mean - 1.0) * 100 if pre_mean else np.nan
                ),
            })
        rows.append(row)
    return pd.DataFrame(rows).sort_values("terminal_match_radius_km").reset_index(drop=True)


def cluster_bootstrap_mean_change(
    voyages: pd.DataFrame,
    value_column: str,
    *,
    cluster_column: str = "imo",
    n_draws: int = 5000,
    seed: int = 20260612,
    alpha: float = 0.05,
) -> dict[str, Any]:
    """Carrier-cluster bootstrap for the pre/post mean percent change."""
    required = {cluster_column, "sample_period", value_column}
    missing = required.difference(voyages.columns)
    if missing:
        raise ValueError(f"Bootstrap frame missing columns: {sorted(missing)}")
    if n_draws <= 0 or not 0 < alpha < 1:
        raise ValueError("n_draws must be positive and alpha must be in (0, 1).")
    frame = voyages.loc[
        voyages[value_column].notna() & voyages["sample_period"].isin(["pre", "post"])
    ].copy()
    clusters = frame[cluster_column].dropna().unique()
    if len(clusters) < 3:
        raise ValueError("Need at least three carrier clusters for BCa inference.")

    def statistic(sample: pd.DataFrame) -> float:
        means = sample.groupby("sample_period")[value_column].mean()
        if not {"pre", "post"}.issubset(means.index) or means["pre"] == 0:
            return float("nan")
        return float((means["post"] / means["pre"] - 1.0) * 100.0)

    point = statistic(frame)
    grouped = {key: value for key, value in frame.groupby(cluster_column, sort=False)}
    rng = np.random.default_rng(seed)
    estimates = []
    for _ in range(n_draws):
        selected = rng.choice(clusters, size=len(clusters), replace=True)
        sample = pd.concat([grouped[key] for key in selected], ignore_index=True)
        estimate = statistic(sample)
        if np.isfinite(estimate):
            estimates.append(estimate)
    if len(estimates) < max(100, int(n_draws * 0.9)):
        raise ValueError("Too many invalid bootstrap draws; period support is inadequate.")
    estimates_array = np.asarray(estimates, dtype="float64")
    percentile_lower, percentile_upper = np.quantile(
        estimates_array, [alpha / 2, 1 - alpha / 2]
    )

    # BCa bias correction from the bootstrap distribution and acceleration
    # from a leave-one-carrier-out jackknife.
    normal = NormalDist()
    tail_clip = 1.0 / (2.0 * len(estimates_array))
    proportion_below = float(np.mean(estimates_array < point))
    proportion_below = float(np.clip(proportion_below, tail_clip, 1 - tail_clip))
    bias_correction = normal.inv_cdf(proportion_below)
    jackknife = np.asarray([
        statistic(frame.loc[frame[cluster_column] != cluster])
        for cluster in clusters
    ])
    if not np.isfinite(jackknife).all():
        raise ValueError("Leave-one-cluster jackknife produced invalid estimates.")
    jackknife_center = float(jackknife.mean())
    deviations = jackknife_center - jackknife
    denominator = 6.0 * float(np.sum(deviations**2)) ** 1.5
    acceleration = (
        float(np.sum(deviations**3)) / denominator if denominator > 0 else 0.0
    )

    adjusted_probabilities = []
    for probability in (alpha / 2, 1 - alpha / 2):
        z_alpha = normal.inv_cdf(probability)
        shifted = bias_correction + z_alpha
        denominator_term = 1.0 - acceleration * shifted
        if denominator_term == 0:
            raise ValueError("BCa adjusted quantile is undefined.")
        adjusted = normal.cdf(
            bias_correction + shifted / denominator_term
        )
        adjusted_probabilities.append(float(np.clip(adjusted, 0.0, 1.0)))
    bca_lower, bca_upper = np.quantile(estimates_array, adjusted_probabilities)
    return {
        "point_estimate_percent_change": point,
        "ci_lower": float(bca_lower),
        "ci_upper": float(bca_upper),
        "bca_ci_lower": float(bca_lower),
        "bca_ci_upper": float(bca_upper),
        "percentile_ci_lower": float(percentile_lower),
        "percentile_ci_upper": float(percentile_upper),
        "bca_adjusted_lower_probability": adjusted_probabilities[0],
        "bca_adjusted_upper_probability": adjusted_probabilities[1],
        "bca_bias_correction": float(bias_correction),
        "bca_acceleration": float(acceleration),
        "n_jackknife_clusters": int(len(jackknife)),
        "confidence_level": float(1 - alpha),
        "n_bootstrap_draws_requested": int(n_draws),
        "n_bootstrap_draws_valid": int(len(estimates)),
        "n_clusters": int(len(clusters)),
        "cluster_column": cluster_column,
        "interval_method": "carrier_cluster_bca_bootstrap",
    }


def route_shift_share_decomposition(
    voyages: pd.DataFrame,
    value_column: str,
    *,
    route_columns: tuple[str, ...] = ("project_id", "destination_project_id"),
) -> dict[str, Any]:
    """Decompose the mean change on common routes and isolate entry/exit residual.

    The common-support Kitagawa identity splits its mean change into a within-
    route component and a route-share component.  New/dropped routes are kept
    as a separate residual because assigning them a counterfactual within-route
    mean would require an unsupported assumption.
    """
    required = {"sample_period", value_column, *route_columns}
    missing = required.difference(voyages.columns)
    if missing:
        raise ValueError(f"Decomposition frame missing columns: {sorted(missing)}")
    frame = voyages.loc[
        voyages[value_column].notna() & voyages["sample_period"].isin(["pre", "post"])
    ].copy()
    grouped = frame.groupby([*route_columns, "sample_period"])[value_column].agg(
        route_mean="mean", voyages="size"
    ).reset_index()
    means = grouped.pivot(index=list(route_columns), columns="sample_period", values="route_mean")
    counts = grouped.pivot(index=list(route_columns), columns="sample_period", values="voyages").fillna(0)
    common = means.dropna(subset=["pre", "post"]).index
    if len(common) == 0:
        raise ValueError("No common pre/post routes for shift-share decomposition.")
    m0, m1 = means.loc[common, "pre"], means.loc[common, "post"]
    s0 = counts.loc[common, "pre"] / counts.loc[common, "pre"].sum()
    s1 = counts.loc[common, "post"] / counts.loc[common, "post"].sum()
    within = float((((s0 + s1) / 2) * (m1 - m0)).sum())
    between = float((((m0 + m1) / 2) * (s1 - s0)).sum())
    common_pre = float((s0 * m0).sum())
    common_post = float((s1 * m1).sum())
    overall = frame.groupby("sample_period")[value_column].mean()
    overall_change = float(overall["post"] - overall["pre"])
    common_change = common_post - common_pre
    return {
        "pre_overall_mean": float(overall["pre"]),
        "post_overall_mean": float(overall["post"]),
        "overall_absolute_change": overall_change,
        "overall_percent_change": float((overall["post"] / overall["pre"] - 1) * 100),
        "common_route_within_change": within,
        "common_route_composition_change": between,
        "common_route_total_change": common_change,
        "entry_exit_route_residual": float(overall_change - common_change),
        "n_pre_routes": int((counts["pre"] > 0).sum()),
        "n_post_routes": int((counts["post"] > 0).sum()),
        "n_common_routes": int(len(common)),
        "identity_error": float(common_change - within - between),
        "within_interpretation": (
            "Within identical terminal pairs, modeled distance is fixed; this "
            "term reflects vessel-capacity mix, not route elongation."
        ),
    }
