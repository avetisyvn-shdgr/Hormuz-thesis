"""Hormuz cross-chokepoint detection runner.

``--phase audit --check-only`` is the A1 seal check: it reads configuration and
computes file hashes only, never touching a PortWatch outcome row.

``--phase validate`` is A2: it fits the pooled global model and the declared
baselines on the 27 non-Hormuz development units, selects the ridge penalty on
the frozen 2024 tasks alone, and writes the validation artefacts.  It fits no
detector.

The Hormuz column is present in the loaded 28-unit panel but is never
materialised into a task, fitted, selected on, or scored.  That, and not "no
Hormuz row is read", is the safety claim this phase supports.
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

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=["audit", "validate"], required=True)
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
