"""Render the aligned-window change in the modeled LNG route network."""
from __future__ import annotations

import hashlib
import json
import math
import os
import sys
from pathlib import Path
from typing import Iterable

os.environ.setdefault("MPLCONFIGDIR", "/tmp/lngfreight-matplotlib")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import matplotlib.patheffects as path_effects  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from figure_style import (  # noqa: E402
    DECREASE_COLOR,
    FIGURE_WIDTH_IN,
    INCREASE_COLOR,
    NEUTRAL_DARK,
    NEUTRAL_MID,
    apply_publication_style,
    save_pdf_and_png,
)
from lngfreight import config  # noqa: E402
from lngfreight.registry import RegisteredArtifact, get_variable  # noqa: E402
from lngfreight.routes import installed_searoute_version, searoute_router  # noqa: E402


PAIR_COLUMNS = [
    "project_id",
    "terminal_name",
    "terminal_lat",
    "terminal_lon",
    "destination_project_id",
    "destination_terminal_name",
    "destination_terminal_lat",
    "destination_terminal_lon",
]
PRIMARY_RADIUS_KM = 30
VALUE_COLUMN = "inferred_nominal_m3_nm_expanded"
LOSS_COLOR = DECREASE_COLOR
GAIN_COLOR = INCREASE_COLOR
OBSERVED_COLOR = NEUTRAL_DARK
CORRIDOR_COORDINATES = {
    "strait_of_hormuz": (56.3, 26.5),
    "cape_of_good_hope": (18.5, -34.4),
    "panama_canal": (-79.7, 9.1),
    "yucatan_channel": (-86.9, 21.5),
}
CORRIDOR_LABELS = {
    "strait_of_hormuz": "Hormuz",
    "cape_of_good_hope": "Cape",
    "panama_canal": "Panama",
    "yucatan_channel": "Yucatán",
}
CORRIDOR_ANNOTATION_OFFSETS = {
    "strait_of_hormuz": (10, 14),
    "cape_of_good_hope": (12, -18),
    "panama_canal": (-30, -23),
    "yucatan_channel": (-62, 17),
}
ROBINSON_X = np.asarray([
    1.0000, 0.9986, 0.9954, 0.9900, 0.9822, 0.9730, 0.9600,
    0.9427, 0.9216, 0.8962, 0.8679, 0.8350, 0.7986, 0.7597,
    0.7186, 0.6732, 0.6213, 0.5722, 0.5322,
])
ROBINSON_Y = np.asarray([
    0.0000, 0.0620, 0.1240, 0.1860, 0.2480, 0.3100, 0.3720,
    0.4340, 0.4958, 0.5571, 0.6176, 0.6769, 0.7346, 0.7903,
    0.8435, 0.8936, 0.9394, 0.9761, 1.0000,
])


def primary_route_sample(voyages: pd.DataFrame) -> pd.DataFrame:
    """Return the frozen 30 km, expanded-route-QA mechanism sample."""
    required = set(
        PAIR_COLUMNS
        + ["sample_period", "terminal_match_radius_km", VALUE_COLUMN]
    )
    missing = required.difference(voyages.columns)
    if missing:
        raise ValueError(f"Voyage artifact missing columns: {sorted(missing)}")
    sample = voyages.loc[
        voyages["terminal_match_radius_km"].eq(PRIMARY_RADIUS_KM)
        & voyages[VALUE_COLUMN].notna()
    ].copy()
    periods = set(sample["sample_period"].unique())
    if periods != {"pre", "post"}:
        raise ValueError(f"Expected pre/post sample periods, found {sorted(periods)}.")
    return sample


def aggregate_pair_changes(sample: pd.DataFrame) -> pd.DataFrame:
    """Aggregate nominal capacity-distance and calculate post-minus-pre changes."""
    period = (
        sample.groupby(PAIR_COLUMNS + ["sample_period"], dropna=False)[VALUE_COLUMN]
        .agg(voyage_count="size", capacity_distance_m3_nm="sum")
        .reset_index()
    )
    values = period.pivot(
        index=PAIR_COLUMNS,
        columns="sample_period",
        values="capacity_distance_m3_nm",
    ).fillna(0.0)
    counts = period.pivot(
        index=PAIR_COLUMNS,
        columns="sample_period",
        values="voyage_count",
    ).fillna(0).astype(int)
    output = values.rename(
        columns={
            "pre": "pre_capacity_distance_m3_nm",
            "post": "post_capacity_distance_m3_nm",
        }
    )
    output = output.join(
        counts.rename(columns={"pre": "pre_voyages", "post": "post_voyages"})
    ).reset_index()
    output["change_capacity_distance_m3_nm"] = (
        output["post_capacity_distance_m3_nm"]
        - output["pre_capacity_distance_m3_nm"]
    )
    output["change_capacity_distance_bn_m3_nm"] = (
        output["change_capacity_distance_m3_nm"] / 1e9
    )
    return output.sort_values(
        "change_capacity_distance_m3_nm"
    ).reset_index(drop=True)


