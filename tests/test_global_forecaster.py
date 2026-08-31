from __future__ import annotations

from copy import deepcopy

import numpy as np
import pandas as pd
import pytest

from hormuz_throughput.global_forecaster import (
    PHASE_LADDER,
    LeakageError,
    LocalARModel,
    RidgeGlobalModel,
    apply_context_normalisation,
    classify_feature_transforms,
    denormalise,
    load_development_panel,
    mase_denominators,
    pinball_loss,
    residual_quantile_offsets,
    score_predictions,
    seasonal_naive_predictions,
    validate_model_spec,
    MeasurementStateError,
    TrainingOnlyStandardizer,
    assert_task_access,
    build_development_geometry,
    build_hormuz_scoring_geometry,
    build_rolling_residual_geometry,
    build_task_geometry,
    development_units,
    feature_columns,
    load_detection_spec,
    materialize_task_features,
    rolling_origin_folds,
    task_geometry_hash,
    validate_task_table,
)


@pytest.fixture(scope="module")
def spec() -> dict:
    loaded, _ = load_detection_spec()
    return loaded


def _panel() -> pd.DataFrame:
    index = pd.date_range("2019-01-01", "2026-07-07", freq="D")
    trend = np.arange(len(index), dtype="float64")
    return pd.DataFrame(
        {
            "dover_strait": 20.0 + trend * 0.01 + np.sin(trend / 7.0),
            "suez_canal": 15.0 + trend * 0.02 + np.cos(trend / 11.0),
            "strait_of_hormuz": 40.0 + trend * 0.03 + np.sin(trend / 13.0),
        },
        index=index,
    )


def _training_tasks(spec: dict) -> pd.DataFrame:
    geometry = build_task_geometry(
        pd.date_range("2023-06-01", "2023-06-05", freq="D"),
        ["dover_strait", "suez_canal"],
        spec["tasks"]["horizons_days"],
        measurement_state="july",
        task_role="development_fit",
        seed=spec["tasks"]["seed"],
    )
    return materialize_task_features(_panel(), geometry, spec)


def test_spec_freezes_leave_hormuz_out_a1_contract(spec: dict):
    assert spec["phase"] in PHASE_LADDER
    assert spec["status"] == PHASE_LADDER[spec["phase"]]["status"]
    assert (
        spec["detector_contract"]["fitting_status"]
        == PHASE_LADDER[spec["phase"]]["fitting_status"]
    )
    assert spec["detector_contract"]["calibration_status"] == "deferred_to_A3"
    assert tuple(spec["tasks"]["horizons_days"]) == (1, 7, 30)
    assert len(development_units(spec)) == 27
    assert spec["population"]["hormuz_unit"] not in development_units(spec)
    assert spec["features"]["identity_embedding"]["enabled"] is False
    assert spec["features"]["network_factors"]["enabled"] is False


def test_direct_geometry_is_chronological_leave_hormuz_out_and_deterministic(spec: dict):
    kwargs = dict(
        target_dates=pd.date_range("2023-06-01", "2023-06-03", freq="D"),
        units=["suez_canal", "dover_strait"],
        horizons_days=[30, 1, 7],
        measurement_state="july",
        task_role="development_fit",
        seed=spec["tasks"]["seed"],
    )
    first = build_task_geometry(**kwargs)
    second = build_task_geometry(**kwargs)
    validate_task_table(first, spec)
    assert set(first["horizon_days"]) == {1, 7, 30}
    assert "strait_of_hormuz" not in set(first["unit"])
    assert (
        pd.to_datetime(first["target_timestamp"])
        > pd.to_datetime(first["feature_timestamp"])
    ).all()
    assert task_geometry_hash(first) == task_geometry_hash(second)


def test_feature_materialization_cannot_see_after_feature_timestamp(spec: dict):
    geometry = build_task_geometry(
        ["2023-06-30"],
        ["dover_strait"],
        [7],
        measurement_state="july",
        task_role="development_fit",
        seed=spec["tasks"]["seed"],
    )
    panel = _panel()
    before = materialize_task_features(
        panel, geometry, spec, include_targets=False
    )
    changed = panel.copy()
    origin = pd.Timestamp(geometry.iloc[0]["feature_timestamp"])
    changed.loc[changed.index > origin, "dover_strait"] = 1_000_000.0
    after = materialize_task_features(
        changed, geometry, spec, include_targets=False
    )
    pd.testing.assert_frame_equal(
        before.loc[:, feature_columns(spec)], after.loc[:, feature_columns(spec)]
    )
    assert before.iloc[0]["max_feature_source_timestamp"] == origin
    assert before.iloc[0]["target_timestamp"] > origin


