"""Resolve the frozen global carrier census to exact-match GFW identities."""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from hormuz_throughput import config, provenance  # noqa: E402
from hormuz_throughput.registry import get_gfw_vessel_identities_batched  # noqa: E402
from hormuz_throughput.sources.gfw import GFWClient, IDENTITY_DATASET  # noqa: E402


def main() -> None:
    settings = config.settings()
    frame = pd.read_csv(
        config.ROOT / settings["paths"]["global_carrier_frame_csv"],
        dtype={"imo": str},
    )
    client = GFWClient()
    identities = get_gfw_vessel_identities_batched(
        frame, client=client, batch_size=10
    )
    out = provenance.save_raw(
        identities,
        provider="gfw",
        variable="gfw_global_vessel_identity",
        code=IDENTITY_DATASET,
        query={
            "lookup": "exact_imo_batched",
            "eligible_fleet_census": int(frame["imo"].nunique()),
            "batch_size": 10,
        },
        license_note="Global Fishing Watch API terms and attribution apply",
        filename="global_vessel_identity.csv",
        source_payloads=client.source_payloads,
    )
    matched = identities["imo"].nunique() if len(identities) else 0
    print(f"wrote {out}")
    print(f"matched_imo={matched}/{frame['imo'].nunique()}")
    print(f"gfw_vessel_ids={len(identities)}")


if __name__ == "__main__":
    main()
