"""Coverage simulation for candidate basin-level uncertainty intervals.

Task 3 of the corridor-transmission plan authorises basin *point* summaries only.
That decision must be backed by evidence, not assertion: the acceptance check
requires a simulation showing that any proposed basin interval fails to reach its
stated coverage under realistic data-generating processes before the protocol
defaults to ``point_only``.

This module supplies that evidence. It is a pure synthetic-data study. It never
touches the real corridor panel, never reads post-cutoff observations and is not
gated by supervisor approval: it answers a statistical question about interval
constructions, not an empirical question about the 2026 disruption.

The object of interest is a basin aggregate effect ``theta_b`` formed from the
corridor-level scaled signed deviations defined in ``corridor_inference``. Each
candidate method turns the per-corridor estimates and a shared-placebo null into
a basin interval; we measure how often that interval contains the *meaningful*
basin estimand across Monte-Carlo replications. Three obstacles are modelled
explicitly, matching the three reasons stated in the inference protocol:

1. cross-corridor dependence (marginal corridor quantiles do not supply a joint
   predictive path);
2. coarse finite placebo draws (a null reference distribution with very few
   shared origins cannot define stable interval quantiles); and
3. chokepoint double counting (summing corridors that share traffic targets an
   ill-posed estimand, so even a covariance-aware interval misses the
   topology-aware effect).
"""
from __future__ import annotations

from dataclasses import dataclass
from statistics import NormalDist

import numpy as np
import pandas as pd

# The four interval constructions a researcher would plausibly reach for. Only
# the last is covariance-aware; the simulation shows even that one is not a safe
# default once finite draws or double counting are present.
BASIN_INTERVAL_METHODS = (
    "independent_normal_sum",
    "marginal_quantile_sum",
    "placebo_reference_as_interval",
    "joint_centered_resample",
)


@dataclass(frozen=True)
class BasinCoverageScenario:
    """One synthetic data-generating process for the coverage study."""

    name: str
    n_corridors: int
    corridor_correlation: float
    true_corridor_effect: float
    estimator_noise_sd: float
    n_placebo_draws: int
    double_count_overlap: float

    def __post_init__(self) -> None:
        if self.n_corridors < 2:
            raise ValueError("a basin needs at least two corridors.")
        if not -1.0 / (self.n_corridors - 1) < self.corridor_correlation < 1.0:
            raise ValueError("corridor_correlation must keep the covariance positive definite.")
        if self.estimator_noise_sd <= 0:
            raise ValueError("estimator_noise_sd must be positive.")
        if self.n_placebo_draws < 2:
            raise ValueError("need at least two placebo draws to form an interval.")
        if not 0.0 <= self.double_count_overlap < 1.0:
            raise ValueError("double_count_overlap must lie in [0, 1).")

    @property
    def naive_basin_effect(self) -> float:
        """Sum of corridor effects: what every estimator's point sum targets."""
        return self.true_corridor_effect * self.n_corridors

    @property
    def meaningful_basin_effect(self) -> float:
        """Topology-aware effect after removing double-counted shared traffic."""
        return self.naive_basin_effect * (1.0 - self.double_count_overlap)


def _equicorrelation_cholesky(k: int, rho: float, sd: float) -> np.ndarray:
    corr = np.full((k, k), rho, dtype="float64")
    np.fill_diagonal(corr, 1.0)
    return np.linalg.cholesky(corr * sd * sd)


def _interval_bounds(
    method: str,
    point_sum: np.ndarray,
    centered_placebo: np.ndarray,
    alpha: float,
) -> tuple[np.ndarray, np.ndarray]:
    """Return (lower, upper) per replication for one candidate construction.

    ``point_sum`` has shape (R,); ``centered_placebo`` has shape (R, B, k) and is
    already centred per replication and per corridor.
    """
    z = NormalDist().inv_cdf(1.0 - alpha / 2.0)
    summed = centered_placebo.sum(axis=2)  # (R, B): joint null of the basin sum.

    if method == "independent_normal_sum":
        per_corridor_var = centered_placebo.var(axis=1, ddof=1)  # (R, k)
        half = z * np.sqrt(per_corridor_var.sum(axis=1))
        return point_sum - half, point_sum + half

    if method == "marginal_quantile_sum":
        lo = np.quantile(centered_placebo, alpha / 2.0, axis=1)  # (R, k)
        hi = np.quantile(centered_placebo, 1.0 - alpha / 2.0, axis=1)
        return point_sum + lo.sum(axis=1), point_sum + hi.sum(axis=1)

    if method == "placebo_reference_as_interval":
        # The anti-pattern the protocol labels placebo_reference_not_interval:
        # the null distribution is centred at zero and is never shifted to the
        # estimate, so it cannot cover a non-zero effect.
        lo = np.quantile(summed, alpha / 2.0, axis=1)
        hi = np.quantile(summed, 1.0 - alpha / 2.0, axis=1)
        return lo, hi

    if method == "joint_centered_resample":
        lo = np.quantile(summed, alpha / 2.0, axis=1)
        hi = np.quantile(summed, 1.0 - alpha / 2.0, axis=1)
        return point_sum + lo, point_sum + hi

    raise ValueError(f"unknown basin interval method {method!r}.")


