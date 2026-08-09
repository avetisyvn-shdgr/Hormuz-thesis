"""Build the frozen-data coverage matrix for the proposed importer panel."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lngfreight import config  # noqa: E402
from lngfreight.importer_coverage import (  # noqa: E402
    build_coverage_matrix,
    coverage_summary,
)
from lngfreight.registry import RegisteredArtifact, get_variable  # noqa: E402


def _render_report(matrix, summary: dict[str, object]) -> str:
    columns = [
        "unit", "official_source", "official_by_source_available",
        "contiguous_pre_months", "post_months", "latest_period",
        "gfw_country_gulf_estimate_admissible", "confirmatory_panel_admissible",
    ]
    rows = matrix[columns].astype(str).values.tolist()
    table_lines = [
        "| " + " | ".join(columns) + " |",
        "|" + "|".join("---" for _ in columns) + "|",
    ]
    table_lines.extend("| " + " | ".join(row) + " |" for row in rows)
    table = "\n".join(table_lines)
    return f"""# Importer source coverage and panel-admission report

**Generated:** 2026-06-22  
**Verdict:** **{str(summary['status']).upper()}** for the confirmatory importer panel.

## Admission rule

An importer requires an official monthly total series, an official by-source
series for predetermined exposure, at least
{summary['minimum_contiguous_pre_months']} contiguous pre-treatment months, and
at least {summary['minimum_post_months']} post-treatment months. The proposed
panel requires at least {summary['minimum_importers']} admitted importers. GFW is
a cross-validation source only; suppressed country-level Gulf estimates cannot
replace missing official observations.

## Observed coverage

{table}

## Decision

**Admitted importers: {summary['admitted_importer_count']} of the required
{summary['minimum_importers']}.** {summary['interpretation']}

The current evidence supports a descriptive EU27/Japan/India comparison, not a
confirmatory cross-importer 2WFE model. Re-run this report after additional
national-statistics snapshots are frozen. The full source paths, hashes, and
failure reasons are in `data/processed/importer_source_coverage.csv`; the summary
is in `data/processed/importer_source_coverage_summary.json`.

## Methodological boundary

This is a coverage/admission audit, not an empirical result. No missing country
is imputed, no GFW proxy is silently promoted to an official outcome, and no
estimator is fitted.
"""


def main() -> None:
    artifact_names = [
        "backup_probe_manifest_snapshot",
        "backup_comtrade_japan_by_partner_snapshot",
        "backup_comtrade_japan_monthly_snapshot",
        "backup_comtrade_usa_monthly_snapshot",
        "backup_eia_us_lng_exports_snapshot",
        "backup_eurostat_eu27_by_partner_snapshot",
        "backup_ppac_lng_historical_snapshot",
        "backup_ppac_lng_current_snapshot",
    ]
    artifacts = [
        get_variable(name, query={"consumer": "build_importer_coverage_report"})
        for name in artifact_names
    ]
    if not all(isinstance(item, RegisteredArtifact) for item in artifacts):
        raise TypeError("coverage-probe inputs must resolve as artifacts")
    probe_dirs = {item.path.parent for item in artifacts}
    if len(probe_dirs) != 1:
        raise ValueError("coverage-probe artifacts must share one directory")
    probe_dir = probe_dirs.pop()
    matrix = build_coverage_matrix(
        probe_dir,
        config.path("data_processed") / "importer_exposure_summary.csv",
    )
    summary = coverage_summary(matrix)
    matrix_path = config.path("data_processed") / "importer_source_coverage.csv"
    summary_path = (
        config.path("data_processed") / "importer_source_coverage_summary.json"
    )
    report_path = config.ROOT / "docs" / "IMPORTER_SOURCE_COVERAGE_REPORT.md"
    matrix.to_csv(matrix_path, index=False)
    summary_path.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    report_path.write_text(_render_report(matrix, summary), encoding="utf-8")
    print(f"wrote {matrix_path}")
    print(f"wrote {summary_path}")
    print(f"wrote {report_path}")
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
