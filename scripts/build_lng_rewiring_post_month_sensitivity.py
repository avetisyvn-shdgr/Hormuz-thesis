"""Build leave-one-post-month LNG typology sensitivity.

The artifact recomputes the descriptive pre/post summary, graph metrics, and
rule-based typology after dropping each available post month in turn. It is a
classification-stability diagnostic, not a causal estimator.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from hormuz_throughput import config  # noqa: E402
from hormuz_throughput.network_rewiring import (  # noqa: E402
    build_rewiring_network,
    post_month_typology_sensitivity,
    registered_rewiring_input_paths,
)


def _load_or_build_network() -> pd.DataFrame:
    network_path = config.ROOT / config.settings()["paths"]["lng_rewiring_network_csv"]
    if network_path.exists():
        return pd.read_csv(network_path)
    return build_rewiring_network(
        *registered_rewiring_input_paths(
            "build_lng_rewiring_post_month_sensitivity"
        )
    )


def main() -> None:
    paths = config.settings()["paths"]
    network = _load_or_build_network()
    sensitivity = post_month_typology_sensitivity(network)

    out = config.ROOT / paths["lng_rewiring_post_month_sensitivity_csv"]
    out.parent.mkdir(parents=True, exist_ok=True)
    sensitivity.to_csv(out, index=False)

    print(f"wrote {out}")
    print(sensitivity[[
        "dropped_month",
        "destination_unit",
        "headline_primary_typology",
        "dropped_primary_typology",
        "changed_under_drop",
        "any_primary_typology_change",
        "post_months_after_drop",
        "coverage_note",
    ]].to_string(index=False))


if __name__ == "__main__":
    main()
