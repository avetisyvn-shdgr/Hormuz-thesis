"""Map the joint observability / counterfactual-uncertainty breakdown frontier.

Motivation
----------
Two facts about the headline throughput result are already established and
separately documented: the observed reduction is a conditional upper bound under
treatment-correlated AIS-dark activity (`scripts/run_ais_dark_bound.py`), and the
counterfactual is interval-identified rather than point-identified
(`scripts/run_interval_calibration.py`, `scripts/run_block_inference.py`). They
have never been varied together. Reported separately, each looks comfortable;
the robustness margin a reader should actually rely on is the *joint* one.

This script combines them into a breakdown frontier: for each claim strength
("the true reduction was at least R̄"), it reports the incremental dark rate that
would break the claim, evaluated at every admissible counterfactual rather than
only at the point estimate, and translates that rate into the number of
completely invisible vessel transits it would require.

No new data source is consulted. Every input is a committed artifact of the
existing pipeline. This adds no variable to the registry and does not touch the
locked cutoff, the primary specification, or any frozen manifest.

Guard
-----
This is a partial-identification sensitivity map over stated assumptions. It is
not a causal correction, not a measurement of dark activity, and not an estimate
of the realised dark rate. The tolerated-dark-rate column reports what the author
would have to be willing to concede; it is an assumption, and the write-up must
say where that assumption comes from.

Run from the repo root:
    .venv/bin/python scripts/run_observability_breakdown_frontier.py
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lngfreight import config  # noqa: E402
from lngfreight import observability_frontier as of  # noqa: E402
from lngfreight.specification import working_specification  # noqa: E402


COUNTERFACTUAL_SUMMARY = "counterfactual_post_treatment_summary.csv"
BOOTSTRAP_INTERVALS = "counterfactual_intervals_summary.csv"
CONFORMAL_INTERVALS = "block_conformal_summary.csv"
LEGACY_BOUND = "ais_dark_bound_critical_rates.csv"
PANEL = "panel_aligned.csv"

FRONTIER_OUT = "observability_breakdown_frontier.csv"
GRID_OUT = "observability_breakdown_grid.csv"
CALIBRATION_OUT = "observability_claim_calibration.csv"
SUMMARY_OUT = "observability_breakdown_summary.json"

# Reference window for "normal" daily throughput. The trailing pre-treatment year
# is used rather than the full 2022-2026 history so the plausibility comparison
# is against recent operating conditions, not a four-year average that spans
# different market regimes.
PRETREATMENT_REFERENCE_DAYS = 365

# Dark rates the author might be willing to concede as possible. These are
# reporting anchors for the claim-calibration table, not estimates.
TOLERATED_DARK_RATES = (0.05, 0.10, 0.20, 0.30)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read(name: str) -> tuple[pd.DataFrame, Path]:
    path = config.path("data_processed") / name
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found. Run the upstream pipeline stage that writes it "
            "before this script (see scripts/run_all.py for the order)."
        )
    return pd.read_csv(path), path


def pretreatment_daily_mean(target: str, cutoff: pd.Timestamp) -> tuple[float, float]:
    """Return (trailing-year mean, full pre-treatment mean) of observed daily values."""
    panel, _ = _read(PANEL)
    if target not in panel.columns:
        raise KeyError(f"{target!r} is not a column of {PANEL}.")
    panel["date"] = pd.to_datetime(panel["date"])
    pre = panel.loc[panel["date"] < cutoff, ["date", target]].dropna()
    if pre.empty:
        raise ValueError(f"no pre-treatment observations of {target!r}.")
    window_start = cutoff - pd.Timedelta(days=PRETREATMENT_REFERENCE_DAYS)
    trailing = pre.loc[pre["date"] >= window_start, target]
    if trailing.empty:
        raise ValueError(
            f"no observations of {target!r} in the {PRETREATMENT_REFERENCE_DAYS}-day "
            "window before the cutoff; the plausibility denominator is undefined."
        )
    return float(trailing.mean()), float(pre[target].mean())


def build_scenarios(
    model: str,
    target: str,
    observed: float,
    counterfactual_point: float,
    bootstrap: pd.DataFrame,
    conformal: pd.DataFrame,
) -> tuple[list[of.CounterfactualScenario], int, list[str]]:
    """Assemble every admissible counterfactual value, plus dropped-endpoint notes.

    Interval endpoints are carried on the counterfactual scale as ``O + loss``.
    Unbounded conformal endpoints are dropped with an explicit note rather than
    clipped, because clipping an infinite endpoint would manufacture a bound the
    inference does not support.
    """
    scenarios = [of.CounterfactualScenario(
        name=of.POINT_SCENARIO,
        counterfactual_sum=counterfactual_point,
        interval_family="point",
        nominal_coverage=None,
    )]
    notes: list[str] = []

    boot = bootstrap[(bootstrap["model"] == model) & (bootstrap["target"] == target)]
    if boot.empty:
        raise KeyError(
            f"no block-bootstrap interval row for model={model!r} target={target!r}."
        )
    boot_row = boot.iloc[0]
    n_post_days = int(boot_row["n_post_days"])
    coverage = 1.0 - float(boot_row["alpha"])
    for label, column in (("lower", "loss_interval_lower"),
                          ("upper", "loss_interval_upper")):
        scenarios.append(of.CounterfactualScenario(
            name=f"bootstrap_block_{label}",
            counterfactual_sum=observed + float(boot_row[column]),
            interval_family="block_bootstrap_residual",
            nominal_coverage=coverage,
        ))

    conf = conformal[(conformal["model"] == model) & (conformal["target"] == target)]
    for _, row in conf.iterrows():
        if not bool(row["finite_interval_supported"]):
            notes.append(
                f"conformal endpoints at nominal coverage "
                f"{float(row['nominal_coverage']):.2f} are unbounded and were "
                "dropped, not clipped."
            )
            continue
        conf_coverage = float(row["nominal_coverage"])
        for label, column in (("lower", "interval_lower"), ("upper", "interval_upper")):
            scenarios.append(of.CounterfactualScenario(
                name=f"conformal_{conf_coverage:.2f}_{label}",
                counterfactual_sum=observed + float(row[column]),
                interval_family="split_conformal_block_rank",
                nominal_coverage=conf_coverage,
            ))
    if conf.empty:
        notes.append(
            f"no conformal interval exists for model={model!r} target={target!r}; "
            "the frontier for this cell rests on the bootstrap interval alone."
        )
    return scenarios, n_post_days, notes


def build_calibration(binding: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for tolerated in TOLERATED_DARK_RATES:
        strongest = of.strongest_surviving_claim(binding, tolerated)
        if strongest.empty:
            rows.append({
                "tolerated_dark_rate": tolerated,
                "model": None,
                "target": None,
                "strongest_surviving_claim": None,
                "binding_scenario": None,
                "binding_breakdown_dark_rate": None,
                "survives": False,
            })
            continue
        for _, row in strongest.iterrows():
            rows.append({
                "tolerated_dark_rate": tolerated,
                "model": row["model"],
                "target": row["target"],
                "strongest_surviving_claim": row["claim_threshold"],
                "binding_scenario": row["counterfactual_scenario"],
                "binding_breakdown_dark_rate": row["breakdown_dark_rate"],
                "survives": True,
            })
    return pd.DataFrame(rows)


def run_target(
    *,
    model: str,
    target: str,
    role: str,
    cutoff: pd.Timestamp,
    summary: pd.DataFrame,
    bootstrap: pd.DataFrame,
    conformal: pd.DataFrame,
    legacy: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, dict]:
    """Build every artifact block for one outcome.

    Both outcomes are produced in a single invocation and stacked, so the
    robustness twin can never overwrite the primary artifacts and the two are
    always reported from the same inputs.
    """
    sel = summary[(summary["model"] == model) & (summary["target"] == target)]
    if sel.empty:
        raise KeyError(f"no counterfactual row for model={model!r} target={target!r}.")
    observed = float(sel.iloc[0]["observed_sum"])
    counterfactual_point = float(sel.iloc[0]["counterfactual_sum"])

    scenarios, n_post_days, notes = build_scenarios(
        model, target, observed, counterfactual_point, bootstrap, conformal
    )
    trailing_mean, full_pre_mean = pretreatment_daily_mean(target, cutoff)

    frontier = of.build_frontier(
        observed=observed,
        scenarios=scenarios,
        model=model,
        target=target,
        n_post_days=n_post_days,
        pretreatment_daily_mean=trailing_mean,
    )
    grid = of.build_two_sided_grid(
        observed=observed, scenarios=scenarios, model=model, target=target
    )
    of.assert_false_positive_direction(grid)

    # The legacy AIS-dark bound exists for the primary outcome only. Skipping is
    # recorded explicitly rather than swallowed, so a run without the cross-check
    # is visibly a weaker run.
    shared_cells = of.legacy_cross_check_cells(frontier, legacy)
    if shared_cells:
        of.assert_point_scenario_matches_legacy_bound(frontier, legacy)
        legacy_cross_check = f"passed on {shared_cells} shared cells"
    else:
        legacy_cross_check = (
            f"SKIPPED: {LEGACY_BOUND} has no rows for model={model!r} "
            f"target={target!r}, so the point-estimate corner is unchecked."
        )
        notes.append(legacy_cross_check)

    binding = of.binding_breakdown(frontier)
    calibration = build_calibration(binding)

    block = {
        "model": model,
        "target": target,
        "role": role,
        "treatment_cutoff": str(cutoff.date()),
        "n_post_days": n_post_days,
        "observed_sum": observed,
        "counterfactual_point_estimate": counterfactual_point,
        "reduction_at_point_estimate": 1.0 - observed / counterfactual_point,
        "pretreatment_reference_days": PRETREATMENT_REFERENCE_DAYS,
        "pretreatment_trailing_daily_mean": trailing_mean,
        "pretreatment_full_daily_mean": full_pre_mean,
        "counterfactual_scenarios": [
            {
                "name": s.name,
                "counterfactual_sum": s.counterfactual_sum,
                "interval_family": s.interval_family,
                "nominal_coverage": s.nominal_coverage,
            }
            for s in scenarios
        ],
        "unit": of.target_unit(target),
        "dropped_endpoint_notes": notes,
        "legacy_bound_cross_check": legacy_cross_check,
        "binding_breakdown": binding.to_dict(orient="records"),
    }

    print(f"\n=== {role}: {model!r} on {target!r} "
          f"[{of.target_unit(target)}] ===")
    print(f"  observed post-period total          O = {observed:,.0f}")
    print(f"  counterfactual point estimate       C = {counterfactual_point:,.1f}")
    print(f"  reduction at zero incremental error   = "
          f"{1.0 - observed / counterfactual_point:.4f}")
    print(f"  pre-treatment trailing-{PRETREATMENT_REFERENCE_DAYS}d daily mean = "
          f"{trailing_mean:,.2f} per day")
    print(f"  post-period length                    = {n_post_days} days")
    print(f"  legacy AIS-dark bound cross-check     = {legacy_cross_check}")

    print("\n  Admissible counterfactual scenarios:")
    for s in scenarios:
        coverage = "n/a" if s.nominal_coverage is None else f"{s.nominal_coverage:.2f}"
        print(f"    {s.name:<26} C = {s.counterfactual_sum:>14,.1f}   "
              f"coverage {coverage}   ({s.interval_family})")
    for note in notes:
        print(f"    note: {note}")

    print("\n  Breakdown dark rate d* by claim threshold and scenario:")
    view = frontier.pivot_table(
        index="claim_threshold",
        columns="counterfactual_scenario",
        values="breakdown_dark_rate",
    )
    print(view.to_string(float_format=lambda v: f"{v: .4f}"))

    print("\n  Binding (least favourable admissible) breakdown per claim threshold:")
    print(binding[[
        "claim_threshold", "counterfactual_scenario", "breakdown_dark_rate",
        "point_estimate_breakdown_dark_rate", "interval_robustness_discount",
        "implied_unobserved_total_at_breakdown", "implied_unobserved_per_post_day",
        "implied_unobserved_share_of_pretreatment_daily_mean", "breakdown_status",
    ]].to_string(index=False, float_format=lambda v: f"{v: .4f}"))

    print("\n  Claim calibration — strongest claim surviving a conceded dark rate:")
    print(calibration.to_string(index=False, float_format=lambda v: f"{v: .4f}"))

    return frontier, grid, binding, calibration, block


GUARD = (
    "Partial-identification sensitivity map over stated assumptions. Not a "
    "causal correction, not a measurement of dark activity, and not an estimate "
    "of the realised dark rate. The false-positive rate s is claim-reinforcing, "
    "so the one-sided AIS-dark bound is the conservative case; the claim-breaking "
    "directions are a large incremental dark rate and a counterfactual at the low "
    "end of its interval."
)


def main(target_override: str | None) -> int:
    spec = working_specification()
    model = spec.primary_estimator
    cutoff = pd.Timestamp(
        config.settings()["study_window"]["primary_treatment_cutoff"]
    )

    targets = [(spec.primary_outcome, "primary_outcome"),
               (spec.robustness_outcome, "robustness_outcome")]
    if target_override is not None:
        targets = [(t, role) for t, role in targets if t == target_override]
        if not targets:
            raise KeyError(
                f"{target_override!r} is neither the primary outcome "
                f"({spec.primary_outcome!r}) nor the robustness outcome "
                f"({spec.robustness_outcome!r}); this layer does not run on "
                "unregistered outcomes."
            )

    summary, summary_path = _read(COUNTERFACTUAL_SUMMARY)
    bootstrap, bootstrap_path = _read(BOOTSTRAP_INTERVALS)
    conformal, conformal_path = _read(CONFORMAL_INTERVALS)
    legacy, legacy_path = _read(LEGACY_BOUND)
    panel_path = config.path("data_processed") / PANEL

    frontiers, grids, bindings, calibrations, blocks = [], [], [], [], []
    for target, role in targets:
        frontier, grid, binding, calibration, block = run_target(
            model=model,
            target=target,
            role=role,
            cutoff=cutoff,
            summary=summary,
            bootstrap=bootstrap,
            conformal=conformal,
            legacy=legacy,
        )
        frontiers.append(frontier)
        grids.append(grid)
        bindings.append(binding)
        calibrations.append(calibration)
        blocks.append(block)

    out_dir = config.path("data_processed")
    frontier_path = out_dir / FRONTIER_OUT
    grid_path = out_dir / GRID_OUT
    calibration_path = out_dir / CALIBRATION_OUT
    summary_json_path = out_dir / SUMMARY_OUT
    pd.concat(frontiers, ignore_index=True).to_csv(frontier_path, index=False)
    pd.concat(grids, ignore_index=True).to_csv(grid_path, index=False)
    pd.concat(calibrations, ignore_index=True).to_csv(calibration_path, index=False)

    payload = {
        "layer_id": "hormuz_observability_counterfactual_breakdown_frontier_v1",
        "outcomes": blocks,
        "inputs": {
            str(path.relative_to(config.ROOT)): sha256_file(path)
            for path in (summary_path, bootstrap_path, conformal_path,
                         legacy_path, panel_path)
        },
        "guard": GUARD,
    }
    summary_json_path.write_text(json.dumps(payload, indent=2) + "\n")

    print(f"\nwrote {frontier_path}")
    print(f"wrote {grid_path}")
    print(f"wrote {calibration_path}")
    print(f"wrote {summary_json_path}")
    print("\nGuard: " + GUARD)
    print("\nSTOP AND REPORT. These outputs are unverified until Mher has run "
          "this script and the focused tests and pasted back the real output. "
          "No claim in the manuscript may cite these artifacts before that.")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--target",
        default=None,
        help="restrict the run to one registered outcome. The default runs both "
             "the primary outcome and the robustness outcome and stacks them.",
    )
    args = parser.parse_args()
    raise SystemExit(main(target_override=args.target))
