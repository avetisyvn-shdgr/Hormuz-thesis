"""Phase A4 final Hormuz stress test.

A4 is the only phase that scores Hormuz and the only phase authorised to read
the August measurement state.  It estimates nothing.

The governing property, and the one this module exists to make mechanical rather
than promised, is **no tuning after Hormuz**.  Every estimated object -- pooled
standardiser, ridge coefficients, Hormuz context scale -- is built from
pre-surveillance data and digested before a single Hormuz surveillance outcome
is read.  Reading those outcomes trips a one-way latch, after which any attempt
to fit, calibrate or select raises.  When scoring finishes the digest is
recomputed and must equal the sealed one.  Two independent checks, both reported
as sealing assertions: the latch catches an attempt, the digest catches a
success.

Thresholds are never recomputed here.  They are loaded from the A3 artefact Mher
accepted on 2026-08-28, whose hash is verified against `a3_acceptance`, and each
loaded value must equal the estimate frozen in the configuration.

The two measurement states are scored separately and never joined or averaged.
Their disagreement is the deliverable, so averaging it away would destroy the
result the phase exists to produce.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path
from typing import Mapping, Sequence

import numpy as np
import pandas as pd

from . import config
from .detector_calibration import (
    DETECTOR_FORMS,
    RAW_LEVEL,
    SCALE_INVARIANT,
    build_episode_curve,
    build_rolling_fit_geometry,
    count_episodes,
    fold_context_scales,
    raw_level_score,
    scale_invariant_score,
    segment_boundaries,
)
from .disruption_detector import fit_context_scale
from .global_forecaster import (
    LeakageError,
    MeasurementStateError,
    RidgeGlobalModel,
    TrainingOnlyStandardizer,
    apply_context_normalisation,
    assert_task_access,
    build_hormuz_scoring_geometry,
    denormalise,
    development_units,
    feature_columns,
    materialize_task_features,
    rolling_origin_folds,
    seasonal_naive_predictions,
    sha256_file,
    validate_task_table,
)

CONSUMER = "scripts/run_hormuz_detection.py"
RIDGE_MODEL = "global_ridge"
SEASONAL_NAIVE = "seasonal_naive"
JULY = "july"
AUGUST = "august"


class PostHormuzTuningError(RuntimeError):
    """Raised when estimation is attempted after Hormuz outcomes were read."""


class A4GateError(RuntimeError):
    """Raised when A4's frozen inputs do not match what Mher accepted."""


class TuningLock:
    """One-way latch separating estimation from scoring.

    The latch is deliberately not resettable.  A phase that could re-open it
    could tune on the event, which is the single thing A4 must not do.
    """

    def __init__(self) -> None:
        self._hormuz_surveillance_read = False

    @property
    def hormuz_surveillance_read(self) -> bool:
        return self._hormuz_surveillance_read

    def note_hormuz_surveillance_read(self) -> None:
        self._hormuz_surveillance_read = True

    def assert_estimation_allowed(self, what: str) -> None:
        if self._hormuz_surveillance_read:
            raise PostHormuzTuningError(
                f"{what} was attempted after Hormuz surveillance outcomes were read. "
                "A4 estimates nothing once the event is in scope; every fitted "
                "object is built and sealed beforehand."
            )




