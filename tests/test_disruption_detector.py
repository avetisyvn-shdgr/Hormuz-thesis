from __future__ import annotations

from copy import deepcopy

import numpy as np
import pandas as pd
import pytest

from hormuz_throughput.disruption_detector import (
    apply_event_mask,
    fit_context_scale,
    load_event_mask,
    validate_detector_calibration_tasks,
)
from hormuz_throughput.global_forecaster import (
    LeakageError,
    build_task_geometry,
    load_detection_spec,
    rolling_origin_folds,
)


@pytest.fixture(scope="module")
def spec() -> dict:
    loaded, _ = load_detection_spec()
    return loaded


@pytest.fixture(scope="module")
def event_mask(spec: dict):
    return load_event_mask(spec)


def _rolling_tasks(spec: dict, date: str, units: list[str]) -> pd.DataFrame:
    target = pd.Timestamp(date)
    fold = next(
        candidate
        for candidate in rolling_origin_folds(spec)
        if candidate.score_start <= target <= candidate.score_end
    )
    residual_role = next(
        (name, bool(raw["detector_calibration_eligible"]))
        for name, raw in spec["rolling_origin"]["residual_roles"].items()
        if pd.Timestamp(raw["start"]) <= target <= pd.Timestamp(raw["end"])
    )
    frames = []
    for horizon in spec["tasks"]["horizons_days"]:
        frames.append(
            build_task_geometry(
                [date],
                units,
                [horizon],
                measurement_state="july",
                task_role="rolling_residual",
                seed=spec["tasks"]["seed"],
                fold_id=fold.fold_id,
                extra_columns={
                    "fit_start": fold.fit_start,
                    "fit_end": fold.score_start - pd.Timedelta(days=int(horizon)),
                    "score_start": fold.score_start,
                    "score_end": fold.score_end,
                    "residual_role": residual_role[0],
                    "calibration_eligible": residual_role[1],
                },
            )
        )
    return pd.concat(frames, ignore_index=True)


def test_event_mask_is_frozen_non_residual_and_unique_by_unit_day(event_mask):
    frame = event_mask.unit_days
    assert len(event_mask.sha256) == 64
    assert dict(event_mask.source_sha256) == {
        "external_chronology_v1": (
            "a0b3cd68ef33e1a4d123d1d827e3a93dfd1de14999c52cbffa0907e58ff98b10"
        )
    }
    assert not frame.duplicated(["unit", "date"]).any()
    assert "strait_of_hormuz" not in set(frame["unit"])
    assert {"suez_canal", "kerch_strait", "panama_canal"}.issubset(frame["unit"])


def test_mask_boundaries_come_from_the_external_record_not_the_panel(spec: dict):
    """No mask onset may be a date that was derived from the PortWatch panel.

    Three onsets in `config/multi_event_propagation.yaml` are marked
    "data-derived". Drawing a calibration mask boundary from the outcome being
    calibrated on would trim the residual pool using the outcome itself. The
    mask therefore binds to the external chronology, and this test fails if any
    record silently reverts to a data-derived date or to the panel register.
    """
    sources = spec["event_mask"]["sources"]
    assert [source["source_id"] for source in sources] == ["external_chronology_v1"]
    assert all(source["kind"] == "frozen_external_record" for source in sources)
    assert all(
        source["path"] != "config/multi_event_propagation.yaml" for source in sources
    )

    onsets = {
        record["event_id"]: record["start"] for record in spec["event_mask"]["records"]
    }
    assert onsets["panama_drought_2023_2024"] == "2023-07-30"
    assert onsets["red_sea_disruption_2024"] == "2023-12-14"
    assert onsets["panama_drought_2023_2024"] != "2023-12-19"
    assert onsets["red_sea_disruption_2024"] != "2024-01-13"
    assert onsets["suez_ever_given_2021"] == "2021-03-23"
    assert onsets["black_sea_kerch_2022"] == "2022-02-24"


def test_externally_documented_disrupted_days_are_not_left_in_calibration(event_mask):
    """The days the correction recovered must actually be masked now."""
    frame = event_mask.unit_days
    masked = {
        (row.unit, str(row.date.date())) for row in frame.itertuples()
    }
    assert ("panama_canal", "2023-07-30") in masked
    assert ("panama_canal", "2023-12-18") in masked
    for unit in ("bab_el_mandeb_strait", "suez_canal"):
        assert (unit, "2023-12-14") in masked
        assert (unit, "2024-01-12") in masked
    assert ("panama_canal", "2023-07-29") not in masked
    assert ("bab_el_mandeb_strait", "2023-12-13") not in masked


