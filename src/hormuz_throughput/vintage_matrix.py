"""Leakage-safe model × PortWatch-vintage sensitivity matrix primitives."""
from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from . import config, registry
from .baselines import arx_forecast, seasonal_naive_forecast
from .bsts import fit_bsts_forecast, posterior_shortfall
from .validation import Fold


DESIGN_PATH = config.CONFIG_DIR / "model_vintage_matrix.yaml"
AUGUST_SENSITIVITY_VARIABLE = (
    "portwatch_chokepoints_vintage_20260809_snapshot"
)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_design(path: Path = DESIGN_PATH) -> tuple[dict, str]:
    raw = path.read_bytes()
    return yaml.safe_load(raw), hashlib.sha256(raw).hexdigest()


def validate_design(design: dict) -> None:
    """Validate dates, model set, protocol identity, and runtime settings."""
    if design.get("schema_version") != 1:
        raise ValueError("model-vintage matrix design must use schema_version 1")
    protocol_path = config.CONFIG_DIR / "model_admission_protocol.yaml"
    protocol_sha = sha256_file(protocol_path)
    if protocol_sha != design["admission_protocol_sha256"]:
        raise ValueError("matrix design points to a stale admission protocol")

    scope = design["scope"]
    start = pd.Timestamp(scope["analysis_start"])
    train_end = pd.Timestamp(scope["training_end"])
    cutoff = pd.Timestamp(scope["cutoff"])
    score_end = pd.Timestamp(scope["scoring_end"])
    if start >= cutoff or train_end != cutoff - pd.Timedelta(days=1):
        raise ValueError("invalid training/cutoff geometry in matrix design")
    if (score_end - cutoff).days + 1 != int(scope["expected_scored_days"]):
        raise ValueError("matrix scoring dates do not match expected_scored_days")

    contract = design["completion_contract"]
    if set(design["models"]) != set(contract["expected_models"]):
        raise ValueError("matrix model definitions differ from completion contract")
    if set(design["vintages"]) != set(contract["expected_vintages"]):
        raise ValueError("matrix vintage definitions differ from completion contract")
    expected_cells = len(design["models"]) * len(design["vintages"])
    if int(contract["expected_cells"]) != expected_cells:
        raise ValueError("matrix expected_cells is internally inconsistent")
    if not contract.get("never_average_vintages"):
        raise ValueError("matrix design must prohibit averaging vintages")
    sensitivity_variables = {
        spec["registry_variable"]
        for spec in design["vintages"].values()
        if spec["reporting_role"] == "sensitivity_only"
    }
    if sensitivity_variables != {AUGUST_SENSITIVITY_VARIABLE}:
        raise ValueError("matrix design must use the declared August sensitivity input")

    settings = config.settings()
    seed = int(settings["reproducibility"]["random_seed"])
    bsts = design["models"]["bsts_local_level_weekly"]
    chronos = design["models"]["chronos2"]
    if int(bsts["seed"]) != seed or int(chronos["seed"]) != seed:
        raise ValueError("matrix model seeds differ from the repository seed")
    for key in (
        "variance_prior_shape",
        "observation_prior_scale_multiplier",
        "level_prior_scale_multiplier",
    ):
        if float(bsts[key]) != float(settings["bsts"][key]):
            raise ValueError(f"matrix BSTS {key} differs from working settings")


