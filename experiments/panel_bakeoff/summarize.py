"""Validate and summarize the complete panel bake-off."""
from __future__ import annotations

import json
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from .protocol import OUTPUT_DIR


KEYS = ["panel", "fold", "horizon", "portname", "vessel_class"]
NOMINAL_COVERAGE = 0.95
BOOTSTRAP_DRAWS = 5000
BOOTSTRAP_SEED = 20260829


def conformal_quantile(values: pd.Series, nominal: float = NOMINAL_COVERAGE) -> float:
    finite = values[np.isfinite(values.to_numpy(dtype="float64"))].to_numpy(dtype="float64")
    if len(finite) == 0:
        return float("nan")
    order = min(int(np.ceil((len(finite) + 1) * nominal)), len(finite))
    return float(np.partition(finite, order - 1)[order - 1])


def add_sequential_common_intervals(daily: pd.DataFrame) -> pd.DataFrame:
    """Use only earlier outer folds to calibrate symmetric scaled intervals."""
    daily = daily.copy()
    daily["fold_number"] = daily["fold"].str.extract(r"(\d+)$").astype(int)
    daily["abs_standardized_error"] = (
        (daily["y_true"] - daily["y_pred"]).abs() / daily["mase_scale"]
    )
    daily["common_q"] = np.nan
    grouping = ["model", "panel", "horizon", "vessel_class"]
    for _, positions in daily.groupby(grouping, sort=False).groups.items():
        positions = np.asarray(list(positions), dtype=int)
        block = daily.loc[positions]
        fold_numbers = sorted(block["fold_number"].unique())
        for fold_number in fold_numbers[1:]:
            prior = block[block["fold_number"] < fold_number]
            quantiles = prior.groupby("lead")["abs_standardized_error"].apply(conformal_quantile)
            current_positions = block.index[block["fold_number"] == fold_number]
            daily.loc[current_positions, "common_q"] = daily.loc[current_positions, "lead"].map(quantiles)
    radius = daily["common_q"] * daily["mase_scale"]
    daily["common_lower"] = np.maximum(0.0, daily["y_pred"] - radius)
    daily["common_upper"] = daily["y_pred"] + radius
    valid = daily["common_q"].notna()
    daily["common_covered"] = np.nan
    daily.loc[valid, "common_covered"] = (
        (daily.loc[valid, "y_true"] >= daily.loc[valid, "common_lower"])
        & (daily.loc[valid, "y_true"] <= daily.loc[valid, "common_upper"])
    ).astype(float)
    daily["common_width_scaled"] = (
        (daily["common_upper"] - daily["common_lower"]) / daily["mase_scale"]
    )
    return daily


def interval_scores(daily: pd.DataFrame) -> pd.DataFrame:
    valid = daily[daily["common_q"].notna()].copy()
    group_columns = ["model", "league", *KEYS]
    common = (
        valid.groupby(group_columns, as_index=False)
        .agg(
            common_95_coverage=("common_covered", "mean"),
            common_width_scaled=("common_width_scaled", "mean"),
            n_coverage_days=("common_covered", "size"),
        )
    )
    native_rows = daily[daily.get("native_covered", pd.Series(index=daily.index, dtype=float)).notna()]
    if len(native_rows):
        native = (
            native_rows.groupby(group_columns, as_index=False)
            .agg(native_95_coverage=("native_covered", "mean"))
        )
        common = common.merge(native, on=group_columns, how="left", validate="one_to_one")
    else:
        common["native_95_coverage"] = np.nan
    return common


def performance_distribution(scores: pd.DataFrame, intervals: pd.DataFrame) -> pd.DataFrame:
    group_columns = ["model", "league", "panel", "horizon"]
    summary = (
        scores.groupby(group_columns, as_index=False)
        .agg(
            n_unit_windows=("mase", "size"),
            mase_mean=("mase", "mean"),
            mase_median=("mase", "median"),
            mase_q25=("mase", lambda values: values.quantile(0.25)),
            mase_q75=("mase", lambda values: values.quantile(0.75)),
            horizon_bias_mase_mean=("horizon_bias_mase", "mean"),
            horizon_abs_bias_mase_mean=("horizon_bias_mase", lambda values: values.abs().mean()),
        )
    )
    interval_summary = (
        intervals.groupby(group_columns, as_index=False)
        .agg(
            common_95_coverage=("common_95_coverage", "mean"),
            common_width_scaled=("common_width_scaled", "mean"),
            n_interval_unit_windows=("common_95_coverage", "size"),
            native_95_coverage=("native_95_coverage", "mean"),
        )
    )
    return summary.merge(interval_summary, on=group_columns, how="left", validate="one_to_one")


