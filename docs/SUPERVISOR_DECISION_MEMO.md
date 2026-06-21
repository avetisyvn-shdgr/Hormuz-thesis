# Supervisor decision memo

**To:** Prof. Li  
**From:** [Student name]  
**Date:** [Send date]  
**Subject:** Approval request: revised empirical scope and ML methodology for the Bachelor thesis

## Decision requested

I request approval to finalize the thesis as a counterfactual analysis of the
2026 Strait of Hormuz tanker-throughput disruption using accessible data. This
is the recommended path because it is implementable, reproducible, and consistent
with the guidance to use established machine-learning methods for substantive
insight rather than develop a novel or unusually complex model architecture.

## Why the scope requires formal alignment

The approved proposal uses daily LNG spot-freight rates (Spark25S/30S) as the
dependent variable and proprietary vessel-level AIS data for the ton-mile
mechanism. These data have not been available. The free-data implementation
therefore uses IMF PortWatch daily tanker throughput as a different, adjacent
outcome. It must not be presented as a proxy for LNG freight rates or as the same
estimand.

The revised study asks:

> How large and persistent was the disruption-associated shortfall in observable
> daily tanker throughput through the Strait of Hormuz relative to counterfactual
> paths estimated exclusively from pre-disruption data?

The primary outcome is daily tanker transit count. Deadweight capacity is a
secondary robustness outcome. The estimand is the cumulative and mean-daily
observed-minus-counterfactual throughput gap over a pre-specified post-disruption
window.

## Implemented methodology

The implementation deliberately uses established methods:

- a transparent autoregressive model trained only on pre-disruption data as the
  primary counterfactual estimator;
- chronological rolling-origin validation against a seasonal-naive benchmark;
- long-horizon uncertainty intervals and placebo-in-time inference;
- same-date spatial placebos and donor leave-one-out checks;
- synthetic control and Bayesian structural time series as corroboration;
- modern time-series foundation models only as optional forecast robustness
  benchmarks, not as the primary estimator or evidence of causality.

The pipeline, provenance controls, model tests, and reporting outputs are already
implemented. The current offline test suite passes 214 tests. The working result
is a large disruption-associated throughput shortfall that remains directionally
consistent across the principal robustness checks. These results do not identify
a causal ATT and do not estimate an LNG freight-rate effect.

## Requested decisions

Please approve the following four items, or identify the numbered item that
requires revision:

1. **Outcome and research question:** Replace LNG spot freight with observable
   Hormuz tanker throughput and adopt the revised research question above.
2. **Claim strength:** Report a **disruption-associated counterfactual shortfall**,
   not a causal ATT or a causal LNG freight-rate effect.
3. **Scope of unavailable data:** Treat freight-rate and inter-basin analyses as
   optional extensions only if Spark/Bloomberg access becomes available with
   adequate historical coverage. They will not block completion of the thesis.
4. **ML strategy:** Retain the transparent autoregressive model as the primary
   estimator and use established synthetic-control, BSTS, placebo, and modern
   forecasting methods only for validation and robustness.

## Proposed thesis title

**Counterfactual Estimation of Tanker-Throughput Disruption at the Strait of
Hormuz: Forecasting and Synthetic-Control Evidence from the 2026 Episode**

## Reply format

A short response is sufficient:

- **“Approved as proposed”**, or
- **“Revise item(s) [number]: [requested change]”.**

Until approval is received, I will retain the original formal proposal and treat
the revised title, research question, hypotheses, and estimand as a working draft.

---

## Suggested cover email

**Subject:** Decision required: revised thesis outcome and methodology

Dear Prof. Li,

I have completed the working empirical pipeline using accessible data and now
need to align the formal thesis scope with what the available data can support.
The attached one-page memo proposes a conservative revision that follows your
guidance to use established ML methods for insight rather than build a novel,
overly complex architecture.

Could you please approve the four numbered items in the memo, or indicate which
item requires revision? A reply of “Approved as proposed” or a numbered change is
sufficient. This decision will allow me to keep the title, research question,
methods, and final claims consistent before drafting the thesis chapters.

Kind regards,  
[Student name]
