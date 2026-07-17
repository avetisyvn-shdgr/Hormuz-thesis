"""Descriptive LNG importer-origin network edge list.

Builds the first network-rewiring artifact from frozen by-origin snapshots:
one row per destination unit, source country, and month. This is an edge list
for mechanism/resilience analysis, not a causal estimator and not observed cargo
matching.
"""
from __future__ import annotations

import hashlib
import itertools
import json
import math
from pathlib import Path

import pandas as pd

from . import config
from .importer_coverage import _jsonstat_frame, verify_probe_manifest
from .importer_outcomes import COMTRADE_GULF_CODES, EUROSTAT_GULF_CODES
from .sources.importer_customs import (
    GULF_BY_UNIT,
    MEASURE_BY_UNIT,
    OMAN_BY_UNIT,
    SNAPSHOT_FILES,
    SOURCE_LABELS,
    load_by_origin,
)

TREATMENT_MONTH = "2026-03"

COMTRADE_OMAN_CODE = 512
EUROSTAT_OMAN_CODE = "OM"

NETWORK_COLUMNS = [
    "period",
    "destination_unit",
    "destination_unit_type",
    "origin_code",
    "origin_country",
    "origin_group",
    "is_gulf_origin",
    "is_oman_excluded_from_gulf",
    "hs",
    "edge_value",
    "unit_of_measure",
    "measurement_basis",
    "source",
    "source_file",
    "snapshot_sha256",
    "post_treatment",
    "admissibility_note",
]

MONTHLY_METRIC_COLUMNS = [
    "period",
    "destination_unit",
    "destination_unit_type",
    "unit_of_measure",
    "measurement_basis",
    "edge_total_value",
    "gulf_edge_value",
    "non_gulf_edge_value",
    "oman_excluded_value",
    "gulf_share",
    "non_gulf_share",
    "source_count",
    "source_hhi",
    "source_entropy",
    "source_entropy_normalized",
    "post_treatment",
    "admissibility_note",
]

REWIRING_SUMMARY_COLUMNS = [
    "destination_unit",
    "destination_unit_type",
    "unit_of_measure",
    "measurement_basis",
    "pre_months",
    "post_months",
    "pre_start",
    "pre_end",
    "post_start",
    "post_end",
    "pre_edge_total_mean",
    "post_edge_total_mean",
    "edge_total_pct_change",
    "pre_gulf_edge_mean",
    "post_gulf_edge_mean",
    "gulf_edge_pct_change",
    "pre_non_gulf_edge_mean",
    "post_non_gulf_edge_mean",
    "non_gulf_edge_pct_change",
    "pre_gulf_share_mean",
    "post_gulf_share_mean",
    "gulf_share_change_pp",
    "pre_source_count_mean",
    "post_source_count_mean",
    "source_count_change",
    "pre_source_hhi_mean",
    "post_source_hhi_mean",
    "source_hhi_change",
    "pre_source_entropy_mean",
    "post_source_entropy_mean",
    "source_entropy_change",
    "same_calendar_pre_months",
    "same_calendar_post_months",
    "same_calendar_edge_total_pct_change",
    "same_calendar_gulf_share_change_pp",
    "same_calendar_non_gulf_edge_pct_change",
    "same_calendar_source_hhi_change",
    "same_calendar_note",
    "coverage_note",
    "admissibility_note",
]

GRAPH_METRIC_COLUMNS = [
    "destination_unit",
    "destination_unit_type",
    "unit_of_measure",
    "measurement_basis",
    "pre_months",
    "post_months",
    "pre_start",
    "pre_end",
    "post_start",
    "post_end",
    "pre_origin_count",
    "post_origin_count",
    "retained_origin_count",
    "new_origin_count",
    "dropped_origin_count",
    "edge_turnover_rate",
    "jensen_shannon_divergence",
    "jensen_shannon_distance",
    "pre_top_origin",
    "post_top_origin",
    "pre_top_origin_share",
    "post_top_origin_share",
    "pre_gulf_share",
    "post_gulf_share",
    "gulf_share_change_pp",
    "pre_non_gulf_edge_mean",
    "post_non_gulf_edge_mean",
    "non_gulf_edge_change",
    "pre_gulf_edge_mean",
    "post_gulf_edge_mean",
    "gulf_edge_change",
    "non_gulf_offset_ratio",
    "coverage_note",
    "admissibility_note",
]

RESILIENCE_TYPOLOGY_COLUMNS = [
    "destination_unit",
    "destination_unit_type",
    "primary_typology",
    "caution_flags",
    "evidence_strength",
    "pre_months",
    "post_months",
    "pre_gulf_share",
    "post_gulf_share",
    "gulf_share_change_pp",
    "edge_total_pct_change",
    "seasonality_adjusted_edge_total_pct_change",
    "typology_total_change_basis",
    "non_gulf_edge_pct_change",
    "non_gulf_offset_ratio",
    "jensen_shannon_distance",
    "edge_turnover_rate",
    "rule_thresholds",
    "typology_reason",
    "coverage_note",
    "admissibility_note",
]

POST_MONTH_SENSITIVITY_COLUMNS = [
    "dropped_month",
    "destination_unit",
    "destination_unit_type",
    "unit_had_dropped_month",
    "headline_primary_typology",
    "dropped_primary_typology",
    "changed_under_drop",
    "any_primary_typology_change",
    "headline_evidence_strength",
    "dropped_evidence_strength",
    "pre_months",
    "post_months_after_drop",
    "pre_gulf_share",
    "post_gulf_share",
    "gulf_share_change_pp",
    "edge_total_pct_change",
    "seasonality_adjusted_edge_total_pct_change",
    "non_gulf_edge_pct_change",
    "non_gulf_offset_ratio",
    "jensen_shannon_distance",
    "edge_turnover_rate",
    "rule_thresholds",
    "coverage_note",
    "admissibility_note",
]

TYPOLOGY_THRESHOLD_SENSITIVITY_COLUMNS = [
    "grid_id",
    "high_exposure_pre_gulf_share_min",
    "high_offset_ratio_min",
    "constrained_total_pct_max",
    "stable_band_abs",
    "destination_unit",
    "destination_unit_type",
    "headline_primary_typology",
    "grid_primary_typology",
    "agrees_with_headline",
    "unit_grid_points",
    "unit_grid_agreement_count",
    "unit_grid_agreement_share",
    "evidence_strength",
    "caution_flags",
    "pre_months",
    "post_months",
    "pre_gulf_share",
    "post_gulf_share",
    "gulf_share_change_pp",
    "edge_total_pct_change",
    "seasonality_adjusted_edge_total_pct_change",
    "non_gulf_edge_pct_change",
    "non_gulf_offset_ratio",
    "jensen_shannon_distance",
    "edge_turnover_rate",
    "rule_thresholds",
    "coverage_note",
    "admissibility_note",
]

