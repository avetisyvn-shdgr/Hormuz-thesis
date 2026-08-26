"""Admission-gate tests for the optional TSFM counterfactual runner."""

import pandas as pd
import pytest

from scripts.run_tsfm_counterfactual import _validate_admission_table


def _table() -> pd.DataFrame:
    return pd.DataFrame([
        {"model": "chronos2", "target": "transits", "admitted": True},
        {"model": "chronos2", "target": "capacity", "admitted": True},
        {"model": "moirai", "target": "transits", "admitted": False},
    ])


def test_gate_accepts_one_admitted_row_per_target():
    _validate_admission_table(
        _table(), model="chronos2", targets=["transits", "capacity"]
    )


def test_gate_rejects_missing_or_rejected_target():
    with pytest.raises(ValueError, match="missing"):
        _validate_admission_table(
            _table(), model="chronos2", targets=["transits", "unknown"]
        )
    with pytest.raises(ValueError, match="not admitted"):
        _validate_admission_table(_table(), model="moirai", targets=["transits"])


def test_gate_rejects_duplicate_or_non_boolean_verdict():
    duplicated = pd.concat([_table(), _table().iloc[[0]]], ignore_index=True)
    with pytest.raises(ValueError, match="duplicates"):
        _validate_admission_table(
            duplicated, model="chronos2", targets=["transits", "capacity"]
        )

    invalid = _table().copy()
    invalid["admitted"] = invalid["admitted"].astype("object")
    invalid.loc[0, "admitted"] = "maybe"
    with pytest.raises(ValueError, match="non-boolean"):
        _validate_admission_table(
            invalid, model="chronos2", targets=["transits", "capacity"]
        )
