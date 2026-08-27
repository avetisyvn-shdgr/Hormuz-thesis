"""B2 - Red Sea positive control under the frozen receiver-test specification.

Reads `config/hormuz_receiver_test.yaml`, reproduces the pre-registered anchor
pair's arithmetic, then evaluates it against two spatial placebo families and a
temporal null that enumerates every unique admissible pseudo-onset exactly once
under 90, 180, and 365-day guards.

Both declared onsets are reported. Neither is the headline: the recovered
fraction moves by roughly a factor of two between them, and that sensitivity is
itself the finding.

Spatial families are reported as standardised ranks with a maximum statistic
and NO inferential p-value, because cross-sectional exchangeability across
chokepoints is not defensible. The p-value comes from the temporal null.

Nothing here opens B3, and nothing here is vessel linkage.

Usage:
    python scripts/run_receiver_test.py --phase positive-control
    python scripts/run_receiver_test.py --phase positive-control --dry-run
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

from lngfreight import config                                        # noqa: E402
from lngfreight.instrument_shift import sha256_file                  # noqa: E402
from lngfreight.receiver_equivalence import (                        # noqa: E402
    admissible_onsets,
    eligible_units,
    finite_sample_p_value,
    response_frame,
    spatial_family,
    temporal_support,
)
from lngfreight.spatial import slugify_portname, wide_chokepoint_panel  # noqa: E402

SPEC_PATH = config.CONFIG_DIR / "hormuz_receiver_test.yaml"


def _git(*args: str) -> str:
    try:
        return subprocess.run(
            ["git", *args], cwd=config.ROOT, capture_output=True, text=True, check=True
        ).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return ""


def _json_default(value):
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        return float(value)
    if isinstance(value, np.bool_):
        return bool(value)
    if isinstance(value, (pd.Timestamp,)):
        return str(value)
    raise TypeError(f"unserialisable manifest value of type {type(value)!r}")


class ResponseCache:
    """One response frame per date, reused across onsets, families and guards.

    The frame at a given date depends only on that date and the donor-exclusion
    list, so recomputing it per pair or per guard would be wasted work and
    would risk the families silently disagreeing.
    """

    def __init__(self, panel, affected, horizon_weeks):
        self._panel = panel
        self._affected = affected
        self._horizon = horizon_weeks
        self._store: dict[pd.Timestamp, pd.Series] = {}
        self.failures = 0

    def get(self, date):
        key = pd.Timestamp(date)
        if key not in self._store:
            try:
                self._store[key] = response_frame(
                    self._panel, key, self._affected, self._horizon
                )
            except (ValueError, KeyError):
                self.failures += 1
                self._store[key] = None
        return self._store[key]

    def __len__(self):
        return sum(1 for value in self._store.values() if value is not None)


def load_disruptions(spec: dict) -> tuple[list, list]:
    """Documented disruption onsets, windows, and affected units.

    Comes from the same external chronology that anchors the A1 detector mask,
    so B2 and A1 cannot disagree about when a unit was disrupted.
    """
    path = config.ROOT / spec["support"]["disruption_source"]
    register = yaml.safe_load(path.read_text(encoding="utf-8"))
    events, units = [], set()
    for event in register["events"].values():
        onset = pd.Timestamp(event["onset"])
        end = event.get("end")
        raw = event.get("units") or [event.get("unit")]
        event_units = {slugify_portname(value) for value in raw if value}
        events.append(
            (onset, pd.Timestamp(end) if end else pd.Timestamp("2100-01-01"), event_units)
        )
        units.update(event_units)
    return events, sorted(units)


def evaluate_onset(
    label: str,
    onset_spec: dict,
    spec: dict,
    panel: pd.DataFrame,
    cache: ResponseCache,
    disruptions: tuple,
) -> dict:
    """Anchor arithmetic, both spatial families, and the temporal null."""
    onset = pd.Timestamp(onset_spec["date"])
    emitter = spec["anchor_pair"]["emitter"]
    receiver = spec["anchor_pair"]["receiver"]
    horizon = int(spec["statistic"]["horizon_weeks"])
    baseline_days = int(spec["statistic"]["baseline_days"])
    events, disrupted_units = disruptions

    response = cache.get(onset)
    if response is None:
        raise ValueError(f"could not compute the response frame at {onset.date()}")
    loss = -float(response[emitter])
    gain = float(response[receiver])
    recovered = gain / loss if loss > 0 else float("nan")

    print(f"\n{'=' * 70}\nONSET {label}: {onset.date()}  ({onset_spec['label']})\n{'=' * 70}")
    print(f"  emitter loss   {loss:8.4f} /day   ({emitter})")
    print(f"  receiver gain  {gain:8.4f} /day   ({receiver})")
    print(f"  recovered      {100 * recovered:8.2f} %")

    # -- support and standardisation ---------------------------------------
    eligible = eligible_units(
        panel,
        onset,
        min_baseline=float(spec["support"]["min_baseline_transits_per_day"]),
        always_excluded=[e["unit"] for e in spec["support"]["always_excluded"]],
        disrupted_units=disrupted_units,
    )
    # The anchor pair is evaluated even though both its units are disrupted;
    # the support rules govern the PLACEBO family, not the pre-registered pair.
    family_units = sorted(set(eligible) | {emitter, receiver})
    print(f"\n  eligible placebo units: {len(eligible)}  (anchor pair added back for scoring)")

    guards = [int(g) for g in spec["temporal_placebo"]["guards_days"]]
    relevant = {emitter, receiver}
    scale_pool = admissible_onsets(
        panel, events,
        relevant_units=relevant,
        horizon_weeks=horizon, baseline_days=baseline_days,
        guard_days=max(guards),
    )
    pre_dates = scale_pool[scale_pool < onset]
    min_draws = int(spec["standardisation"]["min_pre_onset_draws"])
    if len(pre_dates) < min_draws:
        raise ValueError(
            f"only {len(pre_dates)} pre-onset draws for standardisation, need {min_draws}"
        )
    frames = [cache.get(d) for d in pre_dates]
    frames = [f for f in frames if f is not None]
    scales = pd.DataFrame(frames).std(ddof=1).replace(0.0, np.nan)
    print(f"  standardisation: {len(frames)} pre-onset draws before {onset.date()}")

    # -- spatial families (descriptive) ------------------------------------
    receivers_family = spatial_family(response, scales, family_units, receiver, sign=+1.0)
    emitters_family = spatial_family(response, scales, family_units, emitter, sign=-1.0)
    for name, fam in (
        ("same_emitter_alternative_receivers", receivers_family),
        ("same_receiver_alternative_emitters", emitters_family),
    ):
        print(
            f"\n  {name}\n"
            f"    anchor z={fam['anchor_standardised']:.3f}  "
            f"rank {fam['rank_of_anchor']}/{fam['family_size']}  "
            f"family max {fam['max_statistic']:.3f} ({fam['max_statistic_unit']})  "
            f"pctile {fam['percentile_within_family']:.1f}%"
        )
    print("    (descriptive ranks only; no inferential p-value is computed)")

    # -- temporal null ------------------------------------------------------
    print(f"\n  TEMPORAL NULL (every unique admissible date used once)")
    guard_rows = []
    null_records = []
    for guard in guards:
        admissible = admissible_onsets(
            panel, events,
            relevant_units=relevant,
            horizon_weeks=horizon, baseline_days=baseline_days, guard_days=guard,
        )
        support = temporal_support(admissible, horizon_weeks=horizon)
        values = []
        for date in admissible:
            frame = cache.get(date)
            if frame is None:
                continue
            placebo_loss = -float(frame[emitter])
            if placebo_loss <= 0:
                continue  # recovered fraction is undefined without a loss
            values.append(float(frame[receiver]) / placebo_loss)
            null_records.append(
                {
                    "onset_label": label,
                    "guard_days": guard,
                    "pseudo_onset": str(date.date()),
                    "recovered_fraction": values[-1],
                }
            )
        stats = finite_sample_p_value(np.asarray(values), recovered)
        row = {
            "onset_label": label,
            "guard_days": guard,
            **support,
            "n_null_with_positive_loss": stats["B"],
            "n_null_ge_observed": stats["n_null_ge_observed"],
            "p_value": stats["p_value"],
            "p_value_floor": stats["floor"],
            "null_median": float(np.median(values)) if values else float("nan"),
        }
        guard_rows.append(row)
        print(
            f"    guard {guard:>3}d  admissible={support['n_unique_admissible_dates']:>5}"
            f"  non-overlapping~{support['approx_non_overlapping_windows']:>3}"
            f"  B={stats['B']:>5}  p={stats['p_value']:.4f}"
            f"  floor={stats['floor']:.4f}"
        )

    return {
        "label": label,
        "onset": str(onset.date()),
        "onset_role": onset_spec["role"],
        "emitter_loss_per_day": loss,
        "receiver_gain_per_day": gain,
        "recovered_fraction": recovered,
        "eligible_family_size": len(eligible),
        "spatial": {
            "same_emitter_alternative_receivers": receivers_family,
            "same_receiver_alternative_emitters": emitters_family,
        },
        "temporal": guard_rows,
        "_null_records": null_records,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", choices=["positive-control"], required=True)
    parser.add_argument("--dry-run", action="store_true", help="compute but write nothing")
    args = parser.parse_args()

    spec = yaml.safe_load(SPEC_PATH.read_text(encoding="utf-8"))
    config_sha = sha256_file(SPEC_PATH)
    panel_spec = spec["panel"]

    print("=" * 70)
    print("B2 RED SEA POSITIVE CONTROL")
    print("=" * 70)
    print(f"config        : {SPEC_PATH.relative_to(config.ROOT)}")
    print(f"config sha256 : {config_sha}")
    print(f"git           : {_git('branch', '--show-current')} / {_git('rev-parse', 'HEAD')}")

    panel = wide_chokepoint_panel(
        value_col=panel_spec["value_column"],
        start=panel_spec["start"],
        end=panel_spec["end"],
    )
    if panel.shape[1] != int(panel_spec["n_units_expected"]):
        raise ValueError(
            f"STOP: expected {panel_spec['n_units_expected']} chokepoints, got {panel.shape[1]}"
        )
    print(f"panel         : {panel.shape[0]} days x {panel.shape[1]} chokepoints")

    disruptions = load_disruptions(spec)
    events, disrupted_units = disruptions
    print(f"disruptions   : {len(events)} documented events, units {disrupted_units}")

    affected = sorted(set(disrupted_units) | {"strait_of_hormuz"})
    cache = ResponseCache(panel, affected, int(spec["statistic"]["horizon_weeks"]))

    results = []
    for key in ("register_onset", "external_onset"):
        results.append(
            evaluate_onset(key, spec["onsets"][key], spec, panel, cache, disruptions)
        )

    # -- invariants ---------------------------------------------------------
    register = next(r for r in results if r["label"] == "register_onset")
    checks = spec["invariants"]["anchor_at_register_onset"]
    rows = []
    for name, computed in (
        ("emitter_loss_per_day", register["emitter_loss_per_day"]),
        ("receiver_gain_per_day", register["receiver_gain_per_day"]),
        ("recovered_fraction_pct", 100 * register["recovered_fraction"]),
    ):
        expected = float(checks[name]["expected"])
        tol = float(checks[name]["tolerance"])
        rows.append(
            {
                "check": name,
                "expected": expected,
                "computed": computed,
                "tolerance": tol,
                "passed": bool(abs(computed - expected) <= tol),
            }
        )
    invariants = pd.DataFrame(rows)
    print(f"\n{'=' * 70}\nFROZEN INVARIANTS (anchor at the register onset)\n{'=' * 70}")
    print(invariants.to_string(index=False))
    if spec["invariants"].get("enforce", True) and not bool(invariants["passed"].all()):
        raise RuntimeError(
            "STOP: the anchor arithmetic did not reproduce from the frozen panel.\n"
            + invariants[~invariants["passed"]].to_string(index=False)
        )

    print(f"\nONSET SENSITIVITY (the B2 finding, not a nuisance)")
    for r in results:
        print(
            f"  {r['label']:<16} {r['onset']}  loss={r['emitter_loss_per_day']:6.2f}"
            f"  gain={r['receiver_gain_per_day']:6.2f}"
            f"  recovered={100 * r['recovered_fraction']:6.2f}%"
        )

    if args.dry_run:
        print("\n--dry-run: no files written.")
        return 0

    outputs = spec["outputs"]
    paths = {k: config.ROOT / v for k, v in outputs.items()}
    for path in paths.values():
        path.parent.mkdir(parents=True, exist_ok=True)

    control_rows = []
    for r in results:
        for family_name, fam in r["spatial"].items():
            control_rows.append(
                {
                    "onset_label": r["label"],
                    "onset": r["onset"],
                    "emitter_loss_per_day": r["emitter_loss_per_day"],
                    "receiver_gain_per_day": r["receiver_gain_per_day"],
                    "recovered_fraction": r["recovered_fraction"],
                    "family": family_name,
                    "anchor_standardised": fam["anchor_standardised"],
                    "rank_of_anchor": fam["rank_of_anchor"],
                    "family_size": fam["family_size"],
                    "max_statistic": fam["max_statistic"],
                    "max_statistic_unit": fam["max_statistic_unit"],
                    "percentile_within_family": fam["percentile_within_family"],
                    "inferential_p_value": "",
                }
            )
    pd.DataFrame(control_rows).to_csv(paths["positive_control"], index=False)

    null_rows = [rec for r in results for rec in r["_null_records"]]
    pd.DataFrame(null_rows).to_csv(paths["null_distribution"], index=False)

    manifest = {
        "schema": "redsea_cape_manifest/1",
        "phase": "B2",
        "status": "frozen",
        "script": "scripts/run_receiver_test.py",
        "command": " ".join([Path(sys.argv[0]).name, *sys.argv[1:]]),
        "run_utc": datetime.now(timezone.utc).isoformat(),
        "git": {
            "commit": _git("rev-parse", "HEAD"),
            "branch": _git("branch", "--show-current"),
            "dirty": bool(_git("status", "--porcelain")),
        },
        "config": {"path": str(SPEC_PATH.relative_to(config.ROOT)), "sha256": config_sha},
        "inputs": {
            "panel_registry_variable": panel_spec["registry_variable"],
            "measurement_state": panel_spec["measurement_state"],
            "value_column": panel_spec["value_column"],
            "disruption_source": spec["support"]["disruption_source"],
            "disruption_source_sha256": sha256_file(
                config.ROOT / spec["support"]["disruption_source"]
            ),
        },
        "anchor_pair": spec["anchor_pair"],
        "onsets_reported": [r["label"] for r in results],
        "primary_onset": None,
        "results": [{k: v for k, v in r.items() if k != "_null_records"} for r in results],
        "invariant_verification": {
            "all_passed": bool(invariants["passed"].all()),
            "checks": invariants.to_dict(orient="records"),
        },
        "design_assertions": {
            "temporal_null_enumerates_unique_dates_once": True,
            "temporal_null_uses_resampling_with_replacement": False,
            "spatial_families_reported_separately": True,
            "spatial_inferential_p_value_computed": False,
            "pairs_treated_as_independent": False,
            "hormuz_excluded": True,
            "b3_opened": False,
        },
        "environment": {
            "python": platform.python_version(),
            "pandas": pd.__version__,
            "numpy": np.__version__,
        },
        "limitations": spec["limitations"],
        "claims_not_authorised": spec["claim_boundaries"]["prohibited"],
        "outputs": {},
    }
    for key in ("positive_control", "null_distribution"):
        manifest["outputs"][key] = {
            "path": outputs[key],
            "sha256": sha256_file(paths[key]),
        }
    paths["manifest"].write_text(
        json.dumps(manifest, indent=2, default=_json_default) + "\n", encoding="utf-8"
    )

    print("\nOUTPUTS")
    for key in ("positive_control", "null_distribution"):
        print(f"  {outputs[key]:<52} sha256={manifest['outputs'][key]['sha256'][:16]}...")
    print(f"  {outputs['manifest']:<52} sha256={sha256_file(paths['manifest'])[:16]}...")
    print("\nB2 COMPLETE. Descriptive positive control; B3 is NOT opened.")
    print("STOP AND REPORT: paste this complete terminal output.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
