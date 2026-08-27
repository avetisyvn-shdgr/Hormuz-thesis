"""Phase A1 detector inputs: event-mask and context-scaling guards.

No threshold, alarm rule, or detector is calibrated here.  The module only
validates the frozen unit-day exclusion records and prepares leakage-safe
inputs for the later calibration phase.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
from typing import Mapping

import numpy as np
import pandas as pd
import yaml

from . import config
from .global_forecaster import (
    LeakageError,
    assert_task_access,
    development_units,
    sha256_file,
)


ALLOWED_EVENT_SOURCE_KINDS = frozenset(
    {"frozen_external_record", "frozen_repository_event_record"}
)


@dataclass(frozen=True)
class EventMask:
    unit_days: pd.DataFrame
    sha256: str
    source_sha256: tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class MaskApplication:
    eligible: pd.DataFrame
    excluded: pd.DataFrame


@dataclass(frozen=True)
class ContextScale:
    measurement_state: str
    center: float
    scale: float
    context_start: pd.Timestamp
    context_end: pd.Timestamp
    n_context: int
    method: str = "median_mad"

    def transform(self, values: pd.Series | np.ndarray) -> np.ndarray:
        return (np.asarray(values, dtype="float64") - self.center) / self.scale

    def digest(self) -> str:
        payload = {
            "measurement_state": self.measurement_state,
            "center": self.center,
            "scale": self.scale,
            "context_start": self.context_start.strftime("%Y-%m-%d"),
            "context_end": self.context_end.strftime("%Y-%m-%d"),
            "n_context": self.n_context,
            "method": self.method,
        }
        return hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()


def _event_mask_digest(frame: pd.DataFrame, sources: Mapping[str, str]) -> str:
    canonical = frame.copy()
    canonical["date"] = pd.to_datetime(canonical["date"]).dt.strftime("%Y-%m-%d")
    canonical = canonical.sort_values(["unit", "date"], kind="mergesort")
    payload = {
        "source_sha256": dict(sorted(sources.items())),
        "unit_days": canonical.to_dict(orient="records"),
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _source_unit_id(value: object) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(value).strip().lower()).strip("_")


def _bind_mask_record_to_source(
    record: Mapping,
    source_register: Mapping,
) -> None:
    event_id = str(record["event_id"])
    source_key = str(record.get("source_event_key", ""))
    events = source_register.get("events")
    if not source_key or not isinstance(events, Mapping) or source_key not in events:
        raise ValueError(
            f"event {event_id!r} does not identify a structured source event record"
        )
    source_event = events[source_key]
    if not isinstance(source_event, Mapping) or source_event.get("role") == "HELD_OUT":
        raise LeakageError(f"event {event_id!r} cannot bind to a held-out source event")

    declared_start = pd.Timestamp(record["start"])
    source_start = pd.Timestamp(source_event["onset"])
    if declared_start != source_start:
        raise ValueError(
            f"event {event_id!r} start does not match source event {source_key!r}"
        )
    declared_end_raw = record.get("end")
    source_end_raw = source_event.get("end")
    if (declared_end_raw is None) != (source_end_raw is None):
        raise ValueError(
            f"event {event_id!r} end does not match source event {source_key!r}"
        )
    if declared_end_raw is not None and pd.Timestamp(declared_end_raw) != pd.Timestamp(
        source_end_raw
    ):
        raise ValueError(
            f"event {event_id!r} end does not match source event {source_key!r}"
        )

    if "units" in source_event:
        source_units_raw = source_event["units"]
    elif "unit" in source_event:
        source_units_raw = [source_event["unit"]]
    else:
        raise ValueError(f"source event {source_key!r} has no formal affected-unit field")
    source_units = {_source_unit_id(value) for value in source_units_raw}
    declared_units = set(record.get("units", ()))
    if declared_units != source_units:
        raise ValueError(
            f"event {event_id!r} units do not match source event {source_key!r}: "
            f"expected {sorted(source_units)}, got {sorted(declared_units)}"
        )


def load_event_mask(
    spec: Mapping,
    *,
    root: Path = config.ROOT,
    verify_source_files: bool = True,
) -> EventMask:
    """Load and expand the frozen event records to unique unit-day exclusions."""
    cfg = spec["event_mask"]
    if cfg.get("status") != "frozen_before_detector_calibration":
        raise ValueError("event mask is not frozen before detector calibration")
    if cfg.get("unit_day_scope") is not True:
        raise ValueError("event mask must operate at unit-day resolution")
    if cfg.get("source_policy") != "frozen_external_or_event_records_only":
        raise ValueError("event mask source policy drifted")
    if cfg.get("residual_inference_prohibited") is not True:
        raise LeakageError("event mask must prohibit residual-derived exclusions")

    source_specs = cfg.get("sources", [])
    if not source_specs:
        raise ValueError("event mask requires at least one frozen source")
    sources: dict[str, dict] = {}
    source_hashes: dict[str, str] = {}
    source_registers: dict[str, Mapping] = {}
    for source in source_specs:
        source_id = str(source["source_id"])
        if source_id in sources:
            raise ValueError(f"duplicate event-mask source {source_id!r}")
        if source.get("kind") not in ALLOWED_EVENT_SOURCE_KINDS:
            raise ValueError(f"event-mask source {source_id!r} is not an allowed record kind")
        expected = str(source.get("sha256", ""))
        if len(expected) != 64:
            raise ValueError(f"event-mask source {source_id!r} lacks a SHA-256")
        path = root / source["path"]
        if not path.is_file():
            raise FileNotFoundError(f"event-mask source is missing: {source['path']}")
        if verify_source_files:
            actual = sha256_file(path)
            if actual != expected:
                raise ValueError(
                    f"event-mask source hash drift for {source_id}: expected {expected}, got {actual}"
                )
        sources[source_id] = dict(source)
        source_hashes[source_id] = expected
        source_register = yaml.safe_load(path.read_bytes())
        if not isinstance(source_register, Mapping) or source_register.get("status") != "frozen":
            raise ValueError(f"event-mask source {source_id!r} is not a frozen register")
        source_registers[source_id] = source_register

    coverage_end = pd.Timestamp(cfg["coverage_end"])
    allowed_units = set(development_units(spec))
    records = cfg.get("records", [])
    if not records:
        raise ValueError("event mask cannot be an undeclared empty mask")
    event_ids: set[str] = set()
    rows: list[dict[str, object]] = []
    for record in records:
        event_id = str(record["event_id"])
        if event_id in event_ids:
            raise ValueError(f"duplicate event-mask event_id {event_id!r}")
        event_ids.add(event_id)
        source_id = str(record["source_id"])
        if source_id not in sources:
            raise ValueError(f"event {event_id!r} references unknown source {source_id!r}")
        if record.get("residual_derived") is not False:
            raise LeakageError(
                f"event {event_id!r} is not explicitly sealed as non-residual-derived"
            )
        _bind_mask_record_to_source(record, source_registers[source_id])
        units = tuple(record.get("units", ()))
        if not units or not set(units).issubset(allowed_units):
            unknown = sorted(set(units).difference(allowed_units))
            raise ValueError(f"event {event_id!r} has empty/unknown units {unknown}")
        start = pd.Timestamp(record["start"])
        end = coverage_end if record.get("end") is None else pd.Timestamp(record["end"])
        if start > end or end > coverage_end:
            raise ValueError(f"event {event_id!r} has invalid mask dates")
        for unit in sorted(set(units)):
            for date in pd.date_range(start, end, freq="D"):
                rows.append(
                    {
                        "unit": unit,
                        "date": date,
                        "event_id": event_id,
                        "source_id": source_id,
                    }
                )

    expanded = pd.DataFrame.from_records(rows)
    grouped = (
        expanded.groupby(["unit", "date"], sort=True)
        .agg(
            event_ids=("event_id", lambda values: "|".join(sorted(set(values)))),
            source_ids=("source_id", lambda values: "|".join(sorted(set(values)))),
        )
        .reset_index()
    )
    if grouped.duplicated(["unit", "date"]).any():
        raise AssertionError("event mask expansion is not unique by unit-day")
    digest = _event_mask_digest(grouped, source_hashes)
    return EventMask(
        unit_days=grouped,
        sha256=digest,
        source_sha256=tuple(sorted(source_hashes.items())),
    )


def apply_event_mask(
    tasks: pd.DataFrame,
    mask: EventMask,
    *,
    timestamp_column: str = "target_timestamp",
) -> MaskApplication:
    """Exclude only matching unit-days; never remove a whole calendar date."""
    if "unit" not in tasks or timestamp_column not in tasks:
        raise KeyError("tasks require unit and target timestamp columns")
    original = tasks.copy()
    original["_mask_date"] = pd.to_datetime(original[timestamp_column]).dt.normalize()
    lookup = mask.unit_days.rename(columns={"date": "_mask_date"})
    merged = original.merge(
        lookup,
        on=["unit", "_mask_date"],
        how="left",
        validate="many_to_one",
        sort=False,
    )
    merged["event_masked"] = merged["event_ids"].notna()
    merged["event_ids"] = merged["event_ids"].fillna("")
    merged["event_source_ids"] = merged["source_ids"].fillna("")
    merged = merged.drop(columns=["_mask_date", "source_ids"])
    eligible = merged.loc[~merged["event_masked"]].reset_index(drop=True)
    excluded = merged.loc[merged["event_masked"]].reset_index(drop=True)
    _assert_unit_local_application(tasks, eligible, excluded, timestamp_column)
    return MaskApplication(eligible=eligible, excluded=excluded)


def _assert_unit_local_application(
    original: pd.DataFrame,
    eligible: pd.DataFrame,
    excluded: pd.DataFrame,
    timestamp_column: str,
) -> None:
    if len(eligible) + len(excluded) != len(original):
        raise AssertionError("event-mask application changed the task-row count")
    original_keys = set(
        zip(original["unit"], pd.to_datetime(original[timestamp_column]).dt.normalize())
    )
    eligible_keys = set(
        zip(eligible["unit"], pd.to_datetime(eligible[timestamp_column]).dt.normalize())
    )
    excluded_keys = set(
        zip(excluded["unit"], pd.to_datetime(excluded[timestamp_column]).dt.normalize())
    )
    if eligible_keys.intersection(excluded_keys):
        raise AssertionError("a unit-day is both eligible and excluded")
    if eligible_keys.union(excluded_keys) != original_keys:
        raise AssertionError("event-mask application removed an unmasked unit-day")


def validate_detector_calibration_tasks(tasks: pd.DataFrame, spec: Mapping) -> None:
    """Final A1 seal before a later phase may consume residuals for calibration."""
    assert_task_access(tasks, "detector_calibration", spec)


def fit_context_scale(
    series: pd.Series,
    spec: Mapping,
    *,
    measurement_state: str,
    context_start: str | pd.Timestamp | None = None,
    context_end: str | pd.Timestamp | None = None,
) -> ContextScale:
    """Fit a robust scale only on the declared pre-surveillance context."""
    if not isinstance(series.index, pd.DatetimeIndex):
        raise TypeError("context series must use a DatetimeIndex")
    if series.index.tz is not None or not series.index.is_monotonic_increasing:
        raise ValueError("context series index must be timezone-naive and chronological")
    if series.index.has_duplicates:
        raise ValueError("context series has duplicate dates")
    if measurement_state not in {
        key for key, value in spec["measurement_states"].items() if isinstance(value, Mapping)
    }:
        raise ValueError(f"unknown measurement state {measurement_state!r}")

    frozen_end = pd.Timestamp(spec["scaling"]["context_end"])
    chosen_end = frozen_end if context_end is None else pd.Timestamp(context_end)
    surveillance = pd.Timestamp(spec["dates"]["hormuz_surveillance_start"])
    if chosen_end > frozen_end or chosen_end >= surveillance:
        raise LeakageError(
            "context scaling may not read Hormuz surveillance or post-onset observations"
        )
    chosen_start = (
        pd.Timestamp(spec["dates"]["full_start"])
        if context_start is None
        else pd.Timestamp(context_start)
    )
    if chosen_start > chosen_end:
        raise ValueError("context scaling start is after its end")
    selected = pd.to_numeric(
        series.loc[(series.index >= chosen_start) & (series.index <= chosen_end)],
        errors="raise",
    ).dropna()
    if selected.empty or not np.isfinite(selected.to_numpy()).all():
        raise ValueError("context scaling requires finite pre-surveillance observations")
    center = float(selected.median())
    mad = float((selected - center).abs().median())
    scale = 1.4826 * mad
    if not np.isfinite(scale) or scale <= 0.0:
        fallback = float(selected.std(ddof=0))
        scale = fallback if np.isfinite(fallback) and fallback > 0.0 else 1.0
    return ContextScale(
        measurement_state=measurement_state,
        center=center,
        scale=scale,
        context_start=pd.Timestamp(selected.index.min()),
        context_end=pd.Timestamp(selected.index.max()),
        n_context=int(len(selected)),
    )
