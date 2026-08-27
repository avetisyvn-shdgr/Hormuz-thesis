"""Phase A1 forecast-task geometry and leakage seals.

This module deliberately contains no forecasting estimator.  It fixes the
leave-Hormuz-out direct-task geometry, materialises only timestamp-safe
features, and makes every restricted operation pass an explicit information
boundary before later phases may fit anything.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Iterable, Mapping, Sequence

import numpy as np
import pandas as pd
import yaml

from . import config


SPEC_PATH = config.CONFIG_DIR / "hormuz_detection.yaml"

# Phases extend the specification in order.  A later phase inherits every
# earlier obligation; it may only add.  `fitting_status` is the seal that stops
# A1 from quietly fitting a model and stops A2 from pretending it did not.
#
# The `status` token records where the phase stands in Mher's review, so it
# moves when he accepts a phase.  A1's token is left at its pre-freeze value
# because the A1 audit returning PASS is not the same event as Mher accepting
# it, and no such acceptance is on the record.  A2's is not: Mher accepted A2
# on 2026-08-27.
PHASE_LADDER: Mapping[str, Mapping[str, str]] = {
    "A1": {
        "status": "phase_a1_candidate_for_mher_freeze",
        "fitting_status": "deferred_to_A2",
    },
    "A2": {
        "status": "phase_a2_accepted_by_mher",
        "fitting_status": "fitted_in_A2",
    },
}
RESTRICTED_OPERATIONS = frozenset(
    {
        "fitting",
        "scaling",
        "feature_selection",
        "detector_calibration",
        "hyperparameter_selection",
    }
)


class LeakageError(ValueError):
    """Raised when a task crosses a frozen information boundary."""


class MeasurementStateError(ValueError):
    """Raised when July and August measurement states are mixed."""


@dataclass(frozen=True)
class RollingOriginFold:
    fold_id: str
    fit_start: pd.Timestamp
    fit_end: pd.Timestamp
    score_start: pd.Timestamp
    score_end: pd.Timestamp


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_detection_spec(path: Path = SPEC_PATH) -> tuple[dict, str]:
    raw = path.read_bytes()
    spec = yaml.safe_load(raw)
    validate_detection_spec(spec)
    return spec, hashlib.sha256(raw).hexdigest()


def measurement_state_names(spec: Mapping) -> tuple[str, ...]:
    return tuple(
        key
        for key, value in spec["measurement_states"].items()
        if isinstance(value, Mapping)
    )


def development_units(spec: Mapping) -> tuple[str, ...]:
    hormuz = spec["population"]["hormuz_unit"]
    return tuple(unit for unit in spec["population"]["units"] if unit != hormuz)


def validate_detection_spec(spec: Mapping) -> None:
    """Reject any drift from the Phase 0/A1 information contract.

    Later phases extend this specification; they never relax it.  Every A1
    clause below is enforced identically whatever the declared phase, and the
    phase ladder only decides which additional obligations apply.
    """
    if spec.get("schema_version") != 1:
        raise ValueError("Hormuz detection specification must be schema 1")
    phase = spec.get("phase")
    if phase not in PHASE_LADDER:
        raise ValueError(
            f"unknown detection-specification phase {phase!r}; "
            f"expected one of {sorted(PHASE_LADDER)}"
        )
    if spec.get("status") != PHASE_LADDER[phase]["status"]:
        raise ValueError(
            f"phase {phase} specification status is not its expected pre-freeze state"
        )

    plan = spec["plan"]
    if str(plan["version"]) != "1.2":
        raise ValueError("this specification requires technical execution plan version 1.2")
    plan_path = config.ROOT / plan["path"]
    if not plan_path.is_file() or sha256_file(plan_path) != plan["sha256"]:
        raise ValueError("technical execution plan is missing or its hash drifted")

    states = measurement_state_names(spec)
    if states != ("july", "august"):
        raise ValueError(f"measurement states must remain ('july', 'august'), got {states}")
    if spec["measurement_states"].get("never_join_or_average") is not True:
        raise ValueError("measurement-state joining/averaging must be prohibited")
    for state in states:
        state_spec = spec["measurement_states"][state]
        if not state_spec.get("path") or len(str(state_spec.get("sha256", ""))) != 64:
            raise ValueError(f"{state} measurement state lacks a frozen path/hash")

    population = spec["population"]
    units = population["units"]
    hormuz = population["hormuz_unit"]
    if len(units) != len(set(units)):
        raise ValueError("population units must be unique")
    if len(units) != int(population["expected_total_units"]):
        raise ValueError("population total-unit count drifted")
    if hormuz not in units or len(development_units(spec)) != int(
        population["expected_development_units"]
    ):
        raise ValueError("leave-Hormuz-out development population drifted")

    dates = {key: pd.Timestamp(value) for key, value in spec["dates"].items()}
    expected_order = (
        dates["full_start"]
        <= dates["development_end"]
        < dates["hyperparameter_validation_start"]
        <= dates["hyperparameter_validation_end"]
        < dates["detector_calibration_end"]
        < dates["hormuz_surveillance_start"]
        <= dates["hormuz_pre_onset_end"]
        < dates["operational_onset"]
        <= dates["scoring_end"]
    )
    if not expected_order:
        raise ValueError("frozen A1 date order is internally inconsistent")
    if dates["hyperparameter_validation_start"] != dates["development_end"] + pd.Timedelta(days=1):
        raise ValueError("development and validation boundary drifted")
    if dates["operational_onset"] != dates["hormuz_pre_onset_end"] + pd.Timedelta(days=1):
        raise ValueError("Hormuz onset boundary drifted")

    tasks = spec["tasks"]
    if tuple(int(h) for h in tasks["horizons_days"]) != (1, 7, 30):
        raise ValueError("A1 direct horizons must be exactly 1, 7, and 30 days")
    if not tasks.get("chronological_only") or not tasks.get("random_split_prohibited"):
        raise ValueError("chronological-only task generation must be frozen")
    if tasks.get("hormuz_training_prohibited") is not True:
        raise ValueError("leave-Hormuz-out training must be explicit")
    repository_seed = int(config.settings()["reproducibility"]["random_seed"])
    if int(tasks["seed"]) != repository_seed:
        raise ValueError("A1 seed differs from the frozen repository seed")

    features = spec["features"]
    if tuple(features["lag_days"]) != (1, 7, 14, 28, 56):
        raise ValueError("A1 lag set drifted")
    if features["network_factors"].get("enabled") is not False:
        raise ValueError("network factors are disabled in A1")
    if features["identity_embedding"].get("enabled") is not False:
        raise ValueError("identity embeddings are prohibited in A1")

    rolling = spec["rolling_origin"]
    if rolling["scheme"] != "expanding":
        raise ValueError("A1 rolling origin must use expanding training windows")
    if int(rolling["assessment_days"]) <= 0 or int(rolling["step_days"]) <= 0:
        raise ValueError("rolling-origin block lengths must be positive")
    _validate_residual_roles(rolling)

    detector = spec["detector_contract"]
    if detector.get("hormuz_calibration_prohibited") is not True:
        raise ValueError("Hormuz detector-calibration exclusion must be frozen")
    expected_fitting = PHASE_LADDER[phase]["fitting_status"]
    if detector.get("fitting_status") != expected_fitting:
        raise ValueError(
            f"phase {phase} requires fitting_status {expected_fitting!r}, "
            f"got {detector.get('fitting_status')!r}"
        )
    if detector.get("calibration_status") != "deferred_to_A3":
        raise ValueError("detector calibration remains an A3 obligation")

    if phase == "A2":
        validate_model_spec(spec)


def _validate_residual_roles(rolling: Mapping) -> None:
    roles = []
    for name, raw in rolling["residual_roles"].items():
        start, end = pd.Timestamp(raw["start"]), pd.Timestamp(raw["end"])
        if start > end:
            raise ValueError(f"residual role {name!r} has start after end")
        roles.append((start, end, name))
    roles.sort()
    for (_, previous_end, previous), (start, _, current) in zip(roles, roles[1:]):
        if start != previous_end + pd.Timedelta(days=1):
            raise ValueError(
                f"residual roles {previous!r} and {current!r} are not contiguous"
            )
    first = pd.Timestamp(rolling["first_score_start"])
    last = pd.Timestamp(rolling["last_score_end"])
    if roles[0][0] != first or roles[-1][1] != last:
        raise ValueError("residual roles do not cover the frozen rolling-origin window")


def _normalize_dates(values: Iterable[pd.Timestamp | str]) -> pd.DatetimeIndex:
    index = pd.DatetimeIndex(values)
    if index.tz is not None:
        raise ValueError("task timestamps must be timezone-naive calendar dates")
    if index.has_duplicates or not index.is_monotonic_increasing:
        raise ValueError("task target dates must be unique and chronological")
    return index.normalize()


def build_task_geometry(
    target_dates: Iterable[pd.Timestamp | str],
    units: Sequence[str],
    horizons_days: Sequence[int],
    *,
    measurement_state: str,
    task_role: str,
    seed: int,
    fold_id: str = "",
    extra_columns: Mapping[str, object] | None = None,
) -> pd.DataFrame:
    """Build deterministic direct tasks without touching any outcome values."""
    dates = _normalize_dates(target_dates)
    if len(units) != len(set(units)):
        raise ValueError("task units must be unique")
    raw_horizons = tuple(int(value) for value in horizons_days)
    if len(raw_horizons) != len(set(raw_horizons)):
        raise ValueError("forecast horizons must be unique")
    ordered_units = tuple(sorted(units))
    horizons = tuple(sorted(raw_horizons))
    if not len(dates) or not ordered_units:
        raise ValueError("task geometry requires dates and units")
    if not horizons or any(value <= 0 for value in horizons):
        raise ValueError("forecast horizons must be positive")

    records: list[dict[str, object]] = []
    extras = dict(extra_columns or {})
    for unit in ordered_units:
        for target in dates:
            for horizon in horizons:
                records.append(
                    {
                        "measurement_state": measurement_state,
                        "task_role": task_role,
                        "fold_id": fold_id,
                        "unit": unit,
                        "horizon_days": horizon,
                        "feature_timestamp": target - pd.Timedelta(days=horizon),
                        "target_timestamp": target,
                        "seed": int(seed),
                        **extras,
                    }
                )
    return pd.DataFrame.from_records(records)


def _minimum_supported_target(spec: Mapping) -> pd.Timestamp:
    features = spec["features"]
    lookback = max(
        max(int(value) for value in features["lag_days"]),
        max(int(value) for value in features["rolling_windows_days"]),
    )
    max_horizon = max(int(value) for value in spec["tasks"]["horizons_days"])
    return pd.Timestamp(spec["dates"]["full_start"]) + pd.Timedelta(
        days=max_horizon + lookback - 1
    )


def build_development_geometry(spec: Mapping, measurement_state: str) -> pd.DataFrame:
    """Create leave-Hormuz-out development and 2024 validation tasks."""
    seed = int(spec["tasks"]["seed"])
    horizons = spec["tasks"]["horizons_days"]
    units = development_units(spec)
    development_dates = pd.date_range(
        _minimum_supported_target(spec), spec["dates"]["development_end"], freq="D"
    )
    development_end = pd.Timestamp(spec["dates"]["development_end"])
    frames = [
        build_task_geometry(
            development_dates,
            units,
            horizons,
            measurement_state=measurement_state,
            task_role="development_fit",
            seed=seed,
        ),
    ]
    for horizon in horizons:
        first_target = max(
            pd.Timestamp(spec["dates"]["hyperparameter_validation_start"]),
            development_end + pd.Timedelta(days=int(horizon)),
        )
        validation_dates = pd.date_range(
            first_target,
            spec["dates"]["hyperparameter_validation_end"],
            freq="D",
        )
        frames.append(
            build_task_geometry(
                validation_dates,
                units,
                [horizon],
                measurement_state=measurement_state,
                task_role="hyperparameter_validation",
                seed=seed,
                extra_columns={
                    "fit_start": pd.Timestamp(spec["dates"]["full_start"]),
                    "fit_end": development_end,
                },
            )
        )
    tasks = pd.concat(frames, ignore_index=True)
    validate_task_table(tasks, spec)
    return tasks


def build_hormuz_scoring_geometry(spec: Mapping, measurement_state: str) -> pd.DataFrame:
    tasks = build_task_geometry(
        pd.date_range(
            spec["dates"]["hormuz_surveillance_start"],
            spec["dates"]["scoring_end"],
            freq="D",
        ),
        [spec["population"]["hormuz_unit"]],
        spec["tasks"]["horizons_days"],
        measurement_state=measurement_state,
        task_role="scoring_only",
        seed=int(spec["tasks"]["seed"]),
    )
    validate_task_table(tasks, spec)
    return tasks


def rolling_origin_folds(spec: Mapping) -> tuple[RollingOriginFold, ...]:
    cfg = spec["rolling_origin"]
    fit_start = pd.Timestamp(cfg["train_start"])
    score_start = pd.Timestamp(cfg["first_score_start"])
    final_end = pd.Timestamp(cfg["last_score_end"])
    assessment = pd.Timedelta(days=int(cfg["assessment_days"]))
    step = pd.Timedelta(days=int(cfg["step_days"]))
    include_partial = bool(cfg["include_partial_last_fold"])
    folds: list[RollingOriginFold] = []
    while score_start <= final_end:
        proposed_end = score_start + assessment - pd.Timedelta(days=1)
        if proposed_end > final_end and not include_partial:
            break
        score_end = min(proposed_end, final_end)
        folds.append(
            RollingOriginFold(
                fold_id=f"fold_{len(folds) + 1:03d}",
                fit_start=fit_start,
                fit_end=score_start - pd.Timedelta(days=1),
                score_start=score_start,
                score_end=score_end,
            )
        )
        score_start += step
    if not folds:
        raise ValueError("rolling-origin specification produced no folds")
    for fold in folds:
        if fold.fit_end >= fold.score_start:
            raise LeakageError(f"{fold.fold_id} fit window reaches its score window")
    return tuple(folds)


def _residual_role(target: pd.Timestamp, spec: Mapping) -> tuple[str, bool]:
    for role, cfg in spec["rolling_origin"]["residual_roles"].items():
        if pd.Timestamp(cfg["start"]) <= target <= pd.Timestamp(cfg["end"]):
            return role, bool(cfg["detector_calibration_eligible"])
    raise ValueError(f"target {target.date()} is outside frozen residual roles")


def build_rolling_residual_geometry(
    spec: Mapping,
    measurement_state: str,
) -> pd.DataFrame:
    """Build daily rolling-origin residual tasks for later A3 calibration."""
    frames = []
    for fold in rolling_origin_folds(spec):
        dates = pd.date_range(fold.score_start, fold.score_end, freq="D")
        for horizon in spec["tasks"]["horizons_days"]:
            frame = build_task_geometry(
                dates,
                development_units(spec),
                [horizon],
                measurement_state=measurement_state,
                task_role="rolling_residual",
                seed=int(spec["tasks"]["seed"]),
                fold_id=fold.fold_id,
                extra_columns={
                    "fit_start": fold.fit_start,
                    "fit_end": fold.score_start - pd.Timedelta(days=int(horizon)),
                    "score_start": fold.score_start,
                    "score_end": fold.score_end,
                },
            )
            role_values = [
                _residual_role(value, spec) for value in frame["target_timestamp"]
            ]
            frame["residual_role"] = [value[0] for value in role_values]
            frame["calibration_eligible"] = [value[1] for value in role_values]
            frames.append(frame)
    tasks = pd.concat(frames, ignore_index=True)
    validate_task_table(tasks, spec)
    return tasks


def _calendar_dates(values: pd.Series, name: str) -> pd.Series:
    parsed = pd.to_datetime(values, errors="raise")
    if parsed.isna().any():
        raise ValueError(f"{name} contains missing timestamps")
    if parsed.dt.tz is not None:
        raise ValueError(f"{name} must contain timezone-naive calendar dates")
    normalized = parsed.dt.normalize()
    if not np.array_equal(
        parsed.to_numpy(dtype="datetime64[ns]"),
        normalized.to_numpy(dtype="datetime64[ns]"),
    ):
        raise ValueError(f"{name} must contain normalized calendar dates")
    return normalized


def _require_role_columns(tasks: pd.DataFrame, rows: pd.Series, columns: set[str]) -> None:
    missing = columns.difference(tasks.columns)
    if missing:
        roles = sorted(set(tasks.loc[rows, "task_role"]))
        raise LeakageError(f"task roles {roles} require metadata columns {sorted(missing)}")
    if tasks.loc[rows, sorted(columns)].isna().any().any():
        roles = sorted(set(tasks.loc[rows, "task_role"]))
        raise LeakageError(f"task roles {roles} contain missing frozen-geometry metadata")


def _validate_role_geometry(
    tasks: pd.DataFrame,
    spec: Mapping,
    feature_ts: pd.Series,
    target_ts: pd.Series,
) -> None:
    allowed_roles = {
        "development_fit",
        "hyperparameter_validation",
        "rolling_fit",
        "rolling_residual",
        "scoring_only",
    }
    roles = set(tasks["task_role"])
    unknown_roles = roles.difference(allowed_roles)
    if unknown_roles:
        raise LeakageError(f"unknown task roles {sorted(unknown_roles)}")

    all_units = set(spec["population"]["units"])
    unknown_units = set(tasks["unit"]).difference(all_units)
    if unknown_units:
        raise LeakageError(f"tasks contain units outside the frozen population: {sorted(unknown_units)}")
    development = set(development_units(spec))
    hormuz = spec["population"]["hormuz_unit"]
    full_start = pd.Timestamp(spec["dates"]["full_start"])
    development_end = pd.Timestamp(spec["dates"]["development_end"])
    calibration_end = pd.Timestamp(spec["dates"]["detector_calibration_end"])

    development_rows = tasks["task_role"].eq("development_fit")
    if development_rows.any():
        if not set(tasks.loc[development_rows, "unit"]).issubset(development):
            raise LeakageError("development-fit tasks must use only non-Hormuz units")
        if not tasks.loc[development_rows, "fold_id"].eq("").all():
            raise LeakageError("development-fit tasks cannot carry rolling fold identifiers")
        minimum = _minimum_supported_target(spec)
        if (target_ts[development_rows] < minimum).any():
            raise LeakageError("development-fit targets precede the supported feature history")
        if (target_ts[development_rows] > development_end).any():
            raise LeakageError("development-fit targets after the frozen period are forbidden")

    validation_rows = tasks["task_role"].eq("hyperparameter_validation")
    if validation_rows.any():
        _require_role_columns(tasks, validation_rows, {"fit_start", "fit_end"})
        if not set(tasks.loc[validation_rows, "unit"]).issubset(development):
            raise LeakageError("hyperparameter-validation tasks must use non-Hormuz units")
        if not tasks.loc[validation_rows, "fold_id"].eq("").all():
            raise LeakageError("hyperparameter-validation tasks cannot carry rolling folds")
        fit_start = _calendar_dates(tasks.loc[validation_rows, "fit_start"], "fit_start")
        fit_end = _calendar_dates(tasks.loc[validation_rows, "fit_end"], "fit_end")
        start = pd.Timestamp(spec["dates"]["hyperparameter_validation_start"])
        end = pd.Timestamp(spec["dates"]["hyperparameter_validation_end"])
        if not fit_start.eq(full_start).all() or not fit_end.eq(development_end).all():
            raise LeakageError("hyperparameter-validation fit bounds drifted from the frozen split")
        if (target_ts[validation_rows] < start).any() or (target_ts[validation_rows] > end).any():
            raise LeakageError("hyperparameter-validation targets must remain in frozen 2024")
        if (fit_end.to_numpy() > feature_ts[validation_rows].to_numpy()).any():
            raise LeakageError("hyperparameter-validation fit cutoff postdates forecast origin")

    rolling_rows = tasks["task_role"].isin({"rolling_fit", "rolling_residual"})
    if rolling_rows.any():
        metadata = {"fit_start", "fit_end", "score_start", "score_end"}
        _require_role_columns(tasks, rolling_rows, metadata)
        if not set(tasks.loc[rolling_rows, "unit"]).issubset(development):
            raise LeakageError("rolling tasks must use only non-Hormuz units")
        folds = {fold.fold_id: fold for fold in rolling_origin_folds(spec)}
        fold_ids = tasks.loc[rolling_rows, "fold_id"]
        unknown_folds = set(fold_ids).difference(folds)
        if unknown_folds:
            raise LeakageError(f"rolling tasks reference unknown frozen folds {sorted(unknown_folds)}")
        expected_fit_start = fold_ids.map(lambda value: folds[value].fit_start)
        expected_score_start = fold_ids.map(lambda value: folds[value].score_start)
        expected_score_end = fold_ids.map(lambda value: folds[value].score_end)
        fit_start = _calendar_dates(tasks.loc[rolling_rows, "fit_start"], "fit_start")
        fit_end = _calendar_dates(tasks.loc[rolling_rows, "fit_end"], "fit_end")
        score_start = _calendar_dates(tasks.loc[rolling_rows, "score_start"], "score_start")
        score_end = _calendar_dates(tasks.loc[rolling_rows, "score_end"], "score_end")
        horizons = tasks.loc[rolling_rows, "horizon_days"].astype("int64")
        expected_fit_end = expected_score_start - pd.to_timedelta(horizons, unit="D")
        if not np.array_equal(fit_start.to_numpy(), expected_fit_start.to_numpy()):
            raise LeakageError("rolling fit_start does not reproduce the frozen fold")
        if not np.array_equal(fit_end.to_numpy(), expected_fit_end.to_numpy()):
            raise LeakageError("rolling fit_end is not horizon-specific frozen geometry")
        if not np.array_equal(score_start.to_numpy(), expected_score_start.to_numpy()):
            raise LeakageError("rolling score_start does not reproduce the frozen fold")
        if not np.array_equal(score_end.to_numpy(), expected_score_end.to_numpy()):
            raise LeakageError("rolling score_end does not reproduce the frozen fold")
        if (fit_end > calibration_end).any():
            raise LeakageError("rolling fitting reaches beyond the frozen pre-surveillance end")

    rolling_fit_rows = tasks["task_role"].eq("rolling_fit")
    if rolling_fit_rows.any():
        fit_end = _calendar_dates(tasks.loc[rolling_fit_rows, "fit_end"], "fit_end")
        minimum = _minimum_supported_target(spec)
        if (target_ts[rolling_fit_rows] < minimum).any():
            raise LeakageError("rolling-fit targets precede the supported feature history")
        if (target_ts[rolling_fit_rows].to_numpy() > fit_end.to_numpy()).any():
            raise LeakageError("rolling-fit target reaches beyond its frozen fit_end")

    residual_rows = tasks["task_role"].eq("rolling_residual")
    if residual_rows.any():
        _require_role_columns(tasks, residual_rows, {"residual_role", "calibration_eligible"})
        fit_end = _calendar_dates(tasks.loc[residual_rows, "fit_end"], "fit_end")
        score_start = _calendar_dates(tasks.loc[residual_rows, "score_start"], "score_start")
        score_end = _calendar_dates(tasks.loc[residual_rows, "score_end"], "score_end")
        residual_targets = target_ts[residual_rows]
        if (fit_end.to_numpy() > feature_ts[residual_rows].to_numpy()).any():
            raise LeakageError("rolling fit cutoff postdates a forecast origin")
        if (residual_targets.to_numpy() < score_start.to_numpy()).any() or (
            residual_targets.to_numpy() > score_end.to_numpy()
        ).any():
            raise LeakageError("rolling-residual target lies outside its frozen score block")
        expected_roles = residual_targets.map(lambda value: _residual_role(value, spec))
        declared_roles = tasks.loc[residual_rows, "residual_role"].to_numpy()
        declared_eligible = tasks.loc[residual_rows, "calibration_eligible"].to_numpy()
        if not np.array_equal(
            declared_roles, np.array([value[0] for value in expected_roles], dtype=object)
        ):
            raise LeakageError("rolling residual_role does not match the frozen date role")
        if not np.array_equal(
            declared_eligible, np.array([value[1] for value in expected_roles], dtype=bool)
        ):
            raise LeakageError("rolling calibration eligibility does not match the frozen role")

    scoring_rows = tasks["task_role"].eq("scoring_only")
    if scoring_rows.any():
        surveillance = pd.Timestamp(spec["dates"]["hormuz_surveillance_start"])
        scoring_end = pd.Timestamp(spec["dates"]["scoring_end"])
        if not tasks.loc[scoring_rows, "fold_id"].eq("").all():
            raise LeakageError("scoring-only tasks cannot carry rolling fold identifiers")
        if (target_ts[scoring_rows] < surveillance).any() or (
            target_ts[scoring_rows] > scoring_end
        ).any():
            raise LeakageError("scoring-only targets lie outside the frozen scoring window")
        hormuz_rows = scoring_rows & tasks["unit"].eq(hormuz)
        if hormuz_rows.any() and not tasks.loc[hormuz_rows, "task_role"].eq("scoring_only").all():
            raise LeakageError("Hormuz may appear only in scoring-only tasks")


def validate_task_table(
    tasks: pd.DataFrame,
    spec: Mapping,
    *,
    require_single_state: bool = True,
) -> None:
    required = {
        "measurement_state",
        "task_role",
        "fold_id",
        "unit",
        "horizon_days",
        "feature_timestamp",
        "target_timestamp",
        "seed",
    }
    missing = required.difference(tasks.columns)
    if missing:
        raise ValueError(f"task table lacks required columns {sorted(missing)}")
    if tasks.empty:
        raise ValueError("task table is empty")

    states = tuple(pd.unique(tasks["measurement_state"]))
    unknown = set(states).difference(measurement_state_names(spec))
    if unknown:
        raise MeasurementStateError(f"unknown measurement states: {sorted(unknown)}")
    if require_single_state and len(states) != 1:
        raise MeasurementStateError(
            "July and August task rows must be processed separately; joining or "
            f"averaging is prohibited (found {states})"
        )

    horizon_values = pd.to_numeric(tasks["horizon_days"], errors="raise")
    if not np.equal(horizon_values, horizon_values.astype("int64")).all():
        raise LeakageError("forecast horizons must be integer calendar days")
    horizons = set(horizon_values.astype("int64"))
    frozen_horizons = set(int(value) for value in spec["tasks"]["horizons_days"])
    if not horizons.issubset(frozen_horizons):
        raise LeakageError(
            f"task horizons must be drawn from frozen 1/7/30 geometry, got {sorted(horizons)}"
        )
    feature_ts = _calendar_dates(tasks["feature_timestamp"], "feature_timestamp")
    target_ts = _calendar_dates(tasks["target_timestamp"], "target_timestamp")
    if not (feature_ts < target_ts).all():
        raise LeakageError("every target timestamp must be strictly after its feature timestamp")
    expected_target = feature_ts + pd.to_timedelta(tasks["horizon_days"], unit="D")
    if not np.array_equal(
        expected_target.to_numpy(dtype="datetime64[ns]"),
        target_ts.to_numpy(dtype="datetime64[ns]"),
    ):
        raise LeakageError("target timestamp does not equal feature timestamp plus horizon")
    if not tasks["seed"].eq(int(spec["tasks"]["seed"])).all():
        raise ValueError("task rows do not carry the frozen seed")

    _validate_role_geometry(tasks, spec, feature_ts, target_ts)

    duplicate_key = [
        "measurement_state",
        "fold_id",
        "unit",
        "horizon_days",
        "target_timestamp",
    ]
    if tasks.duplicated(duplicate_key).any():
        raise ValueError("task geometry contains duplicate direct tasks")

    hormuz = spec["population"]["hormuz_unit"]
    hormuz_rows = tasks["unit"].eq(hormuz)
    if hormuz_rows.any():
        surveillance = pd.Timestamp(spec["dates"]["hormuz_surveillance_start"])
        if not tasks.loc[hormuz_rows, "task_role"].eq("scoring_only").all():
            raise LeakageError("Hormuz may appear only in scoring-only tasks")
        if not (target_ts[hormuz_rows] >= surveillance).all():
            raise LeakageError("Hormuz task targets before the frozen surveillance start are forbidden")


def assert_task_access(tasks: pd.DataFrame, operation: str, spec: Mapping) -> None:
    """Seal task access for fitting, scaling, selection, and calibration."""
    if operation not in RESTRICTED_OPERATIONS:
        raise KeyError(f"unknown restricted operation {operation!r}")
    validate_task_table(tasks, spec)
    hormuz = spec["population"]["hormuz_unit"]
    if tasks["unit"].eq(hormuz).any():
        raise LeakageError(
            f"Hormuz observations are scoring-only and cannot enter {operation}"
        )
    unknown_units = set(tasks["unit"]).difference(development_units(spec))
    if unknown_units:
        raise LeakageError(
            f"{operation} received units outside the frozen development population: "
            f"{sorted(unknown_units)}"
        )

    roles = set(tasks["task_role"])
    target = pd.to_datetime(tasks["target_timestamp"])
    if operation in {"fitting", "scaling"}:
        allowed = set(spec["scaling"]["permitted_fit_roles"])
        if not roles.issubset(allowed):
            raise LeakageError(f"{operation} received non-training task roles {sorted(roles)}")
        development_rows = tasks["task_role"].eq("development_fit")
        development_end = pd.Timestamp(spec["dates"]["development_end"])
        if development_rows.any() and (target[development_rows] > development_end).any():
            raise LeakageError(
                f"{operation} received development-fit targets after {development_end.date()}"
            )
        rolling_rows = tasks["task_role"].eq("rolling_fit")
        if rolling_rows.any():
            if "fit_end" not in tasks:
                raise LeakageError(f"{operation} rolling-fit tasks require fit_end")
            fit_end = pd.to_datetime(tasks.loc[rolling_rows, "fit_end"])
            if (target[rolling_rows].to_numpy() > fit_end.to_numpy()).any():
                raise LeakageError(f"{operation} rolling-fit target reaches beyond fit_end")
    elif operation == "feature_selection":
        if roles != {"development_fit"}:
            raise LeakageError("feature selection is restricted to development-fit tasks")
        if target.max() > pd.Timestamp(spec["dates"]["development_end"]):
            raise LeakageError("feature selection reaches beyond the development period")
    elif operation == "hyperparameter_selection":
        start = pd.Timestamp(spec["dates"]["hyperparameter_validation_start"])
        end = pd.Timestamp(spec["dates"]["hyperparameter_validation_end"])
        if roles != {"hyperparameter_validation"} or target.min() < start or target.max() > end:
            raise LeakageError("hyperparameter selection must use only the frozen 2024 tasks")
    elif operation == "detector_calibration":
        if roles != {"rolling_residual"}:
            raise LeakageError("detector calibration requires rolling-residual tasks")
        if "calibration_eligible" not in tasks or not tasks["calibration_eligible"].all():
            raise LeakageError("detector calibration received an ineligible residual role")
        if "event_masked" not in tasks:
            raise LeakageError("detector calibration requires the frozen event mask")
        if tasks["event_masked"].any():
            raise LeakageError("exposed unit-days remain in detector calibration")
        if target.max() > pd.Timestamp(spec["dates"]["detector_calibration_end"]):
            raise LeakageError("detector calibration reaches beyond its frozen end date")


def feature_columns(spec: Mapping) -> tuple[str, ...]:
    columns = [f"lag_{int(value)}" for value in spec["features"]["lag_days"]]
    for window in spec["features"]["rolling_windows_days"]:
        for statistic in spec["features"]["rolling_statistics"]:
            columns.append(f"rolling_{statistic}_{int(window)}")
    columns.extend(spec["features"]["calendar"]["fields"])
    return tuple(columns)


def _validate_panel(panel: pd.DataFrame) -> pd.DataFrame:
    if not isinstance(panel.index, pd.DatetimeIndex):
        raise TypeError("panel must use a DatetimeIndex")
    if panel.index.tz is not None or not panel.index.is_monotonic_increasing:
        raise ValueError("panel index must be timezone-naive and chronological")
    if panel.index.has_duplicates:
        raise ValueError("panel index contains duplicate dates")
    expected = pd.date_range(panel.index.min(), panel.index.max(), freq="D")
    if not panel.index.equals(expected):
        raise ValueError("panel must have a complete daily calendar")
    if panel.columns.duplicated().any():
        raise ValueError("panel unit columns must be unique")
    return panel.apply(pd.to_numeric, errors="raise").astype("float64")


def materialize_task_features(
    panel: pd.DataFrame,
    geometry: pd.DataFrame,
    spec: Mapping,
    *,
    include_targets: bool = True,
    require_complete: bool = True,
) -> pd.DataFrame:
    """Attach same-unit lag/rolling features whose source time never exceeds origin."""
    validate_task_table(geometry, spec)
    values = _validate_panel(panel)
    missing_units = set(geometry["unit"]).difference(values.columns)
    if missing_units:
        raise KeyError(f"panel lacks task units {sorted(missing_units)}")

    result = geometry.copy()
    lag_days = tuple(int(value) for value in spec["features"]["lag_days"])
    windows = tuple(int(value) for value in spec["features"]["rolling_windows_days"])
    statistics = tuple(spec["features"]["rolling_statistics"])
    ddof = int(spec["features"]["rolling_std_ddof"])
    numeric_features = feature_columns(spec)

    for column in numeric_features:
        result[column] = np.nan
    if include_targets:
        result["y_target"] = np.nan

    for unit, row_index in result.groupby("unit", sort=True).groups.items():
        series = values[unit]
        frame = pd.DataFrame(index=series.index)
        for lag in lag_days:
            frame[f"lag_{lag}"] = series.shift(lag - 1)
        for window in windows:
            rolling = series.rolling(window=window, min_periods=window)
            if "mean" in statistics:
                frame[f"rolling_mean_{window}"] = rolling.mean()
            if "median" in statistics:
                frame[f"rolling_median_{window}"] = rolling.median()
            if "std" in statistics:
                frame[f"rolling_std_{window}"] = rolling.std(ddof=ddof)
        origins = pd.DatetimeIndex(result.loc[row_index, "feature_timestamp"])
        selected = frame.reindex(origins)
        for column in frame.columns:
            result.loc[row_index, column] = selected[column].to_numpy()
        if include_targets:
            targets = pd.DatetimeIndex(result.loc[row_index, "target_timestamp"])
            result.loc[row_index, "y_target"] = series.reindex(targets).to_numpy()

    target_ts = pd.to_datetime(result["target_timestamp"])
    result["target_day_of_week"] = target_ts.dt.dayofweek.astype("float64")
    angle = 2.0 * np.pi * (target_ts.dt.month.astype("float64") - 1.0) / 12.0
    result["target_month_sin"] = np.sin(angle)
    result["target_month_cos"] = np.cos(angle)
    lookback = max(max(lag_days), max(windows))
    result["context_start_timestamp"] = pd.to_datetime(
        result["feature_timestamp"]
    ) - pd.to_timedelta(lookback - 1, unit="D")
    result["max_feature_source_timestamp"] = pd.to_datetime(result["feature_timestamp"])

    required_values = list(numeric_features)
    if include_targets:
        required_values.append("y_target")
    if require_complete and result[required_values].isna().any().any():
        bad = result[required_values].isna().any(axis=1)
        sample = result.loc[bad, ["unit", "feature_timestamp", "target_timestamp"]].iloc[0]
        raise ValueError(
            "task features/target are incomplete; first failure is "
            f"{sample['unit']} origin={sample['feature_timestamp']} "
            f"target={sample['target_timestamp']}"
        )
    if not (
        pd.to_datetime(result["max_feature_source_timestamp"])
        <= pd.to_datetime(result["feature_timestamp"])
    ).all():
        raise LeakageError("a materialized feature uses information after its feature timestamp")
    return result


def task_geometry_hash(tasks: pd.DataFrame) -> str:
    columns = [
        column
        for column in (
            "measurement_state",
            "task_role",
            "fold_id",
            "residual_role",
            "calibration_eligible",
            "unit",
            "horizon_days",
            "feature_timestamp",
            "target_timestamp",
            "fit_start",
            "fit_end",
            "score_start",
            "score_end",
            "seed",
        )
        if column in tasks.columns
    ]
    frame = tasks.loc[:, columns].copy()
    for column in frame.columns:
        if pd.api.types.is_datetime64_any_dtype(frame[column]):
            frame[column] = pd.to_datetime(frame[column]).dt.strftime("%Y-%m-%d")
    sort_columns = [
        column
        for column in ("measurement_state", "fold_id", "unit", "target_timestamp", "horizon_days")
        if column in frame.columns
    ]
    frame = frame.sort_values(sort_columns, kind="mergesort").reset_index(drop=True)
    payload = frame.to_csv(index=False, lineterminator="\n").encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


@dataclass(frozen=True)
class TrainingOnlyStandardizer:
    measurement_state: str
    feature_columns: tuple[str, ...]
    means: tuple[float, ...]
    scales: tuple[float, ...]
    n_fit_rows: int
    max_fit_target_timestamp: pd.Timestamp
    fit_geometry_sha256: str

    @classmethod
    def fit(
        cls,
        training_tasks: pd.DataFrame,
        columns: Sequence[str],
        spec: Mapping,
    ) -> "TrainingOnlyStandardizer":
        assert_task_access(training_tasks, "scaling", spec)
        columns = tuple(columns)
        if not columns:
            raise ValueError("scaler fit requires at least one frozen feature")
        if len(columns) != len(set(columns)):
            raise ValueError("scaler feature columns must be unique")
        frozen_features = set(feature_columns(spec))
        undeclared = set(columns).difference(frozen_features)
        if undeclared:
            raise LeakageError(
                "scaler columns must be declared A1 features; rejected "
                f"{sorted(undeclared)}"
            )
        missing = set(columns).difference(training_tasks.columns)
        if missing:
            raise KeyError(f"training tasks lack scaler features {sorted(missing)}")
        values = training_tasks.loc[:, columns].apply(pd.to_numeric, errors="raise")
        if values.isna().any().any() or not np.isfinite(values.to_numpy()).all():
            raise ValueError("scaler fit features must be finite and complete")
        means = values.mean(axis=0)
        scales = values.std(axis=0, ddof=0)
        replacement = float(spec["scaling"]["zero_variance_scale"])
        scales = scales.mask(scales.eq(0.0), replacement)
        return cls(
            measurement_state=str(training_tasks["measurement_state"].iloc[0]),
            feature_columns=columns,
            means=tuple(float(means[column]) for column in columns),
            scales=tuple(float(scales[column]) for column in columns),
            n_fit_rows=int(len(training_tasks)),
            max_fit_target_timestamp=pd.Timestamp(training_tasks["target_timestamp"].max()),
            fit_geometry_sha256=task_geometry_hash(training_tasks),
        )

    def transform(self, tasks: pd.DataFrame, spec: Mapping) -> pd.DataFrame:
        validate_task_table(tasks, spec)
        state = str(tasks["measurement_state"].iloc[0])
        if state != self.measurement_state:
            raise MeasurementStateError(
                f"scaler fitted on {self.measurement_state!r}, cannot silently transform {state!r}"
            )
        output = tasks.copy()
        for column, mean, scale in zip(self.feature_columns, self.means, self.scales):
            output[column] = (pd.to_numeric(output[column], errors="raise") - mean) / scale
        return output

    def digest(self) -> str:
        payload = {
            "measurement_state": self.measurement_state,
            "feature_columns": self.feature_columns,
            "means": self.means,
            "scales": self.scales,
            "n_fit_rows": self.n_fit_rows,
            "max_fit_target_timestamp": self.max_fit_target_timestamp.strftime("%Y-%m-%d"),
            "fit_geometry_sha256": self.fit_geometry_sha256,
        }
        return hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()


# ===========================================================================
# Phase A2 -- global forecasting model, declared baselines, and 2024 selection.
#
# Everything below fits estimators.  It may only ever see task tables that have
# already passed the A1 seals above, and it re-asserts those seals at each
# entry point rather than trusting its caller.
# ===========================================================================

LEVEL_KIND = "level"
DISPERSION_KIND = "dispersion"
UNTRANSFORMED_KIND = "untransformed"


def validate_model_spec(spec: Mapping) -> None:
    """Reject drift in the A2 estimator contract."""
    model = spec.get("model")
    if not isinstance(model, Mapping):
        raise ValueError("phase A2 requires a `model` specification block")

    state = model.get("development_measurement_state")
    if state not in measurement_state_names(spec):
        raise ValueError(f"A2 development measurement state {state!r} is not a declared state")

    context = model["context_normalisation"]
    context_end = pd.Timestamp(context["context_end"])
    development_end = pd.Timestamp(spec["dates"]["development_end"])
    if context_end > development_end:
        raise LeakageError(
            "A2 context normalisation may not read beyond the development period; "
            f"context_end={context_end.date()} exceeds development_end={development_end.date()}"
        )

    global_model = model["global_model"]
    if global_model.get("estimator") != "ridge_closed_form":
        raise ValueError("A2 global estimator drifted from the frozen ridge specification")
    if global_model.get("dependency_status") != "no_new_dependency":
        raise ValueError("A2 may not introduce a dependency without a new configuration version")
    alphas = tuple(float(value) for value in global_model["grid"]["alpha"])
    if not alphas or len(alphas) != len(set(alphas)) or any(value <= 0.0 for value in alphas):
        raise ValueError("A2 ridge grid must be unique and strictly positive")
    selection = global_model["selection"]
    if selection.get("period") != "hyperparameter_validation":
        raise LeakageError("A2 hyperparameters must be selected on the frozen 2024 tasks alone")
    if selection.get("metric") not in {"mase", "scaled_mae"}:
        raise ValueError("A2 selection metric must be a scale-free error measure")

    names = [entry["name"] for entry in model["baselines"]]
    if len(names) != len(set(names)) or not {"seasonal_naive", "local_ar_1_7"}.issubset(names):
        raise ValueError("A2 must declare the seasonal-naive and local AR(1,7) baselines")

    if model["tsfm_benchmarks"].get("included") is not False:
        raise ValueError(
            "frozen TSFM artefacts score a different task and unit population; "
            "including them requires a demonstrated identical-task proof"
        )
    if model["scoring"].get("winner_score_prohibited") is not True:
        raise ValueError("A2 may not invent a weighted winner score")
    if model["scoring"]["intervals"].get("provisional") is not True:
        raise ValueError("A2 intervals are provisional until A3 calibrates them")


def classify_feature_transforms(spec: Mapping) -> dict[str, str]:
    """Map every frozen A1 feature onto its context-normalisation behaviour.

    Levels move with the unit's centre and scale, dispersions move with the
    scale only, and calendar features are dimensionless.  The classification is
    derived from the frozen feature list, so it cannot silently miss a feature
    that a later A1 revision adds.
    """
    rule = spec["model"]["context_normalisation"]["feature_transform"]
    if rule.get("rule") != "prefix_classification":
        raise ValueError("A2 feature-transform rule drifted")
    dispersion_prefixes = tuple(rule["dispersion_prefixes"])
    untransformed = set(spec["features"]["calendar"]["fields"])

    kinds: dict[str, str] = {}
    for column in feature_columns(spec):
        if column in untransformed:
            kinds[column] = UNTRANSFORMED_KIND
        elif column.startswith(dispersion_prefixes):
            kinds[column] = DISPERSION_KIND
        else:
            kinds[column] = LEVEL_KIND
    if set(kinds) != set(feature_columns(spec)):
        raise ValueError("feature-transform classification does not partition the frozen features")
    return kinds


def load_development_panel(
    spec: Mapping,
    measurement_state: str,
    *,
    start: str | pd.Timestamp | None = None,
    end: str | pd.Timestamp | None = None,
) -> pd.DataFrame:
    """Load the wide daily panel for the declared A2 measurement state.

    A2 is authorised for the pinned primary state only.  The August vintage is
    a registry-gated sensitivity artefact and is not read here; a phase that
    needs it must obtain its own `allowed_consumers` entry.
    """
    declared = str(spec["model"]["development_measurement_state"])
    if measurement_state != declared:
        raise MeasurementStateError(
            f"A2 is frozen on the {declared!r} measurement state; {measurement_state!r} "
            "requires its own registry authorisation and a new configuration version"
        )
    from .spatial import wide_chokepoint_panel  # deferred: spatial imports the registry

    panel = wide_chokepoint_panel(
        value_col=spec["outcome"]["column"],
        start=str(pd.Timestamp(start or spec["dates"]["full_start"]).date()),
        end=str(pd.Timestamp(end or spec["dates"]["development_end"]).date()),
    )
    missing = set(development_units(spec)).difference(panel.columns)
    if missing:
        raise KeyError(f"panel lacks frozen development units {sorted(missing)}")
    return panel


def fit_unit_context_scales(
    panel: pd.DataFrame,
    spec: Mapping,
    *,
    measurement_state: str,
) -> dict[str, object]:
    """Fit one robust context scale per development unit, training-window only."""
    from .disruption_detector import fit_context_scale  # deferred: avoids an import cycle

    context = spec["model"]["context_normalisation"]
    scales: dict[str, object] = {}
    for unit in development_units(spec):
        scales[unit] = fit_context_scale(
            panel[unit],
            spec,
            measurement_state=measurement_state,
            context_start=context["context_start"],
            context_end=context["context_end"],
        )
    return scales


def apply_context_normalisation(
    tasks: pd.DataFrame,
    scales: Mapping[str, object],
    spec: Mapping,
    *,
    include_targets: bool = True,
) -> pd.DataFrame:
    """Move features and target into each unit's own normalised space."""
    kinds = classify_feature_transforms(spec)
    unknown = set(tasks["unit"]).difference(scales)
    if unknown:
        raise KeyError(f"no fitted context scale for units {sorted(unknown)}")

    output = tasks.copy()
    for unit, rows in output.groupby("unit", sort=True).groups.items():
        scale = scales[unit]
        centre = float(scale.center)
        spread = float(scale.scale)
        for column, kind in kinds.items():
            if kind == UNTRANSFORMED_KIND:
                continue
            values = pd.to_numeric(output.loc[rows, column], errors="raise").to_numpy()
            if kind == LEVEL_KIND:
                output.loc[rows, column] = (values - centre) / spread
            else:
                output.loc[rows, column] = values / spread
        if include_targets and "y_target" in output.columns:
            targets = pd.to_numeric(output.loc[rows, "y_target"], errors="raise").to_numpy()
            output.loc[rows, "z_target"] = (targets - centre) / spread
    return output


