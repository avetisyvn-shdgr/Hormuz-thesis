"""Build descriptive importer and destination-basin LNG exposure tables."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from hormuz_throughput import config  # noqa: E402
from hormuz_throughput.exposure import (  # noqa: E402
    attach_exposure_metadata,
    exposure_diagnostics,
    exposure_summary,
)


def main() -> None:
    settings = config.settings()
    paths = settings["paths"]
    policy = settings["vessel_data_feasibility"]["importer_basin_exposure"]
    voyages = pd.read_csv(
        config.ROOT / paths["inferred_capacity_nm_voyages_csv"], dtype={"imo": str}
    )
    audit = pd.read_csv(config.ROOT / paths["global_terminal_matching_audit_csv"])
    enriched = attach_exposure_metadata(
        voyages,
        audit,
        terminal_match_radius_km=int(policy["terminal_match_radius_km"]),
        gulf_export_project_ids=list(policy["gulf_export_project_ids"]),
        destination_basin_by_country=dict(policy["destination_basin_by_country"]),
    )
    minimum = int(policy["min_country_post_hormuz_exposed_voyages"])
    importer = exposure_summary(
        enriched,
        "destination_country",
        min_post_exposed_voyages=minimum,
    )
    basin = exposure_summary(enriched, "destination_basin")
    diagnostics = exposure_diagnostics(enriched)
    diagnostics["policy"] = policy
    diagnostics["country_hormuz_exposed_estimates_suppressed"] = int(
        (~importer["country_hormuz_exposed_estimate_estimable"]).sum()
    )
    diagnostics["country_reporting_rule"] = (
        "Country-level Hormuz-exposed changes are not estimable below the "
        f"minimum of {minimum} post-period exposed voyages; basin aggregates "
        "remain descriptive."
    )

    outputs = {
        paths["importer_exposure_voyages_csv"]: enriched,
        paths["importer_exposure_summary_csv"]: importer,
        paths["basin_exposure_summary_csv"]: basin,
    }
    for relative_path, frame in outputs.items():
        output = config.ROOT / relative_path
        output.parent.mkdir(parents=True, exist_ok=True)
        frame.to_csv(output, index=False)
        print(f"wrote {output}")
    diagnostics_path = config.ROOT / paths["importer_basin_exposure_diagnostics_json"]
    diagnostics_path.write_text(json.dumps(diagnostics, indent=2, sort_keys=True) + "\n")
    print(f"wrote {diagnostics_path}")
    print(basin.to_string(index=False))


if __name__ == "__main__":
    main()