def load_vintage_series(
    vintage: str,
    design: dict,
    *,
    consumer: str,
) -> tuple[pd.Series, dict]:
    """Registry-load and verify one frozen full-panel PortWatch measurement state."""
    if vintage not in design["vintages"]:
        raise KeyError(f"unknown matrix vintage {vintage!r}")
    vintage_spec = design["vintages"][vintage]
    artifact = registry.get_variable(
        vintage_spec["registry_variable"],
        query={
            "consumer": "src/hormuz_throughput/vintage_matrix.py",
            "initiator": consumer,
            "matrix_vintage": vintage,
            "analysis_scope": "sensitivity_only",
        },
        allow_sensitivity=(vintage_spec["reporting_role"] == "sensitivity_only"),
    )
    relative = artifact.path.relative_to(config.ROOT).as_posix()
    if relative != vintage_spec["expected_path"]:
        raise ValueError(f"{vintage} registry path differs from frozen design")
    if artifact.sha256 != vintage_spec["expected_sha256"]:
        raise ValueError(f"{vintage} source hash differs from frozen design")

    frame = artifact.read_csv(encoding="utf-8-sig", parse_dates=["date"])
    scope = design["scope"]
    required = {"date", "portname", scope["portwatch_column"]}
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"{vintage} lacks PortWatch columns {sorted(missing)}")
    selected = frame.loc[
        frame["portname"] == scope["chokepoint"],
        ["date", scope["portwatch_column"]],
    ].copy()
    if selected.empty or selected["date"].duplicated().any():
        raise ValueError(f"{vintage} has empty or duplicate Hormuz dates")
    values = pd.to_numeric(selected[scope["portwatch_column"]], errors="raise")
    series = pd.Series(
        values.to_numpy(dtype="float64"),
        index=pd.DatetimeIndex(selected["date"]),
        name=scope["outcome"],
    ).sort_index()
    return series, {
        "vintage": vintage,
        "source_variable": vintage_spec["registry_variable"],
        "source_path": relative,
        "source_sha256": artifact.sha256,
        "vintage_reporting_role": vintage_spec["reporting_role"],
    }


def matrix_panel(series: pd.Series, design: dict) -> tuple[pd.DataFrame, Fold]:
    """Restrict a series to the frozen complete calendar and build one fold."""
    scope = design["scope"]
    index = pd.date_range(scope["analysis_start"], scope["scoring_end"], freq="D")
    selected = series.reindex(index)
    if selected.isna().any():
        missing = selected.index[selected.isna()]
        raise ValueError(
            "matrix series lacks complete frozen calendar; first missing="
            f"{missing[0].date()}"
        )
    panel = selected.to_frame(name="y")
    cutoff = pd.Timestamp(scope["cutoff"])
    train_idx = np.flatnonzero(panel.index < cutoff)
    test_idx = np.flatnonzero(panel.index >= cutoff)
    fold = Fold(
        name="matrix_post_treatment",
        train_idx=train_idx,
        test_idx=test_idx,
        train_start=panel.index[train_idx[0]],
        train_end=panel.index[train_idx[-1]],
        test_start=panel.index[test_idx[0]],
        test_end=panel.index[test_idx[-1]],
    )
    if len(test_idx) != int(scope["expected_scored_days"]):
        raise ValueError("matrix fold does not contain the frozen scoring horizon")
    return panel, fold


