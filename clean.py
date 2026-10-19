"""
clean.py

CLI entry point for the spreadsheet-cleaning tool.

Usage:
    python clean.py --input messy.xlsx --output clean.csv --model claude-sonnet-4-6

Pipeline: serialize.py (file -> text) -> model_client.py (text -> validated
JSON) -> writer.py (JSON -> CSV with confidence column).
"""

import argparse
import sys
import time

from src.serializer import serialize_file
from src.model_client import clean_with_model, ModelClientError, get_usage_and_cost
from src.writer import write_clean_csv

def main():
    parser = argparse.ArgumentParser(
        description="Clean a messy spreadsheet into a structured CSV with per-row confidence scores."
    )
    parser.add_argument("--input", required=True, help="Path to the messy input file (.xlsx or .csv)")
    parser.add_argument("--output", required=True, help="Name of the output CSV file to write cleaned data to; results in /results/<output>.csv")
    parser.add_argument("--model", required=True, help="Model name to use, e.g. claude-sonnet-4-6")
    parser.add_argument(
        "--max-tokens", type=int, default=1000, help="Max output tokens for the model call (default 4096)"
    )
    args = parser.parse_args()

    print(f"[1/3] Serializing {args.input} ...")
    try:
        serialized_text = serialize_file(args.input)
    except (ValueError, FileNotFoundError) as e:
        print(f"ERROR: failed to read/serialize input file: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"[2/3] Sending to model '{args.model}' for cleaning ...")
    start = time.time()
    try:
        clean_data, usage_and_cost = clean_with_model(serialized_text, args.model, max_tokens=args.max_tokens)
    except ModelClientError as e:
        print(f"ERROR: model cleaning failed: {e}", file=sys.stderr)
        sys.exit(1)
    elapsed = time.time() - start
    print(f"      done in {elapsed:.1f}s")

    print(f"[3/3] Writing cleaned output to {args.output} ...")
    write_clean_csv(clean_data, args.output)

    n_rows = len(clean_data["rows"])
    n_flagged = sum(1 for r in clean_data["rows"] if r.get("confidence") is not None)
    print(f"Done. {n_rows} rows written, {n_flagged} flagged with a confidence score.")
    print(f"Usage: {usage_and_cost['input_tokens']} input tokens, {usage_and_cost['output_tokens']} output tokens, {usage_and_cost['total_tokens']} total tokens.")

if __name__ == "__main__":
    main()