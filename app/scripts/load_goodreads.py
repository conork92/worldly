#!/usr/bin/env python3
"""
Load latest books from a Goodreads library export (CSV) into Supabase.

Goodreads doesn't offer an API anymore. To get your latest reading challenge data:
1. On Goodreads: My Books → Import and export → Export library (download CSV).
2. Save the CSV to app/data/ (e.g. goodreads_library_YYYYMMDD_HHMMSS.csv) or pass its path.
3. Run: make pull-books   (or: python scripts/load_goodreads.py [path/to/export.csv])

New rows are inserted into worldly_good_reads_books. Existing books (matched by title+author) are skipped.
Set country/iso_code_3 later in the app if needed.
"""

import argparse
import os
import sys
from pathlib import Path

import pandas as pd
import numpy as np
from dotenv import load_dotenv
from supabase import create_client, Client

# Load project root .env (single source of truth)
app_dir = Path(__file__).resolve().parent.parent
root_dir = app_dir.parent
dotenv_path = root_dir / ".env"
if dotenv_path.exists():
    load_dotenv(dotenv_path)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY")
if not SUPABASE_URL or not SUPABASE_KEY:
    print("Missing SUPABASE_URL or SUPABASE_ANON_KEY. Set them in .env (project root)", file=sys.stderr)
    sys.exit(1)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
TABLE = "worldly_good_reads_books"


def clean_goodreads_df(df: pd.DataFrame) -> pd.DataFrame:
    """Clean Goodreads export CSV to match our schema."""
    if "date_read" in df.columns:
        df["date_read"] = df["date_read"].replace(["not set", "", np.nan], pd.NaT)
        df["date_read"] = pd.to_datetime(df["date_read"], errors="coerce", format="%b %d, %Y")
    if "date_added" in df.columns:
        df["date_added"] = df["date_added"].replace(["", np.nan], pd.NaT)
        df["date_added"] = pd.to_datetime(df["date_added"], errors="coerce", format="%b %d, %Y")
    if "rating" in df.columns:
        df["rating"] = pd.to_numeric(df["rating"], errors="coerce")
    for col in ["isbn", "format"]:
        if col in df.columns:
            df[col] = df[col].replace("", None).astype(str).replace("nan", None)
    if "pages" in df.columns:
        df["pages"] = df["pages"].replace(["unknown", ""], None)
        df["pages"] = pd.to_numeric(df["pages"], errors="coerce")
    if "title" in df.columns:
        df = df[df["title"].notna()]
    for col in ["title", "author", "isbn", "format"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip().replace("nan", None).replace("None", None)
    return df


def row_to_record(row: pd.Series) -> dict:
    """Convert a cleaned DataFrame row to a record for Supabase."""
    record = {
        "title": None if pd.isna(row.get("title")) else str(row["title"]).strip(),
        "author": None if pd.isna(row.get("author")) else str(row["author"]).strip(),
        "rating": float(row["rating"]) if pd.notna(row.get("rating")) else None,
        "date_read": row["date_read"].isoformat() if pd.notna(row.get("date_read")) and hasattr(row["date_read"], "isoformat") else None,
        "date_added": row["date_added"].isoformat() if pd.notna(row.get("date_added")) and hasattr(row["date_added"], "isoformat") else None,
        "isbn": None if pd.isna(row.get("isbn")) or str(row.get("isbn")) in ("nan", "None", "") else str(row["isbn"]).strip(),
        "pages": int(row["pages"]) if pd.notna(row.get("pages")) and str(row.get("pages")) not in ("nan", "<NA>", "") else None,
        "format": None if pd.isna(row.get("format")) or str(row.get("format")) in ("nan", "None", "") else str(row["format"]).strip(),
    }
    return {k: v for k, v in record.items() if v is not None or k in ("rating", "pages")}


def find_latest_export(data_dir: Path) -> Path | None:
    """Return path to most recent goodreads_library_*.csv in data_dir."""
    files = list(data_dir.glob("goodreads_library_*.csv"))
    if not files:
        return None
    return max(files, key=lambda p: p.stat().st_mtime)


def main():
    parser = argparse.ArgumentParser(description="Load Goodreads library export into Supabase")
    parser.add_argument("csv_path", nargs="?", help="Path to Goodreads CSV export (default: latest in app/data/)")
    parser.add_argument("--dry-run", action="store_true", help="Only clean and print counts, do not insert")
    args = parser.parse_args()

    if args.csv_path:
        csv_path = Path(args.csv_path)
        if not csv_path.is_absolute():
            csv_path = app_dir / csv_path
    else:
        data_dir = app_dir / "data"
        csv_path = find_latest_export(data_dir)
        if not csv_path:
            print("No goodreads_library_*.csv found in app/data/. Export from Goodreads and save there, or pass csv_path.", file=sys.stderr)
            sys.exit(2)

    if not csv_path.exists():
        print(f"File not found: {csv_path}", file=sys.stderr)
        sys.exit(2)

    print(f"Reading {csv_path}")
    df = pd.read_csv(csv_path)
    df = clean_goodreads_df(df)
    print(f"Cleaned {len(df)} rows")

    # Existing books keyed by (title, author)
    try:
        res = supabase.table(TABLE).select("title, author").execute()
        existing = {((r["title"] or "").strip(), (r["author"] or "").strip()) for r in (res.data or [])}
    except Exception as e:
        print(f"Failed to fetch existing books: {e}", file=sys.stderr)
        sys.exit(3)

    to_insert = []
    for _, row in df.iterrows():
        title = (row.get("title") or "").strip()
        author = (row.get("author") or "").strip()
        if (title, author) in existing:
            continue
        existing.add((title, author))
        to_insert.append(row_to_record(row))

    print(f"New books to insert: {len(to_insert)}")
    if args.dry_run:
        if to_insert:
            print("Sample:", to_insert[0])
        return

    batch_size = 100
    inserted = 0
    for i in range(0, len(to_insert), batch_size):
        batch = to_insert[i : i + batch_size]
        try:
            supabase.table(TABLE).insert(batch).execute()
            inserted += len(batch)
        except Exception as e:
            print(f"Insert error at batch {i // batch_size}: {e}", file=sys.stderr)
    print(f"Inserted {inserted} books.")


if __name__ == "__main__":
    main()
