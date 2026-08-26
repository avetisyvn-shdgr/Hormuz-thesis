# Thesis Figure Restyling Changelog

**Scope:** Three manuscript figures regenerated exclusively through
`scripts/make_run_output.py`, `scripts/make_route_map.py`, and the shared
`scripts/figure_style.py`. No image was edited or post-processed.

## Common publication style

- Arial, matching the TUM thesis body font, with Source Sans 3 and DejaVu Sans
  as deterministic fallbacks.
- Print-scale typography designed for approximately 15 cm final width: 11 pt
  source axis labels and 10 pt source tick labels.
- Consistent 0.65 pt axes and 0.45 pt grids; unnecessary top/right spines
  removed from statistical charts.
- Embedded TrueType fonts in vector PDFs; 300 dpi PNGs retained only as
  previews.
- Stable filenames, fixed ordering, no timestamp metadata, and deterministic
  PDF/PNG output.

## Figure 6.1 — Throughput counterfactual

- Reduced daily-series clutter by plotting observed daily throughput in
  low-alpha gray and adding a trailing seven-day mean in dark gray.
- Preserved the rolling-origin validation path and AR-only counterfactual
  values unchanged.
- Added a separate post-period detail panel with a shared y-axis so the
  throughput collapse remains legible at print size.
- Moved the legend outside the data area and differentiated forecast and cutoff
  lines by dash pattern.
- Retained the exact label **“Short-fold residual band (pointwise)”** and did
  not reintroduce “95%” wording.

## Figure 6.2 — Temporal placebos

- Applied the common typography and axes style and removed unnecessary spines.
- Retained the 14-bin histogram, all 35 placebo values, the placebo p95 marker,
  and the actual-shortfall marker.
- Annotated the actual shortfall once (`6,869`) and the placebo p95 once
  (`2,124`).
- Retained the explicit overlapping-windows warning in the figure:
  “placebo windows overlap; this is a reference distribution, not an
  independent sampling distribution.”

## Figure 7.1 — Modeled route-network change

- Reprojected the complete coastline, graticule, modeled route geometries, and
  observed corridor markers to Robinson projection without changing their
  source coordinates.
- Applied ColorBrewer RdBu anchors: `#B2182B` for modeled decreases and
  `#2166AC` for modeled increases.
- Added solid-versus-dashed encoding so direction remains distinguishable in
  grayscale.
- Reduced the alpha floor for small-absolute-change pairs to limit East Asia
  clutter without suppressing any pair.
- Replaced boxed corridor callouts with transparent text, white contrast
  strokes, and thin leader lines anchored to the corridor diamonds.
- Layered modeled decreases first and modeled increases second so the latter
  remain traceable in dense route clusters.
- Retained observed PortWatch diamonds as a separate shape and legend entry.
- Retained the modeled-flow p95 line-width-cap note and used “modeled” for all
  routed-flow labels.
- Retained the full `searoute` maritime-network polylines rather than replacing
  them with port-to-port geodesics, which would change the represented routing
  mechanism.

## No-numeric-change verification

- `modeled_route_network_change_manifest.json` is byte-for-byte unchanged.
- Pre/post routed voyages remain `948`/`726`; unique pairs remain `405`/`362`;
  the union remains `578`.
- Pre/post aggregate nominal capacity-distance remains
  `628.2448695294609`/`530.1910773338246` billion m³·nm.
- Maximum recomputed-versus-frozen route-distance difference remains
  `1.8189894035458565e-12` nautical miles.
- The hashes of `run_spec_comparison.csv`, `placebo_time_summary.csv`, and
  `corridor_transmission_results.csv` are unchanged.
- Repeating both figure scripts produced identical hashes for all eight
  regenerated PDF/PNG artifacts.
- Full evidence-repository test result: **265 passed**.

## 2026-08-09 — Template-wide serif restyle and full figure embedding

