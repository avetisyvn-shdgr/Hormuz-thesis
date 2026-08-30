# Red Sea positive control

The restricted Hormuz corridor experiment next door is a retrospective screen: an
all-corridor post-event AR map already existed when its five corridors were named.
Romano-Wolf controls multiplicity conditional on the family tested; it cannot
recreate a selection that did not happen.

This experiment runs the identical estimator, bootstrap and multiplicity
machinery on the one event in this panel where the selection *did* happen in
advance. The Cape of Good Hope was designated the receiver of the December 2023
Red Sea diversion on route topology, and the 16-corridor eligible family it is
ranked within was frozen on pre-onset volume, both recorded in
`config/hormuz_receiver_test.yaml` on 2026-08-27 — before any post-onset outcome
was inspected. **This re-run changes the estimator and the inference, never the
designation.**

Held identical to `experiments/network_adaptation`: the Chronos-2 univariate and
recursive AR(1,7) pair, the 130-day horizon, the scaled mean
observed-minus-counterfactual statistic, the synchronized circular moving-block
bootstrap at 7/14/28-day blocks, and Romano-Wolf step-down within explicitly
named families. The historical reference is eight contiguous, disjoint 130-day
out-of-sample origins ending the day before each onset, so it spans exactly 1,040
days and holds no post-onset information.

Both onsets declared in the frozen B2 specification are reported and neither is
the headline. That constraint is inherited, and `validate_protocol` refuses to
load a configuration that names one primary.

## Reproduce

```bash
.venv-bench/bin/python -m experiments.positive_control.run_forecasts
MPLBACKEND=Agg .venv/bin/python -m experiments.positive_control.analyze
.venv/bin/python -m pytest -q tests/test_positive_control.py
```

Configuration: `config/redsea_positive_control.yaml`. Artifacts are under
`experiments/positive_control/outputs/`; the figure is written to
`reports/figures/`.

## What it establishes

The designated receiver ranks first of sixteen at adjusted p=0.0001 in all four
onset-by-model cells and at every block length. The vessel-class controls at that
corridor also fire, which is correct — the diversion rerouted long-haul traffic of
every class around the Cape — and is what makes the same controls' silence in the
Hormuz analysis informative rather than vacuous.

It does not transfer its ex-ante status to the Hormuz corridor screen. It narrows
the objection there to the choice of corridors, rather than leaving open whether
the method can detect a reallocation at all.
