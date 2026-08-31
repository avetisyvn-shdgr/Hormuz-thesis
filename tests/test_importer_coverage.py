
import pandas as pd


from hormuz_throughput.importer_coverage import admission_status, coverage_summary  # noqa: E402


def test_admission_requires_source_and_time_coverage():
    admitted, reason = admission_status(
        unit_type="importer",
        official_total=True,
        official_by_source=True,
        contiguous_pre_months=12,
        post_months=3,
    )
    assert admitted
    assert reason == "admitted"

    admitted, reason = admission_status(
        unit_type="importer",
        official_total=True,
        official_by_source=False,
        contiguous_pre_months=12,
        post_months=2,
    )
    assert not admitted
    assert "by-source" in reason
    assert "2 post months" in reason


def test_summary_does_not_admit_an_undersized_panel():
    matrix = pd.DataFrame({
        "unit": ["A", "B"],
        "unit_type": ["importer", "importer"],
        "confirmatory_panel_admissible": [True, False],
    })
    summary = coverage_summary(matrix)
    assert summary["status"] == "no_go"
    assert summary["admitted_importers"] == ["A"]
