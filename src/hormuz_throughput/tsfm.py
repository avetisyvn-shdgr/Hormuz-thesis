"""Isolated benchmark harness for modern time-series foundation models (TSFM).

This module wires Chronos-2, TimesFM 2.5 and Moirai 2.0 into the SAME
leakage-safe, strictly pre-treatment rolling-origin folds and the SAME scoring
used by the transparent baselines. Foundation models are evaluated using MASE,
RMSE, empirical interval coverage, and interval width rather than external
leaderboard performance.

Methodological constraints:
  * This is a BENCHMARK, never the locked primary estimator and never an enabled
    estimator. Nothing here is promoted into the counterfactual pipeline. A model
    enters the post-treatment comparison only after it materially beats the
    AR-only baseline on BOTH pre-treatment MASE and interval calibration.
  * Foundation models are zero-shot here: only each fold's pre-treatment TRAINING
    context is shown to the model; held-out and post-treatment values are used
    for scoring only. No post-treatment covariate can leak through.
  * The three real adapters require the heavy PyTorch stack, kept OUT of the
    frozen core requirements; it cannot run in this repo's Python 3.14 core venv.
    They were verified end-to-end on real weights on 2026-06-18 (macOS arm64,
    Python 3.11) and run in TWO isolated envs because the stacks conflict on
    torch: Chronos-2 + Moirai 2.0 share ``.venv-bench``
    (``requirements/benchmark.txt``), while TimesFM 2.5 needs a newer torch and
    runs alone in ``.venv-timesfm`` (``requirements/timesfm.txt``). Resolved
    versions must be pinned before results are reported.
  * The dependency-free ``StubAdapter`` exists ONLY to exercise and test the
    harness plumbing end-to-end on the real panel. Its numbers are a plumbing
    check, NOT a model result, and must never be reported as a foundation-model
    finding.

Interval levels are not silently mislabeled. The harness asks each adapter for a
central interval at a target mass (default 95%). Adapters that can only emit a
fixed quantile grid (TimesFM 2.5 emits deciles -> an 80% central interval, not
95%) report the level they actually produced via ``nominal_coverage``. The
calibration error (empirical coverage minus nominal coverage) is therefore
comparable across models even when their native nominal levels differ.
"""
from __future__ import annotations

import random
from dataclasses import dataclass

import numpy as np
import pandas as pd

from .metrics import score_forecast
from .validation import (
    Fold,
    require_chronological_index,
    resolve_cutoff,
    rolling_origin_splits,
)

DEFAULT_LOWER_Q = 0.025
DEFAULT_UPPER_Q = 0.975


def _calendar_preserving_context(train: pd.Series) -> pd.Series:
    """Prepare model context without compressing missing calendar steps.

    Datetime-indexed contexts are reindexed to a complete daily calendar and
    forward-filled using only prior observations. Leading gaps cannot be filled
    without future information and therefore fail loudly. Non-datetime contexts
    cannot establish calendar spacing, so they must already be finite.
    """
    context = pd.Series(train, dtype="float64")
    if len(context) == 0:
        return context
    if isinstance(context.index, pd.DatetimeIndex):
        index = require_chronological_index(
            context.index,
            name="TSFM training index",
        )
        if not index.is_unique:
            raise ValueError("TSFM training dates must be unique.")
        complete = pd.date_range(
            index.min(),
            index.max(),
            freq="D",
            name=index.name,
        )
        context = context.reindex(complete).ffill()
        if context.isna().any():
            raise ValueError(
                "TSFM training context has leading missing values that cannot "
                "be filled without future information."
            )
        return context
    if context.isna().any():
        raise ValueError(
            "Non-datetime TSFM training context contains missing values; "
            "calendar-preserving imputation is unavailable."
        )
    return context


def configure_deterministic_execution(seed: int) -> bool:
    """Seed optional TSFM runtimes and request deterministic Torch operations.

    Returns ``True`` when Torch is installed and configured. The core test
    environment intentionally omits Torch, so the deterministic stub path still
    seeds Python and NumPy and returns ``False`` without importing a heavy
    optional dependency.
    """
    seed = int(seed)
    random.seed(seed)
    np.random.seed(seed)
    try:
        import torch  # type: ignore
    except ImportError:
        return False

    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    torch.use_deterministic_algorithms(True, warn_only=True)
    if hasattr(torch.backends, "cudnn"):
        torch.backends.cudnn.benchmark = False
        torch.backends.cudnn.deterministic = True
    return True


