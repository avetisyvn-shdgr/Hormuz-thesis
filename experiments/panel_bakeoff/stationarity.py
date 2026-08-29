"""Panel-wide persistence diagnostics tied to the AR(1,7) geometry."""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from .protocol import OUTPUT_DIR, TREATMENT_CUTOFF, composition_wide, load_raw_panel, total_wide


def adf_t_statistic(values: np.ndarray, difference_lags: int = 7) -> float:
    """ADF t-stat on the lagged level with intercept and weekday controls."""
    y = np.asarray(values, dtype="float64")
    delta = np.diff(y)
    start = difference_lags
    rows = []
    targets = []
    for delta_index in range(start, len(delta)):
        level_index = delta_index
        weekday = (delta_index + 1) % 7
        weekday_controls = [float(weekday == day) for day in range(1, 7)]
        rows.append(
            [1.0, y[level_index], *delta[delta_index - difference_lags:delta_index], *weekday_controls]
        )
        targets.append(delta[delta_index])
    design = np.asarray(rows, dtype="float64")
    target = np.asarray(targets, dtype="float64")
    beta, *_ = np.linalg.lstsq(design, target, rcond=None)
    residual = target - np.dot(design, beta)
    degrees = len(target) - design.shape[1]
    covariance = np.linalg.pinv(np.dot(design.T, design)) * (np.dot(residual, residual) / degrees)
    standard_error = float(np.sqrt(covariance[1, 1]))
    return float(beta[1] / standard_error) if standard_error > 0 else float("nan")


def ar17_spectral_radius(values: np.ndarray) -> tuple[float, float, float]:
    """Fit AR(1,7)+weekday controls and return phi1, phi7, companion radius."""
    y = np.asarray(values, dtype="float64")
    t = np.arange(7, len(y))
    weekday = t % 7
    weekday_controls = np.column_stack([(weekday == day).astype(float) for day in range(1, 7)])
    design = np.column_stack([np.ones(len(t)), y[t - 1], y[t - 7], weekday_controls])
    beta, *_ = np.linalg.lstsq(design, y[t], rcond=None)
    companion = np.zeros((7, 7), dtype="float64")
    companion[0, 0] = beta[1]
    companion[0, 6] = beta[2]
    companion[1:, :-1] = np.eye(6)
    radius = float(np.max(np.abs(np.linalg.eigvals(companion))))
    return float(beta[1]), float(beta[2]), radius


def main() -> None:
    raw = load_raw_panel()
    panels = {"composition_28x5": composition_wide(raw), "total_28x1": total_wide(raw)}
    rows = []
    for panel_name, panel in panels.items():
        train = panel.loc[panel.index < TREATMENT_CUTOFF]
        for port, vessel_class in train.columns:
            values = train[(port, vessel_class)].to_numpy(dtype="float64")
            phi1, phi7, radius = ar17_spectral_radius(values)
            rows.append(
                {
                    "panel": panel_name,
                    "portname": port,
                    "vessel_class": vessel_class,
                    "n_days": len(values),
                    "adf_t_constant_weekday_lag7": adf_t_statistic(values),
                    "approx_adf_reject_5pct": adf_t_statistic(values) < -2.86,
                    "ar_phi1": phi1,
                    "ar_phi7": phi7,
                    "ar17_companion_spectral_radius": radius,
                    "near_unit_root_radius_ge_0_995": radius >= 0.995,
                }
            )
    result = pd.DataFrame(rows)
    result.to_csv(OUTPUT_DIR / "stationarity_diagnostics.csv", index=False)
    composition = panels["composition_28x5"].loc[
        panels["composition_28x5"].index < TREATMENT_CUTOFF
    ].to_numpy(dtype="float64").T
    composition = (composition - composition.mean(axis=1, keepdims=True)) / np.where(
        composition.std(axis=1, keepdims=True) > 0,
        composition.std(axis=1, keepdims=True),
        1.0,
    )
    singular = np.linalg.svd(composition, full_matrices=False, compute_uv=False)
    energy = np.cumsum(singular**2) / np.sum(singular**2)
    probabilities = singular / singular.sum()
    geometry = {
        "composition_panel_shape_series_by_days": list(composition.shape),
        "components_for_50pct_energy": int(np.searchsorted(energy, 0.50) + 1),
        "components_for_80pct_energy": int(np.searchsorted(energy, 0.80) + 1),
        "components_for_90pct_energy": int(np.searchsorted(energy, 0.90) + 1),
        "components_for_95pct_energy": int(np.searchsorted(energy, 0.95) + 1),
        "entropy_effective_rank": float(
            np.exp(-np.sum(probabilities * np.log(probabilities + 1e-300)))
        ),
        "interpretation": (
            "The standardized composition panel is not strongly low-rank; aggregate columns "
            "n_cargo and n_total were excluded because they are exact sums of explicit classes."
        ),
    }
    (OUTPUT_DIR / "panel_geometry.json").write_text(
        json.dumps(geometry, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        result.groupby("panel").agg(
            n_series=("vessel_class", "size"),
            adf_reject_share=("approx_adf_reject_5pct", "mean"),
            median_spectral_radius=("ar17_companion_spectral_radius", "median"),
            p95_spectral_radius=("ar17_companion_spectral_radius", lambda values: values.quantile(0.95)),
            max_spectral_radius=("ar17_companion_spectral_radius", "max"),
            near_unit_count=("near_unit_root_radius_ge_0_995", "sum"),
        ).to_string()
    )


if __name__ == "__main__":
    main()
