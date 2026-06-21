"""Validated, panel-level admission gate for corridor TSFM candidates.

The gate consumes fold scores only. It does not fit models, inspect post-cutoff
outcomes or choose corridors. Candidate and AR-only rows must have identical
target/corridor/fold keys so model-specific dropping cannot improve a verdict.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from . import config


@dataclass(frozen=True)
class CorridorAdmissionProtocol:
    status: str
    history_start: pd.Timestamp
    cutoff: pd.Timestamp
    horizon_days: int
    minimum_scored_days_per_fold: int
    expected_scored_folds: int
    shared_test_origins: tuple[pd.Timestamp, ...]
    lower_quantile: float
    upper_quantile: float
    nominal_coverage: float
    baseline_model: str
    minimum_median_relative_mase_improvement: float
    minimum_fraction_corridors_non_worse_mase: float
    maximum_median_absolute_calibration_error: float
    calibration_noninferiority_margin: float
    minimum_corridor_empirical_coverage: float
    minimum_fraction_corridors_meeting_coverage: float
    require_every_target_family_to_pass: bool
    eligible_corridors: dict[str, tuple[str, ...]]


def load_corridor_admission_protocol(
    path: str | Path | None = None,
) -> CorridorAdmissionProtocol:
    """Load and validate the frozen corridor admission YAML."""
    source = Path(path) if path is not None else config.CONFIG_DIR / "corridor_transmission.yaml"
    raw = yaml.safe_load(source.read_text(encoding="utf-8"))
    validation = raw["validation"]
    interval = raw["interval"]
    gate = raw["gate"]
    protocol = CorridorAdmissionProtocol(
        status=str(raw["status"]),
        history_start=pd.Timestamp(raw["history"]["start"]),
        cutoff=pd.Timestamp(raw["history"]["cutoff_exclusive"]),
        horizon_days=int(validation["horizon_days"]),
        minimum_scored_days_per_fold=int(validation["minimum_scored_days_per_fold"]),
        expected_scored_folds=int(validation["expected_scored_folds"]),
        shared_test_origins=tuple(
            pd.Timestamp(value) for value in validation["shared_test_origins"]
        ),
        lower_quantile=float(interval["lower_quantile"]),
        upper_quantile=float(interval["upper_quantile"]),
        nominal_coverage=float(interval["nominal_coverage"]),
        baseline_model=str(gate["baseline_model"]),
        minimum_median_relative_mase_improvement=float(
            gate["minimum_median_relative_mase_improvement"]
        ),
        minimum_fraction_corridors_non_worse_mase=float(
            gate["minimum_fraction_corridors_non_worse_mase"]
        ),
        maximum_median_absolute_calibration_error=float(
            gate["maximum_median_absolute_calibration_error"]
        ),
        calibration_noninferiority_margin=float(
            gate["calibration_noninferiority_margin"]
        ),
        minimum_corridor_empirical_coverage=float(
            gate["minimum_corridor_empirical_coverage"]
        ),
        minimum_fraction_corridors_meeting_coverage=float(
            gate["minimum_fraction_corridors_meeting_coverage"]
        ),
        require_every_target_family_to_pass=bool(
            gate["require_every_target_family_to_pass"]
        ),
        eligible_corridors={
            str(target): tuple(str(corridor) for corridor in corridors)
            for target, corridors in raw["eligible_corridors"].items()
        },
    )
    _validate_protocol(protocol)
    return protocol


def _validate_protocol(protocol: CorridorAdmissionProtocol) -> None:
    if protocol.history_start >= protocol.cutoff:
        raise ValueError("history start must be strictly before the cutoff.")
    if protocol.horizon_days <= 0 or protocol.expected_scored_folds <= 0:
        raise ValueError("horizon and expected fold count must be positive.")
    if not 0 < protocol.minimum_scored_days_per_fold <= protocol.horizon_days:
        raise ValueError("minimum scored days must be in (0, horizon_days].")
    if len(protocol.shared_test_origins) != protocol.expected_scored_folds:
        raise ValueError("shared origin count does not equal expected_scored_folds.")
    if len(set(protocol.shared_test_origins)) != len(protocol.shared_test_origins):
        raise ValueError("shared test origins must be unique.")
    if tuple(sorted(protocol.shared_test_origins)) != protocol.shared_test_origins:
        raise ValueError("shared test origins must be chronological.")
    if protocol.shared_test_origins[-1] + pd.Timedelta(days=protocol.horizon_days) > protocol.cutoff:
        raise ValueError("a shared validation horizon reaches the treatment cutoff.")
    if not 0 <= protocol.lower_quantile < protocol.upper_quantile <= 1:
        raise ValueError("invalid interval quantiles.")
    if not np.isclose(
        protocol.upper_quantile - protocol.lower_quantile,
        protocol.nominal_coverage,
    ):
        raise ValueError("nominal coverage must equal upper minus lower quantile.")
    fractions = (
        protocol.minimum_fraction_corridors_non_worse_mase,
        protocol.minimum_fraction_corridors_meeting_coverage,
        protocol.minimum_corridor_empirical_coverage,
        protocol.maximum_median_absolute_calibration_error,
    )
    if any(not 0 <= value <= 1 for value in fractions):
        raise ValueError("coverage, calibration and fraction thresholds must be in [0, 1].")
    if protocol.minimum_median_relative_mase_improvement < 0:
        raise ValueError("minimum MASE improvement must be non-negative.")
    if protocol.calibration_noninferiority_margin < 0:
        raise ValueError("calibration noninferiority margin must be non-negative.")
    if not protocol.eligible_corridors:
        raise ValueError("at least one target family is required.")
    for target, corridors in protocol.eligible_corridors.items():
        if not corridors or len(set(corridors)) != len(corridors):
            raise ValueError(f"eligible corridors for {target!r} must be non-empty and unique.")


_REQUIRED_SCORE_COLUMNS = {
    "model",
    "target",
    "corridor",
    "fold",
    "train_start",
    "train_end",
    "test_start",
    "test_end",
    "n_scored",
    "mase",
    "empirical_coverage",
    "nominal_coverage",
}
_KEY_COLUMNS = ["target", "corridor", "fold", "test_start"]


def panel_admission_test(
    candidate_scores: pd.DataFrame,
    ar_scores: pd.DataFrame,
    protocol: CorridorAdmissionProtocol,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, object]]:
    """Apply one deterministic panel verdict to a candidate model.

    Returns corridor diagnostics, target-family verdicts and the overall verdict.
    Every configured target family must pass when the protocol requests it.
    """
    _validate_protocol(protocol)
    candidate, candidate_model = _validate_score_table(
        candidate_scores, protocol, expected_model=None, label="candidate"
    )
    baseline, baseline_model = _validate_score_table(
        ar_scores, protocol, expected_model=protocol.baseline_model, label="baseline"
    )
    if candidate_model == baseline_model:
        raise ValueError("candidate model must differ from the baseline model.")

    candidate_keys = pd.MultiIndex.from_frame(candidate[_KEY_COLUMNS])
    baseline_keys = pd.MultiIndex.from_frame(baseline[_KEY_COLUMNS])
    if not candidate_keys.equals(baseline_keys):
        missing_candidate = baseline_keys.difference(candidate_keys)
        missing_baseline = candidate_keys.difference(baseline_keys)
        raise ValueError(
            "candidate and baseline must contain identical corridor-fold keys; "
            f"missing candidate={len(missing_candidate)}, missing baseline={len(missing_baseline)}."
        )

    joined = candidate.merge(
        baseline,
        on=_KEY_COLUMNS,
        how="inner",
        suffixes=("_candidate", "_ar"),
        validate="one_to_one",
    )
    if not joined["n_scored_candidate"].equals(joined["n_scored_ar"]):
        raise ValueError("candidate and baseline n_scored must match on every fold.")

    rows: list[dict[str, object]] = []
    for (target, corridor), part in joined.groupby(["target", "corridor"], sort=True):
        cand_mase = float(part["mase_candidate"].mean())
        ar_mase = float(part["mase_ar"].mean())
        if ar_mase <= 0:
            raise ValueError(f"AR MASE must be positive for {target}/{corridor}.")
        weights = part["n_scored_candidate"].to_numpy(dtype="float64")
        cand_coverage = float(np.average(part["empirical_coverage_candidate"], weights=weights))
        ar_coverage = float(np.average(part["empirical_coverage_ar"], weights=weights))
        rows.append({
            "model": candidate_model,
            "target": target,
            "corridor": corridor,
            "n_folds": int(len(part)),
            "candidate_mase_mean": cand_mase,
            "ar_mase_mean": ar_mase,
            "relative_mase_improvement": (ar_mase - cand_mase) / ar_mase,
            "candidate_pooled_coverage": cand_coverage,
            "ar_pooled_coverage": ar_coverage,
            "candidate_absolute_calibration_error": abs(
                cand_coverage - protocol.nominal_coverage
            ),
            "ar_absolute_calibration_error": abs(
                ar_coverage - protocol.nominal_coverage
            ),
        })
    corridor_metrics = pd.DataFrame(rows).sort_values(
        ["target", "corridor"], ignore_index=True
    )

    target_rows: list[dict[str, object]] = []
    for target, part in corridor_metrics.groupby("target", sort=True):
        median_improvement = float(part["relative_mase_improvement"].median())
        fraction_non_worse = float(
            part["relative_mase_improvement"].map(lambda value: _at_least(value, 0)).mean()
        )
        cand_calibration = float(part["candidate_absolute_calibration_error"].median())
        ar_calibration = float(part["ar_absolute_calibration_error"].median())
        fraction_covered = float(
            part["candidate_pooled_coverage"]
            .map(lambda value: _at_least(
                value, protocol.minimum_corridor_empirical_coverage
            ))
            .mean()
        )
        mase_pass = bool(
            _at_least(
                median_improvement,
                protocol.minimum_median_relative_mase_improvement,
            )
            and _at_least(
                fraction_non_worse,
                protocol.minimum_fraction_corridors_non_worse_mase,
            )
        )
        calibration_pass = bool(
            _at_most(
                cand_calibration,
                protocol.maximum_median_absolute_calibration_error,
            )
            and _at_most(
                cand_calibration,
                ar_calibration + protocol.calibration_noninferiority_margin,
            )
            and _at_least(
                fraction_covered,
                protocol.minimum_fraction_corridors_meeting_coverage,
            )
        )
        target_rows.append({
            "model": candidate_model,
            "target": target,
            "n_corridors": int(len(part)),
            "median_relative_mase_improvement": median_improvement,
            "fraction_corridors_non_worse_mase": fraction_non_worse,
            "candidate_median_absolute_calibration_error": cand_calibration,
            "ar_median_absolute_calibration_error": ar_calibration,
            "fraction_corridors_meeting_coverage": fraction_covered,
            "mase_pass": mase_pass,
            "calibration_pass": calibration_pass,
            "target_admitted": bool(mase_pass and calibration_pass),
        })
    target_verdicts = pd.DataFrame(target_rows).sort_values("target", ignore_index=True)
    admitted = bool(target_verdicts["target_admitted"].all())
    if not protocol.require_every_target_family_to_pass:
        admitted = bool(target_verdicts["target_admitted"].any())
    overall = {
        "model": candidate_model,
        "baseline_model": baseline_model,
        "protocol_status": protocol.status,
        "n_target_families": int(len(target_verdicts)),
        "all_target_families_required": protocol.require_every_target_family_to_pass,
        "admitted": admitted,
        "verdict": (
            "ADMITTED by the frozen panel gate."
            if admitted
            else "NOT ADMITTED: at least one required target family failed."
        ),
    }
    return corridor_metrics, target_verdicts, overall


def _at_least(value: float, threshold: float) -> bool:
    """Inclusive threshold comparison robust to representation noise."""
    return bool(value > threshold or np.isclose(value, threshold, rtol=1e-12, atol=1e-12))


def _at_most(value: float, threshold: float) -> bool:
    """Inclusive upper-bound comparison robust to representation noise."""
    return bool(value < threshold or np.isclose(value, threshold, rtol=1e-12, atol=1e-12))


def _validate_score_table(
    scores: pd.DataFrame,
    protocol: CorridorAdmissionProtocol,
    *,
    expected_model: str | None,
    label: str,
) -> tuple[pd.DataFrame, str]:
    missing = _REQUIRED_SCORE_COLUMNS - set(scores.columns)
    if missing:
        raise KeyError(f"{label} scores missing columns: {sorted(missing)}.")
    frame = scores.copy()
    models = frame["model"].dropna().unique()
    if len(models) != 1:
        raise ValueError(f"{label} scores must contain exactly one model.")
    model = str(models[0])
    if expected_model is not None and model != expected_model:
        raise ValueError(f"{label} model must be {expected_model!r}, got {model!r}.")

    for column in ("train_start", "train_end", "test_start", "test_end"):
        frame[column] = pd.to_datetime(frame[column])
    frame = frame.sort_values(_KEY_COLUMNS, ignore_index=True)
    if frame.duplicated(_KEY_COLUMNS).any():
        raise ValueError(f"{label} scores contain duplicate corridor-fold keys.")
    if frame["test_end"].ge(protocol.cutoff).any():
        raise ValueError(f"{label} scores contain a fold reaching the cutoff.")
    if not frame["train_start"].eq(protocol.history_start).all():
        raise ValueError(f"{label} scores do not use the frozen expanding-history start.")
    if not frame["train_end"].lt(frame["test_start"]).all():
        raise ValueError(f"{label} scores contain overlapping train/test windows.")
    expected_test_end = frame["test_start"] + pd.Timedelta(
        days=protocol.horizon_days - 1
    )
    if not frame["test_end"].eq(expected_test_end).all():
        raise ValueError(f"{label} scores do not use the frozen test horizon.")
    if not np.isfinite(frame[["mase", "empirical_coverage", "nominal_coverage"]]).all().all():
        raise ValueError(f"{label} scores must contain finite metrics.")
    if not np.allclose(frame["nominal_coverage"], protocol.nominal_coverage):
        raise ValueError(f"{label} scores do not use the common nominal coverage.")
    if frame["n_scored"].lt(protocol.minimum_scored_days_per_fold).any():
        raise ValueError(f"{label} scores contain a fold below minimum scored days.")
    if frame["n_scored"].gt(protocol.horizon_days).any():
        raise ValueError(f"{label} n_scored exceeds the configured horizon.")
    if not frame["empirical_coverage"].between(0, 1).all():
        raise ValueError(f"{label} empirical coverage must be in [0, 1].")

    expected_rows: list[tuple[str, str, pd.Timestamp]] = []
    for target, corridors in protocol.eligible_corridors.items():
        for corridor in corridors:
            for origin in protocol.shared_test_origins:
                expected_rows.append((target, corridor, origin))
    expected = pd.MultiIndex.from_tuples(
        expected_rows, names=["target", "corridor", "test_start"]
    )
    actual = pd.MultiIndex.from_frame(frame[["target", "corridor", "test_start"]])
    if len(actual) != len(expected) or set(actual) != set(expected):
        raise ValueError(
            f"{label} scores do not match the frozen targets, corridors and shared origins."
        )
    return frame, model
