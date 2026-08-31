"""Exploratory analysis of the 2026-08-09 PortWatch revision and basin asymmetry.

Three descriptive questions, none of them causal:

1. Where did the PortWatch revision land? Across all 28 chokepoints and every
   vessel class, comparing the pinned vintage with the 2026-08-09 capture.
2. How did the Hormuz mean level change across vintages, and does a large
   percentage collapse remain visible at that aggregate level? Daily scaling
   is examined separately and is not assumed to be uniform.
3. Did the freight market's stress sit in the basin the disruption hit, or the
   other one? Plus the country-level ton-mile gradient this would imply.

Everything here is DESCRIPTIVE. Nothing in this script identifies a causal
effect, and the Fearnleys inputs are provenance-limited restricted data whose
permitted uses exclude ATT, causal freight effects, and identified mediation
(docs/DATA_SOURCES.md). Raw restricted values are not printed; only derived
ratios and period aggregates.

Run from the repo root:
    python scripts/run_revision_and_basin_exploration.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from hormuz_throughput import config, registry  # noqa: E402

PINNED_VARIABLE = "portwatch_chokepoints_snapshot"
VINTAGE_VARIABLE = "portwatch_chokepoints_vintage_20260809_snapshot"
BLOOMBERG_DIR = "data/raw/bloomberg_transcription"
CUTOFF = pd.Timestamp("2026-02-28")
VESSEL_COLUMNS = ["n_tanker", "n_cargo", "n_container", "n_dry_bulk", "n_total"]


def _load(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, encoding="utf-8-sig", parse_dates=["date"])


def revision_by_chokepoint(old: pd.DataFrame, new: pd.DataFrame) -> pd.DataFrame:
    key = ["portname", "date"]
    o = old.set_index(key).sort_index()
    n = new.set_index(key).sort_index()
    shared = o.index.intersection(n.index)
    o, n = o.loc[shared], n.loc[shared]

    rows = []
    for cp in sorted(o.index.get_level_values(0).unique()):
        oo, nn = o.xs(cp), n.xs(cp)
        row = {"chokepoint": cp, "days": len(oo)}
        for col in VESSEL_COLUMNS:
            a, b = oo[col].astype(float).mean(), nn[col].astype(float).mean()
            row[f"{col}_pct"] = 100 * (b - a) / a if a > 0 else np.nan
        rows.append(row)
    return pd.DataFrame(rows).set_index("chokepoint").sort_values("n_tanker_pct")


def hormuz_mean_revision_profile(
    old: pd.DataFrame, new: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame]:
    def series(frame):
        s = frame[frame.portname == "Strait of Hormuz"]
        return s.set_index("date")["n_tanker"].astype(float).sort_index()

    o, n = series(old), series(new)
    shared = o.index.intersection(n.index)
    o, n = o[shared], n[shared]

    yearly = pd.DataFrame({"pinned": o, "vintage": n})
    by_year = yearly.groupby(yearly.index.year).mean()
    by_year["ratio"] = by_year["vintage"] / by_year["pinned"]

    rows = []
    for label, s in (("pinned", o), ("vintage_20260809", n)):
        pre = s[(s.index >= "2022-01-01") & (s.index < CUTOFF)].mean()
        post = s[s.index >= CUTOFF].mean()
        rows.append({
            "vintage": label,
            "pre_mean": pre,
            "post_mean": post,
            "pct_collapse": 100 * (1 - post / pre),
            "absolute_drop_per_day": pre - post,
        })
    return by_year, pd.DataFrame(rows)


def basin_asymmetry() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Fearnleys basin spot assessments, restricted/provenance-limited.

    Returns period aggregates and the West/East ratio only. The West series
    keeps its documented unverified-zero mask.
    """
    root = config.ROOT / BLOOMBERG_DIR
    def load(name):
        return pd.read_csv(root / name, parse_dates=["date"]).set_index("date")["value"]

    east = load("fearnleys_lng_spot_east_suez__fearnleys_lng_spot_east_suez.csv")
    west = load("fearnleys_lng_spot_west_suez__fearnleys_lng_spot_west_suez.csv")
    west = west.mask(west == 0)
    tc = load("fearnleys_lng_one_year_time_charter__fearnleys_lng_one_year_time_charter.csv")

    frame = pd.DataFrame({"East_spot": east, "West_spot": west, "OneYear_TC": tc})
    pre = frame[(frame.index >= "2025-03-01") & (frame.index < CUTOFF)]
    post = frame[frame.index >= CUTOFF]
    levels = pd.DataFrame({
        "pre_mean": pre.mean(),
        "post_mean": post.mean(),
        "pct_rise": 100 * (post.mean() / pre.mean() - 1),
        "peak_vs_pre_multiple": post.max() / pre.mean(),
    })

    ratio = (frame.West_spot / frame.East_spot).dropna()
    windows = {
        "2022-2025": ("2022-01-01", "2025-12-31"),
        "pre_onset_2026": ("2026-01-01", "2026-02-27"),
        "post_onset": ("2026-02-28", "2026-12-31"),
    }
    ratios = pd.DataFrame([
        {"window": k, "n": len(ratio.loc[a:b]),
         "mean_west_over_east": ratio.loc[a:b].mean(),
         "median_west_over_east": ratio.loc[a:b].median()}
        for k, (a, b) in windows.items()
    ]).set_index("window")
    return levels, ratios