def verify_accepted_a3(spec: Mapping, *, root: Path = config.ROOT) -> dict[str, object]:
    """Refuse to run unless the A3 artefacts are the ones Mher accepted."""
    acceptance = spec.get("a3_acceptance")
    if not isinstance(acceptance, Mapping) or acceptance.get("accepted") is not True:
        raise A4GateError("A4 requires an accepted A3; `a3_acceptance` does not record one")
    if acceptance.get("thresholds_frozen") is not True:
        raise A4GateError("A4 requires the A3 thresholds to be frozen")

    outputs = spec["detector"]["outputs"]
    expected = acceptance["accepted_artifacts"]
    problems: list[str] = []
    observed: dict[str, str] = {}
    for name, key in (("calibration", "calibration_sha256"), ("false_alarms", "false_alarms_sha256")):
        path = root / outputs[name]
        if not path.is_file():
            problems.append(f"accepted A3 {name} artefact is missing at {outputs[name]}")
            continue
        digest = sha256_file(path)
        observed[name] = digest
        if digest != expected[key]:
            problems.append(
                f"A3 {name} artefact is not the accepted one: expected "
                f"{expected[key]}, found {digest}"
            )

    manifest_path = root / outputs["manifest"]
    manifest: dict = {}
    if not manifest_path.is_file():
        problems.append("the A3 calibration manifest is missing")
    else:
        manifest = json.loads(manifest_path.read_text())
        if manifest.get("status") != "PASS":
            problems.append(f"the A3 manifest status is {manifest.get('status')!r}, not PASS")
        if int(manifest.get("detector_design_version", 0)) != int(
            acceptance["detector_design_version"]
        ):
            problems.append("the A3 manifest was produced under a different design version")
        if manifest.get("ratification_required"):
            problems.append("the A3 manifest still carries an outstanding ratification item")

    if problems:
        raise A4GateError(
            "A4 is gated on the accepted A3 and that gate is not met:\n  - "
            + "\n  - ".join(problems)
        )
    return {
        "calibration_sha256": observed["calibration"],
        "false_alarms_sha256": observed["false_alarms"],
        "a3_manifest_status": manifest.get("status"),
        "a3_manifest_config_sha256": manifest.get("config", {}).get("sha256"),
        "a3_detector_design_version": int(manifest.get("detector_design_version", 0)),
        "accepted_config_sha256": acceptance["accepted_config_sha256"],
        "accepted_on": acceptance["accepted_on"],
        "accepted_by": acceptance["accepted_by"],
    }


@dataclass(frozen=True)
class FrozenThreshold:
    model: str
    horizon_days: int
    form: str
    threshold: float

    @property
    def key(self) -> tuple[str, int, str]:
        return (self.model, int(self.horizon_days), self.form)


def load_accepted_thresholds(
    spec: Mapping,
    *,
    root: Path = config.ROOT,
    lock: TuningLock | None = None,
) -> tuple[FrozenThreshold, ...]:
    """Load A3's operational thresholds and check them against the frozen record.

    Two independent sources must agree: the accepted CSV, whose hash the gate
    verified, and the estimates recorded in `a3_acceptance.operational_thresholds`.
    A drift in either is a refusal, not a warning.
    """
    if lock is not None:
        lock.assert_estimation_allowed("loading detector thresholds")

    frame = pd.read_csv(root / spec["detector"]["outputs"]["calibration"])
    operational = frame.loc[frame["scope"].eq("operational")]
    if operational.empty:
        raise A4GateError("the accepted calibration artefact carries no operational threshold")

    recorded = {
        (str(row["model"]), int(row["horizon_days"]), str(row["form"])): float(row["threshold"])
        for row in spec["a3_acceptance"]["operational_thresholds"]
    }
    thresholds: list[FrozenThreshold] = []
    for _, row in operational.iterrows():
        key = (str(row["model"]), int(row["horizon_days"]), str(row["form"]))
        value = float(row["threshold"])
        if key not in recorded:
            raise A4GateError(f"the accepted CSV carries an unrecorded threshold for {key}")
        if not np.isclose(recorded[key], value, rtol=0.0, atol=1e-12):
            raise A4GateError(
                f"threshold drift for {key}: configuration records {recorded[key]!r}, "
                f"the accepted artefact carries {value!r}"
            )
        thresholds.append(
            FrozenThreshold(model=key[0], horizon_days=key[1], form=key[2], threshold=value)
        )
    missing = set(recorded).difference(item.key for item in thresholds)
    if missing:
        raise A4GateError(f"the accepted artefact is missing frozen thresholds {sorted(missing)}")
    return tuple(sorted(thresholds, key=lambda item: item.key))