Scope: all thesis-facing figures regenerated through their existing scripts
after a central style change; no image was edited or post-processed.

- `scripts/figure_style.py`: body font switched from Arial to serif
  (P052/URW Palladio, the Palatino clone matching the fwalch TUM template's
  mathpazo body font), with mathtext mapped to the same face.
- All in-figure headline titles removed; the LaTeX caption now carries the
  title. Informative panel labels (A./B./..., "Full series") are retained.
- Bloomberg-layer scripts (`make_bloomberg_freight_descriptives.py`,
  `run_bloomberg_freight_counterfactual.py`,
  `make_bloomberg_mechanism_integration.py`,
  `build_bloomberg_market_context.py`) rebuilt on the shared
  `figure_style` at print width (7.2 in) instead of 12-14 in canvases whose
  text shrank below body size when scaled to \textwidth.
- `make_network_rewiring_summary.py`: legend moved out of the axes (was
  colliding with the pre/post bar labels), stray "value" annotation renamed
  "value basis" and repositioned, Gulf/non-Gulf palette switched to the
  colorblind-safe RdBu pair shared with the route map.
- `make_mechanism_summary.py`: panel-B tick labels shortened and shrunk to
  remove overlap; shared style applied.
- `make_event_study.py` / `eventstudy.py`: serif face added to the local
  style block; assertive suptitle dropped; em dash removed from panel title.
- `make_route_map.py`: in-figure title and subtitle removed.
- Thesis embedding: manuscript now includes 14 figures (was 3):
  event study (ch. 3), market context (ch. 4), mechanism summary +
  freight descriptive + freight counterfactual + synchronized integration
  panel (ch. 7), three network-rewiring figures (ch. 8), synthetic-control
  path and placebo gaps (ch. 9), plus the original throughput, placebo, and
  route-map figures.

## 2026-08-09 — Route-map projection correction

Scope: `scripts/make_route_map.py` only. The Robinson projection was being
rendered incorrectly; no data, sample filter, or route geometry changed.

- **Aspect distortion fixed (primary defect).** `_render_map` never called
  `ax.set_aspect("equal")`, so Matplotlib stretched the axes box to the
  figure. For the plotted extent the projected data ratio is 2.356:1 while the
  axes box was 6.674 in x 2.187 in = 3.052:1, i.e. every landmass was drawn
  **1.296x too wide**. The axes aspect is now locked and the figure height is
  derived from the projected data ratio (margins are specified in inches, see
  `MARGIN_*_IN`) so the correction introduces no whitespace.
- **Projection neatline added.** The ocean was a full-width rectangle, which
  painted sea into the corners lying outside Robinson's curved bounding
  meridians. `_boundary_path()` traces the outline; it now fills the ocean,
  clips land, graticule and flow lines, and is stroked as a neatline.
- **Interior rings render as holes.** `_iter_polygon_rings` kept only
  `polygon[0]` and filled it, so enclosed water bodies were drawn as land.
  Replaced by `_iter_polygons` plus `_polygon_path`, building a compound
  `matplotlib.path.Path`. This is a prerequisite for any higher-resolution
  coastline.
- **Flow strokes retuned** so overlapping pairs stop merging into opaque
  blobs at the East Asian and US Gulf hubs: width cap 2.46 pt -> 1.76 pt,
  alpha ceiling 0.715 -> 0.53, dash caps butt instead of round.
- Land/ocean/graticule palette given more separation; corridor deviation
  labels now use a typographic minus (U+2212) rather than a hyphen.
- Known remaining limitation: the basemap is Natural Earth **110m**
  (`ne_110m_land.geojson`, 1:110 million, 127 features). At 7.2 in width the
  Caribbean, Aegean and Indonesian coastlines are visibly generalized, and
  modeled sea routes can appear to clip land. Upgrading to the 50m snapshot
  is a `sources.yaml` path change plus a re-freeze; the plotting code is
  resolution-agnostic.
