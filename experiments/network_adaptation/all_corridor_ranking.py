"""Rank every chokepoint, so nobody has to ask why these five.

**This is disclosure, not inference repair.** Romano-Wolf controls multiplicity
conditional on the family tested. It cannot recreate a selection that did not
happen, and every one of these 28 post-event results had already been inspected
in an earlier all-corridor AR map before the restricted five were named. Nothing
this script produces is confirmatory, and every artifact it writes says so.

What it buys is a better position to defend. "Why these five?" has no good
answer. A full ranking in which the five are simply visible, with family-wide
adjusted values computed over all 28 rather than over the chosen subset, at
least lets a reader see what was left out.

The family here is deliberately the widest one available, so the multiplicity
correction is the harshest: 28 corridors rather than five. The restricted five
are labelled, the treated anchor and the two context corridors are labelled, and
the volume-eligibility flag from the control-robustness work is carried through.

This refits nothing. It reads the executed event forecasts and the executed
pre-event residual vectors.

Run with:

    MPLBACKEND=Agg .venv/bin/python -m experiments.network_adaptation.all_corridor_ranking
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from experiments.network_adaptation.analyze import (
    event_statistics,
    hypothesis_name,
    load_event,
    pre_event_means,
    validation_residuals,
)
from experiments.network_adaptation.control_robustness import (
    family_weights,
    volume_eligible,
)
from experiments.network_adaptation.inference import (
    global_mean_test,
    scale_columns,
    synchronized_circular_mbb,
)
from experiments.network_adaptation.protocol import AdaptationProtocol, load_protocol
from experiments.panel_bakeoff.protocol import file_sha256, load_raw_panel
from lngfreight.inference import romano_wolf_stepdown


ROOT = Path(__file__).resolve().parents[2]
FAMILY = "all_28_corridors_retrospective"
STATUS = "retrospective_disclosure_not_confirmatory"
TREATED_ANCHOR = "Strait of Hormuz"


def _corridor_keys(raw: pd.DataFrame, protocol: AdaptationProtocol) -> tuple[tuple[str, str], ...]:
    ports = sorted(raw["portname"].unique())
    if len(ports) != 28:
        raise ValueError(f"expected 28 chokepoints, found {len(ports)}.")
    return tuple((port, protocol.primary_class) for port in ports)


def _rank(
    stats: pd.DataFrame,
    draws: pd.DataFrame,
    names: list[str],
    block_length: int,
    protocol: AdaptationProtocol,
    model: str,
) -> pd.DataFrame:
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
    out["model"] = model
    out["family"] = FAMILY
    out["status"] = STATUS
    out["block_length_days"] = block_length
    out["in_restricted_five"] = out["portname"].isin(protocol.primary_corridors)
    out["is_treated_anchor"] = out["portname"].eq(TREATED_ANCHOR)
    out["is_context_corridor"] = out["portname"].isin(protocol.context_corridors)
    out["volume_eligible"] = out["pre_event_mean"].ge(protocol.control_minimum_daily_transits)
    return out.reset_index(drop=True)


def _make_figure(ranking: pd.DataFrame, protocol: AdaptationProtocol, path: Path) -> None:
    part = ranking.loc[
        ranking["model"].eq(protocol.primary_model)
        & ranking["block_length_days"].eq(protocol.block_length)
    ].sort_values("studentized_statistic")
    y = np.arange(len(part))
    colors = []
    for _, row in part.iterrows():
        if row["is_treated_anchor"]:
            colors.append("#111111")
        elif row["in_restricted_five"]:
            colors.append("#D55E00")
        elif row["is_context_corridor"]:
            colors.append("#0072B2")
        else:
            colors.append("#B4B4B4")
    fig, ax = plt.subplots(figsize=(10.5, 9.6))
    ax.hlines(y, 0, part["studentized_statistic"], color=colors, linewidth=2.4, alpha=0.55)
    ax.scatter(part["studentized_statistic"], y, color=colors, s=52, zorder=3)
    ax.axvline(0, color="#333333", linewidth=0.9, linestyle="--")
    ax.set_yticks(y, part["portname"], fontsize=9)
    for tick, row in zip(ax.get_yticklabels(), part.itertuples()):
        if row.in_restricted_five:
            tick.set_color("#D55E00")
            tick.set_fontweight("bold")
        elif row.is_treated_anchor:
            tick.set_fontweight("bold")
    ax.set_xlabel("Studentized event statistic (higher is further above counterfactual)")
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="x", color="#EDEDED", linewidth=0.7)
    ax.grid(axis="y", visible=False)
    handles = [
        plt.Line2D([], [], marker="o", linestyle="", color="#D55E00", label="Restricted five (retrospective)"),
        plt.Line2D([], [], marker="o", linestyle="", color="#0072B2", label="Context corridor"),
        plt.Line2D([], [], marker="o", linestyle="", color="#111111", label="Treated anchor"),
        plt.Line2D([], [], marker="o", linestyle="", color="#B4B4B4", label="Not selected"),
    ]
    ax.legend(handles=handles, frameon=False, loc="upper left", fontsize=9)
    fig.suptitle(
        "All 28 chokepoints, ranked — the restricted five in context",
        x=0.02, ha="left", fontsize=14, fontweight="bold",
    )
    fig.text(
        0.02, 0.945,
        "Tanker counts, 130 days from 28 Feb 2026. Romano-Wolf adjusted over all 28, not over the chosen subset. "
        "Retrospective: these results were visible before the five were named.",
        ha="left", fontsize=9, color="#444444",
    )
    fig.tight_layout(rect=[0, 0.01, 1, 0.93])
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=240, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    protocol = load_protocol()
    if file_sha256(protocol.raw_path) != protocol.expected_raw_sha256:
        raise RuntimeError("the PortWatch snapshot hash changed.")
    raw = load_raw_panel(protocol.raw_path)
    event = load_event(protocol)
    keys = _corridor_keys(raw, protocol)
    means = pre_event_means(raw, keys, protocol.cutoff)
    names = [hypothesis_name(port, cls) for port, cls in keys]

    rows: list[pd.DataFrame] = []
    global_rows: list[dict[str, object]] = []
    block_lengths = (protocol.block_length, *protocol.sensitivity_block_lengths)
    for model_index, model in enumerate((protocol.primary_model, protocol.robustness_model)):
        historical = validation_residuals(model, keys, protocol)
        stats = event_statistics(event, model, keys, means)
        for block_length in block_lengths:
            draws = scale_columns(
                synchronized_circular_mbb(
                    historical,
                    horizon=protocol.horizon,
                    block_length=block_length,
                    n_draws=protocol.n_draws,
                    seed=protocol.seed + 1000 * model_index + block_length,
                ),
                means,
            )
            rows.append(_rank(stats, draws, names, block_length, protocol, model))
            eligible = volume_eligible(protocol, means, names)
            for scheme in protocol.control_weighting_schemes:
                global_rows.append({
                    "model": model,
                    "block_length_days": block_length,
                    "variant": "all_28_corridors",
                    "weighting": scheme,
                    "n_series": len(names),
                    **global_mean_test(
                        stats.loc[names, "event_statistic"],
                        draws.reindex(columns=names),
                        family_weights(scheme, names, draws, means),
                    ),
                })
            global_rows.append({
                "model": model,
                "block_length_days": block_length,
                "variant": "volume_eligible_corridors",
                "weighting": "equal",
                "n_series": len(eligible),
                **global_mean_test(
                    stats.loc[eligible, "event_statistic"], draws.reindex(columns=eligible)
                ),
            })

    ranking = pd.concat(rows, ignore_index=True).sort_values(
        ["model", "block_length_days", "studentized_statistic"],
        ascending=[True, True, False],
        kind="stable",
        ignore_index=True,
    )
    global_tests = pd.DataFrame(global_rows).sort_values(
        ["model", "block_length_days", "variant", "weighting"], kind="stable", ignore_index=True
    )

    primary = ranking.loc[
        ranking["model"].eq(protocol.primary_model)
        & ranking["block_length_days"].eq(protocol.block_length)
    ].reset_index(drop=True)
    positions = {
        str(row["portname"]): index + 1
        for index, row in primary.iterrows()
        if row["in_restricted_five"]
    }
    flagged = ranking.loc[ranking["romano_wolf_p_value"].lt(0.05)]

    summary = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": STATUS,
        "purpose": (
            "Descriptive disclosure of the full corridor ranking. The restricted "
            "five were named after these results existed; family-wide adjustment "
            "over 28 hypotheses does not make any of them confirmatory."
        ),
        "family_size": len(names),
        "restricted_five_positions_primary_model_primary_block": positions,
        "corridors_flagged_below_0_05": {
            f"{model}::{int(block)}": sorted(part["portname"].unique())
            for (model, block), part in flagged.groupby(["model", "block_length_days"])
        },
        "restricted_five_share_of_flagged": {
            f"{model}::{int(block)}": [
                int(part["in_restricted_five"].sum()),
                int(len(part)),
            ]
            for (model, block), part in flagged.groupby(["model", "block_length_days"])
        },
        "corridors_flagged_outside_the_restricted_five": sorted(
            flagged.loc[
                ~flagged["in_restricted_five"] & ~flagged["is_context_corridor"], "portname"
            ].unique()
        ),
        "treated_anchor_rank_from_bottom": int(
            len(primary) - primary.index[primary["is_treated_anchor"]][0]
        ),
        "global_by_weighting_primary_block": {
            f"{row['model']}::{row['variant']}::{row['weighting']}": {
                "observed_global_statistic": float(row["observed_global_statistic"]),
                "one_sided_bootstrap_p_value": float(row["one_sided_bootstrap_p_value"]),
            }
            for _, row in global_tests.loc[
                global_tests["block_length_days"].eq(protocol.block_length)
            ].iterrows()
        },
        "what_this_cannot_show": (
            "Adjusting over 28 hypotheses instead of five is a harsher correction, "
            "not a prospective one. No p-value here is confirmatory, and the "
            "ranking must never be presented as a discovery procedure that "
            "independently selected the five."
        ),
    }

    ranking.to_csv(protocol.outputs["all_corridor_ranking"], index=False)
    global_tests.to_csv(protocol.outputs["all_corridor_global_tests"], index=False)
    protocol.outputs["all_corridor_manifest"].write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    _make_figure(ranking, protocol, protocol.outputs["all_corridor_figure"])

    columns = [
        "portname", "pre_event_mean", "event_statistic", "studentized_statistic",
        "romano_wolf_p_value", "in_restricted_five", "volume_eligible",
    ]
    print(f"=== {protocol.primary_model}, {protocol.block_length}-day blocks, all 28 ===")
    print(primary[columns].round(4).to_string(index=False))
    print(f"\nrestricted five at positions: {positions}")
    print(f"flagged outside the five: {summary['corridors_flagged_outside_the_restricted_five']}")
    print(f"\nwrote {protocol.outputs['all_corridor_ranking']}")


if __name__ == "__main__":
    main()
