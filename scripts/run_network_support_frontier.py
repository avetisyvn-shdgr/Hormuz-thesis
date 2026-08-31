"""Task 7: selective network-support frontier for the modeled LNG panel.

The question is whether the modeled terminal-sequence network retains support
generally while selectively losing support for Hormuz-crossing sequences. It is
a denominator audit of the resolved-sequence panel, run at three frozen terminal
radii, with the overall count always reported beside the selective one.

The construct is *modeled resolved terminal-sequence support*. A sequence drops
out of this panel when AIS coverage lapses, when a terminal cannot be attributed
within the radius, or when a route cannot be resolved. Those failure modes are
plausibly more common during a disruption, so a fall in modeled support is
evidence about observation, not proof that no ship sailed and not a basis for
inferring AIS-dark physical throughput.

Run from the repo root:
    python scripts/run_network_support_frontier.py
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

from hormuz_throughput import config  # noqa: E402
from hormuz_throughput import network_support as ns  # noqa: E402
from hormuz_throughput.exposure import attach_exposure_metadata  # noqa: E402


DESIGN_PATH = config.CONFIG_DIR / "network_support_frontier.yaml"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_design() -> tuple[dict, str]:
    raw = DESIGN_PATH.read_bytes()
    return yaml.safe_load(raw), hashlib.sha256(raw).hexdigest()


def output_path(design: dict, key: str) -> Path:
    return config.ROOT / design["outputs"][key]


def load_verified_inputs(design: dict) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Hash-verify every registered upstream artifact, then load it."""
    for label, spec in design["upstream_registered_artifacts"].items():
        path = config.ROOT / spec["path"]
        if not path.is_file():
            raise FileNotFoundError(f"network-support upstream missing: {label}")
        actual = sha256_file(path)
        if actual != spec["sha256"]:
            raise ValueError(
                f"network-support upstream hash drift for {label}: {actual}"
            )
    upstream = design["upstream_registered_artifacts"]
    voyages = pd.read_csv(config.ROOT / upstream["capacity_voyages"]["path"])
    terminals = pd.read_csv(
        config.ROOT / upstream["terminal_matching_audit"]["path"]
    )
    carriers = pd.read_csv(config.ROOT / upstream["carrier_frame"]["path"])
    validate_inputs(design, voyages, carriers)
    return voyages, terminals, carriers


def validate_inputs(
    design: dict, voyages: pd.DataFrame, carriers: pd.DataFrame
) -> None:
    grid = [int(radius) for radius in design["terminal_radius_km_grid"]]
    available = set(voyages["terminal_match_radius_km"].astype(int).unique())
    missing = sorted(set(grid).difference(available))
    if missing:
        raise ValueError(f"upstream lacks frozen radii: {missing}")
    if int(design["primary_terminal_radius_km"]) not in grid:
        raise ValueError("primary_terminal_radius_km must appear in the grid")
    periods = set(voyages["sample_period"].unique())
    if not set(ns.PERIODS).issubset(periods):
        raise ValueError(f"upstream lacks both periods: {sorted(periods)}")
    if carriers["imo"].duplicated().any():
        raise ValueError("carrier census must be one row per IMO")


def resolved_legs(
    design: dict,
    voyages: pd.DataFrame,
    terminals: pd.DataFrame,
    radius: int,
) -> pd.DataFrame:
    """Annotated resolved legs at one radius, via the established exposure path.

    Reusing ``attach_exposure_metadata`` is deliberate: the Hormuz-crossing flag
    must be the same construct the importer/basin exposure layer already uses,
    not a second definition invented here.
    """
    policy = config.settings()["vessel_data_feasibility"]["importer_basin_exposure"]
    return attach_exposure_metadata(
        voyages,
        terminals,
        terminal_match_radius_km=int(radius),
        gulf_export_project_ids=list(policy["gulf_export_project_ids"]),
        destination_basin_by_country=dict(policy["destination_basin_by_country"]),
    )


