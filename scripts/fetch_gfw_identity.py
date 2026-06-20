"""Match the locked LNG benchmark roster to GFW vessel identities."""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lngfreight import config, provenance  # noqa: E402
from lngfreight.registry import get_gfw_vessel_identities  # noqa: E402
from lngfreight.sources.gfw import IDENTITY_DATASET  # noqa: E402


def main() -> None:
    settings = config.settings()
    roster_path = config.ROOT / settings["paths"]["gfw_lng_vessel_benchmark_csv"]
    roster = pd.read_csv(roster_path, dtype={"imo": str})
    identities = get_gfw_vessel_identities(roster)
    out = provenance.save_raw(
        identities,
        provider="gfw",
        variable="gfw_vessel_identity",
        code=IDENTITY_DATASET,
        query={
            "lookup": "exact_imo",
            "benchmark_vessels": int(roster["imo"].nunique()),
        },
        license_note="Global Fishing Watch API terms and attribution apply",
        filename="vessel_identity.csv",
    )
    matched = identities["imo"].nunique() if len(identities) else 0
    print(f"wrote {out}")
    print(f"matched_imo={matched}/{roster['imo'].nunique()}")
    print(f"gfw_vessel_ids={len(identities)}")


if __name__ == "__main__":
    main()
