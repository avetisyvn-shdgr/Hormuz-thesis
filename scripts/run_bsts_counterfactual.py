"""Run the corroborative Bayesian structural time-series counterfactual."""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lngfreight import config  # noqa: E402
from lngfreight.bsts import fit_bsts_forecast, posterior_shortfall  # noqa: E402
from lngfreight.metrics import score_forecast  # noqa: E402
from lngfreight.specification import working_specification  # noqa: E402
from lngfreight.validation import resolve_cutoff, rolling_origin_splits  # noqa: E402


SEED = int(config.settings()["reproducibility"]["random_seed"])


def _validation(panel: pd.DataFrame, target: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows = []
    forecasts = []
    folds = rolling_origin_splits(panel.index)
    y = panel[target].astype("float64")
    for i, fold in enumerate(folds):
        train = y.iloc[fold.train_idx]
        test = y.iloc[fold.test_idx]
        result = fit_bsts_forecast(
            train,
            test.index,
            n_draws=120,
            burn=80,
            thin=1,
            seed=SEED + i,
        )
        prediction = pd.Series(
            np.median(result.predictive_draws, axis=0), index=test.index
        )
        rows.append({
            "model": "bsts_local_level_weekly",
            "target": target,
            "fold": fold.name,
            "train_start": fold.train_start.date(),
            "train_end": fold.train_end.date(),
            "test_start": fold.test_start.date(),
            "test_end": fold.test_end.date(),
            **score_forecast(test, prediction, train, season_length=7),
        })
        forecast_frame = pd.DataFrame({
            "date": test.index,
            "model": "bsts_local_level_weekly",
            "target": target,
            "fold": fold.name,
            "y_true": test.to_numpy(),
            "y_pred": prediction.to_numpy(),
        })
        forecast_frame["error"] = forecast_frame["y_true"] - forecast_frame["y_pred"]
        forecasts.append(forecast_frame)
    return pd.DataFrame(rows), pd.concat(forecasts, ignore_index=True)


def main() -> None:
    panel_path = config.path("data_processed") / "panel_aligned.csv"
    panel = pd.read_csv(panel_path, parse_dates=["date"]).set_index("date")
    cutoff = resolve_cutoff()
    target = working_specification().primary_outcome
    y = panel[target].astype("float64")
    train = y.loc[y.index < cutoff]
    observed = y.loc[y.index >= cutoff]

    result = fit_bsts_forecast(
        train,
        observed.index,
        n_draws=1500,
        burn=750,
        thin=2,
        seed=SEED,
    )
    daily = result.forecast_frame()
    daily["target"] = target
    daily["model"] = "bsts_local_level_weekly"
    daily["y_true"] = observed.to_numpy()
    daily["shortfall"] = daily["y_pred"] - daily["y_true"]
    daily["cumulative_shortfall"] = daily["shortfall"].cumsum()

    effect = posterior_shortfall(result.predictive_draws, observed)
    validation, validation_forecasts = _validation(panel.loc[panel.index < cutoff], target)
    summary = pd.DataFrame([{
        "model": "bsts_local_level_weekly",
        "target": target,
        "train_start": train.index.min().date(),
        "train_end": train.index.max().date(),
        "post_start": observed.index.min().date(),
        "post_end": observed.index.max().date(),
        "n_post_days": len(observed),
        "validation_mase_mean": validation["mase"].mean(),
        "validation_rmse_mean": validation["rmse"].mean(),
        "validation_mase_median": validation["mase"].median(),
        "posterior_observation_sd_median": float(
            np.median(np.sqrt(result.observation_variance_draws))
        ),
        "posterior_level_innovation_sd_median": float(
            np.median(np.sqrt(result.level_variance_draws))
        ),
        **effect,
    }])

    out_dir = config.path("data_processed")
    daily.to_csv(out_dir / "bsts_counterfactual_daily.csv", index=False)
    summary.to_csv(out_dir / "bsts_counterfactual_summary.csv", index=False)
    validation.to_csv(out_dir / "bsts_validation_scores.csv", index=False)
    validation_forecasts.to_csv(out_dir / "bsts_validation_forecasts.csv", index=False)

    fig, ax = plt.subplots(figsize=(11, 5.5))
    ax.plot(panel.index, y, color="#202020", linewidth=1.0, label="Observed")
    ax.plot(daily["date"], daily["y_pred"], color="#276FBF", linewidth=1.7,
            label="BSTS posterior median")
    ax.fill_between(
        daily["date"], daily["lower_95"], daily["upper_95"],
        color="#276FBF", alpha=0.2, label="95% posterior predictive interval",
    )
    ax.axvline(cutoff, color="#B33A3A", linestyle="--", linewidth=1.3,
               label=f"Treatment: {cutoff.date()}")
    ax.set(title="Hormuz tanker transits: BSTS counterfactual",
           ylabel="Daily tanker transit count", xlabel="Date")
    ax.legend(frameon=False, ncol=2)
    ax.grid(alpha=0.2)
    fig.tight_layout()
    figure_path = config.path("figures") / "bsts_counterfactual.png"
    fig.savefig(figure_path, dpi=180)
    plt.close(fig)

    print("BSTS counterfactual summary:")
    print(summary.to_string(index=False))
    print(f"wrote {figure_path}")
    print("Interpretation guard: posterior intervals are model-conditional; this is corroboration, not causal ATT.")


if __name__ == "__main__":
    main()
