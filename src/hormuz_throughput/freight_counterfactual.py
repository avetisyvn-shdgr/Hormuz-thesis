"""Pre-treatment-selected weekly counterfactuals for secondary freight rates.

These routines estimate forecast deviations, not treatment effects. Model
selection and uncertainty calibration use only observations before the locked
first post-treatment assessment week.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd


CANDIDATES = {
    "last_observation": (),
    "seasonal_naive_52": (52,),
    "ar_lags_1_2_4": (1, 2, 4),
    "ar_lags_1_2_4_52": (1, 2, 4, 52),
}
COMPLEXITY = {name: index for index, name in enumerate(CANDIDATES)}


@dataclass(frozen=True)
class WeeklyValidationDesign:
    initial_train_weeks: int = 104
    horizon_weeks: int = 4
    step_weeks: int = 4
    simplicity_tolerance: float = 0.05
    conformal_coverage: float = 0.90


def _last_finite(values: np.ndarray) -> float:
    finite = values[np.isfinite(values)]
    return float(finite[-1]) if len(finite) else np.nan


def _fit_ar(values: np.ndarray, lags: tuple[int, ...]) -> np.ndarray | None:
    rows: list[list[float]] = []
    targets: list[float] = []
    for index in range(max(lags), len(values)):
        predictors = [values[index - lag] for lag in lags]
        if np.isfinite(values[index]) and np.isfinite(predictors).all():
            rows.append([1.0, *predictors])
            targets.append(float(values[index]))
    if len(rows) < max(30, 2 * (len(lags) + 1)):
        return None
    return np.linalg.lstsq(np.asarray(rows), np.asarray(targets), rcond=None)[0]


def forecast_candidate(
    values: np.ndarray,
    *,
    origin: int,
    horizon: int,
    candidate: str,
) -> np.ndarray:
    """Forecast recursively from ``values[:origin]`` without reading its future."""
    if candidate not in CANDIDATES:
        raise KeyError(f"Unknown candidate {candidate!r}")
    history = np.asarray(values[:origin], dtype=float)
    forecasts: list[float] = []
    if candidate == "last_observation":
        return np.repeat(_last_finite(history), horizon)

    if candidate == "seasonal_naive_52":
        for step in range(horizon):
            source = origin + step - 52
            forecasts.append(float(history[source]) if source >= 0 else np.nan)
        return np.asarray(forecasts)

    lags = CANDIDATES[candidate]
    coefficients = _fit_ar(history, lags)
    if coefficients is None:
        return np.repeat(np.nan, horizon)
    working = history.tolist()
    for _ in range(horizon):
        predictors = [working[-lag] for lag in lags]
        if not np.isfinite(predictors).all():
            prediction = np.nan
        else:
            prediction = float(coefficients[0] + np.dot(coefficients[1:], predictors))
        working.append(prediction)
        forecasts.append(prediction)
    return np.asarray(forecasts)


def _scale(values: np.ndarray) -> float:
    pairwise = np.abs(np.diff(values))
    valid = pairwise[np.isfinite(pairwise)]
    scale = float(valid.mean()) if len(valid) else np.nan
    return scale if scale > 0 else np.nan


def rolling_origin_validation(
    values: np.ndarray,
    dates: pd.DatetimeIndex,
    *,
    pre_end: int,
    design: WeeklyValidationDesign,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Score the fixed candidate set using only pre-treatment folds."""
    rows: list[dict[str, Any]] = []
    last_origin = pre_end - design.horizon_weeks
    for origin in range(design.initial_train_weeks, last_origin + 1, design.step_weeks):
        actual = values[origin : origin + design.horizon_weeks]
        scale = _scale(values[:origin])
        for candidate in CANDIDATES:
            predicted = forecast_candidate(
                values, origin=origin, horizon=design.horizon_weeks, candidate=candidate
            )
            valid = np.isfinite(actual) & np.isfinite(predicted)
            errors = actual[valid] - predicted[valid]
            rows.append(
                {
                    "row_type": "fold",
                    "candidate": candidate,
                    "origin_week": dates[origin - 1].date().isoformat(),
                    "test_start_week": dates[origin].date().isoformat(),
                    "test_end_week": dates[origin + design.horizon_weeks - 1].date().isoformat(),
                    "scored_observations": int(valid.sum()),
                    "mae": float(np.abs(errors).mean()) if len(errors) else np.nan,
                    "rmse": float(np.sqrt(np.mean(errors**2))) if len(errors) else np.nan,
                    "mase": (
                        float(np.abs(errors).mean() / scale)
                        if len(errors) and np.isfinite(scale)
                        else np.nan
                    ),
                }
            )
    folds = pd.DataFrame(rows)
    expected = int(folds["origin_week"].nunique() * design.horizon_weeks)
    summaries: list[dict[str, Any]] = []
    for candidate, group in folds.groupby("candidate", sort=False):
        summaries.append(
            {
                "row_type": "aggregate",
                "candidate": candidate,
                "origin_week": None,
                "test_start_week": None,
                "test_end_week": None,
                "scored_observations": int(group["scored_observations"].sum()),
                "expected_scored_observations": expected,
                "coverage_ratio": (
                    float(group["scored_observations"].sum() / expected)
                    if expected
                    else np.nan
                ),
                "mae": float(group["mae"].mean()),
                "rmse": float(group["rmse"].mean()),
                "mase": float(group["mase"].mean()),
            }
        )
    aggregate = pd.DataFrame(summaries)
    return folds, aggregate


