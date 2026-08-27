"""Phase A4 tests: the frozen-input contract and the no-tuning seal.

Every test here runs on synthetic panels or on hand-built score sequences. None
reads a real Hormuz outcome, and none runs the final scoring: A4's own run is
Mher's, and its results are not something a test may pre-empt.

The contract tests check that A4 refuses to run against anything other than the
A3 objects Mher accepted. The seal tests check the property the phase exists to
guarantee -- that nothing is estimated once the event is in scope -- from both
sides: the latch refuses an attempt, and the system digest catches a success.
"""
from __future__ import annotations

from copy import deepcopy
import json

import numpy as np
import pandas as pd
import pytest

from lngfreight.detector_calibration import RAW_LEVEL, SCALE_INVARIANT
from lngfreight.global_forecaster import (
    MeasurementStateError,
    development_units,
    load_detection_spec,
)
from lngfreight.hormuz_stress import (
    AUGUST,
    JULY,
    RIDGE_MODEL,
    SEASONAL_NAIVE,
    A4GateError,
    FrozenSystem,
    PostHormuzTuningError,
    TuningLock,
    build_state_system,
    decompose_revision,
    first_alarm,
    load_accepted_thresholds,
    proportional_constant,
    score_hormuz,
    verify_accepted_a3,
)


@pytest.fixture(scope="module")
def spec() -> dict:
    loaded, _ = load_detection_spec()
    return loaded


def _synthetic_panel(spec: dict, *, factor: float = 1.0, seed: int = 5) -> pd.DataFrame:
    """A complete daily panel over the frozen window for all 28 units."""
    index = pd.date_range(spec["dates"]["full_start"], spec["dates"]["scoring_end"], freq="D")
    rng = np.random.default_rng(seed)
    trend = np.arange(len(index), dtype="float64")
    data = {}
    for position, unit in enumerate(spec["population"]["units"]):
        level = 12.0 + 3.0 * position
        data[unit] = (
            level
            + 0.001 * trend
            + 2.0 * np.sin(trend / 7.0 + position)
            + rng.normal(scale=1.0, size=len(index))
        ) * factor
    return pd.DataFrame(data, index=index)


# ---------------------------------------------------------------------------
# Contract: A4 runs only against the accepted A3
# ---------------------------------------------------------------------------


def test_the_accepted_a3_artifacts_verify(spec: dict):
    accepted = verify_accepted_a3(spec)
    assert accepted["a3_manifest_status"] == "PASS"
    assert accepted["a3_detector_design_version"] == 2
    assert accepted["calibration_sha256"] == spec["a3_acceptance"]["accepted_artifacts"]["calibration_sha256"]
    assert accepted["false_alarms_sha256"] == spec["a3_acceptance"]["accepted_artifacts"]["false_alarms_sha256"]


def test_a_different_a3_artifact_is_refused(spec: dict):
    drifted = deepcopy(spec)
    drifted["a3_acceptance"]["accepted_artifacts"]["calibration_sha256"] = "0" * 64
    with pytest.raises(A4GateError, match="not the accepted one"):
        verify_accepted_a3(drifted)


def test_an_unaccepted_a3_is_refused(spec: dict):
    unaccepted = deepcopy(spec)
    unaccepted["a3_acceptance"]["accepted"] = False
    with pytest.raises(A4GateError):
        verify_accepted_a3(unaccepted)

    unfrozen = deepcopy(spec)
    unfrozen["a3_acceptance"]["thresholds_frozen"] = False
    with pytest.raises(A4GateError):
        verify_accepted_a3(unfrozen)


def test_thresholds_load_from_the_accepted_artifact_and_match_the_frozen_record(spec: dict):
    thresholds = load_accepted_thresholds(spec)
    assert len(thresholds) == 12
    assert {item.model for item in thresholds} == {RIDGE_MODEL, SEASONAL_NAIVE}
    assert {item.form for item in thresholds} == {RAW_LEVEL, SCALE_INVARIANT}
    assert {item.horizon_days for item in thresholds} == {1, 7, 30}


def test_a_threshold_that_drifted_from_the_frozen_record_is_refused(spec: dict):
    drifted = deepcopy(spec)
    drifted["a3_acceptance"]["operational_thresholds"][0]["threshold"] += 0.5
    with pytest.raises(A4GateError, match="threshold drift"):
        load_accepted_thresholds(drifted)


