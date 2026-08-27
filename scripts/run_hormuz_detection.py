"""Hormuz cross-chokepoint detection runner.

``--phase audit --check-only`` is the A1 seal check: it reads configuration and
computes file hashes only, never touching a PortWatch outcome row.

``--phase validate`` is A2: it fits the pooled global model and the declared
baselines on the 27 non-Hormuz development units, selects the ridge penalty on
the frozen 2024 tasks alone, and writes the validation artefacts.  It fits no
detector.

``--phase calibrate`` is A3: it produces rolling-origin residuals across the 27
development units, calibrates one transferable threshold per model, horizon and
detector form against the macro-average episode rate, and runs both
leave-one-chokepoint-out tests.  It refuses to start unless the accepted A2 run
reproduces from the current configuration.  It reads no Hormuz row and scores
nothing on Hormuz; that is A4.

The Hormuz column is present in the loaded 28-unit panel but is never
materialised into a task, fitted, selected on, or scored.  That, and not "no
Hormuz row is read", is the safety claim these phases support.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from typing import Mapping, Sequence
import json
import platform
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lngfreight import config  # noqa: E402
from lngfreight.disruption_detector import (  # noqa: E402
    apply_event_mask,
    load_event_mask,
    validate_detector_calibration_tasks,
)
from lngfreight.detector_calibration import (  # noqa: E402
    DETECTOR_FORMS,
    calibrate_threshold,
    candidate_thresholds,
    curves_by_unit,
    digest_frame,
    eligible_residuals,
    residuals_for_fold,
    scale_invariant_score,
    score_frame,
    select_loco_alphas,
    validate_detector_spec,
)
from lngfreight.global_forecaster import (  # noqa: E402
    LeakageError,
    LocalARModel,
    MeasurementStateError,
    RidgeGlobalModel,
    TrainingOnlyStandardizer,
    apply_context_normalisation,
    assert_task_access,
    build_development_geometry,
    build_hormuz_scoring_geometry,
    build_rolling_residual_geometry,
    build_task_geometry,
    classify_feature_transforms,
    denormalise,
    development_units,
    feature_columns,
    fit_unit_context_scales,
    load_detection_spec,
    load_development_panel,
    mase_denominators,
    materialize_task_features,
    measurement_state_names,
    pinball_loss,
    residual_quantile_offsets,
    rolling_origin_folds,
    score_predictions,
    seasonal_naive_predictions,
    sha256_file,
    task_geometry_hash,
    validate_task_table,
)

# Sealing assertions that must remain False for the audit to pass. A1 is
# check-only: it must never read or print a post-event outcome.
MUST_BE_FALSE_ASSERTIONS = frozenset(
    {"post_event_outcomes_read", "post_event_outcomes_printed"}
)


def _measurement_state_checks(spec: dict) -> list[dict[str, object]]:
    checks = []
    for state in measurement_state_names(spec):
        state_spec = spec["measurement_states"][state]
        path = config.ROOT / state_spec["path"]
        if not path.is_file():
            raise FileNotFoundError(f"{state} measurement state is missing: {path}")
        actual = sha256_file(path)
        if actual != state_spec["sha256"]:
            raise ValueError(
                f"{state} measurement-state hash mismatch: expected "
                f"{state_spec['sha256']}, got {actual}"
            )
        checks.append(
            {
                "measurement_state": state,
                "path": state_spec["path"],
                "sha256": actual,
                "available": True,
                "outcome_rows_read": False,
            }
        )
    return checks


def _expect_failure(name: str, function) -> dict[str, object]:
    try:
        function()
    except (LeakageError, MeasurementStateError, ValueError) as exc:
        return {"check": name, "passed": True, "raised": type(exc).__name__}
    raise AssertionError(f"deliberate leakage check {name!r} did not fail")


def _leakage_checks(
    spec: dict,
    development: dict[str, pd.DataFrame],
    residuals: dict[str, pd.DataFrame],
) -> list[dict]:
    july = development["july"]
    fit = july.loc[july["task_role"].eq("development_fit")].head(3).copy()
    validation = july.loc[
        july["task_role"].eq("hyperparameter_validation")
    ].head(3).copy()
    for operation in ("fitting", "scaling", "feature_selection"):
        assert_task_access(fit, operation, spec)
    assert_task_access(validation, "hyperparameter_selection", spec)

    hormuz = build_hormuz_scoring_geometry(spec, "july").head(1).copy()
    checks = []
    for operation in (
        "fitting",
        "scaling",
        "feature_selection",
        "detector_calibration",
        "hyperparameter_selection",
    ):
        malicious = hormuz.copy()
        if operation == "detector_calibration":
            malicious["event_masked"] = False
            malicious["calibration_eligible"] = True
        checks.append(
            _expect_failure(
                f"hormuz_scoring_row_rejected_from_{operation}",
                lambda frame=malicious, op=operation: assert_task_access(frame, op, spec),
            )
        )

    mixed = pd.concat([development["july"].head(1), development["august"].head(1)])
    checks.append(
        _expect_failure(
            "july_august_join_rejected",
            lambda: assert_task_access(mixed, "fitting", spec),
        )
    )
    invalid_time = fit.copy()
    invalid_time["target_timestamp"] = invalid_time["feature_timestamp"]
    checks.append(
        _expect_failure(
            "non_future_target_rejected",
            lambda: validate_task_table(invalid_time, spec),
        )
    )
    invalid_horizon = build_task_geometry(
        ["2023-06-01"],
        ["dover_strait"],
        [2],
        measurement_state="july",
        task_role="development_fit",
        seed=int(spec["tasks"]["seed"]),
    )
    checks.append(
        _expect_failure(
            "non_frozen_horizon_rejected",
            lambda: assert_task_access(invalid_horizon, "fitting", spec),
        )
    )
    target_scaler = fit.copy()
    target_scaler["y_target"] = 0.0
    checks.append(
        _expect_failure(
            "target_column_rejected_from_scaling",
            lambda: TrainingOnlyStandardizer.fit(target_scaler, ["y_target"], spec),
        )
    )
    late_scoring = build_task_geometry(
        [pd.Timestamp(spec["dates"]["scoring_end"]) + pd.Timedelta(days=1)],
        [spec["population"]["hormuz_unit"]],
        [1],
        measurement_state="july",
        task_role="scoring_only",
        seed=int(spec["tasks"]["seed"]),
    )
    checks.append(
        _expect_failure(
            "post_window_scoring_rejected",
            lambda: validate_task_table(late_scoring, spec),
        )
    )
    origin_leak = residuals["july"].head(1).copy()
    origin_leak["fit_end"] = origin_leak["feature_timestamp"] + pd.Timedelta(days=1)
    checks.append(
        _expect_failure(
            "fit_cutoff_after_forecast_origin_rejected",
            lambda: validate_task_table(origin_leak, spec),
        )
    )
    relabeled = residuals["july"].head(1).copy()
    relabeled["residual_role"] = "hyperparameter_validation_oof"
    checks.append(
        _expect_failure(
            "residual_role_relabeling_rejected",
            lambda: validate_task_table(relabeled, spec),
        )
    )
    source_drift = deepcopy(spec)
    source_drift["event_mask"]["records"][0]["start"] = "2021-03-22"
    checks.append(
        _expect_failure(
            "event_mask_record_source_divergence_rejected",
            lambda: load_event_mask(source_drift),
        )
    )
    return checks


def build_audit() -> dict[str, object]:
    spec, spec_sha = load_detection_spec()
    state_checks = _measurement_state_checks(spec)
    states = measurement_state_names(spec)
    folds = rolling_origin_folds(spec)
    mask = load_event_mask(spec)

    geometry_by_state: dict[str, dict[str, object]] = {}
    development_samples: dict[str, pd.DataFrame] = {}
    residual_frames: dict[str, pd.DataFrame] = {}
    for state in states:
        development = build_development_geometry(spec, state)
        residual = build_rolling_residual_geometry(spec, state)
        scoring = build_hormuz_scoring_geometry(spec, state)
        development_samples[state] = pd.concat(
            [
                development.loc[development["task_role"].eq("development_fit")].head(3),
                development.loc[
                    development["task_role"].eq("hyperparameter_validation")
                ].head(3),
            ],
            ignore_index=True,
        )
        residual_frames[state] = residual
        eligible_role = residual.loc[residual["calibration_eligible"]].copy()
        application = apply_event_mask(eligible_role, mask)
        validate_detector_calibration_tasks(application.eligible, spec)
        geometry_by_state[state] = {
            "development_and_validation_tasks": int(len(development)),
            "development_sha256": task_geometry_hash(development),
            "rolling_residual_tasks": int(len(residual)),
            "rolling_residual_sha256": task_geometry_hash(residual),
            "hormuz_scoring_only_tasks": int(len(scoring)),
            "hormuz_scoring_sha256": task_geometry_hash(scoring),
            "hormuz_scoring_roles": sorted(scoring["task_role"].unique()),
            "eligible_before_event_mask": int(len(eligible_role)),
            "excluded_unit_day_tasks": int(len(application.excluded)),
            "eligible_after_event_mask": int(len(application.eligible)),
            "geometry_sha256_after_mask": task_geometry_hash(application.eligible),
        }

    leakage_checks = _leakage_checks(spec, development_samples, residual_frames)
    if not all(check["passed"] for check in leakage_checks):
        raise AssertionError("one or more A1 leakage checks failed")

    fold_rows = [
        {
            "fold_id": fold.fold_id,
            "fit_start": fold.fit_start.strftime("%Y-%m-%d"),
            "fit_end": fold.fit_end.strftime("%Y-%m-%d"),
            "fit_end_by_horizon": {
                str(horizon): (fold.score_start - pd.Timedelta(days=int(horizon))).strftime(
                    "%Y-%m-%d"
                )
                for horizon in spec["tasks"]["horizons_days"]
            },
            "score_start": fold.score_start.strftime("%Y-%m-%d"),
            "score_end": fold.score_end.strftime("%Y-%m-%d"),
        }
        for fold in folds
    ]
    mask_frame = mask.unit_days
    check_results = {check["check"]: bool(check["passed"]) for check in leakage_checks}
    all_residual_fit_cutoffs_safe = all(
        (
            pd.to_datetime(frame["fit_end"])
            <= pd.to_datetime(frame["feature_timestamp"])
        ).all()
        for frame in residual_frames.values()
    )
    audit = {
        "phase": "A1",
        "status": "PENDING",
        "mode": "audit_check_only",
        "configuration": {
            "path": "config/hormuz_detection.yaml",
            "sha256": spec_sha,
            "status": spec["status"],
            "plan_version": spec["plan"]["version"],
            "plan_sha256": spec["plan"]["sha256"],
            "seed": int(spec["tasks"]["seed"]),
        },
        "measurement_states": state_checks,
        "task_contract": {
            "development_units": int(spec["population"]["expected_development_units"]),
            "hormuz_unit": spec["population"]["hormuz_unit"],
            "horizons_days": spec["tasks"]["horizons_days"],
            "feature_columns": list(feature_columns(spec)),
            "identity_embedding_enabled": False,
            "network_factors_enabled": False,
        },
        "rolling_origin": {
            "n_folds": len(folds),
            "first_fold": fold_rows[0],
            "last_fold": fold_rows[-1],
            "folds": fold_rows,
        },
        "geometry": geometry_by_state,
        "event_mask": {
            "sha256": mask.sha256,
            "source_sha256": dict(mask.source_sha256),
            "n_unique_unit_days": int(len(mask_frame)),
            "excluded_units": sorted(mask_frame["unit"].unique()),
            "unit_day_scope": True,
            "residual_derived": False,
            "same_date_unaffected_units_retained": True,
        },
        "leakage_checks": leakage_checks,
        "sealing_assertions": {
            "hormuz_excluded_from_training": all(
                spec["population"]["hormuz_unit"] not in set(frame["unit"])
                for frame in development_samples.values()
            ),
            "hormuz_excluded_from_detector_calibration": check_results[
                "hormuz_scoring_row_rejected_from_detector_calibration"
            ],
            "hormuz_from_2025_12_01_is_scoring_only": all(
                details["hormuz_scoring_roles"] == ["scoring_only"]
                for details in geometry_by_state.values()
            ),
            "feature_timestamp_strictly_precedes_target": all_residual_fit_cutoffs_safe,
            "fit_cutoff_no_later_than_forecast_origin": all_residual_fit_cutoffs_safe,
            "scaling_is_training_or_context_only": check_results[
                "target_column_rejected_from_scaling"
            ],
            "hyperparameter_selection_is_2024_only": check_results[
                "hormuz_scoring_row_rejected_from_hyperparameter_selection"
            ],
            "fixed_horizons_enforced": check_results["non_frozen_horizon_rejected"],
            "event_mask_records_bound_to_source": check_results[
                "event_mask_record_source_divergence_rejected"
            ],
            "july_august_never_joined_or_averaged": check_results[
                "july_august_join_rejected"
            ],
            "post_event_outcomes_read": False,
            "post_event_outcomes_printed": False,
        },
        "outputs_written": [],
        "a2_started": False,
        "limitations": [
            "A1 verifies task and information geometry only; no model is fitted.",
            "No detector threshold or false-alarm rate is calibrated in A1.",
            "Measurement-state files are hash-checked but outcome rows are not read by check-only audit.",
        ],
    }
    audit["status"] = _derive_status(audit)
    return audit


def _derive_status(audit: Mapping[str, object]) -> str:
    """Derive PASS/FAIL from the evidence instead of asserting it.

    Every hostile check must have passed, every positive sealing assertion must
    be True, and every assertion that must remain False (the audit reads and
    prints no post-event outcome) must be False. `status` is never a literal:
    an assertion that is computed but not backed by a raising validator would
    otherwise be able to report False underneath a PASS banner.
    """
    failures: list[str] = []
    for check in audit["leakage_checks"]:
        if not bool(check["passed"]):
            failures.append(f"leakage_check:{check['check']}")
    assertions = dict(audit["sealing_assertions"])
    for name, value in assertions.items():
        must_be_false = name in MUST_BE_FALSE_ASSERTIONS
        if must_be_false and bool(value):
            failures.append(f"sealing_assertion_must_be_false:{name}")
        elif not must_be_false and not bool(value):
            failures.append(f"sealing_assertion:{name}")
    missing = MUST_BE_FALSE_ASSERTIONS.difference(assertions)
    if missing:
        failures.extend(f"missing_assertion:{name}" for name in sorted(missing))
    audit["status_failures"] = sorted(failures)
    return "PASS" if not failures else "FAIL"


# ===========================================================================
# Phase A2 -- fit the global model and the declared baselines, then select
# hyperparameters on the frozen 2024 tasks alone.
# ===========================================================================

# Positive assertions that must hold, and the negative ones that must not.
A2_MUST_BE_FALSE = frozenset(
    {
        "hormuz_row_entered_any_estimator",
        "hormuz_materialised_into_tasks",
        "validation_influenced_context_scale",
        "measurement_states_mixed",
    }
)


def _git(*args: str) -> str:
    try:
        return subprocess.run(
            ["git", *args],
            cwd=config.ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return ""


def _selected_alpha(scores: pd.DataFrame, spec: Mapping, horizon: int) -> float:
    """Pick the grid point with the best mean 2024 MASE; ties go to the smallest."""
    selection = spec["model"]["global_model"]["selection"]
    metric = str(selection["metric"])
    candidates = scores.loc[
        scores["model"].str.startswith("global_ridge_alpha_")
        & scores["horizon_days"].eq(int(horizon))
    ]
    if candidates.empty:
        raise ValueError(f"no global-model candidates scored at horizon {horizon}")
    aggregate = candidates.groupby("model", sort=True)[metric].mean()
    best = float(aggregate.min())
    tied = [
        float(name.rsplit("_", 1)[1])
        for name, value in aggregate.items()
        if np.isclose(value, best, rtol=0.0, atol=1e-12)
    ]
    return min(tied)


def _predict_all(
    spec: Mapping,
    panel: pd.DataFrame,
    development: pd.DataFrame,
    scored: pd.DataFrame,
    scales: Mapping[str, object],
    horizon: int,
    alphas: Sequence[float],
) -> tuple[pd.DataFrame, dict[str, object]]:
    """Fit every candidate at one horizon and predict on the scored tasks."""
    columns = feature_columns(spec)
    dev_h = development.loc[development["horizon_days"].eq(int(horizon))]
    out_h = scored.loc[scored["horizon_days"].eq(int(horizon))]
    frames: list[pd.DataFrame] = []
    fitted: dict[str, object] = {}

    for alpha in alphas:
        model = RidgeGlobalModel.fit(
            dev_h, columns, spec, horizon_days=int(horizon), alpha=float(alpha)
        )
        name = f"global_ridge_alpha_{alpha:g}"
        fitted[name] = model
        frames.append(
            out_h.loc[:, ["unit", "horizon_days", "target_timestamp", "y_target"]].assign(
                model=name,
                z_prediction=model.predict(out_h),
            )
        )

    local_predictions = np.empty(len(out_h), dtype="float64")
    local_predictions[:] = np.nan
    local_models: dict[str, object] = {}
    unit_values = out_h["unit"].to_numpy()
    for unit in development_units(spec):
        local = LocalARModel.fit(dev_h, spec, unit=unit, horizon_days=int(horizon))
        local_models[unit] = local
        mask = unit_values == unit
        if mask.any():
            local_predictions[mask] = local.predict(out_h.loc[mask])
    if not np.isfinite(local_predictions).all():
        raise ValueError("local AR left an unscored row")
    fitted["local_ar_1_7"] = local_models
    frames.append(
        out_h.loc[:, ["unit", "horizon_days", "target_timestamp", "y_target"]].assign(
            model="local_ar_1_7",
            z_prediction=local_predictions,
        )
    )

    combined = pd.concat(frames, ignore_index=True)
    combined["prediction"] = denormalise(
        combined["z_prediction"].to_numpy(), combined["unit"], scales
    )

    # The seasonal-naive comparator is a lookup in raw units, not a fit.
    seasonal = out_h.loc[:, ["unit", "horizon_days", "target_timestamp", "y_target"]].assign(
        model="seasonal_naive",
        prediction=seasonal_naive_predictions(panel, out_h),
    )
    centres = seasonal["unit"].map(lambda unit: float(scales[unit].center)).to_numpy()
    spreads = seasonal["unit"].map(lambda unit: float(scales[unit].scale)).to_numpy()
    seasonal["z_prediction"] = (seasonal["prediction"].to_numpy() - centres) / spreads
    return pd.concat([combined, seasonal], ignore_index=True), fitted


def run_validation() -> dict:
    """A2: fit on development tasks, select on 2024, and write the artefacts."""
    spec, spec_sha = load_detection_spec()
    state = str(spec["model"]["development_measurement_state"])
    state_checks = _measurement_state_checks(spec)

    tasks = build_development_geometry(spec, state)
    panel = load_development_panel(
        spec,
        state,
        start=spec["dates"]["full_start"],
        end=spec["dates"]["hyperparameter_validation_end"],
    )
    materialised = materialize_task_features(panel, tasks, spec)
    scales = fit_unit_context_scales(panel, spec, measurement_state=state)
    normalised = apply_context_normalisation(materialised, scales, spec)

    development = normalised.loc[normalised["task_role"].eq("development_fit")].copy()
    validation = normalised.loc[normalised["task_role"].eq("hyperparameter_validation")].copy()
    assert_task_access(development, "fitting", spec)
    assert_task_access(validation, "hyperparameter_selection", spec)

    standardiser = TrainingOnlyStandardizer.fit(development, feature_columns(spec), spec)
    development = standardiser.transform(development, spec)
    validation = standardiser.transform(validation, spec)

    denominators = mase_denominators(panel, spec)
    horizons = [int(value) for value in spec["tasks"]["horizons_days"]]
    alphas = [float(value) for value in spec["model"]["global_model"]["grid"]["alpha"]]

    validation_frames: list[pd.DataFrame] = []
    development_frames: list[pd.DataFrame] = []
    for horizon in horizons:
        predicted, _ = _predict_all(
            spec, panel, development, validation, scales, horizon, alphas
        )
        validation_frames.append(predicted)
        in_sample, _ = _predict_all(
            spec, panel, development, development, scales, horizon, alphas
        )
        development_frames.append(in_sample)

    validation_predictions = pd.concat(validation_frames, ignore_index=True)
    development_predictions = pd.concat(development_frames, ignore_index=True)
    scores = score_predictions(validation_predictions, spec, denominators, scales)

    selection = {
        int(horizon): _selected_alpha(scores, spec, int(horizon)) for horizon in horizons
    }
    # Each horizon reports the penalty selected for that horizon, not every
    # penalty selected anywhere: a model chosen at h=1 is not the reported
    # model at h=30 if a different alpha won there.
    baselines = {"seasonal_naive", "local_ar_1_7"}
    reported_by_horizon = {
        int(horizon): {f"global_ridge_alpha_{selection[int(horizon)]:g}"} | baselines
        for horizon in horizons
    }
    reported = set().union(*reported_by_horizon.values())

    # Provisional intervals from in-sample development residuals, per A2 config.
    interval_cfg = spec["model"]["scoring"]["intervals"]
    levels = [float(value) for value in interval_cfg["nominal_levels"]]
    pinball_quantiles = [float(value) for value in interval_cfg["pinball_quantiles"]]
    needed = sorted({0.5 - level / 2.0 for level in levels} | {0.5 + level / 2.0 for level in levels} | set(pinball_quantiles))

    interval_rows: list[dict[str, object]] = []
    for horizon in horizons:
        for model in sorted(reported_by_horizon[int(horizon)]):
            dev_rows = development_predictions.loc[
                development_predictions["model"].eq(model)
                & development_predictions["horizon_days"].eq(horizon)
            ]
            val_rows = validation_predictions.loc[
                validation_predictions["model"].eq(model)
                & validation_predictions["horizon_days"].eq(horizon)
            ]
            if dev_rows.empty or val_rows.empty:
                continue
            centres = dev_rows["unit"].map(lambda unit: float(scales[unit].center)).to_numpy()
            spreads = dev_rows["unit"].map(lambda unit: float(scales[unit].scale)).to_numpy()
            dev_residual_z = (
                (dev_rows["y_target"].to_numpy(dtype="float64") - centres) / spreads
                - dev_rows["z_prediction"].to_numpy(dtype="float64")
            )
            offsets = residual_quantile_offsets(dev_residual_z, needed)

            val_spreads = val_rows["unit"].map(lambda unit: float(scales[unit].scale)).to_numpy()
            actual = val_rows["y_target"].to_numpy(dtype="float64")
            point = val_rows["prediction"].to_numpy(dtype="float64")
            row: dict[str, object] = {"model": model, "horizon_days": horizon}
            for level in levels:
                lower = point + offsets[0.5 - level / 2.0] * val_spreads
                upper = point + offsets[0.5 + level / 2.0] * val_spreads
                inside = (actual >= lower) & (actual <= upper)
                row[f"coverage_{level:g}"] = float(np.mean(inside))
                row[f"mean_width_{level:g}"] = float(np.mean(upper - lower))
            for quantile in pinball_quantiles:
                predicted_q = point + offsets[quantile] * val_spreads
                row[f"pinball_{quantile:g}"] = pinball_loss(actual, predicted_q, quantile)
            interval_rows.append(row)

    aggregate = (
        scores.groupby(["model", "horizon_days"], sort=True)[
            ["mae", "rmse", "mase", "scaled_mae"]
        ]
        .mean()
        .reset_index()
    )

    selected_mask = pd.Series(False, index=validation_predictions.index)
    for horizon, names in reported_by_horizon.items():
        selected_mask |= validation_predictions["horizon_days"].eq(horizon) & (
            validation_predictions["model"].isin(names)
        )
    reported_predictions = validation_predictions.loc[selected_mask].copy()
    reported_predictions = reported_predictions.loc[
        :, ["model", "unit", "horizon_days", "target_timestamp", "y_target", "prediction"]
    ].sort_values(
        ["model", "horizon_days", "unit", "target_timestamp"], kind="mergesort"
    ).reset_index(drop=True)

    outputs = spec["model"]["outputs"]
    scores_path = config.ROOT / outputs["scores"]
    predictions_path = config.ROOT / outputs["predictions"]
    manifest_path = config.ROOT / outputs["manifest"]
    scores_path.parent.mkdir(parents=True, exist_ok=True)
    scores.to_csv(scores_path, index=False)
    reported_predictions.to_csv(predictions_path, index=False)

    hormuz = spec["population"]["hormuz_unit"]
    touched_units = (
        set(development["unit"]) | set(validation["unit"]) | set(scores["unit"])
    )
    context_end = pd.Timestamp(spec["model"]["context_normalisation"]["context_end"])
    assertions = {
        "hormuz_row_entered_any_estimator": hormuz in touched_units,
        "validation_influenced_context_scale": any(
            pd.Timestamp(scale.context_end) > context_end for scale in scales.values()
        ),
        "measurement_states_mixed": len(
            set(development["measurement_state"]) | set(validation["measurement_state"])
        )
        != 1,
        "development_targets_within_frozen_period": bool(
            pd.to_datetime(development["target_timestamp"]).max()
            <= pd.Timestamp(spec["dates"]["development_end"])
        ),
        "validation_targets_within_frozen_2024": bool(
            pd.to_datetime(validation["target_timestamp"]).min()
            >= pd.Timestamp(spec["dates"]["hyperparameter_validation_start"])
            and pd.to_datetime(validation["target_timestamp"]).max()
            <= pd.Timestamp(spec["dates"]["hyperparameter_validation_end"])
        ),
        "scaler_fitted_on_development_only": bool(
            pd.Timestamp(standardiser.max_fit_target_timestamp)
            <= pd.Timestamp(spec["dates"]["development_end"])
        ),
        "targets_follow_feature_timestamps": bool(
            (
                pd.to_datetime(validation["target_timestamp"])
                > pd.to_datetime(validation["feature_timestamp"])
            ).all()
        ),
        "development_population_is_27_non_hormuz": len(touched_units)
        == int(spec["population"]["expected_development_units"]),
        "tsfm_benchmarks_excluded": spec["model"]["tsfm_benchmarks"]["included"] is False,
        "hormuz_materialised_into_tasks": hormuz in set(materialised["unit"]),
    }

    manifest = {
        "schema": "hormuz_detection_validation_manifest/1",
        "phase": "A2",
        "status": "PENDING",
        "script": "scripts/run_hormuz_detection.py",
        "command": "run_hormuz_detection.py --phase validate",
        "run_utc": pd.Timestamp.utcnow().isoformat(),
        "track_ownership": {
            "plan_default_owner": "ChatGPT",
            "reassigned_to": "Claude",
            "reassigned_by": "Mher",
            "reassigned_on": "2026-08-27",
            "consequence": (
                "Plan section 8 gives Claude the adversarial review of Track A. "
                "With Track A reassigned, that independent review is not "
                "available for A2 and Mher accepted that cost explicitly."
            ),
        },
        "git": {
            "commit": _git("rev-parse", "HEAD"),
            "branch": _git("branch", "--show-current"),
            "dirty": bool(_git("status", "--porcelain")),
        },
        "config": {"path": "config/hormuz_detection.yaml", "sha256": spec_sha},
        "plan": {"version": spec["plan"]["version"], "sha256": spec["plan"]["sha256"]},
        "inputs": {
            "measurement_states_verified": [
                # `state_checks` records the A1 hash-only view, where nothing is
                # read.  A2 does read outcome rows for the state it fits on, so
                # that flag is corrected here rather than inherited untrue.
                {**check, "outcome_rows_read": check["measurement_state"] == state}
                for check in state_checks
            ],
            "measurement_state_used": state,
            "hormuz_handling": {
                "present_in_loaded_panel": hormuz in panel.columns,
                "materialised_into_tasks": hormuz in set(materialised["unit"]),
                "entered_fitting": hormuz in set(development["unit"]),
                "entered_hyperparameter_selection": hormuz in set(validation["unit"]),
                "scored": hormuz in set(validation_predictions["unit"]),
                "claim": (
                    "The Hormuz column is loaded with the panel. It is never "
                    "materialised into a task, fitted, selected on, or scored."
                ),
            },
            "outcome_column": spec["outcome"]["column"],
            "panel_days": int(len(panel)),
            "panel_units": int(panel.shape[1]),
        },
        "analysis_window": {
            "development_start": str(pd.to_datetime(development["target_timestamp"]).min().date()),
            "development_end": spec["dates"]["development_end"],
            "validation_start": spec["dates"]["hyperparameter_validation_start"],
            "validation_end": spec["dates"]["hyperparameter_validation_end"],
            "context_start": spec["model"]["context_normalisation"]["context_start"],
            "context_end": spec["model"]["context_normalisation"]["context_end"],
        },
        "estimators": {
            "global_model": spec["model"]["global_model"]["estimator"],
            "grid_alpha": alphas,
            "selected_alpha_by_horizon": {str(k): v for k, v in selection.items()},
            "selection_metric": spec["model"]["global_model"]["selection"]["metric"],
            "selection_period": "2024 hyperparameter-validation tasks only",
            "baselines": ["seasonal_naive", "local_ar_1_7"],
            "tsfm_benchmarks_included": False,
            "tsfm_exclusion_reason": spec["model"]["tsfm_benchmarks"]["reason"],
            "stochastic_component": False,
            "seed": int(spec["tasks"]["seed"]),
            "seed_note": "recorded for provenance; the closed-form fits are deterministic",
        },
        "features": {
            "columns": list(feature_columns(spec)),
            "transform_kinds": classify_feature_transforms(spec),
            "standardiser_digest": standardiser.digest(),
            "context_scale_digests": {
                unit: scale.digest() for unit, scale in sorted(scales.items())
            },
        },
        "geometry": {
            "development_rows": int(len(development)),
            "validation_rows": int(len(validation)),
            "development_geometry_sha256": task_geometry_hash(development),
            "validation_geometry_sha256": task_geometry_hash(validation),
        },
        "results": {
            "aggregate": aggregate.to_dict(orient="records"),
            "intervals": interval_rows,
            "mase_denominators": denominators,
        },
        "sealing_assertions": assertions,
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "pandas": pd.__version__,
            "numpy": np.__version__,
        },
        "outputs": {
            "scores": outputs["scores"],
            "predictions": outputs["predictions"],
            "manifest": outputs["manifest"],
            "scores_sha256": sha256_file(scores_path),
            "predictions_sha256": sha256_file(predictions_path),
            "reported_models": sorted(reported),
            "reported_models_by_horizon": {
                str(horizon): sorted(names)
                for horizon, names in sorted(reported_by_horizon.items())
            },
            "scores_cover_full_grid": True,
            "predictions_cover_reported_models_only": True,
        },
        "limitations": [
            "Provisional intervals come from in-sample development residuals and are "
            "expected to be anti-conservative; the reported 2024 coverage is the honest "
            "check on them. Calibrated intervals are an A3 deliverable.",
            "The global estimator is a regularized linear model, not gradient boosting: "
            "scikit-learn is absent from .venv and the plan forbids a new dependency "
            "without Mher's documented approval. A nonlinear learner could change the "
            "comparison against the local baseline.",
            "target_day_of_week enters as a numeric code under the frozen A1 feature "
            "contract, which a linear model cannot read as a cyclical effect.",
            "August is not read at A2. Any cross-state statement waits for A4 and needs "
            "a registry allowed_consumers entry for the vintage.",
            "Bering Strait has a zero median absolute deviation over the context window, "
            "so its context scale falls back to the standard deviation.",
        ],
        "claims_not_authorised": [
            "Any causal effect, ATT, or structural interpretation of these errors.",
            "Any statement about Hormuz: no Hormuz row was fitted or scored here. "
            "The Hormuz column is present in the loaded panel.",
            "That pooling as such produced the gain: the pooled model carries 17 "
            "features and the local AR baseline carries two, so the comparison "
            "does not separate pooling from feature richness.",
            "That the unexplained error is irreducible noise.",
            "Any detection or alarm claim; the detector is calibrated in A3.",
            "Treating a global-model win or loss as evidence about the disruption.",
        ],
    }
    manifest["status"] = _derive_validation_status(manifest)
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True, default=str))
    return manifest


def _derive_validation_status(manifest: Mapping[str, object]) -> str:
    """Derive PASS/FAIL from the A2 sealing evidence rather than asserting it."""
    failures: list[str] = []
    assertions = dict(manifest["sealing_assertions"])
    for name, value in assertions.items():
        must_be_false = name in A2_MUST_BE_FALSE
        if must_be_false and bool(value):
            failures.append(f"sealing_assertion_must_be_false:{name}")
        elif not must_be_false and not bool(value):
            failures.append(f"sealing_assertion:{name}")
    missing = A2_MUST_BE_FALSE.difference(assertions)
    failures.extend(f"missing_assertion:{name}" for name in sorted(missing))
    manifest["status_failures"] = sorted(failures)
    return "PASS" if not failures else "FAIL"


# ===========================================================================
# Phase A3 -- detector calibration.
# ===========================================================================

A3_MUST_BE_FALSE = frozenset(
    {
        "hormuz_entered_calibration",
        "masked_unit_days_entered_calibration",
        "selection_year_entered_calibration",
        "residuals_reach_past_calibration_end",
        "per_unit_thresholds_used",
        "august_state_read",
    }
)

RIDGE_MODEL = "global_ridge"
SEASONAL_NAIVE = "seasonal_naive"


def _a2_gate(spec: Mapping, spec_sha: str) -> dict:
    """A3 may only run behind an A2 run that reproduces from this configuration.

    The gate is the accepted A2 manifest itself, not a remembered number: it must
    be PASS, made under this exact configuration hash, and made from a clean
    tree.  Anything else means the model A3 is about to calibrate is not the
    model Mher accepted.
    """
    path = config.ROOT / spec["model"]["outputs"]["manifest"]
    if not path.is_file():
        raise SystemExit(
            "A3 requires the accepted A2 validation manifest; run --phase validate first"
        )
    manifest = json.loads(path.read_text())
    problems: list[str] = []
    if manifest.get("status") != "PASS":
        problems.append(f"A2 manifest status is {manifest.get('status')!r}, not PASS")
    if manifest.get("config", {}).get("sha256") != spec_sha:
        problems.append(
            "A2 was run under a different configuration hash "
            f"({manifest.get('config', {}).get('sha256')} against {spec_sha})"
        )
    if manifest.get("git", {}).get("dirty") is not False:
        problems.append("the accepted A2 run was not made from a clean tree")
    for name in ("scores", "predictions"):
        artefact = config.ROOT / manifest["outputs"][name]
        if not artefact.is_file():
            problems.append(f"A2 {name} artefact is missing")
        elif sha256_file(artefact) != manifest["outputs"][f"{name}_sha256"]:
            problems.append(f"A2 {name} artefact no longer matches its recorded hash")
    if problems:
        raise SystemExit(
            "A3 is gated on a reproduced A2 run and that gate is not met:\n  - "
            + "\n  - ".join(problems)
        )
    return manifest


def _episode_rows(
    curves: Mapping[str, object],
    threshold: float,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    point = np.array([float(threshold)])
    for unit, curve in sorted(curves.items()):
        episodes = int(curve.episodes_at(point)[0])
        days = int(curve.duration_at(point)[0])
        rows.append(
            {
                "unit": unit,
                "episodes": episodes,
                "censored_episodes": int(curve.censored_at(point)[0]),
                "episode_days": days,
                "eligible_days": int(curve.eligible_days),
                "exposure_years": float(curve.exposure_years),
                "episodes_per_year": float(episodes / curve.exposure_years),
                "mean_episode_days": float(days / episodes) if episodes else 0.0,
            }
        )
    return rows


def _solution_record(
    solution,
    *,
    model: str,
    horizon: int,
    form: str,
    scope: str,
    held_out_unit: str = "",
    held_out: Mapping[str, object] | None = None,
) -> dict[str, object]:
    record: dict[str, object] = {
        "model": model,
        "horizon_days": int(horizon),
        "form": form,
        "scope": scope,
        "held_out_unit": held_out_unit,
        "threshold": solution.threshold,
        "requested_episodes_per_year": solution.requested_rate,
        "achieved_episodes_per_year": solution.achieved_rate,
        "exceedance_share_of_unit_days": solution.exceedance_share,
        "attainable": solution.attainable,
        "n_calibration_units": solution.n_units,
        "n_candidate_thresholds": solution.n_candidates,
        "rate_curve_monotone": solution.monotone,
        "monotonicity_violations": solution.monotonicity_violations,
        "max_upward_rate_step": solution.max_upward_step,
        "literal_tie_rule_threshold": solution.literal_rule_threshold,
        "literal_tie_rule_rate": solution.literal_rule_achieved_rate,
        "literal_tie_rule_exceedance_share": solution.literal_rule_exceedance_share,
        "literal_tie_rule_degenerate": solution.literal_rule_degenerate,
        "held_out_episodes": "",
        "held_out_censored_episodes": "",
        "held_out_exposure_years": "",
        "held_out_episodes_per_year": "",
    }
    if held_out is not None:
        record.update(
            {
                "held_out_episodes": held_out["episodes"],
                "held_out_censored_episodes": held_out["censored_episodes"],
                "held_out_exposure_years": held_out["exposure_years"],
                "held_out_episodes_per_year": held_out["episodes_per_year"],
            }
        )
    return record


def run_calibration() -> dict:
    """A3: rolling residuals, one transferable threshold, and both LOCO tests."""
    spec, spec_sha = load_detection_spec()
    validate_detector_spec(spec)
    a2 = _a2_gate(spec, spec_sha)

    state = str(spec["model"]["development_measurement_state"])
    units = list(development_units(spec))
    horizons = [int(value) for value in spec["tasks"]["horizons_days"]]
    selected_alpha = {
        int(key): float(value)
        for key, value in a2["estimators"]["selected_alpha_by_horizon"].items()
    }

    panel = load_development_panel(
        spec,
        state,
        start=spec["dates"]["full_start"],
        end=spec["dates"]["detector_calibration_end"],
    )
    mask = load_event_mask(spec)
    residual_geometry = build_rolling_residual_geometry(spec, state)
    folds = rolling_origin_folds(spec)

    # Penalty reselection for end-to-end LOCO: the held-out unit is withheld
    # from hyperparameter selection too, so it cannot inherit A2's penalty.
    loco_alphas = select_loco_alphas(spec, panel, measurement_state=state)

    frames: list[pd.DataFrame] = []
    loco_blocks: list[np.ndarray] = []
    drift: dict[str, dict[str, list[float]]] = {
        unit: {str(horizon): [] for horizon in horizons} for unit in units
    }
    # Every fold's scale must have been fitted through that fold's own
    # horizon-specific fit_end.  This is the check that the algorithm was
    # refitted; whether the resulting number moves is a property of the data.
    context_end_matches = True
    for horizon in horizons:
        for fold in folds:
            produced = residuals_for_fold(
                spec,
                panel,
                fold,
                horizon,
                residual_geometry,
                measurement_state=state,
                alpha=selected_alpha[horizon],
                loco_alphas={unit: loco_alphas[horizon][unit] for unit in units},
            )
            frames.append(produced.frame)
            loco_blocks.append(produced.loco_predictions)
            expected_end = fold.score_start - pd.Timedelta(days=horizon)
            for unit in units:
                drift[unit][str(horizon)].append(produced.context_scales[unit])
                if produced.context_ends[unit] != expected_end:
                    context_end_matches = False

    residuals = pd.concat(frames, ignore_index=True)
    loco_matrix = np.vstack(loco_blocks)
    residuals["row_id"] = np.arange(len(residuals), dtype="int64")

    # Seasonal naive is a lookup on the same rows, so it needs no fold refit.
    residuals["seasonal_naive_prediction"] = seasonal_naive_predictions(
        panel,
        residuals.assign(
            feature_timestamp=pd.to_datetime(residuals["target_timestamp"])
            - pd.to_timedelta(residuals["horizon_days"], unit="D")
        ),
    )

    admitted, excluded = eligible_residuals(residuals, spec, mask)
    kept = admitted["row_id"].to_numpy()
    loco_matrix = loco_matrix[kept]

    # The frozen design requires the invariance test to be executed, not claimed.
    factor = 3.7
    invariance_holds = bool(
        np.allclose(
            scale_invariant_score(
                admitted["prediction"].to_numpy(dtype="float64") * factor,
                admitted["y_target"].to_numpy(dtype="float64") * factor,
                admitted["context_scale"].to_numpy(dtype="float64") * factor,
            ),
            score_frame(admitted, "scale_invariant"),
        )
    )

    calibration_rows: list[dict[str, object]] = []
    false_alarm_rows: list[dict[str, object]] = []
    operational: dict[tuple[str, int, str], object] = {}

    model_columns = {RIDGE_MODEL: "prediction", SEASONAL_NAIVE: "seasonal_naive_prediction"}
    for model, column in model_columns.items():
        for horizon in horizons:
            rows = admitted.loc[admitted["horizon_days"].eq(horizon)]
            for form in DETECTOR_FORMS:
                curves = curves_by_unit(rows, spec, form, prediction_column=column)
                solution = calibrate_threshold(list(curves.values()), spec)
                operational[(model, horizon, form)] = solution
                calibration_rows.append(
                    _solution_record(
                        solution, model=model, horizon=horizon, form=form, scope="operational"
                    )
                )
                for record in _episode_rows(curves, solution.threshold):
                    false_alarm_rows.append(
                        {"model": model, "horizon_days": horizon, "form": form, **record}
                    )

                # threshold_loco: same residuals, the unit withheld only from
                # the threshold. This isolates whether a threshold transfers.
                grid = candidate_thresholds(list(curves.values()))
                for held_out in units:
                    retained = [curves[unit] for unit in units if unit != held_out]
                    loco = calibrate_threshold(retained, spec, candidates=grid)
                    point = np.array([loco.threshold])
                    curve = curves[held_out]
                    calibration_rows.append(
                        _solution_record(
                            loco,
                            model=model,
                            horizon=horizon,
                            form=form,
                            scope="threshold_loco",
                            held_out_unit=held_out,
                            held_out={
                                "episodes": int(curve.episodes_at(point)[0]),
                                "censored_episodes": int(curve.censored_at(point)[0]),
                                "exposure_years": float(curve.exposure_years),
                                "episodes_per_year": float(
                                    curve.episodes_at(point)[0] / curve.exposure_years
                                ),
                            },
                        )
                    )

    # end_to_end_loco: the held-out unit was never in the model, the pooled
    # standardiser, the penalty selection or the threshold. Seasonal naive is a
    # lookup, so withholding a unit from "fitting" withholds nothing and its
    # end-to-end test would be its threshold test under another name.
    horizon_index = {
        horizon: admitted["horizon_days"].to_numpy() == horizon for horizon in horizons
    }
    for horizon in horizons:
        rows = admitted.loc[horizon_index[horizon]]
        block = loco_matrix[horizon_index[horizon]]
        for form in DETECTOR_FORMS:
            for column, held_out in enumerate(units):
                scoped = rows.assign(loco_prediction=block[:, column])
                curves = curves_by_unit(
                    scoped, spec, form, prediction_column="loco_prediction"
                )
                retained = [curves[unit] for unit in units if unit != held_out]
                solution = calibrate_threshold(
                    retained, spec, candidates=candidate_thresholds(list(curves.values()))
                )
                point = np.array([solution.threshold])
                curve = curves[held_out]
                calibration_rows.append(
                    _solution_record(
                        solution,
                        model=RIDGE_MODEL,
                        horizon=horizon,
                        form=form,
                        scope="end_to_end_loco",
                        held_out_unit=held_out,
                        held_out={
                            "episodes": int(curve.episodes_at(point)[0]),
                            "censored_episodes": int(curve.censored_at(point)[0]),
                            "exposure_years": float(curve.exposure_years),
                            "episodes_per_year": float(
                                curve.episodes_at(point)[0] / curve.exposure_years
                            ),
                        },
                    )
                )

    calibration = pd.DataFrame.from_records(calibration_rows).sort_values(
        ["model", "horizon_days", "form", "scope", "held_out_unit"], kind="mergesort"
    ).reset_index(drop=True)
    false_alarms = pd.DataFrame.from_records(false_alarm_rows).sort_values(
        ["model", "horizon_days", "form", "unit"], kind="mergesort"
    ).reset_index(drop=True)

    outputs = spec["detector"]["outputs"]
    calibration_path = config.ROOT / outputs["calibration"]
    false_alarms_path = config.ROOT / outputs["false_alarms"]
    manifest_path = config.ROOT / outputs["manifest"]
    calibration_path.parent.mkdir(parents=True, exist_ok=True)
    calibration.to_csv(calibration_path, index=False)
    false_alarms.to_csv(false_alarms_path, index=False)

    hormuz = spec["population"]["hormuz_unit"]
    calibration_end = pd.Timestamp(spec["detector"]["eligibility"]["calibration_end"])
    degenerate = calibration.loc[
        calibration["scope"].eq("operational") & calibration["literal_tie_rule_degenerate"]
    ]
    assertions = {
        "hormuz_entered_calibration": hormuz in set(admitted["unit"]),
        "masked_unit_days_entered_calibration": bool(admitted.get("event_masked", pd.Series(dtype=bool)).any()),
        "selection_year_entered_calibration": bool(
            admitted["residual_role"].eq("hyperparameter_validation_oof").any()
        ),
        "residuals_reach_past_calibration_end": bool(
            pd.to_datetime(admitted["target_timestamp"]).max() > calibration_end
        ),
        "per_unit_thresholds_used": False,
        "august_state_read": state != "july",
        "calibration_population_is_27_non_hormuz": len(set(admitted["unit"]))
        == int(spec["population"]["expected_development_units"]),
        "both_frozen_forms_calibrated": set(calibration["form"]) == set(DETECTOR_FORMS),
        "threshold_loco_and_end_to_end_loco_reported_separately": {
            "threshold_loco",
            "end_to_end_loco",
        }.issubset(set(calibration["scope"])),
        # The frozen object is the scaling algorithm, so the seal is that every
        # fold refitted through its own fit_end -- not that the resulting number
        # moved. It does not move for the low-count units: `n_tanker` is an
        # integer count, so a small unit's MAD is an integer and its scale is a
        # small integer multiple of 1.4826 that a longer history does not
        # change. The second assertion keeps the first from passing on a
        # constant-by-construction no-op.
        "context_scales_fitted_through_each_folds_fit_end": context_end_matches,
        "context_scale_varies_across_folds_for_some_unit": any(
            len(set(drift[unit][str(horizon)])) > 1 for unit in units for horizon in horizons
        ),
        "scale_invariance_verified": invariance_holds,
        "a2_gate_reproduced": True,
        "event_mask_applied": len(excluded) > 0,
    }

    manifest = {
        "schema": "hormuz_detector_calibration_manifest/1",
        "phase": "A3",
        "status": "PENDING",
        "script": "scripts/run_hormuz_detection.py",
        "command": "run_hormuz_detection.py --phase calibrate",
        "run_utc": pd.Timestamp.utcnow().isoformat(),
        "git": {
            "commit": _git("rev-parse", "HEAD"),
            "branch": _git("branch", "--show-current"),
            "dirty": bool(_git("status", "--porcelain")),
        },
        "config": {"path": "config/hormuz_detection.yaml", "sha256": spec_sha},
        "detector_design_version": int(spec["detector"]["design_version"]),
        "plan": {"version": spec["plan"]["version"], "sha256": spec["plan"]["sha256"]},
        "a2_gate": {
            "manifest": spec["model"]["outputs"]["manifest"],
            "status": a2["status"],
            "config_sha256": a2["config"]["sha256"],
            "git_commit": a2["git"]["commit"],
            "git_dirty": a2["git"]["dirty"],
            "scores_sha256": a2["outputs"]["scores_sha256"],
            "predictions_sha256": a2["outputs"]["predictions_sha256"],
            "selected_alpha_by_horizon": a2["estimators"]["selected_alpha_by_horizon"],
        },
        "inputs": {
            "measurement_state_used": state,
            "august_state_read": False,
            "event_mask_sha256": mask.sha256,
            "event_mask_sources": dict(mask.source_sha256),
            "panel_days": int(len(panel)),
            "panel_units": int(panel.shape[1]),
            "hormuz_handling": {
                "present_in_loaded_panel": hormuz in panel.columns,
                "entered_calibration": hormuz in set(admitted["unit"]),
                "claim": (
                    "The Hormuz column is loaded with the panel. No Hormuz row is "
                    "materialised into a residual task, calibrated on, or scored here."
                ),
            },
        },
        "geometry": {
            "folds": len(folds),
            "horizons": horizons,
            "residual_rows_produced": int(len(residuals)),
            "residual_rows_admitted": int(len(admitted)),
            "residual_rows_event_masked": int(len(excluded)),
            "eligible_residual_roles": sorted(set(admitted["residual_role"])),
            "calibration_window": {
                "start": str(pd.to_datetime(admitted["target_timestamp"]).min().date()),
                "end": str(pd.to_datetime(admitted["target_timestamp"]).max().date()),
            },
            "residuals_digest": digest_frame(
                admitted.loc[:, ["unit", "horizon_days", "target_timestamp", "fold_id"]]
            ),
        },
        "estimators": {
            "models_calibrated": sorted(model_columns),
            "ridge_alpha_by_horizon": {str(k): v for k, v in sorted(selected_alpha.items())},
            "loco_alpha_by_horizon": {
                str(horizon): dict(sorted(loco_alphas[horizon].items()))
                for horizon in horizons
            },
            "end_to_end_loco_models": [RIDGE_MODEL],
            "end_to_end_loco_exclusion_note": (
                "Seasonal naive is a lookup, not a fit, so withholding a unit from "
                "model fitting withholds nothing from it. Its end-to-end LOCO would "
                "be its threshold LOCO under another name and is not reported twice."
            ),
        },
        "context_scale_drift": {
            "rule": spec["detector"]["evaluation"]["context_scale_timing"]["rule"],
            "fitted_through_each_folds_fit_end": context_end_matches,
            "quantised_units": {
                "note": (
                    "n_tanker is an integer count, so a low-volume unit's median "
                    "absolute deviation is an integer and its context scale is a small "
                    "integer multiple of 1.4826 that a longer history does not move. "
                    "For these units the scale-invariant score is the raw error divided "
                    "by a coarse constant, so the two detector forms are closer to each "
                    "other there than the design assumes."
                ),
                "constant_across_all_folds": sorted(
                    {
                        unit
                        for unit in units
                        for horizon in horizons
                        if len(set(drift[unit][str(horizon)])) == 1
                    }
                ),
            },
            "summary": {
                unit: {
                    str(horizon): {
                        "first": drift[unit][str(horizon)][0],
                        "last": drift[unit][str(horizon)][-1],
                        "min": min(drift[unit][str(horizon)]),
                        "max": max(drift[unit][str(horizon)]),
                        "max_over_min": (
                            max(drift[unit][str(horizon)]) / min(drift[unit][str(horizon)])
                            if min(drift[unit][str(horizon)]) > 0
                            else float("inf")
                        ),
                    }
                    for horizon in horizons
                }
                for unit in units
            },
            "trajectories": drift,
        },
        "results": {
            "operational_thresholds": [
                record for record in calibration_rows if record["scope"] == "operational"
            ],
            "loco_summary": {
                scope: {
                    "n_rows": int(calibration["scope"].eq(scope).sum()),
                    "worst_held_out_episodes_per_year": float(
                        pd.to_numeric(
                            calibration.loc[
                                calibration["scope"].eq(scope), "held_out_episodes_per_year"
                            ],
                            errors="coerce",
                        ).max()
                    ),
                    "mean_held_out_episodes_per_year": float(
                        pd.to_numeric(
                            calibration.loc[
                                calibration["scope"].eq(scope), "held_out_episodes_per_year"
                            ],
                            errors="coerce",
                        ).mean()
                    ),
                }
                for scope in ("threshold_loco", "end_to_end_loco")
            },
        },
        "sealing_assertions": assertions,
        # Nothing is outstanding: the one item this phase raised was ratified by
        # Mher on 2026-08-28 and is recorded below rather than left open.
        "ratification_required": [],
        "ratifications": [
            {
                "item": "discrete_ties.rule",
                "ratified_by": "Mher",
                "ratified_on": "2026-08-28",
                "design_version": int(spec["detector"]["design_version"]),
                "superseded_rule": (
                    "smallest_threshold_whose_achieved_rate_is_at_or_below_target"
                ),
                "ratified_rule": spec["detector"]["discrete_ties"]["rule"],
                "why_superseded": (
                    "The episode rate is not monotone in the threshold, and at the "
                    "bottom of the range every day exceeds, so a unit's record "
                    "collapses into one unending episode per segment and the rate "
                    "falls back below target. The literal reading therefore selected "
                    "a threshold firing on almost every unit-day."
                ),
                "operational_rows_where_the_readings_differ": int(len(degenerate)),
                "literal_rule_exceedance_share": sorted(
                    set(degenerate["literal_tie_rule_exceedance_share"].round(6))
                ),
                "unchanged_by_the_amendment": [
                    "strict greater-than exceedance",
                    "the scaling algorithm, which Mher did not authorise changing",
                ],
            },
            {
                "item": "context_scale_quantisation",
                "ratified_by": "Mher",
                "ratified_on": "2026-08-28",
                "disposition": "accepted as a documented limitation, not corrected",
                "scaling_algorithm_change_authorised": False,
            },
        ],
        "outputs": {
            "calibration": outputs["calibration"],
            "false_alarms": outputs["false_alarms"],
            "manifest": outputs["manifest"],
            "calibration_sha256": sha256_file(calibration_path),
            "false_alarms_sha256": sha256_file(false_alarms_path),
        },
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "pandas": pd.__version__,
            "numpy": np.__version__,
        },
        "limitations": [
            "The ridge penalty was selected on 2024, which is after the 2021-2023 "
            "development_oof residual window. Those residuals are out-of-fold with "
            "respect to model fitting but not with respect to penalty selection. A2 "
            "measured that selection to be near-insensitive (at most 0.000391 MASE, "
            "about 0.05%), which bounds the practical size of this, but the structural "
            "point stands and the frozen roles admit the window regardless.",
            "The 2024 selection year carries no admissible residual, so it acts as a "
            "segment boundary: no episode spans it. That follows the frozen masked-gap "
            "rule, but the rule was written about event masks rather than the withheld "
            "selection year.",
            "Censored episodes are counted in the episode rate and reported separately. "
            "An episode that began is an episode; only its duration is censored.",
            "These are false-alarm rates on development units with no disruption label. "
            "Nothing here measures detection power, which needs a positive control.",
            "The event mask removes exposed unit-days from calibration; it does not "
            "make the remaining days a clean null, only a pre-declared one.",
            "For the low-count units the context scale is an integer multiple of "
            "1.4826 and does not move across folds, because the MAD of an integer "
            "count series is an integer. The refit is real but its estimate is "
            "quantised there, which the frozen design did not anticipate and which "
            "narrows the intended contrast between the two detector forms.",
        ],
        "claims_not_authorised": [
            "Any statement about Hormuz: no Hormuz row is calibrated on or scored here.",
            "Any detection-power, sensitivity or true-positive claim; this phase "
            "measures false alarms on unlabelled development units only.",
            "Any causal reading of an exceedance or an episode.",
            "That a threshold transferring across development units will transfer to "
            "Hormuz; that is the A4 question and it is not answered here.",
            "Any cross-measurement-state statement: August is not read at A3.",
        ],
    }
    manifest["status"] = _derive_calibration_status(manifest)
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True, default=str))
    return manifest


def _derive_calibration_status(manifest: Mapping[str, object]) -> str:
    """Derive PASS/FAIL from the A3 sealing evidence rather than asserting it."""
    failures: list[str] = []
    assertions = dict(manifest["sealing_assertions"])
    for name, value in assertions.items():
        must_be_false = name in A3_MUST_BE_FALSE
        if must_be_false and bool(value):
            failures.append(f"sealing_assertion_must_be_false:{name}")
        elif not must_be_false and not bool(value):
            failures.append(f"sealing_assertion:{name}")
    missing = A3_MUST_BE_FALSE.difference(assertions)
    failures.extend(f"missing_assertion:{name}" for name in sorted(missing))
    manifest["status_failures"] = sorted(failures)
    return "PASS" if not failures else "FAIL"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=["audit", "validate", "calibrate"], required=True)
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()

    if args.phase == "audit":
        if not args.check_only:
            raise SystemExit("Phase A1 permits only --phase audit --check-only")
        audit = build_audit()
        print(f"A1 AUDIT CHECK-ONLY {audit['status']}")
        print(json.dumps(audit, indent=2, sort_keys=True))
        print("STOP AND REPORT. No model was fitted and no Hormuz outcome was printed.")
        if audit["status"] != "PASS":
            raise SystemExit(
                "A1 audit FAILED; the phase is not freezable. Failing evidence: "
                + ", ".join(audit["status_failures"])
            )
        return

    if args.phase == "calibrate":
        if args.check_only:
            raise SystemExit("--phase calibrate fits estimators and cannot run check-only")
        manifest = run_calibration()
        print(f"A3 CALIBRATE {manifest['status']}")
        print(f"git branch/HEAD : {manifest['git']['branch']} / {manifest['git']['commit']}")
        print(f"config sha256   : {manifest['config']['sha256']}")
        print(f"A2 gate         : {manifest['a2_gate']['status']} at {manifest['a2_gate']['git_commit'][:10]}, dirty={manifest['a2_gate']['git_dirty']}")
        print(
            "residual rows   : "
            f"{manifest['geometry']['residual_rows_admitted']} admitted, "
            f"{manifest['geometry']['residual_rows_event_masked']} event-masked, "
            f"over {manifest['geometry']['folds']} folds"
        )
        print(
            "window          : "
            f"{manifest['geometry']['calibration_window']['start']} to "
            f"{manifest['geometry']['calibration_window']['end']}"
        )
        print()
        print("Operational thresholds (calibrated on all 27 development units):")
        operational = pd.DataFrame(manifest["results"]["operational_thresholds"])
        print(
            operational.loc[
                :,
                [
                    "model",
                    "horizon_days",
                    "form",
                    "threshold",
                    "achieved_episodes_per_year",
                    "exceedance_share_of_unit_days",
                    "literal_tie_rule_threshold",
                    "literal_tie_rule_exceedance_share",
                ],
            ].to_string(index=False)
        )
        print()
        print("Leave-one-chokepoint-out behaviour:")
        print(json.dumps(manifest["results"]["loco_summary"], indent=2, sort_keys=True))
        print()
        print("Sealing assertions:")
        print(json.dumps(manifest["sealing_assertions"], indent=2, sort_keys=True))
        print()
        if manifest["ratification_required"]:
            print("=" * 72)
            print("RATIFICATION REQUIRED BEFORE A3 CAN BE ACCEPTED")
            print("=" * 72)
            for item in manifest["ratification_required"]:
                print(f"- {item['item']}")
                print(f"  {item['detail']}")
                print(f"  affected operational rows: {item['affected_rows']}")
        else:
            print(
                f"No outstanding ratification item. Detector design version "
                f"{manifest['detector_design_version']}, ratified by Mher on 2026-08-28: "
                + ", ".join(str(item["item"]) for item in manifest["ratifications"])
                + "."
            )
        print()
        print(f"wrote {manifest['outputs']['calibration']}")
        print(f"wrote {manifest['outputs']['false_alarms']}")
        print(f"wrote {manifest['outputs']['manifest']}")
        print(
            "STOP AND REPORT. No Hormuz row was calibrated on or scored; that is A4, "
            "and A4 must not start until Mher accepts this calibration."
        )
        if manifest["status"] != "PASS":
            raise SystemExit(
                "A3 calibration FAILED its sealing assertions: "
                + ", ".join(manifest["status_failures"])
            )
        return

    if args.check_only:
        raise SystemExit("--phase validate fits estimators and cannot run check-only")
    manifest = run_validation()
    print(f"A2 VALIDATE {manifest['status']}")
    print(f"git branch/HEAD : {manifest['git']['branch']} / {manifest['git']['commit']}")
    print(f"config sha256   : {manifest['config']['sha256']}")
    print(f"measurement st. : {manifest['inputs']['measurement_state_used']}")
    print(
        "rows            : "
        f"{manifest['geometry']['development_rows']} development, "
        f"{manifest['geometry']['validation_rows']} validation"
    )
    print(f"selected alpha  : {manifest['estimators']['selected_alpha_by_horizon']}")
    print()
    print("Mean 2024 scores over the 27 development units:")
    aggregate = pd.DataFrame(manifest["results"]["aggregate"])
    print(aggregate.to_string(index=False))
    print()
    print("Provisional interval behaviour (in-sample residual widths):")
    print(pd.DataFrame(manifest["results"]["intervals"]).to_string(index=False))
    print()
    print("Sealing assertions:")
    print(json.dumps(manifest["sealing_assertions"], indent=2, sort_keys=True))
    print()
    print(f"wrote {manifest['outputs']['scores']}")
    print(f"wrote {manifest['outputs']['predictions']}")
    print(f"wrote {manifest['outputs']['manifest']}")
    print("STOP AND REPORT. No Hormuz row was fitted or scored; the detector is A3.")
    if manifest["status"] != "PASS":
        raise SystemExit(
            "A2 validation FAILED its sealing assertions: "
            + ", ".join(manifest["status_failures"])
        )


if __name__ == "__main__":
    main()
