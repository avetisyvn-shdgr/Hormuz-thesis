import pandas as pd

from lngfreight.carrier_frame import build_global_carrier_frame


def _imo(prefix: str) -> str:
    checksum = sum(
        int(digit) * weight
        for digit, weight in zip(prefix, range(7, 1, -1))
    ) % 10
    return prefix + str(checksum)


def test_global_frame_applies_status_type_capacity_and_imo_rules():
    tracker = pd.DataFrame({
        "IMO number": [_imo("900000"), _imo("900001"), _imo("900002"), "bad"],
        "Name": ["A", "B", "C", "D"],
        "Status": ["active", "on order", "active", "active"],
        "Vessel type": ["conventional", "conventional", "FSRU", "icebreaker"],
        "Capacity": [174000, 174000, 174000, 174000],
        "Capacity [ref]": ["source", "source", "source", "source"],
        "IMO number [ref]": ["source"] * 4,
        "Delivery year": [2020] * 4,
        "Shipowner": ["Owner"] * 4,
        "Propulsion type": ["X-DF"] * 4,
    })
    result, diagnostics = build_global_carrier_frame(
        tracker, minimum_capacity_m3=125000,
    )
    assert result["vessel_name"].tolist() == ["A"]
    assert diagnostics["eligible_rows"] == 1


def test_missing_capacity_reference_is_flagged_not_filled():
    tracker = pd.DataFrame({
        "IMO number": [_imo("900003")], "Name": ["A"], "Status": ["active"],
        "Vessel type": ["icebreaker"], "Capacity": [172000],
        "Capacity [ref]": [None], "IMO number [ref]": ["imo source"],
        "Delivery year": [2019], "Shipowner": ["Owner"],
        "Propulsion type": ["DFDE"],
    })
    result, diagnostics = build_global_carrier_frame(
        tracker, minimum_capacity_m3=125000,
    )
    assert bool(result.loc[0, "capacity_reference_missing"]) is True
    assert diagnostics["missing_capacity_references"] == 1