@dataclass(frozen=True)
class QuantileForecast:
    """One adapter's forecast over a single horizon.

    ``point``/``lower``/``upper`` are aligned, same-length arrays. ``level_lower``
    and ``level_upper`` are the quantile levels the model ACTUALLY produced, and
    ``nominal_coverage = level_upper - level_lower`` is the central mass those
    bounds nominally represent (so calibration can be judged honestly even if a
    model cannot emit the requested 95% interval).
    """

    point: np.ndarray
    lower: np.ndarray
    upper: np.ndarray
    level_lower: float
    level_upper: float

    @property
    def nominal_coverage(self) -> float:
        return float(self.level_upper - self.level_lower)

    def __post_init__(self) -> None:
        n = len(self.point)
        if not (len(self.lower) == len(self.upper) == n):
            raise ValueError(
                "point, lower and upper must be equal length, got "
                f"{n}, {len(self.lower)}, {len(self.upper)}."
            )
        if not (0.0 <= self.level_lower < self.level_upper <= 1.0):
            raise ValueError(
                "require 0 <= level_lower < level_upper <= 1, got "
                f"{self.level_lower} and {self.level_upper}."
            )


class TSFMAdapter:
    """Common interface for a zero-shot foundation-model forecaster.

    Subclasses load weights once in ``__init__`` (loading can be expensive) and
    implement ``_predict`` to map a pre-treatment training context to a horizon
    of point + interval forecasts. They MUST NOT receive or look at any value at
    or after the forecast origin; the harness only ever passes the training
    context.
    """

    name = "base"
    native_quantiles: tuple[float, ...] | None = None

    def _resolve_levels(self, lower_q: float, upper_q: float) -> tuple[float, float]:
        """Clamp requested interval bounds to the model's native quantile grid.

        Returns the bounds unchanged when arbitrary quantiles are supported.
        Otherwise snaps to the nearest emitted quantiles so an 80% interval is
        never silently reported as 95% (calibration is judged on the level the
        model actually produced)."""
        if self.native_quantiles is None:
            return lower_q, upper_q
        lo = min(self.native_quantiles, key=lambda q: abs(q - lower_q))
        hi = min(self.native_quantiles, key=lambda q: abs(q - upper_q))
        return lo, hi

    def predict(
        self,
        train: pd.Series,
        horizon: int,
        lower_q: float = DEFAULT_LOWER_Q,
        upper_q: float = DEFAULT_UPPER_Q,
    ) -> QuantileForecast:
        if horizon <= 0:
            raise ValueError(f"horizon must be > 0, got {horizon}.")
        context = _calendar_preserving_context(train)
        if len(context) == 0:
            raise ValueError("training context is empty.")
        fc = self._predict(context, horizon, lower_q, upper_q)
        if len(fc.point) != horizon:
            raise ValueError(
                f"{self.name}: adapter returned {len(fc.point)} steps, "
                f"expected horizon {horizon}."
            )
        if not np.isfinite(fc.point).any():
            raise RuntimeError(
                f"{self.name}: forecast is entirely non-finite — the model likely "
                "ran in an incompatible environment. Check the torch version."
            )
        return fc

    def _predict(
        self, context: pd.Series, horizon: int, lower_q: float, upper_q: float
    ) -> QuantileForecast:
        raise NotImplementedError


