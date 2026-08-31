from __future__ import annotations

import pandas as pd

from hormuz_throughput.bloomberg_market import build_market_context_panel


def test_context_panel_standardizes_on_pre_period_without_filling_gap():
    frames = {
        "ttf_gas": pd.DataFrame(
            {"date": pd.to_datetime(["2025-01-01", "2025-01-03", "2025-01-06"]), "value": [10, 20, 100]}
        ),
        "vlsfo_singapore": pd.DataFrame(
            {"date": pd.to_datetime(["2025-01-01", "2025-01-02", "2025-01-03", "2025-01-06"]), "value": [1, 2, 3, 20]}
        ),
    }
    manifest = {
        "governance": {"designation": "provenance_limited_secondary"},
        "series": {
            "netherlands_ttf_day_ahead": {
                "displayed_series_name": "TTF", "unit": "EUR/MWh", "currency": "EUR", "expected_sha256": "1" * 64
            },
            "clearlynx_vlsfo_singapore": {
                "displayed_series_name": "VLSFO", "unit": "USD/t", "currency": "USD", "expected_sha256": "2" * 64
            },
        },
    }
    panel, quality, output_manifest = build_market_context_panel(
        frames,
        manifest,
        study_start="2025-01-01",
        study_end="2025-01-06",
        treatment_cutoff="2025-01-06",
    )
    missing = panel.loc[panel["date"].eq(pd.Timestamp("2025-01-02")), "ttf_eur_per_mwh"]
    assert missing.isna().all()
    assert panel.loc[panel["date"].lt("2025-01-06"), "ttf_eur_per_mwh_pre_zscore"].mean() == 0
    assert quality.set_index("logical_name").loc["ttf_gas", "missing_business_days"] == 1
    assert output_manifest["model_role"].startswith("context only")