ANOMALY_MONTHLY_COLUMNS = [
    "period",
    "destination_unit",
    "destination_unit_type",
    "unit_of_measure",
    "measurement_basis",
    "portfolio_js_distance",
    "portfolio_js_zscore",
    "portfolio_js_robust_zscore",
    "pre_empirical_tail_p",
    "pre_empirical_percentile",
    "post_treatment",
    "pre_calibration_months",
    "coverage_note",
    "admissibility_note",
]

ANOMALY_SUMMARY_COLUMNS = [
    "destination_unit",
    "destination_unit_type",
    "unit_of_measure",
    "measurement_basis",
    "pre_calibration_months",
    "post_months",
    "pre_mean_js_distance",
    "pre_sd_js_distance",
    "pre_median_js_distance",
    "pre_mad_js_distance",
    "post_mean_js_distance",
    "post_max_js_distance",
    "post_mean_zscore",
    "post_max_zscore",
    "post_mean_robust_zscore",
    "post_max_robust_zscore",
    "post_min_empirical_tail_p",
    "post_max_empirical_percentile",
    "anomaly_flag",
    "coverage_note",
    "admissibility_note",
]

TYPOLOGY_THRESHOLDS = {
    "high_exposure_pre_gulf_share_min": 0.15,
    "high_offset_ratio_min": 0.8,
    "stable_total_abs_pct_max": 10.0,
    "stable_gulf_share_abs_pp_max": 10.0,
    "constrained_total_pct_max": -5.0,
    "constrained_offset_ratio_max": 0.5,
    "min_pre_months": 12,
    "min_post_months": 3,
}

TYPOLOGY_THRESHOLD_SENSITIVITY_GRID = {
    "high_exposure_pre_gulf_share_min": (0.10, 0.15, 0.20),
    "high_offset_ratio_min": (0.7, 0.8, 0.9),
    "constrained_total_pct_max": (-3.0, -5.0, -10.0),
    "stable_band_abs": (8.0, 10.0, 12.0),
}

TYPOLOGY_THRESHOLD_SENSITIVITY_GRID_SIZE = math.prod(
    len(values) for values in TYPOLOGY_THRESHOLD_SENSITIVITY_GRID.values()
)

ANOMALY_THRESHOLDS = {
    "min_pre_calibration_months": 12,
    "min_post_months": 3,
    "zscore_flag_min": 2.0,
    "empirical_percentile_flag_min": 0.9,
}

CUSTOMS_META: dict[str, dict[str, str]] = {
    "kr": {
        "destination_unit": "Korea",
        "destination_unit_type": "importer",
        "unit_of_measure": "t",
        "admissibility_note": "strict origin-split national customs; weight basis",
    },
    "tw": {
        "destination_unit": "Taiwan",
        "destination_unit_type": "importer",
        "unit_of_measure": "t",
        "admissibility_note": "strict origin-split national customs; weight basis",
    },
    "cn": {
        "destination_unit": "China",
        "destination_unit_type": "importer",
        "unit_of_measure": "t",
        "admissibility_note": "strict origin-split national customs; weight basis",
    },
    "in": {
        "destination_unit": "India",
        "destination_unit_type": "importer",
        "unit_of_measure": "kUSD",
        "admissibility_note": (
            "strict origin-split national customs; value basis because "
            "Tradestat HS-6 monthly quantity is unpopulated"
        ),
    },
    "jp": {
        "destination_unit": "Japan",
        "destination_unit_type": "importer",
        "unit_of_measure": "t",
        "admissibility_note": (
            "strict origin-split Japan Customs/e-Stat snapshot; weight basis"
        ),
    },
}


def _origin_group(is_gulf: bool, is_oman: bool) -> str:
    if is_oman:
        return "oman_excluded_from_gulf"
    return "gulf" if is_gulf else "non_gulf"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def customs_edges(unit_key: str, customs_dir: Path) -> pd.DataFrame:
    """Network edges for one national-customs snapshot."""
    frame = load_by_origin(unit_key, base_dir=customs_dir)
    measure = MEASURE_BY_UNIT[unit_key]
    meta = CUSTOMS_META[unit_key]
    path = customs_dir / SNAPSHOT_FILES[unit_key]
    source_file = path.relative_to(config.ROOT).as_posix()
    rows = []
    gulf = GULF_BY_UNIT[unit_key]
    oman = OMAN_BY_UNIT[unit_key]
    for record in frame.to_dict("records"):
        value = record[measure]
        if pd.isna(value) or float(value) <= 0:
            continue
        country = str(record["country"])
        is_gulf = country in gulf
        is_oman = country == oman
        rows.append({
            "period": record["period"],
            "destination_unit": meta["destination_unit"],
            "destination_unit_type": meta["destination_unit_type"],
            "origin_code": country,
            "origin_country": country,
            "origin_group": _origin_group(is_gulf, is_oman),
            "is_gulf_origin": is_gulf,
            "is_oman_excluded_from_gulf": is_oman,
            "hs": str(record["hs"]),
            "edge_value": float(value),
            "unit_of_measure": meta["unit_of_measure"],
            "measurement_basis": measure,
            "source": SOURCE_LABELS[unit_key],
            "source_file": source_file,
            "snapshot_sha256": _sha256(path),
            "post_treatment": str(record["period"]) >= TREATMENT_MONTH,
            "admissibility_note": meta["admissibility_note"],
        })
    return pd.DataFrame(rows, columns=NETWORK_COLUMNS)


def japan_edges(probe_dir: Path, snapshot_sha256: str) -> pd.DataFrame:
    """Japan HS 271111 by-partner import edges from UN Comtrade (kg)."""
    path = probe_dir / "comtrade_japan_lng271111_bypartner.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = []
    for record in payload["data"]:
        if record.get("flowCode") != "M":
            continue
        code = record.get("partnerCode")
        if code == 0:
            continue
        value = record.get("netWgt")
        if value is None or float(value) <= 0:
            continue
        period = str(record["period"])
        month = f"{period[:4]}-{period[4:]}"
        is_gulf = code in COMTRADE_GULF_CODES
        is_oman = code == COMTRADE_OMAN_CODE
        rows.append({
            "period": month,
            "destination_unit": "Japan",
            "destination_unit_type": "importer",
            "origin_code": str(code),
            "origin_country": record.get("partnerDesc") or str(code),
            "origin_group": _origin_group(is_gulf, is_oman),
            "is_gulf_origin": is_gulf,
            "is_oman_excluded_from_gulf": is_oman,
            "hs": "271111",
            "edge_value": float(value),
            "unit_of_measure": "kg",
            "measurement_basis": "net_weight_kg",
            "source": "UN Comtrade HS 271111",
            "source_file": path.relative_to(config.ROOT).as_posix(),
            "snapshot_sha256": snapshot_sha256,
            "post_treatment": month >= TREATMENT_MONTH,
            "admissibility_note": "strict origin-split Comtrade snapshot; weight basis",
        })
    return pd.DataFrame(rows, columns=NETWORK_COLUMNS)