class StubAdapter(TSFMAdapter):
    """Dependency-free deterministic forecaster for PLUMBING TESTS ONLY.

    Point forecast is a seasonal-naive carry-forward; the interval is a Gaussian
    band from the in-sample seasonal-difference residual scale. It produces
    proper arbitrary-quantile intervals so coverage/width logic can be exercised,
    but it is NOT a foundation model and its scores are never a thesis result.
    """

    name = "stub_seasonal"

    def __init__(self, season_length: int = 7) -> None:
        self.season_length = int(season_length)

    def _predict(
        self, context: pd.Series, horizon: int, lower_q: float, upper_q: float
    ) -> QuantileForecast:
        from math import erf, sqrt

        m = self.season_length
        vals = context.to_numpy(dtype="float64")
        last_season = vals[-m:] if len(vals) >= m else vals
        point = np.array(
            [last_season[i % len(last_season)] for i in range(horizon)],
            dtype="float64",
        )
        if len(vals) > m:
            scale = float(np.std(vals[m:] - vals[:-m]))
        else:
            scale = float(np.std(vals)) if len(vals) > 1 else 1.0
        if not np.isfinite(scale) or scale == 0:
            scale = 1.0

        def _z(q: float) -> float:
            lo, hi = -8.0, 8.0
            for _ in range(64):
                mid = 0.5 * (lo + hi)
                cdf = 0.5 * (1.0 + erf(mid / sqrt(2.0)))
                if cdf < q:
                    lo = mid
                else:
                    hi = mid
            return 0.5 * (lo + hi)

        lower = point + _z(lower_q) * scale
        upper = point + _z(upper_q) * scale
        return QuantileForecast(point, lower, upper, lower_q, upper_q)


class Chronos2Adapter(TSFMAdapter):
    """Chronos-2 (Amazon, 2025-10-20, ~120M params) via ``chronos-forecasting``.

    Univariate zero-shot only: future route/energy covariates observed after
    treatment could absorb the disruption and invalidate the counterfactual.
    Supports arbitrary quantile levels, so the requested 95% interval is native.

    Targets the ``Chronos2Pipeline`` / ``predict_df`` public API. Verify column
    names against the installed package version in the benchmark env.
    """

    name = "chronos2"

    def __init__(self, model_id: str = "amazon/chronos-2", device_map: str = "cpu") -> None:
        try:
            from chronos import Chronos2Pipeline  # type: ignore
        except ImportError as exc:  # pragma: no cover - heavy optional dep
            raise ImportError(
                "chronos-forecasting is not installed. Create the isolated "
                "benchmark env (.venv-bench, requirements/benchmark.txt, Python 3.11); do "
                "not add it to the frozen core requirements."
            ) from exc
        self.model_id = model_id
        self.pipeline = Chronos2Pipeline.from_pretrained(model_id, device_map=device_map)

    def _predict(
        self, context: pd.Series, horizon: int, lower_q: float, upper_q: float
    ) -> QuantileForecast:  # pragma: no cover - requires model weights
        idx = (
            context.index
            if isinstance(context.index, pd.DatetimeIndex)
            else pd.RangeIndex(len(context))
        )
        frame = pd.DataFrame(
            {"id": self.name, "timestamp": idx, "target": context.to_numpy()}
        )
        pred = self.pipeline.predict_df(
            frame,
            prediction_length=horizon,
            quantile_levels=[lower_q, 0.5, upper_q],
            id_column="id",
            timestamp_column="timestamp",
            target="target",
        ).sort_values("timestamp")
        point = _column(pred, ["predictions", "0.5", str(0.5)])
        lower = _column(pred, [str(lower_q)])
        upper = _column(pred, [str(upper_q)])
        return QuantileForecast(point, lower, upper, lower_q, upper_q)


