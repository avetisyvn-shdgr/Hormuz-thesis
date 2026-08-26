# Upgrading the route-map basemap from Natural Earth 110m to 50m

Status: **proposed, not executed.** The plotting code in
`scripts/make_route_map.py` is resolution-agnostic — it resolves the basemap
through the `natural_earth_land_snapshot` registry entry — so this upgrade is
a data-provenance change, not a code change. It touches the reproducibility
freeze, which is why it is written up as a runbook rather than applied.

## Why

`data/raw/natural_earth/ne_110m_land.geojson` is the 1:110 million Natural
Earth land layer: 138 KB, 127 features. It is intended for thumbnails. The
route map is printed 7.2 in wide and scaled to a 418 pt text block, at which
size the generalization is visible — the Caribbean, the Aegean, the Malay
archipelago and the Norwegian coast reduce to lumps, and modeled sea routes
can appear to cross land because the coastline is drawn inland of where
`searoute` actually routed around it.

The 1:50 million layer is roughly 10x the vertex density and is the standard
choice for a single-page world map.

## What this does NOT change

- No route geometry, distance, sample filter, or numeric result.
- No figure semantics; the LaTeX caption in
  `chapters/07_results_mechanism.tex` stays valid as written.
- The only value in `modeled_route_network_change_manifest.json` that moves is
  `basemap.file` / `basemap.sha256`.

## Steps

### 1. Download the file

Natural Earth is public domain. The canonical mirror used by the project's
existing 110m snapshot is the `nvkelso/natural-earth-vector` repository:

```
https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_50m_land.geojson
```

Save it to:

```
lng_freight_thesis/data/raw/natural_earth/ne_50m_land.geojson
```

Expect roughly 1.4–1.6 MB and ~1,400 features. If the file is under 200 KB you
have downloaded the HTML page rather than the raw asset.

### 2. Record the hash

```bash
cd lng_freight_thesis
shasum -a 256 data/raw/natural_earth/ne_50m_land.geojson
python3 -c "import json;d=json.load(open('data/raw/natural_earth/ne_50m_land.geojson'));print('features',len(d['features']))"
```

Paste both outputs back before continuing — the feature count is the sanity
check that the download is the land layer and not `ne_50m_coastline` (which is
LineString, not Polygon, and would render nothing).

### 3. Point the registry at it

`config/sources.yaml`, entry `natural_earth_land_snapshot`:

```yaml
  natural_earth_land_snapshot:
    kind: artifact
    role: artifact
    description: "Natural Earth 50m land boundary used for route-map context."
    status: free
    primary:
      provider: frozen_artifact
      path: "data/raw/natural_earth/ne_50m_land.geojson"
      media_type: "application/geo+json"
      license: "Natural Earth public domain"
```

`config/settings.yaml`, line 119:

```yaml
  natural_earth_land_geojson: "data/raw/natural_earth/ne_50m_land.geojson"
```

Keep the 110m file in the repository. It is small, it is the frozen input for
every prior build, and deleting it would break reproduction of the current
committed figure.

### 4. Regenerate and re-freeze

Per the standing rule from the 2026-06-21 determinism post-mortem, regenerate
through `run_all.py` (which pins the seed) rather than ad hoc, then re-freeze:

```bash
python scripts/run_all.py
python scripts/freeze_reproducibility.py
python scripts/freeze_reproducibility.py --check
```

Then copy the figure into the manuscript and rebuild:

```bash
cp reports/figures/modeled_route_network_change.pdf \
   ../TUM_Bachelor_Thesis/figures/
cd ../TUM_Bachelor_Thesis && latexmk -pdf -outdir=build main.tex
```

### 5. If the render regresses

Two things to look at, in order:

- **Slow render or bloated PDF.** 50m has ~10x the vertices and
  `path.simplify` is set to `False` in `figure_style.apply_publication_style()`
  for determinism. If the vector PDF becomes unwieldy, do not enable
  simplification globally — it would perturb every other figure. Drop features
  below a minimum projected area inside `_draw_land` instead, and record the
  threshold in the manifest.
- **Lakes filled as land.** Should not occur — `_polygon_path` now builds a
  compound path so interior rings cut holes — but 50m is the first snapshot
  with a meaningful number of them, so check the Caspian and the Great Lakes.
