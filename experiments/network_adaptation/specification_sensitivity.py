"""Emit the Hormuz shortfall specification-sensitivity table as an artifact.

The legacy counterfactual pipeline and the current network-adaptation event
forecasts score the identical 130 post-cutoff days, but they train on different
information sets.  The legacy pipeline reads ``panel_aligned.csv``, which starts
at the ``analysis_start`` of ``config/model_admission_protocol.yaml``; the event
forecasts read the raw PortWatch snapshot, which starts three years earlier and
gives Chronos a longer context window.  The direction of the Chronos-versus-AR
difference reverses between the two, so the difference is a reportable
sensitivity and needs a file behind it rather than a hand-typed table.

This script refits nothing.  It reads four frozen forecast artifacts and
recomputes their sums on the common scored window.

Run with:

    .venv/bin/python -m experiments.network_adaptation.specification_sensitivity
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from experiments.network_adaptation.protocol import AdaptationProtocol, load_protocol
from experiments.panel_bakeoff.protocol import file_sha256, load_raw_panel


ROOT = Path(__file__).resolve().parents[2]
LEGACY_PANEL = ROOT / "data/processed/panel_aligned.csv"
LEGACY_CHRONOS = ROOT / "data/processed/tsfm_counterfactual_daily.csv"
LEGACY_AR = ROOT / "data/processed/counterfactual_post_treatment.csv"
LEGACY_TARGET = "hormuz_tanker_transits"
HORMUZ = "Strait of Hormuz"

LEGACY_SPEC = "legacy_admission_protocol"
EXPANDED_SPEC = "expanded_history_event_panel"
COLUMNS = (
    "spec",
    "train_start",
    "context_length",
    "model",
    "observed_sum",
    "counterfactual_sum",
    "cumulative_gap",
    "pct_below_counterfactual",
)


def _training_span(index: pd.DatetimeIndex, cutoff: pd.Timestamp) -> tuple[pd.Timestamp, int]:
    """Return the first training date and the number of pre-cutoff days."""
    train = index[index < cutoff]
    if train.empty:
        raise ValueError("no pre-cutoff training observations were found.")
    if train.has_duplicates:
        raise ValueError("the training index contains duplicate dates.")
    expected = pd.date_range(train.min(), train.max(), freq="D")
    if not pd.DatetimeIndex(train.sort_values()).equals(expected):
        raise ValueError("the training index is not a contiguous daily range.")
    return train.min(), len(train)


def _scored(frame: pd.DataFrame, protocol: AdaptationProtocol, label: str) -> pd.DataFrame:
    """Validate one model's 130 scored Hormuz days and return them sorted."""
    part = frame.sort_values("date").reset_index(drop=True)
    if len(part) != protocol.horizon:
        raise ValueError(f"{label}: expected {protocol.horizon} scored days, found {len(part)}.")
    if part["date"].min() != protocol.cutoff or part["date"].max() != protocol.event_end:
        raise ValueError(f"{label}: scored window differs from the frozen event window.")
    if part["date"].duplicated().any():
        raise ValueError(f"{label}: scored window contains duplicate dates.")
    if part[["y_true", "y_pred"]].isna().any().any():
        raise ValueError(f"{label}: scored window contains missing actuals or forecasts.")
    return part


def _row(
    part: pd.DataFrame,
    *,
    spec: str,
    train_start: pd.Timestamp,
    context_length: int,
    model: str,
) -> dict[str, object]:
    observed = float(part["y_true"].sum())
    counterfactual = float(part["y_pred"].sum())
    if counterfactual <= 0:
        raise ValueError(f"{spec}/{model}: non-positive counterfactual sum.")
    return {
        "spec": spec,
        "train_start": str(train_start.date()),
        "context_length": int(context_length),
        "model": model,
        "observed_sum": observed,
        "counterfactual_sum": counterfactual,
        "cumulative_gap": counterfactual - observed,
        "pct_below_counterfactual": 100.0 * (1.0 - observed / counterfactual),
    }


def _legacy_rows(protocol: AdaptationProtocol) -> list[dict[str, object]]:
    panel = pd.read_csv(LEGACY_PANEL, parse_dates=["date"]).set_index("date")
    train_start, train_days = _training_span(pd.DatetimeIndex(panel.index), protocol.cutoff)

    chronos = pd.read_csv(LEGACY_CHRONOS, parse_dates=["date"])
    chronos = chronos.loc[
        chronos["model"].eq("chronos2") & chronos["target"].eq(LEGACY_TARGET)
    ]
    ar = pd.read_csv(LEGACY_AR, parse_dates=["date"])
    ar = ar.loc[
        ar["model"].eq(protocol.robustness_model) & ar["target"].eq(LEGACY_TARGET)
    ]
    return [
        _row(
            _scored(chronos, protocol, "legacy chronos2"),
            spec=LEGACY_SPEC,
            train_start=train_start,
            context_length=min(train_days, protocol.primary_context_length),
            model=protocol.primary_model,
        ),
        _row(
            _scored(ar, protocol, "legacy ar_lag1_7"),
            spec=LEGACY_SPEC,
            train_start=train_start,
            context_length=train_days,
            model=protocol.robustness_model,
        ),
    ]


