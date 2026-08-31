"""Frozen data geometry for the PortWatch panel bake-off.

This experiment reads the institutional raw snapshot directly.  It deliberately
does not import thesis narrative settings, treatment labels, or previously
generated benchmark artifacts.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
RAW_PATH = ROOT / "data/raw/portwatch/Daily_Chokepoints_Data.csv"
OUTPUT_DIR = Path(__file__).resolve().parent / "outputs"

EXPLICIT_CLASSES = (
    "n_container",
    "n_dry_bulk",
    "n_general_cargo",
    "n_roro",
    "n_tanker",
)
TOTAL_OUTCOME = "n_total"
EXPECTED_SHA256 = "66f3a54afb042103f3e0afc9670568cb7be245394ec04eba55ebd158593f579d"

CALIBRATION_START = pd.Timestamp("2022-08-24")
EVALUATION_START = pd.Timestamp("2023-01-01")
TREATMENT_CUTOFF = pd.Timestamp("2026-02-28")
HORIZONS = (30, 130)
ORIGIN_STEP_DAYS = 130
N_MASK_GROUPS = 7
SEASON_LENGTH = 7


@dataclass(frozen=True)
class EvaluationFold:
    name: str
    origin: pd.Timestamp
    horizon: int

    @property
    def test_dates(self) -> pd.DatetimeIndex:
        return pd.date_range(self.origin, periods=self.horizon, freq="D")


def file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_raw_panel(path: Path = RAW_PATH) -> pd.DataFrame:
    """Load and validate the complete daily 28-chokepoint snapshot."""
    actual_hash = file_sha256(path)
    if actual_hash != EXPECTED_SHA256:
        raise ValueError(
            f"PortWatch snapshot hash changed: expected {EXPECTED_SHA256}, got {actual_hash}."
        )
    frame = pd.read_csv(path)
    required = {"date", "portname", "n_cargo", TOTAL_OUTCOME, *EXPLICIT_CLASSES}
    missing = sorted(required.difference(frame.columns))
    if missing:
        raise ValueError(f"PortWatch snapshot is missing columns: {missing}")
    frame["date"] = pd.to_datetime(frame["date"], errors="raise")
    frame = frame.sort_values(["date", "portname"], kind="stable").reset_index(drop=True)
    if frame.duplicated(["date", "portname"]).any():
        raise ValueError("PortWatch contains duplicate chokepoint-days.")
    if frame["portname"].nunique() != 28:
        raise ValueError(f"Expected 28 chokepoints, found {frame['portname'].nunique()}.")
    expected_rows = frame["date"].nunique() * frame["portname"].nunique()
    if len(frame) != expected_rows:
        raise ValueError("PortWatch is not a complete date-by-chokepoint grid.")
    if frame[list(EXPLICIT_CLASSES) + [TOTAL_OUTCOME]].isna().any().any():
        raise ValueError("PortWatch outcome panel contains missing values.")
    explicit_sum = frame[list(EXPLICIT_CLASSES)].sum(axis=1)
    cargo_sum = frame[list(EXPLICIT_CLASSES[:-1])].sum(axis=1)
    if not np.array_equal(explicit_sum.to_numpy(), frame[TOTAL_OUTCOME].to_numpy()):
        raise ValueError("n_total is no longer the exact sum of the five explicit classes.")
    if not np.array_equal(cargo_sum.to_numpy(), frame["n_cargo"].to_numpy()):
        raise ValueError("n_cargo is no longer the exact sum of the four non-tanker classes.")
    return frame


def composition_wide(frame: pd.DataFrame) -> pd.DataFrame:
    """Return dates x (chokepoint, mutually-exclusive vessel class)."""
    ordered = frame.sort_values(["date", "portname"], kind="stable")
    dates = pd.DatetimeIndex(sorted(ordered["date"].unique()), name="date")
    ports = sorted(ordered["portname"].unique())
    expected_dates = np.repeat(dates.to_numpy(), len(ports))
    expected_ports = np.tile(np.asarray(ports, dtype=object), len(dates))
    if not np.array_equal(ordered["date"].to_numpy(), expected_dates):
        raise ValueError("PortWatch rows are not a complete date-major grid.")
    if not np.array_equal(ordered["portname"].to_numpy(), expected_ports):
        raise ValueError("PortWatch rows are not a complete port-minor grid.")
    pieces = []
    for vessel_class in EXPLICIT_CLASSES:
        part = pd.DataFrame(
            ordered[vessel_class].to_numpy(dtype="float64").reshape(len(dates), len(ports)),
            index=dates,
            columns=ports,
        )
        part.columns = pd.MultiIndex.from_product(
            [part.columns, [vessel_class]], names=["portname", "vessel_class"]
        )
        pieces.append(part)
    return pd.concat(pieces, axis=1).sort_index(axis=1).astype("float64")


def total_wide(frame: pd.DataFrame) -> pd.DataFrame:
    ordered = frame.sort_values(["date", "portname"], kind="stable")
    dates = pd.DatetimeIndex(sorted(ordered["date"].unique()), name="date")
    ports = sorted(ordered["portname"].unique())
    part = pd.DataFrame(
        ordered[TOTAL_OUTCOME].to_numpy(dtype="float64").reshape(len(dates), len(ports)),
        index=dates,
        columns=ports,
    )
    part.columns = pd.MultiIndex.from_product(
        [part.columns, [TOTAL_OUTCOME]], names=["portname", "vessel_class"]
    )
    return part.sort_index(axis=1).astype("float64")


def folds(index: pd.DatetimeIndex) -> list[EvaluationFold]:
    """Build common, disjoint 130-day origins and their 30-day sub-horizons."""
    out: list[EvaluationFold] = []
    origin = EVALUATION_START
    fold_number = 1
    while origin + pd.Timedelta(days=max(HORIZONS) - 1) < TREATMENT_CUTOFF:
        for horizon in HORIZONS:
            test_dates = pd.date_range(origin, periods=horizon, freq="D")
            if not test_dates.isin(index).all():
                raise ValueError(f"Missing dates in evaluation window starting {origin.date()}.")
            out.append(EvaluationFold(f"fold_{fold_number:02d}", origin, horizon))
        fold_number += 1
        origin += pd.Timedelta(days=ORIGIN_STEP_DAYS)
    if len(out) != 16:
        raise ValueError(f"Expected 8 origins x 2 horizons, constructed {len(out)} folds.")
    return out


def port_groups(columns: pd.MultiIndex) -> dict[str, int]:
    """Deterministically allocate 28 complete chokepoints to seven mask groups."""
    ports = sorted(columns.get_level_values("portname").unique())
    if len(ports) != 28:
        raise ValueError(f"Expected 28 ports for spatial masks, got {len(ports)}.")
    return {port: idx % N_MASK_GROUPS for idx, port in enumerate(ports)}


def mase_scale(train: np.ndarray, season_length: int = SEASON_LENGTH) -> float:
    values = np.asarray(train, dtype="float64")
    scale = float(np.mean(np.abs(values[season_length:] - values[:-season_length])))
    return scale if np.isfinite(scale) and scale > 0 else float("nan")
