# Corridor-panel model admission protocol

**Status:** Frozen technical proposal, pending Prof. Li approval. No real panel
benchmark or post-cutoff corridor inspection is authorized by this document.
The machine-readable source of truth is `config/corridor_transmission.yaml`.

## Comparison unit

The comparison is paired at corridor × target × shared rolling-origin fold.
Candidate and AR-only score tables must contain exactly the same keys and number
of scored observations. This prevents a model from improving its verdict by
dropping difficult folds or corridors.

The common history begins `2022-01-01`, the cutoff is exclusively
`2026-02-28`, and the fold geometry remains expanding 365-day initial training,
30-day horizon and 30-day step. Admission uses the 23 folds with at least 15
strictly earlier folds available to construct the raw AR interval: `fold_16`
through `fold_38`. All three candidates and AR-only are evaluated at the common
80% central interval (`q0.10`–`q0.90`).

## Eligibility rule

A corridor-target series must have at least 24 observed/scorable days in every
admission fold. Under the pinned PortWatch snapshot and the existing rule that
masks capacity zero when tanker transits are positive, this admits all 28
`n_tanker` corridors and 20 `capacity_tanker` corridors. The exact lists are
frozen in the YAML. Excluded capacity corridors remain visible in the panel
audit; exclusion is a missingness decision, not evidence about model quality.

## MASE gate

For each corridor, average MASE across the 23 identical folds and calculate

`relative improvement = (AR MASE − candidate MASE) / AR MASE`.

Each target family passes only when:

1. median corridor relative improvement is at least 5%; and
2. at least 60% of its corridors are non-worse than AR-only.

The 5% threshold operationalizes “material” improvement; it is a judgement, not
an estimated law. The breadth requirement prevents a large gain on a few busy
corridors from hiding deterioration across most of the panel.

## Calibration gate

For each corridor, pool coverage across folds using `n_scored` as weights, then
take the absolute difference from the common 80% nominal level. Signed errors
are never averaged because overcoverage and undercoverage would cancel.

Each target family passes only when all three conditions hold:

1. candidate median absolute calibration error is no greater than 10 points;
2. it is no more than 2 points worse than the matched AR median error; and
3. at least 80% of corridors achieve empirical coverage of at least 70%.

The first condition is an absolute quality ceiling, the second is a
non-inferiority comparison, and the third prevents acceptable median calibration
from hiding severe undercoverage in a substantial minority of corridors.

## Final verdict

The candidate receives one panel-level admission only if **both** tanker-count
and tanker-capacity target families pass both gates. There are no
corridor-specific admissions. Passing makes a model eligible for a descriptive
post-period robustness run; it does not replace AR-only or identify a causal
effect.

Before approval, Prof. Li should explicitly accept or revise the 5%, 60%, 10
point, 2 point, 70% and 80% thresholds. Any revision must change the YAML and
tests before the real scores are generated.
