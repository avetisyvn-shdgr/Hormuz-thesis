"""Run transparent forecasts and donor-assisted panel estimators.

Usage
-----
.venv/bin/python -m experiments.panel_bakeoff.run_classical
"""
from __future__ import annotations

import json
import platform
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from .models import (
    interactive_fixed_effects,
    nuclear_norm_completion,
    recursive_ar17,
    seasonal_naive,
    synthetic_control,
)
from .protocol import (
    CALIBRATION_START,
    EXPLICIT_CLASSES,
    HORIZONS,
    OUTPUT_DIR,
    RAW_PATH,
    SEASON_LENGTH,
    composition_wide,
    file_sha256,
    folds,
    load_raw_panel,
    mase_scale,
    port_groups,
    total_wide,
)


IFE_RANKS = (1, 2, 3, 5, 8, 12, 16)
MC_LAMBDA_FRACTIONS = (0.005, 0.01, 0.02, 0.05, 0.10, 0.20, 0.35, 0.50)


def _mask_for_group(columns: pd.MultiIndex, groups: dict[str, int], group: int) -> np.ndarray:
    return np.array([groups[str(port)] == group for port, _ in columns], dtype=bool)


def _macro_mase(
    actual: np.ndarray,
    prediction: np.ndarray,
    train: np.ndarray,
    missing_columns: np.ndarray,
) -> list[float]:
    values = []
    missing_indices = np.flatnonzero(missing_columns)
    for local_index, column_index in enumerate(missing_indices):
        scale = mase_scale(train[:, column_index])
        values.append(float(np.mean(np.abs(actual[:, column_index] - prediction[:, local_index])) / scale))
    return values


def calibrate_panel(panel_name: str, wide: pd.DataFrame) -> tuple[pd.DataFrame, dict[int, dict[str, float]]]:
    """Choose one hard rank and one nuclear penalty on a reserved 2022 block."""
    groups = port_groups(wide.columns)
    rows: list[dict] = []
    selected: dict[int, dict[str, float]] = {}
    train_frame = wide.loc[wide.index < CALIBRATION_START]
    train = train_frame.to_numpy(dtype="float64")

    for horizon in HORIZONS:
        dates = pd.date_range(CALIBRATION_START, periods=horizon, freq="D")
        future = wide.loc[dates].to_numpy(dtype="float64")
        ife_scores: dict[int, list[float]] = {rank: [] for rank in IFE_RANKS}
        mc_scores: dict[float, list[float]] = {penalty: [] for penalty in MC_LAMBDA_FRACTIONS}
        mc_diagnostics: dict[float, list[tuple[int, int]]] = {
            penalty: [] for penalty in MC_LAMBDA_FRACTIONS
        }
        for group in sorted(set(groups.values())):
            missing = _mask_for_group(wide.columns, groups, group)
            for rank in IFE_RANKS:
                prediction = interactive_fixed_effects(train, future, missing, rank)
                ife_scores[rank].extend(_macro_mase(future, prediction, train, missing))
            for penalty in MC_LAMBDA_FRACTIONS:
                prediction, iterations, retained_rank = nuclear_norm_completion(
                    train, future, missing, penalty
                )
                mc_scores[penalty].extend(_macro_mase(future, prediction, train, missing))
                mc_diagnostics[penalty].append((iterations, retained_rank))

        for rank, values in ife_scores.items():
            rows.append(
                {
                    "panel": panel_name,
                    "horizon": horizon,
                    "method": "interactive_fixed_effects",
                    "hyperparameter": "rank",
                    "value": float(rank),
                    "macro_mean_mase": float(np.mean(values)),
                    "macro_median_mase": float(np.median(values)),
                    "n_unit_series": len(values),
                    "mean_iterations": np.nan,
                    "mean_retained_rank": float(rank),
                }
            )
        for penalty, values in mc_scores.items():
            diagnostics = mc_diagnostics[penalty]
            rows.append(
                {
                    "panel": panel_name,
                    "horizon": horizon,
                    "method": "nuclear_norm_mc",
                    "hyperparameter": "lambda_fraction",
                    "value": float(penalty),
                    "macro_mean_mase": float(np.mean(values)),
                    "macro_median_mase": float(np.median(values)),
                    "n_unit_series": len(values),
                    "mean_iterations": float(np.mean([item[0] for item in diagnostics])),
                    "mean_retained_rank": float(np.mean([item[1] for item in diagnostics])),
                }
            )
        selected_rank = min(ife_scores, key=lambda value: np.mean(ife_scores[value]))
        selected_penalty = min(mc_scores, key=lambda value: np.mean(mc_scores[value]))
        selected[horizon] = {
            "ife_rank": float(selected_rank),
            "mc_lambda_fraction": float(selected_penalty),
        }
        print(
            f"calibration panel={panel_name} horizon={horizon}: "
            f"IFE rank={selected_rank}; MC lambda fraction={selected_penalty}",
            flush=True,
        )
    return pd.DataFrame(rows), selected