def split_at_dateline(coordinates: Iterable[Iterable[float]]) -> list[np.ndarray]:
    """Split a LineString where adjacent longitudes cross the dateline."""
    array = np.asarray(list(coordinates), dtype=float)
    if array.ndim != 2 or array.shape[1] != 2 or len(array) < 2:
        raise ValueError("Route geometry must contain at least two [lon, lat] points.")
    breaks = np.where(np.abs(np.diff(array[:, 0])) > 180)[0] + 1
    return [segment for segment in np.split(array, breaks) if len(segment) >= 2]


def robinson_project(
    longitudes: Iterable[float] | float,
    latitudes: Iterable[float] | float,
) -> tuple[np.ndarray, np.ndarray]:
    """Project longitude/latitude coordinates with the Robinson coefficient table."""
    longitude = np.asarray(longitudes, dtype=float)
    latitude = np.asarray(latitudes, dtype=float)
    longitude, latitude = np.broadcast_arrays(longitude, latitude)
    absolute_latitude = np.clip(np.abs(latitude), 0.0, 90.0)
    table_latitudes = np.arange(0.0, 91.0, 5.0)
    x_coefficient = np.interp(
        absolute_latitude,
        table_latitudes,
        ROBINSON_X,
    )
    y_coefficient = np.interp(
        absolute_latitude,
        table_latitudes,
        ROBINSON_Y,
    )
    projected_x = 0.8487 * np.deg2rad(longitude) * x_coefficient
    projected_y = 1.3523 * np.sign(latitude) * y_coefficient
    return projected_x, projected_y


def _iter_polygon_rings(geometry: dict) -> Iterable[list[list[float]]]:
    if geometry["type"] == "Polygon":
        polygons = [geometry["coordinates"]]
    elif geometry["type"] == "MultiPolygon":
        polygons = geometry["coordinates"]
    else:
        return
    for polygon in polygons:
        if polygon:
            yield polygon[0]


def _draw_land(ax: plt.Axes, geojson_path: Path) -> None:
    payload = json.loads(geojson_path.read_text())
    for feature in payload["features"]:
        for ring in _iter_polygon_rings(feature["geometry"]):
            coordinates = np.asarray(ring, dtype=float)
            projected_x, projected_y = robinson_project(
                coordinates[:, 0],
                coordinates[:, 1],
            )
            ax.fill(
                projected_x,
                projected_y,
                facecolor="#EAE7E1",
                edgecolor="#BEB9B0",
                linewidth=0.32,
                zorder=1,
            )


def _draw_graticule(ax: plt.Axes) -> None:
    longitude_grid = np.linspace(-180.0, 180.0, 721)
    latitude_grid = np.linspace(-60.0, 80.0, 281)
    for latitude in (-60.0, -30.0, 0.0, 30.0, 60.0):
        projected_x, projected_y = robinson_project(
            longitude_grid,
            latitude,
        )
        ax.plot(
            projected_x,
            projected_y,
            color="#CAD6DC",
            linewidth=0.42,
            linestyle=":",
            zorder=0,
        )
    for longitude in (-120.0, -60.0, 0.0, 60.0, 120.0):
        projected_x, projected_y = robinson_project(
            longitude,
            latitude_grid,
        )
        ax.plot(
            projected_x,
            projected_y,
            color="#CAD6DC",
            linewidth=0.42,
            linestyle=":",
            zorder=0,
        )

    label_effect = [
        path_effects.withStroke(linewidth=2.0, foreground="white")
    ]
    for latitude in (-60.0, -30.0, 0.0, 30.0, 60.0):
        projected_x, projected_y = robinson_project(-180.0, latitude)
        latitude_label = (
            "0°"
            if latitude == 0
            else f"{abs(latitude):.0f}°{'N' if latitude > 0 else 'S'}"
        )
        text = ax.annotate(
            latitude_label,
            (float(projected_x), float(projected_y)),
            xytext=(-7, 0),
            textcoords="offset points",
            ha="right",
            va="center",
            fontsize=8.8,
            color=NEUTRAL_DARK,
            annotation_clip=False,
            zorder=6,
        )
        text.set_path_effects(label_effect)
    for longitude in (-120.0, -60.0, 0.0, 60.0, 120.0):
        projected_x, projected_y = robinson_project(longitude, -60.0)
        longitude_label = (
            "0°"
            if longitude == 0
            else f"{abs(longitude):.0f}°{'E' if longitude > 0 else 'W'}"
        )
        text = ax.annotate(
            longitude_label,
            (float(projected_x), float(projected_y)),
            xytext=(0, -8),
            textcoords="offset points",
            ha="center",
            va="top",
            fontsize=8.8,
            color=NEUTRAL_DARK,
            annotation_clip=False,
            zorder=6,
        )
        text.set_path_effects(label_effect)


