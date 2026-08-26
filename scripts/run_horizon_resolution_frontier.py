"""Task 6: horizon/resolution inference frontier for the locked block design.

The locked primary block artifact selects disjoint reference windows out of a
30-calendar-day origin lattice. That is a restricted subsample of the feasible
partitions, so the reported block count -- and therefore the rank p-value floor
and the conformal coverage ceiling -- can be pessimistic for reasons that are
purely an implementation detail.

This script audits and extends that design without touching it. The block
geometry is fixed first, from the calendar alone, under origin rules frozen in
``config/horizon_resolution_frontier.yaml``. Only then is the locked AR(1,7)
specification applied to those blocks. Outcome, model, training cutoff, units,
and treated window are held fixed throughout; only the reference partition and
its resolution vary.

Nothing here is a significance test. With ``K`` reference blocks the smallest
attainable rank p-value is ``1 / (K + 1)``, which no cell in the frozen grid
brings to 0.05, and any confidence level whose order statistic exceeds ``K`` is
reported as an unbounded interval rather than silently clipped.

Run from the repo root:
    python scripts/run_horizon_resolution_frontier.py
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lngfreight import config  # noqa: E402
from lngfreight import horizon_frontier as hf  # noqa: E402
from lngfreight.baselines import arx_forecast  # noqa: E402
from lngfreight.inference import (  # noqa: E402
    conformal_effect_interval,
    counterfactual_effect,
    empirical_p_value,
)


DESIGN_PATH = config.CONFIG_DIR / "horizon_resolution_frontier.yaml"

BLOCK_COLUMNS = [
    "origin_rule",
    "role",
    "horizon_days",
    "block_index",
    "block_name",
    "is_treated_window",
    "test_start",
    "test_end",
    "train_start",
    "train_end",
    "n_train_days",
    "n_test_days",
    "observed_sum",
    "counterfactual_sum",
    "cumulative_throughput_loss",
    "mean_daily_throughput_loss",
]

SUMMARY_COLUMNS = [
    "origin_rule",
    "role",
    "horizon_days",
    "outcome",
    "model_id",
    "unit",
    "treated_start",
    "treated_end",
    "n_candidate_blocks_all_daily_origins",
    "packing_upper_bound",
    "n_reference_blocks",
    "blocks_forgone_vs_upper_bound",
    "attains_packing_upper_bound",
    "treated_cumulative_loss",
    "treated_mean_daily_loss",
    "reference_max_cumulative_loss",
    "reference_median_cumulative_loss",
    "rank_p_value_greater",
    "rank_p_value_floor",
    "rank_p_value_is_at_floor",
    "five_percent_floor_attainable",
    "five_percent_significance_claimed",
    "is_primary_reporting_resolution",
    "maximum_attainable_coverage",
    "level",
    "order_statistic_rank",
    "finite_interval_supported",
    "conformal_radius",
    "interval_lower",
    "interval_upper",
    "min_blocks_required_for_level",
    "additional_blocks_required_for_level",
]


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_design() -> tuple[dict, str]:
    raw = DESIGN_PATH.read_bytes()
    return yaml.safe_load(raw), hashlib.sha256(raw).hexdigest()


def output_path(design: dict, key: str) -> Path:
    return config.ROOT / design["outputs"][key]


def load_verified_inputs(design: dict) -> pd.DataFrame:
    """Verify every upstream hash, then return the estimation panel.

    The locked primary block artifacts are hash-checked but never read into the
    frontier: this phase must not be able to change them, and a drifted hash is
    a stop condition rather than something to reconcile.
    """
    for label, spec in design["upstream_locked_artifacts"].items():
        path = config.ROOT / spec["path"]
        if not path.is_file():
            raise FileNotFoundError(f"horizon-frontier upstream missing: {label}")
        actual = sha256_file(path)
        if actual != spec["sha256"]:
            raise ValueError(
                f"horizon-frontier upstream hash drift for {label}: {actual}"
            )

    panel = pd.read_csv(
        config.ROOT / design["upstream_locked_artifacts"]["panel_aligned"]["path"],
        parse_dates=["date"],
    ).set_index("date")
    validate_panel(panel, design)
    return panel


def validate_panel(panel: pd.DataFrame, design: dict) -> None:
    """Fail loudly if the panel cannot support the frozen fixed basis."""
    fixed = design["held_fixed"]
    outcome = fixed["outcome"]
    if outcome not in panel.columns:
        raise KeyError(f"panel lacks the frozen outcome column {outcome!r}")
    if not isinstance(panel.index, pd.DatetimeIndex):
        raise TypeError("panel must be indexed by a DatetimeIndex")
    if not panel.index.is_monotonic_increasing or panel.index.has_duplicates:
        raise ValueError("panel index must be strictly chronological")

    gaps = panel.index.to_series().diff().dropna()
    if not gaps.eq(pd.Timedelta(days=1)).all():
        raise ValueError(
            "horizon-frontier block geometry assumes a contiguous daily index"
        )
    if panel[outcome].isna().any():
        raise ValueError(f"frozen outcome {outcome!r} has missing days")
    if panel.index.min() != pd.Timestamp(fixed["panel_start"]):
        raise ValueError("panel start drifted from the frozen basis")
    if panel.index.max() < pd.Timestamp(fixed["treated_window_end"]):
        raise ValueError("panel ends before the frozen treated window")

    treated_days = (
        pd.Timestamp(fixed["treated_window_end"])
        - pd.Timestamp(fixed["treated_window_start"])
    ).days + 1
    if treated_days != int(fixed["treated_window_days"]):
        raise ValueError("frozen treated-window length is internally inconsistent")
    if max(design["horizon_grid_days"]) > treated_days:
        raise ValueError(
            "a horizon longer than the treated window cannot be scored; "
            "shorten horizon_grid_days"
        )
    if int(design["primary_horizon_days"]) not in design["horizon_grid_days"]:
        raise ValueError("primary_horizon_days must appear in horizon_grid_days")


def build_geometry(design: dict, panel: pd.DataFrame) -> pd.DataFrame:
    """Every reference block under every frozen rule -- calendar only.

    This function never touches the outcome column. It is written and validated
    separately from estimation precisely so that origin-rule choice cannot be
    contaminated by an observed result.
    """
    fixed = design["held_fixed"]
    cutoff = pd.Timestamp(fixed["training_cutoff_exclusive"])
    min_train = int(fixed["min_initial_train_days"])
    frames = []
    for rule in design["origin_rules"]:
        for horizon in design["horizon_grid_days"]:
            frames.append(
                hf.geometry_frame(
                    panel.index,
                    cutoff,
                    int(horizon),
                    min_train,
                    origin_rule=rule,
                )
            )
    geometry = pd.concat(frames, ignore_index=True)
    return geometry.sort_values(
        ["origin_rule", "horizon_days", "block_index"], kind="stable"
    ).reset_index(drop=True)


def _fit_block(panel: pd.DataFrame, design: dict, block: hf.Block) -> dict:
    """Score one block with the locked AR(1,7) specification."""
    fixed = design["held_fixed"]
    fold = hf.block_fold(panel.index, block)
    pred = arx_forecast(
        panel,
        target=fixed["outcome"],
        fold=fold,
        exog_cols=list(fixed["exog_cols"]),
        y_lags=tuple(int(lag) for lag in fixed["y_lags"]),
        ridge_alpha=float(fixed["ridge_alpha"]),
    )
    effect = counterfactual_effect(panel.loc[pred.index, fixed["outcome"]], pred)
    return {
        "train_start": fold.train_start.date().isoformat(),
        "train_end": fold.train_end.date().isoformat(),
        "n_train_days": int(len(fold.train_idx)),
        "n_test_days": int(len(fold.test_idx)),
        "observed_sum": float(effect["observed_sum"]),
        "counterfactual_sum": float(effect["counterfactual_sum"]),
        "cumulative_throughput_loss": float(effect["cumulative_throughput_loss"]),
        "mean_daily_throughput_loss": float(effect["mean_daily_throughput_loss"]),
    }


def treated_block(design: dict, horizon: int) -> hf.Block:
    """The treated window truncated to ``horizon`` days.

    The start date is always the locked operational-onset cutoff. A shorter
    horizon reports a strictly nested sub-window of the same treated period; it
    never moves the treatment date.
    """
    start = pd.Timestamp(design["held_fixed"]["treated_window_start"])
    return hf.Block(
        name=f"treated_{horizon:03d}d",
        start=start,
        end=start + pd.Timedelta(days=horizon - 1),
    )


def build_blocks(design: dict, panel: pd.DataFrame, geometry: pd.DataFrame) -> pd.DataFrame:
    """Attach the locked AR(1,7) statistic to the frozen geometry.

    Identical blocks shared by several origin rules are fitted once and reused,
    so the reported statistic cannot differ between rules for the same window.
    """
    fixed = design["held_fixed"]
    roles = {rule: spec["role"] for rule, spec in design["origin_rules"].items()}
    cache: dict[tuple[str, str], dict] = {}

    rows = []
    for horizon in design["horizon_grid_days"]:
        horizon = int(horizon)
        treated = treated_block(design, horizon)
        key = (treated.start.date().isoformat(), treated.end.date().isoformat())
        if key not in cache:
            cache[key] = _fit_block(panel, design, treated)
        rows.append({
            "origin_rule": "treated_window",
            "role": "treated",
            "horizon_days": horizon,
            "block_index": 0,
            "block_name": treated.name,
            "is_treated_window": True,
            "test_start": treated.start.date().isoformat(),
            "test_end": treated.end.date().isoformat(),
            **cache[key],
        })

    for record in geometry.to_dict("records"):
        block = hf.Block(
            name=str(record["block_name"]),
            start=pd.Timestamp(record["test_start"]),
            end=pd.Timestamp(record["test_end"]),
        )
        key = (record["test_start"], record["test_end"])
        if key not in cache:
            cache[key] = _fit_block(panel, design, block)
        fitted = cache[key]
        if fitted["n_train_days"] != int(record["n_train_days"]):
            raise AssertionError("geometry and estimation disagree on training span")
        rows.append({
            "origin_rule": record["origin_rule"],
            "role": roles[record["origin_rule"]],
            "horizon_days": int(record["horizon_days"]),
            "block_index": int(record["block_index"]),
            "block_name": record["block_name"],
            "is_treated_window": False,
            "test_start": record["test_start"],
            "test_end": record["test_end"],
            **fitted,
        })

    blocks = pd.DataFrame(rows, columns=BLOCK_COLUMNS)
    if blocks[["origin_rule", "horizon_days", "block_name"]].duplicated().any():
        raise AssertionError("duplicate block rows in the frontier block table")
    guard_treated_window(blocks, fixed)
    return blocks.sort_values(
        ["horizon_days", "origin_rule", "block_index"], kind="stable"
    ).reset_index(drop=True)


def guard_treated_window(blocks: pd.DataFrame, fixed: dict) -> None:
    """The treated window start and training cutoff must never move."""
    treated = blocks.loc[blocks["is_treated_window"]]
    if treated.empty:
        raise AssertionError("no treated-window row was scored")
    if not treated["test_start"].eq(fixed["treated_window_start"]).all():
        raise AssertionError("treated-window start moved across horizons")
    if not treated["train_end"].lt(fixed["training_cutoff_exclusive"]).all():
        raise AssertionError("treated-window training crossed the locked cutoff")
    reference = blocks.loc[~blocks["is_treated_window"]]
    if not reference["test_end"].lt(fixed["training_cutoff_exclusive"]).all():
        raise AssertionError("a reference block crossed the locked cutoff")


def build_summary(design: dict, panel: pd.DataFrame, blocks: pd.DataFrame) -> pd.DataFrame:
    """One row per origin rule, horizon, and requested confidence level."""
    fixed = design["held_fixed"]
    cutoff = pd.Timestamp(fixed["training_cutoff_exclusive"])
    min_train = int(fixed["min_initial_train_days"])
    levels = [float(level) for level in design["confidence_levels"]]
    roles = {rule: spec["role"] for rule, spec in design["origin_rules"].items()}

    rows = []
    for horizon in design["horizon_grid_days"]:
        horizon = int(horizon)
        treated_row = blocks.loc[
            blocks["is_treated_window"] & blocks["horizon_days"].eq(horizon)
        ].iloc[0]
        point = float(treated_row["cumulative_throughput_loss"])
        candidates = hf.enumerate_candidate_blocks(
            panel.index, cutoff, horizon, min_train
        )
        upper_bound = hf.packing_upper_bound(panel.index, cutoff, horizon, min_train)
        if len(hf.maximum_disjoint_packing(candidates)) != upper_bound:
            raise AssertionError(
                "optimal packing disagrees with the calendar bound; the block "
                "geometry is not internally consistent"
            )

        for rule in design["origin_rules"]:
            subset = blocks.loc[
                blocks["origin_rule"].eq(rule) & blocks["horizon_days"].eq(horizon)
            ]
            values = subset["cumulative_throughput_loss"].to_numpy(dtype="float64")
            n_blocks = len(values)
            capacity = hf.frontier_capacity(n_blocks, levels)
            p_value = empirical_p_value(point, values, alternative="greater")
            for level in levels:
                interval = conformal_effect_interval(
                    point, values, alpha=1.0 - level
                )
                required = hf.minimum_blocks_for_level(level)
                rows.append({
                    "origin_rule": rule,
                    "role": roles[rule],
                    "horizon_days": horizon,
                    "outcome": fixed["outcome"],
                    "model_id": fixed["model_id"],
                    "unit": fixed["unit"],
                    "treated_start": treated_row["test_start"],
                    "treated_end": treated_row["test_end"],
                    "n_candidate_blocks_all_daily_origins": len(candidates),
                    "packing_upper_bound": upper_bound,
                    "n_reference_blocks": n_blocks,
                    "blocks_forgone_vs_upper_bound": upper_bound - n_blocks,
                    "attains_packing_upper_bound": bool(n_blocks == upper_bound),
                    "treated_cumulative_loss": point,
                    "treated_mean_daily_loss": float(
                        treated_row["mean_daily_throughput_loss"]
                    ),
                    "reference_max_cumulative_loss": float(np.max(values)),
                    "reference_median_cumulative_loss": float(np.median(values)),
                    "rank_p_value_greater": p_value,
                    "rank_p_value_floor": capacity["rank_p_value_floor"],
                    "rank_p_value_is_at_floor": bool(
                        np.isclose(p_value, capacity["rank_p_value_floor"])
                    ),
                    "five_percent_floor_attainable": capacity[
                        "five_percent_floor_attainable"
                    ],
                    "five_percent_significance_claimed": False,
                    "is_primary_reporting_resolution": bool(
                        rule == hf.PRIMARY_RULE
                        and horizon == int(design["primary_horizon_days"])
                    ),
                    "maximum_attainable_coverage": capacity[
                        "maximum_attainable_coverage"
                    ],
                    "level": level,
                    "order_statistic_rank": int(interval["order_statistic_rank"]),
                    "finite_interval_supported": bool(
                        interval["finite_interval_supported"]
                    ),
                    "conformal_radius": float(interval["radius"]),
                    "interval_lower": float(interval["interval_lower"]),
                    "interval_upper": float(interval["interval_upper"]),
                    "min_blocks_required_for_level": required,
                    "additional_blocks_required_for_level": max(
                        0, required - n_blocks
                    ),
                })

    summary = pd.DataFrame(rows, columns=SUMMARY_COLUMNS)
    guard_summary(summary)
    return summary.sort_values(
        ["horizon_days", "origin_rule", "level"], kind="stable"
    ).reset_index(drop=True)


def guard_summary(summary: pd.DataFrame) -> None:
    """Structural invariants that must hold before anything is written."""
    if summary.empty:
        raise AssertionError("frontier summary is empty")
    if summary["rank_p_value_greater"].lt(summary["rank_p_value_floor"]).any():
        raise AssertionError("a rank p-value fell below its finite-sample floor")
    if summary["five_percent_significance_claimed"].any():
        raise AssertionError("no cell of this frontier may claim 5% significance")

    # A finer resolution mechanically lowers the 1/(K+1) floor. That is a
    # property of the reference partition, not evidence, so the primary
    # reporting resolution is fixed by the frozen design and may not be
    # swapped for whichever horizon produced the smallest floor.
    consistent = summary["five_percent_floor_attainable"].eq(
        summary["rank_p_value_floor"].le(0.05)
    )
    if not consistent.all():
        raise AssertionError("the 5% floor flag disagrees with 1/(K+1)")
    primary = summary.loc[summary["is_primary_reporting_resolution"]]
    if primary.empty:
        raise AssertionError("the frozen primary reporting cell is missing")
    if primary["five_percent_floor_attainable"].any():
        raise AssertionError(
            "the primary reporting resolution must not be described as capable "
            "of a 5% rank p-value"
        )
    finite = summary.loc[summary["finite_interval_supported"]]
    if not np.isfinite(finite["conformal_radius"]).all():
        raise AssertionError("a supported level carries a non-finite radius")
    unbounded = summary.loc[~summary["finite_interval_supported"]]
    if not np.isinf(unbounded["conformal_radius"]).all():
        raise AssertionError("an unsupported level carries a finite radius")
    if not unbounded.empty and not (
        np.isneginf(unbounded["interval_lower"]).all()
        and np.isposinf(unbounded["interval_upper"]).all()
    ):
        raise AssertionError("an unsupported level was silently clipped")
    if not summary["level"].gt(summary["maximum_attainable_coverage"]).eq(
        ~summary["finite_interval_supported"]
    ).all():
        raise AssertionError(
            "finite support disagrees with the maximum attainable coverage"
        )


def build_audit_expectation(design: dict, summary: pd.DataFrame) -> dict:
    """Reproduce-or-refute record for the stated audit expectation."""
    expected = design["audit_expectation"]
    cell = summary.loc[
        summary["origin_rule"].eq(expected["rule"])
        & summary["horizon_days"].eq(int(expected["horizon_days"]))
    ]
    if cell.empty:
        raise AssertionError("the audit-expectation cell is missing from the grid")

    observed_blocks = int(cell["n_reference_blocks"].iloc[0])
    observed_floor = float(cell["rank_p_value_floor"].iloc[0])
    finite_levels = sorted(
        float(level)
        for level in cell.loc[cell["finite_interval_supported"], "level"]
    )
    unbounded_levels = sorted(
        float(level)
        for level in cell.loc[~cell["finite_interval_supported"], "level"]
    )
    finite_radius = cell.loc[cell["finite_interval_supported"], "conformal_radius"]

    checks = {
        "n_reference_blocks": {
            "expected": int(expected["n_reference_blocks"]),
            "observed": observed_blocks,
            "reproduced": observed_blocks == int(expected["n_reference_blocks"]),
        },
        "rank_p_value_floor": {
            "expected": float(expected["rank_p_value_floor"]),
            "observed": observed_floor,
            "reproduced": bool(
                np.isclose(observed_floor, float(expected["rank_p_value_floor"]))
            ),
        },
        "finite_interval_levels": {
            "expected": [float(x) for x in expected["finite_interval_levels"]],
            "observed": finite_levels,
            "reproduced": finite_levels
            == [float(x) for x in expected["finite_interval_levels"]],
        },
        "unbounded_interval_levels": {
            "expected": [float(x) for x in expected["unbounded_interval_levels"]],
            "observed": unbounded_levels,
            "reproduced": unbounded_levels
            == [float(x) for x in expected["unbounded_interval_levels"]],
        },
        "finite_radius_is_finite": {
            "expected": True,
            "observed": bool(
                len(finite_radius) > 0 and np.isfinite(finite_radius).all()
            ),
            "reproduced": bool(
                len(finite_radius) > 0 and np.isfinite(finite_radius).all()
            ),
        },
    }
    return {
        "rule": expected["rule"],
        "horizon_days": int(expected["horizon_days"]),
        "checks": checks,
        "fully_reproduced": all(item["reproduced"] for item in checks.values()),
        "investigation_note": (
            "Direct one-horizon tiling from the locked anchor attains the "
            "calendar packing bound; the locked primary artifact reports fewer "
            "blocks because its candidate origins are coarsened to a 30-day "
            "lattice before the greedy disjoint pass."
        ),
    }


def build_diagnostics(
    design: dict,
    design_sha256: str,
    panel: pd.DataFrame,
    geometry: pd.DataFrame,
    blocks: pd.DataFrame,
    summary: pd.DataFrame,
) -> dict:
    fixed = design["held_fixed"]
    cutoff = pd.Timestamp(fixed["training_cutoff_exclusive"])
    min_train = int(fixed["min_initial_train_days"])
    primary = int(design["primary_horizon_days"])

    per_cell = []
    for (rule, horizon), group in summary.groupby(
        ["origin_rule", "horizon_days"], sort=True
    ):
        per_cell.append({
            "origin_rule": rule,
            "role": group["role"].iloc[0],
            "horizon_days": int(horizon),
            "n_reference_blocks": int(group["n_reference_blocks"].iloc[0]),
            "packing_upper_bound": int(group["packing_upper_bound"].iloc[0]),
            "blocks_forgone_vs_upper_bound": int(
                group["blocks_forgone_vs_upper_bound"].iloc[0]
            ),
            "rank_p_value_greater": float(group["rank_p_value_greater"].iloc[0]),
            "rank_p_value_floor": float(group["rank_p_value_floor"].iloc[0]),
            "five_percent_floor_attainable": bool(
                group["five_percent_floor_attainable"].iloc[0]
            ),
            "is_primary_reporting_resolution": bool(
                group["is_primary_reporting_resolution"].iloc[0]
            ),
            "maximum_attainable_coverage": float(
                group["maximum_attainable_coverage"].iloc[0]
            ),
            "finite_interval_levels": sorted(
                float(x) for x in group.loc[group["finite_interval_supported"], "level"]
            ),
            "unbounded_interval_levels": sorted(
                float(x)
                for x in group.loc[~group["finite_interval_supported"], "level"]
            ),
        })

    return {
        "design_id": design["design_id"],
        "design_sha256": design_sha256,
        "analysis_role": design["analysis_role"],
        "freeze_status": design["freeze_status"]["timing"],
        "held_fixed": {
            "outcome": fixed["outcome"],
            "unit": fixed["unit"],
            "model_id": fixed["model_id"],
            "y_lags": list(fixed["y_lags"]),
            "exog_cols": list(fixed["exog_cols"]),
            "training_cutoff_exclusive": fixed["training_cutoff_exclusive"],
            "treated_window_start": fixed["treated_window_start"],
            "treated_window_end": fixed["treated_window_end"],
            "min_initial_train_days": min_train,
        },
        "calendar": {
            "panel_start": panel.index.min().date().isoformat(),
            "panel_end": panel.index.max().date().isoformat(),
            "n_pre_cutoff_days": int((panel.index < cutoff).sum()),
            "anchor_origin": hf.anchor_origin(panel.index, min_train)
            .date()
            .isoformat(),
            "available_reference_days": hf.available_reference_days(
                panel.index, cutoff, min_train
            ),
        },
        "outcome_independent_geometry": {
            "geometry_rows": int(len(geometry)),
            "geometry_columns_contain_no_outcome_value": bool(
                not any(
                    "loss" in column or "observed" in column
                    for column in geometry.columns
                )
            ),
            "rules_are_calendar_functions_only": True,
        },
        "primary_cell": next(
            item
            for item in per_cell
            if item["origin_rule"] == hf.PRIMARY_RULE
            and item["horizon_days"] == primary
        ),
        "cells": per_cell,
        "reporting_guards": design["reporting_guards"],
    }


def _fmt(value: float, digits: int = 3) -> str:
    if not np.isfinite(value):
        return "unbounded"
    return f"{value:,.{digits}f}"


def render_markdown(
    design: dict,
    diagnostics: dict,
    summary: pd.DataFrame,
    audit: dict,
) -> str:
    fixed = design["held_fixed"]
    primary = int(design["primary_horizon_days"])
    primary_cell = diagnostics["primary_cell"]
    lines: list[str] = []
    add = lines.append

    add("# Horizon/resolution inference frontier")
    add("")
    add(f"**Design id:** `{design['design_id']}`  ")
    add(f"**Design SHA-256:** `{diagnostics['design_sha256']}`  ")
    add(f"**Frozen (UTC):** {design['frozen_utc']}  ")
    add(f"**Freeze status:** {design['freeze_status']['timing']}  ")
    add("**Verification status:** `NEEDS-VERIFY` until Mher runs the G4 commands.")
    add("")
    add(
        "This document audits and extends the block/placebo inference design. "
        "It reports what the pre-treatment calendar can support. It is not a "
        "significance test and it does not identify a causal effect."
    )
    add("")

    add("## What is held fixed")
    add("")
    add("| Element | Value |")
    add("|---|---|")
    add(f"| Outcome | `{fixed['outcome']}` |")
    add(f"| Unit | {fixed['unit']} |")
    add(f"| Model | `{fixed['model_id']}`, lags {list(fixed['y_lags'])}, no exog |")
    add(f"| Training scheme | {fixed['training_scheme']} |")
    add(f"| Training cutoff (exclusive) | {fixed['training_cutoff_exclusive']} |")
    add(
        f"| Treated window | {fixed['treated_window_start']} to "
        f"{fixed['treated_window_end']} ({fixed['treated_window_days']} days) |"
    )
    add(f"| Minimum initial training | {fixed['min_initial_train_days']} days |")
    add("")
    add(
        "Only the reference partition and its resolution vary. A horizon shorter "
        "than the treated window scores a strictly nested sub-window that still "
        "starts on the locked operational-onset date; no cell moves the "
        "treatment date, the model, or the units."
    )
    add("")

    add("## Origin rules, frozen before generation")
    add("")
    add("| Rule | Role | Definition |")
    add("|---|---|---|")
    for rule, spec in design["origin_rules"].items():
        add(f"| `{rule}` | {spec['role']} | {spec['description'].strip()} |")
    add("")
    add(
        "Each rule is a pure function of the calendar index, the locked cutoff, "
        "and the minimum training length. None of them can read the outcome, so "
        "no rule in this grid was or can be selected for a favourable result."
    )
    add("")

    add("## Complete enumeration versus greedy subsampling")
    add("")
    add(
        "The locked primary artifact coarsens candidate origins to a 30-day "
        "lattice and then greedily retains disjoint windows. This phase instead "
        "enumerates every feasible daily origin and reports the "
        "maximum-cardinality disjoint packing, which for equal-length blocks on "
        "a contiguous daily calendar is exactly "
        "`floor(available_reference_days / horizon)`."
    )
    add("")
    add(
        "| Horizon (days) | Feasible candidate blocks | Packing bound | "
        "`forward_anchored_direct` | `backward_anchored_from_cutoff` | "
        "`legacy_greedy_step30` |"
    )
    add("|---:|---:|---:|---:|---:|---:|")
    for horizon in design["horizon_grid_days"]:
        cells = {
            item["origin_rule"]: item
            for item in diagnostics["cells"]
            if item["horizon_days"] == int(horizon)
        }
        any_cell = cells[hf.PRIMARY_RULE]
        n_cand = int(
            summary.loc[summary["horizon_days"].eq(int(horizon)),
                        "n_candidate_blocks_all_daily_origins"].iloc[0]
        )
        add(
            f"| {int(horizon)} | {n_cand} | {any_cell['packing_upper_bound']} | "
            f"{cells[hf.PRIMARY_RULE]['n_reference_blocks']} | "
            f"{cells[hf.SENSITIVITY_RULE]['n_reference_blocks']} | "
            f"{cells[hf.LEGACY_RULE]['n_reference_blocks']} |"
        )
    add("")

    add("## Finite-sample inference frontier")
    add("")
    add(
        "With `K` disjoint reference blocks the smallest attainable rank "
        "p-value is `1/(K+1)`, the largest coverage a split-conformal interval "
        "can support is `K/(K+1)`, and a requested level is necessarily "
        "unbounded whenever `ceil((K+1) * level) > K`."
    )
    add("")
    add(
        "| Horizon | Rule | K | p-floor `1/(K+1)` | Observed rank p | "
        "Max coverage | Finite levels | Unbounded levels |"
    )
    add("|---:|---|---:|---:|---:|---:|---|---|")
    for item in diagnostics["cells"]:
        finite = ", ".join(f"{x:.0%}" for x in item["finite_interval_levels"]) or "none"
        unbounded = (
            ", ".join(f"{x:.0%}" for x in item["unbounded_interval_levels"]) or "none"
        )
        add(
            f"| {item['horizon_days']} | `{item['origin_rule']}` | "
            f"{item['n_reference_blocks']} | "
            f"{item['rank_p_value_floor']:.4f} | "
            f"{item['rank_p_value_greater']:.4f} | "
            f"{item['maximum_attainable_coverage']:.4f} | {finite} | {unbounded} |"
        )
    add("")
    at_floor = [
        item for item in diagnostics["cells"]
        if np.isclose(item["rank_p_value_greater"], item["rank_p_value_floor"])
    ]
    if len(at_floor) == len(diagnostics["cells"]):
        add(
            "In every cell of the grid the observed rank p-value sits exactly "
            "at its floor: the treated statistic exceeds every pre-treatment "
            "reference block under every origin rule and every resolution. The "
            "rank position is therefore maximal throughout, and what varies "
            "across the grid is only how small a number that maximal position "
            "is permitted to be. Both facts are design properties and neither "
            "is a significance statement."
        )
    else:
        add(
            f"{len(at_floor)} of {len(diagnostics['cells'])} cells put the "
            "treated statistic above every reference block; the remainder do "
            "not, and that disagreement is reported rather than resolved."
        )
    add("")

    add(f"## Primary cell: `{hf.PRIMARY_RULE}` at {primary} days")
    add("")
    add("| Level | Order statistic rank | Finite? | Radius | Interval |")
    add("|---:|---:|---|---:|---|")
    primary_rows = summary.loc[
        summary["origin_rule"].eq(hf.PRIMARY_RULE)
        & summary["horizon_days"].eq(primary)
    ]
    for record in primary_rows.to_dict("records"):
        supported = "yes" if record["finite_interval_supported"] else "no"
        if record["finite_interval_supported"]:
            interval = (
                f"[{_fmt(record['interval_lower'])}, "
                f"{_fmt(record['interval_upper'])}]"
            )
        else:
            interval = "unbounded"
        add(
            f"| {record['level']:.0%} | {record['order_statistic_rank']} | "
            f"{supported} | {_fmt(record['conformal_radius'])} | {interval} |"
        )
    add("")
    add(
        f"The treated statistic is a cumulative shortfall of "
        f"{_fmt(float(primary_rows['treated_cumulative_loss'].iloc[0]))} transits "
        f"({_fmt(float(primary_rows['treated_mean_daily_loss'].iloc[0]))} per day) "
        f"over {primary} days. The rank p-value is "
        f"{primary_cell['rank_p_value_greater']:.4f} against a floor of "
        f"{primary_cell['rank_p_value_floor']:.4f}."
    )
    add("")
    for record in primary_rows.to_dict("records"):
        if not record["finite_interval_supported"]:
            add(
                f"- A {record['level']:.0%} band needs at least "
                f"{int(record['min_blocks_required_for_level'])} disjoint blocks; "
                f"{int(record['additional_blocks_required_for_level'])} more than "
                f"this calendar supports at a {primary}-day resolution. It is "
                "reported as unbounded, not clipped."
            )
    add("")

    add("## Audit expectation")
    add("")
    add(
        f"Expectation under `{audit['rule']}` at {audit['horizon_days']} days: "
        f"{'reproduced' if audit['fully_reproduced'] else 'NOT reproduced'}."
    )
    add("")
    add("| Check | Expected | Observed | Reproduced |")
    add("|---|---|---|---|")
    for name, item in audit["checks"].items():
        add(
            f"| {name} | `{item['expected']}` | `{item['observed']}` | "
            f"{'yes' if item['reproduced'] else 'no'} |"
        )
    add("")
    add(audit["investigation_note"])
    add("")

    add("## The resolution trap, stated explicitly")
    add("")
    fine = [
        item for item in diagnostics["cells"]
        if item["five_percent_floor_attainable"]
    ]
    add(
        f"At the primary resolution the p-value floor is "
        f"{primary_cell['rank_p_value_floor']:.4f}, so **no 5% claim is "
        "arithmetically available there whatever the data show**."
    )
    add("")
    if fine:
        horizons = sorted({item["horizon_days"] for item in fine})
        add(
            "Finer resolutions in this grid do push the floor below 0.05 "
            f"(horizons: {', '.join(str(h) for h in horizons)} days). That is "
            "reported here for completeness and is **not** used as evidence, "
            "for three reasons."
        )
        add("")
        add(
            "1. The floor `1/(K+1)` falls purely because a shorter block length "
            "packs more blocks into the same fixed pre-period. No new "
            "observation is added."
        )
        add(
            "2. At a shorter horizon each reference block, and the treated "
            "statistic itself, measures a shorter accumulation. The quantity "
            "being tested changes with the resolution."
        )
        add(
            "3. Shorter blocks sit closer together in a serially dependent "
            "daily series, so treating them as independent calibration units "
            "is weaker than at the primary resolution."
        )
        add("")
        add(
            "The reporting resolution is fixed at "
            f"{primary} days by the frozen design, before any of these numbers "
            "existed. It is not swapped for whichever horizon produced the "
            "smallest floor, and this document makes no 5% significance claim "
            "at any resolution."
        )
    else:
        add("No resolution in this grid brings the floor to or below 0.05.")
    add("")

    add("## Interpretation limits")
    add("")
    add(
        "- A lower floor at a finer resolution is a partition property, not "
        "additional evidence. Reading the finest resolution as the strongest "
        "result would be a resolution artifact."
    )
    add(
        "- Reference blocks are pre-treatment windows for the same series, not "
        "untreated units. This is a rank position among earlier forecast "
        "errors, not an average treatment effect."
    )
    add(
        "- Unbounded intervals are a property of the available pre-period "
        "length at a given resolution. They are reported as unbounded because "
        "clipping the order statistic would deliver less coverage than the "
        "label claims."
    )
    add(
        "- The locked primary block artifacts are read-only inputs to this "
        "phase. They are hash-verified and never rewritten."
    )
    add("")
    return "\n".join(lines) + "\n"


def main() -> int:
    design, design_sha256 = load_design()
    panel = load_verified_inputs(design)

    geometry = build_geometry(design, panel)
    blocks = build_blocks(design, panel, geometry)
    summary = build_summary(design, panel, blocks)
    audit = build_audit_expectation(design, summary)
    diagnostics = build_diagnostics(
        design, design_sha256, panel, geometry, blocks, summary
    )
    markdown = render_markdown(design, diagnostics, summary, audit)

    outputs = {
        "geometry_csv": geometry,
        "blocks_csv": blocks,
        "summary_csv": summary,
    }
    for key, frame in outputs.items():
        path = output_path(design, key)
        path.parent.mkdir(parents=True, exist_ok=True)
        frame.to_csv(path, index=False)
        print(f"wrote {path}")

    for key, payload in (
        ("diagnostics_json", diagnostics),
        ("audit_expectation_json", audit),
    ):
        path = output_path(design, key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        print(f"wrote {path}")

    doc_path = output_path(design, "documentation_markdown")
    doc_path.parent.mkdir(parents=True, exist_ok=True)
    doc_path.write_text(markdown, encoding="utf-8")
    print(f"wrote {doc_path}")

    primary_cell = diagnostics["primary_cell"]
    print("\nHorizon/resolution frontier (primary cell):")
    print(
        f"  rule={primary_cell['origin_rule']} "
        f"horizon={primary_cell['horizon_days']}d "
        f"K={primary_cell['n_reference_blocks']} "
        f"(packing bound {primary_cell['packing_upper_bound']})"
    )
    print(
        f"  rank p={primary_cell['rank_p_value_greater']:.6f} "
        f"floor=1/(K+1)={primary_cell['rank_p_value_floor']:.6f} "
        f"max coverage={primary_cell['maximum_attainable_coverage']:.6f}"
    )
    print(
        f"  finite levels={primary_cell['finite_interval_levels']} "
        f"unbounded levels={primary_cell['unbounded_interval_levels']}"
    )
    print(
        "  audit expectation: "
        f"{'REPRODUCED' if audit['fully_reproduced'] else 'NOT REPRODUCED'}"
    )
    print("\nFrontier summary:")
    print(
        summary.loc[:, [
            "horizon_days",
            "origin_rule",
            "n_reference_blocks",
            "packing_upper_bound",
            "rank_p_value_greater",
            "rank_p_value_floor",
            "level",
            "finite_interval_supported",
            "conformal_radius",
        ]].to_string(index=False)
    )
    fine = sorted({
        item["horizon_days"]
        for item in diagnostics["cells"]
        if item["five_percent_floor_attainable"]
    })
    print("\nInterpretation guard:")
    print(
        " - The primary reporting resolution "
        f"({primary_cell['horizon_days']}d) has floor "
        f"{primary_cell['rank_p_value_floor']:.4f}; a 5% claim is "
        "arithmetically unavailable there."
    )
    if fine:
        print(
            f" - Finer resolutions ({', '.join(f'{h}d' for h in fine)}) do push "
            "1/(K+1) below 0.05. That is a partition property, not evidence, "
            "and no 5% significance is claimed at any resolution."
        )
    print(" - Unbounded levels are reported as unbounded, never clipped.")
    print(" - Reference blocks are pre-treatment windows, not untreated units.")
    print(" - This is NEEDS-VERIFY until Mher records the G4 output.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
