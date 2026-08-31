"""B2 compatibility migration: the two import paths must stay identical.

`pair_reallocation` moved from `propagation` to `receiver_equivalence` without
any change to its arithmetic. These tests exist so the legacy path cannot
silently drift from the new one, and so the move cannot quietly become a
reimplementation. They are synthetic; the real-data anchor arithmetic is
verified by `scripts/run_receiver_test.py`, which Mher runs.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from hormuz_throughput.propagation import EventSpec
from hormuz_throughput.propagation import pair_reallocation as legacy_path
from hormuz_throughput.receiver_equivalence import pair_reallocation as new_path


def _panel(n_days: int = 1500, seed: int = 5) -> pd.DataFrame:
    """A panel with one emitter that drops and one receiver that gains."""
    rng = np.random.default_rng(seed)
    index = pd.date_range("2019-01-01", periods=n_days, freq="D")
    columns = {
        f"donor_{i}": rng.normal(30.0, 2.0, size=n_days).clip(1.0) for i in range(8)
    }
    emitter = rng.normal(40.0, 2.0, size=n_days)
    receiver = rng.normal(25.0, 2.0, size=n_days)
    onset_position = 1200
    emitter[onset_position:] -= 12.0
    receiver[onset_position:] += 9.0
    columns["emitter_unit"] = emitter.clip(1.0)
    columns["receiver_unit"] = receiver.clip(1.0)
    return pd.DataFrame(columns, index=index)


def _spec(panel: pd.DataFrame) -> EventSpec:
    return EventSpec("probe_event", "emitter_unit", panel.index[1200])


def test_legacy_and_new_import_paths_return_identical_results():
    panel = _panel()
    spec = _spec(panel)
    kwargs = dict(horizon_weeks=8, n_draws=25, seed=20260826)
    old = legacy_path(panel, spec, "receiver_unit", ["emitter_unit"], **kwargs)
    new = new_path(panel, spec, "receiver_unit", ["emitter_unit"], **kwargs)
    assert old.keys() == new.keys()
    for key in old:
        if isinstance(old[key], float) and np.isnan(old[key]):
            assert np.isnan(new[key])
        else:
            assert old[key] == new[key], f"{key} diverged between import paths"


def test_only_one_implementation_exists():
    """The shim must delegate, not duplicate."""
    import inspect

    from hormuz_throughput import propagation, receiver_equivalence

    shim = inspect.getsource(propagation.pair_reallocation)
    assert "receiver_equivalence" in shim
    for fragment in ("null_p95", "np.quantile", "rng.integers"):
        assert fragment not in shim, f"shim still contains implementation detail {fragment!r}"
    assert "rng.integers" in inspect.getsource(receiver_equivalence.pair_reallocation)


def test_migration_preserved_the_documented_output_contract():
    panel = _panel()
    spec = _spec(panel)
    out = new_path(panel, spec, "receiver_unit", ["emitter_unit"], n_draws=25)
    expected = {
        "event",
        "emitter",
        "receiver",
        "observed_gain_per_day",
        "emitter_loss_per_day",
        "recovered_fraction",
        "null_median",
        "null_p95",
        "percentile_of_observed",
        "n_draws",
    }
    assert set(out) == expected
    assert out["emitter"] == "emitter_unit"
    assert out["receiver"] == "receiver_unit"
    assert out["emitter_loss_per_day"] > 0
    assert out["observed_gain_per_day"] > 0


def test_statistic_is_deterministic_for_a_fixed_seed():
    panel = _panel()
    spec = _spec(panel)
    first = new_path(panel, spec, "receiver_unit", ["emitter_unit"], n_draws=25, seed=7)
    second = new_path(panel, spec, "receiver_unit", ["emitter_unit"], n_draws=25, seed=7)
    assert first == second


def test_statistic_does_not_depend_on_the_als_fit():
    """The migration's premise: the pair statistic never used fitted loadings."""
    import inspect

    from hormuz_throughput import receiver_equivalence

    source = inspect.getsource(receiver_equivalence)
    for fragment in ("_rank1_als", "fit_propagation", "PropagationFit", "receiver_loadings"):
        assert fragment not in source, f"receiver_equivalence references ALS symbol {fragment!r}"


