#!/usr/bin/env python3
"""
Load first-level Letterboxd CSV exports into Supabase (letterboxd_* tables).

Process: truncate each table (delete where _source = 'letterboxd'), then full load from CSV.
Run after exporting from Letterboxd and dropping the CSVs into app/data/letterboxd/.

  make load-letterboxd
  # or from app dir:  python scripts/load_letterboxd.py
  # or from repo root: python app/scripts/load_letterboxd.py

Requires: SUPABASE_URL and SUPABASE_ANON_KEY (or SUPABASE_SERVICE_ROLE_KEY) in .env.
Tables must exist; run app/sql/letterboxd_schema.sql once in Supabase SQL Editor if needed.
"""

import csv
import re
import sys
from pathlib import Path

# Ensure app dir is on path so "from supa import supabase" works when run from repo root or app/
_APP_DIR = Path(__file__).resolve().parent.parent
if str(_APP_DIR) not in sys.path:
    sys.path.insert(0, str(_APP_DIR))

from supa import supabase

LETTERBOXD_DIR = Path(__file__).resolve().parent.parent / "data" / "letterboxd"
SOURCE_TAG = "letterboxd"
BATCH_SIZE = 200


def csv_name_to_table_stem(name: str) -> str:
    """e.g. watched.csv -> letterboxd_watched"""
    return f"letterboxd_{Path(name).stem}"


def header_to_snake_case(header: str) -> str:
    """Convert CSV header to snake_case for DB columns."""
    s = header.strip()
    s = re.sub(r"[\s\-]+", "_", s)
    s = re.sub(r"[^a-zA-Z0-9_]", "", s)
    return s.lower() if s else header.lower().replace(" ", "_")


def load_csv_rows(path: Path) -> list[dict]:
    """Read CSV; return list of dicts with snake_case keys. Empty string -> None for DB."""
    rows = []
    with open(path, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            clean = {}
            for k, v in row.items():
                col = header_to_snake_case(k)
                clean[col] = (v.strip() if isinstance(v, str) and v.strip() else None)
            rows.append(clean)
    return rows


def truncate_table(table_name: str) -> None:
    """Remove all rows we loaded (where _source = SOURCE_TAG)."""
    try:
        supabase.table(table_name).delete().eq("_source", SOURCE_TAG).execute()
    except Exception as e:
        print(f"  Warning: truncate (delete by _source) failed: {e}", file=sys.stderr)


def insert_batches(table_name: str, rows: list[dict]) -> int:
    """Insert rows in batches. Each row gets _source added for insert."""
    for i in range(0, len(rows), BATCH_SIZE):
        batch = [{**r, "_source": SOURCE_TAG} for r in rows[i : i + BATCH_SIZE]]
        supabase.table(table_name).insert(batch).execute()
    return len(rows)


def main() -> None:
    if not LETTERBOXD_DIR.is_dir():
        print(f"Letterboxd data dir not found: {LETTERBOXD_DIR}", file=sys.stderr)
        sys.exit(1)

    # First-level CSV files only (no subdirs)
    csv_files = sorted(f for f in LETTERBOXD_DIR.iterdir() if f.is_file() and f.suffix.lower() == ".csv")
    if not csv_files:
        print(f"No CSV files in {LETTERBOXD_DIR}", file=sys.stderr)
        sys.exit(1)

    for path in csv_files:
        table_name = csv_name_to_table_stem(path.name)
        print(f"Loading {path.name} -> {table_name} ...")
        rows = load_csv_rows(path)
        if not rows:
            print(f"  No data rows, skipping.")
            continue
        truncate_table(table_name)
        n = insert_batches(table_name, rows)
        print(f"  Truncated and inserted {n} rows.")

    print("Done.")


if __name__ == "__main__":
    main()