def simulate_scenario(
    scenario: BasinCoverageScenario,
    *,
    alpha: float = 0.20,
    n_replications: int = 4000,
    seed: int = 20260621,
) -> pd.DataFrame:
    """Monte-Carlo coverage of each candidate basin interval under one scenario.

    ``alpha`` defaults to 0.20 so the nominal coverage (0.80) matches the frozen
    corridor interval level. Coverage is measured against the *meaningful* basin
    estimand, which differs from the naive corridor sum when traffic is shared.
    """
    if not 0.0 < alpha < 1.0:
        raise ValueError("alpha must lie strictly between zero and one.")
    if n_replications < 1:
        raise ValueError("n_replications must be positive.")

    rng = np.random.default_rng(seed)
    k = scenario.n_corridors
    chol = _equicorrelation_cholesky(k, scenario.corridor_correlation, scenario.estimator_noise_sd)

    # The matmuls below operate on finite inputs and produce finite output; the
    # Apple Accelerate BLAS occasionally raises spurious overflow/invalid FP
    # warnings on these calls, so we silence FP warnings for the correlation step.
    with np.errstate(all="ignore"):
        # Observed corridor estimates: truth plus correlated estimator noise.
        obs_noise = rng.standard_normal((n_replications, k)) @ chol.T
        d_hat = scenario.true_corridor_effect + obs_noise
        # Shared placebo null draws: mean-zero, same dependence as the estimator.
        b = scenario.n_placebo_draws
        placebo = (rng.standard_normal((n_replications * b, k)) @ chol.T).reshape(
            n_replications, b, k
        )
    point_sum = d_hat.sum(axis=1)  # (R,)
    centered = placebo - placebo.mean(axis=1, keepdims=True)

    target = scenario.meaningful_basin_effect
    nominal = 1.0 - alpha

    rows = []
    for method in BASIN_INTERVAL_METHODS:
        lower, upper = _interval_bounds(method, point_sum, centered, alpha)
        covered = (lower <= target) & (target <= upper)
        coverage = float(covered.mean())
        # Monte-Carlo standard error of the coverage estimate.
        mc_se = float(np.sqrt(coverage * (1.0 - coverage) / n_replications))
        rows.append({
            "scenario": scenario.name,
            "method": method,
            "n_corridors": k,
            "corridor_correlation": scenario.corridor_correlation,
            "n_placebo_draws": scenario.n_placebo_draws,
            "double_count_overlap": scenario.double_count_overlap,
            "nominal_coverage": nominal,
            "empirical_coverage": coverage,
            "coverage_mc_se": mc_se,
            "mean_interval_width": float(np.mean(upper - lower)),
            "meaningful_basin_effect": target,
            "naive_basin_effect": scenario.naive_basin_effect,
            "n_replications": int(n_replications),
        })
    return pd.DataFrame(rows)


def run_coverage_grid(
    scenarios,
    *,
    alpha: float = 0.20,
    n_replications: int = 4000,
    seed: int = 20260621,
    coverage_tolerance: float = 0.03,
) -> pd.DataFrame:
    """Run every scenario and flag whether each interval meets nominal coverage.

    A method "meets" coverage in a scenario when its empirical coverage is within
    ``coverage_tolerance`` of nominal (intervals that badly over-cover are also
    flagged because an uncalibrated-wide interval is not a stated-coverage
    interval either).
    """
    frames = [
        simulate_scenario(s, alpha=alpha, n_replications=n_replications, seed=seed)
        for s in scenarios
    ]
    grid = pd.concat(frames, ignore_index=True)
    grid["meets_nominal_coverage"] = (
        (grid["empirical_coverage"] - grid["nominal_coverage"]).abs()
        <= coverage_tolerance
    )
    return grid


def default_scenarios() -> tuple[BasinCoverageScenario, ...]:
    """The frozen scenario grid reported in the basin-coverage results note.

    The grid isolates one obstacle at a time, then combines them. The
    ``realistic_design`` scenario uses the nine shared placebo draws actually
    available in ``config/corridor_transmission.yaml`` together with positive
    cross-corridor dependence and modest double counting.
    """
    return (
        BasinCoverageScenario(
            name="ideal_independent_large_draws",
            n_corridors=5,
            corridor_correlation=0.0,
            true_corridor_effect=0.10,
            estimator_noise_sd=0.05,
            n_placebo_draws=2000,
            double_count_overlap=0.0,
        ),
        BasinCoverageScenario(
            name="correlated_large_draws",
            n_corridors=5,
            corridor_correlation=0.5,
            true_corridor_effect=0.10,
            estimator_noise_sd=0.05,
            n_placebo_draws=2000,
            double_count_overlap=0.0,
        ),
        BasinCoverageScenario(
            name="correlated_nine_draws",
            n_corridors=5,
            corridor_correlation=0.5,
            true_corridor_effect=0.10,
            estimator_noise_sd=0.05,
            n_placebo_draws=9,
            double_count_overlap=0.0,
        ),
        BasinCoverageScenario(
            name="double_counted_large_draws",
            n_corridors=5,
            corridor_correlation=0.5,
            true_corridor_effect=0.10,
            estimator_noise_sd=0.05,
            n_placebo_draws=2000,
            double_count_overlap=0.25,
        ),
        BasinCoverageScenario(
            name="realistic_design_nine_draws",
            n_corridors=5,
            corridor_correlation=0.5,
            true_corridor_effect=0.10,
            estimator_noise_sd=0.05,
            n_placebo_draws=9,
            double_count_overlap=0.25,
        ),
    )
