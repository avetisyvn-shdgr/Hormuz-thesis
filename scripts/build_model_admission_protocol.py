"""Validate and materialize the ex post PortWatch model-admission lock.

This script runs no forecast. It verifies the exact identities, support,
formulas, units, and information-set labels of every result disclosed as known
when the corrected lock was written.
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
from lngfreight.specification import working_specification  # noqa: E402


PROTOCOL_PATH = config.CONFIG_DIR / "model_admission_protocol.yaml"
RESULT_TOLERANCE = 1e-9
EXPECTED_PRIMARY_MODELS = {
    "seasonal_naive_7d", "ar_lag1_7", "chronos2", "bsts_local_level_weekly"
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_protocol(path: Path = PROTOCOL_PATH) -> tuple[dict, str]:
    raw = path.read_bytes()
    return yaml.safe_load(raw), hashlib.sha256(raw).hexdigest()


def _require_hash(relative: str, expected: str) -> Path:
    path = config.ROOT / relative
    if not path.is_file():
        raise FileNotFoundError(f"declared admission artifact missing: {relative}")
    actual = _sha256(path)
    if actual != expected:
        raise ValueError(
            f"admission artifact hash mismatch for {relative}: "
            f"expected {expected}, got {actual}"
        )
    return path


def _filter(frame: pd.DataFrame, filters: dict, *, source: str) -> pd.DataFrame:
    selected = frame
    for column, value in filters.items():
        if column not in selected.columns:
            raise ValueError(f"required filter column {column!r} absent from {source}")
        selected = selected.loc[selected[column].eq(value)]
    if selected.empty:
        raise ValueError(f"declared filters select no rows in {source}: {filters}")
    return selected.copy()


def _assert_columns(frame: pd.DataFrame, required: set[str], *, source: str) -> None:
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"required columns absent from {source}: {sorted(missing)}")


def _assert_scalar(actual: float, expected: float, *, label: str) -> None:
    if not np.isclose(actual, expected, rtol=0.0, atol=RESULT_TOLERANCE):
        raise ValueError(f"{label} mismatch: declared {expected}, artifact {actual}")


def _support_hash(dates: pd.Series, observed: pd.Series) -> str:
    payload = pd.DataFrame({
        "date": pd.to_datetime(dates).dt.strftime("%Y-%m-%d"),
        "y_true": pd.to_numeric(observed, errors="raise"),
    }).to_csv(index=False, float_format="%.17g")
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _verify_daily_common_point(protocol: dict, declaration: dict) -> dict:
    source = declaration["source"]
    path = _require_hash(source, declaration["source_sha256"])
    frame = _filter(pd.read_csv(path), declaration["filters"], source=source)
    required = {"date", "y_true", "y_pred", *declaration["filters"].keys()}
    _assert_columns(frame, required, source=source)
    scope = protocol["scope"]
    frame["date"] = pd.to_datetime(frame["date"], errors="raise")
    frame = frame.sort_values("date")
    expected_dates = pd.date_range(
        scope["locked_cutoff"], scope["scoring_end"], freq="D"
    )
    if len(frame) != int(scope["expected_scored_days"]):
        raise ValueError(f"{declaration['result_id']} does not contain 130 rows")
    if frame["date"].duplicated().any():
        raise ValueError(f"{declaration['result_id']} contains duplicate dates")
    if not pd.DatetimeIndex(frame["date"]).equals(expected_dates):
        raise ValueError(f"{declaration['result_id']} scoring dates drifted")
    y_true = pd.to_numeric(frame["y_true"], errors="raise").astype("float64")
    y_pred = pd.to_numeric(frame["y_pred"], errors="raise").astype("float64")
    if not np.isfinite(y_true).all() or not np.isfinite(y_pred).all():
        raise ValueError(f"{declaration['result_id']} contains nonfinite values")
    _assert_scalar(
        float(y_true.sum()),
        float(scope["expected_observed_sum_pinned"]),
        label=f"{declaration['result_id']} observed sum",
    )
    if declaration["target"] != scope["outcome"]:
        raise ValueError("daily comparison declaration targets the wrong outcome")
    if declaration["unit"] != scope["unit"]:
        raise ValueError("daily comparison declaration has the wrong unit")
    actual = float((y_pred - y_true).mean())
    _assert_scalar(
        actual,
        float(declaration["declared_value"]),
        label=declaration["result_id"],
    )
    return {
        **declaration,
        "artifact_value": actual,
        "verification_delta": actual - float(declaration["declared_value"]),
        "verified_start": expected_dates.min().date().isoformat(),
        "verified_end": expected_dates.max().date().isoformat(),
        "verified_n_days": len(frame),
        "verified_observed_sum": float(y_true.sum()),
        "observed_support_sha256": _support_hash(frame["date"], y_true),
        "verified_against_artifact": True,
    }


def _verify_bsts_joint(protocol: dict, declaration: dict) -> dict:
    source = declaration["source"]
    path = _require_hash(source, declaration["source_sha256"])
    frame = _filter(pd.read_csv(path), declaration["filters"], source=source)
    required = {
        "train_start", "train_end", "post_start", "post_end", "n_post_days",
        "posterior_median_shortfall", *declaration["filters"].keys(),
    }
    _assert_columns(frame, required, source=source)
    if len(frame) != 1:
        raise ValueError(f"{declaration['result_id']} must select exactly one row")
    row = frame.iloc[0]
    scope = protocol["scope"]
    expected = {
        "train_start": scope["analysis_start"],
        "train_end": scope["training_end"],
        "post_start": scope["locked_cutoff"],
        "post_end": scope["scoring_end"],
    }
    for field, value in expected.items():
        if str(row[field]) != value:
            raise ValueError(f"{declaration['result_id']} {field} drifted")
    n = int(row["n_post_days"])
    if n != int(scope["expected_scored_days"]):
        raise ValueError(f"{declaration['result_id']} day count drifted")
    if declaration["unit"] != scope["unit"]:
        raise ValueError("BSTS joint declaration has the wrong unit")
    actual = float(row["posterior_median_shortfall"]) / n
    _assert_scalar(actual, float(declaration["declared_value"]), label=declaration["result_id"])
    return {
        **declaration,
        "artifact_value": actual,
        "verification_delta": actual - float(declaration["declared_value"]),
        "verified_start": row["post_start"],
        "verified_end": row["post_end"],
        "verified_n_days": n,
        "verified_observed_sum": np.nan,
        "observed_support_sha256": "verified_in_paired_daily_bsts_row",
        "verified_against_artifact": True,
    }


def _verify_synthetic(protocol: dict, declaration: dict) -> dict:
    source = declaration["source"]
    path = _require_hash(source, declaration["source_sha256"])
    frame = _filter(pd.read_csv(path), declaration["filters"], source=source)
    required = {
        "post_start", "post_end", "n_post_days", "mean_daily_scaled_throughput_loss",
        *declaration["filters"].keys(),
    }
    _assert_columns(frame, required, source=source)
    if len(frame) != 1:
        raise ValueError("synthetic declaration must select one treated row")
    row = frame.iloc[0]
    scope = protocol["scope"]
    if (
        str(row["post_start"]) != scope["locked_cutoff"]
        or str(row["post_end"]) != scope["scoring_end"]
        or int(row["n_post_days"]) != int(scope["expected_scored_days"])
    ):
        raise ValueError("synthetic comparison support drifted")
    auxiliary = declaration["auxiliary_source"]
    scale_path = _require_hash(auxiliary, declaration["auxiliary_source_sha256"])
    scales = _filter(
        pd.read_csv(scale_path),
        {"slug": "strait_of_hormuz", "value_col": "n_tanker"},
        source=auxiliary,
    )
    if len(scales) != 1:
        raise ValueError("synthetic scale declaration must select one row")
    actual = float(row["mean_daily_scaled_throughput_loss"]) * float(
        scales.iloc[0]["pre_period_scale"]
    )
    if declaration["unit"] == scope["unit"] or declaration["comparable_same_information"]:
        raise ValueError("synthetic row must remain mechanically noncomparable")
    _assert_scalar(actual, float(declaration["declared_value"]), label=declaration["result_id"])
    return {
        **declaration,
        "artifact_value": actual,
        "verification_delta": actual - float(declaration["declared_value"]),
        "verified_start": row["post_start"],
        "verified_end": row["post_end"],
        "verified_n_days": int(row["n_post_days"]),
        "verified_observed_sum": np.nan,
        "observed_support_sha256": "not_direct_transit_forecast",
        "verified_against_artifact": True,
    }


def _verify_scenario_rows(protocol: dict) -> list[dict]:
    block = protocol["known_vintage_sensitivity_rows_at_lock"]
    source = block["source"]
    path = _require_hash(source, block["source_sha256"])
    frame = pd.read_csv(path)
    required = {
        "target", "scenario", "window_start", "window_end", "pre_days",
        "post_days", "mean_daily_throughput_loss",
    }
    _assert_columns(frame, required, source=source)
    if len(frame) != len(block["rows"]):
        raise ValueError("vintage-sensitivity artifact contains an unexpected row count")
    out = []
    for declaration in block["rows"]:
        selected = _filter(
            frame,
            {"target": declaration["target"], "scenario": declaration["scenario"]},
            source=source,
        )
        if len(selected) != 1:
            raise ValueError("vintage-sensitivity declaration must select one row")
        row = selected.iloc[0]
        if str(row["window_start"]) != protocol["scope"]["analysis_start"]:
            raise ValueError("vintage-sensitivity analysis start drifted")
        if str(row["window_end"]) != declaration["window_end"]:
            raise ValueError("vintage-sensitivity window end drifted")
        if int(row["post_days"]) != int(declaration["post_days"]):
            raise ValueError("vintage-sensitivity day count drifted")
        if int(row["pre_days"]) != 1519:
            raise ValueError("vintage-sensitivity training support drifted")
        expected_unit = (
            "transits_per_day"
            if declaration["target"] == "hormuz_tanker_transits"
            else "deadweight_capacity_per_day"
        )
        if declaration["unit"] != expected_unit:
            raise ValueError("vintage-sensitivity unit declaration drifted")
        actual = float(row["mean_daily_throughput_loss"])
        _assert_scalar(actual, float(declaration["declared_value"]), label="vintage sensitivity row")
        out.append({
            "result_id": f"known_ar_{declaration['target']}_{declaration['scenario']}",
            "model": "ar_lag1_7",
            "vintage": declaration["scenario"],
            "target": declaration["target"],
            "statistic_basis": "known_vintage_window_ar_result",
            "declared_value": declaration["declared_value"],
            "unit": declaration["unit"],
            "comparable_same_information": bool(
                declaration["target"] == protocol["scope"]["outcome"]
                and declaration["scenario"] == "vintage_same_window"
            ),
            "verification_kind": block["verification_kind"],
            "source": source,
            "source_sha256": block["source_sha256"],
            "artifact_value": actual,
            "verification_delta": actual - float(declaration["declared_value"]),
            "verified_start": protocol["scope"]["locked_cutoff"],
            "verified_end": declaration["window_end"],
            "verified_n_days": int(declaration["post_days"]),
            "verified_observed_sum": float(row.get("observed_sum", np.nan)),
            "observed_support_sha256": "scenario_summary_no_daily_vector",
            "verified_against_artifact": True,
        })
    return out


def _validate_foundation_evidence(protocol: dict) -> None:
    evidence = protocol["representative_selection"]["preperiod_evidence"]
    path = _require_hash(evidence["source"], evidence["source_sha256"])
    frame = pd.read_csv(path)
    selected = frame.loc[frame["target"].eq(evidence["target"])].set_index("model")
    for model in ("chronos2", "timesfm", "moirai"):
        if model not in selected.index or not bool(selected.loc[model, "admitted"]):
            raise ValueError(f"pre-period admission evidence missing {model}")
        _assert_scalar(
            float(selected.loc[model, "cand_mase_mean"]),
            float(evidence[f"{model}_mase"]),
            label=f"{model} pre-period MASE",
        )
        _assert_scalar(
            abs(float(selected.loc[model, "cand_coverage_error_mean"])),
            float(evidence[f"{model}_abs_coverage_error"]),
            label=f"{model} pre-period absolute coverage error",
        )
    if not (
        evidence["timesfm_mase"] < evidence["chronos2_mase"]
        and evidence["chronos2_abs_coverage_error"]
        < evidence["timesfm_abs_coverage_error"]
    ):
        raise ValueError("foundation-model rationale does not match validation evidence")


def validate_protocol(protocol: dict) -> None:
    if protocol.get("schema_version") != 2:
        raise ValueError("model-admission protocol must use schema_version 2")
    timing = protocol["design_timing"]
    if timing["preregistered"] or timing["results_blinded"]:
        raise ValueError("protocol must disclose its ex post, unblinded timing")
    scope = protocol["scope"]
    settings = config.settings()["study_window"]
    expected_scope = {
        "analysis_start": settings["full_start"],
        "locked_cutoff": settings["primary_treatment_cutoff"],
        "scoring_end": settings["full_end"],
    }
    for field, value in expected_scope.items():
        if scope[field] != value:
            raise ValueError(f"protocol {field} differs from settings.yaml")
    if pd.Timestamp(scope["training_end"]) != pd.Timestamp(scope["locked_cutoff"]) - pd.Timedelta(days=1):
        raise ValueError("training_end must immediately precede the locked cutoff")
    if len(pd.date_range(scope["locked_cutoff"], scope["scoring_end"], freq="D")) != int(scope["expected_scored_days"]):
        raise ValueError("protocol scoring support is not 130 calendar days")
    working = working_specification()
    if scope["outcome"] != working.primary_outcome or working.primary_estimator != "ar_lag1_7":
        raise ValueError("protocol differs from the locked working specification")

    models = pd.DataFrame(protocol["models"])
    if models["model"].duplicated().any():
        raise ValueError("protocol contains duplicate model declarations")
    sets = protocol["comparison_sets"]
    selected = set(models.loc[models["representative_matrix_selected"], "model"])
    if selected != EXPECTED_PRIMARY_MODELS:
        raise ValueError("representative comparison must contain the frozen four models")
    if selected != set(sets["representative_same_information_range_members"]):
        raise ValueError("selected models differ from the explicit comparison set")
    if not models.loc[models["representative_matrix_selected"], "same_information_contract"].all():
        raise ValueError("every selected model must obey the same-information contract")
    not_run = set(sets["additional_preperiod_admitted_not_matrix_run"])
    rows = models.set_index("model").loc[list(not_run)]
    if not rows["pre_treatment_admission_passed"].all() or rows["pinned_130_day_support_verified"].any():
        raise ValueError("TimesFM/Moirai status must distinguish admission from support")
    if sets["mixed_information_range_status"] != "not_computed_information_sets_differ":
        raise ValueError("mixed-information rows must not form a numeric range")
    _validate_foundation_evidence(protocol)


def _verify_known_result(protocol: dict, declaration: dict) -> dict:
    kind = declaration["verification_kind"]
    if kind == "daily_common_point":
        return _verify_daily_common_point(protocol, declaration)
    if kind == "bsts_joint_summary":
        return _verify_bsts_joint(protocol, declaration)
    if kind == "synthetic_mean_scaled":
        return _verify_synthetic(protocol, declaration)
    raise ValueError(f"unsupported known-result verification kind: {kind}")


def build_tables(protocol: dict, protocol_sha256: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    scope = protocol["scope"]
    common = {
        "protocol_id": protocol["protocol_id"],
        "protocol_sha256": protocol_sha256,
        "locked_utc": protocol["locked_utc"],
        "lock_stage": protocol["lock_stage"],
        "checkpoint_status": protocol["checkpoint_status"],
        "preregistered": protocol["design_timing"]["preregistered"],
        "results_blinded": protocol["design_timing"]["results_blinded"],
        "outcome": scope["outcome"],
        "unit": scope["unit"],
        "analysis_start": scope["analysis_start"],
        "training_end": scope["training_end"],
        "locked_cutoff": scope["locked_cutoff"],
        "scoring_end": scope["scoring_end"],
        "expected_scored_days": scope["expected_scored_days"],
        "primary_range_label": protocol["comparison_sets"]["primary_range_label"],
    }
    models = pd.DataFrame([{**common, **row} for row in protocol["models"]])

    known_rows = [
        _verify_known_result(protocol, declaration)
        for declaration in protocol["known_artifact_results_at_lock"]
    ]
    known_rows.extend(_verify_scenario_rows(protocol))
    normalized_rows = []
    for row in known_rows:
        normalized = dict(row)
        if "filters" in normalized:
            normalized["filters"] = json.dumps(
                normalized["filters"], sort_keys=True, separators=(",", ":")
            )
        normalized_rows.append({
            "protocol_id": protocol["protocol_id"],
            "protocol_sha256": protocol_sha256,
            "locked_utc": protocol["locked_utc"],
            **normalized,
        })
    known = pd.DataFrame(normalized_rows)
    daily_support = known.loc[
        known["verification_kind"].eq("daily_common_point"),
        "observed_support_sha256",
    ]
    if daily_support.nunique() != 1:
        raise ValueError("known daily comparison rows do not share one observed vector")
    return models, known


def main() -> None:
    protocol, digest = load_protocol()
    validate_protocol(protocol)
    models, known = build_tables(protocol, digest)
    model_path = config.path("model_admission_protocol_csv")
    known_path = config.path("model_admission_known_results_csv")
    models.to_csv(model_path, index=False)
    known.to_csv(known_path, index=False)
    selected = models.loc[models["representative_matrix_selected"], "model"].tolist()
    print(f"protocol sha256: {digest}")
    print(f"selected four-specification comparison set: {selected}")
    print(f"verified known artifact rows: {len(known)}")
    print("all-preperiod-admitted range: NOT ESTIMATED")
    print(f"wrote {model_path}")
    print(f"wrote {known_path}")


if __name__ == "__main__":
    main()