def test_local_ar_is_not_scored_on_hormuz(spec: dict):
    """Leave-Hormuz-out forbids the unit-specific fit local AR needs."""
    mode = spec["final"]["modes"][3]
    assert mode["local_ar_scored_on_hormuz"] is False
    assert set(mode["models_scored_on_hormuz"]) == {RIDGE_MODEL, SEASONAL_NAIVE}
    assert all(item.model != "local_ar_1_7" for item in load_accepted_thresholds(spec))


def test_the_august_authorisation_is_recorded_as_neither_promotion_nor_averaging(spec: dict):
    authorisation = spec["final"]["measurement_states"]["august_authorisation"]
    assert authorisation["scope"] == "A4 only"
    assert authorisation["promotes_vintage"] is False
    assert authorisation["averages_vintages"] is False
    assert spec["measurement_states"]["never_join_or_average"] is True


def test_a_configuration_hash_mismatch_refuses_to_score():
    """Plan A4: the script refuses a configuration-hash mismatch."""
    import run_hormuz_detection as runner

    with pytest.raises(SystemExit, match="configuration-hash mismatch"):
        runner.run_final("0" * 64, "both", check_only=True)


def test_the_a4_july_panel_is_the_panel_a2_and_a3_actually_used(spec: dict):
    """A4 must not rebuild the July panel differently from the earlier phases.

    Regression guard: A4 first constructed the panel with `DataFrame.pivot`,
    which returned a silently malformed index on this data -- 92 unique dates
    repeated across 2,526 rows. Nothing downstream would have noticed until a
    context scale refused the duplicated index. Pinning A4's panel to the one
    A2 and A3 used removes the whole class of divergence, and this reads only
    pre-surveillance days.
    """
    from lngfreight.global_forecaster import load_development_panel
    from lngfreight.hormuz_stress import load_measurement_state_panel

    start = spec["dates"]["full_start"]
    end = spec["dates"]["detector_calibration_end"]
    expected = load_development_panel(spec, JULY, start=start, end=end)
    actual = load_measurement_state_panel(spec, JULY, start=start, end=end)

    assert actual.index.has_duplicates is False
    assert actual.index.is_monotonic_increasing
    assert actual.index.equals(pd.date_range(start, end, freq="D", name="date"))
    shared = sorted(set(expected.columns) & set(actual.columns))
    assert set(development_units(spec)).issubset(shared)
    pd.testing.assert_frame_equal(
        actual.loc[:, shared], expected.loc[:, shared], check_names=False
    )


# ---------------------------------------------------------------------------
# The declared cross-state transport (plan A4 mode 3)
# ---------------------------------------------------------------------------


def _scoring_rows(spec: dict, state: str, panel: pd.DataFrame) -> pd.DataFrame:
    from lngfreight.global_forecaster import (
        apply_context_normalisation,
        build_hormuz_scoring_geometry,
        materialize_task_features,
    )
    from lngfreight.disruption_detector import fit_context_scale

    hormuz = spec["population"]["hormuz_unit"]
    rows = materialize_task_features(panel, build_hormuz_scoring_geometry(spec, state), spec)
    scale = fit_context_scale(
        panel[hormuz],
        spec,
        measurement_state=state,
        context_start=spec["model"]["context_normalisation"]["context_start"],
        context_end=spec["scaling"]["context_end"],
    )
    return apply_context_normalisation(rows, {hormuz: scale}, spec)


def test_same_state_standardising_goes_through_the_sealed_transform(spec: dict):
    """Modes 1, 2 and 4 must bypass nothing at all."""
    from lngfreight.hormuz_stress import apply_frozen_standardiser

    panel = _synthetic_panel(spec)
    lock = TuningLock()
    system = build_state_system(
        spec, panel, JULY, alpha_by_horizon={1: 100.0, 7: 1000.0, 30: 1000.0}, lock=lock
    )
    rows = _scoring_rows(spec, JULY, panel)
    subset = rows.loc[rows["horizon_days"].eq(7)]
    standardiser = system.standardisers[7]

    direct = standardiser.transform(subset, spec)
    routed = apply_frozen_standardiser(
        standardiser, subset, spec, detector_state=JULY, outcome_state=JULY
    )
    pd.testing.assert_frame_equal(routed, direct)


