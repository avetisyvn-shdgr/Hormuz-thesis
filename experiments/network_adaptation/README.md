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
.venv/bin/python -m experiments.network_adaptation.specification_sensitivity
MPLBACKEND=Agg .venv/bin/python -m experiments.network_adaptation.cape_residual_drift
.venv/bin/python -m experiments.network_adaptation.control_robustness
MPLBACKEND=Agg .venv/bin/python -m experiments.network_adaptation.all_corridor_ranking
.venv/bin/python -m pytest -q tests/test_network_adaptation.py
```

Neither diagnostic refits anything.

`specification_sensitivity` reads the event forecasts alongside the older
`panel_aligned.csv` counterfactual artifacts and reports the Hormuz 130-day
shortfall under both training-information sets, because the sign of the
Chronos-versus-AR difference depends on which one is used. Any shortfall figure
quoted from this project must carry its training window.

`cape_residual_drift` reads the eight pre-event 130-day residual vectors and
tests whether the December 2023 Red Sea diversion left the Cape corridor's
residual process non-stationary, which would make both its 2026 counterfactual
and its bootstrap reference unreliable. It did. Cape is reported as context
rather than as corroborative evidence, and the finding rests on Panama and
Yucatan.

`control_robustness` re-runs the global family tests under a pre-declared
minimum-volume eligibility rule, two pre-event weighting schemes and every
leave-one-out refit, on the same seeds and the same synchronized bootstrap. Two
results matter. The Chronos specificity finding holds in 41 of 42 control cells,
and the control family is shown to have the power to flag a control-class
movement the size of the tanker anomaly. But the apparent Chronos-versus-AR
difference in specificity does not survive: it is an artifact of equal-weighting
three very low-volume Ro-Ro series, and both models pass once the family is
weighted or volume-restricted. The equal-weighted global tanker screen is
likewise weighting-sensitive. The corridor-level Panama and Yucatan results do
not depend on family weighting at all, and they are what the chapter rests on.

`all_corridor_ranking` is disclosure, not inference repair. It ranks all 28
chokepoints with Romano-Wolf adjusted over the full family rather than the chosen
five, so "why these five?" can be answered with a table instead of an argument.
Panama and Yucatan clear the threshold in every model-by-block cell; Gibraltar
and Malacca rank 26th and 27th; three corridors nobody selected clear it
somewhere. Every artifact it writes is labelled retrospective.

Multiplicity is controlled inside each named family at one (model, block length)
cell, and nowhere wider. The project-level decision surface — every test in this
experiment, the positive control and the panel bake-off, counted once — is stated
in section 4.1 of `docs/NETWORK_ADAPTATION_SECONDARY_CHAPTER.md` and is not
restated anywhere else.

Configuration: `config/network_adaptation.yaml`. Generated artifacts are under
`experiments/network_adaptation/outputs/`; publication figures are written to
`reports/figures/`.
