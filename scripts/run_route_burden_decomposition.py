"""Task 8: route-burden decomposition for retained inferred LNG voyages.

Decomposes the complete-case change in *modeled distance per nominal
vessel-capacity m3 among retained inferred voyages* into terminal-pair share
reweighting, an entry/exit residual from changing pair support, and within-pair
capacity mix. The three components reconcile to the total change exactly.

The construct is modeled on both factors. Nominal capacity is a carrier design
property, not measured cargo; the distance is a shortest-sea-route estimate, not
an AIS track. A rise in the mean is a statement about which sequences remain
observable and how their modeled attributes are distributed. It is not observed
cargo ton-miles, not physical rerouting, and not evidence that individual ships
sailed farther.

Run from the repo root:
    python scripts/run_route_burden_decomposition.py
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
from lngfreight import route_burden as rb  # noqa: E402
from lngfreight.routes import RESOLVED_STATUS  # noqa: E402


DESIGN_PATH = config.CONFIG_DIR / "route_burden_decomposition.yaml"
PAIR_COLUMN = "terminal_pair"

DECOMPOSITION_COLUMNS = [
    "cohort",
    "terminal_radius_km",
    "weighting_scheme",
    "construct_label",
    "unit",
    "pre_mean",
    "post_mean",
    "total_change",
    "common_pair_share_reweighting",
    "within_common_pair_capacity_mix",
    "entry_exit_residual",
    "common_pair_share_reweighting_percent",
    "within_common_pair_capacity_mix_percent",
    "entry_exit_residual_percent",
    "percent_stability_ratio",
    "percent_decomposition_is_unstable",
    "reconciliation_error",
    "residual_identity_error",
    "n_pre_sequences",
    "n_post_sequences",
    "n_common_pairs",
    "n_pre_only_pairs",
    "n_post_only_pairs",
    "common_pair_pre_share",
    "common_pair_post_share",
    "excluded_pre_sequences",
    "excluded_post_sequences",
]


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_design() -> tuple[dict, str]:
    raw = DESIGN_PATH.read_bytes()
    return yaml.safe_load(raw), hashlib.sha256(raw).hexdigest()


def output_path(design: dict, key: str) -> Path:
    return config.ROOT / design["outputs"][key]


def load_verified_inputs(design: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    for label, spec in design["upstream_registered_artifacts"].items():
        path = config.ROOT / spec["path"]
        if not path.is_file():
            raise FileNotFoundError(f"route-burden upstream missing: {label}")
        actual = sha256_file(path)
        if actual != spec["sha256"]:
            raise ValueError(
                f"route-burden upstream hash drift for {label}: {actual}"
            )
    upstream = design["upstream_registered_artifacts"]
    voyages = pd.read_csv(config.ROOT / upstream["capacity_voyages"]["path"])
    carriers = pd.read_csv(config.ROOT / upstream["carrier_frame"]["path"])
    validate_inputs(design, voyages)
    return voyages, carriers


def validate_inputs(design: dict, voyages: pd.DataFrame) -> None:
    outcome = design["construct"]["outcome_column"]
    required = {
        outcome,
        "endpoint_status",
        "sample_period",
        "terminal_match_radius_km",
        "project_id",
        "destination_project_id",
        "imo",
    }
    missing = required.difference(voyages.columns)
    if missing:
        raise ValueError(f"capacity voyages lack columns: {sorted(missing)}")
    grid = [int(radius) for radius in design["terminal_radius_km_grid"]]
    available = set(voyages["terminal_match_radius_km"].astype(int).unique())
    absent = sorted(set(grid).difference(available))
    if absent:
        raise ValueError(f"upstream lacks frozen radii: {absent}")
    if int(design["primary_terminal_radius_km"]) not in grid:
        raise ValueError("primary_terminal_radius_km must appear in the grid")


def complete_case(
    design: dict, voyages: pd.DataFrame, radius: int
) -> tuple[pd.DataFrame, dict]:
    """Retained sequences at one radius, with an explicit exclusion count.

    Excluded sequences are counted and returned, never dropped silently and
    never imputed. A sequence that left the panel is a support fact, documented
    by the task-7 frontier; it is not assigned a burden of zero here.
    """
    outcome = design["construct"]["outcome_column"]
    rule = design["complete_case_rule"]
    at_radius = voyages.loc[
        voyages["terminal_match_radius_km"].astype(int).eq(int(radius))
    ]
    resolved = at_radius.loc[at_radius["endpoint_status"].eq(rule["endpoint_status"])]
    if rule["endpoint_status"] != RESOLVED_STATUS:
        raise ValueError("complete-case endpoint status drifted from the package")
    retained = resolved.loc[resolved[outcome].notna()].copy()
    retained[PAIR_COLUMN] = (
        retained["project_id"].astype(str)
        + " -> "
        + retained["destination_project_id"].astype(str)
    )
    exclusions = {}
    for period in rb.PERIODS:
        resolved_n = int(resolved["sample_period"].eq(period).sum())
        retained_n = int(retained["sample_period"].eq(period).sum())
        exclusions[f"excluded_{period}_sequences"] = resolved_n - retained_n
    return retained, exclusions


def both_period_carrier_restriction(retained: pd.DataFrame) -> pd.DataFrame:
    seen = {
        period: set(retained.loc[retained["sample_period"].eq(period), "imo"])
        for period in rb.PERIODS
    }
    keep = seen["pre"] & seen["post"]
    return retained.loc[retained["imo"].isin(keep)].copy()


def _decomposition_rows(
    design: dict,
    frame: pd.DataFrame,
    *,
    cohort: str,
    radius: int,
    exclusions: dict,
) -> list[dict]:
    outcome = design["construct"]["outcome_column"]
    tolerance = float(design["decomposition"]["reconciliation"]["tolerance_absolute"])
    identity = rb.residual_identity_check(
        frame, pair_column=PAIR_COLUMN, outcome_column=outcome
    )
    unstable_above = float(
        design["decomposition"]["percent_stability"]["unstable_above_ratio"]
    )
    rows = []
    for scheme in design["weighting_schemes"]:
        result = rb.decompose(
            frame,
            pair_column=PAIR_COLUMN,
            outcome_column=outcome,
            weighting_scheme=scheme,
            reconciliation_tolerance=tolerance,
        )
        rows.append({
            "cohort": cohort,
            "terminal_radius_km": int(radius),
            "construct_label": design["construct"]["label"],
            "unit": design["construct"]["unit"],
            "residual_identity_error": abs(result.entry_exit_residual - identity),
            "percent_decomposition_is_unstable": bool(
                result.percent_stability_ratio() > unstable_above
            ),
            **exclusions,
            **result.to_row(),
        })
    return rows


def build_decomposition(
    design: dict, voyages: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Decompositions for every radius, cohort, and weighting scheme."""
    rows = []
    pair_frames = []
    outcome = design["construct"]["outcome_column"]
    primary = int(design["primary_terminal_radius_km"])
    for radius in design["terminal_radius_km_grid"]:
        radius = int(radius)
        retained, exclusions = complete_case(design, voyages, radius)
        rows.extend(_decomposition_rows(
            design, retained,
            cohort="all_retained", radius=radius, exclusions=exclusions,
        ))
        balanced = both_period_carrier_restriction(retained)
        rows.extend(_decomposition_rows(
            design, balanced,
            cohort="both_period_carriers", radius=radius, exclusions=exclusions,
        ))
        if radius == primary:
            pair_frames.append(
                rb.pair_support_table(
                    retained, pair_column=PAIR_COLUMN, outcome_column=outcome
                ).assign(terminal_radius_km=radius, cohort="all_retained")
            )

    decomposition = pd.DataFrame(rows)[DECOMPOSITION_COLUMNS]
    guard_decomposition(design, decomposition)
    pair_support = pd.concat(pair_frames, ignore_index=True)
    return (
        decomposition.sort_values(
            ["cohort", "terminal_radius_km", "weighting_scheme"], kind="stable"
        ).reset_index(drop=True),
        pair_support.sort_values(
            ["terminal_radius_km", "support_status", "terminal_pair"], kind="stable"
        ).reset_index(drop=True),
    )