def test_the_transport_applies_july_constants_without_relabelling_august(spec: dict):
    """Mode 3: the exception is declared, narrow, and leaves provenance intact."""
    from lngfreight.hormuz_stress import apply_frozen_standardiser

    panel = _synthetic_panel(spec)
    lock = TuningLock()
    july_system = build_state_system(
        spec, panel, JULY, alpha_by_horizon={1: 100.0, 7: 1000.0, 30: 1000.0}, lock=lock
    )
    august_rows = _scoring_rows(spec, AUGUST, panel)
    subset = august_rows.loc[august_rows["horizon_days"].eq(7)]
    standardiser = july_system.standardisers[7]

    # The sealed path still refuses: the seal is not weakened.
    with pytest.raises(MeasurementStateError, match="cannot silently transform"):
        standardiser.transform(subset, spec)

    transported = apply_frozen_standardiser(
        standardiser, subset, spec, detector_state=JULY, outcome_state=AUGUST
    )
    # No row is relabelled; the artefacts never claim August rows were July.
    assert set(transported["measurement_state"]) == {AUGUST}
    # And the July constants were the ones applied.
    for column, mean, scale in zip(
        standardiser.feature_columns, standardiser.means, standardiser.scales
    ):
        assert np.allclose(
            transported[column].to_numpy(dtype="float64"),
            (subset[column].to_numpy(dtype="float64") - mean) / scale,
        )


def test_a_transport_that_misdeclares_its_states_is_refused(spec: dict):
    """The declaration must match reality or the exception does not apply."""
    from lngfreight.hormuz_stress import apply_frozen_standardiser

    panel = _synthetic_panel(spec)
    lock = TuningLock()
    july_system = build_state_system(
        spec, panel, JULY, alpha_by_horizon={1: 100.0, 7: 1000.0, 30: 1000.0}, lock=lock
    )
    august_rows = _scoring_rows(spec, AUGUST, panel)
    subset = august_rows.loc[august_rows["horizon_days"].eq(7)]

    # Rows are August but the caller claims the outcomes are July.
    with pytest.raises(MeasurementStateError, match="rows carry"):
        apply_frozen_standardiser(
            july_system.standardisers[7], subset, spec,
            detector_state=AUGUST, outcome_state=JULY,
        )
    # Outcomes declared correctly, but the detector state claimed is not the
    # state the standardiser that was handed over was actually fitted on.
    with pytest.raises(MeasurementStateError, match="fitted on"):
        apply_frozen_standardiser(
            july_system.standardisers[7], subset, spec,
            detector_state="not_a_fitted_state", outcome_state=AUGUST,
        )


# ---------------------------------------------------------------------------
# The no-tuning seal
# ---------------------------------------------------------------------------


def test_the_latch_starts_open_and_closes_one_way():
    lock = TuningLock()
    assert lock.hormuz_surveillance_read is False
    lock.assert_estimation_allowed("fitting")

    lock.note_hormuz_surveillance_read()
    assert lock.hormuz_surveillance_read is True
    with pytest.raises(PostHormuzTuningError):
        lock.assert_estimation_allowed("fitting")

    # There is deliberately no way to reopen it.
    assert not hasattr(lock, "reset")
    lock.note_hormuz_surveillance_read()
    assert lock.hormuz_surveillance_read is True


def test_loading_thresholds_after_the_latch_is_refused(spec: dict):
    lock = TuningLock()
    lock.note_hormuz_surveillance_read()
    with pytest.raises(PostHormuzTuningError):
        load_accepted_thresholds(spec, lock=lock)


def test_building_a_system_after_the_latch_is_refused(spec: dict):
    lock = TuningLock()
    lock.note_hormuz_surveillance_read()
    with pytest.raises(PostHormuzTuningError, match="after Hormuz surveillance outcomes"):
        build_state_system(
            spec,
            _synthetic_panel(spec),
            JULY,
            alpha_by_horizon={1: 100.0, 7: 1000.0, 30: 1000.0},
            lock=lock,
        )


def test_scoring_refuses_to_run_with_the_latch_still_open(spec: dict):
    """The seal cannot be bypassed by never declaring the outcomes read."""
    panel = _synthetic_panel(spec)
    lock = TuningLock()
    system = build_state_system(
        spec, panel, JULY, alpha_by_horizon={1: 100.0, 7: 1000.0, 30: 1000.0}, lock=lock
    )
    with pytest.raises(AssertionError, match="latch"):
        score_hormuz(
            spec,
            panel,
            system,
            outcome_state=JULY,
            detector_state=JULY,
            mode="july_state_detectors",
            lock=lock,
        )