def eu27_edges(path: Path, snapshot_sha256: str) -> pd.DataFrame:
    """EU27 by-partner import edges from Eurostat nrg_ti_gasm (MIO_M3)."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    frame = _jsonstat_frame(payload)
    rows = []
    for record in frame.to_dict("records"):
        partner = str(record["partner"])
        if partner == "TOTAL":
            continue
        value = record["value"]
        if pd.isna(value) or float(value) <= 0:
            continue
        is_gulf = partner in EUROSTAT_GULF_CODES
        is_oman = partner == EUROSTAT_OMAN_CODE
        rows.append({
            "period": str(record["time"]),
            "destination_unit": "EU27",
            "destination_unit_type": "aggregate_comparator",
            "origin_code": partner,
            "origin_country": partner,
            "origin_group": _origin_group(is_gulf, is_oman),
            "is_gulf_origin": is_gulf,
            "is_oman_excluded_from_gulf": is_oman,
            "hs": "G3200",
            "edge_value": float(value),
            "unit_of_measure": "MIO_M3",
            "measurement_basis": "volume_mio_m3",
            "source": "Eurostat nrg_ti_gasm",
            "source_file": path.relative_to(config.ROOT).as_posix(),
            "snapshot_sha256": snapshot_sha256,
            "post_treatment": str(record["time"]) >= TREATMENT_MONTH,
            "admissibility_note": (
                "origin-split Eurostat aggregate comparator; EU27 is not a "
                "single importer"
            ),
        })
    return pd.DataFrame(rows, columns=NETWORK_COLUMNS)


def build_rewiring_network(
    probe_dir: Path,
    customs_dir: Path,
    eurostat_path: Path | None = None,
) -> pd.DataFrame:
    """Assemble the frozen by-origin importer network edge list."""
    hashes = verify_probe_manifest(probe_dir)
    eu_path = eurostat_path or (
        probe_dir / "eurostat_nrg_ti_gasm_lng_eu27_by_partner.json"
    )
    eu_sha = (
        _sha256(eu_path)
        if eurostat_path is not None
        else hashes["eurostat_nrg_ti_gasm_lng_eu27_by_partner.json"]
    )
    frames = [eu27_edges(eu_path, eu_sha)]
    frames.extend(customs_edges(unit, customs_dir) for unit in CUSTOMS_META)
    network = pd.concat(frames, ignore_index=True)
    network = network.sort_values(
        ["destination_unit", "period", "origin_group", "origin_country"]
    ).reset_index(drop=True)
    return network[NETWORK_COLUMNS]


def _pct_change(pre: float, post: float) -> float:
    if pd.isna(pre) or pd.isna(post) or pre == 0:
        return float("nan")
    return (post / pre - 1.0) * 100.0


def _same_calendar_windows(
    group: pd.DataFrame,
    post_start: str,
) -> tuple[pd.DataFrame, pd.DataFrame, str]:
    """Available post months matched to the same calendar months one year prior."""
    post = group[group["period"] >= post_start].copy()
    if post.empty:
        return group.iloc[0:0].copy(), post, "no_post_months"
    post_months = sorted(post["period"].astype(str).unique())
    prior_months = [f"{int(month[:4]) - 1}{month[4:]}" for month in post_months]
    pre_same = group[group["period"].astype(str).isin(prior_months)].copy()
    note = "same_calendar_prior_year"
    if pre_same["period"].nunique() < len(post_months):
        note += "; incomplete_same_calendar_pre"
    if post["period"].nunique() < 3:
        note += "; thin_post_window"
    return pre_same, post, note


def _weighted_entropy(shares: pd.Series) -> float:
    positive = shares[shares > 0]
    if positive.empty:
        return float("nan")
    return float(-(positive * positive.map(math.log)).sum())


def _kl_divergence(left: pd.Series, right: pd.Series) -> float:
    mask = (left > 0) & (right > 0)
    if not mask.any():
        return 0.0
    return float((left[mask] * (left[mask] / right[mask]).map(math.log)).sum())


def _jensen_shannon_divergence(left: pd.Series, right: pd.Series) -> float:
    """Bounded divergence between two origin-share vectors."""
    midpoint = (left + right) / 2.0
    return 0.5 * _kl_divergence(left, midpoint) + 0.5 * _kl_divergence(
        right, midpoint
    )


def monthly_rewiring_metrics(network: pd.DataFrame) -> pd.DataFrame:
    """Collapse edge rows into monthly origin-portfolio metrics per unit."""
    rows: list[dict[str, object]] = []
    for (unit, period), group in network.groupby(["destination_unit", "period"]):
        total = float(group["edge_value"].sum())
        gulf = float(group.loc[group["is_gulf_origin"], "edge_value"].sum())
        oman = float(
            group.loc[group["is_oman_excluded_from_gulf"], "edge_value"].sum()
        )
        shares = group["edge_value"] / total if total else group["edge_value"] * 0
        entropy = _weighted_entropy(shares)
        source_count = int(group["origin_code"].nunique())
        rows.append({
            "period": period,
            "destination_unit": unit,
            "destination_unit_type": group["destination_unit_type"].iloc[0],
            "unit_of_measure": group["unit_of_measure"].iloc[0],
            "measurement_basis": group["measurement_basis"].iloc[0],
            "edge_total_value": total,
            "gulf_edge_value": gulf,
            "non_gulf_edge_value": total - gulf,
            "oman_excluded_value": oman,
            "gulf_share": gulf / total if total else float("nan"),
            "non_gulf_share": (total - gulf) / total if total else float("nan"),
            "source_count": source_count,
            "source_hhi": float((shares ** 2).sum()) if total else float("nan"),
            "source_entropy": entropy,
            "source_entropy_normalized": (
                entropy / math.log(source_count) if source_count > 1 else 0.0
            ),
            "post_treatment": period >= TREATMENT_MONTH,
            "admissibility_note": group["admissibility_note"].iloc[0],
        })
    frame = pd.DataFrame(rows, columns=MONTHLY_METRIC_COLUMNS)
    return frame.sort_values(["destination_unit", "period"]).reset_index(drop=True)


def rewiring_prepost_summary(
    monthly: pd.DataFrame,
    pre_start: str = "2025-03",
    pre_end: str = "2026-02",
    post_start: str = TREATMENT_MONTH,
) -> pd.DataFrame:
    """Compare pre-period and available post-period network metrics."""
    metric_cols = [
        "edge_total_value",
        "gulf_edge_value",
        "non_gulf_edge_value",
        "gulf_share",
        "source_count",
        "source_hhi",
        "source_entropy",
    ]
    rows: list[dict[str, object]] = []
    for unit, group in monthly.groupby("destination_unit"):
        pre = group[(group["period"] >= pre_start) & (group["period"] <= pre_end)]
        post = group[group["period"] >= post_start]
        row: dict[str, object] = {
            "destination_unit": unit,
            "destination_unit_type": group["destination_unit_type"].iloc[0],
            "unit_of_measure": group["unit_of_measure"].iloc[0],
            "measurement_basis": group["measurement_basis"].iloc[0],
            "pre_months": int(len(pre)),
            "post_months": int(len(post)),
            "pre_start": str(pre["period"].min()) if len(pre) else None,
            "pre_end": str(pre["period"].max()) if len(pre) else None,
            "post_start": str(post["period"].min()) if len(post) else None,
            "post_end": str(post["period"].max()) if len(post) else None,
            "admissibility_note": group["admissibility_note"].iloc[0],
        }
        means: dict[str, tuple[float, float]] = {}
        for col in metric_cols:
            pre_mean = float(pre[col].mean()) if len(pre) else float("nan")
            post_mean = float(post[col].mean()) if len(post) else float("nan")
            means[col] = (pre_mean, post_mean)
        row.update({
            "pre_edge_total_mean": means["edge_total_value"][0],
            "post_edge_total_mean": means["edge_total_value"][1],
            "edge_total_pct_change": _pct_change(*means["edge_total_value"]),
            "pre_gulf_edge_mean": means["gulf_edge_value"][0],
            "post_gulf_edge_mean": means["gulf_edge_value"][1],
            "gulf_edge_pct_change": _pct_change(*means["gulf_edge_value"]),
            "pre_non_gulf_edge_mean": means["non_gulf_edge_value"][0],
            "post_non_gulf_edge_mean": means["non_gulf_edge_value"][1],
            "non_gulf_edge_pct_change": _pct_change(*means["non_gulf_edge_value"]),
            "pre_gulf_share_mean": means["gulf_share"][0],
            "post_gulf_share_mean": means["gulf_share"][1],
            "gulf_share_change_pp": (
                (means["gulf_share"][1] - means["gulf_share"][0]) * 100.0
            ),
            "pre_source_count_mean": means["source_count"][0],
            "post_source_count_mean": means["source_count"][1],
            "source_count_change": means["source_count"][1] - means["source_count"][0],
            "pre_source_hhi_mean": means["source_hhi"][0],
            "post_source_hhi_mean": means["source_hhi"][1],
            "source_hhi_change": means["source_hhi"][1] - means["source_hhi"][0],
            "pre_source_entropy_mean": means["source_entropy"][0],
            "post_source_entropy_mean": means["source_entropy"][1],
            "source_entropy_change": (
                means["source_entropy"][1] - means["source_entropy"][0]
            ),
        })
        pre_same, post_same, same_note = _same_calendar_windows(group, post_start)
        same_edge_pre = (
            float(pre_same["edge_total_value"].mean()) if len(pre_same) else float("nan")
        )
        same_edge_post = (
            float(post_same["edge_total_value"].mean()) if len(post_same) else float("nan")
        )
        same_gulf_pre = (
            float(pre_same["gulf_share"].mean()) if len(pre_same) else float("nan")
        )
        same_gulf_post = (
            float(post_same["gulf_share"].mean()) if len(post_same) else float("nan")
        )
        same_non_gulf_pre = (
            float(pre_same["non_gulf_edge_value"].mean())
            if len(pre_same)
            else float("nan")
        )
        same_non_gulf_post = (
            float(post_same["non_gulf_edge_value"].mean())
            if len(post_same)
            else float("nan")
        )
        same_hhi_pre = (
            float(pre_same["source_hhi"].mean()) if len(pre_same) else float("nan")
        )
        same_hhi_post = (
            float(post_same["source_hhi"].mean()) if len(post_same) else float("nan")
        )
        row.update({
            "same_calendar_pre_months": int(pre_same["period"].nunique()),
            "same_calendar_post_months": int(post_same["period"].nunique()),
            "same_calendar_edge_total_pct_change": _pct_change(
                same_edge_pre, same_edge_post
            ),
            "same_calendar_gulf_share_change_pp": (
                (same_gulf_post - same_gulf_pre) * 100.0
            ),
            "same_calendar_non_gulf_edge_pct_change": _pct_change(
                same_non_gulf_pre, same_non_gulf_post
            ),
            "same_calendar_source_hhi_change": same_hhi_post - same_hhi_pre,
            "same_calendar_note": same_note,
        })
        if len(pre) < 12:
            coverage = "incomplete_pre_window"
        elif len(post) < 3:
            coverage = "thin_post_window"
        else:
            coverage = "descriptive_coverage_ok"
        if row["measurement_basis"] == "value_kusd":
            coverage += "; value_basis"
        if row["destination_unit_type"] == "aggregate_comparator":
            coverage += "; aggregate_comparator"
        row["coverage_note"] = coverage
        rows.append(row)
    return pd.DataFrame(rows, columns=REWIRING_SUMMARY_COLUMNS).sort_values(
        "destination_unit"
    ).reset_index(drop=True)


def _origin_period_matrix(network: pd.DataFrame) -> pd.DataFrame:
    grouped = (
        network.groupby(
            [
                "destination_unit",
                "period",
                "origin_code",
                "origin_country",
                "is_gulf_origin",
            ],
            as_index=False,
        )["edge_value"]
        .sum()
    )
    grouped["period_total"] = grouped.groupby(
        ["destination_unit", "period"]
    )["edge_value"].transform("sum")
    grouped["origin_share"] = grouped["edge_value"] / grouped["period_total"]
    return grouped


def _portfolio_vector(group: pd.DataFrame, all_origins: list[str]) -> pd.Series:
    if group.empty:
        return pd.Series(0.0, index=all_origins)
    shares = group.groupby("origin_code")["origin_share"].mean()
    shares = shares.reindex(all_origins, fill_value=0.0)
    total = shares.sum()
    if total > 0:
        shares = shares / total
    return shares


def _mean_edges_by_origin(group: pd.DataFrame, all_origins: list[str]) -> pd.Series:
    if group.empty:
        return pd.Series(0.0, index=all_origins)
    return group.groupby("origin_code")["edge_value"].mean().reindex(
        all_origins, fill_value=0.0
    )


def dynamic_network_graph_metrics(
    network: pd.DataFrame,
    pre_start: str = "2025-03",
    pre_end: str = "2026-02",
    post_start: str = TREATMENT_MONTH,
) -> pd.DataFrame:
    """Pre/post origin-portfolio movement metrics for each destination unit.

    The divergence and turnover metrics compare origin shares, not physical
    cargo matches. Offset ratios compare mean monthly edge magnitudes within a
    unit's own measurement basis.
    """
    matrix = _origin_period_matrix(network)
    rows: list[dict[str, object]] = []
    meta = network.sort_values(["destination_unit", "period"])

    for unit, unit_edges in meta.groupby("destination_unit"):
        unit_matrix = matrix[matrix["destination_unit"] == unit]
        pre = unit_matrix[
            (unit_matrix["period"] >= pre_start) & (unit_matrix["period"] <= pre_end)
        ]
        post = unit_matrix[unit_matrix["period"] >= post_start]
        pre_months = int(pre["period"].nunique())
        post_months = int(post["period"].nunique())
        all_origins = sorted(unit_matrix["origin_code"].unique())
        pre_share = _portfolio_vector(pre, all_origins)
        post_share = _portfolio_vector(post, all_origins)
        pre_edges = _mean_edges_by_origin(pre, all_origins)
        post_edges = _mean_edges_by_origin(post, all_origins)

        origin_country = (
            unit_matrix.drop_duplicates("origin_code")
            .set_index("origin_code")["origin_country"]
            .to_dict()
        )
        gulf_flags = (
            unit_matrix.drop_duplicates("origin_code")
            .set_index("origin_code")["is_gulf_origin"]
            .reindex(all_origins, fill_value=False)
            .astype(bool)
        )
        pre_support = set(pre_share[pre_share > 0].index)
        post_support = set(post_share[post_share > 0].index)
        retained = pre_support & post_support
        new = post_support - pre_support
        dropped = pre_support - post_support

        jsd = _jensen_shannon_divergence(pre_share, post_share)
        edge_turnover = 0.5 * float((post_share - pre_share).abs().sum())
        pre_gulf_share = float(pre_share[gulf_flags].sum())
        post_gulf_share = float(post_share[gulf_flags].sum())
        pre_gulf_edge = float(pre_edges[gulf_flags].sum())
        post_gulf_edge = float(post_edges[gulf_flags].sum())
        pre_non_gulf_edge = float(pre_edges[~gulf_flags].sum())
        post_non_gulf_edge = float(post_edges[~gulf_flags].sum())
        non_gulf_change = post_non_gulf_edge - pre_non_gulf_edge
        gulf_change = post_gulf_edge - pre_gulf_edge
        lost_gulf = max(0.0, -gulf_change)
        offset_ratio = non_gulf_change / lost_gulf if lost_gulf > 0 else float("nan")

        if pre_months < 12:
            coverage = "incomplete_pre_window"
        elif post_months < 3:
            coverage = "thin_post_window"
        else:
            coverage = "descriptive_coverage_ok"
        if unit_edges["measurement_basis"].iloc[0] == "value_kusd":
            coverage += "; value_basis"
        if unit_edges["destination_unit_type"].iloc[0] == "aggregate_comparator":
            coverage += "; aggregate_comparator"

        pre_top = pre_share.idxmax() if pre_share.sum() > 0 else None
        post_top = post_share.idxmax() if post_share.sum() > 0 else None
        rows.append({
            "destination_unit": unit,
            "destination_unit_type": unit_edges["destination_unit_type"].iloc[0],
            "unit_of_measure": unit_edges["unit_of_measure"].iloc[0],
            "measurement_basis": unit_edges["measurement_basis"].iloc[0],
            "pre_months": pre_months,
            "post_months": post_months,
            "pre_start": str(pre["period"].min()) if len(pre) else None,
            "pre_end": str(pre["period"].max()) if len(pre) else None,
            "post_start": str(post["period"].min()) if len(post) else None,
            "post_end": str(post["period"].max()) if len(post) else None,
            "pre_origin_count": int(len(pre_support)),
            "post_origin_count": int(len(post_support)),
            "retained_origin_count": int(len(retained)),
            "new_origin_count": int(len(new)),
            "dropped_origin_count": int(len(dropped)),
            "edge_turnover_rate": edge_turnover,
            "jensen_shannon_divergence": jsd,
            "jensen_shannon_distance": math.sqrt(jsd),
            "pre_top_origin": origin_country.get(pre_top, pre_top),
            "post_top_origin": origin_country.get(post_top, post_top),
            "pre_top_origin_share": float(pre_share.max()) if pre_share.sum() > 0 else float("nan"),
            "post_top_origin_share": float(post_share.max()) if post_share.sum() > 0 else float("nan"),
            "pre_gulf_share": pre_gulf_share,
            "post_gulf_share": post_gulf_share,
            "gulf_share_change_pp": (post_gulf_share - pre_gulf_share) * 100.0,
            "pre_non_gulf_edge_mean": pre_non_gulf_edge,
            "post_non_gulf_edge_mean": post_non_gulf_edge,
            "non_gulf_edge_change": non_gulf_change,
            "pre_gulf_edge_mean": pre_gulf_edge,
            "post_gulf_edge_mean": post_gulf_edge,
            "gulf_edge_change": gulf_change,
            "non_gulf_offset_ratio": offset_ratio,
            "coverage_note": coverage,
            "admissibility_note": unit_edges["admissibility_note"].iloc[0],
        })

    return pd.DataFrame(rows, columns=GRAPH_METRIC_COLUMNS).sort_values(
        "destination_unit"
    ).reset_index(drop=True)


def _robust_zscore(value: float, median: float, mad: float) -> float:
    if pd.isna(value) or pd.isna(median) or pd.isna(mad) or mad == 0:
        return float("nan")
    return 0.67448975 * (value - median) / mad


def graph_anomaly_scores(
    network: pd.DataFrame,
    pre_start: str = "2025-03",
    pre_end: str = "2026-02",
    post_start: str = TREATMENT_MONTH,
    thresholds: dict[str, float] | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Score monthly origin portfolios against pre-shock network variation.

    This is an exploratory anomaly diagnostic. Distances compare monthly origin
    share vectors to the unit's average pre-period portfolio. Pre-period
    calibration distances use a leave-one-month-out centroid so the reference
    vector is not fit with the same month being scored. The score is not a
    causal effect and does not identify which replacement cargo displaced which
    Gulf cargo.
    """
    rules = {**ANOMALY_THRESHOLDS, **(thresholds or {})}
    matrix = _origin_period_matrix(network)
    monthly_rows: list[dict[str, object]] = []
    summary_rows: list[dict[str, object]] = []

    for unit, unit_matrix in matrix.groupby("destination_unit"):
        unit_edges = network[network["destination_unit"] == unit]
        all_origins = sorted(unit_matrix["origin_code"].unique())
        pre = unit_matrix[
            (unit_matrix["period"] >= pre_start) & (unit_matrix["period"] <= pre_end)
        ]
        centroid = _portfolio_vector(pre, all_origins)
        pre_months = int(pre["period"].nunique())
        pre_distances: list[float] = []
        period_distances: dict[str, float] = {}

        for period, period_group in unit_matrix.groupby("period"):
            vector = _portfolio_vector(period_group, all_origins)
            if pre_start <= str(period) <= pre_end and pre_months > 1:
                reference = _portfolio_vector(pre[pre["period"] != period], all_origins)
            else:
                reference = centroid
            distance = math.sqrt(_jensen_shannon_divergence(vector, reference))
            period_distances[str(period)] = distance
            if pre_start <= str(period) <= pre_end:
                pre_distances.append(distance)

        pre_series = pd.Series(pre_distances, dtype=float)
        pre_mean = float(pre_series.mean()) if len(pre_series) else float("nan")
        pre_sd = float(pre_series.std(ddof=1)) if len(pre_series) > 1 else float("nan")
        pre_median = float(pre_series.median()) if len(pre_series) else float("nan")
        pre_mad = (
            float((pre_series - pre_median).abs().median())
            if len(pre_series)
            else float("nan")
        )

        coverage = "descriptive_anomaly_ok"
        if pre_months < rules["min_pre_calibration_months"]:
            coverage = "thin_pre_calibration"
        post_months_available = sum(period >= post_start for period in period_distances)
        if post_months_available < rules["min_post_months"]:
            coverage += "; thin_post_window"
        if unit_edges["measurement_basis"].iloc[0] == "value_kusd":
            coverage += "; value_basis"
        if unit_edges["destination_unit_type"].iloc[0] == "aggregate_comparator":
            coverage += "; aggregate_comparator"

        for period, distance in sorted(period_distances.items()):
            if pd.notna(pre_sd) and pre_sd > 0:
                zscore = (distance - pre_mean) / pre_sd
            else:
                zscore = float("nan")
            robust_z = _robust_zscore(distance, pre_median, pre_mad)
            if len(pre_series):
                tail_p = float(((pre_series >= distance).sum() + 1) / (len(pre_series) + 1))
                percentile = float((pre_series <= distance).mean())
            else:
                tail_p = float("nan")
                percentile = float("nan")
            monthly_rows.append({
                "period": period,
                "destination_unit": unit,
                "destination_unit_type": unit_edges["destination_unit_type"].iloc[0],
                "unit_of_measure": unit_edges["unit_of_measure"].iloc[0],
                "measurement_basis": unit_edges["measurement_basis"].iloc[0],
                "portfolio_js_distance": distance,
                "portfolio_js_zscore": zscore,
                "portfolio_js_robust_zscore": robust_z,
                "pre_empirical_tail_p": tail_p,
                "pre_empirical_percentile": percentile,
                "post_treatment": period >= post_start,
                "pre_calibration_months": pre_months,
                "coverage_note": coverage,
                "admissibility_note": unit_edges["admissibility_note"].iloc[0],
            })

        post = [
            row for row in monthly_rows
            if row["destination_unit"] == unit and row["post_treatment"]
        ]
        post_frame = pd.DataFrame(post)
        post_months = int(len(post_frame))
        post_max_z = (
            float(post_frame["portfolio_js_zscore"].max())
            if post_months
            else float("nan")
        )
        post_max_pct = (
            float(post_frame["pre_empirical_percentile"].max())
            if post_months
            else float("nan")
        )
        anomaly_flag = (
            pd.notna(post_max_z)
            and post_max_z >= rules["zscore_flag_min"]
            and post_max_pct >= rules["empirical_percentile_flag_min"]
            and pre_months >= rules["min_pre_calibration_months"]
            and post_months >= rules["min_post_months"]
        )
        summary_rows.append({
            "destination_unit": unit,
            "destination_unit_type": unit_edges["destination_unit_type"].iloc[0],
            "unit_of_measure": unit_edges["unit_of_measure"].iloc[0],
            "measurement_basis": unit_edges["measurement_basis"].iloc[0],
            "pre_calibration_months": pre_months,
            "post_months": post_months,
            "pre_mean_js_distance": pre_mean,
            "pre_sd_js_distance": pre_sd,
            "pre_median_js_distance": pre_median,
            "pre_mad_js_distance": pre_mad,
            "post_mean_js_distance": (
                float(post_frame["portfolio_js_distance"].mean())
                if post_months
                else float("nan")
            ),
            "post_max_js_distance": (
                float(post_frame["portfolio_js_distance"].max())
                if post_months
                else float("nan")
            ),
            "post_mean_zscore": (
                float(post_frame["portfolio_js_zscore"].mean())
                if post_months
                else float("nan")
            ),
            "post_max_zscore": post_max_z,
            "post_mean_robust_zscore": (
                float(post_frame["portfolio_js_robust_zscore"].mean())
                if post_months
                else float("nan")
            ),
            "post_max_robust_zscore": (
                float(post_frame["portfolio_js_robust_zscore"].max())
                if post_months
                else float("nan")
            ),
            "post_min_empirical_tail_p": (
                float(post_frame["pre_empirical_tail_p"].min())
                if post_months
                else float("nan")
            ),
            "post_max_empirical_percentile": post_max_pct,
            "anomaly_flag": bool(anomaly_flag),
            "coverage_note": coverage,
            "admissibility_note": unit_edges["admissibility_note"].iloc[0],
        })

    monthly = pd.DataFrame(monthly_rows, columns=ANOMALY_MONTHLY_COLUMNS).sort_values(
        ["destination_unit", "period"]
    ).reset_index(drop=True)
    summary = pd.DataFrame(summary_rows, columns=ANOMALY_SUMMARY_COLUMNS).sort_values(
        "destination_unit"
    ).reset_index(drop=True)
    return monthly, summary


