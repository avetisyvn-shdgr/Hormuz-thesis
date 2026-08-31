"""AR-only corridor transmission outputs (exploratory, post-cutoff).

This module generates the descriptive corridor-transmission results: for every
eligible corridor it forecasts the post-cutoff window from that corridor's own
pre-cutoff history with the locked AR-only baseline, forms the scaled signed
deviation defined in ``corridor_inference``, and assembles the long-form
statistics that the frozen shared-placebo inference contract consumes.

Discipline preserved here:
- training is always expanding from the frozen ``history_start`` and ends
  strictly before each window's origin (no leakage across the cutoff);
- every corridor is forecast univariately, so one corridor's post-cutoff values
  can never change another corridor's counterfactual (leakage-safe by design);
- the basin layer is point-only and never sums corridors (aggregation is not
  authorised); and
- the outputs are exploratory: the AR-only model is the locked primary estimator
  regardless of any later foundation-model robustness check.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .baselines import arx_forecast
from .corridor_inference import CorridorInferenceProtocol, mean_scaled_signed_deviation
from .metrics import mase
from .spatial import wide_chokepoint_panel
from .validation import Fold

AR_MODEL_NAME = "ar_lag1_7"
AR_Y_LAGS = (1, 7)


def _window_fold(index: pd.DatetimeIndex, history_start, origin, horizon_days) -> Fold:
    """Expanding-history fold: train [history_start, origin), test 94 days from origin."""
    origin = pd.Timestamp(origin)
    history_start = pd.Timestamp(history_start)
    end_excl = origin + pd.Timedelta(days=horizon_days)
    train_pos = np.flatnonzero((index >= history_start) & (index < origin))
    test_pos = np.flatnonzero((index >= origin) & (index < end_excl))
    if len(train_pos) == 0 or len(test_pos) == 0:
        raise ValueError(f"empty fold at origin {origin.date()}.")
    return Fold(
        name=f"win_{origin.date()}",
        train_idx=train_pos,
        test_idx=test_pos,
        train_start=index[train_pos[0]],
        train_end=index[train_pos[-1]],
        test_start=index[test_pos[0]],
        test_end=index[test_pos[-1]],
    )


def ar_window_statistic(
    series: pd.Series,
    *,
    history_start,
    origin,
    horizon_days: int,
    y_lags: tuple[int, ...] = AR_Y_LAGS,
) -> dict[str, object]:
    """AR-only counterfactual and scaled signed deviation for one window.

    The denominator of the statistic is the corridor's own pre-origin observed
    mean, exactly as defined in the inference protocol.
    """
    series = series.sort_index()
    index = series.index
    fold = _window_fold(index, history_start, origin, horizon_days)
    model_frame = series.ffill().bfill().to_frame("value")
    y_pred = arx_forecast(model_frame, "value", fold, exog_cols=[], y_lags=y_lags)
    y_true = series.iloc[fold.test_idx]

    pre = series[index < pd.Timestamp(origin)].dropna()
    if pre.empty or pre.mean() <= 0:
        raise ValueError("pre-origin mean must be finite and positive.")
    pre_mean = float(pre.mean())

    valid = y_true.notna().to_numpy() & y_pred.notna().to_numpy()
    statistic = mean_scaled_signed_deviation(y_true, y_pred, pre_period_mean=pre_mean)
    return {
        "model": AR_MODEL_NAME,
        "statistic_value": statistic,
        "n_scored": int(valid.sum()),
        "train_start": fold.train_start,
        "train_end": fold.train_end,
        "origin": pd.Timestamp(origin),
        "window_end": fold.test_end,
        "pre_period_mean": pre_mean,
        "observed_sum": float(np.nansum(y_true.to_numpy()[valid])),
        "counterfactual_sum": float(np.nansum(y_pred.to_numpy()[valid])),
    }


def build_corridor_statistics(
    protocol: CorridorInferenceProtocol,
    *,
    panel_end: str = "2026-06-01",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return (observed_long, placebo_long) frames for the inference contract."""
    horizon = protocol.post_horizon_days
    observed_rows: list[dict[str, object]] = []
    placebo_rows: list[dict[str, object]] = []

    for target, corridors in sorted(protocol.eligible_corridors.items()):
        wide = wide_chokepoint_panel(
            target, start=str(protocol.history_start.date()), end=panel_end
        )
        for corridor in corridors:
            series = wide[corridor]

            obs = ar_window_statistic(
                series,
                history_start=protocol.history_start,
                origin=protocol.cutoff,
                horizon_days=horizon,
            )
            observed_rows.append({
                "model": obs["model"],
                "target": target,
                "corridor": corridor,
                "statistic_value": obs["statistic_value"],
                "n_scored": obs["n_scored"],
                "train_start": obs["train_start"],
                "train_end": obs["train_end"],
                "window_start": obs["origin"],
                "window_end": obs["window_end"],
                "pre_period_mean": obs["pre_period_mean"],
                "observed_sum": obs["observed_sum"],
                "counterfactual_sum": obs["counterfactual_sum"],
            })

            for placebo_origin in protocol.shared_placebo_origins:
                pl = ar_window_statistic(
                    series,
                    history_start=protocol.history_start,
                    origin=placebo_origin,
                    horizon_days=horizon,
                )
                placebo_rows.append({
                    "model": pl["model"],
                    "target": target,
                    "corridor": corridor,
                    "statistic_value": pl["statistic_value"],
                    "n_scored": pl["n_scored"],
                    "train_start": pl["train_start"],
                    "train_end": pl["train_end"],
                    "placebo_start": pl["origin"],
                    "placebo_end": pl["window_end"],
                })

    observed = pd.DataFrame(observed_rows)
    placebo = pd.DataFrame(placebo_rows)
    return observed, placebo


