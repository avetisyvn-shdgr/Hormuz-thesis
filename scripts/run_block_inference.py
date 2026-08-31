"""Independent horizon blocks, rank placebo inference, and block conformal intervals."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from hormuz_throughput import config  # noqa: E402
from hormuz_throughput.inference import conformal_effect_interval, empirical_p_value  # noqa: E402
from hormuz_throughput.specification import working_specification  # noqa: E402


def _select_disjoint_rows(rows: pd.DataFrame) -> pd.DataFrame:
    selected = []
    last_end = None
    for _, row in rows.sort_values("test_start").iterrows():
        start = pd.Timestamp(row["test_start"])
        end = pd.Timestamp(row["test_end"])
        if last_end is None or start > last_end:
            selected.append(row)
            last_end = end
    return pd.DataFrame(selected)


def main() -> None:
    in_path = config.path("data_processed") / "placebo_time_effects.csv"
    effects = pd.read_csv(in_path, parse_dates=["test_start", "test_end"])
    target = working_specification().primary_outcome
    subset = effects.loc[
        (effects["model"] == "ar_lag1_7") & (effects["target"] == target)
    ].copy()
    actual = subset.loc[subset["is_actual"].astype(str).str.lower() == "true"].iloc[0]
    placebo = subset.loc[subset["is_actual"].astype(str).str.lower() != "true"]
    horizon_calendar_days = int((actual["test_end"] - actual["test_start"]).days + 1)
    independent = _select_disjoint_rows(placebo)
    values = independent["cumulative_throughput_loss"].to_numpy(dtype="float64")
    point = float(actual["cumulative_throughput_loss"])
    p_value = empirical_p_value(point, values, alternative="greater")
    p95 = float(np.quantile(values, 0.95))

    rows = []
    for coverage in (0.80, 0.90, 0.95):
        interval = conformal_effect_interval(point, values, alpha=1 - coverage)
        rows.append({
            "model": "ar_lag1_7",
            "target": target,
            "scheme": "non_overlapping_horizon_block_rank",
            "horizon_calendar_days": horizon_calendar_days,
            "n_overlapping_placebo_windows": len(placebo),
            "n_independent_placebo_blocks": len(independent),
            "placebo_p_value_greater": p_value,
            "placebo_p_value_floor": 1.0 / (len(independent) + 1),
            "actual_to_placebo_p95_ratio": point / p95 if p95 else np.nan,
            **interval,
        })
    summary = pd.DataFrame(rows)
    independent = independent.assign(block_scheme="non_overlapping_horizon_block_rank")
    out_dir = config.path("data_processed")
    summary.to_csv(out_dir / "block_conformal_summary.csv", index=False)
    independent.to_csv(out_dir / "block_placebo_effects.csv", index=False)
    print("Block placebo and conformal summary:")
    print(summary.to_string(index=False))
    print(
        "Interpretation guard: only disjoint "
        f"{horizon_calendar_days}-calendar-day windows enter the rank p-value "
        "and conformal calibration."
    )


if __name__ == "__main__":
    main()
