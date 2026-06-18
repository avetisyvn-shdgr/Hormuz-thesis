"""Validated access to the locked working fallback specification."""
from __future__ import annotations

from dataclasses import dataclass

from . import config


@dataclass(frozen=True)
class WorkingSpecification:
    status: str
    branch: str
    primary_outcome: str
    robustness_outcome: str
    active_secondary_outcomes: tuple[str, ...]
    dormant_secondary_outcomes: tuple[str, ...]
    primary_estimator: str
    benchmark_estimators: tuple[str, ...]
    conditional_sensitivity_estimators: tuple[str, ...]
    reporting_term: str
    transformer_enabled: bool
    transformer_reentry_rule: str

    @property
    def outcomes(self) -> tuple[str, ...]:
        return (
            self.primary_outcome,
            self.robustness_outcome,
            *self.active_secondary_outcomes,
        )

    @property
    def estimators(self) -> tuple[str, ...]:
        return (
            *self.benchmark_estimators,
            self.primary_estimator,
            *self.conditional_sensitivity_estimators,
        )


def working_specification(settings: dict | None = None) -> WorkingSpecification:
    raw = (settings or config.settings()).get("modeling", {}).get(
        "working_specification"
    )
    if not raw:
        raise ValueError("modeling.working_specification is required.")

    spec = WorkingSpecification(
        status=str(raw["status"]),
        branch=str(raw["branch"]),
        primary_outcome=str(raw["primary_outcome"]),
        robustness_outcome=str(raw["robustness_outcome"]),
        active_secondary_outcomes=tuple(raw.get("active_secondary_outcomes", [])),
        dormant_secondary_outcomes=tuple(raw.get("dormant_secondary_outcomes", [])),
        primary_estimator=str(raw["primary_estimator"]),
        benchmark_estimators=tuple(raw.get("benchmark_estimators", [])),
        conditional_sensitivity_estimators=tuple(
            raw.get("conditional_sensitivity_estimators", [])
        ),
        reporting_term=str(raw["reporting_term"]),
        transformer_enabled=bool(raw.get("transformer_enabled", False)),
        transformer_reentry_rule=str(raw.get("transformer_reentry_rule", "")),
    )
    if spec.primary_outcome == spec.robustness_outcome:
        raise ValueError("Primary and robustness outcomes must differ.")
    if set(spec.active_secondary_outcomes) & set(spec.dormant_secondary_outcomes):
        raise ValueError("A secondary outcome cannot be active and dormant.")
    if spec.primary_estimator in spec.conditional_sensitivity_estimators:
        raise ValueError("Primary estimator cannot also be a conditional sensitivity.")
    if len(set(spec.estimators)) != len(spec.estimators):
        raise ValueError("Estimator roles contain duplicates.")
    if spec.transformer_enabled:
        raise ValueError(
            "Transformer is disabled for the working fallback. Satisfy and document "
            "the configured re-entry rule before enabling it."
        )
    return spec