def load_measurement_state_panel(
    spec: Mapping,
    state: str,
    *,
    start: str | pd.Timestamp,
    end: str | pd.Timestamp,
    lock: TuningLock | None = None,
) -> pd.DataFrame:
    """Admit one measurement state through the registry and build its wide panel.

    August is registered sensitivity-only behind a consumer allowlist.  A4 opts
    in as a declared consumer on Mher's 2026-08-28 authorisation: it scores the
    vintage as a separate state and reports its disagreement with July.  It does
    not promote the vintage, substitute it for the pinned primary, or average
    the two.  The opt-in is declared in the frozen configuration, not decided
    here.
    """
    from .registry import RegisteredArtifact, get_variable
    from .spatial import slugify_portname

    if spec["measurement_states"].get("never_join_or_average") is not True:
        raise LeakageError("measurement-state joining/averaging must be prohibited")
    scored = tuple(spec["final"]["measurement_states"]["scored"])
    if state not in scored:
        raise ValueError(f"A4 scores {scored}, not {state!r}")

    state_spec = spec["measurement_states"][state]
    try:
        artifact = get_variable(
            state_spec["registry_variable"],
            query={"consumer": CONSUMER},
            allow_sensitivity=state != JULY,
        )
    except PermissionError as exc:
        raise PermissionError(
            f"STOP: the registry refused measurement state {state!r}.\n  {exc}\n"
            f"  consumer presented: {CONSUMER}\n"
            "A4 reads this vintage as a separate measurement state and reports its "
            "disagreement with July; it does not promote or substitute it. Admitting "
            "a sensitivity consumer is a governance decision recorded in "
            "config/sources.yaml."
        ) from exc
    if not isinstance(artifact, RegisteredArtifact):
        raise TypeError(f"{state_spec['registry_variable']!r} must resolve as a frozen artifact")

    expected_path = (config.ROOT / state_spec["path"]).resolve()
    if artifact.path.resolve() != expected_path:
        raise A4GateError(
            f"state {state!r} resolved to {artifact.path}, expected {expected_path}; "
            "refusing to substitute a measurement state"
        )
    if artifact.sha256 != state_spec["sha256"]:
        raise A4GateError(
            f"STOP: input hash mismatch for state {state!r}.\n"
            f"  expected {state_spec['sha256']}\n  found    {artifact.sha256}"
        )

    value_col = spec["outcome"]["column"]
    frame = artifact.read_csv(encoding="utf-8-sig")
    frame = frame.loc[:, ["date", "portname", value_col]].copy()
    frame["date"] = pd.to_datetime(frame["date"], format="%Y/%m/%d")
    frame["slug"] = frame["portname"].map(slugify_portname)

    index = pd.date_range(pd.Timestamp(start), pd.Timestamp(end), freq="D", name="date")
    columns: dict[str, pd.Series] = {}
    for slug, part in frame.groupby("slug", sort=True):
        if part["date"].duplicated().any():
            raise A4GateError(f"duplicate {state} dates for {slug!r}; refusing to score")
        columns[slug] = part.set_index("date")[value_col].sort_index().reindex(index)
    panel = pd.DataFrame(columns, index=index)

    missing = set(spec["population"]["units"]).difference(panel.columns)
    if missing:
        raise A4GateError(f"the {state} panel lacks frozen population units {sorted(missing)}")
    if panel.loc[:, sorted(spec["population"]["units"])].isna().any().any():
        raise A4GateError(
            f"the {state} panel has gaps over {index.min().date()}..{index.max().date()}; "
            "A4 requires a complete daily calendar for every frozen unit"
        )

    surveillance = pd.Timestamp(spec["dates"]["hormuz_surveillance_start"])
    hormuz = spec["population"]["hormuz_unit"]
    if lock is not None and hormuz in panel.columns and panel.index.max() >= surveillance:
        lock.note_hormuz_surveillance_read()
    return panel.astype("float64")




@dataclass(frozen=True)
class StateSystem:
    """Everything A4 needs for one measurement state, all pre-surveillance."""

    state: str
    fold_id: str
    models: dict[int, RidgeGlobalModel]
    standardisers: dict[int, TrainingOnlyStandardizer]
    development_scales: dict[int, dict[str, object]]
    hormuz_scale: object

    def digest(self) -> str:
        payload = {
            "state": self.state,
            "fold_id": self.fold_id,
            "models": {str(h): m.digest() for h, m in sorted(self.models.items())},
            "standardisers": {
                str(h): s.digest() for h, s in sorted(self.standardisers.items())
            },
            "development_scales": {
                str(h): {unit: scale.digest() for unit, scale in sorted(scales.items())}
                for h, scales in sorted(self.development_scales.items())
            },
            "hormuz_scale": self.hormuz_scale.digest(),
        }
        return hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()


