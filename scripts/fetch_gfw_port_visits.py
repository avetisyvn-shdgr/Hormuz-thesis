"""Fetch equal-length seasonal GFW port-visit windows for the locked roster."""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lngfreight import config, provenance  # noqa: E402
from lngfreight.registry import get_gfw_port_visits  # noqa: E402
from lngfreight.sources.gfw import PORT_VISIT_DATASET  # noqa: E402


# End dates are exclusive under the GFW API. Each window contains 94 days and
# uses the same calendar season to avoid introducing a seasonal comparison bias.
WINDOWS = {
    "pre": ("2025-02-28", "2025-06-02"),
    "post": ("2026-02-28", "2026-06-02"),
}


def main() -> None:
    settings = config.settings()
    identity_path = config.ROOT / settings["paths"]["gfw_vessel_identity_csv"]
    identities = pd.read_csv(identity_path, dtype={"imo": str})
    visits = get_gfw_port_visits(identities["vessel_id"].tolist(), WINDOWS)
    out = provenance.save_raw(
        visits,
        provider="gfw",
        variable="gfw_port_visits",
        code=PORT_VISIT_DATASET,
        query={"windows": WINDOWS, "end_date_semantics": "exclusive"},
        license_note="Global Fishing Watch API terms and attribution apply",
        filename="port_visits.csv",
    )
    print(f"wrote {out}")
    print(f"rows={len(visits)}")
    for period in WINDOWS:
        subset = visits.loc[visits["sample_period"] == period]
        print(
            f"{period}: visits={len(subset)} "
            f"vessel_ids={subset['vessel_id'].nunique()}"
        )


if __name__ == "__main__":
    main()
