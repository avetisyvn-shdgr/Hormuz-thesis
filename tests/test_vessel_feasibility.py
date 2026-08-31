from pathlib import Path

import pandas as pd

from hormuz_throughput.feasibility import build_vessel_feasibility_report


def _settings() -> dict:
    return {
        "paths": {
            "wto_hormuz_lng_csv": "wto.csv",
            "portwatch_csv": "portwatch.csv",
            "gfw_lng_vessel_benchmark_csv": "roster.csv",
            "gfw_vessel_identity_csv": "identity.csv",
            "gfw_port_visits_csv": "visits.csv",
            "gfw_lng_terminals_csv": "terminals.csv",
        },
        "vessel_data_feasibility": {
            "benchmark_vessels": 30,
            "min_identity_match_rate": 0.8,
            "min_port_visit_coverage_rate": 0.8,
            "min_terminal_endpoint_rate": 0.9,
            "max_median_ais_gap_hours": 24,
            "accepted_measure": "inferred_lng_capacity_nautical_miles",
            "prohibited_measure_label": "observed_laden_cargo_ton_miles",
        },
    }


def _valid_imo(prefix: int) -> str:
    first_six = f"{prefix:06d}"
    checksum = sum(
        int(digit) * weight
        for digit, weight in zip(first_six, range(7, 1, -1))
    ) % 10
    return first_six + str(checksum)


def _write_complete_inputs(tmp_path: Path, roster_rows: int) -> None:
    pd.DataFrame({"voy_load_date": ["2026-01-01"], "value": [1]}).to_csv(
        tmp_path / "wto.csv", index=False
    )
    pd.DataFrame({"date": ["2026-01-01"]}).to_csv(
        tmp_path / "portwatch.csv", index=False
    )
    pd.DataFrame({
        "imo": [_valid_imo(900000 + i) for i in range(roster_rows)],
        "vessel_name": [f"Vessel {i}" for i in range(roster_rows)],
        "lng_capacity_m3": [174_000] * roster_rows,
        "source": ["documented source"] * roster_rows,
    }).to_csv(tmp_path / "roster.csv", index=False)
    pd.DataFrame({"imo": [_valid_imo(900000)], "vessel_id": ["v1"]}).to_csv(
        tmp_path / "identity.csv", index=False
    )
    pd.DataFrame({
        "vessel_id": ["v1"], "start": ["2026-01-01"], "end": ["2026-01-02"],
        "port_id": ["p1"], "lat": [1], "lon": [1], "sample_period": ["pre"]
    }).to_csv(tmp_path / "visits.csv", index=False)
    pd.DataFrame({
        "port_id": ["p1"], "terminal_name": ["T"], "terminal_role": ["liquefaction"],
        "country": ["X"], "source": ["documented source"]
    }).to_csv(tmp_path / "terminals.csv", index=False)


def test_missing_token_and_sample_block_empirical_branch(tmp_path: Path):
    report = build_vessel_feasibility_report(tmp_path, _settings(), {})
    gate = report["empirical_vessel_branch"]
    assert gate["status"] == "blocked_pending_access_and_sample"
    assert "GFW_API_TOKEN is not configured" in gate["blockers"]
    assert report["spark_extension"]["preserved"] is True


def test_undersized_roster_blocks_scoring(tmp_path: Path):
    _write_complete_inputs(tmp_path, roster_rows=1)

    report = build_vessel_feasibility_report(
        tmp_path, _settings(), {"GFW_API_TOKEN": True}
    )
    gate = report["empirical_vessel_branch"]
    roster = report["gfw"]["required_local_inputs"]["gfw_lng_vessel_benchmark_csv"]
    assert gate["status"] == "blocked_pending_access_and_sample"
    assert "benchmark roster does not meet quality criteria" in gate["blockers"]
    assert roster["roster_diagnostics"]["unique_imo_count"] == 1


def test_complete_sample_is_ready_for_scoring_not_automatically_passed(tmp_path: Path):
    _write_complete_inputs(tmp_path, roster_rows=30)

    report = build_vessel_feasibility_report(
        tmp_path, _settings(), {"GFW_API_TOKEN": True}
    )
    assert report["empirical_vessel_branch"]["status"] == (
        "sample_scored_below_coverage_threshold"
    )
    assert report["empirical_vessel_branch"]["prohibited_label"] == (
        "observed_laden_cargo_ton_miles"
    )
    coverage = report["gfw"]["coverage_diagnostics"]
    assert coverage["identity_match_rate"] == 1 / 30
    assert coverage["all_periods_pass"] is False
    assert any(
        "manually transcribed" in limitation
        and "source PDFs" in limitation
        and "not retained" in limitation
        for limitation in report["gfw"]["documented_limitations"]
    )


def test_duplicate_and_invalid_imos_fail_roster_quality(tmp_path: Path):
    _write_complete_inputs(tmp_path, roster_rows=30)
    roster_path = tmp_path / "roster.csv"
    roster = pd.read_csv(roster_path, dtype={"imo": str})
    roster.loc[1, "imo"] = roster.loc[0, "imo"]
    roster.loc[2, "imo"] = "1234560"
    roster.to_csv(roster_path, index=False)

    report = build_vessel_feasibility_report(
        tmp_path, _settings(), {"GFW_API_TOKEN": True}
    )
    diagnostics = report["gfw"]["required_local_inputs"][
        "gfw_lng_vessel_benchmark_csv"
    ]["roster_diagnostics"]
    assert diagnostics["duplicate_imo_rows"] == 1
    assert diagnostics["invalid_imo_rows"] == 1
    assert report["empirical_vessel_branch"]["status"] == (
        "blocked_pending_access_and_sample"
    )