def test_receiver_must_exist_in_the_panel():
    panel = _panel()
    spec = _spec(panel)
    with pytest.raises(KeyError):
        new_path(panel, spec, "not_a_chokepoint", ["emitter_unit"], n_draws=5)



from hormuz_throughput.receiver_equivalence import (  # noqa: E402
    admissible_onsets,
    eligible_units,
    finite_sample_p_value,
    response_frame,
    spatial_family,
    temporal_support,
)

HORIZON = 8


def _disruption(panel, position=1200, length=200, units=("emitter_unit",)):
    """One documented event as (onset, end, units)."""
    onset = panel.index[position]
    return [(onset, onset + pd.Timedelta(days=length), set(units))]


def test_temporal_null_enumerates_each_date_once_and_never_resamples():
    panel = _panel(n_days=2000)
    events = _disruption(panel)
    onset, end, _ = events[0]
    dates = admissible_onsets(
        panel, events, relevant_units={"emitter_unit"},
        horizon_weeks=HORIZON, baseline_days=365, guard_days=90,
    )
    assert len(dates) == len(set(dates)), "a pseudo-onset appeared twice"
    assert list(dates) == sorted(dates)
    for date in dates:
        assert abs((date - onset).days) >= 90
        stop = date + pd.Timedelta(days=(HORIZON + 1) * 7 - 1)
        assert not (onset <= stop and date <= end)


def test_wider_guards_monotonically_shrink_the_admissible_pool():
    panel = _panel(n_days=2000)
    events = _disruption(panel)
    sizes = [
        len(admissible_onsets(panel, events, relevant_units={"emitter_unit"},
                              horizon_weeks=HORIZON, baseline_days=365, guard_days=g))
        for g in (90, 180, 365)
    ]
    assert sizes[0] >= sizes[1] >= sizes[2]
    assert sizes[2] > 0


def test_temporal_support_reports_the_p_value_floor_and_window_count():
    panel = _panel(n_days=2000)
    events = _disruption(panel)
    dates = admissible_onsets(
        panel, events, relevant_units={"emitter_unit"},
        horizon_weeks=HORIZON, baseline_days=365, guard_days=90,
    )
    support = temporal_support(dates, horizon_weeks=HORIZON)
    assert support["n_unique_admissible_dates"] == len(dates)
    assert support["attainable_p_value_floor"] == pytest.approx(1.0 / (len(dates) + 1))
    assert support["approx_non_overlapping_windows"] < support["n_unique_admissible_dates"]


def test_empty_support_does_not_fabricate_a_floor():
    support = temporal_support(pd.DatetimeIndex([]), horizon_weeks=HORIZON)
    assert support["n_unique_admissible_dates"] == 0
    assert np.isnan(support["attainable_p_value_floor"])


def test_finite_sample_p_value_matches_the_declared_formula():
    null = np.array([0.0, 1.0, 2.0, 3.0, 4.0])
    out = finite_sample_p_value(null, observed=3.0)
    assert out["n_null_ge_observed"] == 2
    assert out["B"] == 5
    assert out["p_value"] == pytest.approx((1 + 2) / (5 + 1))
    assert out["floor"] == pytest.approx(1 / 6)


def test_p_value_can_never_be_zero():
    null = np.zeros(50)
    out = finite_sample_p_value(null, observed=99.0)
    assert out["p_value"] == pytest.approx(1 / 51)
    assert out["p_value"] >= out["floor"]


def test_support_rules_drop_thin_units_and_always_exclude_hormuz():
    panel = _panel(n_days=1500)
    panel = panel.copy()
    panel["thin_unit"] = 1.0
    panel["strait_of_hormuz"] = 50.0
    keep = eligible_units(
        panel,
        panel.index[1200],
        min_baseline=5.0,
        always_excluded=["strait_of_hormuz"],
        disrupted_units=["emitter_unit"],
    )
    assert "thin_unit" not in keep
    assert "strait_of_hormuz" not in keep
    assert "emitter_unit" not in keep
    assert "receiver_unit" in keep