def basin_point_summary(
    observed: pd.DataFrame,
    metadata: pd.DataFrame,
) -> pd.DataFrame:
    """Point-only basin descriptive summary. Never sums corridors.

    ``aggregation_allowed`` is false for these operational regions, so this
    reports the central tendency and spread of corridor deviations within a
    basin, explicitly NOT a basin total.
    """
    basin_map = metadata.set_index("slug")["basin_group"]
    df = observed.copy()
    df["basin_group"] = df["corridor"].map(basin_map)
    if df["basin_group"].isna().any():
        missing = sorted(df.loc[df["basin_group"].isna(), "corridor"].unique())
        raise ValueError(f"corridors missing a basin mapping: {missing}.")
    rows = []
    for (target, basin), part in df.groupby(["target", "basin_group"], sort=True):
        rows.append({
            "target": target,
            "basin_group": basin,
            "n_corridors": int(len(part)),
            "mean_signed_deviation_point": float(part["statistic_value"].mean()),
            "median_signed_deviation_point": float(part["statistic_value"].median()),
            "min_signed_deviation": float(part["statistic_value"].min()),
            "max_signed_deviation": float(part["statistic_value"].max()),
            "interval_policy": "point_only_not_additive",
        })
    return pd.DataFrame(rows).sort_values(["target", "basin_group"], ignore_index=True)


def ar_baseline_fold_mase(
    protocol_admission_origins,
    *,
    history_start,
    cutoff,
    eligible_corridors: dict[str, tuple[str, ...]],
    horizon_days: int,
    panel_end: str = "2026-06-01",
) -> pd.DataFrame:
    """Per-corridor AR-only MASE over the frozen pre-cutoff admission folds.

    This is the forecasting-credibility check for the locked baseline; it uses
    pre-cutoff folds only and is independent of any post-cutoff result.
    """
    rows = []
    for target, corridors in sorted(eligible_corridors.items()):
        wide = wide_chokepoint_panel(
            target, start=str(pd.Timestamp(history_start).date()), end=panel_end
        )
        for corridor in corridors:
            series = wide[corridor].sort_index()
            model_frame = series.ffill().bfill().to_frame("value")
            fold_mases = []
            for origin in protocol_admission_origins:
                if pd.Timestamp(origin) + pd.Timedelta(days=horizon_days) > pd.Timestamp(cutoff):
                    raise ValueError("an admission fold reaches the cutoff.")
                fold = _window_fold(series.index, history_start, origin, horizon_days)
                y_pred = arx_forecast(model_frame, "value", fold, exog_cols=[], y_lags=AR_Y_LAGS)
                y_true = series.iloc[fold.test_idx]
                y_train = series.iloc[fold.train_idx]
                value = mase(y_true, y_pred, y_train, season_length=7)
                if np.isfinite(value):
                    fold_mases.append(value)
            if not fold_mases:
                raise ValueError(f"no scored folds for {target}/{corridor}.")
            rows.append({
                "model": AR_MODEL_NAME,
                "target": target,
                "corridor": corridor,
                "n_folds_scored": len(fold_mases),
                "mean_mase": float(np.mean(fold_mases)),
                "median_mase": float(np.median(fold_mases)),
            })
    return pd.DataFrame(rows).sort_values(["target", "corridor"], ignore_index=True)