def country_haul_gradient() -> tuple[pd.DataFrame, dict]:
    """Does pre-shock Gulf exposure predict a longer average haul after?

    Uses the frozen GFW-derived importer exposure summary. Leave-one-out is
    reported because n is small and one country can carry the whole result.
    """
    path = config.path("data_processed") / "importer_exposure_summary.csv"
    d = pd.read_csv(path)
    d = d[(d.pre_resolved_voyages >= 15) & (d.post_resolved_voyages >= 15)].copy()
    d["haul_change_pct"] = 100 * (
        (d.post_expanded_m3_nm / d.post_nominal_capacity_m3)
        / (d.pre_expanded_m3_nm / d.pre_nominal_capacity_m3) - 1
    )
    d["exposure"] = d.pre_hormuz_exposure_capacity_share_pct
    d = d[["destination_country", "exposure", "haul_change_pct"]].reset_index(drop=True)

    def spearman(x, y):
        return np.corrcoef(pd.Series(x).rank(), pd.Series(y).rank())[0, 1]

    stats = {
        "n": len(d),
        "pearson": float(np.corrcoef(d.exposure, d.haul_change_pct)[0, 1]),
        "spearman": float(spearman(d.exposure, d.haul_change_pct)),
        "leave_one_out": {},
    }
    for i, row in d.iterrows():
        m = d.drop(i)
        stats["leave_one_out"][row.destination_country] = float(
            np.corrcoef(m.exposure, m.haul_change_pct)[0, 1]
        )
    return d.sort_values("exposure", ascending=False), stats


def main() -> None:
    pd.set_option("display.width", 220)
    root = config.ROOT
    pinned_artifact = registry.get_variable(
        PINNED_VARIABLE,
        query={
            "consumer": "scripts/run_revision_and_basin_exploration.py",
            "analysis_scope": "sensitivity_only",
        },
    )
    artifact = registry.get_variable(
        VINTAGE_VARIABLE,
        query={"consumer": "scripts/run_revision_and_basin_exploration.py"},
        allow_sensitivity=True,
    )
    old, new = _load(pinned_artifact.path), _load(artifact.path)

    print("=" * 78)
    print("1. WHERE THE REVISION LANDED (mean-level % change, new vs pinned)")
    print("=" * 78)
    table = revision_by_chokepoint(old, new)
    print(table[[f"{c}_pct" for c in VESSEL_COLUMNS]].round(2).to_string())

    print("\n" + "=" * 78)
    print("2. HORMUZ MEAN-LEVEL REVISION AND AGGREGATE % COLLAPSE")
    print("=" * 78)
    by_year, mean_revision = hormuz_mean_revision_profile(old, new)
    print(by_year.round(3).to_string())
    print()
    print(mean_revision.round(3).to_string(index=False))

    print("\n" + "=" * 78)
    print("3. BASIN ASYMMETRY (restricted Fearnleys data; derived values only)")
    print("=" * 78)
    levels, ratios = basin_asymmetry()
    print(levels.round(1).to_string())
    print()
    print(ratios.round(3).to_string())

    print("\n" + "=" * 78)
    print("4. COUNTRY-LEVEL HAUL GRADIENT (falsification check)")
    print("=" * 78)
    countries, stats = country_haul_gradient()
    print(countries.round(1).to_string(index=False))
    print(f"\nn={stats['n']}  Pearson={stats['pearson']:+.3f}  Spearman={stats['spearman']:+.3f}")
    print("leave-one-out Pearson:")
    for k, v in sorted(stats["leave_one_out"].items(), key=lambda kv: kv[1]):
        print(f"   drop {k:14s} r={v:+.3f}")

    out_dir = config.path("data_processed")
    table.to_csv(out_dir / "revision_by_chokepoint.csv")
    countries.to_csv(out_dir / "country_haul_gradient.csv", index=False)
    print(f"\nwrote {out_dir / 'revision_by_chokepoint.csv'}")
    print(f"wrote {out_dir / 'country_haul_gradient.csv'}")

    print("\n=== interpretation guard ===")
    print(" - All four blocks are DESCRIPTIVE. None identifies a causal effect.")
    print(" - Block 3 uses restricted provenance-limited data: no ATT, no causal")
    print("   freight claim, no identified mediation (docs/DATA_SOURCES.md).")
    print(" - Block 4 is reported as a NULL: the gradient is carried by one country.")


if __name__ == "__main__":
    main()