def _daily_chunk(
    *,
    model: str,
    league: str,
    panel_name: str,
    fold_name: str,
    horizon: int,
    origin: pd.Timestamp,
    port: str,
    vessel_class: str,
    mask_group: int,
    dates: pd.DatetimeIndex,
    actual: np.ndarray,
    prediction: np.ndarray,
    scale: float,
    diagnostics: str = "",
) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "model": model,
            "league": league,
            "panel": panel_name,
            "fold": fold_name,
            "horizon": horizon,
            "origin": origin,
            "portname": port,
            "vessel_class": vessel_class,
            "mask_group": mask_group,
            "date": dates,
            "lead": np.arange(1, horizon + 1),
            "y_true": actual,
            "y_pred": prediction,
            "mase_scale": scale,
            "diagnostics": diagnostics,
        }
    )


def _score_chunk(chunk: pd.DataFrame) -> dict:
    error = chunk["y_pred"].to_numpy() - chunk["y_true"].to_numpy()
    scale = float(chunk["mase_scale"].iloc[0])
    actual_sum = float(chunk["y_true"].sum())
    return {
        **{column: chunk[column].iloc[0] for column in (
            "model", "league", "panel", "fold", "horizon", "origin",
            "portname", "vessel_class", "mask_group", "diagnostics"
        )},
        "mae": float(np.mean(np.abs(error))),
        "rmse": float(np.sqrt(np.mean(error**2))),
        "mase": float(np.mean(np.abs(error)) / scale),
        "horizon_bias_mase": float(np.mean(error) / scale),
        "cumulative_bias": float(np.sum(error)),
        "relative_cumulative_bias": float(np.sum(error) / actual_sum) if actual_sum else np.nan,
        "n_days": len(chunk),
    }


