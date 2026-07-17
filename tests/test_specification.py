
import pytest


from lngfreight.specification import working_specification


def test_working_specification_locks_fallback_roles():
    spec = working_specification()
    assert spec.branch == "fallback_portwatch"
    assert spec.primary_outcome == "hormuz_tanker_transits"
    assert spec.robustness_outcome == "hormuz_tanker_capacity"
    assert spec.primary_estimator == "ar_lag1_7"
    assert spec.active_secondary_outcomes == ()
    assert set(spec.dormant_secondary_outcomes) == {
        "spark30s_atlantic_freight", "spark25s_pacific_freight"
    }
    assert spec.reporting_term == "disruption-associated counterfactual shortfall"
    assert spec.transformer_enabled is False


def test_working_specification_rejects_transformer_activation():
    settings = {
        "modeling": {"working_specification": {
            "status": "test",
            "branch": "fallback_portwatch",
            "primary_outcome": "count",
            "robustness_outcome": "capacity",
            "active_secondary_outcomes": [],
            "dormant_secondary_outcomes": [],
            "primary_estimator": "ar",
            "benchmark_estimators": [],
            "conditional_sensitivity_estimators": [],
            "reporting_term": "shortfall",
            "transformer_enabled": True,
            "transformer_reentry_rule": "not satisfied",
        }}
    }
    with pytest.raises(ValueError, match="Transformer"):
        working_specification(settings)
