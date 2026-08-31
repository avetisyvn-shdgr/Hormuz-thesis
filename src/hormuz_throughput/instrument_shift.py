"""B1 - instrument revision audit between two PortWatch measurement states.

Two captures of the same historical period disagree. This module decomposes
that disagreement into a PROPORTIONAL component (a pure rescaling of the
historical series) and a NON-PROPORTIONAL, date-specific residual.

Why the split matters: a purely multiplicative revision cancels by
construction under within-series normalisation, so cross-state agreement of a
scale-invariant statistic is arithmetic, not empirical evidence. Only the
residual that survives the proportional mapping carries information about how
the historical measurement construct changed.

What this module does NOT do: it does not identify a revision mechanism, and
nothing here licenses the claim that the disruption caused the provider's
revision. See docs/HORMUZ_TECHNICAL_EXECUTION_PLAN.md v1.1, section 2.

The mapping estimator and its sample come from `config/hormuz_measurement_audit.yaml`
and are frozen before the fit. Functions here take the specification as an
argument; they never choose it.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from itertools import combinations
from pathlib import Path
import hashlib
import json

import numpy as np
import pandas as pd

MAPPING_FORMS = ("proportional", "affine", "additive")




@dataclass(frozen=True)
class MeasurementState:
    """One frozen PortWatch capture. States are never merged into each other."""

    label: str
    path: Path
    sha256: str
    frame: pd.DataFrame

    @property
    def n_rows(self) -> int:
        return len(self.frame)

    def coverage(self, date_column: str = "date") -> tuple[pd.Timestamp, pd.Timestamp]:
        col = self.frame[date_column]
        return col.min(), col.max()


def sha256_file(path: str | Path) -> str:
    """SHA-256 of a file's bytes."""
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def tidy_state(
    frame: pd.DataFrame,
    label: str,
    path: str | Path,
    sha256: str,
    date_column: str = "date",
    date_format: str = "%Y/%m/%d",
    unit_column: str = "portname",
) -> MeasurementState:
    """Parse dates and check the unit/date key is unique within one state."""
    out = frame.copy()
    out[date_column] = pd.to_datetime(out[date_column], format=date_format)
    if out.duplicated([unit_column, date_column]).any():
        dupes = int(out.duplicated([unit_column, date_column]).sum())
        raise ValueError(
            f"State {label!r} has {dupes} duplicate (unit, date) rows; "
            "the audit requires a unique daily key per chokepoint."
        )
    return MeasurementState(label=label, path=Path(path), sha256=sha256, frame=out)


def assert_states_separate(july: MeasurementState, august: MeasurementState) -> dict:
    """Prove the two states stayed distinct and were never averaged.

    Raises if the two states are byte-identical, share a label, or resolve to
    the same file. Returns the separation record written to the manifest.
    """
    if july.label == august.label:
        raise ValueError("Measurement states must carry distinct labels.")
    if july.path.resolve() == august.path.resolve():
        raise ValueError(
            "Both measurement states resolve to the same file; the July and "
            "August states must be separate inputs."
        )
    if july.sha256 == august.sha256:
        raise ValueError(
            "July and August states hash identically; there is no revision to "
            "audit and one state has been substituted for the other."
        )
    j_start, j_end = july.coverage()
    a_start, a_end = august.coverage()
    return {
        "states_separate": True,
        "never_averaged": True,
        "july": {
            "label": july.label,
            "path": str(july.path),
            "sha256": july.sha256,
            "n_rows": july.n_rows,
            "date_min": str(j_start.date()),
            "date_max": str(j_end.date()),
        },
        "august": {
            "label": august.label,
            "path": str(august.path),
            "sha256": august.sha256,
            "n_rows": august.n_rows,
            "date_min": str(a_start.date()),
            "date_max": str(a_end.date()),
        },
        "identical_content": False,
    }


