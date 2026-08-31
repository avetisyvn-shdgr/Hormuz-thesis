

from hormuz_throughput import config  # noqa: E402
from hormuz_throughput.importer_outcomes import (  # noqa: E402
    build_outcomes,
    outcomes_summary,
)


def _frame():
    probe_dir = config.path("data_raw") / "backup_pathway_probe_20260621"
    return build_outcomes(probe_dir)


def _value(frame, unit, outcome, month):
    row = frame[
        (frame["unit"] == unit)
        & (frame["outcome"] == outcome)
        & (frame["month"] == month)
    ]
    assert len(row) == 1, f"expected one row for {unit}/{outcome}/{month}"
    return float(row["value"].iloc[0])


def test_japan_gulf_excludes_oman_and_matches_frozen_values():
    frame = _frame()
    assert _value(frame, "Japan", "y1_gulf_volume", "2026-03") == 144_243_000.0
    assert _value(frame, "Japan", "y2_total_volume", "2026-03") == 5_869_358_000.0
    assert _value(frame, "Japan", "y1_gulf_volume", "2026-02") == 428_129_000.0


def test_share_is_a_valid_proportion_and_consistent_with_volumes():
    frame = _frame()
    shares = frame[frame["outcome"] == "y1_gulf_share"]["value"]
    assert ((shares >= 0) & (shares <= 1)).all()
    total = _value(frame, "Japan", "y2_total_volume", "2026-03")
    gulf = _value(frame, "Japan", "y1_gulf_volume", "2026-03")
    assert abs(_value(frame, "Japan", "y1_gulf_share", "2026-03") - gulf / total) < 1e-12
    non_gulf = _value(frame, "Japan", "y3_non_gulf_volume", "2026-03")
    assert abs(non_gulf - (total - gulf)) < 1e-6


def test_post_treatment_flag_and_provenance_present():
    frame = _frame()
    assert (frame.loc[frame["month"] >= "2026-03", "post_treatment"]).all()
    assert (~frame.loc[frame["month"] < "2026-03", "post_treatment"]).all()
    assert (frame["snapshot_sha256"].str.len() == 64).all()


def test_summary_reports_units_and_defers_y4():
    frame = _frame()
    summary = outcomes_summary(frame)
    assert summary["units_with_gulf_outcome"] == ["EU27", "Japan"]
    assert summary["outcomes_deferred"] == ["y4_composite_vulnerability"]
    assert "y4_composite_vulnerability" not in summary["outcomes_built"]
