"""Opt-in reader for provenance-limited Bloomberg transcription workbooks.

The provider is deliberately local-only. It requires ``BLOOMBERG_EXPORT_DIR``,
verifies the manifest-pinned workbook checksum, preserves the workbook as an
ignored raw source payload, and returns only the standard tidy ``date,value``
contract. It does not interpolate, smooth, deduplicate, or convert blanks to
zero. Registry status ``restricted`` keeps these series out of default runs.
"""
from __future__ import annotations

import os
from pathlib import Path

import pandas as pd

from .. import config
from ..bloomberg_admission import (
    _is_blank,
    load_manifest,
    parse_date,
    parse_decimal,
    sha256_file,
)
from .base import BaseSource, SourcePayload


_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


class BloombergTranscriptionSource(BaseSource):
    name = "bloomberg_transcription"

    @staticmethod
    def _manifest() -> dict:
        return load_manifest(config.ROOT / "config/bloomberg_exports.yaml")

    @staticmethod
    def _export_dir(manifest: dict) -> Path:
        env_name = manifest["export_directory_env"]
        value = os.environ.get(env_name)
        if not value:
            raise RuntimeError(
                f"Missing environment variable {env_name!r}. Point it to the "
                "local Bloomberg workbook directory. Restricted Bloomberg "
                "inputs are never required by the default free-data pipeline."
            )
        path = Path(value).expanduser().resolve()
        if not path.is_dir():
            raise FileNotFoundError(f"Bloomberg export directory not found: {path}")
        return path

    def fetch(self, code: str, start: str, end: str) -> pd.DataFrame:
        manifest = self._manifest()
        governance = manifest["governance"]
        if governance.get("designation") != "provenance_limited_secondary":
            raise ValueError("Bloomberg limited-use governance is not authorized.")
        if governance.get("authorized_by") != "thesis_author":
            raise ValueError("Bloomberg limited-use authorization is missing.")
        if code not in manifest["series"]:
            raise ValueError(
                f"Unknown Bloomberg transcription code {code!r}; expected one of "
                f"{sorted(manifest['series'])}."
            )
        spec = manifest["series"][code]
        if spec.get("analysis_use") != "provenance_limited_secondary":
            raise ValueError(f"Bloomberg series {code!r} is not approved for limited use.")

        path = self._export_dir(manifest) / spec["filename"]
        if not path.is_file():
            raise FileNotFoundError(f"Bloomberg workbook missing: {spec['filename']}")
        actual_sha256 = sha256_file(path)
        if actual_sha256 != spec["expected_sha256"]:
            raise ValueError(
                f"Bloomberg workbook checksum mismatch for {spec['filename']}: "
                f"expected {spec['expected_sha256']}, got {actual_sha256}"
            )

        frame = pd.read_excel(
            path,
            sheet_name=spec["raw_sheet"],
            dtype=object,
            engine="openpyxl",
        )
        date_column = spec["date_column"]
        value_column = spec["value_column"]
        missing_columns = [
            column for column in (date_column, value_column) if column not in frame
        ]
        if missing_columns:
            raise ValueError(
                f"Bloomberg workbook {spec['filename']} is missing columns "
                f"{missing_columns}."
            )

        raw_dates = frame[date_column]
        raw_values = frame[value_column]
        dates = raw_dates.map(parse_date)
        values = raw_values.map(parse_decimal)
        invalid_dates = (~raw_dates.map(_is_blank)) & dates.isna()
        invalid_values = (~raw_values.map(_is_blank)) & values.isna()
        if invalid_dates.any():
            rows = [int(index) + 2 for index in frame.index[invalid_dates][:10]]
            raise ValueError(f"Unparseable Bloomberg dates at workbook rows {rows}.")
        if invalid_values.any():
            rows = [int(index) + 2 for index in frame.index[invalid_values][:10]]
            raise ValueError(f"Unparseable Bloomberg values at workbook rows {rows}.")
        if dates.dropna().duplicated().any():
            duplicates = dates.loc[dates.notna() & dates.duplicated(keep=False)]
            labels = sorted({stamp.date().isoformat() for stamp in duplicates})
            raise ValueError(f"Duplicate Bloomberg dates: {labels[:10]}")

        out = pd.DataFrame({"date": dates, "value": values})
        start_ts = pd.Timestamp(start)
        end_ts = pd.Timestamp(end)
        out = out.loc[out["date"].between(start_ts, end_ts, inclusive="both")]
        if out.dropna(subset=["value"]).empty:
            raise ValueError(
                f"Bloomberg series {code!r} has no priced observations in "
                f"[{start}, {end}]."
            )
        self._capture_source_payload(
            SourcePayload(
                filename=path.name,
                media_type=_MEDIA_TYPE,
                role="provenance_limited_structured_transcription",
                path=path,
            )
        )
        return self._validate(out)