def _flag_text(flags: list[str]) -> str:
    return "; ".join(flags) if flags else "none"


def resilience_typology(
    summary: pd.DataFrame,
    graph_metrics: pd.DataFrame,
    thresholds: dict[str, float] | None = None,
) -> pd.DataFrame:
    """Rule-based descriptive resilience categories for importer units.

    The feature table is intentionally small, so the typology is thresholded and
    transparent rather than clustered. Categories summarize observed origin
    rewiring, not causal resilience or welfare.
    """
    rules = {**TYPOLOGY_THRESHOLDS, **(thresholds or {})}
    merged = summary.merge(
        graph_metrics[[
            "destination_unit",
            "non_gulf_offset_ratio",
            "jensen_shannon_distance",
            "edge_turnover_rate",
            "coverage_note",
        ]],
        on="destination_unit",
        how="left",
        suffixes=("", "_graph"),
    )
    rows: list[dict[str, object]] = []
    for row in merged.to_dict("records"):
        flags: list[str] = []
        if row["measurement_basis"] == "value_kusd":
            flags.append("value_basis_caution")
        if row["destination_unit_type"] == "aggregate_comparator":
            flags.append("aggregate_comparator")
        if int(row["pre_months"]) < rules["min_pre_months"]:
            flags.append("incomplete_pre_window")
        if int(row["post_months"]) < rules["min_post_months"]:
            flags.append("thin_post_window")

        high_exposure = (
            row["pre_gulf_share_mean"] >= rules["high_exposure_pre_gulf_share_min"]
        )
        high_offset = (
            pd.notna(row["non_gulf_offset_ratio"])
            and row["non_gulf_offset_ratio"] >= rules["high_offset_ratio_min"]
            and row["non_gulf_edge_pct_change"] >= 0
        )
        adjusted_total_change = row.get("same_calendar_edge_total_pct_change")
        if pd.isna(adjusted_total_change):
            adjusted_total_change = row["edge_total_pct_change"]
            total_change_basis = "available_post_vs_12m_pre"
        else:
            total_change_basis = "same_calendar_prior_year"
        constrained = (
            high_exposure
            and (
                adjusted_total_change <= rules["constrained_total_pct_max"]
                or (
                    pd.notna(row["non_gulf_offset_ratio"])
                    and row["non_gulf_offset_ratio"]
                    <= rules["constrained_offset_ratio_max"]
                )
                or row["non_gulf_edge_pct_change"] < 0
            )
        )
        low_stable = (
            not high_exposure
            and abs(adjusted_total_change) <= rules["stable_total_abs_pct_max"]
            and abs(row["gulf_share_change_pp"])
            <= rules["stable_gulf_share_abs_pp_max"]
        )

        if row["destination_unit_type"] == "aggregate_comparator":
            typology = "aggregate_comparator"
            strength = "context_only"
            reason = "EU27-style aggregate comparator is not treated as a single importer."
        elif (
            int(row["pre_months"]) < rules["min_pre_months"]
            or int(row["post_months"]) < rules["min_post_months"]
        ):
            typology = "not_estimable_coverage_limited"
            strength = "low"
            reason = "Insufficient balanced pre/post support for a stable typology."
        elif high_exposure and high_offset:
            typology = "high_exposure_high_offset"
            strength = "medium" if flags else "high"
            reason = (
                "Pre-shock Gulf share is high and non-Gulf growth offsets most "
                "lost Gulf edge value."
            )
        elif constrained:
            typology = "high_exposure_constrained"
            strength = "medium"
            reason = (
                "Pre-shock Gulf share is high, while total edge value falls or "
                "non-Gulf offset is weak."
            )
        elif low_stable:
            typology = "low_exposure_stable"
            strength = "medium"
            reason = "Pre-shock Gulf share is low and aggregate edge totals remain stable."
        else:
            typology = "intermediate_rewiring"
            strength = "low"
            reason = "Signals are mixed under the current transparent thresholds."

        rows.append({
            "destination_unit": row["destination_unit"],
            "destination_unit_type": row["destination_unit_type"],
            "primary_typology": typology,
            "caution_flags": _flag_text(flags),
            "evidence_strength": strength,
            "pre_months": int(row["pre_months"]),
            "post_months": int(row["post_months"]),
            "pre_gulf_share": row["pre_gulf_share_mean"],
            "post_gulf_share": row["post_gulf_share_mean"],
            "gulf_share_change_pp": row["gulf_share_change_pp"],
            "edge_total_pct_change": row["edge_total_pct_change"],
            "seasonality_adjusted_edge_total_pct_change": adjusted_total_change,
            "typology_total_change_basis": total_change_basis,
            "non_gulf_edge_pct_change": row["non_gulf_edge_pct_change"],
            "non_gulf_offset_ratio": row["non_gulf_offset_ratio"],
            "jensen_shannon_distance": row["jensen_shannon_distance"],
            "edge_turnover_rate": row["edge_turnover_rate"],
            "rule_thresholds": json.dumps(rules, sort_keys=True),
            "typology_reason": reason,
            "coverage_note": row["coverage_note"],
            "admissibility_note": row["admissibility_note"],
        })
    return pd.DataFrame(rows, columns=RESILIENCE_TYPOLOGY_COLUMNS).sort_values(
        "destination_unit"
    ).reset_index(drop=True)