def select_candidate(
    aggregate: pd.DataFrame, *, simplicity_tolerance: float
) -> str:
    eligible = aggregate.loc[
        aggregate["coverage_ratio"].ge(0.90) & aggregate["mase"].notna()
    ].copy()
    if eligible.empty:
        raise ValueError("No candidate has adequate pre-treatment validation coverage")
    best = float(eligible["mase"].min())
    near_best = eligible.loc[eligible["mase"].le(best * (1 + simplicity_tolerance))]
    return min(near_best["candidate"], key=lambda name: COMPLEXITY[name])


def _validation_residuals(
    values: np.ndarray,
    folds: pd.DataFrame,
    candidate: str,
    dates: pd.DatetimeIndex,
    horizon: int,
) -> np.ndarray:
    residuals: list[float] = []
    date_to_index = {date.date().isoformat(): index for index, date in enumerate(dates)}
    selected = folds.loc[folds["candidate"].eq(candidate)]
    for row in selected.itertuples(index=False):
        origin = date_to_index[row.test_start_week]
        predicted = forecast_candidate(
            values,
            origin=origin,
            horizon=len(values[origin : origin + horizon]),
            candidate=candidate,
        )
        actual = values[origin : origin + len(predicted)]
        valid = np.isfinite(actual) & np.isfinite(predicted)
        residuals.extend((actual[valid] - predicted[valid]).tolist())
    return np.asarray(residuals)


