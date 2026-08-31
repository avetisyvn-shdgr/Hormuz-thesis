from __future__ import annotations

import pandas as pd

from hormuz_throughput.freight_integration import build_freight_mechanism_integration


def test_integration_preserves_evidence_roles_and_direction_conventions():
    dates = pd.date_range("2026-03-01", periods=14, freq="D")
    port = pd.DataFrame({"date": dates, "model": "ar_lag1_7", "target": "hormuz_tanker_transits", "y_true": 2.0, "y_pred": 10.0})
    wto = pd.DataFrame({"date": dates, "observed_lng_volume_index": 5.0, "ar_counterfactual": 20.0})
    weeks = pd.to_datetime(["2026-03-06", "2026-03-13"])
    freight = pd.concat([
        pd.DataFrame({"week_end": weeks, "series": name, "observed_usd_per_day": 100.0, "counterfactual_usd_per_day": 40.0, "deviation_usd_per_day": 60.0})
        for name in ["east_spot", "west_spot", "one_year_charter"]
    ], ignore_index=True)
    context = pd.DataFrame({"date": dates, "ttf_eur_per_mwh": 30.0, "vlsfo_singapore_usd_per_metric_tonne": 600.0, "ttf_eur_per_mwh_pre_zscore": 1.0, "vlsfo_singapore_usd_per_metric_tonne_pre_zscore": 2.0})
    panel, summary, manifest = build_freight_mechanism_integration(port, wto, freight, context, first_post_week="2026-03-06")
    indexed = summary.set_index("measure")
    assert indexed.loc["PortWatch tanker transits", "directional_deviation"] == 8
    assert indexed.loc["East of Suez spot assessment", "directional_deviation"] == 60
    assert indexed["identified_mediation"].eq(False).all()
    assert len(panel) == 2
    assert "triangulation" in manifest["claim_boundary"]