def assert_not_averaged(frame: pd.DataFrame, july_col: str, august_col: str) -> None:
    """Guard against a state-averaged column reaching an output.

    Any column equal to the elementwise mean of the two state columns is a
    forbidden blend of measurement states (plan v1.1, section 2).
    """
    blend = (frame[july_col].to_numpy(float) + frame[august_col].to_numpy(float)) / 2.0
    if not np.any(frame[july_col].to_numpy(float) != frame[august_col].to_numpy(float)):
        return
    for name in frame.columns:
        if name in (july_col, august_col):
            continue
        column = frame[name]
        if not pd.api.types.is_numeric_dtype(column):
            continue
        values = column.to_numpy(dtype=float, na_value=np.nan)
        if values.shape != blend.shape or np.all(np.isnan(values)):
            continue
        if np.allclose(values, blend, rtol=0, atol=1e-12, equal_nan=True):
            raise ValueError(
                f"Column {name!r} equals the July/August average. Measurement "
                "states are never averaged."
            )




def overlap_panel(
    july: MeasurementState,
    august: MeasurementState,
    measures: list[str],
    unit_column: str = "portname",
    date_column: str = "date",
) -> pd.DataFrame:
    """Inner-join the two states on (unit, date), keeping both states labelled.

    Returns a long frame with one row per (unit, date, measure) and separate
    `july` and `august` columns. The states stay side by side; they are never
    stacked into a single value column or averaged.
    """
    missing_j = [m for m in measures if m not in july.frame.columns]
    missing_a = [m for m in measures if m not in august.frame.columns]
    if missing_j or missing_a:
        raise ValueError(
            f"Measures missing from july={missing_j} august={missing_a}."
        )
    keep = [unit_column, date_column, *measures]
    merged = july.frame[keep].merge(
        august.frame[keep],
        on=[unit_column, date_column],
        how="inner",
        suffixes=("__july", "__august"),
    )
    blocks = []
    for measure in measures:
        block = merged[[unit_column, date_column]].copy()
        block["measure"] = measure
        block["july"] = merged[f"{measure}__july"].astype(float)
        block["august"] = merged[f"{measure}__august"].astype(float)
        blocks.append(block)
    panel = pd.concat(blocks, ignore_index=True)
    return panel.sort_values(["measure", unit_column, date_column], ignore_index=True)


def _changed_mask(july: np.ndarray, august: np.ndarray) -> np.ndarray:
    """NaN-safe inequality: both-missing counts as unchanged."""
    both_nan = np.isnan(july) & np.isnan(august)
    differs = (july != august) & ~both_nan
    return differs


def changed_rows_by_unit(
    panel: pd.DataFrame, unit_column: str = "portname"
) -> pd.DataFrame:
    """Percent of overlapping rows revised, by chokepoint and measure."""
    rows = []
    for (measure, unit), part in panel.groupby(["measure", unit_column], sort=True):
        j = part["july"].to_numpy(float)
        a = part["august"].to_numpy(float)
        changed = _changed_mask(j, a)
        n = int(len(part))
        j_mean = float(np.nanmean(j)) if n else float("nan")
        a_mean = float(np.nanmean(a)) if n else float("nan")
        rows.append(
            {
                "measure": measure,
                unit_column: unit,
                "n_overlap_days": n,
                "n_changed_rows": int(changed.sum()),
                "pct_changed_rows": 100.0 * float(changed.mean()) if n else float("nan"),
                "mean_july": j_mean,
                "mean_august": a_mean,
                "mean_ratio_august_over_july": (
                    a_mean / j_mean if j_mean not in (0.0,) and np.isfinite(j_mean) else float("nan")
                ),
                "mean_difference_august_minus_july": a_mean - j_mean,
            }
        )
    out = pd.DataFrame(rows)
    return out.sort_values(
        ["measure", "pct_changed_rows", unit_column], ascending=[True, False, True]
    ).reset_index(drop=True)


