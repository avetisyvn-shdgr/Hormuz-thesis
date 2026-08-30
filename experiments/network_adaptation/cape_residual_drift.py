"""Test whether the Red Sea diversion left the Cape counterfactual unreliable.

Traffic diverted from the Red Sea to the Cape of Good Hope from December 2023.
Both forecasters train through 2026-02-27, so both have seen two years of the
elevated regime -- but a corridor still in transition would leave drifting
pre-event residuals, and the synchronized block bootstrap in
``experiments.network_adaptation.inference`` assumes those residuals supply a
weakly stationary reference for the event window.

This refits nothing.  It reads the executed 130-day out-of-sample residual
vectors from the panel bake-off (eight origins x 130 days per series) and asks
three questions of the five restricted corridors:

1. Does the mean residual shift across the diversion onset?
2. Does it drift within an origin, as a corridor still repricing would?
3. How much of each corridor's event statistic survives if the historical
   reference is centred on the recent regime rather than on all eight origins?

Run with:

    MPLBACKEND=Agg .venv/bin/python -m experiments.network_adaptation.cape_residual_drift
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from experiments.network_adaptation.protocol import AdaptationProtocol, load_protocol
from experiments.panel_bakeoff.protocol import file_sha256, load_raw_panel


ROOT = Path(__file__).resolve().parents[2]
FORECAST_FILES = {
    "chronos2_univariate": ROOT / "experiments/panel_bakeoff/outputs/chronos_forecasts.csv.gz",
    "ar_lag1_7": ROOT / "experiments/panel_bakeoff/outputs/classical_forecasts.csv.gz",
}
PANEL = "composition_28x5"
SUSPECT = "Cape of Good Hope"
# Red Sea transits collapsed and Cape routings began from December 2023.
DIVERSION_ONSET = pd.Timestamp("2023-12-01")
# The last three origins are the closest analogue to the event window's
# information state: they are the regime the 2026 counterfactual extrapolates.
RECENT_ORIGINS = 3


def _residuals(protocol: AdaptationProtocol) -> pd.DataFrame:
    """Executed 130-day OOS residuals for the restricted corridors, one row a day."""
    wanted = set(protocol.primary_corridors)
    frames = []
    for model, path in FORECAST_FILES.items():
        frame = pd.read_csv(
            path,
            parse_dates=["origin", "date"],
            usecols=[
                "model", "panel", "fold", "horizon", "origin", "portname",
                "vessel_class", "date", "lead", "y_true", "y_pred",
            ],
        )
        frame = frame.loc[
            frame["model"].eq(model)
            & frame["panel"].eq(PANEL)
            & frame["horizon"].eq(protocol.horizon)
            & frame["vessel_class"].eq(protocol.primary_class)
            & frame["portname"].isin(wanted)
        ]
        frames.append(frame)
    residuals = pd.concat(frames, ignore_index=True)
    if residuals["date"].max() >= protocol.cutoff:
        raise ValueError("historical residuals reach the event cutoff.")
    counts = residuals.groupby(["model", "portname"]).size()
    if not counts.eq(8 * protocol.horizon).all():
        raise ValueError(f"expected 8 x {protocol.horizon} residual days per series.")
    residuals["residual"] = residuals["y_true"] - residuals["y_pred"]
    return residuals


def _pre_event_means(raw: pd.DataFrame, protocol: AdaptationProtocol) -> pd.Series:
    pre = raw.loc[raw["date"] < protocol.cutoff]
    means = pre.groupby("portname")[protocol.primary_class].mean()
    return means.loc[list(protocol.primary_corridors)]


def _annual_level(raw: pd.DataFrame, protocol: AdaptationProtocol) -> dict[str, float]:
    """Cape tanker traffic by year, which is what the diversion actually moved."""
    cape = raw.loc[raw["portname"].eq(SUSPECT)]
    yearly = cape.groupby(cape["date"].dt.year)[protocol.primary_class].mean()
    return {str(int(year)): round(float(value), 2) for year, value in yearly.items()}


def _fold_04_decomposition(protocol: AdaptationProtocol) -> dict[str, float]:
    """The one origin where Chronos loses the 130-day panel, with and without Cape.

    RESULTS.md reports that Chronos loses at one of eight origins. If that loss is
    a Cape regime-break artifact rather than a general weakness, the write-up has
    to say so.
    """
    scores = pd.concat(
        [
            pd.read_csv(ROOT / f"experiments/panel_bakeoff/outputs/{name}")
            for name in ("chronos_scores.csv", "classical_scores.csv")
        ],
        ignore_index=True,
    )
    scores = scores.loc[
        scores["panel"].eq(PANEL)
        & scores["horizon"].eq(protocol.horizon)
        & scores["model"].isin({protocol.primary_model, protocol.robustness_model})
    ]
    paired = scores.pivot_table(
        index=["fold", "portname", "vessel_class"], columns="model", values="mase"
    ).reset_index()
    losing = (
        paired.groupby("fold")
        .apply(
            lambda part: 1.0
            - part[protocol.primary_model].mean() / part[protocol.robustness_model].mean(),
            include_groups=False,
        )
        .idxmin()
    )
    part = paired.loc[paired["fold"].eq(losing)]
    without = part.loc[~part["portname"].eq(SUSPECT)]
    reduction = lambda frame: 1.0 - frame[protocol.primary_model].mean() / frame[
        protocol.robustness_model
    ].mean()
    worst = part.assign(
        gap=part[protocol.primary_model] - part[protocol.robustness_model]
    ).nlargest(1, "gap").iloc[0]
    return {
        "fold": str(losing),
        "reduction_all_series": float(reduction(part)),
        "reduction_excluding_cape": float(reduction(without)),
        "worst_series": f"{worst['portname']}/{worst['vessel_class']}",
        "worst_series_chronos_mase": float(worst[protocol.primary_model]),
        "worst_series_ar_mase": float(worst[protocol.robustness_model]),
    }


def _regime(origin: pd.Timestamp, horizon: int) -> str:
    end = origin + pd.Timedelta(days=horizon - 1)
    if end < DIVERSION_ONSET:
        return "pre_diversion"
    if origin < DIVERSION_ONSET:
        return "straddles_onset"
    return "post_diversion"


def _by_origin(
    residuals: pd.DataFrame, pre_means: pd.Series, protocol: AdaptationProtocol
) -> pd.DataFrame:
    rows = []
    for (model, portname, fold), part in residuals.groupby(
        ["model", "portname", "fold"], sort=True
    ):
        part = part.sort_values("lead")
        origin = part["origin"].iloc[0]
        scale = float(pre_means[portname])
        slope = float(np.polyfit(part["lead"].to_numpy(), part["residual"].to_numpy(), 1)[0])
        rows.append({
            "model": model,
            "portname": portname,
            "fold": fold,
            "origin": str(origin.date()),
            "scored_end": str(part["date"].max().date()),
            "regime": _regime(origin, protocol.horizon),
            "n_days": len(part),
            "pre_event_mean": scale,
            "mean_residual": float(part["residual"].mean()),
            "scaled_mean_residual": float(part["residual"].mean()) / scale,
            "residual_lead_slope": slope,
            "scaled_residual_lead_slope": slope / scale,
        })
    return pd.DataFrame(rows).sort_values(
        ["model", "portname", "fold"], kind="stable", ignore_index=True
    )


def _drift(by_origin: pd.DataFrame, event: pd.DataFrame) -> pd.DataFrame:
    """Per corridor: regime shift, and the event statistic under each centring."""
    rows = []
    for (model, portname), part in by_origin.groupby(["model", "portname"], sort=True):
        part = part.sort_values("fold")
        scaled = part["scaled_mean_residual"]
        before = scaled.loc[part["regime"].ne("post_diversion")]
        after = scaled.loc[part["regime"].eq("post_diversion")]
        recent = scaled.iloc[-RECENT_ORIGINS:]
        statistic = float(
            event.loc[
                event["model"].eq(model) & event["portname"].eq(portname), "event_statistic"
            ].iloc[0]
        )
        index = np.arange(1, len(scaled) + 1, dtype="float64")
        rows.append({
            "model": model,
            "portname": portname,
            "pooled_reference_mean": float(scaled.mean()),
            "pre_and_straddling_mean": float(before.mean()),
            "post_diversion_mean": float(after.mean()),
            "onset_shift": float(after.mean() - before.mean()),
            "recent_regime_mean": float(recent.mean()),
            "pooled_minus_recent": float(scaled.mean() - recent.mean()),
            "reduction_slope_per_origin": float(np.polyfit(index, scaled.to_numpy(), 1)[0]),
            "event_statistic": statistic,
            "excess_over_pooled_reference": statistic - float(scaled.mean()),
            "excess_over_recent_reference": statistic - float(recent.mean()),
            "share_of_event_statistic_absorbed": (
                float(recent.mean()) / statistic if statistic else float("nan")
            ),
        })
    return pd.DataFrame(rows)


def _make_figure(by_origin: pd.DataFrame, protocol: AdaptationProtocol, path: Path) -> None:
    models = [protocol.primary_model, protocol.robustness_model]
    labels = {protocol.primary_model: "Chronos-2", protocol.robustness_model: "AR(1,7)"}
    others = [c for c in protocol.primary_corridors if c != SUSPECT]
    folds = sorted(by_origin["fold"].unique())
    x = np.arange(1, len(folds) + 1)
    fig, axes = plt.subplots(1, 2, figsize=(12.5, 5.4), sharey=True)
    for ax, model in zip(axes, models):
        part = by_origin.loc[by_origin["model"].eq(model)]
        for corridor in others:
            series = part.loc[part["portname"].eq(corridor)].set_index("fold")
            ax.plot(
                x, series.loc[folds, "scaled_mean_residual"], color="#B0B0B0",
                linewidth=1.4, marker="o", markersize=3.5, zorder=2,
            )
        cape = part.loc[part["portname"].eq(SUSPECT)].set_index("fold")
        ax.plot(
            x, cape.loc[folds, "scaled_mean_residual"], color="#D55E00", linewidth=2.4,
            marker="o", markersize=6, zorder=3, label=SUSPECT,
        )
        onset = [
            i for i, fold in zip(x, folds)
            if cape.loc[fold, "regime"] == "straddles_onset"
        ]
        if onset:
            ax.axvline(onset[0], color="#333333", linewidth=0.9, linestyle=":")
            ax.text(
                onset[0] + 0.1, 0.97, "Red Sea diversion",
                transform=ax.get_xaxis_transform(), fontsize=8.5,
                color="#333333", va="top",
            )
        ax.axhline(0, color="#333333", linewidth=0.9, linestyle="--")
        ax.set_xticks(x, [f.replace("fold_", "") for f in folds])
        ax.set_xlabel("Rolling origin")
        ax.set_title(labels[model], loc="left", fontweight="bold")
        ax.spines[["top", "right"]].set_visible(False)
        ax.grid(axis="y", color="#E5E5E5", linewidth=0.7)
    axes[0].set_ylabel("Mean 130-day OOS residual / pre-event mean")
    axes[0].legend(frameon=False, loc="lower right", fontsize=9)
    fig.suptitle(
        "Only the Cape corridor's forecast residuals shift with the Red Sea diversion",
        x=0.06, ha="left", fontsize=14, fontweight="bold",
    )
    fig.text(
        0.06, 0.925,
        "Grey lines are the other four restricted corridors. Positive values mean the model under-predicted tanker traffic; "
        "Chronos's origin-4 spike is an over-prediction.",
        ha="left", fontsize=9.5, color="#444444",
    )
    fig.text(
        0.06, 0.015,
        "Source: executed 28 x 5 panel bake-off, eight disjoint 130-day origins, 2023-01-01 to 2025-11-05. Tanker counts only.",
        ha="left", fontsize=8.5, color="#555555",
    )
    fig.tight_layout(rect=[0.04, 0.05, 1, 0.9])
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=240, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    protocol = load_protocol()
    if file_sha256(protocol.raw_path) != protocol.expected_raw_sha256:
        raise RuntimeError("the PortWatch snapshot hash changed.")

    raw = load_raw_panel(protocol.raw_path)
    residuals = _residuals(protocol)
    pre_means = _pre_event_means(raw, protocol)
    by_origin = _by_origin(residuals, pre_means, protocol)

    inference = pd.read_csv(protocol.outputs["inference"])
    event = inference.loc[
        inference["family"].eq("restricted_tanker_adaptation")
        & inference["block_length_days"].eq(protocol.block_length)
    ]
    drift = _drift(by_origin, event)

    cape = drift.loc[drift["portname"].eq(SUSPECT)].set_index("model")
    others = drift.loc[~drift["portname"].eq(SUSPECT)]
    summary = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "question": (
            "Did the December 2023 Red Sea diversion leave the Cape corridor's "
            "pre-event residuals non-stationary, and therefore its 2026 "
            "counterfactual and bootstrap reference unreliable?"
        ),
        "diversion_onset": str(DIVERSION_ONSET.date()),
        "recent_regime_origins": RECENT_ORIGINS,
        "cape_annual_mean_tanker_transits": _annual_level(raw, protocol),
        "losing_origin_decomposition": _fold_04_decomposition(protocol),
        "cape_onset_shift": {
            model: float(cape.loc[model, "onset_shift"]) for model in cape.index
        },
        "largest_non_cape_onset_shift": float(others["onset_shift"].abs().max()),
        "cape_is_the_largest_onset_shift": bool(
            cape["onset_shift"].abs().max() > others["onset_shift"].abs().max()
        ),
        "cape_event_statistic_excess": {
            model: {
                "over_pooled_reference": float(cape.loc[model, "excess_over_pooled_reference"]),
                "over_recent_reference": float(cape.loc[model, "excess_over_recent_reference"]),
            }
            for model in cape.index
        },
        "verdict": (
            "demoted_to_context" if bool(
                cape["onset_shift"].abs().max() > others["onset_shift"].abs().max()
            ) else "exonerated"
        ),
        "what_this_cannot_show": (
            "A regime-matched reference mean is a descriptive re-centring, not a "
            "re-estimated test. It quantifies how much of the Cape event statistic "
            "the pooled reference leaves uncharged; it does not supply a corrected "
            "p-value, and the residual process it re-centres on is itself short."
        ),
    }
    by_origin.to_csv(protocol.outputs["cape_drift"], index=False)
    drift.to_csv(protocol.outputs["cape_drift_summary"], index=False)
    protocol.outputs["cape_drift_manifest"].write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    _make_figure(by_origin, protocol, protocol.outputs["cape_drift_figure"])

    pivot = by_origin.pivot_table(
        index=["model", "portname"], columns="fold", values="scaled_mean_residual"
    )
    print("=== mean 130-day OOS residual / pre-event mean, by origin ===")
    print(pivot.round(3).to_string())
    print("\n=== reference centring and what it charges the event statistic ===")
    print(
        drift[[
            "model", "portname", "pooled_reference_mean", "post_diversion_mean",
            "recent_regime_mean", "event_statistic", "excess_over_pooled_reference",
            "excess_over_recent_reference",
        ]].round(3).to_string(index=False)
    )
    print(f"\nCape annual mean tanker transits: {summary['cape_annual_mean_tanker_transits']}")
    losing = summary["losing_origin_decomposition"]
    print(
        f"{losing['fold']} 130-day panel reduction: {losing['reduction_all_series']:+.4f} "
        f"with Cape, {losing['reduction_excluding_cape']:+.4f} without it "
        f"(worst cell {losing['worst_series']}: Chronos MASE "
        f"{losing['worst_series_chronos_mase']:.2f} vs AR {losing['worst_series_ar_mase']:.2f})"
    )
    print(f"verdict: {summary['verdict']}")
    print(f"\nwrote {protocol.outputs['cape_drift']}")
    print(f"wrote {protocol.outputs['cape_drift_summary']}")


if __name__ == "__main__":
    main()
