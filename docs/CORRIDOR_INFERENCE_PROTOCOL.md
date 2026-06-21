# Corridor shared-placebo inference protocol

**Status:** Frozen technical proposal, pending Prof. Li approval. This protocol
does not authorize a real corridor run or inspection of post-cutoff deviations.
Its machine-readable source is the `inference` block in
`config/corridor_transmission.yaml`.

## Statistic and sign

For corridor `i` and window `w`, define

`D(i,w) = mean(observed − counterfactual) / pre-period mean observed throughput`.

Negative values mean below-counterfactual throughput; positive values mean
above-counterfactual throughput. The denominator is calculated from that
corridor's own pre-origin training history. This is a dimensionless descriptive
deviation, not a flow reallocation measure.

Because the map reports both positive and negative deviations, inference is
two-sided. Studentization uses the standard deviation across the shared placebo
draws for each hypothesis. The implementation centers each raw placebo column
before taking the absolute standardized statistic; taking absolute values first
would estimate the wrong two-sided null.

## Multiplicity family

The only primary inferential family is AR-only across every eligible corridor
and both target families:

- 28 `n_tanker` hypotheses;
- 20 `capacity_tanker` hypotheses;
- 48 hypotheses in one Romano–Wolf family.

This single family prevents separate target corrections from understating the
number of reported corridor claims. Foundation models do not create additional
hypothesis tests: they remain descriptive robustness maps. Adding inferential
claims for model variants would require a new family specification frozen before
viewing those results.

## Shared placebo draws

The primary joint null uses nine mutually disjoint 94-day windows shared across
all 48 hypotheses. Each origin produces one complete vector of corridor-target
statistics. Rows are never independently permuted by corridor. The 36 aligned
94-day windows stepped every 30 days may be reported only as an overlapping
sensitivity analysis, not as the primary Romano–Wolf input.

Every corridor-window statistic must contain at least 76 valid days (80% of the
94-day horizon). All frozen eligible corridors pass this rule in all nine
primary windows; the minimum is 81 valid days for capacity and 94 for counts.

With nine primary joint draws, the finite-sample p-value floor is `1/(9+1) =
0.10`. Therefore this design cannot support an adjusted 5% rejection. That is a
property of the available independent historical windows, not a software defect.
Report adjusted p-values as coarse reference measures alongside separation and
rank, without significance language.

## Basin uncertainty decision

The protocol authorizes basin point summaries only. It does not authorize a
basin prediction or confidence interval because:

1. marginal corridor quantiles do not supply joint predictive paths;
2. a shared-placebo null distribution is not automatically an interval; and
3. summing chokepoints may double-count traffic unless the basin estimand and
   corridor topology are explicitly resolved.

Any displayed placebo distribution must be labelled
`placebo_reference_not_interval`. A future basin interval requires a separate
estimand, construction and simulation coverage study before real results are
viewed.

This point-only decision is now backed by a coverage simulation rather than
theory alone. Under the realistic design — nine shared placebo draws, positively
correlated corridors and chokepoint double counting — no candidate basin
interval reaches its stated 0.80 coverage; the best achieved is 0.72 and the
covariance-aware joint method falls to 0.59. See
`docs/BASIN_INTERVAL_COVERAGE_RESULTS.md` and `src/lngfreight/basin_coverage.py`.

## Required implementation checks

The code must reject missing hypotheses, missing origins, duplicate
corridor-origin rows, changed family membership, non-finite values, wrong
horizons, zero-variance studentization and foundation-model rows. The long-form
origin key is preserved through pivoting so the joint dependence structure is
auditable.