def test_shuffling_hormuz_scoring_outcomes_changes_no_development_parameter(spec: dict):
    tasks = _training_tasks(spec)
    panel = _panel()
    shuffled = panel.copy()
    post = shuffled.index >= pd.Timestamp("2025-12-01")
    shuffled.loc[post, "strait_of_hormuz"] = (
        shuffled.loc[post, "strait_of_hormuz"].sample(frac=1.0, random_state=99).to_numpy()
    )
    geometry = tasks.loc[:, [
        "measurement_state",
        "task_role",
        "fold_id",
        "unit",
        "horizon_days",
        "feature_timestamp",
        "target_timestamp",
        "seed",
    ]]
    rematerialized = materialize_task_features(shuffled, geometry, spec)
    pd.testing.assert_frame_equal(
        tasks.loc[:, feature_columns(spec) + ("y_target",)],
        rematerialized.loc[:, feature_columns(spec) + ("y_target",)],
    )
    first = TrainingOnlyStandardizer.fit(tasks, feature_columns(spec), spec)
    second = TrainingOnlyStandardizer.fit(rematerialized, feature_columns(spec), spec)
    assert first.digest() == second.digest()


@pytest.mark.parametrize(
    "operation",
    [
        "fitting",
        "scaling",
        "feature_selection",
        "detector_calibration",
        "hyperparameter_selection",
    ],
)
def test_hormuz_post_onset_task_deliberately_fails_every_restricted_access(
    spec: dict, operation: str
):
    malicious = build_task_geometry(
        ["2026-03-01"],
        ["strait_of_hormuz"],
        [1],
        measurement_state="july",
        task_role="scoring_only",
        seed=spec["tasks"]["seed"],
    )
    if operation == "detector_calibration":
        malicious["calibration_eligible"] = True
        malicious["event_masked"] = False
    with pytest.raises(LeakageError, match="Hormuz observations are scoring-only"):
        assert_task_access(malicious, operation, spec)


def test_scaler_refuses_nontraining_rows_and_cross_state_transport(spec: dict):
    training = _training_tasks(spec)
    scaler = TrainingOnlyStandardizer.fit(training, feature_columns(spec), spec)
    validation = build_development_geometry(spec, "july")
    validation = validation.loc[
        validation["task_role"].eq("hyperparameter_validation")
    ].head(3)
    with pytest.raises(LeakageError, match="non-training task roles"):
        TrainingOnlyStandardizer.fit(validation, feature_columns(spec), spec)

    august = training.copy()
    august["measurement_state"] = "august"
    with pytest.raises(MeasurementStateError, match="cannot silently transform"):
        scaler.transform(august, spec)


def test_july_and_august_tasks_cannot_be_joined_for_fitting(spec: dict):
    july = _training_tasks(spec).head(1)
    august = july.copy()
    august["measurement_state"] = "august"
    with pytest.raises(MeasurementStateError, match="processed separately"):
        assert_task_access(pd.concat([july, august], ignore_index=True), "fitting", spec)


def test_target_timestamp_equal_to_feature_timestamp_is_rejected(spec: dict):
    tasks = _training_tasks(spec).head(1).copy()
    tasks["target_timestamp"] = tasks["feature_timestamp"]
    with pytest.raises(LeakageError, match="strictly after"):
        validate_task_table(tasks, spec)


@pytest.mark.parametrize("operation", ["fitting", "scaling"])
def test_spoofed_development_role_after_frozen_period_is_rejected(
    spec: dict, operation: str
):
    malicious = build_task_geometry(
        ["2025-01-01"],
        ["dover_strait"],
        [1],
        measurement_state="july",
        task_role="development_fit",
        seed=spec["tasks"]["seed"],
    )
    with pytest.raises(LeakageError, match="development-fit targets after"):
        assert_task_access(malicious, operation, spec)


def test_frozen_split_boundaries_and_hormuz_scoring_role(spec: dict):
    geometry = build_development_geometry(spec, "july")
    development = geometry.loc[geometry["task_role"].eq("development_fit")]
    validation = geometry.loc[
        geometry["task_role"].eq("hyperparameter_validation")
    ]
    assert development["target_timestamp"].max() == pd.Timestamp("2023-12-31")
    assert validation["target_timestamp"].min() == pd.Timestamp("2024-01-01")
    assert validation["target_timestamp"].max() == pd.Timestamp("2024-12-31")
    assert validation.groupby("horizon_days")["target_timestamp"].min().to_dict() == {
        1: pd.Timestamp("2024-01-01"),
        7: pd.Timestamp("2024-01-07"),
        30: pd.Timestamp("2024-01-30"),
    }
    assert (
        pd.to_datetime(validation["fit_end"])
        <= pd.to_datetime(validation["feature_timestamp"])
    ).all()
    assert "strait_of_hormuz" not in set(geometry["unit"])

    scoring = build_hormuz_scoring_geometry(spec, "july")
    assert set(scoring["task_role"]) == {"scoring_only"}
    assert scoring["target_timestamp"].min() == pd.Timestamp("2025-12-01")
    assert scoring["target_timestamp"].max() == pd.Timestamp("2026-07-07")