def post_month_typology_sensitivity(
    network: pd.DataFrame,
    pre_start: str = "2025-03",
    pre_end: str = "2026-02",
    post_start: str = TREATMENT_MONTH,
) -> pd.DataFrame:
    """Leave-one-post-month sensitivity for the descriptive typology.

    For each available post-treatment month, the function drops that month from
    the network edge list, recomputes the pre/post summary, recomputes graph
    movement metrics, and then reruns the rule-based typology. The result is a
    long unit-by-dropped-month table. It is a coverage and classification
    stability diagnostic, not a new estimator.
    """
    network = network.copy()
    network["period"] = network["period"].astype(str)
    monthly = monthly_rewiring_metrics(network)
    post_months = sorted(
        monthly.loc[monthly["period"].astype(str) >= post_start, "period"]
        .astype(str)
        .unique()
    )
    if not post_months:
        return pd.DataFrame(columns=POST_MONTH_SENSITIVITY_COLUMNS)

    headline_summary = rewiring_prepost_summary(monthly, pre_start, pre_end, post_start)
    headline_graph = dynamic_network_graph_metrics(network, pre_start, pre_end, post_start)
    headline_typology = resilience_typology(headline_summary, headline_graph)
    headline = headline_typology.set_index("destination_unit")
    unit_months = set(
        monthly.loc[monthly["period"].astype(str) >= post_start, [
            "destination_unit",
            "period",
        ]]
        .astype({"period": str})
        .itertuples(index=False, name=None)
    )

    rows: list[dict[str, object]] = []
    for dropped_month in post_months:
        filtered = network[network["period"] != dropped_month].copy()
        dropped_monthly = monthly_rewiring_metrics(filtered)
        dropped_summary = rewiring_prepost_summary(
            dropped_monthly, pre_start, pre_end, post_start
        )
        dropped_graph = dynamic_network_graph_metrics(
            filtered, pre_start, pre_end, post_start
        )
        dropped_typology = resilience_typology(dropped_summary, dropped_graph)
        for row in dropped_typology.to_dict("records"):
            unit = row["destination_unit"]
            headline_row = headline.loc[unit]
            changed = row["primary_typology"] != headline_row["primary_typology"]
            rows.append({
                "dropped_month": dropped_month,
                "destination_unit": unit,
                "destination_unit_type": row["destination_unit_type"],
                "unit_had_dropped_month": (unit, dropped_month) in unit_months,
                "headline_primary_typology": headline_row["primary_typology"],
                "dropped_primary_typology": row["primary_typology"],
                "changed_under_drop": bool(changed),
                "any_primary_typology_change": False,
                "headline_evidence_strength": headline_row["evidence_strength"],
                "dropped_evidence_strength": row["evidence_strength"],
                "pre_months": int(row["pre_months"]),
                "post_months_after_drop": int(row["post_months"]),
                "pre_gulf_share": row["pre_gulf_share"],
                "post_gulf_share": row["post_gulf_share"],
                "gulf_share_change_pp": row["gulf_share_change_pp"],
                "edge_total_pct_change": row["edge_total_pct_change"],
                "seasonality_adjusted_edge_total_pct_change": row[
                    "seasonality_adjusted_edge_total_pct_change"
                ],
                "non_gulf_edge_pct_change": row["non_gulf_edge_pct_change"],
                "non_gulf_offset_ratio": row["non_gulf_offset_ratio"],
                "jensen_shannon_distance": row["jensen_shannon_distance"],
                "edge_turnover_rate": row["edge_turnover_rate"],
                "rule_thresholds": row["rule_thresholds"],
                "coverage_note": row["coverage_note"],
                "admissibility_note": row["admissibility_note"],
            })

    frame = pd.DataFrame(rows, columns=POST_MONTH_SENSITIVITY_COLUMNS)
    frame["any_primary_typology_change"] = frame.groupby("destination_unit")[
        "changed_under_drop"
    ].transform("any")
    return frame.sort_values(["destination_unit", "dropped_month"]).reset_index(
        drop=True
    )