def evaluate_panel(
    panel_name: str,
    wide: pd.DataFrame,
    selected: dict[int, dict[str, float]],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    groups = port_groups(wide.columns)
    daily_chunks: list[pd.DataFrame] = []
    score_rows: list[dict] = []

    for fold in folds(wide.index):
        train_frame = wide.loc[wide.index < fold.origin]
        future_frame = wide.loc[fold.test_dates]
        train = train_frame.to_numpy(dtype="float64")
        future = future_frame.to_numpy(dtype="float64")
        dates = fold.test_dates
        print(
            f"evaluation panel={panel_name} {fold.name} origin={fold.origin.date()} "
            f"horizon={fold.horizon}",
            flush=True,
        )

        # Past-only forecasting league.
        for column_index, (port, vessel_class) in enumerate(wide.columns):
            scale = mase_scale(train[:, column_index])
            for model, prediction in (
                ("seasonal_naive_7d", seasonal_naive(train[:, column_index], fold.horizon)),
                ("ar_lag1_7", recursive_ar17(train[:, column_index], fold.horizon)),
            ):
                chunk = _daily_chunk(
                    model=model,
                    league="past_only_forecast",
                    panel_name=panel_name,
                    fold_name=fold.name,
                    horizon=fold.horizon,
                    origin=fold.origin,
                    port=str(port),
                    vessel_class=str(vessel_class),
                    mask_group=groups[str(port)],
                    dates=dates,
                    actual=future[:, column_index],
                    prediction=prediction,
                    scale=scale,
                )
                daily_chunks.append(chunk)
                score_rows.append(_score_chunk(chunk))

        # Donor-assisted league. Complete chokepoints are masked together.
        for group in sorted(set(groups.values())):
            missing = _mask_for_group(wide.columns, groups, group)
            missing_indices = np.flatnonzero(missing)
            ife_rank = int(selected[fold.horizon]["ife_rank"])
            ife_prediction = interactive_fixed_effects(train, future, missing, ife_rank)
            mc_penalty = float(selected[fold.horizon]["mc_lambda_fraction"])
            mc_prediction, iterations, retained_rank = nuclear_norm_completion(
                train, future, missing, mc_penalty
            )
            for local_index, column_index in enumerate(missing_indices):
                port, vessel_class = wide.columns[column_index]
                scale = mase_scale(train[:, column_index])
                same_class = np.array(
                    [
                        other_class == vessel_class and groups[str(other_port)] != group
                        for other_port, other_class in wide.columns
                    ],
                    dtype=bool,
                )
                synthetic_prediction, weights = synthetic_control(
                    train[:, column_index], train[:, same_class], future[:, same_class]
                )
                specifications = (
                    ("synthetic_control", synthetic_prediction, f"positive_weights={(weights > 1e-8).sum()}"),
                    ("interactive_fixed_effects", ife_prediction[:, local_index], f"rank={ife_rank}"),
                    (
                        "nuclear_norm_mc",
                        mc_prediction[:, local_index],
                        f"lambda_fraction={mc_penalty};iterations={iterations};retained_rank={retained_rank}",
                    ),
                )
                for model, prediction, diagnostics in specifications:
                    chunk = _daily_chunk(
                        model=model,
                        league="contemporaneous_spatial_donors",
                        panel_name=panel_name,
                        fold_name=fold.name,
                        horizon=fold.horizon,
                        origin=fold.origin,
                        port=str(port),
                        vessel_class=str(vessel_class),
                        mask_group=group,
                        dates=dates,
                        actual=future[:, column_index],
                        prediction=prediction,
                        scale=scale,
                        diagnostics=diagnostics,
                    )
                    daily_chunks.append(chunk)
                    score_rows.append(_score_chunk(chunk))
    return pd.DataFrame(score_rows), pd.concat(daily_chunks, ignore_index=True)


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    raw = load_raw_panel()
    panels = {"composition_28x5": composition_wide(raw), "total_28x1": total_wide(raw)}
    all_tuning = []
    selected_by_panel: dict[str, dict[int, dict[str, float]]] = {}
    for panel_name, wide in panels.items():
        tuning, selected = calibrate_panel(panel_name, wide)
        all_tuning.append(tuning)
        selected_by_panel[panel_name] = selected
    tuning_frame = pd.concat(all_tuning, ignore_index=True)
    tuning_frame.to_csv(OUTPUT_DIR / "classical_hyperparameter_calibration.csv", index=False)

    all_scores = []
    all_daily = []
    for panel_name, wide in panels.items():
        scores, daily = evaluate_panel(panel_name, wide, selected_by_panel[panel_name])
        all_scores.append(scores)
        all_daily.append(daily)
    scores = pd.concat(all_scores, ignore_index=True)
    daily = pd.concat(all_daily, ignore_index=True)
    scores.to_csv(OUTPUT_DIR / "classical_scores.csv", index=False)
    daily.to_csv(OUTPUT_DIR / "classical_forecasts.csv.gz", index=False, compression="gzip")

    manifest = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "raw_path": str(RAW_PATH.relative_to(RAW_PATH.parents[2])),
        "raw_sha256": file_sha256(RAW_PATH),
        "python": platform.python_version(),
        "numpy": np.__version__,
        "pandas": pd.__version__,
        "panels": {name: list(wide.shape) for name, wide in panels.items()},
        "explicit_classes": list(EXPLICIT_CLASSES),
        "horizons": list(HORIZONS),
        "selected_hyperparameters": selected_by_panel,
        "n_score_rows": len(scores),
        "n_daily_rows": len(daily),
        "information_sets": {
            "past_only_forecast": ["seasonal_naive_7d", "ar_lag1_7"],
            "contemporaneous_spatial_donors": [
                "synthetic_control", "interactive_fixed_effects", "nuclear_norm_mc"
            ],
        },
    }
    (OUTPUT_DIR / "classical_run_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"wrote {len(scores)} score rows and {len(daily)} daily rows to {OUTPUT_DIR}")


if __name__ == "__main__":
    main()