def denormalise(values: np.ndarray, units: pd.Series, scales: Mapping[str, object]) -> np.ndarray:
    """Invert the per-unit context normalisation for predictions."""
    centres = units.map(lambda unit: float(scales[unit].center)).to_numpy(dtype="float64")
    spreads = units.map(lambda unit: float(scales[unit].scale)).to_numpy(dtype="float64")
    return np.asarray(values, dtype="float64") * spreads + centres


@dataclass(frozen=True)
class RidgeGlobalModel:
    """Pooled ridge regression in context-normalised space, one per horizon."""

    horizon_days: int
    alpha: float
    feature_columns: tuple[str, ...]
    coefficients: tuple[float, ...]
    intercept: float
    n_fit_rows: int
    fit_geometry_sha256: str

    @classmethod
    def fit(
        cls,
        training_tasks: pd.DataFrame,
        columns: Sequence[str],
        spec: Mapping,
        *,
        horizon_days: int,
        alpha: float,
    ) -> "RidgeGlobalModel":
        assert_task_access(training_tasks, "fitting", spec)
        if not training_tasks["horizon_days"].eq(int(horizon_days)).all():
            raise ValueError("a horizon-specific model received mixed horizons")
        if alpha <= 0.0:
            raise ValueError("ridge penalty must be strictly positive")
        columns = tuple(columns)
        design = training_tasks.loc[:, list(columns)].to_numpy(dtype="float64")
        target = training_tasks["z_target"].to_numpy(dtype="float64")
        if not np.isfinite(design).all() or not np.isfinite(target).all():
            raise ValueError("ridge fit requires finite features and targets")

        # Centre so the intercept is never penalised, then solve through the
        # SVD.  This is the same estimator as solving the normal equations but
        # stays finite on a rank-deficient design, where forming the Gram
        # matrix would square the condition number and can overflow.
        design_mean = design.mean(axis=0)
        target_mean = float(target.mean())
        centred = design - design_mean
        # Adding a positive alpha to the diagonal makes the Gram matrix
        # symmetric positive definite for any design, singular or not, so the
        # Cholesky factorisation always exists and the solve is exact.
        #
        # Note on warnings: on this machine numpy is built against Apple
        # Accelerate, which raises a spurious "divide by zero encountered in
        # matmul" on healthy, finite inputs.  It is a BLAS artefact, not a
        # numerical failure, so the result is verified explicitly below rather
        # than the warning being suppressed.
        gram = centred.T @ centred
        gram[np.diag_indices_from(gram)] += float(alpha)
        factor = np.linalg.cholesky(gram)
        forward = np.linalg.solve(factor, centred.T @ (target - target_mean))
        beta = np.linalg.solve(factor.T, forward)
        if not np.isfinite(beta).all():
            raise ValueError(
                "ridge solution is not finite; the penalty is too small for this design"
            )
        return cls(
            horizon_days=int(horizon_days),
            alpha=float(alpha),
            feature_columns=columns,
            coefficients=tuple(float(value) for value in beta),
            intercept=float(target_mean - design_mean @ beta),
            n_fit_rows=int(len(training_tasks)),
            fit_geometry_sha256=task_geometry_hash(training_tasks),
        )

    def predict(self, tasks: pd.DataFrame) -> np.ndarray:
        design = tasks.loc[:, list(self.feature_columns)].to_numpy(dtype="float64")
        if not np.isfinite(design).all():
            raise ValueError("ridge prediction received a non-finite design matrix")
        return design @ np.asarray(self.coefficients, dtype="float64") + self.intercept

    def digest(self) -> str:
        payload = {
            "horizon_days": self.horizon_days,
            "alpha": self.alpha,
            "feature_columns": self.feature_columns,
            "coefficients": self.coefficients,
            "intercept": self.intercept,
            "n_fit_rows": self.n_fit_rows,
            "fit_geometry_sha256": self.fit_geometry_sha256,
        }
        return hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()