def annual_summary(
    panel: pd.DataFrame,
    unit: str,
    measure: str,
    unit_column: str = "portname",
    date_column: str = "date",
) -> pd.DataFrame:
    """Per-year July/August means, ratio, and revision counts for one unit.

    Also carries the temporal distribution of revisions: how many of the
    revised rows fall in each year.
    """
    part = panel[(panel[unit_column] == unit) & (panel["measure"] == measure)].copy()
    if part.empty:
        raise ValueError(f"No overlapping rows for unit={unit!r} measure={measure!r}.")
    part["year"] = part[date_column].dt.year
    total_changed = int(_changed_mask(
        part["july"].to_numpy(float), part["august"].to_numpy(float)
    ).sum())
    rows = []
    for year, block in part.groupby("year", sort=True):
        j = block["july"].to_numpy(float)
        a = block["august"].to_numpy(float)
        changed = _changed_mask(j, a)
        j_mean, a_mean = float(np.nanmean(j)), float(np.nanmean(a))
        rows.append(
            {
                unit_column: unit,
                "measure": measure,
                "year": int(year),
                "n_days": int(len(block)),
                "n_changed_rows": int(changed.sum()),
                "pct_changed_rows": 100.0 * float(changed.mean()),
                "share_of_all_revisions_pct": (
                    100.0 * changed.sum() / total_changed if total_changed else 0.0
                ),
                "mean_july": j_mean,
                "mean_august": a_mean,
                "ratio_august_over_july": a_mean / j_mean if j_mean else float("nan"),
                "date_min": str(block[date_column].min().date()),
                "date_max": str(block[date_column].max().date()),
                "partial_year": bool(
                    len(block) < (366 if pd.Timestamp(int(year), 12, 31).dayofyear == 366 else 365)
                ),
            }
        )
    return pd.DataFrame(rows)




@dataclass(frozen=True)
class MappingFit:
    """A frozen July -> August mapping. The spec is an input, never a choice."""

    name: str
    form: str
    role: str
    intercept: float
    scale: float
    sample_start: str
    sample_end: str
    n_sample: int

    def apply(self, july: np.ndarray) -> np.ndarray:
        return self.intercept + self.scale * np.asarray(july, dtype=float)

    def to_dict(self) -> dict:
        return asdict(self)


def fit_mapping(
    july: np.ndarray,
    august: np.ndarray,
    form: str,
    name: str = "",
    role: str = "",
    sample_start: str = "",
    sample_end: str = "",
) -> MappingFit:
    """Least-squares July -> August mapping in one of the three declared forms.

    proportional : august = scale * july          (zero intercept)
    affine       : august = intercept + scale * july
    additive     : august = july + intercept      (unit scale)
    """
    if form not in MAPPING_FORMS:
        raise ValueError(f"form must be one of {MAPPING_FORMS}, got {form!r}.")
    x = np.asarray(july, dtype=float)
    y = np.asarray(august, dtype=float)
    if x.shape != y.shape:
        raise ValueError("July and August samples must have the same shape.")
    good = np.isfinite(x) & np.isfinite(y)
    x, y = x[good], y[good]
    if x.size == 0:
        raise ValueError(f"Mapping {name or form!r} has an empty estimation sample.")

    if form == "proportional":
        denom = float((x * x).sum())
        if denom == 0.0:
            raise ValueError(f"Mapping {name or form!r}: July sample is all zeros.")
        intercept, scale = 0.0, float((x * y).sum() / denom)
    elif form == "affine":
        design = np.column_stack([np.ones_like(x), x])
        coef, *_ = np.linalg.lstsq(design, y, rcond=None)
        intercept, scale = float(coef[0]), float(coef[1])
    else:
        intercept, scale = float(np.mean(y - x)), 1.0

    return MappingFit(
        name=name or form,
        form=form,
        role=role,
        intercept=intercept,
        scale=scale,
        sample_start=sample_start,
        sample_end=sample_end,
        n_sample=int(x.size),
    )


def fit_declared_mappings(
    series: pd.DataFrame,
    forms_spec: dict,
    date_column: str = "date",
) -> dict[str, MappingFit]:
    """Fit every mapping declared in the frozen config, on its declared sample.

    `series` must carry `date`, `july`, `august`. Samples are selected only by
    the configured dates, never by residual behaviour.
    """
    fits: dict[str, MappingFit] = {}
    for name, spec in forms_spec.items():
        start = pd.Timestamp(spec["sample_start"])
        end = pd.Timestamp(spec["sample_end"])
        window = series[
            (series[date_column] >= start) & (series[date_column] <= end)
        ]
        fits[name] = fit_mapping(
            window["july"].to_numpy(float),
            window["august"].to_numpy(float),
            form=spec["form"],
            name=name,
            role=spec.get("role", ""),
            sample_start=str(start.date()),
            sample_end=str(end.date()),
        )
    return fits




