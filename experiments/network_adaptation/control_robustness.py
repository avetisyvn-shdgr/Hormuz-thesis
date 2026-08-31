"""Measure whether the negative-control family can falsify anything.

The specificity argument in the secondary chapter turns on one comparison:
Chronos's global Ro-Ro/dry-bulk statistic is unremarkable against its historical
reference, AR's is not.  That comparison is only informative if the control
family has power.  It may not: ``global_mean_test`` weights every control series
equally after scaling, so Cape Ro-Ro at a pre-event mean of 1.77 transits a day
moves the global statistic exactly as much as Malacca dry bulk at 50.5, while
carrying a reference range several times its own mean.  A control distribution
that wide would let Chronos pass the specificity test for the wrong reason.

This refits nothing.  It re-runs the global control test under every variant the
remediation plan declared, using the same executed residual vectors, the same
seeds and the same synchronized bootstrap:

* the full ten-control family, equal-weighted, retained and reported whatever
  the other variants say;
* the same family under inverse-reference-variance and pre-event-volume weights;
* a pre-event minimum daily-volume eligibility rule, threshold declared in
  ``config/network_adaptation.yaml`` before this ran and computed on pre-event
  data only;
* ten leave-one-control-out refits.

It also reports what the family could detect: the smallest global control
statistic that would reach p <= 0.05, next to the tanker family's own observed
statistic.  If the control family cannot flag a movement the size of the one the
primary family found, it is not a falsification test.

No control is removed on the basis of a post-event result. The eligibility rule
is volume-based and pre-event, or it would reproduce the selection problem the
control family exists to guard against.

Run with:

    .venv/bin/python -m experiments.network_adaptation.control_robustness
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from experiments.network_adaptation.analyze import (
    event_statistics,
    hypothesis_name,
    load_event,
    pre_event_means,
    validation_residuals,
)
from experiments.network_adaptation.inference import (
    global_mean_test,
    scale_columns,
    synchronized_circular_mbb,
)
from experiments.network_adaptation.protocol import AdaptationProtocol, load_protocol
from experiments.panel_bakeoff.protocol import file_sha256, load_raw_panel


ROOT = Path(__file__).resolve().parents[2]
FULL_FAMILY = "full_ten_control_family"
ELIGIBLE_FAMILY = "volume_eligible_controls"
LEAVE_ONE_OUT = "leave_one_control_out"


def family_weights(
    scheme: str,
    names: list[str],
    draws: pd.DataFrame,
    volumes: pd.Series,
) -> pd.Series | None:
    """Pre-event weights for one scheme; None keeps the equal-weighted statistic."""
    if scheme == "equal":
        return None
    if scheme == "inverse_reference_variance":
        variance = draws.loc[:, names].var(ddof=1)
        if not np.isfinite(variance).all() or variance.le(0).any():
            raise ValueError("a control series has a degenerate reference variance.")
        return 1.0 / variance
    if scheme == "pre_event_volume":
        return volumes.reindex(names)
    raise ValueError(f"undeclared weighting scheme {scheme!r}.")


def volume_eligible(
    protocol: AdaptationProtocol, volumes: pd.Series, names: list[str]
) -> list[str]:
    keep = [
        name for name in names
        if float(volumes[name]) >= protocol.control_minimum_daily_transits
    ]
    if not keep:
        raise ValueError("the declared volume threshold excludes every control.")
    return keep


def _row(
    protocol: AdaptationProtocol,
    *,
    family: str,
    model: str,
    block_length: int,
    variant: str,
    scheme: str,
    names: list[str],
    dropped: str,
    observed: pd.Series,
    draws: pd.DataFrame,
    volumes: pd.Series,
    primary_global: float,
) -> dict[str, object]:
    weights = family_weights(scheme, names, draws, volumes)
    result = global_mean_test(observed.loc[names], draws.loc[:, names], weights)
    threshold = result["reference_q950"]
    is_control = family == "non_tanker_negative_controls"
    return {
        "family": family,
        "model": model,
        "block_length_days": block_length,
        "variant": variant,
        "weighting": scheme,
        "n_series": len(names),
        "dropped_control": dropped,
        "minimum_pre_event_daily_transits": float(volumes.loc[names].min()),
        **result,
        "equal_weighted_tanker_global": primary_global,
        "minimum_detectable_global_statistic": threshold,
        "would_flag_a_tanker_sized_movement": (
            bool(primary_global > threshold) if is_control else None
        ),
    }


def _variants(
    protocol: AdaptationProtocol,
    *,
    family: str,
    model: str,
    block_length: int,
    observed: pd.Series,
    draws: pd.DataFrame,
    volumes: pd.Series,
    primary_global: float,
) -> list[dict[str, object]]:
    names = list(observed.index)
    common = {
        "protocol": protocol,
        "family": family,
        "model": model,
        "block_length": block_length,
        "observed": observed,
        "draws": draws,
        "volumes": volumes,
        "primary_global": primary_global,
    }
    rows = [
        _row(variant=FULL_FAMILY, scheme=scheme, names=names, dropped="", **common)
        for scheme in protocol.control_weighting_schemes
    ]
    eligible = volume_eligible(protocol, volumes, names)
    if eligible != names:
        rows.append(
            _row(variant=ELIGIBLE_FAMILY, scheme="equal", names=eligible, dropped="", **common)
        )
    for name in names:
        rows.append(
            _row(
                variant=LEAVE_ONE_OUT,
                scheme="equal",
                names=[other for other in names if other != name],
                dropped=name,
                **common,
            )
        )
    return rows


def main() -> None:
    protocol = load_protocol()
    if file_sha256(protocol.raw_path) != protocol.expected_raw_sha256:
        raise RuntimeError("the PortWatch snapshot hash changed.")

    raw = load_raw_panel(protocol.raw_path)
    event = load_event(protocol)
    all_keys = tuple(
        dict.fromkeys(protocol.primary_keys + protocol.control_keys + protocol.context_keys)
    )
    means = pre_event_means(raw, all_keys, protocol.cutoff)
    control_names = [hypothesis_name(port, cls) for port, cls in protocol.control_keys]
    primary_names = [hypothesis_name(port, cls) for port, cls in protocol.primary_keys]

    rows: list[dict[str, object]] = []
    block_lengths = (protocol.block_length, *protocol.sensitivity_block_lengths)
    for model_index, model in enumerate((protocol.primary_model, protocol.robustness_model)):
        historical = validation_residuals(model, all_keys, protocol)
        stats = event_statistics(event, model, all_keys, means)
        observed = stats["event_statistic"]
        primary_global = float(observed.loc[primary_names].mean())
        for block_length in block_lengths:
            raw_draws = synchronized_circular_mbb(
                historical,
                horizon=protocol.horizon,
                block_length=block_length,
                n_draws=protocol.n_draws,
                seed=protocol.seed + 1000 * model_index + block_length,
            )
            draws = scale_columns(raw_draws, means)
            for family, names in (
                ("non_tanker_negative_controls", control_names),
                ("restricted_tanker_adaptation", primary_names),
            ):
                rows.extend(
                    _variants(
                        protocol,
                        family=family,
                        model=model,
                        block_length=block_length,
                        observed=observed.loc[names],
                        draws=draws.loc[:, names],
                        volumes=means.loc[names],
                        primary_global=primary_global,
                    )
                )

    table = pd.DataFrame(rows).sort_values(
        ["family", "model", "block_length_days", "variant", "weighting", "dropped_control"],
        kind="stable",
        ignore_index=True,
    )

    controls = table.loc[table["family"].eq("non_tanker_negative_controls")]
    tanker = table.loc[table["family"].eq("restricted_tanker_adaptation")]
    tanker_full = tanker.loc[tanker["variant"].eq(FULL_FAMILY)]
    primary_block = controls["block_length_days"].eq(protocol.block_length)
    chronos = controls.loc[controls["model"].eq(protocol.primary_model)]
    ar_controls = controls.loc[controls["model"].eq(protocol.robustness_model)]
    chronos_primary = chronos.loc[primary_block]
    eligible_names = volume_eligible(protocol, means.loc[control_names], control_names)
    full_width = float(
        chronos.loc[
            chronos["block_length_days"].eq(protocol.block_length)
            & chronos["variant"].eq(FULL_FAMILY)
            & chronos["weighting"].eq("equal"),
            "reference_q950",
        ].iloc[0]
    )
    summary = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "question": (
            "Does the Chronos specificity result survive a hardened negative-control "
            "family, and can that family falsify anything at all?"
        ),
        "declared_before_running": {
            "minimum_pre_event_daily_transits": protocol.control_minimum_daily_transits,
            "source": "Research Record/plan-technical-remediation.md item T1.1",
            "computed_on": "pre_event_observations_only",
            "no_post_event_removal": True,
        },
        "controls_excluded_by_volume_rule": sorted(
            set(control_names).difference(eligible_names)
        ),
        "controls_retained_by_volume_rule": sorted(eligible_names),
        "chronos_control_p_value_range_primary_block": [
            float(chronos_primary["one_sided_bootstrap_p_value"].min()),
            float(chronos_primary["one_sided_bootstrap_p_value"].max()),
        ],
        "chronos_control_p_value_range_all_blocks": [
            float(chronos["one_sided_bootstrap_p_value"].min()),
            float(chronos["one_sided_bootstrap_p_value"].max()),
        ],
        "chronos_specificity_survives_every_variant": bool(
            chronos["one_sided_bootstrap_p_value"].gt(0.05).all()
        ),
        "family_can_flag_a_tanker_sized_movement": {
            variant: bool(part["would_flag_a_tanker_sized_movement"].all())
            for variant, part in chronos_primary.groupby("variant")
        },
        "full_family_reference_q950": full_width,
        "widest_single_control_contribution": (
            chronos_primary.loc[chronos_primary["variant"].eq(LEAVE_ONE_OUT)]
            .assign(
                shift=lambda frame: (
                    frame["minimum_detectable_global_statistic"]
                    - float(
                        chronos_primary.loc[
                            chronos_primary["variant"].eq(FULL_FAMILY)
                            & chronos_primary["weighting"].eq("equal"),
                            "minimum_detectable_global_statistic",
                        ].iloc[0]
                    )
                )
            )
            .nsmallest(1, "shift")[["dropped_control", "shift"]]
            .to_dict(orient="records")[0]
        ),
        "ar_control_p_value_by_variant_primary_block": {
            f"{row['variant']}::{row['weighting']}::{row['dropped_control']}".rstrip(":"): float(
                row["one_sided_bootstrap_p_value"]
            )
            for _, row in ar_controls.loc[
                ar_controls["block_length_days"].eq(protocol.block_length)
            ].iterrows()
        },
        "ar_control_failure_is_equal_weighting_only": bool(
            ar_controls.loc[
                ar_controls["variant"].eq(FULL_FAMILY)
                & ar_controls["weighting"].eq("equal"),
                "one_sided_bootstrap_p_value",
            ].lt(0.05).all()
            and ar_controls.loc[
                ar_controls["variant"].eq(ELIGIBLE_FAMILY)
                | ar_controls["weighting"].ne("equal"),
                "one_sided_bootstrap_p_value",
            ].gt(0.05).all()
        ),
        "tanker_family_p_value_range_by_model": {
            model: [
                float(part["one_sided_bootstrap_p_value"].min()),
                float(part["one_sided_bootstrap_p_value"].max()),
            ]
            for model, part in tanker.groupby("model")
        },
        "tanker_family_global_is_weighting_sensitive": bool(
            tanker_full.loc[
                tanker_full["weighting"].eq("equal"), "one_sided_bootstrap_p_value"
            ].lt(0.05).all()
            and tanker_full.loc[
                tanker_full["weighting"].ne("equal"), "one_sided_bootstrap_p_value"
            ].gt(0.05).all()
        ),
        "tanker_family_global_leave_one_corridor_out_primary_block": {
            f"{row['model']}::drop {row['dropped_control']}": {
                "observed_global_statistic": float(row["observed_global_statistic"]),
                "one_sided_bootstrap_p_value": float(row["one_sided_bootstrap_p_value"]),
            }
            for _, row in tanker.loc[
                tanker["block_length_days"].eq(protocol.block_length)
                & tanker["variant"].eq(LEAVE_ONE_OUT)
            ].iterrows()
        },
        "control_reference_width_shift_when_a_control_is_dropped": {
            row["dropped_control"]: float(row["reference_q950"] - full_width)
            for _, row in chronos.loc[
                chronos["block_length_days"].eq(protocol.block_length)
                & chronos["variant"].eq(LEAVE_ONE_OUT)
            ].iterrows()
        },
        "tanker_family_global_by_weighting_primary_block": {
            f"{row['model']}::{row['weighting']}": {
                "observed_global_statistic": float(row["observed_global_statistic"]),
                "one_sided_bootstrap_p_value": float(row["one_sided_bootstrap_p_value"]),
            }
            for _, row in tanker.loc[
                tanker["block_length_days"].eq(protocol.block_length)
                & tanker["variant"].eq(FULL_FAMILY)
            ].iterrows()
        },
        "control_family_can_falsify": bool(
            controls["would_flag_a_tanker_sized_movement"].all()
        ),
        "chronos_control_cells_above_0_05": (
            int(chronos["one_sided_bootstrap_p_value"].gt(0.05).sum()),
            int(len(chronos)),
        ),
        "what_this_cannot_show": (
            "Every variant reuses the same executed forecasts and the same "
            "historical residual vectors. This measures the robustness of the "
            "control test to family composition and weighting, not to the choice "
            "of control classes, which remains Ro-Ro and dry bulk by declaration."
        ),
    }

    protocol.outputs["control_robustness"].parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(protocol.outputs["control_robustness"], index=False)
    protocol.outputs["control_robustness_manifest"].write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    columns = [
        "model", "variant", "weighting", "dropped_control", "n_series",
        "observed_global_statistic", "reference_q950",
        "one_sided_bootstrap_p_value", "would_flag_a_tanker_sized_movement",
    ]
    print(f"=== negative controls, {protocol.block_length}-day blocks ===")
    print(controls.loc[primary_block, columns].round(4).to_string(index=False))
    print(f"\n=== restricted tanker family, {protocol.block_length}-day blocks ===")
    print(
        tanker.loc[
            tanker["block_length_days"].eq(protocol.block_length)
            & tanker["variant"].eq(FULL_FAMILY),
            columns,
        ].round(4).to_string(index=False)
    )
    print(
        f"\nChronos control p-value across every variant and block length: "
        f"{summary['chronos_control_p_value_range_all_blocks'][0]:.4f} to "
        f"{summary['chronos_control_p_value_range_all_blocks'][1]:.4f}"
    )
    print(f"survives every variant: {summary['chronos_specificity_survives_every_variant']}")
    print(f"\nwrote {protocol.outputs['control_robustness']}")
    print(f"wrote {protocol.outputs['control_robustness_manifest']}")


if __name__ == "__main__":
    main()