def guard_decomposition(design: dict, decomposition: pd.DataFrame) -> None:
    """Structural invariants that must hold before anything is written."""
    if decomposition.empty:
        raise AssertionError("route-burden decomposition table is empty")
    tolerance = float(design["decomposition"]["reconciliation"]["tolerance_absolute"])
    if decomposition["reconciliation_error"].gt(tolerance).any():
        raise AssertionError("a decomposition failed exact reconciliation")
    if decomposition["residual_identity_error"].gt(tolerance).any():
        raise AssertionError(
            "the entry/exit residual disagrees with its conditional-mean "
            "identity; it is not the support term it claims to be"
        )
    components = [
        "common_pair_share_reweighting",
        "within_common_pair_capacity_mix",
        "entry_exit_residual",
    ]
    recomputed = decomposition[components].sum(axis=1)
    if not np.allclose(
        recomputed, decomposition["total_change"], rtol=0.0, atol=tolerance
    ):
        raise AssertionError("component sum does not equal the total change")
    percents = [f"{name}_percent" for name in components]
    finite = decomposition[percents].notna().all(axis=1)
    percent_sum = decomposition.loc[finite, percents].sum(axis=1)
    if not np.allclose(percent_sum, 100.0, rtol=0.0, atol=1e-6):
        raise AssertionError("component percentages do not sum to 100")
    unstable_above = float(
        design["decomposition"]["percent_stability"]["unstable_above_ratio"]
    )
    expected_flag = decomposition["percent_stability_ratio"].gt(unstable_above)
    if not decomposition["percent_decomposition_is_unstable"].eq(
        expected_flag
    ).all():
        raise AssertionError(
            "the percent-instability flag disagrees with its stability ratio"
        )
    if not decomposition["construct_label"].eq(design["construct"]["label"]).all():
        raise AssertionError("construct label drifted from the frozen design")
    if decomposition["n_common_pairs"].le(0).any():
        raise AssertionError("a cell has no common terminal pair")

    # The entry/exit residual must not depend on index-number weighting.
    grouped = decomposition.groupby(["cohort", "terminal_radius_km"])
    for key, group in grouped:
        spread = float(
            group["entry_exit_residual"].max() - group["entry_exit_residual"].min()
        )
        if spread > tolerance:
            raise AssertionError(
                f"entry/exit residual varies with weighting scheme for {key}"
            )