@dataclass(frozen=True)
class LocalARModel:
    """Per-unit direct AR(1,7) comparator, fitted in normalised space.

    Ordinary least squares with an intercept is equivariant under the affine
    per-unit normalisation, so fitting here and inverting gives the same raw
    predictions as fitting in raw units.  Normalised space is used so every
    estimator in A2 shares one representation.
    """

    unit: str
    horizon_days: int
    coefficients: tuple[float, float]
    intercept: float
    n_fit_rows: int

    @classmethod
    def fit(
        cls,
        training_tasks: pd.DataFrame,
        spec: Mapping,
        *,
        unit: str,
        horizon_days: int,
    ) -> "LocalARModel":
        assert_task_access(training_tasks, "fitting", spec)
        rows = training_tasks.loc[
            training_tasks["unit"].eq(unit)
            & training_tasks["horizon_days"].eq(int(horizon_days))
        ]
        if rows.empty:
            raise ValueError(f"local AR has no development rows for {unit} h={horizon_days}")
        design = np.column_stack(
            [
                np.ones(len(rows)),
                rows["lag_1"].to_numpy(dtype="float64"),
                rows["lag_7"].to_numpy(dtype="float64"),
            ]
        )
        target = rows["z_target"].to_numpy(dtype="float64")
        solution, *_ = np.linalg.lstsq(design, target, rcond=None)
        return cls(
            unit=unit,
            horizon_days=int(horizon_days),
            coefficients=(float(solution[1]), float(solution[2])),
            intercept=float(solution[0]),
            n_fit_rows=int(len(rows)),
        )

    def predict(self, tasks: pd.DataFrame) -> np.ndarray:
        lag_1 = tasks["lag_1"].to_numpy(dtype="float64")
        lag_7 = tasks["lag_7"].to_numpy(dtype="float64")
        return self.intercept + self.coefficients[0] * lag_1 + self.coefficients[1] * lag_7


