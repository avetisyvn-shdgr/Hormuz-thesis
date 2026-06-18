"""Optional LNG-specific robustness analysis using the public WTO index."""
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
from lngfreight.baselines import arx_forecast  # noqa: E402
from lngfreight.bsts import fit_bsts_forecast, posterior_shortfall  # noqa: E402
from lngfreight.inference import counterfactual_effect  # noqa: E402
from lngfreight.sources.wto_hormuz import WTOHormuzLNGSource  # noqa: E402
from lngfreight.validation import Fold, resolve_cutoff  # noqa: E402


def main() -> None:
    cutoff = resolve_cutoff()
    study_end = pd.Timestamp(config.settings()["study_window"]["full_end"])
    series = WTOHormuzLNGSource().fetch(
        "lng_outbound_volume_index", "2025-01-01", str(study_end.date())
    ).set_index("date")["value"]
    panel = series.rename("wto_hormuz_lng_volume_index").to_frame()
    train_idx = np.flatnonzero(panel.index < cutoff)
    post_idx = np.flatnonzero(panel.index >= cutoff)
    fold = Fold(
        name="lng_actual",
        train_idx=train_idx,
        test_idx=post_idx,
        train_start=panel.index[train_idx[0]],
        train_end=panel.index[train_idx[-1]],
        test_start=panel.index[post_idx[0]],
        test_end=panel.index[post_idx[-1]],
    )
    ar = arx_forecast(
        panel, "wto_hormuz_lng_volume_index", fold, exog_cols=[], y_lags=(1, 7)
    )
    observed = panel.iloc[post_idx, 0]
    bsts = fit_bsts_forecast(
        panel.iloc[train_idx, 0], observed.index,
        n_draws=1500, burn=750, thin=2,
        seed=int(config.settings()["reproducibility"]["random_seed"]) + 101,
    )
    bsts_frame = bsts.forecast_frame().set_index("date")
    ar_effect = counterfactual_effect(observed, ar)
    bsts_effect = posterior_shortfall(bsts.predictive_draws, observed)
    summary = pd.DataFrame([
        {"model": "ar_lag1_7", "outcome": "wto_hormuz_lng_volume_index",
         "n_pre_days": len(train_idx), "n_post_days": len(post_idx), **ar_effect},
        {"model": "bsts_local_level_weekly", "outcome": "wto_hormuz_lng_volume_index",
         "n_pre_days": len(train_idx), "n_post_days": len(post_idx), **bsts_effect},
    ])
    daily = pd.DataFrame({
        "date": observed.index,
        "observed_lng_volume_index": observed.to_numpy(),
        "ar_counterfactual": ar.to_numpy(),
        "bsts_counterfactual_median": bsts_frame["y_pred"].to_numpy(),
        "bsts_lower_95": bsts_frame["lower_95"].to_numpy(),
        "bsts_upper_95": bsts_frame["upper_95"].to_numpy(),
    })
    out = config.path("data_processed")
    summary.to_csv(out / "lng_index_counterfactual_summary.csv", index=False)
    daily.to_csv(out / "lng_index_counterfactual_daily.csv", index=False)

    fig, ax = plt.subplots(figsize=(11, 5.5))
    ax.plot(panel.index, panel.iloc[:, 0], color="#202020", linewidth=1, label="Observed LNG index")
    ax.plot(observed.index, ar, color="#D17A22", linewidth=1.5, label="AR counterfactual")
    ax.plot(observed.index, bsts_frame["y_pred"], color="#276FBF", linewidth=1.5,
            label="BSTS counterfactual")
    ax.fill_between(observed.index, bsts_frame["lower_95"], bsts_frame["upper_95"],
                    color="#276FBF", alpha=0.18)
    ax.axvline(cutoff, color="#B33A3A", linestyle="--", linewidth=1.2)
    ax.set(title="WTO/AXSMarine LNG outbound volume index: optional robustness outcome",
           ylabel="Daily index (2025 average = 100)", xlabel="Date")
    ax.legend(frameon=False)
    ax.grid(alpha=0.2)
    fig.tight_layout()
    figure = config.path("figures") / "lng_index_counterfactual.png"
    fig.savefig(figure, dpi=180)
    plt.close(fig)
    print(summary.to_string(index=False))
    print(f"wrote {figure}")
    print("Guard: LNG-only volume index; not a freight rate, carrier count, or causal ATT.")


if __name__ == "__main__":
    main()