def test_rolling_origin_geometry_is_frozen_and_seed_deterministic(spec: dict):
    folds = rolling_origin_folds(spec)
    assert len(folds) == 60
    assert folds[0].fit_start == pd.Timestamp("2019-01-01")
    assert folds[0].fit_end == pd.Timestamp("2020-12-31")
    assert folds[0].score_start == pd.Timestamp("2021-01-01")
    assert folds[-1].score_end == pd.Timestamp("2025-11-30")
    assert all(fold.fit_end < fold.score_start for fold in folds)

    compact = deepcopy(spec)
    compact["rolling_origin"]["last_score_end"] = "2021-02-15"
    compact["rolling_origin"]["residual_roles"] = {
        "development_oof": {
            "start": "2021-01-01",
            "end": "2021-02-15",
            "detector_calibration_eligible": True,
        }
    }
    first = build_rolling_residual_geometry(compact, "july")
    second = build_rolling_residual_geometry(compact, "july")
    assert task_geometry_hash(first) == task_geometry_hash(second)
    assert first["seed"].nunique() == 1
    assert int(first["seed"].iloc[0]) == 20260612
    assert (
        pd.to_datetime(first["fit_end"])
        <= pd.to_datetime(first["feature_timestamp"])
    ).all()
    first_fold = first.loc[first["fold_id"].eq("fold_001")]
    assert first_fold.groupby("horizon_days")["fit_end"].first().to_dict() == {
        1: pd.Timestamp("2020-12-31"),
        7: pd.Timestamp("2020-12-25"),
        30: pd.Timestamp("2020-12-02"),
    }


def test_non_frozen_horizon_is_rejected(spec: dict):
    malicious = build_task_geometry(
        ["2023-06-01"],
        ["dover_strait"],
        [2],
        measurement_state="july",
        task_role="development_fit",
        seed=spec["tasks"]["seed"],
    )
    with pytest.raises(LeakageError, match="frozen 1/7/30"):
        assert_task_access(malicious, "fitting", spec)


def test_scaler_rejects_target_and_metadata_columns(spec: dict):
    training = _training_tasks(spec)
    with pytest.raises(LeakageError, match="declared A1 features"):
        TrainingOnlyStandardizer.fit(training, ["y_target"], spec)
    with pytest.raises(LeakageError, match="declared A1 features"):
        TrainingOnlyStandardizer.fit(training, ["horizon_days"], spec)


def test_scoring_task_after_frozen_end_is_rejected(spec: dict):
    malicious = build_task_geometry(
        ["2026-07-08"],
        ["strait_of_hormuz"],
        [1],
        measurement_state="july",
        task_role="scoring_only",
        seed=spec["tasks"]["seed"],
    )
    with pytest.raises(LeakageError, match="outside the frozen scoring window"):
        validate_task_table(malicious, spec)


def test_rolling_residual_fit_cutoff_and_metadata_spoofing_are_rejected(spec: dict):
    compact = deepcopy(spec)
    compact["rolling_origin"]["last_score_end"] = "2021-01-30"
    compact["rolling_origin"]["residual_roles"] = {
        "development_oof": {
            "start": "2021-01-01",
            "end": "2021-01-30",
            "detector_calibration_eligible": True,
        }
    }
    tasks = build_rolling_residual_geometry(compact, "july")
    malicious = tasks.head(1).copy()
    malicious["fit_end"] = malicious["feature_timestamp"] + pd.Timedelta(days=1)
    with pytest.raises(LeakageError, match="horizon-specific frozen geometry"):
        validate_task_table(malicious, compact)

    malicious = tasks.head(1).copy()
    malicious["residual_role"] = "hyperparameter_validation_oof"
    with pytest.raises(LeakageError, match="residual_role"):
        validate_task_table(malicious, compact)