def _daily_and_summary(
    *,
    prediction: pd.Series,
    observed: pd.Series,
    model: str,
    point_definition: str,
    source: dict,
    design: dict,
    design_sha256: str,
    lower: pd.Series | None = None,
    upper: pd.Series | None = None,
    model_native_joint_cumulative_shortfall: float | None = None,
    model_native_statistic: str | None = None,
    extras: dict | None = None,
) -> tuple[pd.DataFrame, dict]:
    prediction = prediction.astype("float64").reindex(observed.index)
    if prediction.isna().any() or not np.isfinite(prediction.to_numpy()).all():
        raise ValueError(f"{model} produced incomplete matrix predictions")
    shortfall = prediction - observed
    common_cumulative = float(shortfall.sum())
    n = int(len(observed))
    native_cumulative = (
        common_cumulative
        if model_native_joint_cumulative_shortfall is None
        else float(model_native_joint_cumulative_shortfall)
    )
    lower_values = (
        np.full(n, np.nan)
        if lower is None
        else lower.reindex(observed.index).to_numpy(dtype="float64")
    )
    upper_values = (
        np.full(n, np.nan)
        if upper is None
        else upper.reindex(observed.index).to_numpy(dtype="float64")
    )
    daily = pd.DataFrame({
        "design_id": design["design_id"],
        "design_sha256": design_sha256,
        "admission_protocol_sha256": design["admission_protocol_sha256"],
        **source,
        "model": model,
        "point_definition": point_definition,
        "date": observed.index,
        "y_true": observed.to_numpy(dtype="float64"),
        "y_pred": prediction.to_numpy(dtype="float64"),
        "lower_pointwise": lower_values,
        "upper_pointwise": upper_values,
        "common_point_shortfall": shortfall.to_numpy(dtype="float64"),
        "cumulative_common_point_shortfall": shortfall.cumsum().to_numpy(),
    })
    summary = {
        "design_id": design["design_id"],
        "design_sha256": design_sha256,
        "admission_protocol_sha256": design["admission_protocol_sha256"],
        **source,
        "model": model,
        "point_definition": point_definition,
        "unit": design["scope"]["unit"],
        "train_start": design["scope"]["analysis_start"],
        "train_end": design["scope"]["training_end"],
        "scoring_start": observed.index.min().date(),
        "scoring_end": observed.index.max().date(),
        "n_scored_days": n,
        "observed_sum": float(observed.sum()),
        "counterfactual_point_sum": float(prediction.sum()),
        "cumulative_common_point_shortfall": common_cumulative,
        "mean_daily_common_point_shortfall": common_cumulative / n,
        "model_native_statistic": (
            model_native_statistic or "same_as_common_daily_point"
        ),
        "model_native_joint_cumulative_shortfall": native_cumulative,
        "mean_daily_model_native_shortfall": native_cumulative / n,
        **(extras or {}),
    }
    return daily, summary


