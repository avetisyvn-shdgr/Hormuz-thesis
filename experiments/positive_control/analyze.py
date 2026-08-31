"""Analyze the Red Sea positive control with the Hormuz corridor machinery.

Same statistic, same synchronized circular block bootstrap, same Romano-Wolf
step-down as ``experiments.network_adaptation.analyze``. The difference that
matters is upstream of all of it: the receiver was designated on route topology
before any post-onset outcome was inspected, so the multiplicity-adjusted
p-value on the anchor is a test rather than a screen.

Both declared onsets are reported. Neither is the headline.

Run with:

    MPLBACKEND=Agg .venv/bin/python -m experiments.positive_control.analyze
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from experiments.network_adaptation.analyze import hypothesis_name
from experiments.network_adaptation.inference import (
    global_mean_test,
    scale_columns,
    synchronized_circular_mbb,
)
from experiments.panel_bakeoff.protocol import file_sha256, load_raw_panel
from experiments.positive_control.protocol import (
    Onset,
    PositiveControlProtocol,
    load_protocol,
)
from hormuz_throughput.inference import romano_wolf_stepdown


ROOT = Path(__file__).resolve().parents[2]
ANCHOR_FAMILY = "ex_ante_designated_anchor"
RECEIVER_FAMILY = "eligible_receiver_family"
CONTROL_FAMILY = "anchor_negative_controls"
CONTEXT_FAMILY = "context_descriptive_not_tested"


def _load(protocol: PositiveControlProtocol) -> pd.DataFrame:
    path = protocol.outputs["event_forecasts"]
    if not path.exists():
        raise FileNotFoundError(
            f"Missing {path}. Run experiments.positive_control.run_forecasts first."
        )
    frame = pd.read_csv(path, parse_dates=["origin", "date"])
    expected = (
        len(protocol.onsets) * 2 * (protocol.reference_origins + 1)
        * len(protocol.all_keys) * protocol.horizon
    )
    if len(frame) != expected:
        raise ValueError(f"positive-control forecasts are incomplete: {len(frame)} rows.")
    if set(frame["model"]) != {protocol.primary_model, protocol.robustness_model}:
        raise ValueError("forecast model set differs from the frozen protocol.")
    if frame[["y_true", "y_pred"]].isna().any().any():
        raise ValueError("forecasts contain missing actuals or point predictions.")
    frame["residual"] = frame["y_true"] - frame["y_pred"]
    frame["hypothesis"] = [
        hypothesis_name(port, vessel_class)
        for port, vessel_class in zip(frame["portname"], frame["vessel_class"])
    ]
    return frame


def _pre_onset_means(raw: pd.DataFrame, protocol: PositiveControlProtocol, onset: Onset) -> pd.Series:
    pre = raw.loc[raw["date"] < onset.date]
    values = {}
    for port, vessel_class in protocol.all_keys:
        part = pre.loc[pre["portname"].eq(port), vessel_class]
        if part.empty or not np.isfinite(part).all() or part.mean() <= 0:
            raise ValueError(f"invalid pre-onset mean for {vessel_class}/{port} at {onset.name}")
        values[hypothesis_name(port, vessel_class)] = float(part.mean())
    return pd.Series(values, dtype="float64")


def _reference_matrix(
    frame: pd.DataFrame, protocol: PositiveControlProtocol, onset: Onset, model: str
) -> pd.DataFrame:
    part = frame.loc[
        frame["onset"].eq(onset.name)
        & frame["model"].eq(model)
        & frame["origin_role"].eq("reference")
    ]
    matrix = part.pivot(
        index=["origin", "date", "lead"], columns="hypothesis", values="residual"
    ).sort_index()
    names = sorted(hypothesis_name(p, c) for p, c in protocol.all_keys)
    matrix = matrix.reindex(columns=names)
    expected_rows = protocol.reference_origins * protocol.horizon
    if matrix.shape != (expected_rows, len(names)) or matrix.isna().any().any():
        raise ValueError(f"incomplete residual reference for {onset.name}/{model}.")
    dates = matrix.index.get_level_values("date")
    contiguous = pd.date_range(dates.min(), periods=len(matrix), freq="D")
    if not pd.DatetimeIndex(dates).equals(contiguous):
        raise ValueError(f"the {onset.name} residual reference is not contiguous.")
    if dates.max() >= onset.date:
        raise ValueError(f"the {onset.name} residual reference reaches its own onset.")
    return matrix


def _event_statistics(
    frame: pd.DataFrame,
    protocol: PositiveControlProtocol,
    onset: Onset,
    model: str,
    means: pd.Series,
) -> pd.DataFrame:
    part = frame.loc[
        frame["onset"].eq(onset.name)
        & frame["model"].eq(model)
        & frame["origin_role"].eq("event")
    ]
    rows = []
    for port, vessel_class in protocol.all_keys:
        series = part.loc[
            part["portname"].eq(port) & part["vessel_class"].eq(vessel_class)
        ].sort_values("date")
        if len(series) != protocol.horizon:
            raise ValueError(f"event window incomplete for {model}/{vessel_class}/{port}")
        name = hypothesis_name(port, vessel_class)
        gap = series["residual"].to_numpy()
        rows.append({
            "hypothesis": name,
            "onset": onset.name,
            "model": model,
            "portname": port,
            "vessel_class": vessel_class,
            "n_days": len(series),
            "pre_onset_mean": float(means[name]),
            "observed_sum": float(series["y_true"].sum()),
            "counterfactual_sum": float(series["y_pred"].sum()),
            "cumulative_gap": float(gap.sum()),
            "event_statistic": float(gap.mean() / means[name]),
        })
    return pd.DataFrame(rows).set_index("hypothesis", drop=False)


def _tested_family(
    stats: pd.DataFrame, draws: pd.DataFrame, names: list[str], family: str, block_length: int
) -> tuple[pd.DataFrame, dict[str, float | int]]:
    observed = stats.loc[names, "event_statistic"]
    family_draws = draws.reindex(columns=names)
    rw = romano_wolf_stepdown(
        observed, family_draws, alternative="greater", studentize=True
    ).set_index("hypothesis")
    reference = pd.DataFrame({
        "historical_reference_mean": family_draws.mean(),
        "historical_reference_sd": family_draws.std(ddof=1),
        "reference_q025": family_draws.quantile(0.025),
        "reference_q975": family_draws.quantile(0.975),
    })
    out = stats.loc[names].join(reference).join(
        rw[["studentized_statistic", "raw_resampling_p_value", "romano_wolf_p_value",
            "stepdown_rank", "family_size", "n_joint_resamples"]]
    )
    out["family"] = family
    out["block_length_days"] = block_length
    return out.reset_index(drop=True), global_mean_test(observed, family_draws)


def _descriptive_family(
    stats: pd.DataFrame, draws: pd.DataFrame, names: list[str], block_length: int
) -> pd.DataFrame:
    family_draws = draws.reindex(columns=names)
    reference = pd.DataFrame({
        "historical_reference_mean": family_draws.mean(),
        "historical_reference_sd": family_draws.std(ddof=1),
        "reference_q025": family_draws.quantile(0.025),
        "reference_q975": family_draws.quantile(0.975),
    })
    out = stats.loc[names].join(reference)
    out["family"] = CONTEXT_FAMILY
    out["block_length_days"] = block_length
    for column in (
        "studentized_statistic", "raw_resampling_p_value", "romano_wolf_p_value",
        "stepdown_rank", "family_size", "n_joint_resamples",
    ):
        out[column] = np.nan
    return out.reset_index(drop=True)


def _make_figure(inference: pd.DataFrame, protocol: PositiveControlProtocol, path: Path) -> None:
    primary = inference.loc[
        inference["family"].eq(RECEIVER_FAMILY)
        & inference["block_length_days"].eq(protocol.block_length)
        & inference["model"].eq(protocol.primary_model)
    ]
    onsets = [onset.name for onset in protocol.onsets]
    fig, axes = plt.subplots(1, 2, figsize=(12.8, 6.4), sharex=True)
    for ax, onset_name in zip(axes, onsets):
        part = primary.loc[primary["onset"].eq(onset_name)].sort_values("event_statistic")
        y = np.arange(len(part))
        colors = [
            "#D55E00" if port == protocol.anchor_receiver else "#9A9A9A"
            for port in part["portname"]
        ]
        ax.hlines(
            y, part["reference_q025"], part["reference_q975"],
            color="#C9C9C9", linewidth=2.0, zorder=1,
        )
        ax.scatter(part["event_statistic"], y, color=colors, s=46, zorder=3)
        ax.axvline(0, color="#333333", linewidth=0.9, linestyle="--")
        labels = [
            f"{port}" if port != protocol.anchor_receiver else f"{port}  (ex ante)"
            for port in part["portname"]
        ]
        ax.set_yticks(y, labels, fontsize=8.5)
        for tick, port in zip(ax.get_yticklabels(), part["portname"]):
            if port == protocol.anchor_receiver:
                tick.set_fontweight("bold")
                tick.set_color("#D55E00")
        onset = next(o for o in protocol.onsets if o.name == onset_name)
        ax.set_title(
            f"{onset_name.replace('_', ' ')} — {onset.date.date()}",
            loc="left", fontweight="bold", fontsize=11,
        )
        ax.set_xlabel("Mean observed-minus-counterfactual gap / pre-onset mean")
        ax.spines[["top", "right"]].set_visible(False)
        ax.grid(axis="x", color="#EDEDED", linewidth=0.7)
        ax.grid(axis="y", visible=False)
    fig.suptitle(
        "The ex-ante designated receiver ranks first in its frozen eligible family",
        x=0.045, ha="left", fontsize=14, fontweight="bold",
    )
    fig.text(
        0.045, 0.935,
        "130 days from each declared Red Sea onset. Grey segments are synchronized 14-day block-bootstrap historical reference ranges, not causal intervals.",
        ha="left", fontsize=9, color="#444444",
    )
    fig.text(
        0.045, 0.012,
        "Source: IMF PortWatch snapshot; Chronos-2 univariate. Both onsets are declared sensitivities; neither is the headline.",
        ha="left", fontsize=8.5, color="#555555",
    )
    fig.tight_layout(rect=[0.02, 0.04, 1, 0.91])
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=240, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    protocol = load_protocol()
    if file_sha256(protocol.raw_path) != protocol.expected_raw_sha256:
        raise RuntimeError("the PortWatch snapshot hash changed.")
    raw = load_raw_panel(protocol.raw_path)
    frame = _load(protocol)

    anchor = hypothesis_name(*protocol.anchor_key)
    receiver_names = sorted(hypothesis_name(p, c) for p, c in protocol.eligible_keys)
    control_names = sorted(hypothesis_name(p, c) for p, c in protocol.control_keys)
    context_names = sorted(hypothesis_name(p, c) for p, c in protocol.context_keys)

    inference_rows: list[pd.DataFrame] = []
    global_rows: list[dict[str, object]] = []
    block_lengths = (protocol.block_length, *protocol.sensitivity_block_lengths)
    for onset_index, onset in enumerate(protocol.onsets):
        means = _pre_onset_means(raw, protocol, onset)
        for model_index, model in enumerate(
            (protocol.primary_model, protocol.robustness_model)
        ):
            historical = _reference_matrix(frame, protocol, onset, model)
            stats = _event_statistics(frame, protocol, onset, model, means)
            for block_length in block_lengths:
                draws = scale_columns(
                    synchronized_circular_mbb(
                        historical,
                        horizon=protocol.horizon,
                        block_length=block_length,
                        n_draws=protocol.n_draws,
                        seed=(
                            protocol.seed
                            + 100_000 * onset_index
                            + 1000 * model_index
                            + block_length
                        ),
                    ),
                    means,
                )
                for family, names in (
                    (ANCHOR_FAMILY, [anchor]),
                    (RECEIVER_FAMILY, receiver_names),
                    (CONTROL_FAMILY, control_names),
                ):
                    part, result = _tested_family(stats, draws, names, family, block_length)
                    inference_rows.append(part)
                    global_rows.append({
                        "onset": onset.name,
                        "model": model,
                        "family": family,
                        "block_length_days": block_length,
                        "n_series": len(names),
                        **result,
                    })
                inference_rows.append(
                    _descriptive_family(stats, draws, context_names, block_length)
                )

    inference = pd.concat(inference_rows, ignore_index=True).sort_values(
        ["onset", "block_length_days", "family", "model", "vessel_class", "portname"],
        kind="stable",
    )
    global_tests = pd.DataFrame(global_rows).sort_values(
        ["onset", "block_length_days", "family", "model"], kind="stable"
    )

    for name in ("inference", "global_tests"):
        protocol.outputs[name].parent.mkdir(parents=True, exist_ok=True)
    inference.to_csv(protocol.outputs["inference"], index=False)
    global_tests.to_csv(protocol.outputs["global_tests"], index=False)
    _make_figure(inference, protocol, protocol.outputs["figure_png"])

    primary_block = inference["block_length_days"].eq(protocol.block_length)
    anchor_rows = inference.loc[primary_block & inference["family"].eq(ANCHOR_FAMILY)]
    receiver_rows = inference.loc[primary_block & inference["family"].eq(RECEIVER_FAMILY)]
    control_rows = inference.loc[primary_block & inference["family"].eq(CONTROL_FAMILY)]

    ranks = {}
    for (onset_name, model), part in receiver_rows.groupby(["onset", "model"]):
        ordered = part.sort_values("studentized_statistic", ascending=False)
        ranks[f"{onset_name}::{model}"] = {
            "anchor_rank": int(
                ordered.reset_index(drop=True)
                .index[ordered["portname"].eq(protocol.anchor_receiver).to_numpy()][0]
            )
            + 1,
            "family_size": int(len(ordered)),
            "anchor_is_family_max": bool(
                ordered["portname"].iloc[0] == protocol.anchor_receiver
            ),
            "anchor_romano_wolf_p": float(
                part.loc[part["portname"].eq(protocol.anchor_receiver), "romano_wolf_p_value"].iloc[0]
            ),
        }

    validation = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": protocol.status,
        "designation": protocol.designation,
        "why_this_differs_from_the_hormuz_screen": (
            "The receiver was named on route topology before any post-onset "
            "outcome was inspected, and the eligible family it is ranked within "
            "was frozen on pre-onset volume. The Hormuz five-corridor set was "
            "restricted after an all-corridor post-event AR map existed."
        ),
        "onsets_reported": [onset.name for onset in protocol.onsets],
        "primary_onset": protocol.primary_onset,
        "anchor": {
            "receiver": protocol.anchor_receiver,
            "emitter": protocol.anchor_emitter,
            "vessel_class": protocol.anchor_class,
        },
        "anchor_standing": ranks,
        "anchor_event_statistic": {
            f"{row['onset']}::{row['model']}": float(row["event_statistic"])
            for _, row in anchor_rows.iterrows()
        },
        "anchor_raw_p_value_singleton_family": {
            f"{row['onset']}::{row['model']}": float(row["raw_resampling_p_value"])
            for _, row in anchor_rows.iterrows()
        },
        "negative_controls_below_0_05": {
            f"{onset}::{model}": int(part["romano_wolf_p_value"].lt(0.05).sum())
            for (onset, model), part in control_rows.groupby(["onset", "model"])
        },
        "anchor_detected_under_every_block_length": bool(
            inference.loc[
                inference["family"].eq(ANCHOR_FAMILY), "raw_resampling_p_value"
            ].lt(0.05).all()
        ),
        "required_caveats": [
            "Aggregate correspondence at the Cape is not vessel linkage; no voyage is matched to a missing Bab el-Mandeb transit.",
            "Both onsets are declared sensitivities and both are reported; neither is the headline.",
            "The register onset's residual reference and scaling window include 30 days already inside the diversion, which deflates its measured gain.",
            "PortWatch n_tanker aggregates tanker types and cannot isolate any cargo class.",
            "The ex-ante status of this test does not transfer to the retrospective Hormuz corridor screen.",
        ],
    }
    protocol.outputs["validation"].write_text(
        json.dumps(validation, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    output_paths = [
        protocol.outputs[name]
        for name in ("event_forecasts", "inference", "global_tests", "validation", "figure_png")
    ]
    manifest = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": protocol.status,
        "claim": protocol.claim,
        "raw_sha256": file_sha256(protocol.raw_path),
        "models": [protocol.primary_model, protocol.robustness_model],
        "inference": {
            "method": "synchronized_circular_moving_block_bootstrap_plus_Romano_Wolf",
            "horizon_days": protocol.horizon,
            "reference_origins": protocol.reference_origins,
            "primary_block_length_days": protocol.block_length,
            "sensitivity_block_lengths_days": list(protocol.sensitivity_block_lengths),
            "draws": protocol.n_draws,
            "seed": protocol.seed,
        },
        "families": {
            ANCHOR_FAMILY: [anchor],
            RECEIVER_FAMILY: receiver_names,
            CONTROL_FAMILY: control_names,
            CONTEXT_FAMILY: context_names,
        },
        "outputs_sha256": {
            str(path.relative_to(ROOT)): file_sha256(path) for path in output_paths
        },
    }
    protocol.outputs["manifest"].write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    print("=== anchor, 14-day blocks ===")
    print(anchor_rows[[
        "onset", "model", "event_statistic", "cumulative_gap",
        "reference_q025", "reference_q975", "raw_resampling_p_value",
    ]].round(4).to_string(index=False))
    print("\n=== standing within the frozen eligible family ===")
    for key, value in ranks.items():
        print(
            f"{key}: rank {value['anchor_rank']} of {value['family_size']}"
            f"{' (family max)' if value['anchor_is_family_max'] else ''}, "
            f"Romano-Wolf p = {value['anchor_romano_wolf_p']:.4f}"
        )
    print("\n=== anchor negative controls, 14-day blocks ===")
    print(control_rows[[
        "onset", "model", "vessel_class", "event_statistic", "romano_wolf_p_value",
    ]].round(4).to_string(index=False))
    print(f"\nwrote {protocol.outputs['inference']}")
    print(f"wrote {protocol.outputs['validation']}")


if __name__ == "__main__":
    main()