def residual_summary(residual: np.ndarray, quantiles: list[float]) -> dict:
    """Distribution summary for a residual vector."""
    r = np.asarray(residual, dtype=float)
    r = r[np.isfinite(r)]
    if r.size == 0:
        return {"n": 0}
    out = {
        "n": int(r.size),
        "mean": float(r.mean()),
        "sd": float(r.std(ddof=1)) if r.size > 1 else float("nan"),
        "rmse": float(np.sqrt(np.mean(r**2))),
        "mae": float(np.mean(np.abs(r))),
        "min": float(r.min()),
        "max": float(r.max()),
    }
    for q in quantiles:
        out[f"q{q:g}"] = float(np.quantile(r, q))
    return out


def squared_error_decomposition(
    july: np.ndarray, august: np.ndarray, fit: MappingFit
) -> dict:
    """How much of the revision survives the mapping.

    `raw` is the revision itself (august - july). `residual` is what remains
    after the frozen mapping. The fraction remaining is the share of squared
    revision error the mapping does NOT absorb; one minus that is the share
    attributable to proportional rescaling under this frozen estimator.

    A small remaining fraction means the revision is close to a pure
    rescaling. It does not mean the two states measure the same thing, and it
    carries no causal content.
    """
    x = np.asarray(july, dtype=float)
    y = np.asarray(august, dtype=float)
    good = np.isfinite(x) & np.isfinite(y)
    x, y = x[good], y[good]
    raw = y - x
    residual = y - fit.apply(x)
    sse_raw = float((raw**2).sum())
    sse_resid = float((residual**2).sum())
    fraction_remaining = sse_resid / sse_raw if sse_raw > 0 else float("nan")
    return {
        "n": int(x.size),
        "sse_raw_revision": sse_raw,
        "sse_after_mapping": sse_resid,
        "rmse_raw_revision": float(np.sqrt(np.mean(raw**2))) if x.size else float("nan"),
        "rmse_after_mapping": float(np.sqrt(np.mean(residual**2))) if x.size else float("nan"),
        "fraction_squared_error_remaining": fraction_remaining,
        "share_absorbed_by_mapping": (
            1.0 - fraction_remaining if np.isfinite(fraction_remaining) else float("nan")
        ),
    }


def split_residuals_by_onset(
    series: pd.DataFrame,
    fit: MappingFit,
    onset: str | pd.Timestamp,
    quantiles: list[float],
    date_column: str = "date",
) -> dict:
    """Pre-onset and post-onset residual behaviour, reported separately.

    The onset only partitions the report. It never selects an estimation
    sample, and a post-onset residual is not evidence of a treatment effect.
    """
    onset = pd.Timestamp(onset)
    x = series["july"].to_numpy(float)
    y = series["august"].to_numpy(float)
    residual = y - fit.apply(x)
    pre = (series[date_column] < onset).to_numpy()
    post = (series[date_column] >= onset).to_numpy()
    return {
        "onset": str(onset.date()),
        "pre_onset": residual_summary(residual[pre], quantiles),
        "post_onset": residual_summary(residual[post], quantiles),
        "full_overlap": residual_summary(residual, quantiles),
    }


def daily_revision_frame(
    series: pd.DataFrame,
    fits: dict[str, MappingFit],
    default_name: str,
    onset: str | pd.Timestamp,
    date_column: str = "date",
    measure: str = "n_tanker",
) -> pd.DataFrame:
    """Per-day revision record: both states, raw revision, mapped residuals.

    One residual column per declared mapping so a reader can see every
    sensitivity beside the default rather than only the reported one.
    """
    onset = pd.Timestamp(onset)
    july_col, august_col = f"{measure}_july", f"{measure}_august"
    out = series[[date_column, "july", "august"]].copy()
    out = out.rename(columns={"july": july_col, "august": august_col})
    x = out[july_col].to_numpy(float)
    y = out[august_col].to_numpy(float)
    out["revision_august_minus_july"] = y - x
    out["changed"] = _changed_mask(x, y)
    with np.errstate(divide="ignore", invalid="ignore"):
        out["ratio_august_over_july"] = np.where(x != 0, y / x, np.nan)
    for name, fit in fits.items():
        out[f"residual__{name}"] = y - fit.apply(x)
    out["default_mapping"] = default_name
    out["residual_default"] = out[f"residual__{default_name}"]
    out["period"] = np.where(out[date_column] < onset, "pre_onset", "post_onset")
    out["year"] = out[date_column].dt.year
    out["month"] = out[date_column].dt.to_period("M").astype(str)
    return out


