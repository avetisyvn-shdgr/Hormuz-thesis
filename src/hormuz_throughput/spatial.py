"""Spatial placebo utilities for PortWatch chokepoints.

These helpers build wide daily panels from the pinned PortWatch snapshot so the
same counterfactual machinery can be applied to non-Hormuz chokepoints. This is
not synthetic control yet; it is a placebo-in-space diagnostic.
"""
from __future__ import annotations

import pandas as pd

from . import config
from .inference import empirical_p_value, separation_ratio
from .registry import RegisteredArtifact, get_variable
from .sources.portwatch import EXPECTED_COLUMNS, VALUE_COLUMNS


CONTAMINATION_NOTES = {
    "Panama Canal": "Potential rerouting / Atlantic-Pacific LNG arbitrage channel.",
    "Suez Canal": "Potential rerouting / Red Sea disruption exposure.",
    "Bab el-Mandeb Strait": "Potential rerouting / Red Sea disruption exposure.",
    "Cape of Good Hope": "Direct rerouting substitute for Middle East-Europe traffic.",
    "Gibraltar Strait": "Europe/Mediterranean route exposure; possible spillover.",
}


def slugify_portname(portname: str) -> str:
    """Stable column slug for PortWatch port names."""
    return (
        portname.strip()
        .lower()
        .replace(" ", "_")
        .replace("-", "_")
    )


def load_portwatch_snapshot() -> pd.DataFrame:
    """Load and schema-check the pinned PortWatch CSV snapshot."""
    artifact = get_variable(
        "portwatch_chokepoints_snapshot",
        query={"consumer": "spatial_placebo"},
    )
    if not isinstance(artifact, RegisteredArtifact):
        raise TypeError("portwatch_chokepoints_snapshot must resolve as an artifact")
    df = artifact.read_csv(encoding="utf-8-sig")
    if list(df.columns) != EXPECTED_COLUMNS:
        raise ValueError(
            "PortWatch schema drift detected. Expected columns "
            f"{EXPECTED_COLUMNS}, got {list(df.columns)}."
        )
    return df


def wide_chokepoint_panel(
    value_col: str = "n_tanker",
    start: str | None = None,
    end: str | None = None,
    exclude: list[str] | None = None,
) -> pd.DataFrame:
    """Return a date x chokepoint wide panel for one PortWatch value column."""
    if value_col not in VALUE_COLUMNS:
        raise ValueError(f"value_col must be one of {VALUE_COLUMNS}, got {value_col!r}.")

    win = config.settings()["study_window"]
    start = start or win["full_start"]
    end = end or win["full_end"]
    exclude_slugs = {slugify_portname(x) for x in (exclude or [])}

    needed_cols = ["date", "portname", value_col]
    if value_col == "capacity_tanker":
        needed_cols.append("n_tanker")
    df = load_portwatch_snapshot()
    df = df[needed_cols].copy()
    df["date"] = pd.to_datetime(df["date"], format="%Y/%m/%d")
    df["slug"] = df["portname"].map(slugify_portname)
    df = df[~df["slug"].isin(exclude_slugs)]
    df = df[(df["date"] >= pd.Timestamp(start)) & (df["date"] <= pd.Timestamp(end))]

    if (
        value_col == "capacity_tanker"
        and config.settings().get("imputation", {}).get("capacity_zero_with_transits") == "mask"
    ):
        artifact = (df["n_tanker"] > 0) & (df[value_col] == 0)
        df.loc[artifact, value_col] = pd.NA

    index = pd.date_range(start, end, freq="D", name="date")
    cols: dict[str, pd.Series] = {}
    for slug, part in df.groupby("slug", sort=True):
        if part["date"].duplicated().any():
            raise ValueError(f"Duplicate PortWatch dates for {slug!r}.")
        cols[slug] = part.set_index("date")[value_col].sort_index().reindex(index)

    wide = pd.DataFrame(cols, index=index)
    return wide.astype("float64")


def chokepoint_metadata(exclude: list[str] | None = None) -> pd.DataFrame:
    """Return one metadata row per PortWatch chokepoint in the snapshot."""
    exclude_slugs = {slugify_portname(x) for x in (exclude or [])}
    df = load_portwatch_snapshot()[["portname"]].drop_duplicates().copy()
    df["slug"] = df["portname"].map(slugify_portname)
    df = df[~df["slug"].isin(exclude_slugs)].sort_values("slug")
    df["contamination_note"] = df["portname"].map(CONTAMINATION_NOTES).fillna("")
    df["contamination_flag"] = df["contamination_note"].ne("")
    return df[["slug", "portname", "contamination_flag", "contamination_note"]].reset_index(drop=True)