def test_masking_exposed_unit_does_not_delete_unaffected_unit_same_date(
    spec: dict, event_mask
):
    tasks = _rolling_tasks(spec, "2021-03-24", ["suez_canal", "dover_strait"])
    applied = apply_event_mask(tasks, event_mask)
    assert set(applied.excluded["unit"]) == {"suez_canal"}
    assert set(applied.eligible["unit"]) == {"dover_strait"}
    assert len(applied.excluded) == 3
    assert len(applied.eligible) == 3
    validate_detector_calibration_tasks(applied.eligible, spec)


def test_exposed_rows_deliberately_fail_detector_calibration(spec: dict, event_mask):
    tasks = _rolling_tasks(spec, "2021-03-24", ["suez_canal"])
    applied = apply_event_mask(tasks, event_mask)
    with pytest.raises(LeakageError, match="exposed unit-days"):
        validate_detector_calibration_tasks(applied.excluded, spec)


def test_hormuz_is_excluded_from_detector_calibration_even_before_onset(spec: dict):
    malicious = build_task_geometry(
        ["2025-12-01"],
        ["strait_of_hormuz"],
        [1],
        measurement_state="july",
        task_role="scoring_only",
        seed=spec["tasks"]["seed"],
        extra_columns={"calibration_eligible": True, "event_masked": False},
    )
    with pytest.raises(LeakageError, match="Hormuz observations are scoring-only"):
        validate_detector_calibration_tasks(malicious, spec)


def test_2024_hyperparameter_residuals_cannot_enter_detector_calibration(spec: dict):
    tasks = _rolling_tasks(spec, "2024-06-01", ["dover_strait"])
    tasks["residual_role"] = "hyperparameter_validation_oof"
    tasks["calibration_eligible"] = False
    tasks["event_masked"] = False
    with pytest.raises(LeakageError, match="ineligible residual role"):
        validate_detector_calibration_tasks(tasks, spec)


def test_event_mask_rejects_residual_derived_record(spec: dict):
    malicious = deepcopy(spec)
    malicious["event_mask"]["records"][0]["residual_derived"] = True
    with pytest.raises(LeakageError, match="non-residual-derived"):
        load_event_mask(malicious, verify_source_files=False)


def test_event_mask_rejects_source_hash_drift(spec: dict):
    malicious = deepcopy(spec)
    malicious["event_mask"]["sources"][0]["sha256"] = "0" * 64
    with pytest.raises(ValueError, match="source hash drift"):
        load_event_mask(malicious)


def test_event_mask_rejects_record_date_or_unit_not_in_frozen_source(spec: dict):
    malicious = deepcopy(spec)
    malicious["event_mask"]["records"][0]["start"] = "2021-03-22"
    with pytest.raises(ValueError, match="start does not match source event"):
        load_event_mask(malicious)

    malicious = deepcopy(spec)
    malicious["event_mask"]["records"][3]["units"].append("cape_of_good_hope")
    with pytest.raises(ValueError, match="units do not match source event"):
        load_event_mask(malicious)


def test_event_mask_rejects_missing_source_event_binding(spec: dict):
    malicious = deepcopy(spec)
    malicious["event_mask"]["records"][0].pop("source_event_key")
    with pytest.raises(ValueError, match="structured source event record"):
        load_event_mask(malicious)


def test_context_scale_ignores_all_surveillance_and_post_onset_values(spec: dict):
    index = pd.date_range("2019-01-01", "2026-03-10", freq="D")
    values = pd.Series(np.sin(np.arange(len(index)) / 17.0) + 50.0, index=index)
    first = fit_context_scale(values, spec, measurement_state="july")
    changed = values.copy()
    changed.loc[changed.index >= pd.Timestamp("2025-12-01")] = 9_999_999.0
    second = fit_context_scale(changed, spec, measurement_state="july")
    assert first.digest() == second.digest()
    assert first.context_end == pd.Timestamp("2025-11-30")
    assert first.n_context == second.n_context


def test_context_scale_deliberately_rejects_post_surveillance_access(spec: dict):
    index = pd.date_range("2019-01-01", "2026-03-10", freq="D")
    values = pd.Series(np.arange(len(index), dtype="float64"), index=index)
    with pytest.raises(LeakageError, match="may not read Hormuz surveillance"):
        fit_context_scale(
            values,
            spec,
            measurement_state="july",
            context_end="2025-12-01",
        )


def test_context_scales_keep_measurement_states_separate(spec: dict):
    index = pd.date_range("2019-01-01", "2025-11-30", freq="D")
    july = pd.Series(np.arange(len(index), dtype="float64"), index=index)
    august = july * 0.8 + 3.0
    july_scale = fit_context_scale(july, spec, measurement_state="july")
    august_scale = fit_context_scale(august, spec, measurement_state="august")
    assert july_scale.measurement_state == "july"
    assert august_scale.measurement_state == "august"
    assert july_scale.digest() != august_scale.digest()
