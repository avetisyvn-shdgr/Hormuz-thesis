"""Build the descriptive PortWatch rebound/relapse phase profile.

The calendar windows are frozen in ``config/settings.yaml``. This script reads
both PortWatch snapshots through ``registry.get_variable()``, reports coverage
and right-censoring, and writes phase and contrast tables. It does not retrain a
counterfactual model or identify a causal effect of the dated context events.

Run from the repository root:
    .venv/bin/python scripts/run_rebound_relapse_profile.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lngfreight import config, registry  # noqa: E402


def extract_series(frame: pd.DataFrame, *, chokepoint: str, outcome: str) -> pd.Series:
    """Return one unique, chronological, numeric chokepoint series."""
    required = {"date", "portname", outcome}
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"PortWatch frame lacks required columns: {sorted(missing)}")
    work = frame.copy()
    work["date"] = pd.to_datetime(work["date"])
    selected = work.loc[work["portname"] == chokepoint, ["date", outcome]]
    if selected.empty:
        raise ValueError(f"no rows found for {chokepoint}")
    if selected["date"].duplicated().any():
        raise ValueError(f"duplicate dates found for {chokepoint}")
    values = pd.to_numeric(selected[outcome], errors="raise").astype("float64")
    series = pd.Series(values.to_numpy(), index=selected["date"], name=outcome)
    return series.sort_index()


def complete_slice(series: pd.Series, start: pd.Timestamp, end: pd.Timestamp) -> pd.Series:
    """Return a complete daily slice or fail on an internal gap."""
    expected = pd.date_range(start, end, freq="D")
    selected = series.reindex(expected)
    internal_missing = selected.index[
        selected.isna()
        & (selected.index >= series.index.min())
        & (selected.index <= series.index.max())
    ]
    if len(internal_missing):
        dates = ", ".join(ts.date().isoformat() for ts in internal_missing[:5])
        raise ValueError(f"internal missing daily observations: {dates}")
    return selected


def summarize_phases(
    series: pd.Series,
    *,
    vintage: str,
    source_variable: str,
    source_sha256: str,
    trusted_reporting_end: pd.Timestamp,
    endpoint_policy: str,
    settings: dict,
) -> pd.DataFrame:
    """Summarize fixed phases on each vintage's analysis-eligible support."""
    study = settings["study_window"]
    profile = study["rebound_relapse_profile"]
    pre_start = pd.Timestamp(study["full_start"])
    pre_end = pd.Timestamp(study["primary_treatment_cutoff"]) - pd.Timedelta(days=1)
    eligible_series = series.loc[series.index <= trusted_reporting_end]
    pre = complete_slice(eligible_series, pre_start, pre_end)
    if pre.isna().any():
        raise ValueError(f"{vintage} does not cover the configured analysis pre-period")
    analysis_pre_mean = float(pre.mean())

    rows: list[dict] = []
    for phase, spec in profile["windows"].items():
        start = pd.Timestamp(spec["start"])
        end = pd.Timestamp(spec["end"])
        selected = complete_slice(eligible_series, start, end)
        observed = selected.dropna()
        planned_days = int((end - start).days + 1)
        observed_days = int(len(observed))
        complete = observed_days == planned_days
        right_censored = bool(eligible_series.index.max() < end)
        buffer_excluded_days = int(
            series.loc[
                (series.index >= start)
                & (series.index <= end)
                & (series.index > trusted_reporting_end)
            ].notna().sum()
        )
        mean = float(observed.mean()) if observed_days else np.nan
        rows.append({
            "vintage": vintage,
            "source_variable": source_variable,
            "source_sha256": source_sha256,
            "source_date_min": series.index.min().date(),
            "source_date_max": series.index.max().date(),
            "trusted_reporting_end": trusted_reporting_end.date(),
            "endpoint_policy": endpoint_policy,
            "window_selection_status": profile["window_selection_status"],
            "phase": phase,
            "phase_role": spec["role"],
            "phase_start": start.date(),
            "phase_end": end.date(),
            "planned_calendar_days": planned_days,
            "observed_days": observed_days,
            "coverage_ratio": observed_days / planned_days,
            "complete_window": complete,
            "right_censored": right_censored,
            "window_extends_beyond_trusted_end": bool(end > trusted_reporting_end),
            "buffer_excluded_source_days": buffer_excluded_days,
            "transit_sum": float(observed.sum()) if observed_days else np.nan,
            "mean_daily_transits": mean,
            "median_daily_transits": (
                float(observed.median()) if observed_days else np.nan
            ),
            "nonzero_days": int((observed > 0).sum()),
            "zero_days": int((observed == 0).sum()),
            "analysis_pre_start": pre_start.date(),
            "analysis_pre_end": pre_end.date(),
            "analysis_pre_days": int(len(pre)),
            "analysis_pre_mean": analysis_pre_mean,
            "mean_as_share_of_analysis_pre": mean / analysis_pre_mean,
            "admissible_for_phase_contrast": complete,
        })
    return pd.DataFrame(rows)


