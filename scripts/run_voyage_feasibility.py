"""Score terminal endpoint resolution without claiming observed LNG cargo."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lngfreight import config  # noqa: E402
from lngfreight.registry import RegisteredArtifact, get_variable  # noqa: E402
from lngfreight.voyages import candidate_voyage_endpoints, endpoint_summary  # noqa: E402


def main() -> None:
    settings = config.settings()
    paths = settings["paths"]
    artifacts = {
        "visits": get_variable(
            "qflex_gfw_port_visits_snapshot",
            query={"consumer": "run_voyage_feasibility"},
        ),
        "identities": get_variable(
            "qflex_gfw_identity_snapshot",
            query={"consumer": "run_voyage_feasibility"},
        ),
        "terminals": get_variable(
            "qflex_lng_terminal_crosswalk_snapshot",
            query={"consumer": "run_voyage_feasibility"},
        ),
    }
    if not all(isinstance(item, RegisteredArtifact) for item in artifacts.values()):
        raise TypeError("voyage-feasibility inputs must resolve as artifacts")
    visits = artifacts["visits"].read_csv()
    identities = artifacts["identities"].read_csv(dtype={"imo": str})
    terminals = artifacts["terminals"].read_csv()
    voyages = candidate_voyage_endpoints(visits, identities, terminals)
    out = config.path("data_processed") / "candidate_voyage_endpoints.csv"
    voyages.to_csv(out, index=False)

    threshold = float(
        settings["vessel_data_feasibility"]["min_terminal_endpoint_rate"]
    )
    summary = endpoint_summary(voyages, threshold)
    summary.update({
        "measure_supported": "port_to_port_sequence_feasibility",
        "cargo_state_observed": False,
        "cargo_quantity_observed": False,
        "track_distance_observed": False,
        "ais_gap_criterion": "not_applicable_without_track_derived_distance",
        "scope_warning": (
            "Q-Flex coverage supports Qatar-linked port-sequence reconstruction; "
            "it does not represent the global replacement-supply fleet."
        ),
    })
    summary_path = config.path("data_processed") / "voyage_feasibility_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(f"wrote {out}")
    print(f"wrote {summary_path}")
    print(
        f"resolved={summary['resolved_endpoint_calls']}/"
        f"{summary['scorable_export_origin_calls']} "
        f"rate={summary['endpoint_resolution_rate']:.1%}"
    )


if __name__ == "__main__":
    main()