def test_post_window_rolling_fit_is_rejected(spec: dict):
    malicious = build_task_geometry(
        ["2026-03-01"],
        ["dover_strait"],
        [1],
        measurement_state="july",
        task_role="rolling_fit",
        seed=spec["tasks"]["seed"],
        fold_id="fold_060",
        extra_columns={
            "fit_start": pd.Timestamp("2019-01-01"),
            "fit_end": pd.Timestamp("2026-03-01"),
            "score_start": pd.Timestamp("2026-03-02"),
            "score_end": pd.Timestamp("2026-03-31"),
        },
    )
    with pytest.raises(LeakageError, match="frozen geometry|frozen folds"):
        assert_task_access(malicious, "fitting", spec)


def _audit_module():
    """Load the A1 audit script as a module for status-derivation tests."""
    import importlib.util
    from pathlib import Path

    path = Path(__file__).resolve().parents[1] / "scripts" / "run_hormuz_detection.py"
    loader = importlib.util.spec_from_file_location("a1_audit_script", path)
    module = importlib.util.module_from_spec(loader)
    loader.loader.exec_module(module)
    return module


def test_audit_status_is_derived_from_evidence_not_asserted():
    """A1 must never print PASS while its own evidence says otherwise.

    Regression guard for the review finding that `status` was a literal. Every
    failure mode below must flip the audit to FAIL: a hostile check that did
    not fail, a positive sealing assertion that is False, an assertion that
    must stay False turning True, and a required assertion going missing.
    """
    module = _audit_module()
    audit = {
        "leakage_checks": [{"check": "example", "passed": True}],
        "sealing_assertions": {
            "hormuz_excluded_from_training": True,
            "post_event_outcomes_read": False,
            "post_event_outcomes_printed": False,
        },
    }
    assert module._derive_status(audit) == "PASS"
    assert audit["status_failures"] == []

    failing_check = deepcopy(audit)
    failing_check["leakage_checks"][0]["passed"] = False
    assert module._derive_status(failing_check) == "FAIL"
    assert failing_check["status_failures"] == ["leakage_check:example"]

    false_assertion = deepcopy(audit)
    false_assertion["sealing_assertions"]["hormuz_excluded_from_training"] = False
    assert module._derive_status(false_assertion) == "FAIL"

    read_outcomes = deepcopy(audit)
    read_outcomes["sealing_assertions"]["post_event_outcomes_read"] = True
    assert module._derive_status(read_outcomes) == "FAIL"
    assert read_outcomes["status_failures"] == [
        "sealing_assertion_must_be_false:post_event_outcomes_read"
    ]

    dropped = deepcopy(audit)
    del dropped["sealing_assertions"]["post_event_outcomes_printed"]
    assert module._derive_status(dropped) == "FAIL"
    assert dropped["status_failures"] == ["missing_assertion:post_event_outcomes_printed"]


def test_full_frozen_rolling_geometry_never_fits_past_a_forecast_origin(spec: dict):
    """The origin-leakage invariant must hold on the whole frozen geometry.

    The per-fold test above runs on a shortened spec. This one exercises every
    fold, horizon, and measurement state, so a regression that only surfaces in
    later folds cannot pass unnoticed.
    """
    for state in ("july", "august"):
        tasks = build_rolling_residual_geometry(spec, state)
        fit_end = pd.to_datetime(tasks["fit_end"])
        origin = pd.to_datetime(tasks["feature_timestamp"])
        assert (fit_end <= origin).all()
        assert (origin < pd.to_datetime(tasks["target_timestamp"])).all()

        validation = build_development_geometry(spec, state)
        validation = validation.loc[
            validation["task_role"].eq("hyperparameter_validation")
        ]
        assert (
            pd.to_datetime(validation["fit_end"])
            <= pd.to_datetime(validation["feature_timestamp"])
        ).all()




def _a2_tasks(spec: dict, *, horizon: int = 7, role: str = "development_fit") -> pd.DataFrame:
    """A wide, well-conditioned development task table for estimator tests."""
    extras = {}
    if role == "hyperparameter_validation":
        extras = {
            "fit_start": pd.Timestamp(spec["dates"]["full_start"]),
            "fit_end": pd.Timestamp(spec["dates"]["development_end"]),
        }
        dates = pd.date_range("2024-02-01", "2024-08-31", freq="D")
    else:
        dates = pd.date_range("2022-01-01", "2023-12-31", freq="D")
    geometry = build_task_geometry(
        dates,
        ["dover_strait", "suez_canal"],
        [horizon],
        measurement_state="july",
        task_role=role,
        seed=spec["tasks"]["seed"],
        extra_columns=extras,
    )
    return materialize_task_features(_panel(), geometry, spec)