def monthly_revision_distribution(
    daily: pd.DataFrame, date_column: str = "date"
) -> pd.DataFrame:
    """Temporal distribution of revisions at monthly granularity."""
    total = int(daily["changed"].sum())
    grouped = daily.groupby("month", sort=True).agg(
        n_days=("changed", "size"),
        n_changed=("changed", "sum"),
        mean_revision=("revision_august_minus_july", "mean"),
        mean_residual_default=("residual_default", "mean"),
    )
    grouped["pct_changed"] = 100.0 * grouped["n_changed"] / grouped["n_days"]
    grouped["share_of_all_revisions_pct"] = (
        100.0 * grouped["n_changed"] / total if total else 0.0
    )
    return grouped.reset_index()




def _read_wto_series(
    path: Path, date_aliases: list[str], value_aliases: list[str]
) -> pd.Series:
    frame = pd.read_csv(path)
    date_col = next((c for c in date_aliases if c in frame.columns), None)
    value_col = next((c for c in value_aliases if c in frame.columns), None)
    if date_col is None or value_col is None:
        raise ValueError(
            f"{path.name}: could not resolve date/value columns from "
            f"{list(frame.columns)} using aliases {date_aliases}/{value_aliases}."
        )
    series = pd.Series(
        frame[value_col].to_numpy(dtype=float),
        index=pd.to_datetime(frame[date_col]),
        name=path.name,
    )
    return series.sort_index()


def _pairwise_regime_matrix(
    series: dict[str, pd.Series], tolerance: float
) -> list[dict]:
    rows = []
    for left, right in combinations(sorted(series), 2):
        a, b = series[left], series[right]
        shared = a.index.intersection(b.index)
        if len(shared) == 0:
            rows.append(
                {
                    "file_a": left,
                    "file_b": right,
                    "n_overlap_dates": 0,
                    "n_differing_dates": 0,
                    "identical_on_overlap": None,
                }
            )
            continue
        diff = np.abs(a.loc[shared].to_numpy(float) - b.loc[shared].to_numpy(float))
        n_diff = int((diff > tolerance).sum())
        rows.append(
            {
                "file_a": left,
                "file_b": right,
                "n_overlap_dates": int(len(shared)),
                "n_differing_dates": n_diff,
                "identical_on_overlap": bool(n_diff == 0),
            }
        )
    return rows


def _assign_regimes(files: list[str], pairwise: list[dict]) -> dict[str, int]:
    """Strict clique grouping in deterministic filename order.

    Exact equality over unequal overlap windows is not transitive, so a file
    joins a regime only if it agrees with EVERY member of that regime. Nothing
    is merged through a chain of pairwise agreements.
    """
    identical = {
        (row["file_a"], row["file_b"]): row["identical_on_overlap"] for row in pairwise
    }

    def agrees(a: str, b: str) -> bool:
        return bool(identical.get((a, b), identical.get((b, a), False)))

    regimes: list[list[str]] = []
    for name in files:
        placed = False
        for regime in regimes:
            if all(agrees(name, member) for member in regime):
                regime.append(name)
                placed = True
                break
        if not placed:
            regimes.append([name])
    return {name: i + 1 for i, regime in enumerate(regimes) for name in regime}


