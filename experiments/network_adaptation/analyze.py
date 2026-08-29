"""Run the restricted, dependence-aware network-adaptation analysis.

This consumes the already executed panel bake-off residuals and the separately
generated event forecasts. It never refits on post-cutoff observations.

Run with:

    .venv/bin/python -m experiments.network_adaptation.analyze
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from experiments.network_adaptation.inference import (
    global_mean_test,
    scale_columns,
    synchronized_circular_mbb,
)
from experiments.network_adaptation.protocol import AdaptationProtocol, load_protocol
from experiments.panel_bakeoff.protocol import EXPLICIT_CLASSES, file_sha256, load_raw_panel
from lngfreight.inference import romano_wolf_stepdown


ROOT = Path(__file__).resolve().parents[2]
VALIDATION_FILES = {
    "chronos2_univariate": ROOT / "experiments/panel_bakeoff/outputs/chronos_forecasts.csv.gz",
    "ar_lag1_7": ROOT / "experiments/panel_bakeoff/outputs/classical_forecasts.csv.gz",
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _hypothesis(portname: str, vessel_class: str) -> str:
    return f"{vessel_class}::{portname}"


def _load_event(protocol: AdaptationProtocol) -> pd.DataFrame:
    path = protocol.outputs["event_forecasts"]
    if not path.exists():
        raise FileNotFoundError(
            f"Missing {path}. Run experiments.network_adaptation.run_event_forecasts first."
        )
    frame = pd.read_csv(path, parse_dates=["origin", "date"])
    required = {
        "model", "portname", "vessel_class", "origin", "date", "lead", "y_true", "y_pred"
    }
    if missing := required.difference(frame.columns):
        raise KeyError(f"event forecasts missing columns: {sorted(missing)}")
    if frame.duplicated(["model", "portname", "vessel_class", "date"]).any():
        raise ValueError("event forecasts contain duplicate model-series-days.")
    if set(frame["model"].unique()) != {protocol.primary_model, protocol.robustness_model}:
        raise ValueError("event forecast model set differs from the frozen protocol.")
    if not frame["origin"].eq(protocol.cutoff).all():
        raise ValueError("event forecast origin differs from the treatment cutoff.")
    if frame["date"].min() != protocol.cutoff or frame["date"].max() != protocol.event_end:
        raise ValueError("event forecast date range differs from the frozen horizon.")
    counts = frame.groupby(["model", "portname", "vessel_class"]).size()
    if not counts.eq(protocol.horizon).all() or len(counts) != 2 * 28 * len(EXPLICIT_CLASSES):
        raise ValueError("event forecasts are not a complete 2 x 28 x 5 x 130 panel.")
    if frame[["y_true", "y_pred"]].isna().any().any():
        raise ValueError("event actuals or point forecasts contain missing values.")
    return frame


def _validation_residuals(
    model: str,
    keys: tuple[tuple[str, str], ...],
    protocol: AdaptationProtocol,
) -> pd.DataFrame:
    source = VALIDATION_FILES[model]
    frame = pd.read_csv(source, parse_dates=["origin", "date"])
    frame = frame.loc[
        frame["model"].eq(model)
        & frame["panel"].eq("composition_28x5")
        & frame["horizon"].eq(protocol.horizon)
    ].copy()
    wanted = {_hypothesis(port, vessel_class) for port, vessel_class in keys}
    frame["hypothesis"] = frame.apply(
        lambda row: _hypothesis(str(row["portname"]), str(row["vessel_class"])), axis=1
    )
    frame = frame.loc[frame["hypothesis"].isin(wanted)]
    if set(frame["hypothesis"].unique()) != wanted:
        missing = sorted(wanted.difference(frame["hypothesis"].unique()))
        raise ValueError(f"validation forecasts omit frozen series: {missing}")
    if frame["date"].max() >= protocol.cutoff:
        raise ValueError("historical residual calibration reaches the event cutoff.")
    if frame.duplicated(["origin", "date", "hypothesis"]).any():
        raise ValueError("validation residuals contain duplicate synchronized keys.")
    frame["residual"] = frame["y_true"] - frame["y_pred"]
    matrix = frame.pivot(
        index=["origin", "date", "lead"], columns="hypothesis", values="residual"
    ).sort_index()
    matrix = matrix.reindex(columns=sorted(wanted))
    if matrix.shape != (8 * protocol.horizon, len(wanted)):
        raise ValueError(f"unexpected validation residual geometry: {matrix.shape}")
    if matrix.isna().any().any() or matrix.index.get_level_values("origin").nunique() != 8:
        raise ValueError("validation residual matrix is incomplete.")
    dates = matrix.index.get_level_values("date")
    expected = pd.date_range(dates.min(), periods=len(matrix), freq="D")
    if not dates.equals(pd.DatetimeIndex(expected)):
        raise ValueError("the eight 130-day OOS residual blocks are not contiguous.")
    return matrix


def _pre_event_means(raw: pd.DataFrame, keys, cutoff: pd.Timestamp) -> pd.Series:
    pre = raw.loc[raw["date"] < cutoff]
    values = {}
    for port, vessel_class in keys:
        part = pre.loc[pre["portname"].eq(port), vessel_class]
        if part.empty or not np.isfinite(part).all() or part.mean() <= 0:
            raise ValueError(f"invalid pre-event mean for {vessel_class}/{port}")
        values[_hypothesis(port, vessel_class)] = float(part.mean())
    return pd.Series(values, dtype="float64")


def _event_statistics(event: pd.DataFrame, model: str, keys, pre_means: pd.Series) -> pd.DataFrame:
    rows = []
    for port, vessel_class in keys:
        part = event.loc[
            event["model"].eq(model)
            & event["portname"].eq(port)
            & event["vessel_class"].eq(vessel_class)
        ].sort_values("date")
        if len(part) != 130:
            raise ValueError(f"event series incomplete for {model}/{vessel_class}/{port}")
        hypothesis = _hypothesis(port, vessel_class)
        gap = part["y_true"].to_numpy() - part["y_pred"].to_numpy()
        rows.append({
            "hypothesis": hypothesis,
            "model": model,
            "portname": port,
            "vessel_class": vessel_class,
            "n_days": len(part),
            "pre_event_mean": float(pre_means[hypothesis]),
            "observed_sum": float(part["y_true"].sum()),
            "counterfactual_sum": float(part["y_pred"].sum()),
            "cumulative_gap": float(gap.sum()),
            "event_statistic": float(gap.mean() / pre_means[hypothesis]),
        })
    return pd.DataFrame(rows).set_index("hypothesis", drop=False)


def _family_rows(
    event_stats: pd.DataFrame,
    draws: pd.DataFrame,
    family: str,
    block_length: int,
) -> tuple[pd.DataFrame, dict[str, float | int]]:
    observed = event_stats["event_statistic"]
    family_draws = draws.reindex(columns=observed.index)
    rw = romano_wolf_stepdown(
        observed,
        family_draws,
        alternative="greater",
        studentize=True,
    ).set_index("hypothesis")
    reference = pd.DataFrame({
        "historical_reference_mean": family_draws.mean(),
        "historical_reference_sd": family_draws.std(ddof=1),
        "reference_q025": family_draws.quantile(0.025),
        "reference_q975": family_draws.quantile(0.975),
    })
    out = event_stats.join(reference).join(
        rw[["studentized_statistic", "raw_resampling_p_value", "romano_wolf_p_value",
            "stepdown_rank", "family_size", "n_joint_resamples"]]
    )
    out["family"] = family
    out["block_length_days"] = block_length
    return out.reset_index(drop=True), global_mean_test(observed, family_draws)


def _context_rows(
    event_stats: pd.DataFrame,
    draws: pd.DataFrame,
    block_length: int,
) -> pd.DataFrame:
    reference = pd.DataFrame({
        "historical_reference_mean": draws.mean(),
        "historical_reference_sd": draws.std(ddof=1),
        "reference_q025": draws.quantile(0.025),
        "reference_q975": draws.quantile(0.975),
    })
    out = event_stats.join(reference)
    out["family"] = "context_descriptive_not_tested"
    out["block_length_days"] = block_length
    for column in (
        "studentized_statistic", "raw_resampling_p_value", "romano_wolf_p_value",
        "stepdown_rank", "family_size", "n_joint_resamples",
    ):
        out[column] = np.nan
    return out.reset_index(drop=True)


def _make_figure(inference: pd.DataFrame, protocol: AdaptationProtocol) -> None:
    primary = inference.loc[
        inference["family"].eq("restricted_tanker_adaptation")
        & inference["block_length_days"].eq(protocol.block_length)
    ].copy()
    order = list(protocol.primary_corridors)[::-1]
    models = [protocol.primary_model, protocol.robustness_model]
    labels = {protocol.primary_model: "Chronos-2", protocol.robustness_model: "AR(1,7)"}
    colors = {protocol.primary_model: "#0072B2", protocol.robustness_model: "#D55E00"}
    markers = {protocol.primary_model: "o", protocol.robustness_model: "s"}
    fig, axes = plt.subplots(1, 2, figsize=(12.5, 5.8), sharey=True)
    for ax, model in zip(axes, models):
        part = primary.loc[primary["model"].eq(model)].set_index("portname").reindex(order)
        y = np.arange(len(order))
        ax.hlines(
            y,
            part["reference_q025"],
            part["reference_q975"],
            color="#7A7A7A",
            linewidth=2.0,
            label="Historical 95% reference range",
        )
        ax.vlines(
            np.r_[part["reference_q025"].to_numpy(), part["reference_q975"].to_numpy()],
            np.r_[y - 0.045, y - 0.045],
            np.r_[y + 0.045, y + 0.045],
            color="#7A7A7A",
            linewidth=1.2,
        )
        ax.scatter(
            part["event_statistic"], y, marker=markers[model], color=colors[model],
            s=48, zorder=3, label="Event statistic",
        )
        ax.axvline(0, color="#333333", linewidth=0.9, linestyle="--")
        ax.set_yticks(y, order)
        ax.set_xlabel("Mean observed-minus-counterfactual gap / pre-event mean")
        ax.set_title(labels[model], loc="left", fontweight="bold")
        ax.spines[["top", "right"]].set_visible(False)
        ax.grid(axis="x", color="#E5E5E5", linewidth=0.7)
        ax.grid(axis="y", visible=False)
    x_min = float(min(primary["reference_q025"].min(), primary["event_statistic"].min()))
    x_max = float(max(primary["reference_q975"].max(), primary["event_statistic"].max()))
    x_pad = 0.04 * (x_max - x_min)
    for ax in axes:
        ax.set_xlim(x_min - x_pad, x_max + x_pad)
    fig.suptitle(
        "Positive tanker anomalies are concentrated at Cape, Panama, and Yucatan",
        x=0.08, ha="left", fontsize=14, fontweight="bold",
    )
    fig.text(
        0.08, 0.93,
        "130 days from 28 Feb 2026; whiskers are synchronized 14-day block-bootstrap reference ranges, not causal confidence intervals",
        ha="left", fontsize=9.5, color="#444444",
    )
    fig.text(
        0.08, 0.015,
        "Source: IMF PortWatch snapshot; Chronos-2 univariate and recursive AR(1,7). Restricted set is retrospective and exploratory.",
        ha="left", fontsize=8.5, color="#555555",
    )
    fig.tight_layout(rect=[0.06, 0.06, 1, 0.9])
    for key in ("figure_png", "figure_pdf"):
        path = protocol.outputs[key]
        path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(path, dpi=240, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    protocol = load_protocol()
    if file_sha256(protocol.raw_path) != protocol.expected_raw_sha256:
        raise RuntimeError("the PortWatch snapshot hash changed.")
    raw = load_raw_panel(protocol.raw_path)
    event = _load_event(protocol)
    all_keys = tuple(dict.fromkeys(protocol.primary_keys + protocol.control_keys + protocol.context_keys))
    pre_means = _pre_event_means(raw, all_keys, protocol.cutoff)

    inference_rows: list[pd.DataFrame] = []
    global_rows: list[dict[str, object]] = []
    residual_audit: dict[str, dict[str, object]] = {}
    block_lengths = (protocol.block_length, *protocol.sensitivity_block_lengths)
    for model_index, model in enumerate((protocol.primary_model, protocol.robustness_model)):
        historical = _validation_residuals(model, all_keys, protocol)
        residual_audit[model] = {
            "rows": len(historical),
            "columns": historical.shape[1],
            "origins": historical.index.get_level_values("origin").nunique(),
            "start": str(historical.index.get_level_values("date").min().date()),
            "end": str(historical.index.get_level_values("date").max().date()),
            "all_pre_cutoff": bool(
                historical.index.get_level_values("date").max() < protocol.cutoff
            ),
        }
        event_stats = _event_statistics(event, model, all_keys, pre_means)
        for block_length in block_lengths:
            raw_draws = synchronized_circular_mbb(
                historical,
                horizon=protocol.horizon,
                block_length=block_length,
                n_draws=protocol.n_draws,
                seed=protocol.seed + 1000 * model_index + block_length,
            )
            draws = scale_columns(raw_draws, pre_means)
            for family, keys in (
                ("restricted_tanker_adaptation", protocol.primary_keys),
                ("non_tanker_negative_controls", protocol.control_keys),
            ):
                names = [_hypothesis(port, vessel_class) for port, vessel_class in keys]
                part, global_result = _family_rows(
                    event_stats.loc[names], draws.loc[:, names], family, block_length
                )
                inference_rows.append(part)
                global_rows.append({
                    "model": model,
                    "family": family,
                    "block_length_days": block_length,
                    "n_series": len(names),
                    **global_result,
                })
            context_names = [_hypothesis(port, vessel_class) for port, vessel_class in protocol.context_keys]
            inference_rows.append(
                _context_rows(
                    event_stats.loc[context_names], draws.loc[:, context_names], block_length
                )
            )

    inference = pd.concat(inference_rows, ignore_index=True).sort_values(
        ["block_length_days", "family", "model", "vessel_class", "portname"],
        kind="stable",
    )
    global_tests = pd.DataFrame(global_rows).sort_values(
        ["block_length_days", "family", "model"], kind="stable"
    )
    primary_comparison = inference.loc[
        inference["family"].eq("restricted_tanker_adaptation")
        & inference["block_length_days"].eq(protocol.block_length),
        ["model", "portname", "vessel_class", "event_statistic", "cumulative_gap",
         "romano_wolf_p_value"],
    ]
    comparison = primary_comparison.pivot(
        index=["portname", "vessel_class"], columns="model"
    )
    comparison.columns = [f"{metric}__{model}" for metric, model in comparison.columns]
    comparison = comparison.reset_index()
    comparison["event_statistic_absolute_difference"] = (
        comparison[f"event_statistic__{protocol.primary_model}"]
        - comparison[f"event_statistic__{protocol.robustness_model}"]
    ).abs()
    comparison["sign_agreement"] = np.sign(
        comparison[f"event_statistic__{protocol.primary_model}"]
    ).eq(np.sign(comparison[f"event_statistic__{protocol.robustness_model}"]))

    protocol.outputs["inference"].parent.mkdir(parents=True, exist_ok=True)
    inference.to_csv(protocol.outputs["inference"], index=False)
    global_tests.to_csv(protocol.outputs["global_tests"], index=False)
    comparison.to_csv(protocol.outputs["model_comparison"], index=False)
    _make_figure(inference, protocol)

    primary_block = inference["block_length_days"].eq(protocol.block_length)
    primary_results = inference.loc[
        primary_block & inference["family"].eq("restricted_tanker_adaptation")
    ]
    controls = inference.loc[
        primary_block & inference["family"].eq("non_tanker_negative_controls")
    ]
    validation = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": protocol.status,
        "overall_assessment": "share_with_noted_caveats",
        "raw_data": {
            "sha256_verified": True,
            "rows": len(raw),
            "date_min": str(raw["date"].min().date()),
            "date_max": str(raw["date"].max().date()),
            "chokepoints": int(raw["portname"].nunique()),
            "duplicate_port_dates": int(raw.duplicated(["date", "portname"]).sum()),
            "primary_and_control_nulls": int(
                raw[["n_tanker", "n_roro", "n_dry_bulk"]].isna().sum().sum()
            ),
        },
        "event_forecasts": {
            "rows": len(event),
            "models": sorted(event["model"].unique()),
            "unit_series_per_model": int(
                event.loc[event["model"].eq(protocol.primary_model)]
                .groupby(["portname", "vessel_class"]).ngroups
            ),
            "days_per_series": protocol.horizon,
            "training_end_precedes_cutoff": True,
        },
        "historical_oos_residuals": residual_audit,
        "inference": {
            "joint_resampling_preserves_cross_series_indices": True,
            "primary_block_length_days": protocol.block_length,
            "sensitivity_block_lengths_days": list(protocol.sensitivity_block_lengths),
            "draws": protocol.n_draws,
            "primary_family_size": len(protocol.primary_keys),
            "negative_control_family_size": len(protocol.control_keys),
            "chronos_primary_rw_p_below_0_05": int(
                primary_results.loc[primary_results["model"].eq(protocol.primary_model),
                                    "romano_wolf_p_value"].lt(0.05).sum()
            ),
            "negative_controls_rw_p_below_0_05": int(
                controls["romano_wolf_p_value"].lt(0.05).sum()
            ),
            "model_sign_agreement_fraction": float(comparison["sign_agreement"].mean()),
        },
        "required_caveats": [
            "The restricted corridor set was frozen after an earlier post-event AR map existed; p-values are descriptive, not preregistered confirmatory evidence.",
            "PortWatch n_tanker aggregates tanker types and cannot isolate LNG carriers.",
            "No vessel identity or origin-destination linkage is available; positive anomalies do not identify physical rerouting or displaced Hormuz volume.",
            "The block bootstrap is a historical forecast-error reference, not a causal confidence interval.",
            "Concurrent Red Sea and other shocks can affect the same corridors.",
        ],
    }
    protocol.outputs["validation"].write_text(
        json.dumps(validation, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    output_paths = [
        protocol.outputs[name]
        for name in ("event_forecasts", "inference", "global_tests", "model_comparison",
                     "validation", "figure_png", "figure_pdf")
    ]
    manifest = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": protocol.status,
        "claim": protocol.claim,
        "raw_sha256": file_sha256(protocol.raw_path),
        "models": [protocol.primary_model, protocol.robustness_model],
        "primary_family": [
            {"portname": port, "vessel_class": vessel_class}
            for port, vessel_class in protocol.primary_keys
        ],
        "negative_controls": [
            {"portname": port, "vessel_class": vessel_class}
            for port, vessel_class in protocol.control_keys
        ],
        "inference": {
            "method": "synchronized_circular_moving_block_bootstrap_plus_Romano_Wolf",
            "horizon_days": protocol.horizon,
            "primary_block_length_days": protocol.block_length,
            "sensitivity_block_lengths_days": list(protocol.sensitivity_block_lengths),
            "draws": protocol.n_draws,
            "seed": protocol.seed,
        },
        "outputs_sha256": {str(path.relative_to(ROOT)): _sha256(path) for path in output_paths},
        "interpretation_guard": protocol.claim,
    }
    protocol.outputs["manifest"].write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print("=== 14-day block primary tanker results ===")
    print(primary_results[[
        "model", "portname", "event_statistic", "cumulative_gap",
        "raw_resampling_p_value", "romano_wolf_p_value",
    ]].sort_values(["model", "event_statistic"], ascending=[True, False]).to_string(index=False))
    print("\n=== global tests ===")
    print(global_tests.loc[global_tests["block_length_days"].eq(protocol.block_length)].to_string(index=False))
    print(f"\nwrote {protocol.outputs['inference']}")
    print(f"wrote {protocol.outputs['validation']}")


if __name__ == "__main__":
    main()
