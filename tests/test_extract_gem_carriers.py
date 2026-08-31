from datetime import datetime
import json

from openpyxl import Workbook
from openpyxl.utils.datetime import to_excel
import pytest

from scripts.extract_gem_carriers import REQUIRED_COLUMNS, extract


def _valid_imo(prefix: str) -> int:
    checksum = sum(
        int(digit) * weight
        for digit, weight in zip(prefix, range(7, 1, -1))
    ) % 10
    return int(prefix + str(checksum))


def _write_workbook(path, records):
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "data"
    headers = sorted(REQUIRED_COLUMNS)
    worksheet.append(headers)
    for row_number, record in records:
        for column_number, header in enumerate(headers, start=1):
            worksheet.cell(row=row_number, column=column_number, value=record.get(header))
    workbook.save(path)
    return headers


def _record(imo: int) -> dict[str, object]:
    return {
        "IMO number": imo,
        "IMO number [ref]": "source",
        "Name": f"Vessel {imo}",
        "Status": "active",
        "Capacity": 174000,
        "Capacity [ref]": "source",
        "Vessel type": "conventional",
        "Delivery year": 2020,
        "Shipowner": "Owner",
        "Propulsion type": "DFDE",
    }


def test_extract_reads_dynamic_extent_and_writes_provenance(tmp_path):
    source = tmp_path / "carrier.xlsx"
    first = _record(_valid_imo("900000"))
    first["Delivery year"] = datetime(2020, 1, 2)
    second = _record(_valid_imo("900001"))
    headers = _write_workbook(source, [(2, first), (1200, second)])
    output = tmp_path / "carrier.json"
    metadata_output = tmp_path / "carrier.metadata.json"

    records, metadata = extract(source, output, metadata_output)

    assert len(records) == 2
    assert records[0]["Delivery year"] == int(to_excel(datetime(2020, 1, 2)))
    assert records[1]["IMO number"] == second["IMO number"]
    assert json.loads(output.read_text(encoding="utf-8")) == records
    assert metadata["extracted_columns"] == headers
    assert metadata["extracted_rows"] == 2
    assert metadata["extraction_tool"] == "openpyxl"
    assert len(metadata["source_sha256"]) == 64
    assert json.loads(metadata_output.read_text(encoding="utf-8")) == metadata


def test_extract_rejects_duplicate_imo_numbers(tmp_path):
    source = tmp_path / "carrier.xlsx"
    record = _record(_valid_imo("900002"))
    _write_workbook(source, [(2, record), (3, record)])

    with pytest.raises(ValueError, match="duplicate IMO"):
        extract(source, tmp_path / "out.json", tmp_path / "metadata.json")
