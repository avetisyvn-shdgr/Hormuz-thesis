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
