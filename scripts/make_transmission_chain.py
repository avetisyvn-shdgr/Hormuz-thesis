"""Package the cross-source evidence cascade into one table + narrative.

Reads only frozen processed artifacts (no recomputation) and assembles the
five-link transmission chain for the mechanism/corridor-aligned 94-day window.
The active primary PortWatch counterfactual is the 130-day result in
reports/run_output.md and reports/current_results_summary.md. Outputs a tidy CSV
and a short markdown narrative. Kept outside run_all.py.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lngfreight import config  # noqa: E402
from lngfreight.transmission_chain import build_evidence_cascade  # noqa: E402

PROC = config.ROOT / "data/processed"


def _load():
    results = pd.read_csv(PROC / "corridor_transmission_results.csv")
    hz = results.loc[
        results["corridor"].eq("strait_of_hormuz") & results["target"].eq("n_tanker")
    ].iloc[0]

    stress = pd.read_csv(PROC / "donor_contamination_stress.csv")
    donor_sep = float(stress.loc[
        stress["screen"].eq("pessimistic_union") & stress["value_col"].eq("n_tanker"),
        "separation_vs_placebo_p95",
    ].iloc[0])

    wto = json.loads((PROC / "gulf_departure_wto_validation_summary.json").read_text())
    pre, post = wto["periods"]["pre"], wto["periods"]["post"]

    comp = pd.read_csv(PROC / "inferred_capacity_nautical_miles_comparison.csv")
    r30 = comp.loc[comp["terminal_match_radius_km"].eq(30)].iloc[0]

    boot = json.loads((PROC / "inferred_capacity_nautical_miles_bootstrap.json").read_text())
    decomp = json.loads((PROC / "inferred_capacity_nautical_miles_decomposition.json").read_text())
    composition_share = 100.0 * decomp["common_route_composition_change"] / decomp["common_route_total_change"]

    # Destination risers: alternative corridors above their counterfactual (n_tanker).
    risers = results.loc[results["target"].eq("n_tanker")].nlargest(3, "signed_deviation")
    destination_risers = dict(zip(risers["corridor"], risers["signed_deviation"]))

    return dict(
        hormuz_observed=float(hz["observed_sum"]),
        hormuz_counterfactual=float(hz["counterfactual_sum"]),
        hormuz_signed_deviation=float(hz["signed_deviation"]),
        hormuz_rw_p=float(hz["romano_wolf_p_value"]),
        donor_separation_pessimistic=donor_sep,
        gfw_pre=float(pre["gfw_departure_calls"]),
        gfw_post=float(post["gfw_departure_calls"]),
        wto_pre=float(pre["wto_mean_outbound_volume_index"]),
        wto_post=float(post["wto_mean_outbound_volume_index"]),
        voyages_pre=float(r30["expanded_pre_routed_voyages"]),
        voyages_post=float(r30["expanded_post_routed_voyages"]),
        total_pre=float(r30["expanded_pre_total_nominal_m3_nm"]),
        total_post=float(r30["expanded_post_total_nominal_m3_nm"]),
        mean_per_voyage_pct=float(r30["expanded_mean_per_voyage_percent_change"]),
        mean_bca_lower=float(boot["bca_ci_lower"]),
        mean_bca_upper=float(boot["bca_ci_upper"]),
        composition_share_pct=composition_share,
        destination_risers=destination_risers,
    )


NARRATIVE = """# Transmission chain — cross-source evidence cascade

**Status:** Exploratory synthesis, updated 2026-07-18. Packages frozen results;
computes nothing new. This chain uses the **94-day mechanism/corridor-aligned
window** so Layer 1 lines up with the GFW/WTO and corridor-validation branches.
It is **descriptive triangulation**, not a causal ton-mile multiplier. The active
primary PortWatch headline remains the 130-day AR-only counterfactual in
`reports/run_output.md` and `reports/current_results_summary.md`.

## The one-paragraph argument

A Strait-of-Hormuz disruption shows up as a **cascade across five independent
evidence layers** in the 94-day mechanism-aligned window. (1) Hormuz tanker
throughput collapses ~95% below its own pre-treatment counterfactual, and the
gap separates from a clean donor pool even under a pessimistic contamination
screen. (2) The collapse is **commodity-specific and cross-validated**:
GFW-inferred Gulf LNG departures and the
independent WTO/AXSMarine outbound index both fall ~93–99% with no calibration.
(3) The LNG fleet **contracts**: resolved Gulf voyages and aggregate inferred
capacity-distance both decline. (4) Among voyages that still complete, mean
capacity-distance **rises ~10%**, but a Kitagawa/Oaxaca decomposition shows this
is overwhelmingly a **route-composition shift, not route elongation**. (5)
Consistent with substitution, **alternative corridors rise** (Cape of Good Hope,
Yucatan, Panama). The honest reading is **contraction plus substitution**, not an
aggregate ton-mile multiplier — the strong freight-multiplier claim is not
supported on free data and is explicitly retired.

## The cascade

{table}

## Interpretation boundaries (load-bearing)

- Window discipline matters: this table is the 94-day corridor/GFW-WTO-aligned
  synthesis window. Do not cite its 5,366 counterfactual or 245 observed transits
  as the active 130-day primary headline.
- Every layer is descriptive; none establishes a causal ATT or observed cargo
  ton-miles or freight rates (those need proprietary access that is unavailable).
- Layers 2–4 rest on terminal-sequence inference (laden state not observed) and
  carry right-censoring and AIS-coverage caveats.
- The cross-source agreement in layer 2 is the strongest single result and should
  anchor the narrative; the foundation-model work is a forecasting cross-check
  only.
"""


def _to_markdown(df: pd.DataFrame) -> str:
    """Minimal GitHub-flavoured markdown table (avoids a tabulate dependency)."""
    cols = list(df.columns)
    cells = df.astype(object).where(df.notna(), "").astype(str)
    head = "| " + " | ".join(cols) + " |"
    sep = "| " + " | ".join("---" for _ in cols) + " |"
    body = "\n".join(
        "| " + " | ".join(row) + " |" for row in cells.to_numpy().tolist()
    )
    return "\n".join([head, sep, body])


def main() -> None:
    values = _load()
    cascade = build_evidence_cascade(**values)

    csv_path = config.ROOT / config.settings()["paths"]["transmission_chain_csv"]
    cascade.to_csv(csv_path, index=False)

    md_path = config.ROOT / "reports/transmission_chain_summary.md"
    md_path.write_text(NARRATIVE.format(table=_to_markdown(cascade)), encoding="utf-8")

    pd.set_option("display.width", 240)
    pd.set_option("display.max_columns", None)
    print(cascade.to_string(index=False))
    print(f"\nwrote {csv_path}")
    print(f"wrote {md_path}")


if __name__ == "__main__":
    main()