def _a2_scales(spec: dict, units=("dover_strait", "suez_canal")) -> dict:
    from hormuz_throughput.disruption_detector import fit_context_scale

    panel = _panel()
    context = spec["model"]["context_normalisation"]
    return {
        unit: fit_context_scale(
            panel[unit],
            spec,
            measurement_state="july",
            context_start=context["context_start"],
            context_end=context["context_end"],
        )
        for unit in units
    }


def test_a2_model_spec_is_frozen_and_refuses_drift(spec: dict):
    validate_model_spec(spec)
    assert spec["model"]["development_measurement_state"] == "july"
    assert spec["model"]["tsfm_benchmarks"]["included"] is False
    assert spec["model"]["scoring"]["winner_score_prohibited"] is True

    beyond = deepcopy(spec)
    beyond["model"]["context_normalisation"]["context_end"] = "2024-06-30"
    with pytest.raises(LeakageError):
        validate_model_spec(beyond)

    reselected = deepcopy(spec)
    reselected["model"]["global_model"]["selection"]["period"] = "development"
    with pytest.raises(LeakageError):
        validate_model_spec(reselected)

    smuggled = deepcopy(spec)
    smuggled["model"]["tsfm_benchmarks"]["included"] = True
    with pytest.raises(ValueError):
        validate_model_spec(smuggled)

    dependency = deepcopy(spec)
    dependency["model"]["global_model"]["dependency_status"] = "requires_scikit_learn"
    with pytest.raises(ValueError):
        validate_model_spec(dependency)

    invented = deepcopy(spec)
    invented["model"]["scoring"]["winner_score_prohibited"] = False
    with pytest.raises(ValueError):
        validate_model_spec(invented)


def test_feature_transform_classification_partitions_the_frozen_features(spec: dict):
    kinds = classify_feature_transforms(spec)
    assert set(kinds) == set(feature_columns(spec))
    assert kinds["lag_1"] == "level"
    assert kinds["rolling_mean_28"] == "level"
    assert kinds["rolling_median_56"] == "level"
    assert kinds["rolling_std_7"] == "dispersion"
    for field in spec["features"]["calendar"]["fields"]:
        assert kinds[field] == "untransformed"


def test_context_normalisation_moves_levels_and_dispersions_differently(spec: dict):
    tasks = _a2_tasks(spec)
    scales = _a2_scales(spec)
    normalised = apply_context_normalisation(tasks, scales, spec)

    row = 0
    unit = tasks["unit"].iloc[row]
    centre = float(scales[unit].center)
    spread = float(scales[unit].scale)
    assert normalised["lag_1"].iloc[row] == pytest.approx(
        (tasks["lag_1"].iloc[row] - centre) / spread
    )
    assert normalised["rolling_std_7"].iloc[row] == pytest.approx(
        tasks["rolling_std_7"].iloc[row] / spread
    )
    assert normalised["target_day_of_week"].iloc[row] == tasks["target_day_of_week"].iloc[row]
    assert normalised["z_target"].iloc[row] == pytest.approx(
        (tasks["y_target"].iloc[row] - centre) / spread
    )


def test_denormalise_round_trips_the_context_transform(spec: dict):
    tasks = _a2_tasks(spec)
    scales = _a2_scales(spec)
    normalised = apply_context_normalisation(tasks, scales, spec)
    recovered = denormalise(
        normalised["z_target"].to_numpy(), normalised["unit"], scales
    )
    np.testing.assert_allclose(recovered, tasks["y_target"].to_numpy(), rtol=1e-12)


def test_ridge_recovers_a_known_linear_signal_and_shrinks_with_alpha(spec: dict):
    """On a well-conditioned design the solver must return the true weights.

    The real 27-unit design has a condition number near 30, but the smooth
    synthetic panel is numerically singular, so coefficients are only
    identifiable once the features are made independent.
    """
    tasks = _a2_tasks(spec)
    scales = _a2_scales(spec)
    normalised = apply_context_normalisation(tasks, scales, spec)
    columns = list(feature_columns(spec))

    generator = np.random.default_rng(int(spec["tasks"]["seed"]))
    normalised.loc[:, columns] = generator.normal(size=(len(normalised), len(columns)))
    truth = np.zeros(len(columns))
    truth[columns.index("lag_1")] = 0.8
    truth[columns.index("lag_7")] = -0.3
    design = normalised.loc[:, columns].to_numpy(dtype="float64")
    normalised["z_target"] = design @ truth + 1.5

    weak = RidgeGlobalModel.fit(normalised, columns, spec, horizon_days=7, alpha=1e-6)
    np.testing.assert_allclose(np.asarray(weak.coefficients), truth, atol=1e-4)
    assert weak.intercept == pytest.approx(1.5, abs=1e-4)
    np.testing.assert_allclose(
        weak.predict(normalised), normalised["z_target"].to_numpy(), atol=1e-4
    )

    strong = RidgeGlobalModel.fit(normalised, columns, spec, horizon_days=7, alpha=1e6)
    assert np.abs(np.asarray(strong.coefficients)).sum() < np.abs(
        np.asarray(weak.coefficients)
    ).sum()


