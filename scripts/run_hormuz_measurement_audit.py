"""B1 - run the Hormuz instrument revision audit across two PortWatch states.

Reads `config/hormuz_measurement_audit.yaml`, loads the July and August
measurement states through the registry, verifies their hashes, reproduces the
frozen numerical invariants from the raw data, decomposes the Hormuz revision
into a proportional component and a non-proportional residual, and writes the
five B1 outputs plus a manifest.

The states are never averaged and never substituted for one another. The
mapping estimator and its sample come from the frozen config; this script does
not choose them. A failed invariant stops the phase.

Nothing here identifies why PortWatch revised the series. The audit
establishes that a unit-specific retrospective revision occurred between two
captures; the provider-side reason is not observed.

Usage:
    python scripts/run_hormuz_measurement_audit.py --check
    python scripts/run_hormuz_measurement_audit.py --check --dry-run
"""
from __future__ import annotations

import argparse
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from hormuz_throughput import config                                        # noqa: E402
from hormuz_throughput.instrument_shift import (                            # noqa: E402
    annual_summary,
    assert_not_averaged,
    assert_states_separate,
    changed_rows_by_unit,
    daily_revision_frame,
    fit_declared_mappings,
    monthly_revision_distribution,
    overlap_panel,
    residual_summary,
    sha256_file,
    split_residuals_by_onset,
    squared_error_decomposition,
    tidy_state,
    verify_invariants,
    wto_state_audit,
)
from hormuz_throughput.registry import RegisteredArtifact, get_variable     # noqa: E402

SPEC_PATH = config.CONFIG_DIR / "hormuz_measurement_audit.yaml"


def _json_default(value):
    """Coerce numpy scalars so a manifest never fails to serialise."""
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    if isinstance(value, (np.bool_,)):
        return bool(value)
    if isinstance(value, (pd.Timestamp,)):
        return str(value)
    raise TypeError(f"Unserialisable manifest value of type {type(value)!r}.")