def paired_comparison(
    scores: pd.DataFrame,
    challenger: str,
    baseline: str,
    comparison: str,
) -> pd.DataFrame:
    left = scores[scores["model"] == challenger]
    right = scores[scores["model"] == baseline]
    paired = left.merge(
        right,
        on=KEYS,
        suffixes=("_challenger", "_baseline"),
        validate="one_to_one",
    )
    if paired.empty:
        return pd.DataFrame()
    rows = []
    for (panel, horizon), group in paired.groupby(["panel", "horizon"], sort=False):
        ports = sorted(group["portname"].unique())
        fold_names = sorted(group["fold"].unique())
        classes = sorted(group["vessel_class"].unique())
        complete_index = pd.MultiIndex.from_product(
            [ports, fold_names, classes], names=["portname", "fold", "vessel_class"]
        )
        indexed = group.set_index(["portname", "fold", "vessel_class"])
        if not indexed.index.is_unique or not indexed.index.equals(complete_index):
            indexed = indexed.reindex(complete_index)
        challenger_array = indexed["mase_challenger"].to_numpy().reshape(
            len(ports), len(fold_names), len(classes)
        )
        baseline_array = indexed["mase_baseline"].to_numpy().reshape(
            len(ports), len(fold_names), len(classes)
        )
        if not np.isfinite(challenger_array).all() or not np.isfinite(baseline_array).all():
            raise ValueError(f"Incomplete paired cube for {challenger} vs {baseline}.")
        seed_offset = int(horizon) + sum(map(ord, challenger + baseline + str(panel)))
        rng = np.random.default_rng(BOOTSTRAP_SEED + seed_offset)
        reductions = np.empty(BOOTSTRAP_DRAWS, dtype="float64")
        for draw in range(BOOTSTRAP_DRAWS):
            sampled_ports = rng.integers(0, len(ports), size=len(ports))
            sampled_folds = rng.integers(0, len(fold_names), size=len(fold_names))
            sampled_challenger = challenger_array[sampled_ports][:, sampled_folds, :]
            sampled_baseline = baseline_array[sampled_ports][:, sampled_folds, :]
            reductions[draw] = 1.0 - sampled_challenger.mean() / sampled_baseline.mean()
        threshold = 0.02 if comparison == "multivariate_vs_univariate_chronos" else 0.05
        rows.append(
            {
                    "panel": panel,
                    "horizon": horizon,
                    "comparison": comparison,
                    "challenger": challenger,
                    "baseline": baseline,
                    "n_pairs": len(group),
                    "challenger_mean_mase": group["mase_challenger"].mean(),
                    "baseline_mean_mase": group["mase_baseline"].mean(),
                    "mean_mase_reduction": 1.0
                    - group["mase_challenger"].mean() / group["mase_baseline"].mean(),
                    "paired_win_rate": (group["mase_challenger"] < group["mase_baseline"]).mean(),
                    "median_paired_mase_difference": (
                        group["mase_challenger"] - group["mase_baseline"]
                    ).median(),
                    "cluster_bootstrap_reduction_ci_lower": float(np.quantile(reductions, 0.025)),
                    "cluster_bootstrap_reduction_ci_upper": float(np.quantile(reductions, 0.975)),
                    "cluster_bootstrap_probability_meets_threshold": float(
                        np.mean(reductions >= threshold)
                    ),
                }
        )
    return pd.DataFrame(rows)


def build_paired_table(scores: pd.DataFrame) -> pd.DataFrame:
    specifications = (
        ("chronos2_univariate", "ar_lag1_7", "chronos_vs_ar17"),
        ("chronos2_multivariate_5class", "ar_lag1_7", "chronos_vs_ar17"),
        (
            "chronos2_multivariate_5class",
            "chronos2_univariate",
            "multivariate_vs_univariate_chronos",
        ),
        ("interactive_fixed_effects", "synthetic_control", "latent_factor_vs_synthetic"),
        ("nuclear_norm_mc", "synthetic_control", "latent_factor_vs_synthetic"),
    )
    frames = [paired_comparison(scores, *specification) for specification in specifications]
    return pd.concat([frame for frame in frames if len(frame)], ignore_index=True)


def admission_decisions(
    performance: pd.DataFrame,
    paired: pd.DataFrame,
) -> pd.DataFrame:
    rows = []
    primary = paired[paired["panel"] == "composition_28x5"]
    for (comparison, challenger, baseline), group in primary.groupby(
        ["comparison", "challenger", "baseline"], sort=False
    ):
        required_reduction = 0.02 if comparison == "multivariate_vs_univariate_chronos" else 0.05
        checks = []
        details = []
        for horizon in (30, 130):
            item = group[group["horizon"] == horizon]
            if len(item) != 1:
                checks.append(False)
                details.append(f"h{horizon}:missing_pair")
                continue
            item = item.iloc[0]
            reduction_ok = float(item["mean_mase_reduction"]) >= required_reduction
            win_ok = (
                True
                if comparison == "multivariate_vs_univariate_chronos"
                else float(item["paired_win_rate"]) > 0.50
            )
            challenger_perf = performance[
                (performance["panel"] == "composition_28x5")
                & (performance["horizon"] == horizon)
                & (performance["model"] == challenger)
            ].iloc[0]
            coverage_error = abs(float(challenger_perf["common_95_coverage"]) - 0.95)
            coverage_ok = coverage_error <= 0.05
            if comparison == "chronos_vs_ar17":
                baseline_perf = performance[
                    (performance["panel"] == "composition_28x5")
                    & (performance["horizon"] == horizon)
                    & (performance["model"] == baseline)
                ].iloc[0]
                width_ratio = float(challenger_perf["common_width_scaled"]) / float(
                    baseline_perf["common_width_scaled"]
                )
                width_ok = width_ratio <= 1.10
            else:
                width_ratio = np.nan
                width_ok = True
            if comparison == "multivariate_vs_univariate_chronos":
                baseline_perf = performance[
                    (performance["panel"] == "composition_28x5")
                    & (performance["horizon"] == horizon)
                    & (performance["model"] == baseline)
                ].iloc[0]
                baseline_coverage_error = abs(float(baseline_perf["common_95_coverage"]) - 0.95)
                coverage_ok = coverage_error <= baseline_coverage_error + 1e-12
            passed = reduction_ok and win_ok and coverage_ok and width_ok
            checks.append(passed)
            details.append(
                f"h{horizon}:reduction={item['mean_mase_reduction']:.4f},"
                f"win={item['paired_win_rate']:.4f},coverage={challenger_perf['common_95_coverage']:.4f},"
                f"width_ratio={width_ratio:.4f},pass={passed}"
            )
        rows.append(
            {
                "comparison": comparison,
                "challenger": challenger,
                "baseline": baseline,
                "admitted": bool(all(checks)),
                "details": " | ".join(details),
            }
        )
    return pd.DataFrame(rows)


