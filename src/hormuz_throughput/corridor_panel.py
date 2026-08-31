"""Build and audit the frozen PortWatch corridor-transmission input panel."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from . import config
from .corridor_admission import load_corridor_admission_protocol
from .spatial import chokepoint_metadata, load_portwatch_snapshot, wide_chokepoint_panel
from .validation import rolling_origin_splits


@dataclass(frozen=True)
class CorridorPanelProtocol:
    status: str
    start: pd.Timestamp
    end: pd.Timestamp
    cutoff: pd.Timestamp
    history_policy: str
    targets: dict[str, str]
    outputs: dict[str, str]
    grouping_type: str
    aggregation_allowed: bool
    basin_mapping: dict[str, tuple[str, str]]
    eligible_corridors: dict[str, tuple[str, ...]]


def load_corridor_panel_protocol(
    transmission_path: str | Path | None = None,
    basin_path: str | Path | None = None,
) -> CorridorPanelProtocol:
    """Load the panel and operational-region mapping specifications."""
    transmission_source = (
        Path(transmission_path)
        if transmission_path is not None
        else config.CONFIG_DIR / "corridor_transmission.yaml"
    )
    basin_source = (
        Path(basin_path)
        if basin_path is not None
        else config.CONFIG_DIR / "corridor_basins.yaml"
    )
    raw = yaml.safe_load(transmission_source.read_text(encoding="utf-8"))
    basin = yaml.safe_load(basin_source.read_text(encoding="utf-8"))
    admission = load_corridor_admission_protocol(transmission_source)
    panel = raw["panel"]
    protocol = CorridorPanelProtocol(
        status=str(basin["status"]),
        start=admission.history_start,
        end=pd.Timestamp(panel["end_inclusive"]),
        cutoff=admission.cutoff,
        history_policy=str(panel["history_policy"]),
        targets={
            str(target): str(details["unit"])
            for target, details in panel["targets"].items()
        },
        outputs={str(key): str(value) for key, value in panel["outputs"].items()},
        grouping_type=str(basin["grouping_type"]),
        aggregation_allowed=bool(basin["aggregation_allowed"]),
        basin_mapping={
            str(corridor): (str(details["basin_group"]), str(details["note"]))
            for corridor, details in basin["mapping"].items()
        },
        eligible_corridors=admission.eligible_corridors,
    )
    _validate_protocol(protocol)
    return protocol


def _validate_protocol(protocol: CorridorPanelProtocol) -> None:
    if not protocol.start < protocol.cutoff <= protocol.end:
        raise ValueError("panel dates must satisfy start < cutoff <= end.")
    if protocol.history_policy != "common_2022_window_for_all_models":
        raise ValueError("unsupported corridor history policy.")
    if protocol.grouping_type != "operational_maritime_region":
        raise ValueError("corridor groups must remain operational maritime regions.")
    if protocol.aggregation_allowed:
        raise ValueError("corridor grouping must not authorize additive aggregation.")
    if set(protocol.targets) != set(protocol.eligible_corridors):
        raise ValueError("panel targets and admission target families must match.")
    configured_corridors = set().union(*map(set, protocol.eligible_corridors.values()))
    if set(protocol.basin_mapping) != configured_corridors:
        raise ValueError("basin mapping must cover exactly the configured corridors.")
    required_outputs = {"panel", "metadata", "quality", "audit", "manifest"}
    if set(protocol.outputs) != required_outputs:
        raise ValueError(f"panel outputs must be exactly {sorted(required_outputs)}.")


def build_corridor_panel(
    protocol: CorridorPanelProtocol,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[str, object]]:
    """Return long panel, metadata, pre-cutoff quality table and audit summary."""
    _validate_protocol(protocol)
    base_meta = chokepoint_metadata()
    raw = load_portwatch_snapshot()
    port_ids = raw[["portid", "portname"]].drop_duplicates()
    if port_ids["portname"].duplicated().any() or port_ids["portid"].duplicated().any():
        raise ValueError("PortWatch portid/portname mapping is not one-to-one.")
    metadata = base_meta.merge(port_ids, on="portname", how="left", validate="one_to_one")
    metadata["basin_group"] = metadata["slug"].map(
        {key: value[0] for key, value in protocol.basin_mapping.items()}
    )
    metadata["basin_assignment_note"] = metadata["slug"].map(
        {key: value[1] for key, value in protocol.basin_mapping.items()}
    )
    metadata["grouping_type"] = protocol.grouping_type
    metadata["aggregation_allowed"] = protocol.aggregation_allowed
    for target, corridors in protocol.eligible_corridors.items():
        metadata[f"eligible_{target}"] = metadata["slug"].isin(corridors)
    metadata = metadata[
        [
            "portid", "slug", "portname", "basin_group", "grouping_type",
            "aggregation_allowed", "basin_assignment_note", "contamination_flag",
            "contamination_note", *[f"eligible_{target}" for target in protocol.targets],
        ]
    ].sort_values("slug", ignore_index=True)

    long_parts: list[pd.DataFrame] = []
    for target, unit in protocol.targets.items():
        wide = wide_chokepoint_panel(
            target,
            start=str(protocol.start.date()),
            end=str(protocol.end.date()),
        )
        long = wide.rename_axis("date").reset_index().melt(
            id_vars="date", var_name="corridor", value_name="value"
        )
        long["target"] = target
        long["unit"] = unit
        long["is_pre_cutoff"] = long["date"].lt(protocol.cutoff)
        long["eligible_for_admission"] = long["corridor"].isin(
            protocol.eligible_corridors[target]
        )
        long_parts.append(long)
    panel = pd.concat(long_parts, ignore_index=True)
    panel = panel.merge(
        metadata[["slug", "portname", "basin_group"]],
        left_on="corridor",
        right_on="slug",
        how="left",
        validate="many_to_one",
    ).drop(columns="slug")
    panel = panel[
        [
            "date", "target", "unit", "corridor", "portname", "basin_group",
            "value", "is_pre_cutoff", "eligible_for_admission",
        ]
    ].sort_values(["target", "corridor", "date"], ignore_index=True)

    quality = _pre_cutoff_quality(panel)
    audit = _audit_panel(panel, metadata, quality, raw, protocol)
    return panel, metadata, quality, audit


def _pre_cutoff_quality(panel: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    pre = panel[panel["is_pre_cutoff"]]
    for (target, corridor), part in pre.groupby(["target", "corridor"], sort=True):
        values = part.sort_values("date")["value"]
        observed = values.dropna()
        zero = values.eq(0) & values.notna()
        run_ids = zero.ne(zero.shift(fill_value=False)).cumsum()
        zero_runs = zero.groupby(run_ids).sum()
        longest_zero_run = int(zero_runs.max()) if zero.any() else 0
        rows.append({
            "target": target,
            "corridor": corridor,
            "n_days_expected": int(len(values)),
            "n_observed": int(observed.size),
            "n_missing": int(values.isna().sum()),
            "missing_rate": float(values.isna().mean()),
            "n_zero_days": int(zero.sum()),
            "longest_zero_run_days": longest_zero_run,
            "pre_mean": float(observed.mean()),
            "pre_median": float(observed.median()),
            "pre_std": float(observed.std(ddof=1)),
            "pre_p05": float(observed.quantile(0.05)),
            "pre_p95": float(observed.quantile(0.95)),
            "pre_min": float(observed.min()),
            "pre_max": float(observed.max()),
        })
    return pd.DataFrame(rows).sort_values(["target", "corridor"], ignore_index=True)


def _audit_panel(
    panel: pd.DataFrame,
    metadata: pd.DataFrame,
    quality: pd.DataFrame,
    raw: pd.DataFrame,
    protocol: CorridorPanelProtocol,
) -> dict[str, object]:
    key = ["date", "target", "corridor"]
    duplicates = int(panel.duplicated(key).sum())
    expected_dates = int((protocol.end - protocol.start).days + 1)
    expected_rows = expected_dates * len(metadata) * len(protocol.targets)
    if duplicates:
        raise ValueError(f"corridor panel contains {duplicates} duplicate keys.")
    if len(panel) != expected_rows:
        raise ValueError(f"corridor panel has {len(panel)} rows; expected {expected_rows}.")
    if panel[["portname", "basin_group", "unit"]].isna().any().any():
        raise ValueError("corridor panel metadata contains missing values.")

    folds = rolling_origin_splits(
        pd.date_range(protocol.start, protocol.end, freq="D", name="date")
    )
    if any(fold.train_end >= protocol.cutoff or fold.test_end >= protocol.cutoff for fold in folds):
        raise AssertionError("a corridor validation fold reaches the treatment cutoff.")

    eligible_from_quality: dict[str, list[str]] = {}
    for target in protocol.targets:
        configured = list(protocol.eligible_corridors[target])
        observed = sorted(
            panel.loc[
                panel["target"].eq(target) & panel["eligible_for_admission"],
                "corridor",
            ].unique()
        )
        if observed != sorted(configured):
            raise ValueError(f"panel eligibility drift for target {target!r}.")
        eligible_from_quality[target] = configured

    raw_dates = pd.to_datetime(raw["date"], format="%Y/%m/%d")
    basin_counts = metadata.groupby("basin_group")["slug"].nunique().sort_index()
    missing_by_target = quality.groupby("target")["n_missing"].sum().sort_index()
    return {
        "schema_version": 1,
        "status": protocol.status,
        "history_policy": protocol.history_policy,
        "panel_start": str(protocol.start.date()),
        "panel_end": str(protocol.end.date()),
        "cutoff_exclusive": str(protocol.cutoff.date()),
        "raw_snapshot_start": str(raw_dates.min().date()),
        "raw_snapshot_end": str(raw_dates.max().date()),
        "raw_history_before_panel_start_is_intentionally_unused": True,
        "grouping_type": protocol.grouping_type,
        "aggregation_allowed": protocol.aggregation_allowed,
        "n_rows": int(len(panel)),
        "expected_rows": expected_rows,
        "n_dates": expected_dates,
        "n_corridors": int(metadata["slug"].nunique()),
        "n_targets": int(len(protocol.targets)),
        "n_duplicate_keys": duplicates,
        "n_pre_cutoff_rows": int(panel["is_pre_cutoff"].sum()),
        "n_post_cutoff_rows": int((~panel["is_pre_cutoff"]).sum()),
        "n_validation_folds": int(len(folds)),
        "last_validation_test_end": str(folds[-1].test_end.date()),
        "basin_group_corridor_counts": {
            key: int(value) for key, value in basin_counts.items()
        },
        "pre_cutoff_missing_values_by_target": {
            key: int(value) for key, value in missing_by_target.items()
        },
        "eligible_corridors": eligible_from_quality,
        "diagnostic_scope": "pre_cutoff_only",
    }
