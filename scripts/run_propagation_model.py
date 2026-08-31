"""Phase 2 - fit the multi-event chokepoint propagation model.

Reads `config/multi_event_propagation.yaml`, fits the shared-profile rank-1
response model on the training events, runs the sanity gate and the placebo
null, and writes results for the Phase 2 stop-and-report.

Hormuz stays sealed. The script refuses to run if any training window reaches
past the held-out onset.

Usage:
    python scripts/run_propagation_model.py
    python scripts/run_propagation_model.py --value-col n_container --draws 400
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from hormuz_throughput import config                                      # noqa: E402
from hormuz_throughput.propagation import (                               # noqa: E402
    EventSpec,
    fit_propagation,
    placebo_reallocation,
    sanity_gate,
    screened_receivers,
)
from hormuz_throughput.spatial import slugify_portname, wide_chokepoint_panel  # noqa: E402

SPEC_PATH = config.CONFIG_DIR / "multi_event_propagation.yaml"


def load_specs(spec: dict) -> list[EventSpec]:
    out = []
    for name, ev in spec["events"].items():
        unit = ev.get("unit") or ev["units"][0]
        out.append(
            EventSpec(
                name=name,
                unit=slugify_portname(unit),
                onset=pd.Timestamp(ev["onset"]),
                role=ev.get("role", "train"),
                mechanism=ev.get("mechanism", ""),
            )
        )
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--value-col", default=None)
    ap.add_argument("--horizon-weeks", type=int, default=None)
    ap.add_argument("--draws", type=int, default=200)
    args = ap.parse_args()

    spec = yaml.safe_load(SPEC_PATH.read_text(encoding="utf-8"))
    value_col = args.value_col or spec["panel"]["primary_value_column"]
    horizon = args.horizon_weeks or int(spec["model"].get("horizon_weeks", 8))
    specs = load_specs(spec)

    win = spec["training_window"]
    panel = wide_chokepoint_panel(
        value_col=value_col, start=win["start"], end=win["end"]
    )
    fit = fit_propagation(panel, specs, horizon_weeks=horizon)

    gate_cfg = spec["model"]["sanity_gate"]
    emitter, receiver = (slugify_portname(x) for x in gate_cfg["required_edge"])
    gate = sanity_gate(fit, "red_sea", emitter, receiver)

    affected = sorted({s.unit for s in specs})
    nulls = {}
    for s in [x for x in specs if not x.held_out]:
        draw = placebo_reallocation(
            panel, s, affected, horizon_weeks=horizon, n_draws=args.draws
        )
        obs = fit.reallocation_share[s.name]["gross_gain_per_day"]
        g = draw["gross_gain_per_day"]
        nulls[s.name] = {
            "observed_gross_gain_per_day": obs,
            "null_median": float(g.median()),
            "null_p95": float(g.quantile(0.95)),
            "percentile_of_observed": float((g < obs).mean() * 100),
            "n_draws": int(len(g)),
            "screened_receivers": screened_receivers(
                fit.response[s.name], panel, s.onset, s.unit
            ),
        }

    out = Path("data/processed")
    out.mkdir(parents=True, exist_ok=True)
    suffix = "" if value_col == spec["panel"]["primary_value_column"] else f"__{value_col}"
    fit.receiver_loadings.to_csv(out / f"propagation_receiver_loadings{suffix}.csv")
    fit.profile.to_csv(out / f"propagation_response_profile{suffix}.csv")
    payload = {
        "value_col": value_col,
        "horizon_weeks": horizon,
        "diagnostics": fit.diagnostics,
        "amplitude": fit.amplitude,
        "reallocation_accounting": fit.reallocation_share,
        "sanity_gate": gate,
        "placebo_null": nulls,
    }
    (out / f"propagation_results{suffix}.json").write_text(
        json.dumps(payload, indent=2, default=str), encoding="utf-8"
    )

    print(f"value column        : {value_col}")
    print(f"training events     : {fit.diagnostics['n_train_events']}")
    print(f"variance explained  : {fit.diagnostics['variance_explained']:.3f}")
    print(f"sealed              : {fit.diagnostics['sealed_events']}")
    print(f"\nSANITY GATE  {emitter} -> {receiver}")
    print(f"  loading {gate['loading']:.3f}  rank {gate['rank_among_receivers']}"
          f"/{gate['n_receivers']}  passed={gate['passed']}")
    print("\nREALLOCATION ACCOUNTING vs placebo null")
    print(f"  {'event':<20}{'obs':>9}{'null p50':>10}{'null p95':>10}{'pctile':>8}{'screened':>10}")
    for k, v in nulls.items():
        print(f"  {k:<20}{v['observed_gross_gain_per_day']:>9.1f}"
              f"{v['null_median']:>10.1f}{v['null_p95']:>10.1f}"
              f"{v['percentile_of_observed']:>7.0f}%{len(v['screened_receivers']):>10}")
    print("\nSTOP AND REPORT. Read the percentile column before quoting any "
          "reallocation figure: below ~95 means the aggregate is not separable "
          "from noise, whatever the point estimate says.")


if __name__ == "__main__":
    main()