class TimesFM25Adapter(TSFMAdapter):
    """TimesFM 2.5 (Google, 2025-09-15, ~200M params) via ``timesfm``.

    Its continuous quantile head emits a FIXED decile grid (0.1..0.9), so the
    widest native central interval is 80% (0.1/0.9), not 95%. The adapter clamps
    the requested bounds to the nearest available deciles and reports the level
    it actually produced through ``QuantileForecast.level_*`` so the harness does
    not mislabel an 80% interval as 95%.

    Targets the ``TimesFM_2p5_200M_torch`` + ``ForecastConfig`` + ``forecast``
    API. Verify the quantile ordering against the installed version.
    """

    name = "timesfm"
    native_quantiles = (0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9)

    def __init__(self, max_context: int = 2048, max_horizon: int = 64) -> None:
        try:
            import timesfm  # type: ignore
        except ImportError as exc:  # pragma: no cover - heavy optional dep
            raise ImportError(
                "timesfm is not installed. TimesFM 2.5 needs torch >= 2.5 and is "
                "incompatible with the torch pin uni2ts/Moirai forces, so it runs "
                "in its OWN env (.venv-timesfm; see requirements/timesfm.txt)."
            ) from exc
        self._timesfm = timesfm
        cls = timesfm.TimesFM_2p5_200M_torch
        self.model = cls.from_pretrained(cls.DEFAULT_REPO_ID)
        self.model.compile(
            timesfm.ForecastConfig(
                max_context=max_context,
                max_horizon=max_horizon,
                normalize_inputs=True,
                use_continuous_quantile_head=True,
                force_flip_invariance=True,
                infer_is_positive=True,
                fix_quantile_crossing=True,
            )
        )

    def _predict(
        self, context: pd.Series, horizon: int, lower_q: float, upper_q: float
    ) -> QuantileForecast:  # pragma: no cover - requires model weights
        lvl_lo, lvl_hi = self._resolve_levels(lower_q, upper_q)
        point_forecast, quantile_forecast = self.model.forecast(
            horizon=horizon, inputs=[context.to_numpy(dtype="float64")]
        )
        point = np.asarray(point_forecast[0], dtype="float64")[:horizon]
        q = np.asarray(quantile_forecast[0], dtype="float64")
        offset = q.shape[-1] - len(self.native_quantiles)
        if offset < 0:
            raise ValueError(
                f"{self.name}: quantile head has {q.shape[-1]} columns, fewer "
                f"than the {len(self.native_quantiles)} expected deciles."
            )
        lo_idx = offset + self.native_quantiles.index(lvl_lo)
        hi_idx = offset + self.native_quantiles.index(lvl_hi)
        lower = q[:horizon, lo_idx]
        upper = q[:horizon, hi_idx]
        return QuantileForecast(point, lower, upper, lvl_lo, lvl_hi)


class Moirai2Adapter(TSFMAdapter):
    """Moirai 2.0 R-small (Salesforce, 2025-08) via ``uni2ts`` + GluonTS.

    Verified against ``uni2ts`` 2.0.0: ``Moirai2Forecast`` emits a FIXED decile
    grid (``module.quantile_levels`` == 0.1..0.9) through a
    ``QuantileForecastGenerator`` — it is NOT the sample-based, arbitrary-quantile
    forecaster of Moirai 1.x, and the 2.0 constructor no longer takes
    ``patch_size``/``num_samples``. The adapter therefore reads the model's own
    quantile grid and snaps the requested interval to it (widest native central
    interval = 80%), reporting the level actually produced so an 80% interval is
    never mislabeled as 95%. Third independent cross-check; heaviest stack.
    """

    name = "moirai"

    def __init__(self, model_name: str = "Salesforce/moirai-2.0-R-small") -> None:
        try:
            from uni2ts.model.moirai2 import Moirai2Module  # type: ignore
        except ImportError as exc:  # pragma: no cover - heavy optional dep
            raise ImportError(
                "uni2ts is not installed. Create the isolated benchmark env "
                "(requirements/benchmark.txt, Python 3.11)."
            ) from exc
        self._module = Moirai2Module.from_pretrained(model_name)
        self.model_name = model_name
        levels = getattr(self._module, "quantile_levels", None)
        self.native_quantiles = tuple(float(q) for q in levels) if levels else None

    def _predict(
        self, context: pd.Series, horizon: int, lower_q: float, upper_q: float
    ) -> QuantileForecast:  # pragma: no cover - requires model weights
        from uni2ts.model.moirai2 import Moirai2Forecast  # type: ignore
        from gluonts.dataset.pandas import PandasDataset  # type: ignore

        lvl_lo, lvl_hi = self._resolve_levels(lower_q, upper_q)
        idx = (
            context.index
            if isinstance(context.index, pd.DatetimeIndex)
            else pd.date_range("2000-01-01", periods=len(context), freq="D")
        )
        frame = pd.DataFrame({"target": context.to_numpy()}, index=idx)
        ds = PandasDataset(frame, target="target")
        forecaster = Moirai2Forecast(
            module=self._module,
            prediction_length=horizon,
            context_length=len(context),
            target_dim=1,
            feat_dynamic_real_dim=0,
            past_feat_dynamic_real_dim=0,
        )
        predictor = forecaster.create_predictor(batch_size=1)
        forecast = next(iter(predictor.predict(ds)))
        point = np.asarray(forecast.quantile(0.5), dtype="float64")[:horizon]
        lower = np.asarray(forecast.quantile(lvl_lo), dtype="float64")[:horizon]
        upper = np.asarray(forecast.quantile(lvl_hi), dtype="float64")[:horizon]
        return QuantileForecast(point, lower, upper, lvl_lo, lvl_hi)