def _spatial_summary_row(
    value_col: str,
    donor_set: str,
    actual: pd.Series,
    donors: pd.DataFrame,
    dropped_slug: str | None = None,
    dropped_portname: str | None = None,
) -> dict[str, object]:
    """Summarize treated-vs-donor losses for one donor pool."""
    if donors.empty:
        raise ValueError("Need at least one donor to summarize spatial placebo evidence.")

    losses = donors["cumulative_throughput_loss"]
    daily = donors["mean_daily_throughput_loss"]
    normalized = donors["normalized_throughput_loss"]
    loss_p95 = float(losses.quantile(0.95))
    daily_p95 = float(daily.quantile(0.95))
    normalized_p95 = float(normalized.quantile(0.95))
    row = {
        "value_col": value_col,
        "donor_set": donor_set,
        "actual_cumulative_throughput_loss": float(actual["cumulative_throughput_loss"]),
        "actual_mean_daily_throughput_loss": float(actual["mean_daily_throughput_loss"]),
        "actual_counterfactual_sum": float(actual["counterfactual_sum"]),
        "actual_normalized_throughput_loss": float(actual["normalized_throughput_loss"]),
        "actual_n_days": int(actual["n_days"]),
        "n_donors": int(len(donors)),
        "donor_loss_mean": float(losses.mean()),
        "donor_loss_median": float(losses.median()),
        "donor_loss_p95": loss_p95,
        "loss_vs_donor_p95_ratio": separation_ratio(
            actual["cumulative_throughput_loss"],
            loss_p95,
        ),
        "donor_mean_daily_loss_mean": float(daily.mean()),
        "donor_mean_daily_loss_median": float(daily.median()),
        "donor_mean_daily_loss_p95": daily_p95,
        "mean_daily_loss_vs_donor_p95_ratio": separation_ratio(
            actual["mean_daily_throughput_loss"],
            daily_p95,
        ),
        "donor_normalized_loss_mean": float(normalized.mean()),
        "donor_normalized_loss_median": float(normalized.median()),
        "donor_normalized_loss_p95": normalized_p95,
        "normalized_loss_vs_donor_p95_ratio": separation_ratio(
            actual["normalized_throughput_loss"],
            normalized_p95,
        ),
        "p_donor_loss_ge_actual": empirical_p_value(
            actual["cumulative_throughput_loss"],
            losses,
            alternative="greater",
        ),
        "p_donor_mean_daily_loss_ge_actual": empirical_p_value(
            actual["mean_daily_throughput_loss"],
            daily,
            alternative="greater",
        ),
        "p_donor_normalized_loss_ge_actual": empirical_p_value(
            actual["normalized_throughput_loss"],
            normalized,
            alternative="greater",
        ),
        "max_donor_slug": str(donors.loc[losses.idxmax(), "slug"]),
        "max_donor_loss": float(losses.max()),
        "max_normalized_donor_slug": str(donors.loc[normalized.idxmax(), "slug"]),
        "max_normalized_donor_loss": float(normalized.max()),
    }
    if dropped_slug is not None:
        row["dropped_slug"] = dropped_slug
        row["dropped_portname"] = dropped_portname or ""
    return row


def spatial_placebo_summary(
    effects: pd.DataFrame,
    meta: pd.DataFrame,
) -> pd.DataFrame:
    """Summarize same-date spatial placebo evidence for all and clean donors."""
    merged = effects.merge(meta, on="slug", how="left")
    rows = []
    for value_col, group in merged.groupby("value_col"):
        actual = group.loc[group["is_treated"]].iloc[0]
        donors_all = group.loc[~group["is_treated"]].copy()
        donors_clean = donors_all.loc[~donors_all["contamination_flag"]].copy()

        for donor_set, donors in [
            ("all_donors", donors_all),
            ("low_contamination_donors", donors_clean),
        ]:
            rows.append(_spatial_summary_row(value_col, donor_set, actual, donors))
    return pd.DataFrame(rows)


def leave_one_donor_out_summary(
    effects: pd.DataFrame,
    meta: pd.DataFrame,
) -> pd.DataFrame:
    """Recompute spatial placebo statistics after dropping each donor in turn.

    This is a sensitivity diagnostic for the unweighted donor-pool comparison,
    not a new model. The treated chokepoint is never dropped.
    """
    merged = effects.merge(meta, on="slug", how="left")
    rows = []
    for value_col, group in merged.groupby("value_col"):
        actual = group.loc[group["is_treated"]].iloc[0]
        donors_all = group.loc[~group["is_treated"]].copy()
        donor_sets = [
            ("all_donors", donors_all),
            (
                "low_contamination_donors",
                donors_all.loc[~donors_all["contamination_flag"]].copy(),
            ),
        ]
        for donor_set, donors in donor_sets:
            for _, dropped in donors.iterrows():
                kept = donors.loc[donors["slug"] != dropped["slug"]].copy()
                row = _spatial_summary_row(
                    value_col,
                    donor_set,
                    actual,
                    kept,
                    dropped_slug=str(dropped["slug"]),
                    dropped_portname=str(dropped.get("portname", "")),
                )
                row["dropped_contamination_flag"] = bool(dropped["contamination_flag"])
                row["dropped_was_raw_max"] = dropped["slug"] == donors.loc[
                    donors["cumulative_throughput_loss"].idxmax(),
                    "slug",
                ]
                row["dropped_was_normalized_max"] = dropped["slug"] == donors.loc[
                    donors["normalized_throughput_loss"].idxmax(),
                    "slug",
                ]
                rows.append(row)
    return pd.DataFrame(rows)