def build_contrasts(profile: pd.DataFrame, settings: dict) -> pd.DataFrame:
    """Compute declared phase contrasts only when both windows are complete."""
    specs = settings["study_window"]["rebound_relapse_profile"]["contrasts"]
    rows: list[dict] = []
    for vintage, vintage_rows in profile.groupby("vintage", sort=False):
        by_phase = vintage_rows.set_index("phase")
        for contrast, spec in specs.items():
            reference = by_phase.loc[spec["reference_phase"]]
            comparison = by_phase.loc[spec["comparison_phase"]]
            admissible = bool(
                reference["complete_window"] and comparison["complete_window"]
            )
            reference_mean = float(reference["mean_daily_transits"])
            comparison_mean = float(comparison["mean_daily_transits"])
            difference = comparison_mean - reference_mean if admissible else np.nan
            ratio = (
                comparison_mean / reference_mean
                if admissible and reference_mean != 0
                else np.nan
            )
            rows.append({
                "vintage": vintage,
                "contrast": contrast,
                "contrast_role": spec["role"],
                "reference_phase": spec["reference_phase"],
                "comparison_phase": spec["comparison_phase"],
                "reference_complete": bool(reference["complete_window"]),
                "comparison_complete": bool(comparison["complete_window"]),
                "admissible_contrast": admissible,
                "status": (
                    "estimated_complete_windows"
                    if admissible
                    else "not_estimated_incomplete_window"
                ),
                "reference_mean_daily_transits": (
                    reference_mean if admissible else np.nan
                ),
                "comparison_mean_daily_transits": (
                    comparison_mean if admissible else np.nan
                ),
                "difference_mean_daily_transits": difference,
                "comparison_to_reference_ratio": ratio,
                "percent_change_from_reference": (
                    (ratio - 1.0) * 100.0 if np.isfinite(ratio) else np.nan
                ),
            })
    return pd.DataFrame(rows)


def main() -> None:
    settings = config.settings()
    phase_config = settings["study_window"]["rebound_relapse_profile"]
    frames = []
    for vintage, policy in phase_config["vintage_policies"].items():
        variable = policy["registry_variable"]
        artifact = registry.get_variable(
            variable,
            query={
                "consumer": "scripts/run_rebound_relapse_profile.py",
                "analysis_scope": "sensitivity_only",
            },
            allow_sensitivity=(
                variable
                == "portwatch_chokepoints_vintage_20260809_snapshot"
            ),
        )
        raw = artifact.read_csv(encoding="utf-8-sig", parse_dates=["date"])
        series = extract_series(
            raw,
            chokepoint=phase_config["chokepoint"],
            outcome=phase_config["outcome_column"],
        )
        frames.append(
            summarize_phases(
                series,
                vintage=vintage,
                source_variable=variable,
                source_sha256=artifact.sha256,
                trusted_reporting_end=pd.Timestamp(policy["trusted_reporting_end"]),
                endpoint_policy=policy["endpoint_policy"],
                settings=settings,
            )
        )

    profile = pd.concat(frames, ignore_index=True)
    contrasts = build_contrasts(profile, settings)
    profile_path = config.path("portwatch_regime_phase_profile_csv")
    contrast_path = config.path("portwatch_regime_contrasts_csv")
    profile.to_csv(profile_path, index=False)
    contrasts.to_csv(contrast_path, index=False)

    print("=== complete phase means (PortWatch n_tanker) ===")
    print(
        profile.loc[
            profile["complete_window"],
            [
                "vintage", "phase", "observed_days", "transit_sum",
                "mean_daily_transits", "nonzero_days",
                "mean_as_share_of_analysis_pre",
            ],
        ].to_string(index=False)
    )
    print("\n=== declared contrasts ===")
    print(
        contrasts[[
            "vintage", "contrast", "status",
            "difference_mean_daily_transits", "percent_change_from_reference",
        ]].to_string(index=False)
    )
    print("\n=== interpretation guard ===")
    print(" - These are descriptive calendar partitions, not causal event effects.")
    print(" - The pinned reporting support ends 2026-07-07. Its raw 07-08--07-12")
    print("   source-buffer days are excluded, so no pinned relapse contrast is fit.")
    print(" - Defensible claim: temporary partial rebound, then relapse; no sustained")
    print("   recovery through 2026-08-01. Do not write 'no rebound'.")
    print(f"\nwrote {profile_path}")
    print(f"wrote {contrast_path}")


if __name__ == "__main__":
    main()