def validate(scores: pd.DataFrame, daily: pd.DataFrame) -> dict:
    expected_models = {
        "seasonal_naive_7d",
        "ar_lag1_7",
        "synthetic_control",
        "interactive_fixed_effects",
        "nuclear_norm_mc",
        "chronos2_univariate",
        "chronos2_multivariate_5class",
    }
    composition_models = set(scores.loc[scores["panel"] == "composition_28x5", "model"])
    if composition_models != expected_models:
        raise ValueError(f"Incomplete composition model set: {sorted(composition_models)}")
    duplicate_scores = int(scores.duplicated(["model", *KEYS]).sum())
    duplicate_daily = int(daily.duplicated(["model", *KEYS, "date"]).sum())
    if duplicate_scores or duplicate_daily:
        raise ValueError(
            f"Duplicate result keys: score={duplicate_scores}, daily={duplicate_daily}."
        )
    truth_variation = (
        daily.groupby([*KEYS, "date"])["y_true"].agg(lambda values: values.max() - values.min()).max()
    )
    if float(truth_variation) != 0.0:
        raise ValueError("Models were not scored against identical observed values.")
    model_counts = (
        scores.groupby(["panel", "horizon", "model"]).size().rename("n").reset_index()
    )
    return {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "score_rows": len(scores),
        "daily_rows": len(daily),
        "duplicate_score_keys": duplicate_scores,
        "duplicate_daily_keys": duplicate_daily,
        "maximum_truth_disagreement": float(truth_variation),
        "composition_models": sorted(composition_models),
        "model_cell_counts": model_counts.to_dict(orient="records"),
        "coverage_protocol": (
            "lead-specific symmetric absolute-error intervals, scaled by each unit-series' "
            "training MASE denominator and calibrated using earlier outer folds only; spatial "
            "pooling is within vessel class, so coverage is an empirical diagnostic rather than "
            "a formal exchangeability guarantee"
        ),
        "paired_uncertainty_protocol": (
            "5000-draw product cluster bootstrap resampling chokepoints and rolling origins "
            "independently with replacement; all vessel classes remain nested within the "
            "resampled chokepoint-origin cells"
        ),
    }


def main() -> None:
    classical_scores = pd.read_csv(OUTPUT_DIR / "classical_scores.csv", parse_dates=["origin"])
    chronos_scores = pd.read_csv(OUTPUT_DIR / "chronos_scores.csv", parse_dates=["origin"])
    scores = pd.concat([classical_scores, chronos_scores], ignore_index=True)
    classical_daily = pd.read_csv(
        OUTPUT_DIR / "classical_forecasts.csv.gz", parse_dates=["origin", "date"]
    )
    chronos_daily = pd.read_csv(
        OUTPUT_DIR / "chronos_forecasts.csv.gz", parse_dates=["origin", "date"]
    )
    daily = pd.concat([classical_daily, chronos_daily], ignore_index=True)
    audit = validate(scores, daily)
    daily = add_sequential_common_intervals(daily)
    intervals = interval_scores(daily)
    performance = performance_distribution(scores, intervals)
    paired = build_paired_table(scores)
    decisions = admission_decisions(performance, paired)

    intervals.to_csv(OUTPUT_DIR / "interval_scores.csv", index=False)
    performance.to_csv(OUTPUT_DIR / "performance_distribution.csv", index=False)
    paired.to_csv(OUTPUT_DIR / "paired_comparisons.csv", index=False)
    decisions.to_csv(OUTPUT_DIR / "admission_decisions.csv", index=False)
    (OUTPUT_DIR / "validation_report.json").write_text(
        json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(performance.to_string(index=False))
    print("\nAdmission decisions")
    print(decisions.to_string(index=False))


if __name__ == "__main__":
    main()