def test_ridge_stays_finite_on_a_rank_deficient_design(spec: dict):
    """A collinear design must not blow the closed-form solution up."""
    tasks = _a2_tasks(spec)
    scales = _a2_scales(spec)
    normalised = apply_context_normalisation(tasks, scales, spec)
    columns = list(feature_columns(spec))
    normalised.loc[:, "lag_14"] = normalised.loc[:, "lag_7"].to_numpy()
    model = RidgeGlobalModel.fit(normalised, columns, spec, horizon_days=7, alpha=1.0)
    assert np.isfinite(np.asarray(model.coefficients)).all()
    assert np.isfinite(model.predict(normalised)).all()


def test_ridge_fit_is_deterministic(spec: dict):
    tasks = _a2_tasks(spec)
    scales = _a2_scales(spec)
    normalised = apply_context_normalisation(tasks, scales, spec)
    columns = feature_columns(spec)
    first = RidgeGlobalModel.fit(normalised, columns, spec, horizon_days=7, alpha=10.0)
    second = RidgeGlobalModel.fit(normalised, columns, spec, horizon_days=7, alpha=10.0)
    assert first.digest() == second.digest()


def test_ridge_refuses_hormuz_rows_and_mixed_horizons(spec: dict):
    tasks = _a2_tasks(spec)
    scales = _a2_scales(spec)
    normalised = apply_context_normalisation(tasks, scales, spec)
    columns = feature_columns(spec)

    contaminated = normalised.copy()
    contaminated.loc[contaminated.index[0], "unit"] = spec["population"]["hormuz_unit"]
    with pytest.raises(LeakageError):
        RidgeGlobalModel.fit(contaminated, columns, spec, horizon_days=7, alpha=1.0)

    mixed = normalised.copy()
    mixed.loc[mixed.index[0], "horizon_days"] = 1
    with pytest.raises(ValueError):
        RidgeGlobalModel.fit(mixed, columns, spec, horizon_days=7, alpha=1.0)


def test_ridge_refuses_to_fit_on_validation_tasks(spec: dict):
    """2024 may select a hyperparameter; it may never fit a coefficient."""
    validation = _a2_tasks(spec, role="hyperparameter_validation")
    scales = _a2_scales(spec)
    normalised = apply_context_normalisation(validation, scales, spec)
    with pytest.raises(LeakageError):
        RidgeGlobalModel.fit(
            normalised, feature_columns(spec), spec, horizon_days=7, alpha=1.0
        )


def test_local_ar_refuses_hormuz_and_fits_only_its_own_unit(spec: dict):
    tasks = _a2_tasks(spec)
    scales = _a2_scales(spec)
    normalised = apply_context_normalisation(tasks, scales, spec)

    model = LocalARModel.fit(normalised, spec, unit="dover_strait", horizon_days=7)
    assert model.unit == "dover_strait"
    assert model.n_fit_rows == int(normalised["unit"].eq("dover_strait").sum())

    contaminated = normalised.copy()
    contaminated.loc[contaminated.index[0], "unit"] = spec["population"]["hormuz_unit"]
    with pytest.raises(LeakageError):
        LocalARModel.fit(contaminated, spec, unit="dover_strait", horizon_days=7)


def test_seasonal_naive_never_reads_past_its_forecast_origin(spec: dict):
    for horizon in spec["tasks"]["horizons_days"]:
        tasks = _a2_tasks(spec, horizon=int(horizon))
        targets = pd.to_datetime(tasks["target_timestamp"])
        origins = pd.to_datetime(tasks["feature_timestamp"])
        back = np.ceil(int(horizon) / 7.0)
        sources = targets - pd.to_timedelta(7 * back, unit="D")
        assert (sources <= origins).all()
        panel = _panel()
        predicted = seasonal_naive_predictions(panel, tasks)
        expected = np.array(
            [
                panel[unit].loc[source]
                for unit, source in zip(tasks["unit"], sources)
            ]
        )
        np.testing.assert_allclose(predicted, expected, rtol=1e-12)