@dataclass(frozen=True)
class FrozenSystem:
    states: dict[str, StateSystem]
    thresholds: tuple[FrozenThreshold, ...]

    def digest(self) -> str:
        payload = {
            "states": {name: system.digest() for name, system in sorted(self.states.items())},
            "thresholds": [
                [item.model, item.horizon_days, item.form, repr(item.threshold)]
                for item in self.thresholds
            ],
        }
        return hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()


def build_state_system(
    spec: Mapping,
    panel: pd.DataFrame,
    state: str,
    *,
    alpha_by_horizon: Mapping[int, float],
    lock: TuningLock,
) -> StateSystem:
    """Fit the deployment-time system for one state, entirely pre-surveillance.

    The model is the last frozen rolling fold's model.  A4 does not invent a new
    fit window: the fold geometry is frozen, the final fold is the most recent
    system that geometry defines, and its residuals are part of the calibration
    the accepted thresholds were set on.  The Hormuz context scale follows its
    own pinned rule and is fitted once through 2025-11-30.
    """
    lock.assert_estimation_allowed(f"building the {state} system")

    columns = feature_columns(spec)
    fold = rolling_origin_folds(spec)[-1]
    horizons = [int(value) for value in spec["tasks"]["horizons_days"]]

    models: dict[int, RidgeGlobalModel] = {}
    standardisers: dict[int, TrainingOnlyStandardizer] = {}
    development: dict[int, dict[str, object]] = {}
    for horizon in horizons:
        fit_end = fold.score_start - pd.Timedelta(days=horizon)
        scales = fold_context_scales(
            panel, spec, measurement_state=state, context_end=fit_end
        )
        geometry = build_rolling_fit_geometry(spec, fold, horizon, state)
        rows = materialize_task_features(panel, geometry, spec)
        assert_task_access(rows, "fitting", spec)
        normalised = apply_context_normalisation(rows, scales, spec)

        standardiser = TrainingOnlyStandardizer.fit(normalised, columns, spec)
        models[horizon] = RidgeGlobalModel.fit(
            standardiser.transform(normalised, spec),
            columns,
            spec,
            horizon_days=horizon,
            alpha=float(alpha_by_horizon[horizon]),
        )
        standardisers[horizon] = standardiser
        development[horizon] = scales

    hormuz_scale = fit_context_scale(
        panel[spec["population"]["hormuz_unit"]],
        spec,
        measurement_state=state,
        context_start=spec["model"]["context_normalisation"]["context_start"],
        context_end=spec["scaling"]["context_end"],
    )
    return StateSystem(
        state=state,
        fold_id=fold.fold_id,
        models=models,
        standardisers=standardisers,
        development_scales=development,
        hormuz_scale=hormuz_scale,
    )