def _column(df: pd.DataFrame, candidates: list[str]) -> np.ndarray:
    """Return the first matching column as a float array, else fail loudly."""
    for c in candidates:
        if c in df.columns:
            return df[c].to_numpy(dtype="float64")
    raise KeyError(
        f"none of {candidates} found in prediction columns {list(df.columns)}; "
        "the installed package version may use different names — verify the adapter."
    )


MODEL_REGISTRY: dict[str, type[TSFMAdapter]] = {
    "stub": StubAdapter,
    "chronos2": Chronos2Adapter,
    "timesfm": TimesFM25Adapter,
    "moirai": Moirai2Adapter,
}
FOUNDATION_MODELS = ("chronos2", "timesfm", "moirai")


def run_benchmark(
    panel: pd.DataFrame,
    target: str,
    adapter: TSFMAdapter,
    folds: list[Fold] | None = None,
    lower_q: float = DEFAULT_LOWER_Q,
    upper_q: float = DEFAULT_UPPER_Q,
    season_length: int = 7,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Score one adapter over the leakage-safe rolling-origin folds.

    Only each fold's pre-treatment training context is shown to the model; the
    test window is used for scoring only. Returns ``(scores, forecasts)`` with
    one score row per fold (MASE, RMSE, sMAPE, MAE, empirical vs nominal interval
    coverage, and mean interval width) and one forecast row per test day.
    """
    if target not in panel.columns:
        raise KeyError(f"target {target!r} not found in panel columns.")
    if not isinstance(panel.index, pd.DatetimeIndex):
        raise TypeError("panel must be indexed by a DatetimeIndex.")

    folds = folds or rolling_origin_splits(panel.index)
    y = panel[target].astype("float64")

    score_rows = []
    forecast_rows = []
    for fold in folds:
        y_train = y.iloc[fold.train_idx]
        y_test = y.iloc[fold.test_idx]

        fc = adapter.predict(y_train, len(y_test), lower_q=lower_q, upper_q=upper_q)

        point = pd.Series(fc.point, index=y_test.index, name="y_pred")
        lower = pd.Series(fc.lower, index=y_test.index)
        upper = pd.Series(fc.upper, index=y_test.index)
        metrics = score_forecast(y_test, point, y_train, season_length=season_length)

        finite = (
            y_test.notna().to_numpy()
            & np.isfinite(fc.lower)
            & np.isfinite(fc.upper)
        )
        if finite.any():
            yt = y_test.to_numpy()[finite]
            inside = (yt >= fc.lower[finite]) & (yt <= fc.upper[finite])
            coverage = float(inside.mean())
            width = float(np.mean(fc.upper[finite] - fc.lower[finite]))
        else:
            coverage = float("nan")
            width = float("nan")

        score_rows.append({
            "model": adapter.name,
            "target": target,
            "fold": fold.name,
            "train_start": fold.train_start.date(),
            "train_end": fold.train_end.date(),
            "test_start": fold.test_start.date(),
            "test_end": fold.test_end.date(),
            "n_train": len(fold.train_idx),
            "n_test": len(fold.test_idx),
            "n_scored": int((y_test.notna() & point.notna()).sum()),
            "nominal_coverage": fc.nominal_coverage,
            "empirical_coverage": coverage,
            "coverage_error": coverage - fc.nominal_coverage,
            "interval_width": width,
            **metrics,
        })

        fold_forecasts = pd.DataFrame({
            "date": y_test.index,
            "model": adapter.name,
            "target": target,
            "fold": fold.name,
            "y_true": y_test.to_numpy(),
            "y_pred": point.to_numpy(),
            "lower": lower.to_numpy(),
            "upper": upper.to_numpy(),
        })
        fold_forecasts["error"] = fold_forecasts["y_true"] - fold_forecasts["y_pred"]
        forecast_rows.append(fold_forecasts)

    scores = pd.DataFrame(score_rows)
    forecasts = pd.concat(forecast_rows, ignore_index=True)
    return scores, forecasts


def counterfactual_shortfall(
    panel: pd.DataFrame,
    target: str,
    adapter: TSFMAdapter,
    cutoff: pd.Timestamp | str | None = None,
    lower_q: float = DEFAULT_LOWER_Q,
    upper_q: float = DEFAULT_UPPER_Q,
) -> tuple[pd.DataFrame, dict]:
    """Post-treatment counterfactual shortfall from an ADMITTED benchmark model.

    A robustness CROSS-CHECK only: it re-estimates the observed-minus-predicted
    shortfall with a foundation model in place of AR-only, to test whether the
    headline shortfall is sensitive to the forecaster. It does NOT promote the
    model into the locked pipeline and is NOT causal inference on its own.

    Discipline mirrors ``scripts/run_counterfactual.py``: the model trains on the
    full STRICTLY pre-cutoff history (univariate target only — no post-treatment
    covariate can leak in and absorb the disruption) and forecasts the whole
    post-treatment window. ``throughput_loss = counterfactual - observed``.

    Note on intervals: ``lower_cf``/``upper_cf`` are the model's POINTWISE daily
    band. They are intentionally NOT summed into a cumulative interval — summing
    pointwise quantiles ignores serial correlation and would misstate the
    cumulative band. The honest cumulative interval is the separate residual /
    placebo-horizon method (``scripts/run_long_horizon_intervals.py``).
    """
    if target not in panel.columns:
        raise KeyError(f"target {target!r} not found in panel columns.")
    if not isinstance(panel.index, pd.DatetimeIndex):
        raise TypeError("panel must be indexed by a DatetimeIndex.")

    cut = pd.Timestamp(cutoff) if cutoff is not None else resolve_cutoff()
    y = panel[target].astype("float64")
    train = y[y.index < cut]
    test_index = panel.index[panel.index >= cut]
    if len(train) == 0 or len(test_index) == 0:
        raise ValueError(
            f"counterfactual needs both pre- and post-cutoff rows at {cut.date()}; "
            f"have {len(train)} pre and {len(test_index)} post."
        )

    fc = adapter.predict(train, len(test_index), lower_q=lower_q, upper_q=upper_q)
    point = pd.Series(fc.point, index=test_index)
    y_true = y.loc[test_index]

    daily = pd.DataFrame({
        "date": test_index,
        "model": adapter.name,
        "target": target,
        "y_true": y_true.to_numpy(),
        "y_pred": point.to_numpy(),
        "lower_cf": fc.lower,
        "upper_cf": fc.upper,
    })
    daily["gap_observed_minus_predicted"] = daily["y_true"] - daily["y_pred"]
    daily["throughput_loss_vs_counterfactual"] = daily["y_pred"] - daily["y_true"]
    daily["cumulative_throughput_loss"] = (
        daily["throughput_loss_vs_counterfactual"].fillna(0).cumsum()
    )

    valid = daily.dropna(subset=["y_true", "y_pred"])
    summary = {
        "model": adapter.name,
        "target": target,
        "nominal_coverage": fc.nominal_coverage,
        "start": valid["date"].min().date() if len(valid) else None,
        "end": valid["date"].max().date() if len(valid) else None,
        "n_days": int(len(valid)),
        "observed_sum": float(valid["y_true"].sum()),
        "counterfactual_sum": float(valid["y_pred"].sum()),
        "cumulative_throughput_loss": float(
            valid["throughput_loss_vs_counterfactual"].sum()
        ),
        "mean_daily_throughput_loss": float(
            valid["throughput_loss_vs_counterfactual"].mean()
        ),
    }
    return daily, summary


def aggregate_benchmark(scores: pd.DataFrame) -> pd.DataFrame:
    """Summarize fold-level benchmark scores for the admission table."""
    metric_cols = [
        "mase", "rmse", "mae", "smape",
        "empirical_coverage", "nominal_coverage", "coverage_error",
        "interval_width",
    ]
    present = [c for c in metric_cols if c in scores.columns]
    out = (
        scores.groupby(["model", "target"], dropna=False)[present]
        .agg(["mean", "median"])
        .reset_index()
    )
    out.columns = [
        "_".join(str(part) for part in col if part)
        if isinstance(col, tuple) else str(col)
        for col in out.columns
    ]
    return out


def admission_test(
    tsfm_agg: pd.DataFrame,
    ar_agg: pd.DataFrame,
    ar_model: str = "ar_lag1_7",
    mase_margin: float = 0.0,
) -> pd.DataFrame:
    """Apply the documented admission test against the AR-only baseline.

    A candidate is admitted to the post-treatment comparison only if, per target,
    it BOTH lowers mean MASE versus AR-only (by at least ``mase_margin``) AND does
    not worsen interval calibration (absolute mean coverage error no larger than
    AR-only's). Calibration is compared on |coverage_error|, which stays
    meaningful even when models report different native nominal levels (e.g.
    TimesFM's 80% interval vs others' 95%).

    ``tsfm_agg`` and ``ar_agg`` are outputs of ``aggregate_benchmark`` /
    ``baselines.aggregate_scores`` style frames. ``ar_agg`` must contain MASE; if
    it lacks ``coverage_error_mean`` (the transparent baselines do not emit
    intervals), the calibration leg is reported as ``unavailable`` rather than
    silently passed.
    """
    ar = ar_agg[ar_agg["model"] == ar_model]
    if ar.empty:
        raise ValueError(
            f"AR baseline model {ar_model!r} not found in ar_agg; got "
            f"{sorted(ar_agg['model'].unique())}."
        )
    ar_by_target = ar.set_index("target")

    rows = []
    for _, r in tsfm_agg.iterrows():
        target = r["target"]
        if target not in ar_by_target.index:
            continue
        ar_mase = float(ar_by_target.at[target, "mase_mean"])
        cand_mase = float(r["mase_mean"])
        beats_mase = cand_mase <= ar_mase - mase_margin

        ar_has_cov = "coverage_error_mean" in ar_by_target.columns and pd.notna(
            ar_by_target.at[target, "coverage_error_mean"]
        )
        if ar_has_cov:
            ar_cov_err = abs(float(ar_by_target.at[target, "coverage_error_mean"]))
            cand_cov_err = abs(float(r["coverage_error_mean"]))
            keeps_calibration = cand_cov_err <= ar_cov_err
            calibration_assessed = True
            calib_note = f"|cand cov err|={cand_cov_err:.3f} vs AR {ar_cov_err:.3f}"
        else:
            keeps_calibration = False
            calibration_assessed = False
            calib_note = ("AR baseline carries no comparable interval; supply one "
                          "(raw, not conformal) to assess the calibration leg")

        admitted = bool(beats_mase and calibration_assessed and keeps_calibration)
        rows.append({
            "model": r["model"],
            "target": target,
            "cand_mase_mean": cand_mase,
            "ar_mase_mean": ar_mase,
            "mase_improvement": ar_mase - cand_mase,
            "beats_ar_mase": beats_mase,
            "cand_coverage_error_mean": float(r.get("coverage_error_mean", float("nan"))),
            "calibration_assessed": calibration_assessed,
            "keeps_calibration": keeps_calibration,
            "admitted": admitted,
            "verdict": _verdict(
                admitted, beats_mase, calibration_assessed, keeps_calibration, calib_note
            ),
        })
    return pd.DataFrame(rows)


def _verdict(
    admitted: bool,
    beats_mase: bool,
    calibration_assessed: bool,
    keeps_cal: bool,
    calib_note: str,
) -> str:
    if admitted:
        return ("ADMITTED: beats AR MASE and holds calibration — eligible for the "
                "post-treatment comparison.")
    if not beats_mase:
        return "rejected: does not beat AR-only MASE (expected for this short horizon)."
    if not calibration_assessed:
        return (f"not admitted: MASE improvement confirmed, calibration NOT assessed "
                f"({calib_note}).")
    return f"not admitted: improves MASE but worsens calibration ({calib_note})."
