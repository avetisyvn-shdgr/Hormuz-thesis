"""Shared-placebo inference contract for corridor deviations.

This module builds an aligned joint null for Romano-Wolf correction. It does not
construct prediction intervals or basin confidence intervals. Long-form input is
required so shared placebo origins and family membership remain auditable.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from . import config
from .corridor_admission import load_corridor_admission_protocol
from .inference import romano_wolf_stepdown


@dataclass(frozen=True)
class CorridorInferenceProtocol:
    status: str
    history_start: pd.Timestamp
    cutoff: pd.Timestamp
    family_name: str
    model: str
    statistic: str
    sign: str
    alternative: str
    studentize: bool
    post_horizon_days: int
    minimum_scored_days_per_window: int
    primary_placebo_design: str
    expected_joint_draws: int
    shared_placebo_origins: tuple[pd.Timestamp, ...]
    overlapping_placebo_policy: str
    basin_interval_policy: str
    basin_reference_distribution_label: str
    eligible_corridors: dict[str, tuple[str, ...]]

    @property
    def hypotheses(self) -> tuple[str, ...]:
        return tuple(
            _hypothesis_name(self.model, target, corridor)
            for target, corridors in sorted(self.eligible_corridors.items())
            for corridor in corridors
        )

    @property
    def finite_sample_p_value_floor(self) -> float:
        return 1.0 / (self.expected_joint_draws + 1.0)


def load_corridor_inference_protocol(
    path: str | Path | None = None,
) -> CorridorInferenceProtocol:
    """Load and validate the inference block of the corridor YAML."""
    source = Path(path) if path is not None else config.CONFIG_DIR / "corridor_transmission.yaml"
    raw = yaml.safe_load(source.read_text(encoding="utf-8"))
    inference = raw["inference"]
    admission = load_corridor_admission_protocol(source)
    protocol = CorridorInferenceProtocol(
        status=str(inference["status"]),
        history_start=admission.history_start,
        cutoff=admission.cutoff,
        family_name=str(inference["family_name"]),
        model=str(inference["model"]),
        statistic=str(inference["statistic"]),
        sign=str(inference["sign"]),
        alternative=str(inference["alternative"]),
        studentize=bool(inference["studentize"]),
        post_horizon_days=int(inference["post_horizon_days"]),
        minimum_scored_days_per_window=int(
            inference["minimum_scored_days_per_window"]
        ),
        primary_placebo_design=str(inference["primary_placebo_design"]),
        expected_joint_draws=int(inference["expected_joint_draws"]),
        shared_placebo_origins=tuple(
            pd.Timestamp(value) for value in inference["shared_placebo_origins"]
        ),
        overlapping_placebo_policy=str(
            inference["overlapping_30_day_step_placebos"]
        ),
        basin_interval_policy=str(inference["basin_interval_policy"]),
        basin_reference_distribution_label=str(
            inference["basin_reference_distribution_label"]
        ),
        eligible_corridors=admission.eligible_corridors,
    )
    _validate_protocol(protocol)
    return protocol


def _validate_protocol(protocol: CorridorInferenceProtocol) -> None:
    if protocol.model != "ar_lag1_7":
        raise ValueError("the primary corridor inference family must remain AR-only.")
    if protocol.statistic != "mean_scaled_signed_deviation":
        raise ValueError("unsupported corridor inference statistic.")
    if protocol.sign != "observed_minus_counterfactual":
        raise ValueError("unsupported corridor statistic sign convention.")
    if protocol.alternative != "two-sided":
        raise ValueError("corridor maps require the pre-registered two-sided alternative.")
    if protocol.post_horizon_days <= 0 or protocol.expected_joint_draws <= 1:
        raise ValueError("horizon must be positive and at least two joint draws are required.")
    if not 0 < protocol.minimum_scored_days_per_window <= protocol.post_horizon_days:
        raise ValueError("minimum scored days must be in (0, post_horizon_days].")
    if len(protocol.shared_placebo_origins) != protocol.expected_joint_draws:
        raise ValueError("shared-placebo count does not equal expected_joint_draws.")
    if tuple(sorted(set(protocol.shared_placebo_origins))) != protocol.shared_placebo_origins:
        raise ValueError("shared placebo origins must be unique and chronological.")
    prior_end: pd.Timestamp | None = None
    for origin in protocol.shared_placebo_origins:
        end = origin + pd.Timedelta(days=protocol.post_horizon_days - 1)
        if end >= protocol.cutoff:
            raise ValueError("a shared placebo window reaches the treatment cutoff.")
        if prior_end is not None and origin <= prior_end:
            raise ValueError("primary shared placebo windows must not overlap.")
        prior_end = end
    if protocol.primary_placebo_design != "non_overlapping_shared_origins":
        raise ValueError("primary placebo design must use non-overlapping shared origins.")
    if protocol.overlapping_placebo_policy != "sensitivity_only":
        raise ValueError("overlapping placebos may be used only as sensitivity.")
    if protocol.basin_interval_policy != "point_only":
        raise ValueError("basin intervals are not authorized by this protocol.")
    if len(protocol.hypotheses) != len(set(protocol.hypotheses)):
        raise ValueError("inference hypotheses must be unique.")


def mean_scaled_signed_deviation(
    observed,
    counterfactual,
    *,
    pre_period_mean: float,
) -> float:
    """Mean observed-minus-counterfactual deviation scaled by pre-period mean."""
    obs = pd.Series(observed, dtype="float64")
    pred = pd.Series(counterfactual, dtype="float64")
    if len(obs) != len(pred):
        raise ValueError("observed and counterfactual must have the same length.")
    if not np.isfinite(pre_period_mean) or pre_period_mean <= 0:
        raise ValueError("pre_period_mean must be finite and positive.")
    valid = np.isfinite(obs.to_numpy()) & np.isfinite(pred.to_numpy())
    if not valid.any():
        raise ValueError("no finite observed/counterfactual pairs.")
    return float(np.mean(obs.to_numpy()[valid] - pred.to_numpy()[valid]) / pre_period_mean)


def build_shared_placebo_matrix(
    statistics: pd.DataFrame,
    protocol: CorridorInferenceProtocol,
) -> pd.DataFrame:
    """Validate long-form placebo statistics and return origin × hypothesis draws."""
    _validate_protocol(protocol)
    _validate_long_statistics(statistics, protocol, is_placebo=True)
    frame = statistics.copy()
    frame["placebo_start"] = pd.to_datetime(frame["placebo_start"])
    frame["hypothesis"] = frame.apply(
        lambda row: _hypothesis_name(row["model"], row["target"], row["corridor"]),
        axis=1,
    )
    joint = frame.pivot(
        index="placebo_start",
        columns="hypothesis",
        values="statistic_value",
    )
    joint = joint.reindex(
        index=protocol.shared_placebo_origins,
        columns=protocol.hypotheses,
    )
    if joint.isna().any().any() or not np.isfinite(joint.to_numpy()).all():
        raise ValueError("shared placebo matrix must be finite and complete.")
    joint.index.name = "placebo_start"
    joint.columns.name = "hypothesis"
    return joint


def build_observed_statistics(
    statistics: pd.DataFrame,
    protocol: CorridorInferenceProtocol,
) -> pd.Series:
    """Validate one observed statistic per frozen hypothesis."""
    _validate_protocol(protocol)
    _validate_long_statistics(statistics, protocol, is_placebo=False)
    frame = statistics.copy()
    frame["hypothesis"] = frame.apply(
        lambda row: _hypothesis_name(row["model"], row["target"], row["corridor"]),
        axis=1,
    )
    observed = frame.set_index("hypothesis")["statistic_value"].reindex(
        protocol.hypotheses
    )
    if observed.isna().any() or not np.isfinite(observed.to_numpy()).all():
        raise ValueError("observed corridor statistics must be finite and complete.")
    return observed


def corridor_romano_wolf(
    observed_statistics: pd.DataFrame,
    placebo_statistics: pd.DataFrame,
    protocol: CorridorInferenceProtocol,
) -> pd.DataFrame:
    """Run the frozen family correction and attach its design limitations."""
    observed = build_observed_statistics(observed_statistics, protocol)
    joint = build_shared_placebo_matrix(placebo_statistics, protocol)
    result = romano_wolf_stepdown(
        observed,
        joint,
        alternative=protocol.alternative,
        studentize=protocol.studentize,
    )
    result.insert(0, "family", protocol.family_name)
    result["statistic"] = protocol.statistic
    result["sign"] = protocol.sign
    result["placebo_design"] = protocol.primary_placebo_design
    result["finite_sample_p_value_floor"] = protocol.finite_sample_p_value_floor
    result["basin_interval_policy"] = protocol.basin_interval_policy
    return result


def _validate_long_statistics(
    statistics: pd.DataFrame,
    protocol: CorridorInferenceProtocol,
    *,
    is_placebo: bool,
) -> None:
    required = {
        "model", "target", "corridor", "statistic_value", "n_scored",
        "train_start", "train_end",
    }
    if is_placebo:
        required |= {"placebo_start", "placebo_end"}
    else:
        required |= {"window_start", "window_end"}
    missing = required - set(statistics.columns)
    if missing:
        raise KeyError(f"corridor statistics missing columns: {sorted(missing)}.")
    frame = statistics.copy()
    if not frame["model"].eq(protocol.model).all():
        raise ValueError("statistics contain a model outside the frozen AR-only family.")
    if not np.isfinite(frame["statistic_value"]).all():
        raise ValueError("corridor statistics must be finite.")
    if (
        frame["n_scored"].lt(protocol.minimum_scored_days_per_window).any()
        or frame["n_scored"].gt(protocol.post_horizon_days).any()
    ):
        raise ValueError("n_scored violates the frozen window-completeness rule.")
    frame["train_start"] = pd.to_datetime(frame["train_start"])
    frame["train_end"] = pd.to_datetime(frame["train_end"])
    if not frame["train_start"].eq(protocol.history_start).all():
        raise ValueError("statistics do not use the frozen expanding-history start.")

    expected_members = {
        (target, corridor)
        for target, corridors in protocol.eligible_corridors.items()
        for corridor in corridors
    }
    actual_members = set(zip(frame["target"], frame["corridor"]))
    if actual_members != expected_members:
        raise ValueError("statistics do not match the frozen multiplicity family.")

    if is_placebo:
        frame["placebo_start"] = pd.to_datetime(frame["placebo_start"])
        frame["placebo_end"] = pd.to_datetime(frame["placebo_end"])
        keys = ["target", "corridor", "placebo_start"]
        if frame.duplicated(keys).any():
            raise ValueError("duplicate corridor-placebo rows are not allowed.")
        expected_rows = len(protocol.hypotheses) * protocol.expected_joint_draws
        if len(frame) != expected_rows:
            raise ValueError("placebo rows do not form the complete frozen joint design.")
        if set(frame["placebo_start"]) != set(protocol.shared_placebo_origins):
            raise ValueError("placebo origins do not match the frozen shared origins.")
        expected_end = frame["placebo_start"] + pd.Timedelta(
            days=protocol.post_horizon_days - 1
        )
        if not frame["placebo_end"].eq(expected_end).all():
            raise ValueError("placebo rows do not use the frozen horizon.")
        expected_train_end = frame["placebo_start"] - pd.Timedelta(days=1)
        if not frame["train_end"].eq(expected_train_end).all():
            raise ValueError("placebo training must end immediately before its origin.")
    else:
        frame["window_start"] = pd.to_datetime(frame["window_start"])
        frame["window_end"] = pd.to_datetime(frame["window_end"])
        if not frame["window_start"].eq(protocol.cutoff).all():
            raise ValueError("observed windows must begin at the frozen cutoff.")
        expected_window_end = protocol.cutoff + pd.Timedelta(
            days=protocol.post_horizon_days - 1
        )
        if not frame["window_end"].eq(expected_window_end).all():
            raise ValueError("observed rows do not use the frozen horizon.")
        if not frame["train_end"].eq(protocol.cutoff - pd.Timedelta(days=1)).all():
            raise ValueError("observed training must end before the frozen cutoff.")
        keys = ["target", "corridor"]
        if frame.duplicated(keys).any() or len(frame) != len(protocol.hypotheses):
            raise ValueError("need exactly one observed row per frozen hypothesis.")


def _hypothesis_name(model: str, target: str, corridor: str) -> str:
    return f"{model}::{target}::{corridor}"