def test_the_system_digest_is_stable_and_sensitive(spec: dict):
    panel = _synthetic_panel(spec)
    lock = TuningLock()
    system = build_state_system(
        spec, panel, JULY, alpha_by_horizon={1: 100.0, 7: 1000.0, 30: 1000.0}, lock=lock
    )
    thresholds = load_accepted_thresholds(spec)
    frozen = FrozenSystem(states={JULY: system}, thresholds=thresholds)

    assert frozen.digest() == frozen.digest()
    moved = FrozenSystem(
        states={JULY: system},
        thresholds=tuple(
            item.__class__(
                model=item.model,
                horizon_days=item.horizon_days,
                form=item.form,
                threshold=item.threshold + (1.0 if index == 0 else 0.0),
            )
            for index, item in enumerate(thresholds)
        ),
    )
    assert moved.digest() != frozen.digest()


def test_scoring_leaves_the_system_digest_unchanged(spec: dict):
    """End to end on synthetic data: score, then prove nothing moved."""
    panel = _synthetic_panel(spec)
    lock = TuningLock()
    system = build_state_system(
        spec, panel, JULY, alpha_by_horizon={1: 100.0, 7: 1000.0, 30: 1000.0}, lock=lock
    )
    frozen = FrozenSystem(states={JULY: system}, thresholds=load_accepted_thresholds(spec))
    sealed = frozen.digest()

    lock.note_hormuz_surveillance_read()
    scored = score_hormuz(
        spec,
        panel,
        system,
        outcome_state=JULY,
        detector_state=JULY,
        mode="july_state_detectors",
        lock=lock,
    )
    assert frozen.digest() == sealed
    assert set(scored["unit"]) == {spec["population"]["hormuz_unit"]}
    assert set(scored["model"]) == {RIDGE_MODEL, SEASONAL_NAIVE}
    assert "local_ar_1_7" not in set(scored["model"])
    # Scoring covers the frozen surveillance window and nothing outside it.
    targets = pd.to_datetime(scored["target_timestamp"])
    assert targets.min() >= pd.Timestamp(spec["dates"]["hormuz_surveillance_start"])
    assert targets.max() <= pd.Timestamp(spec["dates"]["scoring_end"])


# ---------------------------------------------------------------------------
# Synthetic: alarms and severity
# ---------------------------------------------------------------------------


def _alarm(pattern: str, spec: dict, start: str = "2026-02-28"):
    dates = pd.date_range(start, periods=len(pattern), freq="D")
    scores = np.array([10.0 if char == "X" else 0.0 for char in pattern])
    return first_alarm(dates, scores, spec, threshold=5.0)


def test_an_isolated_exceedance_does_not_raise_an_alarm(spec: dict):
    assert _alarm("X.X.X", spec).fired is False


def test_the_alarm_is_dated_from_the_first_of_its_consecutive_exceedances(spec: dict):
    outcome = _alarm("..XX.", spec)
    assert outcome.fired is True
    # Onset is 2026-02-28; the pair starts on the third day.
    assert outcome.alarm_date == pd.Timestamp("2026-03-02")
    assert outcome.delay_days == 2.0


def test_severity_averages_the_score_over_the_frozen_windows(spec: dict):
    dates = pd.date_range("2026-02-28", periods=40, freq="D")
    scores = np.zeros(40)
    scores[0:2] = 10.0  # the alarm pair
    scores[2:7] = 20.0  # rest of the 7-day window
    outcome = first_alarm(dates, scores, spec, threshold=5.0)
    assert outcome.fired is True
    assert outcome.severity_7_day == pytest.approx((2 * 10.0 + 5 * 20.0) / 7.0)
    assert outcome.severity_30_day == pytest.approx((2 * 10.0 + 5 * 20.0) / 30.0)


def test_a_detector_that_never_exceeds_reports_no_alarm_and_no_severity(spec: dict):
    outcome = _alarm("......", spec)
    assert outcome.fired is False
    assert outcome.alarm_date is None
    assert outcome.delay_days is None
    assert np.isnan(outcome.severity_7_day)


# ---------------------------------------------------------------------------
# Synthetic: the rescaling invariance the plan requires
# ---------------------------------------------------------------------------