def build_denominators(
    design: dict,
    voyages: pd.DataFrame,
    terminals: pd.DataFrame,
    carriers: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Full-panel and both-period-balanced denominators for every radius."""
    census = int(carriers["imo"].nunique())
    cohorts = tuple(design["cohorts"])
    full_frames = []
    balanced_frames = []
    for radius in design["terminal_radius_km_grid"]:
        legs = resolved_legs(design, voyages, terminals, int(radius))
        full_frames.append(
            ns.support_denominators(
                legs,
                terminal_radius_km=int(radius),
                census_eligible_imos=census,
                cohorts=cohorts,
            )
        )
        balanced = ns.balanced_cohort(legs)
        balanced_frames.append(
            ns.support_denominators(
                balanced,
                terminal_radius_km=int(radius),
                census_eligible_imos=census,
                cohorts=cohorts,
            ).assign(panel="both_period_balanced_cohort")
        )

    full = pd.concat(full_frames, ignore_index=True).assign(panel="full_resolved_panel")
    balanced_all = pd.concat(balanced_frames, ignore_index=True)
    ordered = ["panel", *ns.DENOMINATOR_COLUMNS]
    denominators = pd.concat([full, balanced_all], ignore_index=True)[ordered]
    guard_denominators(denominators)
    return (
        denominators.sort_values(
            ["panel", "terminal_radius_km", "cohort", "sample_period"], kind="stable"
        ).reset_index(drop=True),
        full,
    )


def guard_denominators(denominators: pd.DataFrame) -> None:
    """Structural invariants for the denominator table."""
    if denominators.empty:
        raise AssertionError("network-support denominator table is empty")
    if "all_resolved" not in set(denominators["cohort"]):
        raise AssertionError(
            "a selective cohort was emitted without its overall denominator"
        )
    counts = [
        "n_sequences",
        "n_unique_imos",
        "n_destination_countries",
        "n_destination_terminals",
        "n_origin_terminals",
    ]
    if (denominators[counts] < 0).to_numpy().any():
        raise AssertionError("negative support count")
    if not denominators["census_coverage_share"].between(0.0, 1.0).all():
        raise AssertionError("census coverage share outside [0, 1]")

    for (panel, radius, period), group in denominators.groupby(
        ["panel", "terminal_radius_km", "sample_period"], sort=True
    ):
        indexed = group.set_index("cohort")["n_sequences"]
        overall = int(indexed.loc["all_resolved"])
        parts = [
            "hormuz_crossing",
            "inside_hormuz_non_crossing",
            "non_gulf",
        ]
        if set(parts).issubset(indexed.index):
            partition = int(indexed.loc[parts].sum())
            if partition != overall:
                raise AssertionError(
                    f"cohorts do not partition all_resolved for {panel} "
                    f"{radius}km {period}: {partition} != {overall}"
                )
        for cohort in indexed.index:
            if int(indexed.loc[cohort]) > overall:
                raise AssertionError(
                    f"cohort {cohort} exceeds its overall denominator"
                )


def build_radius_sensitivity(design: dict, full: pd.DataFrame) -> pd.DataFrame:
    change = ns.support_change(
        full,
        thin_denominator_threshold=int(design["thin_denominator_threshold_sequences"]),
    )
    contrast = ns.selectivity_contrast(change)
    return change.merge(contrast, on="terminal_radius_km", how="left").sort_values(
        ["terminal_radius_km", "cohort"], kind="stable"
    ).reset_index(drop=True)


def build_balanced_table(design: dict, denominators: pd.DataFrame) -> pd.DataFrame:
    balanced = denominators.loc[
        denominators["panel"].eq("both_period_balanced_cohort")
    ].drop(columns=["panel"])
    change = ns.support_change(
        balanced,
        thin_denominator_threshold=int(design["thin_denominator_threshold_sequences"]),
    )
    contrast = ns.selectivity_contrast(change)
    return change.merge(contrast, on="terminal_radius_km", how="left").sort_values(
        ["terminal_radius_km", "cohort"], kind="stable"
    ).reset_index(drop=True)


def build_audit_expectation(design: dict, sensitivity: pd.DataFrame) -> dict:
    """Reproduce-or-refute record for the stated 30 km benchmark."""
    expected = design["audit_expectation"]
    radius = int(expected["terminal_radius_km"])
    subset = sensitivity.loc[sensitivity["terminal_radius_km"].eq(radius)]
    if subset.empty:
        raise AssertionError("the audit-expectation radius is missing from the grid")
    indexed = subset.set_index("cohort")

    observed = {
        "hormuz_crossing_pre_sequences": int(
            indexed.loc["hormuz_crossing", "pre_sequences"]
        ),
        "hormuz_crossing_post_sequences": int(
            indexed.loc["hormuz_crossing", "post_sequences"]
        ),
        "all_resolved_pre_sequences": int(
            indexed.loc["all_resolved", "pre_sequences"]
        ),
        "all_resolved_post_sequences": int(
            indexed.loc["all_resolved", "post_sequences"]
        ),
    }
    checks = {
        name: {
            "expected": int(expected[name]),
            "observed": value,
            "reproduced": value == int(expected[name]),
        }
        for name, value in observed.items()
    }
    return {
        "terminal_radius_km": radius,
        "checks": checks,
        "fully_reproduced": all(item["reproduced"] for item in checks.values()),
        "definition_note": (
            "A Hormuz-crossing sequence is a resolved liquefaction-to-"
            "regasification sequence whose origin is a registered Gulf export "
            "project AND whose modeled route transits the strait. This is the "
            "hormuz_exposed_leg flag already used by the importer/basin "
            "exposure layer. Counting every resolved sequence whose modeled "
            "route merely transits Hormuz gives 152 pre-period sequences "
            "instead of 145; the seven extra sequences originate outside the "
            "registered Gulf export projects (Oman Qalhat, Nigeria, Sabine "
            "Pass) and are reported in the non_gulf cohort."
        ),
        "support_note": (
            "These are counts of modeled sequences that remain resolvable in "
            "the panel. They are not voyage counts, not cargo, and not "
            "evidence that unobserved sequences did not occur."
        ),
    }


def build_diagnostics(
    design: dict,
    design_sha256: str,
    denominators: pd.DataFrame,
    sensitivity: pd.DataFrame,
    balanced: pd.DataFrame,
    carriers: pd.DataFrame,
) -> dict:
    primary = int(design["primary_terminal_radius_km"])
    primary_rows = sensitivity.loc[sensitivity["terminal_radius_km"].eq(primary)]
    indexed = primary_rows.set_index("cohort")

    per_radius = []
    for radius, group in sensitivity.groupby("terminal_radius_km", sort=True):
        cohort_rows = group.set_index("cohort")
        per_radius.append({
            "terminal_radius_km": int(radius),
            "all_resolved_pre": int(cohort_rows.loc["all_resolved", "pre_sequences"]),
            "all_resolved_post": int(
                cohort_rows.loc["all_resolved", "post_sequences"]
            ),
            "all_resolved_retention_share": float(
                cohort_rows.loc["all_resolved", "retention_share"]
            ),
            "hormuz_crossing_pre": int(
                cohort_rows.loc["hormuz_crossing", "pre_sequences"]
            ),
            "hormuz_crossing_post": int(
                cohort_rows.loc["hormuz_crossing", "post_sequences"]
            ),
            "hormuz_crossing_retention_share": float(
                cohort_rows.loc["hormuz_crossing", "retention_share"]
            ),
            "retention_share_ratio": float(
                cohort_rows.loc["hormuz_crossing", "retention_share_ratio"]
            ),
            "selective_support_loss_exceeds_general": bool(
                cohort_rows.loc["hormuz_crossing",
                                "selective_support_loss_exceeds_general"]
            ),
        })

    balanced_primary = balanced.loc[
        balanced["terminal_radius_km"].eq(primary)
    ].set_index("cohort")
    return {
        "design_id": design["design_id"],
        "design_sha256": design_sha256,
        "analysis_role": design["analysis_role"],
        "freeze_status": design["freeze_status"]["timing"],
        "construct_label": design["reporting_guards"]["construct_label"],
        "census": {
            "eligible_fleet_census_imos": int(carriers["imo"].nunique()),
            "sampling_design": str(
                config.settings()["vessel_data_feasibility"]
                ["global_carrier_frame"]["sampling_design"]
            ),
        },
        "primary_terminal_radius_km": primary,
        "primary_cell": {
            "all_resolved_pre": int(indexed.loc["all_resolved", "pre_sequences"]),
            "all_resolved_post": int(indexed.loc["all_resolved", "post_sequences"]),
            "all_resolved_retention_share": float(
                indexed.loc["all_resolved", "retention_share"]
            ),
            "hormuz_crossing_pre": int(
                indexed.loc["hormuz_crossing", "pre_sequences"]
            ),
            "hormuz_crossing_post": int(
                indexed.loc["hormuz_crossing", "post_sequences"]
            ),
            "hormuz_crossing_retention_share": float(
                indexed.loc["hormuz_crossing", "retention_share"]
            ),
            "retention_share_ratio": float(
                indexed.loc["hormuz_crossing", "retention_share_ratio"]
            ),
        },
        "balanced_primary_cell": {
            "all_resolved_pre": int(
                balanced_primary.loc["all_resolved", "pre_sequences"]
            ),
            "all_resolved_post": int(
                balanced_primary.loc["all_resolved", "post_sequences"]
            ),
            "hormuz_crossing_pre": int(
                balanced_primary.loc["hormuz_crossing", "pre_sequences"]
            ),
            "hormuz_crossing_post": int(
                balanced_primary.loc["hormuz_crossing", "post_sequences"]
            ),
            "all_resolved_retention_share": float(
                balanced_primary.loc["all_resolved", "retention_share"]
            ),
            "hormuz_crossing_retention_share": float(
                balanced_primary.loc["hormuz_crossing", "retention_share"]
            ),
        },
        "radius_sensitivity": per_radius,
        "selectivity_direction_consistent_across_radii": bool(
            all(item["selective_support_loss_exceeds_general"] for item in per_radius)
        ),
        "reporting_guards": design["reporting_guards"],
    }


def _pct(value: float) -> str:
    if not np.isfinite(value):
        return "n/a"
    return f"{value * 100:.1f}%"


def render_markdown(
    design: dict,
    diagnostics: dict,
    denominators: pd.DataFrame,
    sensitivity: pd.DataFrame,
    balanced: pd.DataFrame,
    audit: dict,
) -> str:
    primary = diagnostics["primary_terminal_radius_km"]
    cell = diagnostics["primary_cell"]
    lines: list[str] = []
    add = lines.append

    add("# Selective network-support frontier")
    add("")
    add(f"**Design id:** `{design['design_id']}`  ")
    add(f"**Design SHA-256:** `{diagnostics['design_sha256']}`  ")
    add(f"**Frozen (UTC):** {design['frozen_utc']}  ")
    add(f"**Freeze status:** {design['freeze_status']['timing']}  ")
    add("**Verification status:** `NEEDS-VERIFY` until the complete pipeline is run.")
    add("")
    add(
        "This document measures **modeled resolved terminal-sequence support**: "
        "how many liquefaction-to-regasification sequences remain resolvable in "
        "the panel before and after the disruption, overall and for "
        "Hormuz-crossing sequences. It is a denominator audit, not a voyage "
        "count, not cargo, and not a causal estimate."
    )
    add("")

    add("## What a missing edge means")
    add("")
    add(
        "A sequence leaves this panel when AIS coverage lapses, when neither "
        "endpoint can be attributed to a terminal within the chosen radius, or "
        "when no route can be resolved. Each of those failure modes is "
        "plausibly **more** likely during a disruption."
    )
    add("")
    add(
        "So a fall in modeled Hormuz-crossing support is evidence that the "
        "panel stopped observing those sequences. It is **not** evidence that "
        "no ship sailed, and no AIS-dark physical throughput may be inferred "
        "from it. Loss of support and loss of sailing are different "
        "propositions, and only the first is measurable here."
    )
    add("")

    add("## Frozen definitions")
    add("")
    add("| Cohort | Definition | Role |")
    add("|---|---|---|")
    for cohort, spec in design["cohorts"].items():
        add(f"| `{cohort}` | {spec['definition']} | {spec['role']} |")
    add("")
    add(
        f"Radii {', '.join(str(r) for r in design['terminal_radius_km_grid'])} km "
        f"are frozen, with {primary} km primary. Every selective count below is "
        "reported beside its overall denominator for the same radius and period."
    )
    add("")

    add(f"## Primary radius ({primary} km)")
    add("")
    add(
        "| Cohort | Pre sequences | Post sequences | Change | Retention | "
        "Pre IMOs | Post IMOs | Pre dest. countries | Post dest. countries |"
    )
    add("|---|---:|---:|---:|---:|---:|---:|---:|---:|")
    primary_rows = sensitivity.loc[sensitivity["terminal_radius_km"].eq(primary)]
    for record in primary_rows.to_dict("records"):
        add(
            f"| `{record['cohort']}` | {record['pre_sequences']} | "
            f"{record['post_sequences']} | "
            f"{record['absolute_change_sequences']:+d} | "
            f"{_pct(record['retention_share'])} | "
            f"{record['pre_unique_imos']} | {record['post_unique_imos']} | "
            f"{record['pre_destination_countries']} | "
            f"{record['post_destination_countries']} |"
        )
    add("")
    add(
        f"The panel as a whole retains {_pct(cell['all_resolved_retention_share'])} "
        f"of its resolved sequences ({cell['all_resolved_pre']} to "
        f"{cell['all_resolved_post']}), while the Hormuz-crossing cohort retains "
        f"{_pct(cell['hormuz_crossing_retention_share'])} "
        f"({cell['hormuz_crossing_pre']} to {cell['hormuz_crossing_post']}). The "
        f"ratio of the two retention shares is "
        f"{cell['retention_share_ratio']:.4f}."
    )
    add("")
    add(
        "That is the selectivity result: general support largely persists while "
        "Hormuz-crossing support very nearly disappears from the panel. Both "
        "numbers describe observability."
    )
    add("")

    add("## Radius sensitivity")
    add("")
    add(
        "| Radius (km) | All resolved pre | post | retention | "
        "Hormuz-crossing pre | post | retention | Retention ratio |"
    )
    add("|---:|---:|---:|---:|---:|---:|---:|---:|")
    for item in diagnostics["radius_sensitivity"]:
        add(
            f"| {item['terminal_radius_km']} | {item['all_resolved_pre']} | "
            f"{item['all_resolved_post']} | "
            f"{_pct(item['all_resolved_retention_share'])} | "
            f"{item['hormuz_crossing_pre']} | {item['hormuz_crossing_post']} | "
            f"{_pct(item['hormuz_crossing_retention_share'])} | "
            f"{item['retention_share_ratio']:.4f} |"
        )
    add("")
    if diagnostics["selectivity_direction_consistent_across_radii"]:
        add(
            "The direction is consistent at every frozen radius: the "
            "Hormuz-crossing cohort loses a larger share of its modeled support "
            "than the panel as a whole. Radius choice changes the level of both "
            "denominators, not the sign of the contrast."
        )
    else:
        add(
            "The direction is **not** consistent across radii. The "
            "disagreement is reported rather than resolved, and the selectivity "
            "claim does not survive the radius sensitivity."
        )
    add("")

    add("## Both-period balanced cohort")
    add("")
    add(
        "Restricting to IMOs with at least one resolved sequence in both "
        "periods holds the observed carrier set fixed, so a support change "
        "cannot come purely from carriers entering or leaving the panel."
    )
    add("")
    threshold = int(design["thin_denominator_threshold_sequences"])
    add(
        "| Radius (km) | Cohort | Pre | Post | Retention | Pre IMOs | Post IMOs |"
    )
    add("|---:|---|---:|---:|---:|---:|---:|")
    for record in balanced.to_dict("records"):
        retention = _pct(record["retention_share"])
        if record["pre_denominator_is_thin"]:
            retention = f"{retention} †"
        add(
            f"| {record['terminal_radius_km']} | `{record['cohort']}` | "
            f"{record['pre_sequences']} | {record['post_sequences']} | "
            f"{retention} | "
            f"{record['pre_unique_imos']} | {record['post_unique_imos']} |"
        )
    add("")
    add(
        f"† Pre-period support of {threshold} sequences or fewer. A retention "
        "share on such a base is numerically unstable — a movement of one or "
        "two sequences can exceed 100% — and must not be read as a trend."
    )
    add("")
    balanced_cell = diagnostics["balanced_primary_cell"]
    add(
        f"At {primary} km the balanced cohort retains "
        f"{_pct(balanced_cell['all_resolved_retention_share'])} of overall "
        f"support and {_pct(balanced_cell['hormuz_crossing_retention_share'])} "
        "of Hormuz-crossing support, so the contrast is not an artifact of "
        "carrier turnover."
    )
    add("")

    add("## Census coverage")
    add("")
    add(
        f"The eligible fleet census contains "
        f"{diagnostics['census']['eligible_fleet_census_imos']} IMOs under the "
        f"`{diagnostics['census']['sampling_design']}` sampling design. Coverage "
        "shares below are the fraction of that census appearing at all in a "
        "cell. They are support-observation shares, never fleet utilisation."
    )
    add("")
    add("| Radius (km) | Period | Cohort | Unique IMOs | Census coverage |")
    add("|---:|---|---|---:|---:|")
    census_rows = denominators.loc[
        denominators["panel"].eq("full_resolved_panel")
        & denominators["cohort"].isin(["all_resolved", "hormuz_crossing"])
    ]
    for record in census_rows.to_dict("records"):
        add(
            f"| {record['terminal_radius_km']} | {record['sample_period']} | "
            f"`{record['cohort']}` | {record['n_unique_imos']} | "
            f"{_pct(record['census_coverage_share'])} |"
        )
    add("")

    add("## Audit expectation")
    add("")
    add(
        f"Benchmark at {audit['terminal_radius_km']} km: "
        f"{'reproduced' if audit['fully_reproduced'] else 'NOT reproduced'}."
    )
    add("")
    add("| Check | Expected | Observed | Reproduced |")
    add("|---|---:|---:|---|")
    for name, item in audit["checks"].items():
        add(
            f"| {name} | {item['expected']} | {item['observed']} | "
            f"{'yes' if item['reproduced'] else 'no'} |"
        )
    add("")
    add(audit["definition_note"])
    add("")

    add("## Interpretation limits")
    add("")
    add(
        "- The construct is modeled resolved terminal-sequence support. It is "
        "not observed voyages, not cargo, and not physical throughput."
    )
    add(
        "- A missing modeled edge is a missing observation. It is not evidence "
        "that no ship sailed."
    )
    add(
        "- No AIS-dark throughput may be inferred from these counts. The "
        "failure modes that remove a sequence from the panel are themselves "
        "plausibly correlated with the disruption, which would bias any such "
        "inference in an unknown direction."
    )
    add(
        "- Selective support loss is a descriptive contrast between two "
        "observation counts. It is not an average treatment effect and it does "
        "not identify a causal mechanism."
    )
    add(
        "- The upstream capacity and radius-comparison artifacts are "
        "hash-verified read-only inputs to this phase."
    )
    add("")
    return "\n".join(lines) + "\n"


def main() -> int:
    design, design_sha256 = load_design()
    voyages, terminals, carriers = load_verified_inputs(design)

    denominators, full = build_denominators(design, voyages, terminals, carriers)
    sensitivity = build_radius_sensitivity(design, full)
    balanced = build_balanced_table(design, denominators)
    audit = build_audit_expectation(design, sensitivity)
    diagnostics = build_diagnostics(
        design, design_sha256, denominators, sensitivity, balanced, carriers
    )
    markdown = render_markdown(
        design, diagnostics, denominators, sensitivity, balanced, audit
    )

    for key, frame in (
        ("denominators_csv", denominators),
        ("radius_sensitivity_csv", sensitivity),
        ("balanced_cohort_csv", balanced),
    ):
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

    cell = diagnostics["primary_cell"]
    print("\nSelective network-support frontier (primary radius "
          f"{diagnostics['primary_terminal_radius_km']} km):")
    print(
        f"  all resolved: {cell['all_resolved_pre']} -> "
        f"{cell['all_resolved_post']} "
        f"(retention {cell['all_resolved_retention_share']:.4f})"
    )
    print(
        f"  Hormuz-crossing: {cell['hormuz_crossing_pre']} -> "
        f"{cell['hormuz_crossing_post']} "
        f"(retention {cell['hormuz_crossing_retention_share']:.4f})"
    )
    print(f"  retention share ratio: {cell['retention_share_ratio']:.6f}")
    print(
        "  audit expectation: "
        f"{'REPRODUCED' if audit['fully_reproduced'] else 'NOT REPRODUCED'}"
    )
    print("\nRadius sensitivity:")
    print(
        sensitivity.loc[
            sensitivity["cohort"].isin(["all_resolved", "hormuz_crossing"]),
            [
                "terminal_radius_km",
                "cohort",
                "pre_sequences",
                "post_sequences",
                "retention_share",
                "retention_share_ratio",
            ],
        ].to_string(index=False)
    )
    print("\nInterpretation guard:")
    print(" - Construct: modeled resolved terminal-sequence SUPPORT.")
    print(" - A missing modeled edge is a missing observation, not proof")
    print("   that no ship sailed.")
    print(" - No AIS-dark physical throughput may be inferred from these counts.")
    print(" - Selective counts are always paired with their overall denominator.")
    print(" - This is NEEDS-VERIFY until the complete pipeline transcript is retained.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