def _expanded_rows(protocol: AdaptationProtocol) -> list[dict[str, object]]:
    raw = load_raw_panel(protocol.raw_path)
    index = pd.DatetimeIndex(sorted(raw["date"].unique()))
    train_start, train_days = _training_span(index, protocol.cutoff)

    event = pd.read_csv(protocol.outputs["event_forecasts"], parse_dates=["date"])
    event = event.loc[
        event["portname"].eq(HORMUZ) & event["vessel_class"].eq(protocol.primary_class)
    ]
    rows = []
    for model, context_length in (
        (protocol.primary_model, min(train_days, protocol.primary_context_length)),
        (protocol.robustness_model, train_days),
    ):
        rows.append(
            _row(
                _scored(event.loc[event["model"].eq(model)], protocol, f"expanded {model}"),
                spec=EXPANDED_SPEC,
                train_start=train_start,
                context_length=context_length,
                model=model,
            )
        )
    return rows


def _model_difference(table: pd.DataFrame, spec: str, protocol: AdaptationProtocol) -> float:
    """Chronos cumulative gap as a percentage difference from the AR gap."""
    part = table.loc[table["spec"].eq(spec)].set_index("model")
    chronos = part.loc[protocol.primary_model, "cumulative_gap"]
    ar = part.loc[protocol.robustness_model, "cumulative_gap"]
    return 100.0 * (chronos - ar) / ar


def _markdown(table: pd.DataFrame, protocol: AdaptationProtocol) -> str:
    labels = {LEGACY_SPEC: "Legacy", EXPANDED_SPEC: "Expanded history"}
    lines = [
        "| Specification | Training start | Chronos shortfall | AR shortfall | Model difference |",
        "|---|---|---:|---:|---|",
    ]
    for spec in (LEGACY_SPEC, EXPANDED_SPEC):
        part = table.loc[table["spec"].eq(spec)].set_index("model")
        chronos = part.loc[protocol.primary_model]
        ar = part.loc[protocol.robustness_model]
        difference = _model_difference(table, spec, protocol)
        window = f"{chronos['train_start']}"
        if int(chronos["context_length"]) < int(ar["context_length"]):
            window += f" (Chronos: trailing {int(chronos['context_length']):,}d)"
        lines.append(
            f"| {labels[spec]} | {window} | {chronos['cumulative_gap']:,.0f} | "
            f"{ar['cumulative_gap']:,.0f} | Chronos {abs(difference):.1f}% "
            f"{'above' if difference > 0 else 'below'} |"
        )
    return "\n".join(lines)


def main() -> None:
    protocol = load_protocol()
    if file_sha256(protocol.raw_path) != protocol.expected_raw_sha256:
        raise RuntimeError("the PortWatch snapshot hash changed.")

    table = pd.DataFrame(_legacy_rows(protocol) + _expanded_rows(protocol), columns=list(COLUMNS))
    if list(table.columns) != list(COLUMNS):
        raise AssertionError("the specification-sensitivity schema changed.")
    if table["observed_sum"].nunique() != 1:
        raise AssertionError(
            "the two specifications do not score the same observed Hormuz total; "
            "they are not comparable."
        )
    if table.duplicated(["spec", "model"]).any() or len(table) != 4:
        raise AssertionError("the specification-sensitivity table is incomplete.")

    path = protocol.outputs["specification_sensitivity"]
    path.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(path, index=False)

    sources = {
        "legacy_training_panel": LEGACY_PANEL,
        "legacy_chronos_daily": LEGACY_CHRONOS,
        "legacy_ar_daily": LEGACY_AR,
        "expanded_training_panel": protocol.raw_path,
        "expanded_event_forecasts": protocol.outputs["event_forecasts"],
    }
    manifest = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "purpose": (
            "Hormuz 130-day shortfall under two training-information sets scored on "
            "identical dates. Refits nothing; reads frozen forecast artifacts."
        ),
        "scored_window": {
            "start": str(protocol.cutoff.date()),
            "end": str(protocol.event_end.date()),
            "days": protocol.horizon,
            "observed_sum": float(table["observed_sum"].iloc[0]),
        },
        "chronos_context_length_cap": protocol.primary_context_length,
        "model_difference_pct_chronos_vs_ar": {
            spec: _model_difference(table, spec, protocol)
            for spec in (LEGACY_SPEC, EXPANDED_SPEC)
        },
        "pct_below_counterfactual_range": [
            float(table["pct_below_counterfactual"].min()),
            float(table["pct_below_counterfactual"].max()),
        ],
        "sources_sha256": {
            name: file_sha256(source) for name, source in sorted(sources.items())
        },
        "outputs_sha256": {str(path.relative_to(ROOT)): file_sha256(path)},
    }
    protocol.outputs["specification_sensitivity_manifest"].write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    print(table.to_string(index=False))
    print()
    print(_markdown(table, protocol))
    print()
    low, high = manifest["pct_below_counterfactual_range"]
    print(
        f"Observed Hormuz traffic is {low:.1f}-{high:.1f}% below counterfactual across "
        f"both specifications ({table['observed_sum'].iloc[0]:,.0f} observed)."
    )
    print(f"\nwrote {path}")
    print(f"wrote {protocol.outputs['specification_sensitivity_manifest']}")


if __name__ == "__main__":
    main()
