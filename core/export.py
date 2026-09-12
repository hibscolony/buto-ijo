"""In-memory, portable exports of the actual analysis results."""

from __future__ import annotations

import csv
from io import StringIO
import json
from pathlib import PureWindowsPath
import re


RESULT_COLUMNS = [
    "claim_id", "page", "claim", "prediction", "greenwashing_probability", "confidence"
]


def _spreadsheet_safe(value: object) -> object:
    # CSV quoting alone does not stop a spreadsheet interpreting a formula.
    if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@")):
        return "'" + value
    return value


def results_to_csv(results: list[dict]) -> bytes:
    """Export all supplied claims, with a BOM for Indonesian text in Excel.

    Formula-like strings receive a leading apostrophe for safe spreadsheet
    opening. Numeric probability/confidence values remain actual numeric values.
    """
    output = StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=RESULT_COLUMNS, extrasaction="ignore")
    writer.writeheader()
    for result in results:
        writer.writerow({column: _spreadsheet_safe(result.get(column, "")) for column in RESULT_COLUMNS})
    return output.getvalue().encode("utf-8-sig")


def summary_to_json(summary: dict, document_name: str) -> bytes:
    """Include aggregation settings so a saved score remains interpretable."""
    result = {"document": document_name, **summary}
    return json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False).encode("utf-8")


def safe_export_name(filename: str) -> str:
    """Return a readable filename stem, stripping path traversal and unsafe names."""
    stem = PureWindowsPath(filename).stem
    stem = re.sub(r"[^\w .-]", "_", stem, flags=re.UNICODE).strip(" .")
    return stem[:120] or "document"