def _line_width(value_bn: float, cap_bn: float) -> float:
    scaled = min(abs(value_bn), cap_bn) / cap_bn
    return 0.16 + 2.30 * math.sqrt(scaled)


def _line_alpha(value_bn: float, cap_bn: float) -> float:
    scaled = min(abs(value_bn), cap_bn) / cap_bn
    return 0.045 + 0.67 * (scaled ** 0.70)


def _corridor_markers(corridors: pd.DataFrame) -> pd.DataFrame:
    selected = corridors.loc[
        corridors["target"].eq("n_tanker")
        & corridors["corridor"].isin(CORRIDOR_COORDINATES)
    ].copy()
    if set(selected["corridor"]) != set(CORRIDOR_COORDINATES):
        missing = set(CORRIDOR_COORDINATES).difference(selected["corridor"])
        raise ValueError(f"Missing corridor results for {sorted(missing)}.")
    selected["longitude"] = selected["corridor"].map(
        lambda corridor: CORRIDOR_COORDINATES[corridor][0]
    )
    selected["latitude"] = selected["corridor"].map(
        lambda corridor: CORRIDOR_COORDINATES[corridor][1]
    )
    return selected


def _route_geometries(
    pairs: pd.DataFrame,
    *,
    units: str,
    restrictions: list[str],
) -> tuple[dict[tuple[str, str], list[list[float]]], float]:
    geometries: dict[tuple[str, str], list[list[float]]] = {}
    max_distance_difference_nm = 0.0
    voyage_path = (
        config.ROOT
        / config.settings()["paths"]["inferred_capacity_nm_voyages_csv"]
    )
    persisted = primary_route_sample(pd.read_csv(voyage_path))
    distance_lookup = (
        persisted.groupby(
            ["project_id", "destination_project_id"]
        )["modeled_route_nm"]
        .first()
        .to_dict()
    )
    for row in pairs.itertuples(index=False):
        route = searoute_router(
            (float(row.terminal_lon), float(row.terminal_lat)),
            (
                float(row.destination_terminal_lon),
                float(row.destination_terminal_lat),
            ),
            units=units,
            restrictions=restrictions,
        )
        key = (str(row.project_id), str(row.destination_project_id))
        expected_distance = float(distance_lookup[key])
        difference = abs(float(route["distance_nm"]) - expected_distance)
        max_distance_difference_nm = max(max_distance_difference_nm, difference)
        if difference > 0.1:
            raise RuntimeError(
                f"Recomputed route distance differs from frozen artifact by "
                f"{difference:.3f} nm for {key}."
            )
        geometries[key] = route["coordinates"]
    return geometries, max_distance_difference_nm