def fit_freight_counterfactuals(
    data: pd.DataFrame,
    *,
    first_post_week: str,
    series_columns: dict[str, str],
    design: WeeklyValidationDesign | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    """Validate, select, forecast, calibrate, and run time placebos."""
    design = design or WeeklyValidationDesign()
    frame = data.copy()
    frame["week_end"] = pd.to_datetime(frame["week_end"], errors="raise")
    dates = pd.DatetimeIndex(frame["week_end"])
    first_post = pd.Timestamp(first_post_week)
    post_indices = np.flatnonzero(dates >= first_post)
    if not len(post_indices):
        raise ValueError("No post-treatment assessment weeks")
    pre_end = int(post_indices[0])
    post_horizon = len(dates) - pre_end

    all_scores: list[pd.DataFrame] = []
    weekly_rows: list[pd.DataFrame] = []
    summary_rows: list[dict[str, Any]] = []
    placebo_rows: list[dict[str, Any]] = []
    selections: dict[str, str] = {}

    for series, column in series_columns.items():
        values = frame[column].to_numpy(dtype=float)
        folds, aggregate = rolling_origin_validation(
            values, dates, pre_end=pre_end, design=design
        )
        selected = select_candidate(
            aggregate, simplicity_tolerance=design.simplicity_tolerance
        )
        selections[series] = selected
        aggregate["selected"] = aggregate["candidate"].eq(selected)
        folds["selected"] = folds["candidate"].eq(selected)
        scores = pd.concat([folds, aggregate], ignore_index=True, sort=False)
        scores.insert(0, "series", series)
        all_scores.append(scores)

        predicted = forecast_candidate(
            values, origin=pre_end, horizon=post_horizon, candidate=selected
        )
        residuals = _validation_residuals(
            values, folds, selected, dates, design.horizon_weeks
        )
        absolute_residuals = np.abs(residuals[np.isfinite(residuals)])
        if not len(absolute_residuals):
            raise ValueError(f"No validation residuals for {series}")
        radius = float(
            np.quantile(absolute_residuals, design.conformal_coverage, method="higher")
        )
        observed = values[pre_end:]
        weekly = pd.DataFrame(
            {
                "week_end": dates[pre_end:],
                "series": series,
                "selected_model": selected,
                "observed_usd_per_day": observed,
                "counterfactual_usd_per_day": predicted,
                "lower_90_usd_per_day": predicted - radius,
                "upper_90_usd_per_day": predicted + radius,
                "deviation_usd_per_day": observed - predicted,
            }
        )
        weekly_rows.append(weekly)
        valid = np.isfinite(observed) & np.isfinite(predicted)
        inside = (
            observed[valid] >= predicted[valid] - radius
        ) & (observed[valid] <= predicted[valid] + radius)
        selected_score = aggregate.loc[aggregate["candidate"].eq(selected)].iloc[0]
        summary_rows.append(
            {
                "series": series,
                "selected_model": selected,
                "post_observations": int(valid.sum()),
                "average_deviation_usd_per_day": float((observed[valid] - predicted[valid]).mean()),
                "cumulative_deviation_usd_per_day_weeks": float((observed[valid] - predicted[valid]).sum()),
                "mean_observed_usd_per_day": float(observed[valid].mean()),
                "mean_counterfactual_usd_per_day": float(predicted[valid].mean()),
                "conformal_radius_usd_per_day": radius,
                "pointwise_interval_coverage": float(inside.mean()),
                "pointwise_interval_exceedances": int((~inside).sum()),
                "validation_mase": float(selected_score["mase"]),
                "causal_effect_interpretation_permitted": False,
            }
        )

        for origin in range(
            design.initial_train_weeks,
            pre_end - post_horizon + 1,
            design.step_weeks,
        ):
            placebo_predicted = forecast_candidate(
                values, origin=origin, horizon=post_horizon, candidate=selected
            )
            placebo_actual = values[origin : origin + post_horizon]
            placebo_valid = np.isfinite(placebo_actual) & np.isfinite(placebo_predicted)
            if placebo_valid.sum() < int(np.ceil(0.80 * post_horizon)):
                continue
            deviations = placebo_actual[placebo_valid] - placebo_predicted[placebo_valid]
            placebo_rows.append(
                {
                    "series": series,
                    "selected_model": selected,
                    "pseudo_cutoff_week": dates[origin].date().isoformat(),
                    "horizon_weeks": post_horizon,
                    "scored_observations": int(placebo_valid.sum()),
                    "average_deviation_usd_per_day": float(deviations.mean()),
                    "cumulative_deviation_usd_per_day_weeks": float(deviations.sum()),
                }
            )

    summary_frame = pd.DataFrame(summary_rows)
    placebo_frame = pd.DataFrame(placebo_rows)
    for index, row in summary_frame.iterrows():
        placebo = placebo_frame.loc[placebo_frame["series"].eq(row["series"])]
        exceedances = placebo["average_deviation_usd_per_day"].abs().ge(
            abs(row["average_deviation_usd_per_day"])
        ).sum()
        summary_frame.loc[index, "time_placebo_count"] = int(len(placebo))
        summary_frame.loc[index, "two_sided_placebo_p_value"] = (
            float((1 + exceedances) / (1 + len(placebo)))
            if len(placebo)
            else np.nan
        )

    manifest = {
        "schema_version": 1,
        "design": {
            "initial_train_weeks": design.initial_train_weeks,
            "validation_horizon_weeks": design.horizon_weeks,
            "validation_step_weeks": design.step_weeks,
            "candidate_models": list(CANDIDATES),
            "simplicity_tolerance": design.simplicity_tolerance,
            "pointwise_conformal_coverage": design.conformal_coverage,
            "missing_policy": "score available observations; never impute or carry rates",
            "post_lag_policy": "recursive forecasts never use observed post-treatment lags",
        },
        "first_post_week": first_post.date().isoformat(),
        "post_horizon_weeks": post_horizon,
        "selected_models": selections,
        "claim_boundary": (
            "Disruption-associated counterfactual deviations in assessed rates; "
            "not ATT or identified causal freight effects."
        ),
    }
    return (
        pd.concat(all_scores, ignore_index=True, sort=False),
        pd.concat(weekly_rows, ignore_index=True),
        summary_frame,
        placebo_frame,
        manifest,
    )
