"""Interactive Plotly figure: TSFM foundation models vs transparent AR baselines.

Reads only the per-fold score files and recomputes every aggregate in this
script. The pre-aggregated *_summary.csv files are used solely as a
cross-check (see verify_tsfm_benchmark_figure.py), never as plot input.

Panels
------
A  Mean MASE by model and target over the common rolling-origin folds.
B  Per-fold MASE distribution (box + points) -- shows dispersion the means hide.
C  Interval calibration: empirical vs nominal coverage. Nominal level differs by
   model (0.80 vs 0.95), so the panel plots empirical against its own nominal
   reference rather than pooling incomparable levels.

Output: reports/figures/tsfm_benchmark_interactive.html (self-contained).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
FIGDIR = ROOT / "reports" / "figures"

TSFM_SCORES = PROCESSED / "tsfm_benchmark_scores.csv"
BASELINE_SCORES = PROCESSED / "baseline_scores.csv"
AR_INTERVAL_SCORES = PROCESSED / "ar_interval_scores.csv"

TARGET_LABEL = {
    "hormuz_tanker_transits": "Hormuz tanker transits (vessels/day)",
    "hormuz_tanker_capacity": "Hormuz tanker capacity (DWT/day)",
}

FAMILY = {
    "chronos2": "foundation",
    "timesfm": "foundation",
    "moirai": "foundation",
    "stub_seasonal": "null",
    "ar_lag1_7": "baseline",
    "arx_lag1_7_route": "baseline",
    "arx_lag1_7_route_energy": "baseline",
    "seasonal_naive_7d": "null",
}
COLOR = {"foundation": "#1f78b4", "baseline": "#33a02c", "null": "#9e9e9e"}
REFERENCE_MODEL = "ar_lag1_7"


def load_scores() -> tuple[pd.DataFrame, list[str]]:
    """Return per-fold scores restricted to folds every model actually scored.

    A model that skipped folds would otherwise get a mean over an easier
    subset. Restricting to the intersection makes the MASE column comparable
    across model families by construction rather than by assumption.
    """
    tsfm = pd.read_csv(TSFM_SCORES)
    base = pd.read_csv(BASELINE_SCORES)

    keep = ["model", "target", "fold", "test_start", "test_end", "n_scored", "mase"]
    scores = pd.concat([tsfm[keep], base[keep]], ignore_index=True)

    per_model_folds = scores.groupby(["model", "target"]).fold.apply(set)
    common = set.intersection(*per_model_folds.tolist())
    dropped = sorted(set(scores.fold) - common)
    scores = scores[scores.fold.isin(common)].copy()

    if scores.n_scored.nunique() != 1:
        raise ValueError(
            f"non-constant scoring horizon: {sorted(scores.n_scored.unique())}"
        )
    return scores, dropped


def load_coverage() -> pd.DataFrame:
    """Interval calibration for models that emit intervals.

    The transparent AR baselines emit no native intervals; ar_interval_scores.csv
    holds their split-conformal intervals, which only exist from the fold where
    enough calibration residuals have accumulated. Those folds are therefore a
    subset and are labelled as such in the figure.
    """
    tsfm = pd.read_csv(TSFM_SCORES)
    cols = ["model", "target", "fold", "nominal_coverage", "empirical_coverage"]
    frames = [tsfm[cols]]

    if AR_INTERVAL_SCORES.exists():
        ar = pd.read_csv(AR_INTERVAL_SCORES)
        ar = ar[cols].copy()
        ar["model"] = ar["model"] + " (conformal)"
        frames.append(ar)
    return pd.concat(frames, ignore_index=True)


def order_models(scores: pd.DataFrame, target: str) -> list[str]:
    means = scores[scores.target == target].groupby("model").mase.mean()
    return list(means.sort_values().index)


def build_figure(scores: pd.DataFrame, coverage: pd.DataFrame, dropped: list[str]):
    targets = sorted(scores.target.unique())
    cov_lo = float(coverage.empirical_coverage.min())
    cov_range = [min(0.70, cov_lo - 0.05), 1.02]
    n_folds = scores.fold.nunique()
    horizon = int(scores.n_scored.iloc[0])
    span = f"{scores.test_start.min()} to {scores.test_end.max()}"

    fig = make_subplots(
        rows=3,
        cols=len(targets),
        subplot_titles=[
            *[f"A. Mean MASE — {TARGET_LABEL.get(t, t)}" for t in targets],
            *[f"B. Per-fold MASE — {TARGET_LABEL.get(t, t)}" for t in targets],
            *[f"C. Interval coverage — {TARGET_LABEL.get(t, t)}" for t in targets],
        ],
        vertical_spacing=0.09,
        horizontal_spacing=0.10,
        row_heights=[0.3, 0.36, 0.34],
    )

    for col, target in enumerate(targets, start=1):
        sub = scores[scores.target == target]
        order = order_models(sub, target)
        means = sub.groupby("model").mase.mean()
        ar_mean = means.get(REFERENCE_MODEL)

        fig.add_trace(
            go.Bar(
                x=[means[m] for m in order],
                y=order,
                orientation="h",
                marker_color=[COLOR[FAMILY[m]] for m in order],
                text=[f"{means[m]:.3f}" for m in order],
                textposition="outside",
                cliponaxis=False,
                hovertemplate=(
                    "%{y}<br>mean MASE %{x:.4f}"
                    f"<br>{n_folds} folds, {horizon}-day horizon<extra></extra>"
                ),
                showlegend=False,
            ),
            row=1,
            col=col,
        )
        fig.add_vline(
            x=1.0, line=dict(color="#b2182b", width=1, dash="dot"), row=1, col=col
        )
        if ar_mean is not None:
            fig.add_vline(
                x=ar_mean,
                line=dict(color="#33a02c", width=1, dash="dash"),
                row=1,
                col=col,
            )

        for model in order:
            d = sub[sub.model == model]
            fig.add_trace(
                go.Box(
                    x=d.mase,
                    y=[model] * len(d),
                    orientation="h",
                    name=model,
                    marker_color=COLOR[FAMILY[model]],
                    boxpoints="all",
                    jitter=0.45,
                    pointpos=0,
                    marker=dict(size=4, opacity=0.55),
                    line=dict(width=1.2),
                    customdata=d[["fold", "test_start"]].values,
                    hovertemplate=(
                        "%{y}<br>MASE %{x:.3f}"
                        "<br>%{customdata[0]} (test from %{customdata[1]})<extra></extra>"
                    ),
                    showlegend=False,
                ),
                row=2,
                col=col,
            )
        fig.add_vline(
            x=1.0, line=dict(color="#b2182b", width=1, dash="dot"), row=2, col=col
        )

        cov = coverage[coverage.target == target]
        for model in sorted(cov.model.unique()):
            d = cov[cov.model == model]
            base_name = model.replace(" (conformal)", "")
            fam = FAMILY.get(base_name, "baseline")
            fig.add_trace(
                go.Scatter(
                    x=d.nominal_coverage,
                    y=d.empirical_coverage,
                    mode="markers",
                    name=model,
                    marker=dict(
                        color=COLOR[fam],
                        size=8,
                        opacity=0.6,
                        symbol="diamond" if "conformal" in model else "circle",
                        line=dict(width=0.5, color="white"),
                    ),
                    customdata=d[["fold", "model"]].values,
                    hovertemplate=(
                        "%{customdata[1]}<br>nominal %{x:.2f} / empirical %{y:.3f}"
                        "<br>%{customdata[0]}<extra></extra>"
                    ),
                    showlegend=(col == 1),
                    legendgroup=model,
                ),
                row=3,
                col=col,
            )
        fig.add_trace(
            go.Scatter(
                x=[0.75, 1.0],
                y=[0.75, 1.0],
                mode="lines",
                line=dict(color="#666666", width=1, dash="dash"),
                hoverinfo="skip",
                showlegend=False,
            ),
            row=3,
            col=col,
        )

        fig.update_xaxes(title_text="MASE (lower is better)", row=1, col=col)
        fig.update_xaxes(title_text="MASE by fold", row=2, col=col)
        fig.update_xaxes(
            title_text="nominal coverage", row=3, col=col, range=[0.75, 1.0]
        )
        fig.update_yaxes(
            title_text="empirical coverage", row=3, col=col, range=cov_range
        )
        fig.update_yaxes(categoryorder="array", categoryarray=order[::-1], row=1, col=col)
        fig.update_yaxes(categoryorder="array", categoryarray=order[::-1], row=2, col=col)

    note = (
        f"Rolling-origin evaluation: {n_folds} folds, {horizon}-day horizon, "
        f"test windows {span}. Blue = time-series foundation models, "
        "green = transparent AR baselines, grey = null models. "
        "Dotted red line: MASE = 1 (seasonal-naive equivalent). "
        "Dashed green line: ar_lag1_7 reference. "
        "Panel C — nominal level is model-native (0.80 for moirai/timesfm, "
        "0.95 for chronos2/stub_seasonal and the AR conformal intervals), so "
        "points are read against the diagonal, not against each other."
    )
    if dropped:
        note += f" Folds excluded (not scored by every model): {', '.join(dropped)}."

    fig.update_layout(
        template="plotly_white",
        height=1250,
        width=1400,
        title=dict(
            text=(
                "Foundation-model forecasts beat the AR baseline on point accuracy; "
                "calibration is the binding constraint"
                "<br><sup>Strait of Hormuz tanker throughput, leakage-safe "
                "rolling-origin folds</sup>"
            ),
            x=0.01,
            xanchor="left",
        ),
        legend=dict(
            orientation="h", yanchor="top", y=-0.04, xanchor="left", x=0, title=""
        ),
        margin=dict(t=110, b=190, l=190, r=60),
        boxgap=0.35,
        annotations=list(fig.layout.annotations)
        + [
            dict(
                text=note,
                xref="paper",
                yref="paper",
                x=0,
                y=-0.135,
                xanchor="left",
                yanchor="top",
                showarrow=False,
                align="left",
                font=dict(size=11, color="#444444"),
                width=1300,
            )
        ],
    )
    return fig


def main() -> int:
    scores, dropped = load_scores()
    coverage = load_coverage()
    fig = build_figure(scores, coverage, dropped)

    FIGDIR.mkdir(parents=True, exist_ok=True)
    out = FIGDIR / "tsfm_benchmark_interactive.html"
    fig.write_html(out, include_plotlyjs="inline", full_html=True)
    print(f"wrote {out}")

    tidy = FIGDIR / "tsfm_benchmark_interactive_data.csv"
    scores.to_csv(tidy, index=False)
    print(f"wrote {tidy}  ({len(scores)} model-target-fold rows)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