def test_standardisation_makes_high_and_low_volume_units_comparable():
    """A raw gain favours big units; the standardised one should not."""
    response = pd.Series({"big": 8.0, "small": 2.0})
    scales = pd.Series({"big": 8.0, "small": 1.0})
    fam = spatial_family(response, scales, ["big", "small"], "small", sign=+1.0)
    assert fam["anchor_standardised"] == pytest.approx(2.0)
    assert fam["rank_of_anchor"] == 1
    assert fam["anchor_is_family_max"]


def test_spatial_family_withholds_an_inferential_p_value():
    response = pd.Series({"a": 3.0, "b": 1.0, "c": 0.5})
    scales = pd.Series({"a": 1.0, "b": 1.0, "c": 1.0})
    fam = spatial_family(response, scales, ["a", "b", "c"], "a", sign=+1.0)
    assert fam["inferential_p_value"] is None
    assert "exchangeability" in fam["p_value_withheld_reason"]
    assert fam["family_size"] == 3
    assert fam["max_statistic_unit"] == "a"


def test_emitter_family_sign_flips_so_a_loss_ranks_as_extreme():
    response = pd.Series({"emitter": -9.0, "other": 1.0})
    scales = pd.Series({"emitter": 1.0, "other": 1.0})
    fam = spatial_family(response, scales, ["emitter", "other"], "emitter", sign=-1.0)
    assert fam["anchor_standardised"] == pytest.approx(9.0)
    assert fam["rank_of_anchor"] == 1


def test_zero_variability_units_are_dropped_not_divided_by_zero():
    response = pd.Series({"a": 3.0, "flat": 2.0})
    scales = pd.Series({"a": 1.0, "flat": np.nan})
    fam = spatial_family(response, scales, ["a", "flat"], "a", sign=+1.0)
    assert fam["family_size"] == 1
    assert "flat" not in fam["standardised_values"]


def test_anchor_must_survive_support_or_the_phase_stops():
    response = pd.Series({"a": 3.0})
    scales = pd.Series({"a": 1.0})
    with pytest.raises(ValueError, match="did not survive the support rules"):
        spatial_family(response, scales, ["a"], "missing_anchor", sign=+1.0)


def test_response_frame_returns_every_unit_in_transits_per_day():
    panel = _panel(n_days=1500)
    frame = response_frame(panel, panel.index[1200], ["emitter_unit"], HORIZON)
    assert set(frame.index) == set(panel.columns)
    assert frame["emitter_unit"] < 0
    assert frame["receiver_unit"] > 0


def test_response_frame_is_independent_of_which_pair_is_named():
    """Both spatial families must read one shared computation."""
    panel = _panel(n_days=1500)
    onset = panel.index[1200]
    first = response_frame(panel, onset, ["emitter_unit"], HORIZON)
    second = response_frame(panel, onset, ["emitter_unit"], HORIZON)
    pd.testing.assert_series_equal(first, second)


def test_a_disruption_at_an_unrelated_unit_does_not_delete_the_pool():
    """Unit-local exclusion: one chokepoint's event must not blank the panel.

    An open-ended window at an unrelated unit previously deleted every date
    after its onset, which is the same error the plan forbids for the A1 mask.
    """
    panel = _panel(n_days=2000)
    onset = panel.index[900]
    forever = pd.Timestamp("2100-01-01")
    unrelated = [(onset, forever, {"donor_0"})]
    relevant = [(onset, forever, {"emitter_unit"})]

    kept = admissible_onsets(
        panel, unrelated, relevant_units={"emitter_unit", "receiver_unit"},
        horizon_weeks=HORIZON, baseline_days=365, guard_days=90,
    )
    deleted = admissible_onsets(
        panel, relevant, relevant_units={"emitter_unit", "receiver_unit"},
        horizon_weeks=HORIZON, baseline_days=365, guard_days=90,
    )
    assert len(kept) > len(deleted)
    assert (kept > onset).any(), "an unrelated unit's event wiped out later dates"
    assert not (deleted >= onset).any(), "the pair's own event must exclude its window"
