"""
writer.py

Takes a validated clean-table dict (see schema.py) and writes it out as a
CSV: the declared columns, plus a trailing `confidence` column that is only
populated for rows the model flagged as uncertain (blank otherwise, per
spec -- "a confidence value on every row it was unsure about").

A `notes` column is included too, since it's the human-readable explanation
of *why* a row is uncertain -- useful for reviewers, cheap to keep.

Writes a validated clean_table result to a CSV file.
"""

import csv
from pathlib import Path


def write_clean_csv(data: dict, output_path: str) -> None:
    """Write `data` (as returned/validated by model_client + schema) to a CSV.

    data shape:
        {
            "columns": ["Name", "Amount", ...],
            "rows": [
                {"cells": ["Alice", 120, ...], "confidence": 0.6 or None, "notes": "..." or None},
                ...
            ]
        }

    Each row's "cells" list is aligned with "columns".
    """
    columns = data["columns"]
    rows = data["rows"]

    fieldnames = columns + ["confidence", "notes"]

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(f"results/{output_path}.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for row in rows:
            cells = row.get("cells", [])

            # Pad or trim so every row has exactly one value per column,
            # with null/missing cells written as blank.
            cells = (list(cells) + [None] * len(columns))[: len(columns)]
            out_row = {col: ("" if val is None else val) for col, val in zip(columns, cells)}

            confidence = row.get("confidence")
            out_row["confidence"] = "" if confidence is None else confidence

            notes = row.get("notes")
            out_row["notes"] = "" if notes is None else notes

            writer.writerow(out_row)