def _render_map(
    pairs: pd.DataFrame,
    geometries: dict[tuple[str, str], list[list[float]]],
    corridors: pd.DataFrame,
    land_path: Path,
    png_path: Path,
    pdf_path: Path,
) -> float:
    apply_publication_style()
    absolute_change = pairs["change_capacity_distance_bn_m3_nm"].abs()
    cap_bn = float(absolute_change.quantile(0.95))
    if not math.isfinite(cap_bn) or cap_bn <= 0:
        raise ValueError("Route changes do not contain a positive plotting scale.")

    fig, ax = plt.subplots(figsize=(FIGURE_WIDTH_IN, 4.05))
    fig.subplots_adjust(
        left=0.065,
        right=0.992,
        bottom=0.24,
        top=0.78,
    )
    fig.patch.set_facecolor("white")
    ax.set_facecolor("#F5F9FB")
    _draw_graticule(ax)
    _draw_land(ax, land_path)

    losses = pairs.loc[
        pairs["change_capacity_distance_bn_m3_nm"].lt(0)
    ].copy()
    gains = pairs.loc[
        pairs["change_capacity_distance_bn_m3_nm"].gt(0)
    ].copy()
    draw_layers = (
        losses.reindex(
            losses["change_capacity_distance_bn_m3_nm"].abs().sort_values().index
        ),
        gains.reindex(
            gains["change_capacity_distance_bn_m3_nm"].abs().sort_values().index
        ),
    )
    for layer_index, layer in enumerate(draw_layers):
        for row in layer.itertuples(index=False):
            value_bn = float(row.change_capacity_distance_bn_m3_nm)
            color = GAIN_COLOR if value_bn > 0 else LOSS_COLOR
            line_style = (0, (4.0, 1.8)) if value_bn > 0 else "-"
            key = (str(row.project_id), str(row.destination_project_id))
            for segment in split_at_dateline(geometries[key]):
                projected_x, projected_y = robinson_project(
                    segment[:, 0],
                    segment[:, 1],
                )
                ax.plot(
                    projected_x,
                    projected_y,
                    color=color,
                    linewidth=_line_width(value_bn, cap_bn),
                    alpha=_line_alpha(value_bn, cap_bn),
                    linestyle=line_style,
                    solid_capstyle="round",
                    dash_capstyle="round",
                    zorder=2.0 + (0.15 * layer_index),
                )

    for row in corridors.itertuples(index=False):
        marker_x, marker_y = robinson_project(row.longitude, row.latitude)
        ax.scatter(
            marker_x,
            marker_y,
            marker="D",
            s=30,
            facecolor="white",
            edgecolor=OBSERVED_COLOR,
            linewidth=1.15,
            zorder=4,
        )
        label = (
            f"{CORRIDOR_LABELS[row.corridor]} "
            f"{row.signed_deviation:+.0%}"
        )
        ax.annotate(
            label,
            (float(marker_x), float(marker_y)),
            xytext=CORRIDOR_ANNOTATION_OFFSETS[row.corridor],
            textcoords="offset points",
            fontsize=8.8,
            color=OBSERVED_COLOR,
            weight="bold",
            arrowprops={
                "arrowstyle": "-",
                "color": OBSERVED_COLOR,
                "linewidth": 0.55,
                "shrinkA": 2,
                "shrinkB": 3,
            },
            zorder=5,
        ).set_path_effects([
            path_effects.withStroke(linewidth=2.8, foreground="white")
        ])

    x_limit = float(robinson_project(180.0, 0.0)[0])
    y_min = float(robinson_project(0.0, -60.0)[1])
    y_max = float(robinson_project(0.0, 80.0)[1])
    ax.set_xlim(-x_limit, x_limit)
    ax.set_ylim(y_min, y_max)
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)

    fig.suptitle(
        "Modeled LNG route-network change",
        x=0.065,
        y=0.96,
        ha="left",
        fontsize=13.0,
        fontweight="semibold",
        color=NEUTRAL_DARK,
    )
    fig.text(
        0.065,
        0.875,
        (
            "Modeled post-minus-pre aggregate nominal capacity-distance; "
            "equal 94-day windows, 30 km expanded-QA sample"
        ),
        ha="left",
        va="bottom",
        fontsize=10.0,
        color=NEUTRAL_MID,
    )
    legend_handles = [
        Line2D(
            [0],
            [0],
            color=LOSS_COLOR,
            linewidth=2.0,
            linestyle="-",
            label="Modeled pair-level decrease",
        ),
        Line2D(
            [0],
            [0],
            color=GAIN_COLOR,
            linewidth=2.0,
            linestyle=(0, (4.0, 1.8)),
            label="Modeled pair-level increase",
        ),
        Line2D(
            [0],
            [0],
            color=OBSERVED_COLOR,
            marker="D",
            markerfacecolor="white",
            markeredgewidth=1.1,
            markersize=5.3,
            linewidth=0,
            label="Observed PortWatch corridor deviation",
        ),
    ]
    fig.legend(
        handles=legend_handles,
        loc="lower center",
        bbox_to_anchor=(0.50, 0.085),
        frameon=False,
        ncol=3,
        fontsize=9.0,
        handlelength=2.6,
        columnspacing=1.25,
    )
    fig.text(
        0.992,
        0.025,
        (
            "Modeled-flow line width scales with |change| and is capped at "
            "the pair-level p95 for legibility."
        ),
        ha="right",
        va="bottom",
        fontsize=8.5,
        color=NEUTRAL_MID,
    )
    save_pdf_and_png(
        fig,
        png_path,
        pdf_path=pdf_path,
    )
    plt.close(fig)
    return cap_bn


