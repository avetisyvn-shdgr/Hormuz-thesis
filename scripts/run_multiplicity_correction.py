"""Romano-Wolf corrections for placebo families with aligned joint null draws.

Temporal placebo windows are reduced to a common disjoint block set before
step-down inference. Overlapping windows are descriptive diagnostics only.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from hormuz_throughput import config  # noqa: E402
from hormuz_throughput.inference import romano_wolf_stepdown  # noqa: E402


def _temporal_family(path: Path) -> pd.DataFrame:
    effects = pd.read_csv(path)
    effects["hypothesis"] = effects["model"] + "::" + effects["target"]
    actual = effects.loc[effects["is_actual"].astype(str).str.lower().eq("true")]
    observed = actual.set_index("hypothesis")["cumulative_throughput_loss"]
    placebo = effects.loc[~effects["is_actual"].astype(str).str.lower().eq("true")]
    spans = (
        placebo[["fold", "test_start", "test_end"]]
        .drop_duplicates()
        .assign(
            test_start=lambda frame: pd.to_datetime(frame["test_start"]),
            test_end=lambda frame: pd.to_datetime(frame["test_end"]),
        )
        .sort_values("test_start")
    )
    selected_folds: list[str] = []
    last_end = None
    for row in spans.itertuples(index=False):
        if last_end is None or row.test_start > last_end:
            selected_folds.append(row.fold)
            last_end = row.test_end
    placebo = placebo.loc[placebo["fold"].isin(selected_folds)]
    joint = placebo.pivot(
        index="fold", columns="hypothesis", values="cumulative_throughput_loss"
    )[observed.index]
    result = romano_wolf_stepdown(observed, joint, alternative="greater")
    result.insert(0, "family", "disjoint_placebo_time_generators_by_outcome")
    return result


def _spatial_family(path: Path) -> pd.DataFrame:
    effects = pd.read_csv(path)
    is_treated = effects["is_treated"].astype(str).str.lower().eq("true")
    contaminated = effects["contamination_flag"].astype(str).str.lower().eq("true")
    actual_rows = effects.loc[is_treated].copy()
    effects = effects.loc[~is_treated & ~contaminated].copy()
    observed = actual_rows.set_index("value_col")["normalized_throughput_loss"]
    joint = effects.pivot(
        index="slug", columns="value_col", values="normalized_throughput_loss"
    )[observed.index].dropna()
    result = romano_wolf_stepdown(observed, joint, alternative="greater")
    result.insert(0, "family", "spatial_placebo_outcomes_low_contamination")
    return result


def main() -> None:
    processed = config.path("data_processed")
    results = pd.concat([
        _temporal_family(processed / "placebo_time_effects.csv"),
        _spatial_family(processed / "spatial_placebo_effects.csv"),
    ], ignore_index=True)
    output = config.ROOT / config.settings()["paths"]["multiplicity_correction_csv"]
    results.to_csv(output, index=False)
    print(results.to_string(index=False))
    print(f"\nwrote {output}")
    print("\nInterpretation guard:")
    print(" - Each family uses aligned joint placebo draws; dependence is preserved.")
    print(" - Temporal inference uses only disjoint full-horizon blocks.")
    print(" - Families without a joint null matrix are not pooled by shuffling draws.")
    print(" - Correction is within inference axis, as pre-registered; family sizes are explicit.")


if __name__ == "__main__":
    main()
