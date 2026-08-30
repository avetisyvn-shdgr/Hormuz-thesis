# PortWatch panel bake-off

This directory is an isolated technical experiment. It reads the pinned IMF
PortWatch snapshot directly and does not treat thesis prose or prior result files
as evidence.

The primary panel is 28 chokepoints by five mutually exclusive vessel classes.
`n_cargo` and `n_total` are exact arithmetic aggregates and are therefore not
stacked as a sixth class. Total transits are evaluated separately as a robustness
outcome.

Two information sets are reported separately:

1. **Forecasting:** seasonal-naive, recursive AR(1,7), univariate Chronos-2,
   and multivariate Chronos-2 see only observations before the forecast origin.
2. **Donor-assisted imputation:** synthetic control, Interactive Fixed Effects,
   and nuclear-norm completion may use contemporaneous outcomes at spatial donor
   chokepoints. Complete five-class chokepoint blocks are masked together.

There are eight disjoint origins, 130 days apart, beginning 2023-01-01. Each is
scored at 30 and 130 days and ends before the 2026-02-28 event cutoff. IFE rank
and the nuclear-norm penalty are selected once on a separate 2022 block, then
frozen. Final metrics are macro-averaged over unit-series so large ports cannot
dominate the result.

The executed findings and academic interpretation are in [RESULTS.md](RESULTS.md).

Reproduction order:

```bash
.venv/bin/python -m experiments.panel_bakeoff.run_classical
.venv-bench/bin/python -m experiments.panel_bakeoff.run_chronos
.venv/bin/python -m experiments.panel_bakeoff.summarize
.venv/bin/python -m experiments.panel_bakeoff.stationarity
.venv/bin/python -m experiments.panel_bakeoff.pretraining_contamination
.venv/bin/python -m pytest -q tests/test_panel_bakeoff.py
```

`pretraining_contamination` refits nothing. It re-reads the executed scores and
reports the Chronos-over-AR advantage origin by origin, because Chronos-2 was
released 2025-10-20 and seven of the eight scored windows close before that date.
The event window does not: it lies provably outside any pretraining corpus.