def build_audit_expectation(design: dict, decomposition: pd.DataFrame) -> dict:
    expected = design["audit_expectation"]
    cell = decomposition.loc[
        decomposition["cohort"].eq("all_retained")
        & decomposition["terminal_radius_km"].eq(int(expected["terminal_radius_km"]))
        & decomposition["weighting_scheme"].eq(expected["weighting_scheme"])
    ]
    if cell.empty:
        raise AssertionError("the audit-expectation cell is missing from the grid")
    row = cell.iloc[0]

    total_tol = float(expected["total_change_tolerance"])
    pct_tol = float(expected["component_percent_tolerance"])
    checks = {
        "total_change_m3_nm_per_retained_sequence": {
            "expected": float(expected["total_change_m3_nm_per_retained_sequence"]),
            "observed": float(row["total_change"]),
            "tolerance": total_tol,
            "reproduced": bool(
                abs(
                    float(row["total_change"])
                    - float(expected["total_change_m3_nm_per_retained_sequence"])
                )
                <= total_tol
            ),
        },
    }
    for name in (
        "common_pair_share_reweighting",
        "entry_exit_residual",
        "within_common_pair_capacity_mix",
    ):
        observed = float(row[f"{name}_percent"])
        target = float(expected[f"{name}_percent"])
        checks[f"{name}_percent"] = {
            "expected": target,
            "observed": observed,
            "tolerance": pct_tol,
            "reproduced": bool(abs(observed - target) <= pct_tol),
        }
    return {
        "terminal_radius_km": int(expected["terminal_radius_km"]),
        "weighting_scheme": expected["weighting_scheme"],
        "cohort": "all_retained",
        "checks": checks,
        "fully_reproduced": all(item["reproduced"] for item in checks.values()),
        "weighting_note": (
            "The entry/exit residual is invariant across all three weighting "
            "schemes. Only the split between share reweighting and within-pair "
            "capacity mix is index-number dependent, which is why the symmetric "
            "scheme is primary and the other two are reported as sensitivity."
        ),
        "construct_note": (
            "Reproducing these numbers confirms an arithmetic decomposition of "
            "a modeled composition statistic. It does not establish observed "
            "cargo ton-miles, physical rerouting, or that any individual ship "
            "sailed farther."
        ),
    }


