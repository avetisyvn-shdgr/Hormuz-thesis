# Restricted network-adaptation experiment

This experiment asks whether selected non-Hormuz chokepoints exhibit positive
130-day tanker-count anomalies compatible with network adaptation or
alternative-source substitution. It does **not** identify physical rerouting,
displaced volume, LNG-specific traffic, or a causal effect.

The design improves on the earlier 94-day all-corridor AR map by using:

- the admitted univariate Chronos-2 forecaster as the primary model;
- recursive AR(1,7) as a transparent robustness model;
- the identical 130-day event horizon and pre-event bake-off geometry;
- synchronized circular moving-block resampling of 1,040 genuinely
  out-of-sample historical residual vectors;
- one global family test followed by Romano-Wolf corridor tests; and
- Ro-Ro and dry-bulk outcomes at the same corridors as negative controls.

The five-corridor restriction is retrospective because an earlier post-event AR
map already existed. The configuration is a reproducibility freeze, not a
preregistration, and every output carries that limitation.

## Reproduce

```bash
.venv-bench/bin/python -m experiments.network_adaptation.run_event_forecasts
.venv/bin/python -m experiments.network_adaptation.analyze
.venv/bin/python -m pytest -q tests/test_network_adaptation.py
```

Configuration: `config/network_adaptation.yaml`. Generated artifacts are under
`experiments/network_adaptation/outputs/`; the publication figure is written to
`reports/figures/`.