def test_seasonal_naive_is_exact_on_a_perfectly_weekly_series(spec: dict):
    index = pd.date_range("2019-01-01", "2026-07-07", freq="D")
    weekly = pd.DataFrame(
        {
            "dover_strait": 10.0 + index.dayofweek.to_numpy(dtype="float64"),
            "suez_canal": 20.0 + index.dayofweek.to_numpy(dtype="float64"),
        },
        index=index,
    )
    geometry = build_task_geometry(
        pd.date_range("2023-01-01", "2023-03-31", freq="D"),
        ["dover_strait", "suez_canal"],
        [30],
        measurement_state="july",
        task_role="development_fit",
        seed=spec["tasks"]["seed"],
    )
    tasks = materialize_task_features(weekly, geometry, spec)
    predicted = seasonal_naive_predictions(weekly, tasks)
    np.testing.assert_allclose(predicted, tasks["y_target"].to_numpy(), rtol=1e-12)


def test_mase_denominator_ignores_the_validation_year(spec: dict):
    """Perturbing 2024 must not move a denominator defined on development."""
    panel = _panel()[["dover_strait", "suez_canal"]]
    limited = deepcopy(spec)
    limited["population"]["units"] = [
        "dover_strait",
        "suez_canal",
        spec["population"]["hormuz_unit"],
    ]
    baseline = mase_denominators(panel, limited)

    perturbed = panel.copy()
    mask = perturbed.index >= pd.Timestamp("2024-01-01")
    perturbed.loc[mask, "dover_strait"] += 500.0
    assert mase_denominators(perturbed, limited) == baseline


def test_scoring_reports_mase_as_mae_over_the_frozen_denominator(spec: dict):
    scales = _a2_scales(spec)
    frame = pd.DataFrame(
        {
            "model": ["m"] * 4,
            "horizon_days": [7] * 4,
            "unit": ["dover_strait"] * 4,
            "y_target": [10.0, 12.0, 14.0, 16.0],
            "prediction": [11.0, 11.0, 15.0, 15.0],
        }
    )
    denominators = {"dover_strait": 2.0}
    scored = score_predictions(frame, spec, denominators, scales)
    assert scored["mae"].iloc[0] == pytest.approx(1.0)
    assert scored["mase"].iloc[0] == pytest.approx(0.5)
    assert scored["scaled_mae"].iloc[0] == pytest.approx(
        1.0 / float(scales["dover_strait"].scale)
    )
    assert scored["n_scored"].iloc[0] == 4


def test_pinball_at_the_median_is_half_the_absolute_error():
    actual = np.array([1.0, 2.0, 3.0])
    predicted = np.array([2.0, 2.0, 1.0])
    assert pinball_loss(actual, predicted, 0.5) == pytest.approx(
        0.5 * np.mean(np.abs(actual - predicted))
    )


def test_residual_quantile_offsets_are_empirical_quantiles():
    residuals = np.linspace(-1.0, 1.0, 201)
    offsets = residual_quantile_offsets(residuals, [0.025, 0.5, 0.975])
    assert offsets[0.5] == pytest.approx(0.0, abs=1e-12)
    assert offsets[0.025] == pytest.approx(-0.95, abs=1e-9)
    assert offsets[0.975] == pytest.approx(0.95, abs=1e-9)


def test_context_scale_and_scaler_are_blind_to_the_validation_year(spec: dict):
    """The strongest A2 seal: 2024 cannot move anything fitted before it."""
    from hormuz_throughput.disruption_detector import fit_context_scale

    panel = _panel()
    perturbed = panel.copy()
    perturbed.loc[perturbed.index >= pd.Timestamp("2024-01-01"), :] += 999.0
    context = spec["model"]["context_normalisation"]

    for unit in ("dover_strait", "suez_canal"):
        clean = fit_context_scale(
            panel[unit],
            spec,
            measurement_state="july",
            context_start=context["context_start"],
            context_end=context["context_end"],
        )
        dirty = fit_context_scale(
            perturbed[unit],
            spec,
            measurement_state="july",
            context_start=context["context_start"],
            context_end=context["context_end"],
        )
        assert clean.digest() == dirty.digest()

    tasks = _a2_tasks(spec)
    scales = _a2_scales(spec)
    normalised = apply_context_normalisation(tasks, scales, spec)
    scaler = TrainingOnlyStandardizer.fit(normalised, feature_columns(spec), spec)
    assert pd.Timestamp(scaler.max_fit_target_timestamp) <= pd.Timestamp(
        spec["dates"]["development_end"]
    )


def test_development_panel_refuses_the_unauthorised_measurement_state(spec: dict):
    with pytest.raises(MeasurementStateError):
        load_development_panel(spec, "august")