def build_diagnostics(
    design: dict,
    design_sha256: str,
    decomposition: pd.DataFrame,
    pair_support: pd.DataFrame,
    carriers: pd.DataFrame,
) -> dict:
    primary = int(design["primary_terminal_radius_km"])
    scheme = rb.SYMMETRIC

    def cell(cohort: str, radius: int) -> dict:
        row = decomposition.loc[
            decomposition["cohort"].eq(cohort)
            & decomposition["terminal_radius_km"].eq(radius)
            & decomposition["weighting_scheme"].eq(scheme)
        ].iloc[0]
        return {
            "cohort": cohort,
            "terminal_radius_km": radius,
            "pre_mean": float(row["pre_mean"]),
            "post_mean": float(row["post_mean"]),
            "total_change": float(row["total_change"]),
            "common_pair_share_reweighting_percent": float(
                row["common_pair_share_reweighting_percent"]
            ),
            "entry_exit_residual_percent": float(row["entry_exit_residual_percent"]),
            "within_common_pair_capacity_mix_percent": float(
                row["within_common_pair_capacity_mix_percent"]
            ),
            "n_pre_sequences": int(row["n_pre_sequences"]),
            "n_post_sequences": int(row["n_post_sequences"]),
            "n_common_pairs": int(row["n_common_pairs"]),
            "n_pre_only_pairs": int(row["n_pre_only_pairs"]),
            "n_post_only_pairs": int(row["n_post_only_pairs"]),
            "excluded_pre_sequences": int(row["excluded_pre_sequences"]),
            "excluded_post_sequences": int(row["excluded_post_sequences"]),
            "total_change_is_positive": bool(float(row["total_change"]) > 0),
            "percent_stability_ratio": float(row["percent_stability_ratio"]),
            "percent_decomposition_is_unstable": bool(
                row["percent_decomposition_is_unstable"]
            ),
        }

    return {
        "design_id": design["design_id"],
        "design_sha256": design_sha256,
        "analysis_role": design["analysis_role"],
        "freeze_status": design["freeze_status"]["timing"],
        "construct_label": design["construct"]["label"],
        "construct_unit": design["construct"]["unit"],
        "primary_weighting_scheme": scheme,
        "primary_terminal_radius_km": primary,
        "census_eligible_imos": int(carriers["imo"].nunique()),
        "primary_cell": cell("all_retained", primary),
        "balanced_primary_cell": cell("both_period_carriers", primary),
        "radius_sensitivity": [
            cell("all_retained", int(radius))
            for radius in design["terminal_radius_km_grid"]
        ],
        "balanced_radius_sensitivity": [
            cell("both_period_carriers", int(radius))
            for radius in design["terminal_radius_km_grid"]
        ],
        "pair_support_counts": {
            status: int((pair_support["support_status"] == status).sum())
            for status in ("common", "pre_only_exit", "post_only_entry")
        },
        "entry_exit_residual_invariant_to_weighting": True,
        "component_split_generalises_across_grid": False,
        "total_change_sign_consistent_across_grid": bool(
            len({
                bool(float(row["total_change"]) > 0)
                for row in decomposition.loc[
                    decomposition["weighting_scheme"].eq(rb.SYMMETRIC)
                ].to_dict("records")
            }) == 1
        ),
        "unstable_percent_cells": int(
            decomposition.loc[
                decomposition["weighting_scheme"].eq(rb.SYMMETRIC),
                "percent_decomposition_is_unstable",
            ].sum()
        ),
        "reporting_guards": design["reporting_guards"],
    }