def run_core_vintage(
    series: pd.Series,
    source: dict,
    design: dict,
    design_sha256: str,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Run seasonal, AR, and BSTS cells for one measurement vintage."""
    panel, fold = matrix_panel(series, design)
    observed = panel.iloc[fold.test_idx]["y"]
    daily_frames: list[pd.DataFrame] = []
    summaries: list[dict] = []

    seasonal_spec = design["models"]["seasonal_naive_7d"]
    seasonal = seasonal_naive_forecast(
        panel["y"], fold, season_length=int(seasonal_spec["season_length_days"])
    )
    daily, summary = _daily_and_summary(
        prediction=seasonal,
        observed=observed,
        model="seasonal_naive_7d",
        point_definition=seasonal_spec["point_statistic"],
        source=source,
        design=design,
        design_sha256=design_sha256,
    )
    daily_frames.append(daily)
    summaries.append(summary)

    ar_spec = design["models"]["ar_lag1_7"]
    ar = arx_forecast(
        panel,
        target="y",
        fold=fold,
        exog_cols=[],
        y_lags=tuple(int(x) for x in ar_spec["outcome_lags"]),
        ridge_alpha=float(ar_spec["ridge_alpha"]),
    )
    daily, summary = _daily_and_summary(
        prediction=ar,
        observed=observed,
        model="ar_lag1_7",
        point_definition=ar_spec["point_statistic"],
        source=source,
        design=design,
        design_sha256=design_sha256,
    )
    daily_frames.append(daily)
    summaries.append(summary)

    bsts_spec = design["models"]["bsts_local_level_weekly"]
    train = panel.iloc[fold.train_idx]["y"]
    bsts = fit_bsts_forecast(
        train,
        observed.index,
        n_draws=int(bsts_spec["n_draws"]),
        burn=int(bsts_spec["burn"]),
        thin=int(bsts_spec["thin"]),
        seed=int(bsts_spec["seed"]),
        observation_prior_scale_multiplier=float(
            bsts_spec["observation_prior_scale_multiplier"]
        ),
        level_prior_scale_multiplier=float(
            bsts_spec["level_prior_scale_multiplier"]
        ),
        variance_prior_shape=float(bsts_spec["variance_prior_shape"]),
    )
    bsts_frame = bsts.forecast_frame().set_index("date")
    joint = posterior_shortfall(bsts.predictive_draws, observed)
    daily, summary = _daily_and_summary(
        prediction=bsts_frame["y_pred"],
        observed=observed,
        model="bsts_local_level_weekly",
        point_definition=bsts_spec["point_statistic"],
        source=source,
        design=design,
        design_sha256=design_sha256,
        lower=bsts_frame["lower_95"],
        upper=bsts_frame["upper_95"],
        model_native_joint_cumulative_shortfall=joint[
            "posterior_median_shortfall"
        ],
        model_native_statistic=bsts_spec["model_native_secondary"],
        extras={
            "model_native_joint_mean_shortfall": joint[
                "posterior_mean_shortfall"
            ],
            "model_native_lower_95": joint["lower_95"],
            "model_native_upper_95": joint["upper_95"],
            "model_native_probability_positive": joint[
                "posterior_probability_shortfall_positive"
            ],
            "model_native_draws": joint["n_posterior_draws"],
        },
    )
    daily_frames.append(daily)
    summaries.append(summary)
    return pd.concat(daily_frames, ignore_index=True), pd.DataFrame(summaries)


def run_chronos_vintage(
    series: pd.Series,
    source: dict,
    design: dict,
    design_sha256: str,
    *,
    adapter,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Run the frozen univariate Chronos cell for one measurement vintage."""
    panel, fold = matrix_panel(series, design)
    train = panel.iloc[fold.train_idx]["y"]
    observed = panel.iloc[fold.test_idx]["y"]
    spec = design["models"]["chronos2"]
    fc = adapter.predict(
        train,
        len(observed),
        lower_q=float(spec["lower_quantile"]),
        upper_q=float(spec["upper_quantile"]),
    )
    prediction = pd.Series(fc.point, index=observed.index)
    lower = pd.Series(fc.lower, index=observed.index)
    upper = pd.Series(fc.upper, index=observed.index)
    daily, summary = _daily_and_summary(
        prediction=prediction,
        observed=observed,
        model="chronos2",
        point_definition=spec["point_statistic"],
        source=source,
        design=design,
        design_sha256=design_sha256,
        lower=lower,
        upper=upper,
        extras={"nominal_pointwise_coverage": fc.nominal_coverage},
    )
    return daily, pd.DataFrame([summary])


def validate_complete_matrix(
    daily: pd.DataFrame,
    summary: pd.DataFrame,
    design: dict,
    design_sha256: str,
) -> None:
    """Reject missing/duplicate cells, mismatched dates, units, or summaries."""
    contract = design["completion_contract"]
    expected = {
        (vintage, model)
        for vintage in contract["expected_vintages"]
        for model in contract["expected_models"]
    }
    cells = set(zip(summary["vintage"], summary["model"]))
    if cells != expected or len(summary) != int(contract["expected_cells"]):
        raise ValueError(f"matrix cells differ from frozen contract: {cells}")
    if summary.duplicated(["vintage", "model"]).any():
        raise ValueError("matrix contains duplicate summary cells")
    for frame in (daily, summary):
        if not frame["design_sha256"].eq(design_sha256).all():
            raise ValueError("matrix contains stale design hashes")
        if not frame["admission_protocol_sha256"].eq(
            design["admission_protocol_sha256"]
        ).all():
            raise ValueError("matrix contains stale admission-protocol hashes")
    if not summary["unit"].eq(design["scope"]["unit"]).all():
        raise ValueError("matrix summary mixes outcome units")

    expected_dates = pd.date_range(
        design["scope"]["cutoff"], design["scope"]["scoring_end"], freq="D"
    )
    for vintage in contract["expected_vintages"]:
        reference_dates = None
        reference_observed = None
        for model in contract["expected_models"]:
            cell = daily.loc[
                daily["vintage"].eq(vintage) & daily["model"].eq(model)
            ].sort_values("date")
            dates = pd.DatetimeIndex(pd.to_datetime(cell["date"]))
            observed = cell["y_true"].to_numpy(dtype="float64")
            if len(cell) != len(expected_dates) or not dates.equals(expected_dates):
                raise ValueError(f"{vintage}/{model} has mismatched scored dates")
            if reference_dates is None:
                reference_dates = dates
                reference_observed = observed
            elif not dates.equals(reference_dates) or not np.array_equal(
                observed, reference_observed
            ):
                raise ValueError(f"{vintage} models do not share observed support")
            row = summary.loc[
                summary["vintage"].eq(vintage) & summary["model"].eq(model)
            ].iloc[0]
            if int(row["n_scored_days"]) != len(cell):
                raise ValueError(f"{vintage}/{model} summary day count mismatch")
            if not np.isclose(
                float(row["mean_daily_common_point_shortfall"]),
                float(cell["common_point_shortfall"].mean()),
            ):
                raise ValueError(f"{vintage}/{model} summary shortfall mismatch")


def pinned_self_checks(
    daily: pd.DataFrame,
    summary: pd.DataFrame,
    *,
    tolerance: float = 1e-6,
) -> dict[str, dict[str, float | bool]]:
    """Reconcile every pinned matrix cell to the existing committed artifacts."""
    root = config.ROOT
    references = {
        "seasonal_naive_7d": (
            root / "data/processed/counterfactual_post_treatment.csv",
            "throughput_loss_vs_counterfactual",
        ),
        "ar_lag1_7": (
            root / "data/processed/counterfactual_post_treatment.csv",
            "throughput_loss_vs_counterfactual",
        ),
        "chronos2": (
            root / "data/processed/tsfm_counterfactual_daily.csv",
            "throughput_loss_vs_counterfactual",
        ),
        "bsts_local_level_weekly": (
            root / "data/processed/bsts_counterfactual_daily.csv",
            "shortfall",
        ),
    }
    checks: dict[str, dict[str, float | bool]] = {}
    for model, (path, shortfall_col) in references.items():
        reference = pd.read_csv(path, parse_dates=["date"])
        if "target" in reference.columns:
            reference = reference.loc[
                reference["target"].eq("hormuz_tanker_transits")
            ]
        reference = reference.loc[reference["model"].eq(model)].sort_values("date")
        cell = daily.loc[
            daily["vintage"].eq("pinned_primary") & daily["model"].eq(model)
        ].sort_values("date")
        dates_match = pd.DatetimeIndex(cell["date"]).equals(
            pd.DatetimeIndex(reference["date"])
        )
        observed_delta = float(np.max(np.abs(
            cell["y_true"].to_numpy(dtype="float64")
            - reference["y_true"].to_numpy(dtype="float64")
        )))
        prediction_delta = float(np.max(np.abs(
            cell["y_pred"].to_numpy(dtype="float64")
            - reference["y_pred"].to_numpy(dtype="float64")
        )))
        shortfall_delta = float(abs(
            cell["common_point_shortfall"].mean()
            - reference[shortfall_col].mean()
        ))
        passed = bool(
            dates_match
            and observed_delta <= tolerance
            and prediction_delta <= tolerance
            and shortfall_delta <= tolerance
        )
        if not passed:
            raise ValueError(
                f"pinned self-check failed for {model}: dates={dates_match}, "
                f"observed_delta={observed_delta}, prediction_delta={prediction_delta}, "
                f"shortfall_delta={shortfall_delta}"
            )
        checks[model] = {
            "passed": passed,
            "max_observed_delta": observed_delta,
            "max_prediction_delta": prediction_delta,
            "mean_shortfall_delta": shortfall_delta,
        }

    bsts_summary = pd.read_csv(root / "data/processed/bsts_counterfactual_summary.csv")
    native_reference = float(
        bsts_summary.loc[
            bsts_summary["target"].eq("hormuz_tanker_transits"),
            "posterior_median_shortfall",
        ].iloc[0]
    )
    native_matrix = float(
        summary.loc[
            summary["vintage"].eq("pinned_primary")
            & summary["model"].eq("bsts_local_level_weekly"),
            "model_native_joint_cumulative_shortfall",
        ].iloc[0]
    )
    native_delta = abs(native_matrix - native_reference)
    if native_delta > tolerance:
        raise ValueError(f"pinned BSTS joint-statistic delta={native_delta}")
    checks["bsts_local_level_weekly"]["joint_statistic_delta"] = native_delta
    return checks