def _synthetic_development_panel(spec: dict) -> pd.DataFrame:
    """A 27-unit panel with realistic scale spread but no real outcome values."""
    index = pd.date_range(
        spec["dates"]["full_start"],
        spec["dates"]["hyperparameter_validation_end"],
        freq="D",
    )
    generator = np.random.default_rng(int(spec["tasks"]["seed"]))
    day = np.arange(len(index), dtype="float64")
    columns = {}
    for position, unit in enumerate(development_units(spec)):
        level = 0.5 * (1.6 ** position)
        weekly = 0.15 * level * np.sin(2.0 * np.pi * day / 7.0)
        drift = 0.02 * level * np.sin(2.0 * np.pi * day / 365.0)
        noise = generator.normal(scale=0.10 * level, size=len(index))
        columns[unit] = np.clip(level + weekly + drift + noise, 0.0, None)
    return pd.DataFrame(columns, index=index)


def test_a2_validation_runs_end_to_end_on_a_synthetic_panel(tmp_path, monkeypatch):
    """Exercise the whole A2 phase without reading a real outcome row.

    This is a synthetic smoke test, not a result: it proves the phase executes,
    writes its three artefacts, and derives PASS from its own sealing evidence.
    The real measurement-state hash verification is covered by the A1 audit
    tests and is stubbed here so nothing is written into the repository.
    """
    module = _audit_module()
    loaded, sha = module.load_detection_spec()
    patched = deepcopy(loaded)
    patched["model"]["outputs"] = {
        "scores": "scores.csv",
        "predictions": "predictions.csv",
        "manifest": "manifest.json",
    }
    patched["model"]["global_model"]["grid"]["alpha"] = [1.0, 100.0]

    monkeypatch.setattr(module, "load_detection_spec", lambda *a, **k: (patched, sha))
    monkeypatch.setattr(
        module,
        "load_development_panel",
        lambda spec_, state, **kwargs: _synthetic_development_panel(spec_),
    )
    monkeypatch.setattr(
        module,
        "_measurement_state_checks",
        lambda spec_: [
            {"measurement_state": name, "available": True, "outcome_rows_read": False}
            for name in ("july", "august")
        ],
    )
    monkeypatch.setattr(module.config, "ROOT", tmp_path)

    manifest = module.run_validation()

    assert manifest["phase"] == "A2"
    assert manifest["status"] == "PASS", manifest.get("status_failures")
    assert manifest["status_failures"] == []
    assert manifest["inputs"]["measurement_state_used"] == "july"
    assert manifest["sealing_assertions"]["hormuz_row_entered_any_estimator"] is False
    assert manifest["sealing_assertions"]["measurement_states_mixed"] is False
    assert manifest["sealing_assertions"]["validation_influenced_context_scale"] is False
    assert manifest["sealing_assertions"]["development_population_is_27_non_hormuz"] is True
    assert manifest["estimators"]["tsfm_benchmarks_included"] is False
    assert manifest["estimators"]["stochastic_component"] is False

    selected = manifest["estimators"]["selected_alpha_by_horizon"]
    assert sorted(int(key) for key in selected) == [1, 7, 30]
    assert set(selected.values()).issubset({1.0, 100.0})

    for name in ("scores.csv", "predictions.csv", "manifest.json"):
        assert (tmp_path / name).is_file()
    assert len(manifest["outputs"]["scores_sha256"]) == 64
    assert len(manifest["outputs"]["predictions_sha256"]) == 64

    scores = pd.read_csv(tmp_path / "scores.csv")
    assert set(scores["unit"]) == set(development_units(patched))
    assert patched["population"]["hormuz_unit"] not in set(scores["unit"])
    assert {"seasonal_naive", "local_ar_1_7"}.issubset(set(scores["model"]))
    assert (scores["mase"] > 0).all()
    assert set(scores["horizon_days"]) == {1, 7, 30}

    predictions = pd.read_csv(tmp_path / "predictions.csv")
    assert set(predictions["model"]) == set(manifest["outputs"]["reported_models"])
    for horizon in (1, 7, 30):
        at_horizon = set(predictions.loc[predictions["horizon_days"].eq(horizon), "model"])
        assert at_horizon == {
            f"global_ridge_alpha_{selected[str(horizon)]:g}",
            "seasonal_naive",
            "local_ar_1_7",
        }

    intervals = pd.DataFrame(manifest["results"]["intervals"])
    assert {"coverage_0.8", "coverage_0.95"}.issubset(intervals.columns)
    assert ((intervals["coverage_0.8"] >= 0.0) & (intervals["coverage_0.8"] <= 1.0)).all()