def _iter_typology_threshold_grid() -> list[tuple[str, dict[str, float], float]]:
    rows: list[tuple[str, dict[str, float], float]] = []
    keys = list(TYPOLOGY_THRESHOLD_SENSITIVITY_GRID)
    values = [TYPOLOGY_THRESHOLD_SENSITIVITY_GRID[key] for key in keys]
    for index, combo in enumerate(itertools.product(*values), start=1):
        params = dict(zip(keys, combo))
        stable_band = float(params.pop("stable_band_abs"))
        thresholds = {
            **params,
            "stable_total_abs_pct_max": stable_band,
            "stable_gulf_share_abs_pp_max": stable_band,
        }
        rows.append((f"grid_{index:03d}", thresholds, stable_band))
    return rows


def typology_threshold_sensitivity(
    summary: pd.DataFrame,
    graph_metrics: pd.DataFrame,
) -> pd.DataFrame:
    """Typology sensitivity over the pre-declared threshold grid.

    The grid varies only the published typology thresholds declared in
    TYPOLOGY_THRESHOLD_SENSITIVITY_GRID. It repeats per-unit stability summaries
    on each row so the CSV remains a single long-format artifact.
    """
    headline_typology = resilience_typology(summary, graph_metrics)
    headline = headline_typology.set_index("destination_unit")
    rows: list[dict[str, object]] = []
    for grid_id, thresholds, stable_band in _iter_typology_threshold_grid():
        typology = resilience_typology(summary, graph_metrics, thresholds=thresholds)
        for row in typology.to_dict("records"):
            unit = row["destination_unit"]
            headline_label = headline.loc[unit, "primary_typology"]
            agrees = row["primary_typology"] == headline_label
            rows.append({
                "grid_id": grid_id,
                "high_exposure_pre_gulf_share_min": thresholds[
                    "high_exposure_pre_gulf_share_min"
                ],
                "high_offset_ratio_min": thresholds["high_offset_ratio_min"],
                "constrained_total_pct_max": thresholds[
                    "constrained_total_pct_max"
                ],
                "stable_band_abs": stable_band,
                "destination_unit": unit,
                "destination_unit_type": row["destination_unit_type"],
                "headline_primary_typology": headline_label,
                "grid_primary_typology": row["primary_typology"],
                "agrees_with_headline": bool(agrees),
                "unit_grid_points": 0,
                "unit_grid_agreement_count": 0,
                "unit_grid_agreement_share": float("nan"),
                "evidence_strength": row["evidence_strength"],
                "caution_flags": row["caution_flags"],
                "pre_months": int(row["pre_months"]),
                "post_months": int(row["post_months"]),
                "pre_gulf_share": row["pre_gulf_share"],
                "post_gulf_share": row["post_gulf_share"],
                "gulf_share_change_pp": row["gulf_share_change_pp"],
                "edge_total_pct_change": row["edge_total_pct_change"],
                "seasonality_adjusted_edge_total_pct_change": row[
                    "seasonality_adjusted_edge_total_pct_change"
                ],
                "non_gulf_edge_pct_change": row["non_gulf_edge_pct_change"],
                "non_gulf_offset_ratio": row["non_gulf_offset_ratio"],
                "jensen_shannon_distance": row["jensen_shannon_distance"],
                "edge_turnover_rate": row["edge_turnover_rate"],
                "rule_thresholds": row["rule_thresholds"],
                "coverage_note": row["coverage_note"],
                "admissibility_note": row["admissibility_note"],
            })

    frame = pd.DataFrame(rows, columns=TYPOLOGY_THRESHOLD_SENSITIVITY_COLUMNS)
    if frame.empty:
        return frame
    frame["unit_grid_points"] = frame.groupby("destination_unit")[
        "grid_id"
    ].transform("nunique").astype(int)
    frame["unit_grid_agreement_count"] = frame.groupby("destination_unit")[
        "agrees_with_headline"
    ].transform("sum").astype(int)
    frame["unit_grid_agreement_share"] = (
        frame["unit_grid_agreement_count"] / frame["unit_grid_points"]
    )
    return frame.sort_values(["destination_unit", "grid_id"]).reset_index(drop=True)