def seasonal_naive_predictions(panel: pd.DataFrame, tasks: pd.DataFrame) -> np.ndarray:
    """Most recent same-weekday observation at or before the forecast origin.

    For a target ``tau`` and horizon ``h`` the source date is
    ``tau - 7 * ceil(h / 7)``, which is always at or before the origin, so the
    baseline never reads across its own information boundary.
    """
    targets = pd.to_datetime(tasks["target_timestamp"])
    origins = pd.to_datetime(tasks["feature_timestamp"])
    horizons = tasks["horizon_days"].to_numpy(dtype="int64")
    back_weeks = np.ceil(horizons / 7.0).astype("int64")
    sources = targets - pd.to_timedelta(7 * back_weeks, unit="D")
    if (sources.to_numpy() > origins.to_numpy()).any():
        raise LeakageError("seasonal-naive source date reached past its forecast origin")

    values = np.empty(len(tasks), dtype="float64")
    values[:] = np.nan
    unit_values = tasks["unit"].to_numpy()
    for unit in pd.unique(unit_values):
        mask = unit_values == unit
        values[mask] = panel[unit].reindex(pd.DatetimeIndex(sources[mask])).to_numpy()
    if not np.isfinite(values).all():
        raise ValueError("seasonal-naive baseline hit a missing source observation")
    return values


