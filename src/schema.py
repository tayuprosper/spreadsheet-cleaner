"""
schema.py

Defines the exact JSON shape we force the model to return when cleaning a
messy spreadsheet, plus validation so a malformed model response fails loudly
instead of silently corrupting the output CSV.

The core design decision (per spec): confidence is only present on rows the
model was unsure about. Confident rows carry confidence = null.

Rows are positional: each row's "cells" list is aligned with the top-level
"columns" list. This is far more reliable across models than a free-form
column-name -> value object, where models tend to invent or misspell keys,
or return the object as a JSON-encoded string.
"""

from typing import Any


# JSON schema (for use with the model's tool-use feature).
# Columns vary per messy file, so the column names are declared once at the
# top level and every row carries its values in the same order.
CLEAN_TABLE_SCHEMA = {
    "name": "clean_table",
    "description": "A cleaned, structured table extracted from a messy spreadsheet.",
    "input_schema": {
        "type": "object",
        "properties": {
            "columns": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Ordered list of column names in the cleaned table.",
            },
            "rows": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "cells": {
                            "type": "array",
                            "items": {"type": ["string", "number", "null"]},
                            "description": (
                                "Cleaned cell values in the same order as 'columns'. "
                                "The length MUST equal the number of columns. Each cell "
                                "holds ONLY a value, never explanations, comments or "
                                "parenthetical remarks. Use null only when the source cell "
                                "is empty. Normalize formats consistently across rows. "
                                "Correct obvious mistakes only when there is exactly one "
                                "sensible correct value (record the original in 'notes'). "
                                "If a value is wrong but cannot be confidently corrected, "
                                "keep the original value as-is and explain in 'notes'."
                            ),
                        },
                        "confidence": {
                            "type": ["number", "null"],
                            "description": (
                                "How sure you are (0-1) that this row's cells correctly "
                                "represent the intended source data. Lower = more "
                                "uncertain. Null ONLY when every value was clear and needed "
                                "at most formatting normalization. Obvious mistake "
                                "corrected: 0.7-0.95. Value inferred or contradiction "
                                "resolved by judgment: 0.5-0.7. Wrong or broken value that "
                                "could not be corrected and was kept as-is: below 0.5."
                            ),
                        },
                        "notes": {
                            "type": ["string", "null"],
                            "description": (
                                "Short, accurate description of what was corrected (with "
                                "the original value, e.g. \"Email: 'a@@b.cm' -> 'a@b.cm'\") "
                                "or what is still wrong in THIS row, matching the final "
                                "cell values. "
                                "Required whenever confidence is not null; null when "
                                "confidence is null."
                            ),
                        },
                    },
                    "required": ["cells", "confidence", "notes"],
                    "additionalProperties": False,
                },
            },
        },
        "required": ["columns", "rows"],
        "additionalProperties": False,
    },
}


class SchemaValidationError(ValueError):
    pass


def validate_clean_table(data: Any) -> None:
    """Raise SchemaValidationError if `data` doesn't match the expected shape.

    This is deliberately stricter than the JSON schema above (which we hand
    to the model as guidance) -- it's the last line of defense before we
    trust the model's output enough to write a CSV from it.
    """
    if not isinstance(data, dict):
        raise SchemaValidationError(f"Top-level response must be an object, got {type(data)}")

    if "columns" not in data or "rows" not in data:
        raise SchemaValidationError("Response must contain 'columns' and 'rows'")

    columns = data["columns"]
    rows = data["rows"]

    if not isinstance(columns, list) or not all(isinstance(c, str) for c in columns):
        raise SchemaValidationError("'columns' must be a list of strings")

    if len(set(columns)) != len(columns):
        raise SchemaValidationError("'columns' contains duplicate names")

    if not isinstance(rows, list):
        raise SchemaValidationError("'rows' must be a list")

    for i, row in enumerate(rows):
        if not isinstance(row, dict):
            raise SchemaValidationError(f"Row {i} is not an object")

        # Cells must be a list aligned with the declared columns -- catches
        # the model dropping, adding, or shifting values in a row.
        cells = row.get("cells")
        if not isinstance(cells, list):
            raise SchemaValidationError(f"Row {i} 'cells' must be a list")
        if len(cells) != len(columns):
            raise SchemaValidationError(
                f"Row {i} has {len(cells)} cells, expected {len(columns)}"
            )
        for j, cell in enumerate(cells):
            if cell is not None and not isinstance(cell, (str, int, float)):
                raise SchemaValidationError(
                    f"Row {i} cell {j} must be a string, number, or null"
                )

        confidence = row.get("confidence")
        if confidence is not None:
            if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
                raise SchemaValidationError(f"Row {i} 'confidence' must be a number or null")
            if not (0 <= confidence <= 1):
                raise SchemaValidationError(f"Row {i} 'confidence' must be between 0 and 1")
            if not row.get("notes"):
                raise SchemaValidationError(
                    f"Row {i} has confidence set but no 'notes' explaining why"
                )

        notes = row.get("notes")
        if notes is not None and not isinstance(notes, str):
            raise SchemaValidationError(f"Row {i} 'notes' must be a string or null")
        if notes and confidence is None:
            raise SchemaValidationError(
                f"Row {i} has notes but confidence is null; a row with issues needs a score"
            )


def row_to_dict(columns: list[str], row: dict) -> dict:
    """Rebuild a column_name -> value dict for a validated row (e.g. for CSV writing)."""
    return dict(zip(columns, row["cells"]))