def main() -> None:
    settings = config.settings()
    paths = settings["paths"]
    policy = settings["vessel_data_feasibility"]["route_distance"]
    engine_version = installed_searoute_version()
    if engine_version != str(policy["engine_version"]):
        raise RuntimeError(
            f"Configured searoute {policy['engine_version']}, "
            f"installed {engine_version}."
        )

    voyage_path = config.ROOT / paths["inferred_capacity_nm_voyages_csv"]
    sample = primary_route_sample(pd.read_csv(voyage_path))
    pairs = aggregate_pair_changes(sample)
    geometries, max_distance_difference_nm = _route_geometries(
        pairs,
        units=str(policy["units"]),
        restrictions=list(policy["restrictions"]),
    )
    corridor_path = config.ROOT / paths["corridor_transmission_results_csv"]
    corridors = _corridor_markers(pd.read_csv(corridor_path))
    land_artifact = get_variable(
        "natural_earth_land_snapshot",
        query={"consumer": "make_route_map"},
    )
    if not isinstance(land_artifact, RegisteredArtifact):
        raise TypeError("natural_earth_land_snapshot must resolve as an artifact")
    land_path = land_artifact.path
    png_path = config.ROOT / paths["modeled_route_network_change_png"]
    pdf_path = config.ROOT / paths["modeled_route_network_change_pdf"]
    cap_bn = _render_map(
        pairs,
        geometries,
        corridors,
        land_path,
        png_path,
        pdf_path,
    )

    output_csv = config.ROOT / paths["modeled_route_network_change_csv"]
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    pairs.to_csv(output_csv, index=False)
    windows = settings["vessel_data_feasibility"][
        "wto_departure_validation"
    ]["comparison_windows"]
    unique_pair_counts = {
        period: int(len(frame[PAIR_COLUMNS].drop_duplicates()))
        for period, frame in sample.groupby("sample_period")
    }
    manifest = {
        "figure": str(png_path.relative_to(config.ROOT)),
        "route_engine": str(policy["engine"]),
        "route_engine_version": engine_version,
        "route_units": str(policy["units"]),
        "route_restrictions": list(policy["restrictions"]),
        "sample_filter": {
            "terminal_match_radius_km": PRIMARY_RADIUS_KM,
            "route_qa": f"{VALUE_COLUMN} is non-null",
            "pre_window": windows["pre"],
            "post_window": windows["post"],
        },
        "voyage_counts": (
            sample.groupby("sample_period").size().astype(int).to_dict()
        ),
        "unique_pair_counts": unique_pair_counts,
        "union_unique_pairs": int(len(pairs)),
        "aggregate_capacity_distance_bn_m3_nm": (
            sample.groupby("sample_period")[VALUE_COLUMN]
            .sum()
            .div(1e9)
            .to_dict()
        ),
        "max_recomputed_route_distance_difference_nm": (
            max_distance_difference_nm
        ),
        "line_width_cap_bn_m3_nm": cap_bn,
        "basemap": {
            "file": str(land_path.relative_to(config.ROOT)),
            "sha256": hashlib.sha256(land_path.read_bytes()).hexdigest(),
            "license": "Natural Earth public domain",
        },
        "observed_marker_source": str(corridor_path.relative_to(config.ROOT)),
        "limitations": [
            (
                "Route geometry is modeled shortest-sea-route output, "
                "not sailed AIS tracks."
            ),
            (
                "Terminal-sequence inference and right-censoring propagate "
                "into the drawn network."
            ),
            (
                "Line width represents nominal capacity-distance change, "
                "not cargo."
            ),
            (
                "PortWatch markers are an independent observed corridor layer "
                "and do not trace the routed voyages."
            ),
        ],
    }
    manifest_path = (
        config.ROOT / paths["modeled_route_network_change_manifest_json"]
    )
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    )
    print(f"wrote {output_csv}")
    print(f"wrote {manifest_path}")
    print(f"wrote {png_path}")
    print(f"wrote {pdf_path}")
    print(
        f"sample voyages pre={manifest['voyage_counts']['pre']} "
        f"post={manifest['voyage_counts']['post']}; pairs={len(pairs)}"
    )


if __name__ == "__main__":
    main()