def _git(*args: str) -> str:
    try:
        return subprocess.run(
            ["git", *args],
            cwd=config.ROOT,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return ""


def load_state(spec: dict, panel_spec: dict, consumer: str):
    """Admit one measurement state through the registry and verify its hash.

    The August vintage is registered sensitivity-only behind a consumer
    allowlist. B1 opts in as a declared sensitivity consumer: it reads the
    vintage as the second measurement state of a revision audit, and never
    promotes or substitutes it. The opt-in is declared in the frozen config,
    not decided here.
    """
    allow_sensitivity = bool(spec.get("allow_sensitivity", False))
    try:
        artifact = get_variable(
            spec["registry_variable"],
            query={"consumer": consumer},
            allow_sensitivity=allow_sensitivity,
        )
    except PermissionError as exc:
        raise PermissionError(
            f"STOP: the registry refused measurement state {spec['label']!r}.\n"
            f"  {exc}\n"
            f"  consumer presented: {consumer}\n"
            "B1 reads this vintage as the second measurement state of a "
            "revision audit; it does not promote or substitute it. Admitting "
            "a new sensitivity consumer is a data-access governance decision "
            "recorded in config/sources.yaml, which Track B does not edit."
        ) from exc
    if not isinstance(artifact, RegisteredArtifact):
        raise TypeError(
            f"{spec['registry_variable']!r} must resolve as a frozen artifact."
        )
    expected_path = (config.ROOT / spec["path"]).resolve()
    if artifact.path.resolve() != expected_path:
        raise ValueError(
            f"State {spec['label']!r} resolved to {artifact.path}, expected "
            f"{expected_path}. Refusing to substitute a measurement state."
        )
    if artifact.sha256 != spec["expected_sha256"]:
        raise ValueError(
            f"STOP: input hash mismatch for state {spec['label']!r}.\n"
            f"  expected {spec['expected_sha256']}\n  found    {artifact.sha256}\n"
            "The frozen input changed; re-freeze before running B1."
        )
    frame = artifact.read_csv(encoding="utf-8-sig")
    return tidy_state(
        frame,
        label=spec["label"],
        path=artifact.path.relative_to(config.ROOT),
        sha256=artifact.sha256,
        date_column=panel_spec["date_column"],
        date_format=panel_spec["date_format"],
        unit_column=panel_spec["unit_column"],
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help=(
            "Print the invariant verification table. Invariant enforcement is "
            "ALWAYS on; this flag only controls the printed report. There is "
            "no flag that disables the frozen-invariant check."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run every computation and check but write no output files.",
    )
    args = parser.parse_args()

    spec = yaml.safe_load(SPEC_PATH.read_text(encoding="utf-8"))
    panel_spec = spec["panel"]
    unit_col = panel_spec["unit_column"]
    date_col = panel_spec["date_column"]
    focus = panel_spec["focus_unit"]
    primary = panel_spec["primary_measure"]
    quantiles = spec["residual_reporting"]["quantiles"]
    onset = spec["windows"]["operational_onset"]
    consumer = spec["consumer"]
    config_sha = sha256_file(SPEC_PATH)

    print("=" * 72)
    print("B1 INSTRUMENT REVISION AUDIT")
    print("=" * 72)
    print(f"config          : {SPEC_PATH.relative_to(config.ROOT)}")
    print(f"config sha256   : {config_sha}")
    print(f"git branch/HEAD : {_git('branch', '--show-current')} / {_git('rev-parse', 'HEAD')}")
    print(f"default mapping : {spec['mapping']['default']}")
    print()

    july = load_state(spec["states"]["july"], panel_spec, consumer)
    august = load_state(spec["states"]["august"], panel_spec, consumer)
    separation = assert_states_separate(july, august)
    print("STATES (verified separate, never averaged)")
    for label in ("july", "august"):
        s = separation[label]
        print(
            f"  {label:<7} rows={s['n_rows']:>6}  {s['date_min']} -> {s['date_max']}"
            f"  sha256={s['sha256'][:16]}..."
        )

    n_units_july = july.frame[unit_col].nunique()
    n_units_august = august.frame[unit_col].nunique()
    if n_units_july != panel_spec["n_units_expected"] or n_units_august != panel_spec["n_units_expected"]:
        raise ValueError(
            f"STOP: expected {panel_spec['n_units_expected']} chokepoints, found "
            f"july={n_units_july} august={n_units_august}."
        )

    measures = list(panel_spec["count_measures"]) + list(panel_spec["capacity_measures"])
    panel = overlap_panel(july, august, measures, unit_col, date_col)
    overlap_dates = panel[date_col]
    n_days = int(overlap_dates.nunique())
    expected_overlap = spec["windows"]["expected_overlap"]
    overlap_record = {
        "start": str(overlap_dates.min().date()),
        "end": str(overlap_dates.max().date()),
        "n_days": n_days,
        "n_units": int(panel[unit_col].nunique()),
    }
    print(
        f"\nOVERLAP  {overlap_record['start']} -> {overlap_record['end']}  "
        f"({n_days} days x {overlap_record['n_units']} chokepoints)"
    )
    for key in ("start", "end", "n_days"):
        if str(overlap_record[key]) != str(expected_overlap[key]):
            raise ValueError(
                f"STOP: overlap {key} is {overlap_record[key]}, frozen config "
                f"expects {expected_overlap[key]}."
            )

    by_unit = changed_rows_by_unit(panel, unit_col)
    assert_not_averaged(
        by_unit.rename(columns={"mean_july": "july", "mean_august": "august"}),
        "july",
        "august",
    )
    primary_changed = by_unit[by_unit["measure"] == primary].sort_values(
        "pct_changed_rows", ascending=False
    )
    hormuz_pct = float(
        primary_changed.loc[primary_changed[unit_col] == focus, "pct_changed_rows"].iloc[0]
    )
    others = primary_changed[primary_changed[unit_col] != focus]
    next_pct = float(others["pct_changed_rows"].iloc[0])
    next_unit = str(others[unit_col].iloc[0])
    median_pct = float(primary_changed["pct_changed_rows"].median())

    print(f"\nCHANGED ROWS ({primary}, all 28 chokepoints, {n_days} overlapping days)")
    print(f"  {focus:<22} {hormuz_pct:>10.4f}%")
    print(f"  next highest: {next_unit:<9} {next_pct:>10.4f}%")
    print(f"  median across 28 units  {median_pct:>10.4f}%")

    series = (
        panel[(panel[unit_col] == focus) & (panel["measure"] == primary)]
        .sort_values(date_col)
        .reset_index(drop=True)
    )

    annual = annual_summary(panel, focus, primary, unit_col, date_col)
    computed_ratios = {
        int(row.year): float(row.ratio_august_over_july) for row in annual.itertuples()
    }

    fits = fit_declared_mappings(series, spec["mapping"]["forms"], date_col)
    default_name = spec["mapping"]["default"]
    if default_name not in fits:
        raise ValueError(f"STOP: default mapping {default_name!r} is not declared.")
    default_fit = fits[default_name]

    print("\nDECLARED MAPPINGS (July -> August, samples frozen in config)")
    for name, fit in fits.items():
        marker = "*" if name == default_name else " "
        print(
            f" {marker} {name:<32} form={fit.form:<12} "
            f"intercept={fit.intercept:>9.6f} scale={fit.scale:>9.6f} n={fit.n_sample}"
        )
    print("   (* = frozen reporting default; others are declared sensitivities)")

    x = series["july"].to_numpy(float)
    y = series["august"].to_numpy(float)
    decompositions = {
        name: squared_error_decomposition(x, y, fit) for name, fit in fits.items()
    }
    default_decomp = decompositions[default_name]

    print("\nPROPORTIONAL / NON-PROPORTIONAL DECOMPOSITION (full overlap)")
    print(f"  raw revision RMSE           : {default_decomp['rmse_raw_revision']:.6f}")
    print(f"  RMSE after default mapping  : {default_decomp['rmse_after_mapping']:.6f}")
    print(
        f"  squared error remaining     : "
        f"{default_decomp['fraction_squared_error_remaining']:.6f}"
    )
    print(
        f"  absorbed by rescaling       : "
        f"{default_decomp['share_absorbed_by_mapping']:.6f}"
    )

    residual_split = split_residuals_by_onset(series, default_fit, onset, quantiles, date_col)
    print(f"\nRESIDUAL BEHAVIOUR, SPLIT AT LOCKED ONSET {onset} (default mapping)")
    for period in ("pre_onset", "post_onset"):
        block = residual_split[period]
        print(
            f"  {period:<11} n={block['n']:>5}  mean={block['mean']:>9.6f}  "
            f"sd={block['sd']:>9.6f}  rmse={block['rmse']:>9.6f}  "
            f"min={block['min']:>8.3f}  max={block['max']:>8.3f}"
        )

    daily = daily_revision_frame(series, fits, default_name, onset, date_col, primary)
    assert_not_averaged(daily, f"{primary}_july", f"{primary}_august")
    monthly = monthly_revision_distribution(daily, date_col)

    print("\nTEMPORAL DISTRIBUTION OF REVISIONS (annual)")
    for row in annual.itertuples():
        print(
            f"  {row.year}  days={row.n_days:>4}  changed={row.n_changed_rows:>4} "
            f"({row.pct_changed_rows:>7.3f}%)  july_mean={row.mean_july:>7.3f}  "
            f"august_mean={row.mean_august:>7.3f}  ratio={row.ratio_august_over_july:.6f}"
            + ("  [partial year]" if row.partial_year else "")
        )

    print("\nHORMUZ REVISIONS BY MEASURE")
    hormuz_measures = by_unit[by_unit[unit_col] == focus].sort_values(
        "pct_changed_rows", ascending=False
    )
    for row in hormuz_measures.itertuples():
        print(
            f"  {row.measure:<24} changed={row.pct_changed_rows:>8.4f}%  "
            f"july_mean={row.mean_july:>14.3f}  august_mean={row.mean_august:>14.3f}  "
            f"ratio={row.mean_ratio_august_over_july:.6f}"
        )

    wto_spec = spec["wto"]
    wto_audit, wto_pairwise = wto_state_audit(
        config.ROOT / wto_spec["directory"],
        wto_spec["glob"],
        config.ROOT / wto_spec["provenance"],
        wto_spec["provenance_variable"],
        wto_spec["date_aliases"],
        wto_spec["value_aliases"],
        float(wto_spec["value_tolerance"]),
    )
    n_regimes = int(wto_audit["regime_id"].nunique())
    print(f"\nWTO MEASUREMENT STATES: {len(wto_audit)} files, {n_regimes} distinct value regimes")
    for row in wto_audit.itertuples():
        print(
            f"  regime {row.regime_id}  {row.file[:58]:<58} rows={row.n_rows:>4} "
            f"{row.data_start} -> {row.data_end}  retrieved={row.retrieved_utc_last[:10] or 'n/a'}"
        )

    computed = {
        "hormuz_pct_changed_n_tanker": hormuz_pct,
        "next_highest_pct_changed_n_tanker": next_pct,
        "next_highest_pct_changed_n_tanker__unit": next_unit,
        "median_pct_changed_n_tanker": median_pct,
        "hormuz_annual_ratio_n_tanker": computed_ratios,
    }
    invariant_table = verify_invariants(computed, spec["invariants"])
    if args.check:
        print("\nFROZEN INVARIANT VERIFICATION (computed from raw states)")
        print(invariant_table.drop(columns=["description"]).to_string(index=False))
    print(f"\nINVARIANTS: {int(invariant_table['passed'].sum())}/{len(invariant_table)} passed")

    outputs = spec["outputs"]
    if args.dry_run:
        print("\n--dry-run: no files written.")
        return 0

    paths = {key: config.ROOT / value for key, value in outputs.items()}
    for path in paths.values():
        path.parent.mkdir(parents=True, exist_ok=True)

    by_unit.to_csv(paths["by_chokepoint"], index=False)
    daily.to_csv(paths["hormuz_daily"], index=False)
    annual.to_csv(paths["hormuz_annual"], index=False)
    wto_audit.to_csv(paths["wto_audit"], index=False)

    manifest = {
        "schema": "hormuz_measurement_state_manifest/1",
        "phase": "B1",
        "status": "frozen",
        "script": "scripts/run_hormuz_measurement_audit.py",
        "command": " ".join([Path(sys.argv[0]).name, *sys.argv[1:]]),
        "run_utc": datetime.now(timezone.utc).isoformat(),
        "plan": {"path": spec["plan"], "version": spec["plan_version"]},
        "git": {
            "commit": _git("rev-parse", "HEAD"),
            "branch": _git("branch", "--show-current"),
            "dirty": bool(_git("status", "--porcelain")),
            "status_porcelain": _git("status", "--porcelain"),
        },
        "config": {
            "path": str(SPEC_PATH.relative_to(config.ROOT)),
            "sha256": config_sha,
            "version": spec["version"],
        },
        "inputs": {
            "july": {
                "path": str(july.path),
                "sha256": july.sha256,
                "registry_variable": spec["states"]["july"]["registry_variable"],
                "sensitivity_opt_in": bool(
                    spec["states"]["july"].get("allow_sensitivity", False)
                ),
            },
            "august": {
                "path": str(august.path),
                "sha256": august.sha256,
                "registry_variable": spec["states"]["august"]["registry_variable"],
                "sensitivity_opt_in": bool(
                    spec["states"]["august"].get("allow_sensitivity", False)
                ),
            },
            "registry_consumer": consumer,
            "sensitivity_use_note": (
                "The August vintage is admitted as a declared sensitivity input: "
                "the second measurement state of a revision audit. It is not "
                "promoted, not substituted for the pinned primary, and not "
                "averaged with it."
            ),
        },
        "measurement_states": separation,
        "analysis_window": overlap_record,
        "focus_unit": focus,
        "primary_measure": primary,
        "measures_audited": measures,
        "estimators": {
            "default_mapping": default_name,
            "residual_evaluation": spec["mapping"]["residual_evaluation"],
            "forms": {name: fit.to_dict() for name, fit in fits.items()},
            "sample_selection_rule": (
                "Samples are fixed by date in the frozen config before fitting. "
                "No sample or form was chosen after inspecting residuals."
            ),
        },
        "revision_decomposition": decompositions,
        "residual_distribution": residual_split,
        "changed_rows": {
            "primary_measure": primary,
            "hormuz_pct_changed": hormuz_pct,
            "next_highest_unit": next_unit,
            "next_highest_pct_changed": next_pct,
            "median_pct_changed_across_units": median_pct,
            "n_overlap_days_per_unit": n_days,
        },
        "annual_ratios_august_over_july": computed_ratios,
        "temporal_distribution_monthly": monthly.to_dict(orient="records"),
        "wto_measurement_states": {
            "n_files": int(len(wto_audit)),
            "n_distinct_regimes": n_regimes,
            "regime_rule": wto_spec["regime_rule"],
            "files": wto_audit.to_dict(orient="records"),
            "pairwise_comparisons": wto_pairwise,
        },
        "invariant_verification": {
            "enforced": True,
            "all_passed": bool(invariant_table["passed"].all()),
            "checks": invariant_table.to_dict(orient="records"),
            "note": (
                "Expected values in the config are verification targets only. "
                "Every reported number is computed from the frozen raw states."
            ),
        },
        "assertions": {
            "states_never_averaged": True,
            "states_never_substituted": True,
            "input_hashes_match_frozen_config": True,
            "no_raw_data_modified": True,
            "no_post_hoc_mapping_selection": True,
            "august_vintage_not_promoted_to_primary": True,
        },
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "pandas": pd.__version__,
            "numpy": np.__version__,
        },
        "limitations": spec["limitations"],
        "claims_not_authorised": [
            "That the Hormuz disruption caused the PortWatch revision.",
            "Any causal ATT or structural treatment effect.",
            "That Hormuz traffic physically stopped.",
            "That the residual revision is a measurement-error variance.",
            "Any averaging or blending of the July and August states.",
        ],
        "outputs": {},
    }

    for key in ("by_chokepoint", "hormuz_daily", "hormuz_annual", "wto_audit"):
        manifest["outputs"][key] = {
            "path": outputs[key],
            "sha256": sha256_file(paths[key]),
            "n_rows": int(
                {
                    "by_chokepoint": len(by_unit),
                    "hormuz_daily": len(daily),
                    "hormuz_annual": len(annual),
                    "wto_audit": len(wto_audit),
                }[key]
            ),
        }

    paths["manifest"].write_text(
        json.dumps(manifest, indent=2, default=_json_default) + "\n", encoding="utf-8"
    )

    print("\nOUTPUTS")
    for key in ("by_chokepoint", "hormuz_daily", "hormuz_annual", "wto_audit"):
        info = manifest["outputs"][key]
        print(f"  {info['path']:<62} rows={info['n_rows']:>5}  sha256={info['sha256'][:16]}...")
    print(f"  {outputs['manifest']:<62} sha256={sha256_file(paths['manifest'])[:16]}...")

    print("\nB1 COMPLETE. Measurement revision established; no cause claimed.")
    print("STOP AND REPORT: paste this complete terminal output.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
