"""Quantify the AIS-dark-vessel bound on the throughput-reduction estimate.

Motivation (FALLBACK_STRATEGY.md, INFERENCE_NOTES.md):
    Under a Hormuz conflict episode, AIS dark activity / GPS jamming / spoofing is
    *correlated with the treatment*, not random noise. Observed transits therefore
    fall by MORE than true transits, concentrated in the treated window, so the
    naive observed-minus-counterfactual loss is a CONDITIONAL UPPER BOUND on the
    true throughput reduction under a one-sided undercount assumption. So far
    that has been stated only qualitatively. This script puts an auditable
    sensitivity number on it.

Transparent identity (no new data, no model fit):
    O  = observed post-period transits (PortWatch, treated window)
    C  = counterfactual post-period transits (AR-only primary, pre-treatment fit)
    d  = treatment-period incremental AIS-dark rate = fraction of the period's
         TRUE transits that PortWatch does NOT observe, OVER AND ABOVE the baseline
         AIS gap-fill already embedded in the pre-treatment counterfactual.

    True transits implied by a dark rate d:   T(d)  = O / (1 - d)
    Observed reduction (the naive estimate):  R_obs = 1 - O / C            (= R_true at d = 0)
    True reduction under d:                   R_true(d) = 1 - O / ((1 - d) * C)
    Critical dark rate to reach a reduction R: d*(R)  = 1 - O / (C * (1 - R))

The naive R_obs is recovered at d = 0 and is the largest possible R_true within
this one-sided model, i.e. the conditional upper bound. This requires that the
treatment-period measurement error adds missed true transits rather than false
positive observed transits, and treats C as the reference counterfactual.
d*(R) answers the decision-relevant sensitivity question directly: "how much of
ALL tanker traffic truly transiting Hormuz would have had to go dark for the
estimated collapse to actually be only R?"

This is a directional measurement-error bound, NOT a causal correction and NOT a
claim about the realised dark rate. The realised d should be anchored from
external dark-fleet reporting (IEA / UNCTAD / Kpler-LSEG style) that the author
cites; pass it via --plausible-dark-rate. The default grid is a sensitivity span.

Run from the repo root:
    python scripts/run_ais_dark_bound.py
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lngfreight import config  # noqa: E402
from lngfreight.specification import working_specification  # noqa: E402


# Reductions of interest: the thresholds a sceptic might propose the "true"
# collapse is no larger than. d*(R) is reported for each.
REFERENCE_REDUCTIONS = (0.50, 0.75, 0.90, 0.95)
# Sensitivity grid for the incremental treatment-period dark rate.
DARK_RATE_GRID = (0.0, 0.10, 0.20, 0.30, 0.40, 0.50, 0.70, 0.90)


def _load_primary_summary() -> pd.DataFrame:
    path = config.path("data_processed") / "counterfactual_post_treatment_summary.csv"
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found. Run scripts/run_counterfactual.py first."
        )
    return pd.read_csv(path)


def _row(summary: pd.DataFrame, model: str, target: str) -> pd.Series:
    sel = summary[(summary["model"] == model) & (summary["target"] == target)]
    if sel.empty:
        raise KeyError(f"no counterfactual row for model={model!r} target={target!r}.")
    return sel.iloc[0]


def true_reduction(observed: float, counterfactual: float, dark_rate: float) -> float:
    """R_true(d) = 1 - O / ((1 - d) C). NaN if d >= 1 (degenerate)."""
    if dark_rate >= 1.0:
        return float("nan")
    return 1.0 - observed / ((1.0 - dark_rate) * counterfactual)


def critical_dark_rate(observed: float, counterfactual: float, reduction: float) -> float:
    """d*(R) = 1 - O / (C (1 - R)). The dark rate needed to pull the reduction
    down to ``reduction``. Clipped to [0, 1]; >1 means even a total blackout
    cannot reach that small a reduction (reported as 1.0 with a flag)."""
    if reduction >= 1.0:
        return float("nan")
    needed_observed_share = observed / (counterfactual * (1.0 - reduction))
    d = 1.0 - needed_observed_share
    return d


def build_bound(observed: float, counterfactual: float, target: str, model: str):
    r_obs = 1.0 - observed / counterfactual

    sens_rows = []
    for d in DARK_RATE_GRID:
        r_true = true_reduction(observed, counterfactual, d)
        sens_rows.append({
            "model": model,
            "target": target,
            "observed_sum": observed,
            "counterfactual_sum": counterfactual,
            "assumed_dark_rate": d,
            "implied_true_transits": observed / (1.0 - d) if d < 1.0 else float("nan"),
            "true_reduction": r_true,
            "reduction_attributable_to_observability": r_obs - r_true,
        })
    sensitivity = pd.DataFrame(sens_rows)

    crit_rows = []
    for r in REFERENCE_REDUCTIONS:
        d_star = critical_dark_rate(observed, counterfactual, r)
        crit_rows.append({
            "model": model,
            "target": target,
            "reference_reduction": r,
            "critical_dark_rate": min(max(d_star, 0.0), 1.0),
            "exceeds_total_blackout": d_star > 1.0,
            "feasible": 0.0 <= d_star <= 1.0,
        })
    critical = pd.DataFrame(crit_rows)
    return r_obs, sensitivity, critical


def main(plausible_dark_rate: float | None) -> int:
    spec = working_specification()
    model = spec.primary_estimator  # ar_lag1_7 — no post-treatment covariate exposure
    target = spec.primary_outcome   # hormuz_tanker_transits

    summary = _load_primary_summary()
    row = _row(summary, model, target)
    observed = float(row["observed_sum"])
    counterfactual = float(row["counterfactual_sum"])

    r_obs, sensitivity, critical = build_bound(observed, counterfactual, target, model)

    out_dir = config.path("data_processed")
    sens_path = out_dir / "ais_dark_bound_sensitivity.csv"
    crit_path = out_dir / "ais_dark_bound_critical_rates.csv"
    sensitivity.to_csv(sens_path, index=False)
    critical.to_csv(crit_path, index=False)

    print(f"AIS-dark-vessel bound — primary estimator {model!r} on {target!r}")
    print(f"  observed post-period transits      O = {observed:,.0f}")
    print(f"  counterfactual post-period transits C = {counterfactual:,.0f}")
    print(f"  naive observed reduction (CONDITIONAL UPPER BOUND under "
          f"one-sided undercounting, d=0): {r_obs:.4f} "
          f"({r_obs * 100:.1f}%)")
    print("\nSensitivity — true reduction if a fraction d of true transits went dark:")
    print(sensitivity[["assumed_dark_rate", "implied_true_transits",
                       "true_reduction"]].to_string(index=False))
    print("\nCritical dark rate d* needed to pull the true reduction down to R:")
    print(critical[["reference_reduction", "critical_dark_rate",
                    "exceeds_total_blackout"]].to_string(index=False))

    d50 = float(critical.loc[critical["reference_reduction"] == 0.50,
                             "critical_dark_rate"].iloc[0])
    print(f"\nHeadline: to make the TRUE collapse merely 50%, {d50 * 100:.0f}% of "
          f"ALL tankers truly transiting Hormuz in the post-period would have had "
          f"to be simultaneously AIS-dark.")

    if plausible_dark_rate is not None:
        r_true = true_reduction(observed, counterfactual, plausible_dark_rate)
        print(f"\nUnder the supplied plausible dark rate d = {plausible_dark_rate:.2f} "
              f"(anchor it to a cited external figure): true reduction = "
              f"{r_true:.4f} ({r_true * 100:.1f}%).")

    print(f"\nwrote {sens_path}")
    print(f"wrote {crit_path}")
    print("\nGuard: this is a conditional directional measurement-error bound, "
          "not a causal correction. It assumes one-sided undercounting: treatment-"
          "period observability error adds missed true transits, not false-positive "
          "observed transits. d is the INCREMENTAL treatment-period dark rate above "
          "the baseline gap-fill already in the pre-treatment counterfactual.")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--plausible-dark-rate",
        type=float,
        default=None,
        help="optional externally-anchored incremental dark rate in [0,1) to "
             "report the implied true reduction for.",
    )
    args = parser.parse_args()
    raise SystemExit(main(plausible_dark_rate=args.plausible_dark_rate))