def score_hormuz(
    spec: Mapping,
    panel: pd.DataFrame,
    system: StateSystem,
    *,
    outcome_state: str,
    detector_state: str,
    mode: str,
    lock: TuningLock,
) -> pd.DataFrame:
    """Score Hormuz surveillance days under one detector/outcome pairing.

    `detector_state` names the state the system was fitted on and
    `outcome_state` the state supplying the outcomes.  They differ only in the
    transport mode, where the July detector -- its July Hormuz context scale
    included -- is applied to August outcomes.  Reusing the frozen July object
    is exactly what makes that a transport test rather than a refit.
    """
    if not lock.hormuz_surveillance_read:
        raise AssertionError(
            "scoring reached Hormuz without the surveillance latch being set; "
            "the no-tuning seal would not be enforced"
        )

    columns = feature_columns(spec)
    hormuz = spec["population"]["hormuz_unit"]
    geometry = build_hormuz_scoring_geometry(spec, outcome_state)
    rows = materialize_task_features(panel, geometry, spec)

    scales = {hormuz: system.hormuz_scale}
    normalised = apply_context_normalisation(rows, scales, spec)

    frames: list[pd.DataFrame] = []
    for horizon in sorted(system.models):
        subset = normalised.loc[normalised["horizon_days"].eq(horizon)]
        if subset.empty:
            continue
        standardised = apply_frozen_standardiser(
            system.standardisers[horizon],
            subset,
            spec,
            detector_state=detector_state,
            outcome_state=outcome_state,
        )
        z_prediction = system.models[horizon].predict(standardised)
        block = subset.loc[
            :, ["unit", "horizon_days", "target_timestamp", "feature_timestamp", "y_target"]
        ].copy()
        block["model"] = RIDGE_MODEL
        block["prediction"] = denormalise(z_prediction, block["unit"], scales)
        frames.append(block)

    seasonal = normalised.loc[
        :, ["unit", "horizon_days", "target_timestamp", "feature_timestamp", "y_target"]
    ].copy()
    seasonal["model"] = SEASONAL_NAIVE
    seasonal["prediction"] = seasonal_naive_predictions(panel, seasonal)
    frames.append(seasonal)

    scored = pd.concat(frames, ignore_index=True)
    scored["mode"] = mode
    scored["detector_state"] = detector_state
    scored["outcome_state"] = outcome_state
    scored["context_scale"] = float(system.hormuz_scale.scale)
    scored[RAW_LEVEL] = raw_level_score(
        scored["prediction"].to_numpy(dtype="float64"),
        scored["y_target"].to_numpy(dtype="float64"),
    )
    scored[SCALE_INVARIANT] = scale_invariant_score(
        scored["prediction"].to_numpy(dtype="float64"),
        scored["y_target"].to_numpy(dtype="float64"),
        scored["context_scale"].to_numpy(dtype="float64"),
    )
    return scored.sort_values(
        ["model", "horizon_days", "target_timestamp"], kind="mergesort"
    ).reset_index(drop=True)


def apply_frozen_standardiser(
    standardiser: TrainingOnlyStandardizer,
    tasks: pd.DataFrame,
    spec: Mapping,
    *,
    detector_state: str,
    outcome_state: str,
) -> pd.DataFrame:
    """Standardise scoring rows, permitting the declared cross-state transport.

    `TrainingOnlyStandardizer.transform` refuses to *silently* transform a state
    it was not fitted on, and that seal is right: an accidental cross-state
    application is exactly the kind of mixing the A1 contract exists to stop.

    Plan v1.2 A4 mode 3 asks for one deliberate exception -- the frozen July
    scale-invariant detector transported to August -- and a transport test is
    the one operation that cannot satisfy the seal, because applying the July
    objects to August outcomes is the whole point of it.

    So the exception is made here, explicitly and narrowly, rather than by
    loosening the sealed class:

    * When the states match, the sealed `transform` is called and nothing is
      bypassed.  Modes 1, 2 and 4 all take that path.
    * When they differ, this applies the frozen means and scales directly.  The
      task table is still validated, no row is relabelled, and the frame keeps
      its true `measurement_state`, so the artefacts never claim August rows
      were July.  The **only** thing skipped is the state-equality check, and
      only for a pairing the caller named.

    Any cross-state application that is not routed through here still raises.
    """
    if detector_state == outcome_state:
        return standardiser.transform(tasks, spec)

    validate_task_table(tasks, spec)
    observed = str(tasks["measurement_state"].iloc[0])
    if observed != outcome_state:
        raise MeasurementStateError(
            f"transport declared {outcome_state!r} outcomes but the rows carry {observed!r}"
        )
    if standardiser.measurement_state != detector_state:
        raise MeasurementStateError(
            f"transport declared a {detector_state!r} detector but the standardiser "
            f"was fitted on {standardiser.measurement_state!r}"
        )

    output = tasks.copy()
    for column, mean, scale in zip(
        standardiser.feature_columns, standardiser.means, standardiser.scales
    ):
        output[column] = (pd.to_numeric(output[column], errors="raise") - mean) / scale
    return output


@dataclass(frozen=True)
class AlarmOutcome:
    fired: bool
    alarm_date: pd.Timestamp | None
    delay_days: float | None
    episodes: int
    exceedance_days: int
    severity_7_day: float
    severity_30_day: float