def test_rescaling_a_whole_series_leaves_the_scale_invariant_detector_unchanged(spec: dict):
    """Plan A4's required synthetic test.

    Multiplying an entire series by a positive constant scales the context MAD
    by the same constant, so the scale-invariant score is unchanged and the
    detector fires identically. This is mathematical behaviour, not evidence
    about the vintages.
    """
    base = _synthetic_panel(spec, seed=11)
    for factor in (0.5, 2.0, 7.3):
        rescaled = base * factor
        results = []
        for panel in (base, rescaled):
            lock = TuningLock()
            system = build_state_system(
                spec, panel, JULY, alpha_by_horizon={1: 100.0, 7: 1000.0, 30: 1000.0}, lock=lock
            )
            lock.note_hormuz_surveillance_read()
            scored = score_hormuz(
                spec, panel, system,
                outcome_state=JULY, detector_state=JULY,
                mode="july_state_detectors", lock=lock,
            )
            results.append(
                scored.sort_values(["model", "horizon_days", "target_timestamp"])[
                    SCALE_INVARIANT
                ].to_numpy()
            )
        assert np.allclose(results[0], results[1], rtol=1e-8, atol=1e-8)


def test_rescaling_does_move_the_raw_level_detector(spec: dict):
    """The contrast the two forms exist to expose; assert it is real."""
    base = _synthetic_panel(spec, seed=11)
    results = []
    for panel in (base, base * 2.0):
        lock = TuningLock()
        system = build_state_system(
            spec, panel, JULY, alpha_by_horizon={1: 100.0, 7: 1000.0, 30: 1000.0}, lock=lock
        )
        lock.note_hormuz_surveillance_read()
        scored = score_hormuz(
            spec, panel, system,
            outcome_state=JULY, detector_state=JULY,
            mode="july_state_detectors", lock=lock,
        )
        results.append(
            scored.sort_values(["model", "horizon_days", "target_timestamp"])[RAW_LEVEL].to_numpy()
        )
    assert not np.allclose(results[0], results[1])


# ---------------------------------------------------------------------------
# Synthetic: the cross-vintage decomposition
# ---------------------------------------------------------------------------


def test_the_proportional_constant_is_recovered_exactly(spec: dict):
    july = np.array([3.0, 5.0, 8.0, 13.0])
    assert proportional_constant(july, july * 1.37) == pytest.approx(1.37)


def test_a_purely_proportional_revision_leaves_no_residual(spec: dict):
    index = pd.date_range("2025-01-01", "2026-03-31", freq="D")
    july = pd.Series(np.linspace(40.0, 60.0, len(index)), index=index)
    august = july * 0.83

    constant, frame = decompose_revision(july, august, fit_end=pd.Timestamp("2025-11-30"))
    assert constant == pytest.approx(0.83)
    assert np.allclose(frame["residual_revision"].to_numpy(), 0.0, atol=1e-9)
    # And the split is estimated on pre-surveillance days alone.
    assert frame["pre_surveillance"].sum() == (index <= pd.Timestamp("2025-11-30")).sum()


def test_a_non_proportional_revision_lands_in_the_residual(spec: dict):
    index = pd.date_range("2025-01-01", "2026-03-31", freq="D")
    july = pd.Series(np.linspace(40.0, 60.0, len(index)), index=index)
    august = july * 0.9
    bump = index >= pd.Timestamp("2026-01-01")
    august = august + pd.Series(np.where(bump, -7.0, 0.0), index=index)

    constant, frame = decompose_revision(july, august, fit_end=pd.Timestamp("2025-11-30"))
    # The constant is estimated pre-surveillance, so the bump does not enter it.
    assert constant == pytest.approx(0.9, abs=1e-6)
    pre = frame.loc[frame["pre_surveillance"], "residual_revision"].to_numpy()
    bumped = frame["date"] >= pd.Timestamp("2026-01-01")
    post = frame.loc[bumped, "residual_revision"].to_numpy()
    assert np.allclose(pre, 0.0, atol=1e-9)
    assert np.allclose(post, -7.0, atol=1e-9)


def test_the_decomposition_needs_a_pre_surveillance_overlap(spec: dict):
    index = pd.date_range("2026-01-01", "2026-03-31", freq="D")
    series = pd.Series(np.ones(len(index)), index=index)
    with pytest.raises(ValueError, match="pre-surveillance overlap"):
        decompose_revision(series, series, fit_end=pd.Timestamp("2025-11-30"))