def wto_state_audit(
    directory: str | Path,
    pattern: str,
    provenance_path: str | Path,
    provenance_variable: str,
    date_aliases: list[str],
    value_aliases: list[str],
    tolerance: float = 0.0,
) -> tuple[pd.DataFrame, list[dict]]:
    """File count, retrieval horizons, and distinct historical value regimes.

    Returns the per-file audit frame and the full pairwise comparison matrix.
    """
    directory = Path(directory)
    files = sorted(p for p in directory.glob(pattern) if p.is_file())
    if not files:
        raise ValueError(f"No WTO files matched {directory}/{pattern}.")

    retrievals: dict[str, list[dict]] = {}
    prov_path = Path(provenance_path)
    if prov_path.exists():
        for line in prov_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            record = json.loads(line)
            if record.get("variable") != provenance_variable:
                continue
            targets = [record.get("file")]
            for payload in record.get("source_payloads", []) or []:
                targets.append(payload.get("file"))
            for target in targets:
                if not target:
                    continue
                retrievals.setdefault(Path(target).name, []).append(record)

    series = {p.name: _read_wto_series(p, date_aliases, value_aliases) for p in files}
    pairwise = _pairwise_regime_matrix(series, tolerance)
    regimes = _assign_regimes([p.name for p in files], pairwise)

    rows = []
    for path in files:
        name = path.name
        s = series[name]
        records = retrievals.get(name, [])
        retrieved = sorted(r["retrieved_utc"] for r in records if r.get("retrieved_utc"))
        query_starts = sorted({r.get("query", {}).get("start") for r in records} - {None})
        query_ends = sorted({r.get("query", {}).get("end") for r in records} - {None})
        roles = sorted({r.get("artifact_role", "unspecified") for r in records})
        conflicts = sum(
            1
            for row in pairwise
            if name in (row["file_a"], row["file_b"])
            and row["identical_on_overlap"] is False
        )
        rows.append(
            {
                "file": name,
                "relative_path": str(path.as_posix()),
                "sha256": sha256_file(path),
                "n_rows": int(len(s)),
                "data_start": str(s.index.min().date()),
                "data_end": str(s.index.max().date()),
                "n_provenance_records": len(records),
                "retrieved_utc_first": retrieved[0] if retrieved else "",
                "retrieved_utc_last": retrieved[-1] if retrieved else "",
                "query_start": ";".join(query_starts),
                "query_end": ";".join(query_ends),
                "artifact_roles": ";".join(roles),
                "regime_id": regimes[name],
                "n_pairwise_conflicts": conflicts,
                "regime_rule": "exact_equality_on_overlap_strict_clique",
            }
        )
    audit = pd.DataFrame(rows).sort_values(["regime_id", "file"], ignore_index=True)
    return audit, pairwise




class InvariantMismatch(RuntimeError):
    """A frozen numerical invariant did not reproduce from the raw states."""


def verify_invariants(computed: dict, spec: dict) -> pd.DataFrame:
    """Compare freshly computed values against the frozen expectations.

    Every `computed` value arrives from the raw states. The expectations are
    verification targets only and never enter any output. A mismatch raises,
    stopping the phase (plan v1.1 section 12).
    """
    rows = []
    for key, check in spec["checks"].items():
        expected = check["expected"]
        tolerance = float(check["tolerance"])
        if isinstance(expected, dict):
            for sub_key, sub_expected in expected.items():
                actual = computed.get(key, {}).get(int(sub_key))
                rows.append(
                    _invariant_row(
                        f"{key}[{sub_key}]", sub_expected, actual, tolerance, check
                    )
                )
        else:
            rows.append(_invariant_row(key, expected, computed.get(key), tolerance, check))
        expected_unit = check.get("expected_unit")
        if expected_unit is not None:
            actual_unit = computed.get(f"{key}__unit")
            rows.append(
                {
                    "check": f"{key}__unit",
                    "expected": expected_unit,
                    "computed": actual_unit,
                    "tolerance": "",
                    "abs_error": "",
                    "passed": bool(actual_unit == expected_unit),
                    "description": check.get("description", ""),
                }
            )
    table = pd.DataFrame(rows)
    if spec.get("enforce", True) and not bool(table["passed"].all()):
        failed = table[~table["passed"]]
        raise InvariantMismatch(
            "Frozen invariants did not reproduce from the raw states. "
            "STOP: do not proceed with B1.\n" + failed.to_string(index=False)
        )
    return table


def _invariant_row(name, expected, actual, tolerance, check) -> dict:
    if actual is None or (isinstance(actual, float) and not np.isfinite(actual)):
        return {
            "check": name,
            "expected": expected,
            "computed": actual,
            "tolerance": tolerance,
            "abs_error": float("nan"),
            "passed": False,
            "description": check.get("description", ""),
        }
    error = abs(float(actual) - float(expected))
    return {
        "check": name,
        "expected": float(expected),
        "computed": float(actual),
        "tolerance": tolerance,
        "abs_error": error,
        "passed": bool(error <= tolerance),
        "description": check.get("description", ""),
    }