def first_alarm(
    dates: pd.DatetimeIndex,
    scores: np.ndarray,
    spec: Mapping,
    threshold: float,
) -> AlarmOutcome:
    """Apply the frozen episode machine and report the first alarm and severity.

    Severity is the mean nonconformity score over the 7 and 30 days from the
    alarm, in the score's own units, so the raw-level and scale-invariant forms
    each report severity on their own scale and are not comparable across forms.
    """
    episodes_cfg = spec["detector"]["episodes"]
    onset = int(episodes_cfg["alarm_begins_after_consecutive_exceedances"])
    quiet = int(episodes_cfg["quiet_days_required_for_new_episode"])
    exceeds = scores > threshold

    episodes, _, _ = count_episodes(
        scores, np.array([threshold]), segment_boundaries(dates), onset=onset, quiet_days=quiet
    )

    alarm_index: int | None = None
    run = 0
    for position, flag in enumerate(exceeds):
        run = run + 1 if flag else 0
        if run >= onset:
            alarm_index = position - onset + 1
            break

    if alarm_index is None:
        return AlarmOutcome(
            fired=False,
            alarm_date=None,
            delay_days=None,
            episodes=int(episodes[0]),
            exceedance_days=int(exceeds.sum()),
            severity_7_day=float("nan"),
            severity_30_day=float("nan"),
        )

    onset_date = pd.Timestamp(spec["dates"]["operational_onset"])
    alarm_date = pd.Timestamp(dates[alarm_index])
    return AlarmOutcome(
        fired=True,
        alarm_date=alarm_date,
        delay_days=float((alarm_date - onset_date).days),
        episodes=int(episodes[0]),
        exceedance_days=int(exceeds.sum()),
        severity_7_day=float(np.mean(scores[alarm_index : alarm_index + 7])),
        severity_30_day=float(np.mean(scores[alarm_index : alarm_index + 30])),
    )




def proportional_constant(july: np.ndarray, august: np.ndarray) -> float:
    """Least-squares constant `c` minimising ||august - c*july|| through the origin."""
    july = np.asarray(july, dtype="float64")
    august = np.asarray(august, dtype="float64")
    denominator = float(july @ july)
    if denominator <= 0.0:
        raise ValueError("the proportional constant is undefined on an all-zero series")
    return float((july @ august) / denominator)


def decompose_revision(
    july: pd.Series,
    august: pd.Series,
    *,
    fit_end: pd.Timestamp,
) -> tuple[float, pd.DataFrame]:
    """Split the July-to-August revision into proportional and residual parts.

    The constant is estimated on the pre-surveillance overlap alone, so the
    decomposition of the surveillance window is out of sample with respect to
    it.  The scale-invariant detector is invariant to the proportional component
    by construction, so only the residual component can move it -- which is why
    the two are reported apart.
    """
    overlap = july.index.intersection(august.index)
    fit_dates = overlap[overlap <= pd.Timestamp(fit_end)]
    if len(fit_dates) == 0:
        raise ValueError("no pre-surveillance overlap to estimate the proportional constant on")

    constant = proportional_constant(
        july.loc[fit_dates].to_numpy(dtype="float64"),
        august.loc[fit_dates].to_numpy(dtype="float64"),
    )
    frame = pd.DataFrame(
        {
            "date": overlap,
            "july_outcome": july.loc[overlap].to_numpy(dtype="float64"),
            "august_outcome": august.loc[overlap].to_numpy(dtype="float64"),
        }
    )
    frame["proportional_component"] = constant * frame["july_outcome"]
    frame["residual_revision"] = frame["august_outcome"] - frame["proportional_component"]
    frame["pre_surveillance"] = frame["date"] <= pd.Timestamp(fit_end)
    return constant, frame


__all__ = [
    "AUGUST",
    "CONSUMER",
    "JULY",
    "RIDGE_MODEL",
    "SEASONAL_NAIVE",
    "A4GateError",
    "AlarmOutcome",
    "FrozenSystem",
    "FrozenThreshold",
    "PostHormuzTuningError",
    "StateSystem",
    "TuningLock",
    "apply_frozen_standardiser",
    "build_state_system",
    "decompose_revision",
    "first_alarm",
    "load_accepted_thresholds",
    "load_measurement_state_panel",
    "proportional_constant",
    "score_hormuz",
    "verify_accepted_a3",
]