def mase_denominators(panel: pd.DataFrame, spec: Mapping) -> dict[str, float]:
    """Per-unit seasonal-7 mean absolute difference over the development window."""
    scoring = spec["model"]["scoring"]["mase_denominator"]
    minimum = float(scoring["minimum"])
    window = panel.loc[
        (panel.index >= pd.Timestamp(spec["dates"]["full_start"]))
        & (panel.index <= pd.Timestamp(spec["dates"]["development_end"]))
    ]
    denominators: dict[str, float] = {}
    for unit in development_units(spec):
        value = float(window[unit].diff(7).abs().mean())
        if not np.isfinite(value) or value < minimum:
            raise ValueError(
                f"MASE denominator for {unit} is degenerate ({value}); "
                "this unit cannot be scored on MASE under the frozen definition"
            )
        denominators[unit] = value
    return denominators


def pinball_loss(actual: np.ndarray, predicted: np.ndarray, quantile: float) -> float:
    """Mean pinball loss at one quantile level."""
    error = np.asarray(actual, dtype="float64") - np.asarray(predicted, dtype="float64")
    return float(np.mean(np.maximum(quantile * error, (quantile - 1.0) * error)))


def score_predictions(
    frame: pd.DataFrame,
    spec: Mapping,
    denominators: Mapping[str, float],
    scales: Mapping[str, object],
) -> pd.DataFrame:
    """Per model, horizon, and unit error measures in raw outcome units."""
    required = {"model", "horizon_days", "unit", "y_target", "prediction"}
    missing = required.difference(frame.columns)
    if missing:
        raise KeyError(f"scoring frame lacks {sorted(missing)}")

    records: list[dict[str, object]] = []
    for (model, horizon, unit), rows in frame.groupby(
        ["model", "horizon_days", "unit"], sort=True
    ):
        actual = rows["y_target"].to_numpy(dtype="float64")
        predicted = rows["prediction"].to_numpy(dtype="float64")
        error = actual - predicted
        mae = float(np.mean(np.abs(error)))
        records.append(
            {
                "model": model,
                "horizon_days": int(horizon),
                "unit": unit,
                "n_scored": int(len(rows)),
                "mae": mae,
                "rmse": float(np.sqrt(np.mean(np.square(error)))),
                "mase": mae / float(denominators[unit]),
                "scaled_mae": mae / float(scales[unit].scale),
                "mean_error": float(np.mean(error)),
            }
        )
    return pd.DataFrame.from_records(records).sort_values(
        ["model", "horizon_days", "unit"], kind="mergesort"
    ).reset_index(drop=True)


def residual_quantile_offsets(
    residuals_normalised: np.ndarray,
    quantiles: Sequence[float],
) -> dict[float, float]:
    """Empirical quantiles of normalised development residuals."""
    values = np.asarray(residuals_normalised, dtype="float64")
    if not np.isfinite(values).all() or values.size == 0:
        raise ValueError("interval construction requires finite residuals")
    return {float(q): float(np.quantile(values, q)) for q in quantiles}
