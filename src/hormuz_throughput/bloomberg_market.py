"""Auditable weekly frames for provenance-limited LNG market assessments."""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from . import registry


FREIGHT_SERIES = {
    "fearnleys_lng_spot_east_suez": "east_spot",
    "fearnleys_lng_spot_west_suez": "west_spot",
    "fearnleys_lng_one_year_time_charter": "one_year_charter",
}
EXTREME_WEEKLY_CHANGE_THRESHOLD = 1.0


def friday_week_end(dates: pd.Series) -> pd.Series:
    """Map assessment dates to Friday week-end labels without filling weeks."""
    parsed = pd.to_datetime(dates, errors="raise")
    return parsed.dt.to_period("W-FRI").dt.end_time.dt.normalize()


def _longest_gap_days(dates: pd.Series) -> int | None:
    gaps = dates.dropna().sort_values().diff().dt.days.dropna()
    return int(gaps.max()) if len(gaps) else None


def _one_series_frame(
    logical_name: str,
    slug: str,
    frame: pd.DataFrame,
    spec: dict[str, Any],
    expected_weeks: pd.DatetimeIndex,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    data = frame.loc[:, ["date", "value"]].copy()
    data["date"] = pd.to_datetime(data["date"], errors="raise")
    if data["date"].duplicated().any():
        raise ValueError(f"{logical_name} contains duplicate native dates")
    data["week_end"] = friday_week_end(data["date"])
    if data["week_end"].duplicated().any():
        raise ValueError(f"{logical_name} maps multiple observations to one week")

    flags = {pd.Timestamp(date): flag for date, flag in spec.get("quality_flags", {}).items()}
    data["quality_flag"] = data["date"].map(flags).fillna("")
    data["analysis_value"] = data["value"].astype(float)
    zero_mask = data["quality_flag"].eq("unverified_zero_mask_in_analysis")
    data.loc[zero_mask, "analysis_value"] = np.nan

    aligned = pd.DataFrame({"week_end": expected_weeks}).merge(
        data, on="week_end", how="left", validate="one_to_one"
    )
    missing = aligned["date"].isna()
    aligned.loc[missing, "quality_flag"] = "missing_assessment"
    aligned = aligned.rename(
        columns={
            "date": f"{slug}_assessment_date",
            "value": f"{slug}_usd_per_day_raw",
            "analysis_value": f"{slug}_usd_per_day_analysis",
            "quality_flag": f"{slug}_quality_flag",
        }
    )

    nonzero_base = data["value"].shift(1).ne(0)
    pct_change = data["value"].pct_change(fill_method=None).where(nonzero_base)
    absolute_change = data["value"].diff().abs()
    quality = {
        "logical_name": logical_name,
        "displayed_series_name": spec["displayed_series_name"],
        "unit": spec["unit"],
        "currency": spec["currency"],
        "expected_sha256": spec["expected_sha256"],
        "expected_weeks": int(len(expected_weeks)),
        "observed_weeks": int(data["week_end"].isin(expected_weeks).sum()),
        "missing_weeks": int(missing.sum()),
        "null_raw_values": int(aligned[f"{slug}_usd_per_day_raw"].isna().sum()),
        "null_analysis_values": int(
            aligned[f"{slug}_usd_per_day_analysis"].isna().sum()
        ),
        "duplicate_native_dates": 0,
        "duplicate_week_ends": 0,
        "longest_calendar_gap_days": _longest_gap_days(data["date"]),
        "zero_raw_observations": int(data["value"].eq(0).sum()),
        "masked_zero_observations": int(zero_mask.sum()),
        "source_flagged_observations": int(data["quality_flag"].ne("").sum()),
        "extreme_weekly_change_threshold_fraction": EXTREME_WEEKLY_CHANGE_THRESHOLD,
        "extreme_weekly_change_count": int(
            pct_change.abs().ge(EXTREME_WEEKLY_CHANGE_THRESHOLD).sum()
        ),
        "maximum_absolute_weekly_change_usd_per_day": (
            float(absolute_change.max()) if absolute_change.notna().any() else None
        ),
        "maximum_absolute_weekly_pct_change_excluding_zero_base": (
            float(pct_change.abs().max()) if pct_change.notna().any() else None
        ),
        "earliest_native_date": data["date"].min().date().isoformat(),
        "latest_native_date": data["date"].max().date().isoformat(),
    }
    return aligned, quality


def build_weekly_freight_panel(
    series_frames: dict[str, pd.DataFrame],
    manifest: dict[str, Any],
    *,
    study_start: str,
    study_end: str,
    treatment_cutoff: str,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    """Align the three weekly assessments while preserving raw observations."""
    missing = set(FREIGHT_SERIES) - set(series_frames)
    if missing:
        raise ValueError(f"Missing freight series: {sorted(missing)}")
    expected_weeks = pd.date_range(study_start, study_end, freq="W-FRI")
    panel = pd.DataFrame({"week_end": expected_weeks})
    quality_rows: list[dict[str, Any]] = []
    for logical_name, slug in FREIGHT_SERIES.items():
        aligned, quality = _one_series_frame(
            logical_name,
            slug,
            series_frames[logical_name],
            manifest["series"][logical_name],
            expected_weeks,
        )
        panel = panel.merge(aligned, on="week_end", how="left", validate="one_to_one")
        quality_rows.append(quality)

    cutoff = pd.Timestamp(treatment_cutoff)
    first_post_week = pd.date_range(
        cutoff + pd.Timedelta(days=1), periods=1, freq="W-FRI"
    )[0]
    panel["post_treatment"] = panel["week_end"].ge(first_post_week)
    output_manifest = {
        "schema_version": 1,
        "authorized_vintage": manifest["governance"]["authorized_date"],
        "governance": manifest["governance"],
        "study_window": {
            "start": study_start,
            "end": study_end,
            "treatment_cutoff": treatment_cutoff,
            "first_expected_post_week": first_post_week.date().isoformat(),
        },
        "calendar": "Friday week-ending; native assessment dates retained",
        "missing_week_policy": "leave missing; never carry forward or interpolate",
        "zero_policy": "preserve raw; mask only manifest-flagged unverified zeros in analysis columns",
        "extreme_weekly_change_threshold_fraction": EXTREME_WEEKLY_CHANGE_THRESHOLD,
        "series": {
            name: {
                "slug": slug,
                "expected_sha256": manifest["series"][name]["expected_sha256"],
                "quality_flags": manifest["series"][name].get("quality_flags", {}),
            }
            for name, slug in FREIGHT_SERIES.items()
        },
        "claim_boundary": (
            "Secondary descriptive market evidence only; no ATT, causal freight "
            "effect, or identified mediation effect."
        ),
    }
    return panel, pd.DataFrame(quality_rows), output_manifest


def load_freight_series(start: str, end: str) -> dict[str, pd.DataFrame]:
    """Load every freight input through the provenance-aware registry."""
    return {
        name: registry.get_variable(name, start=start, end=end)
        for name in FREIGHT_SERIES
    }


ANALYSIS_COLUMNS = {
    "east_spot": "east_spot_usd_per_day_analysis",
    "west_spot": "west_spot_usd_per_day_analysis",
    "one_year_charter": "one_year_charter_usd_per_day_analysis",
}
CONTEXT_SERIES = {
    "ttf_gas": ("ttf_eur_per_mwh", "netherlands_ttf_day_ahead"),
    "vlsfo_singapore": (
        "vlsfo_singapore_usd_per_metric_tonne",
        "clearlynx_vlsfo_singapore",
    ),
}


def descriptive_freight_layer(
    panel: pd.DataFrame,
    *,
    first_post_week: str,
    balanced_weeks: int = 12,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Add declared descriptive transforms and return tidy pre/post summaries."""
    if balanced_weeks < 1:
        raise ValueError("balanced_weeks must be positive")
    data = panel.copy()
    data["week_end"] = pd.to_datetime(data["week_end"], errors="raise")
    first_post = pd.Timestamp(first_post_week)
    data["east_minus_west_spot_usd_per_day"] = (
        data[ANALYSIS_COLUMNS["east_spot"]]
        - data[ANALYSIS_COLUMNS["west_spot"]]
    )
    pre = data.loc[data["week_end"].lt(first_post)]
    post = data.loc[data["week_end"].ge(first_post)]
    pre_balanced = pre.tail(balanced_weeks)
    post_balanced = post.head(balanced_weeks)
    for slug, column in ANALYSIS_COLUMNS.items():
        base = pre_balanced[column].mean()
        if pd.isna(base) or base == 0:
            data[f"{slug}_pre12_index"] = np.nan
        else:
            data[f"{slug}_pre12_index"] = data[column] / base * 100.0

    series = {
        **ANALYSIS_COLUMNS,
        "east_minus_west_spot": "east_minus_west_spot_usd_per_day",
    }
    comparisons = {
        f"balanced_{balanced_weeks}_week": (pre_balanced, post_balanced),
        "full_pre_vs_available_post": (pre, post),
    }
    rows: list[dict[str, Any]] = []
    for comparison, (left, right) in comparisons.items():
        for name, column in series.items():
            left_values = left[column].dropna()
            right_values = right[column].dropna()
            left_mean = float(left_values.mean()) if len(left_values) else np.nan
            right_mean = float(right_values.mean()) if len(right_values) else np.nan
            absolute_change = right_mean - left_mean
            allow_percent = name != "east_minus_west_spot" and left_mean != 0
            rows.append(
                {
                    "series": name,
                    "comparison": comparison,
                    "unit": "USD/day",
                    "pre_observations": int(len(left_values)),
                    "post_observations": int(len(right_values)),
                    "pre_mean": left_mean,
                    "post_mean": right_mean,
                    "absolute_change": absolute_change,
                    "percent_change": (
                        absolute_change / left_mean * 100.0
                        if allow_percent
                        else np.nan
                    ),
                    "pre_median": (
                        float(left_values.median()) if len(left_values) else np.nan
                    ),
                    "post_median": (
                        float(right_values.median()) if len(right_values) else np.nan
                    ),
                    "last_pre_observation": (
                        float(left_values.iloc[-1]) if len(left_values) else np.nan
                    ),
                    "first_post_observation": (
                        float(right_values.iloc[0]) if len(right_values) else np.nan
                    ),
                    "causal_interpretation_permitted": False,
                }
            )
    return data, pd.DataFrame(rows)


def build_market_context_panel(
    series_frames: dict[str, pd.DataFrame],
    manifest: dict[str, Any],
    *,
    study_start: str,
    study_end: str,
    treatment_cutoff: str,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    """Build a native-frequency context frame with pre-event standardization."""
    missing = set(CONTEXT_SERIES) - set(series_frames)
    if missing:
        raise ValueError(f"Missing context series: {sorted(missing)}")
    expected_dates = pd.bdate_range(study_start, study_end)
    panel = pd.DataFrame({"date": expected_dates})
    quality_rows: list[dict[str, Any]] = []
    cutoff = pd.Timestamp(treatment_cutoff)
    for registry_name, (column, manifest_name) in CONTEXT_SERIES.items():
        frame = series_frames[registry_name].loc[:, ["date", "value"]].copy()
        frame["date"] = pd.to_datetime(frame["date"], errors="raise")
        if frame["date"].duplicated().any():
            raise ValueError(f"{registry_name} contains duplicate dates")
        frame = frame.rename(columns={"value": column})
        panel = panel.merge(frame, on="date", how="left", validate="one_to_one")
        pre_values = panel.loc[panel["date"].lt(cutoff), column].dropna()
        pre_mean = float(pre_values.mean())
        pre_std = float(pre_values.std(ddof=1))
        panel[f"{column}_pre_zscore"] = (
            (panel[column] - pre_mean) / pre_std if pre_std > 0 else np.nan
        )
        spec = manifest["series"][manifest_name]
        nonmissing = panel[column].notna()
        dates = panel.loc[nonmissing, "date"]
        quality_rows.append(
            {
                "logical_name": registry_name,
                "displayed_series_name": spec["displayed_series_name"],
                "unit": spec["unit"],
                "currency": spec["currency"],
                "expected_sha256": spec["expected_sha256"],
                "expected_business_days": int(len(expected_dates)),
                "observed_business_days": int(nonmissing.sum()),
                "missing_business_days": int((~nonmissing).sum()),
                "duplicate_dates": 0,
                "zero_observations": int(panel[column].eq(0).sum()),
                "longest_calendar_gap_days": _longest_gap_days(dates),
                "earliest_date": dates.min().date().isoformat(),
                "latest_date": dates.max().date().isoformat(),
                "pre_treatment_mean": pre_mean,
                "pre_treatment_standard_deviation": pre_std,
            }
        )
    panel["post_treatment"] = panel["date"].ge(cutoff)
    output_manifest = {
        "schema_version": 1,
        "governance": manifest["governance"],
        "study_window": {
            "start": study_start,
            "end": study_end,
            "treatment_cutoff": treatment_cutoff,
        },
        "frequency": "native business-day observations on a weekday calendar",
        "missing_policy": "leave missing; no carry-forward, interpolation, or backfill",
        "standardization": "z-score using observations strictly before the treatment cutoff",
        "model_role": "context only; excluded from headline freight counterfactuals",
        "claim_boundary": "potential common shock or mediator; no causal conditioning claim",
    }
    return panel, pd.DataFrame(quality_rows), output_manifest


def load_market_context(start: str, end: str) -> dict[str, pd.DataFrame]:
    """Load TTF and VLSFO through the provenance-aware registry."""
    return {
        name: registry.get_variable(name, start=start, end=end)
        for name in CONTEXT_SERIES
    }