def _m(value: float) -> str:
    return f"{value / 1e6:,.3f}"


def render_markdown(
    design: dict,
    diagnostics: dict,
    decomposition: pd.DataFrame,
    audit: dict,
) -> str:
    primary = diagnostics["primary_terminal_radius_km"]
    cell = diagnostics["primary_cell"]
    balanced = diagnostics["balanced_primary_cell"]
    lines: list[str] = []
    add = lines.append

    add("# Route-burden decomposition")
    add("")
    add(f"**Design id:** `{design['design_id']}`  ")
    add(f"**Design SHA-256:** `{diagnostics['design_sha256']}`  ")
    add(f"**Frozen (UTC):** {design['frozen_utc']}  ")
    add(f"**Freeze status:** {design['freeze_status']['timing']}  ")
    add("**Verification status:** `NEEDS-VERIFY` until Mher runs the G4 commands.")
    add("")
    add(f"**Construct:** {design['construct']['label']}.  ")
    add(f"**Unit:** {design['construct']['unit']}.")
    add("")
    add(
        "Both factors are modeled. Nominal vessel capacity is a design property "
        "of the carrier, not a measured cargo quantity, and the distance is a "
        "shortest-sea-route network estimate, not an observed AIS track. A "
        "change in this mean describes **which sequences remain observable and "
        "how their modeled attributes are distributed**. It is not observed "
        "cargo ton-miles, not physical rerouting, and not evidence that any "
        "individual ship sailed farther."
    )
    add("")

    add("## Decomposition identity")
    add("")
    add("The pre-to-post change in the mean splits into three parts:")
    add("")
    for name, spec in design["decomposition"]["components"].items():
        add(f"- **`{name}`** — {spec['meaning']}.")
    add("")
    add(
        "The residual is defined as the remainder, so the three sum to the total "
        "exactly. It is independently cross-checked against its conditional-mean "
        "identity "
        "`(Y_post - Y_common_post) - (Y_pre - Y_common_pre)`, and the build fails "
        "if the two disagree."
    )
    add("")

    add(f"## Primary cell ({primary} km, symmetric weighting, all retained)")
    add("")
    add("| Quantity | Value (million m³-nm per retained sequence) | Share |")
    add("|---|---:|---:|")
    add(f"| Pre-period mean | {_m(cell['pre_mean'])} | |")
    add(f"| Post-period mean | {_m(cell['post_mean'])} | |")
    add(f"| **Total change** | **{_m(cell['total_change'])}** | **100.0%** |")
    add(
        f"| Common-pair share reweighting | "
        f"{_m(cell['total_change'] * cell['common_pair_share_reweighting_percent'] / 100)} "
        f"| {cell['common_pair_share_reweighting_percent']:.1f}% |"
    )
    add(
        f"| Entry/exit residual | "
        f"{_m(cell['total_change'] * cell['entry_exit_residual_percent'] / 100)} "
        f"| {cell['entry_exit_residual_percent']:.1f}% |"
    )
    add(
        f"| Within-common-pair capacity mix | "
        f"{_m(cell['total_change'] * cell['within_common_pair_capacity_mix_percent'] / 100)} "
        f"| {cell['within_common_pair_capacity_mix_percent']:.1f}% |"
    )
    add("")
    add(
        f"Support: {cell['n_pre_sequences']} pre and {cell['n_post_sequences']} "
        f"post retained sequences across {cell['n_common_pairs']} common terminal "
        f"pairs, with {cell['n_pre_only_pairs']} pairs leaving and "
        f"{cell['n_post_only_pairs']} entering."
    )
    add("")
    add(
        "Read together with the components, this says the increase is almost "
        "entirely **compositional**: mass moving between terminal pairs "
        f"({cell['common_pair_share_reweighting_percent']:.1f}%) plus pairs "
        f"entering and leaving support ({cell['entry_exit_residual_percent']:.1f}%). "
        "Carrying larger vessels on an unchanged terminal pair explains only "
        f"{cell['within_common_pair_capacity_mix_percent']:.1f}%."
    )
    add("")

    add("## Index-number sensitivity")
    add("")
    add(
        "Only the split between share reweighting and within-pair capacity mix "
        "depends on the weighting choice. The entry/exit residual is invariant."
    )
    add("")
    add("| Weighting scheme | Role | Share reweighting | Entry/exit | Within-pair |")
    add("|---|---|---:|---:|---:|")
    primary_rows = decomposition.loc[
        decomposition["cohort"].eq("all_retained")
        & decomposition["terminal_radius_km"].eq(primary)
    ]
    for record in primary_rows.to_dict("records"):
        role = design["weighting_schemes"][record["weighting_scheme"]]["role"]
        add(
            f"| `{record['weighting_scheme']}` | {role} | "
            f"{record['common_pair_share_reweighting_percent']:.1f}% | "
            f"{record['entry_exit_residual_percent']:.1f}% | "
            f"{record['within_common_pair_capacity_mix_percent']:.1f}% |"
        )
    add("")

    add("## The component split does not generalise")
    add("")
    add(
        f"The {cell['common_pair_share_reweighting_percent']:.1f} / "
        f"{cell['entry_exit_residual_percent']:.1f} / "
        f"{cell['within_common_pair_capacity_mix_percent']:.1f} split above is "
        f"specific to the {primary} km all-retained cell. **It is not stable "
        "across the radius grid or the carrier restriction**, and it must never "
        "be quoted as if it were a general property of the mechanism."
    )
    add("")
    add("Two facts establish that:")
    add("")
    unstable = decomposition.loc[
        decomposition["percent_decomposition_is_unstable"]
        & decomposition["weighting_scheme"].eq(rb.SYMMETRIC)
    ]
    add(
        "1. At 10 km the entry/exit residual carries "
        f"{diagnostics['radius_sensitivity'][0]['entry_exit_residual_percent']:.1f}% "
        "against "
        f"{diagnostics['radius_sensitivity'][0]['common_pair_share_reweighting_percent']:.1f}% "
        "for share reweighting — close to the reverse of the primary cell — and "
        "the within-pair term turns negative."
    )
    add(
        "2. Under the both-period carrier restriction the shares move again, to "
        f"{balanced['common_pair_share_reweighting_percent']:.1f}% / "
        f"{balanced['entry_exit_residual_percent']:.1f}% / "
        f"{balanced['within_common_pair_capacity_mix_percent']:.1f}% at "
        f"{primary} km."
    )
    add("")
    if not unstable.empty:
        add(
            "Some cells are worse than unstable: their components largely "
            "offset, so the percentage shares divide by a near-zero total and "
            "become meaningless. Those cells are flagged "
            "`percent_decomposition_is_unstable` and their percentages are not "
            "interpreted here."
        )
        add("")
        add("| Cohort | Radius (km) | Total change | max\\|component\\|/\\|total\\| |")
        add("|---|---:|---:|---:|")
        for record in unstable.to_dict("records"):
            add(
                f"| `{record['cohort']}` | {record['terminal_radius_km']} | "
                f"{_m(record['total_change'])} | "
                f"{record['percent_stability_ratio']:.2f} |"
            )
        add("")
    all_cells = (
        diagnostics["radius_sensitivity"]
        + diagnostics["balanced_radius_sensitivity"]
    )
    positive = [item for item in all_cells if item["total_change"] > 0]
    negative = [item for item in all_cells if item["total_change"] <= 0]
    within_small = all(
        abs(item["within_common_pair_capacity_mix_percent"]) < 50.0
        for item in all_cells
        if not item["percent_decomposition_is_unstable"]
    )
    add(
        f"Across the {len(all_cells)} radius-by-cohort cells, "
        f"{len(positive)} show a rise in the modeled burden per retained "
        f"sequence and {len(negative)} do not."
    )
    if negative:
        add("")
        for item in negative:
            add(
                f"- `{item['cohort']}` at {item['terminal_radius_km']} km gives "
                f"{_m(item['total_change'])} million m³-nm per retained "
                "sequence — the opposite sign to the primary cell. The "
                "direction of the headline is therefore **not** universal "
                "across the sensitivity grid."
            )
    add("")
    if within_small:
        add(
            "What does hold in every interpretable cell is the weaker, "
            "qualitative statement: whatever change occurs is **compositional** "
            "rather than within-pair. Carrying different vessels on an "
            "unchanged terminal pair never accounts for a large share of the "
            "movement. The apportionment between mass moving across pairs and "
            "pairs entering or leaving support is not identified by this "
            "design."
        )
    else:
        add(
            "The within-pair term is large in at least one interpretable cell, "
            "so even the compositional-versus-within-pair reading does not hold "
            "uniformly. The grid is reported without a summarising claim."
        )
    add("")

    add("## Radius sensitivity (symmetric weighting, all retained)")
    add("")
    add(
        "| Radius (km) | Pre mean | Post mean | Total change | Share | "
        "Entry/exit | Within-pair | Pre seq. | Post seq. |"
    )
    add("|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for item in diagnostics["radius_sensitivity"]:
        add(
            f"| {item['terminal_radius_km']} | {_m(item['pre_mean'])} | "
            f"{_m(item['post_mean'])} | {_m(item['total_change'])} | "
            f"{item['common_pair_share_reweighting_percent']:.1f}% | "
            f"{item['entry_exit_residual_percent']:.1f}% | "
            f"{item['within_common_pair_capacity_mix_percent']:.1f}% | "
            f"{item['n_pre_sequences']} | {item['n_post_sequences']} |"
        )
    add("")

    add("## Both-period carrier restriction")
    add("")
    add(
        "Restricting to IMOs with a retained sequence in both periods holds the "
        "observed carrier set fixed, so composition cannot be produced purely by "
        "carrier turnover."
    )
    add("")
    add(
        "| Radius (km) | Total change | Share | Entry/exit | Within-pair | "
        "Pre seq. | Post seq. |"
    )
    add("|---:|---:|---:|---:|---:|---:|---:|")
    for item in diagnostics["balanced_radius_sensitivity"]:
        mark = " ‡" if item["percent_decomposition_is_unstable"] else ""
        add(
            f"| {item['terminal_radius_km']} | {_m(item['total_change'])} | "
            f"{item['common_pair_share_reweighting_percent']:.1f}%{mark} | "
            f"{item['entry_exit_residual_percent']:.1f}%{mark} | "
            f"{item['within_common_pair_capacity_mix_percent']:.1f}%{mark} | "
            f"{item['n_pre_sequences']} | {item['n_post_sequences']} |"
        )
    add("")
    add(
        "‡ Components largely offset, so these percentages divide by a "
        "near-zero total and carry no interpretation."
    )
    add("")
    add(
        f"At {primary} km the restricted cohort gives a total change of "
        f"{_m(balanced['total_change'])} million m³-nm per retained sequence "
        f"across {balanced['n_pre_sequences']} pre and "
        f"{balanced['n_post_sequences']} post sequences."
    )
    add("")

    add("## Censoring and support bounds")
    add("")
    add(
        f"At {primary} km, {cell['excluded_pre_sequences']} pre and "
        f"{cell['excluded_post_sequences']} post resolved sequences are excluded "
        "from the complete case because no expanded-specification route distance "
        "or nominal capacity could be joined."
    )
    add("")
    add(
        "Excluded and vanished sequences are **not** assigned a burden of zero "
        "and are **not** assumed to carry the pre-period average. The total is "
        "conditional on the support documented by the task-7 network-support "
        "frontier, where Hormuz-crossing support falls from 145 to 2 sequences "
        f"at {primary} km. A decomposition computed on a panel that lost its "
        "Hormuz-crossing mass will attribute much of the change to entry/exit "
        "for exactly that reason, and the entry/exit share here "
        f"({cell['entry_exit_residual_percent']:.1f}%) should be read as that "
        "support fact, not as a behavioural finding."
    )
    add("")

    add("## Interpretation limits")
    add("")
    add(
        f"- The construct is `{design['construct']['label']}`. It is not "
        "observed cargo ton-miles."
    )
    add(
        "- It is not physical rerouting and not evidence that individual ships "
        "sailed farther. No vessel-level distance change is measured anywhere "
        "in this artifact."
    )
    add(
        "- The change is compositional. It reflects which terminal pairs retain "
        "modeled support and how retained sequences distribute across them."
    )
    add(
        "- No AIS-dark physical throughput may be inferred, and nothing here is "
        "an average treatment effect or a causal identification."
    )
    add(
        "- The upstream capacity, comparison, and task-7 artifacts are "
        "hash-verified read-only inputs to this phase."
    )
    add("")
    return "\n".join(lines) + "\n"


def main() -> int:
    design, design_sha256 = load_design()
    voyages, carriers = load_verified_inputs(design)

    decomposition, pair_support = build_decomposition(design, voyages)
    audit = build_audit_expectation(design, decomposition)
    diagnostics = build_diagnostics(
        design, design_sha256, decomposition, pair_support, carriers
    )
    markdown = render_markdown(design, diagnostics, decomposition, audit)

    weighting = decomposition.loc[
        decomposition["cohort"].eq("all_retained")
    ].copy()

    for key, frame in (
        ("decomposition_csv", decomposition),
        ("weighting_sensitivity_csv", weighting),
        ("pair_support_csv", pair_support),
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
    print(
        f"\nRoute-burden decomposition (primary {cell['terminal_radius_km']} km, "
        f"{diagnostics['primary_weighting_scheme']}):"
    )
    print(
        f"  total change: {cell['total_change']:,.3f} m3-nm per retained "
        f"sequence ({_m(cell['total_change'])} million)"
    )
    print(
        f"  common-pair share reweighting: "
        f"{cell['common_pair_share_reweighting_percent']:.1f}%"
    )
    print(f"  entry/exit residual:           "
          f"{cell['entry_exit_residual_percent']:.1f}%")
    print(
        f"  within-pair capacity mix:      "
        f"{cell['within_common_pair_capacity_mix_percent']:.1f}%"
    )
    print(
        "  audit expectation: "
        f"{'REPRODUCED' if audit['fully_reproduced'] else 'NOT REPRODUCED'}"
    )
    print("\nRadius and cohort sensitivity (symmetric weighting):")
    print(
        decomposition.loc[
            decomposition["weighting_scheme"].eq(rb.SYMMETRIC),
            [
                "cohort",
                "terminal_radius_km",
                "total_change",
                "common_pair_share_reweighting_percent",
                "entry_exit_residual_percent",
                "within_common_pair_capacity_mix_percent",
            ],
        ].to_string(index=False)
    )
    print("\nInterpretation guard:")
    print(
        " - The 54.9/43.8/1.3 split is SPECIFIC to the 30 km all-retained cell."
    )
    print(
        "   It does not generalise: 10 km gives ~22/80/-2 and the both-period"
    )
    print(
        "   carrier restriction gives ~97/9/-6 at 30 km. Quote the absolute"
    )
    print("   components, not the apportionment.")
    if diagnostics["unstable_percent_cells"]:
        print(
            f" - {diagnostics['unstable_percent_cells']} cell(s) flagged "
            "percent_decomposition_is_unstable: components offset and the"
        )
        print("   percentages divide by a near-zero total. Do not interpret them.")
    print(f" - Construct: {design['construct']['label']}.")
    print(" - NOT observed cargo ton-miles, NOT physical rerouting, and NOT")
    print("   evidence that individual ships sailed farther.")
    print(" - The change is compositional and conditional on modeled support.")
    print(" - Components reconcile to the total exactly.")
    print(" - This is NEEDS-VERIFY until Mher records the G4 output.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
