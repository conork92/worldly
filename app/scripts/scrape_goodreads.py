#!/usr/bin/env python3
"""
Scrape your Goodreads "read" shelf and load books into Supabase (no CSV).

Setup:
1. Log in to Goodreads in your browser.
2. Open DevTools → Application (or Storage) → Cookies → goodreads.com.
3. Copy the full cookie string (e.g. run in console: copy(document.cookie)).
4. In project root .env set:
   GOODREADS_SESSION=<paste the cookie string>
   GOODREADS_LIST_URL=https://www.goodreads.com/review/list/YOUR_USER_ID-YOUR_USERNAME?shelf=read&per_page=100

   To find your list URL: open your profile → "My Books" → "Read" shelf, copy the URL (without &page=).

Run: make pull-books   or   python scripts/scrape_goodreads.py
"""

import argparse
import os
import re
import sys
from datetime import datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup
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
GOODREADS_SESSION = os.getenv("GOODREADS_SESSION")
GOODREADS_LIST_URL = os.getenv("GOODREADS_LIST_URL")

TABLE = "worldly_good_reads_books"

# Goodreads table uses .bookalike rows; title/value pattern for fields
def _text(el, selector):
    if el is None:
        return ""
    found = el.select_one(selector)
    if found is None:
        return ""
    return " ".join(found.get_text().split()).strip()


def _parse_date_read(soup_row):
    """Get most recent 'date read' from the row (Goodreads allows multiple for re-reads)."""
    container = soup_row.select_one(".date_read")
    if not container:
        return None
    spans = container.select("span")
    dates = []
    for span in spans:
        raw = span.get_text().strip()
        if not raw or raw == "?":
            continue
        # Goodreads format e.g. "Dec 09, 2025" or "18 Nov, 2023"
        for fmt in ("%b %d, %Y", "%d %b, %Y"):
            try:
                d = datetime.strptime(raw, fmt)
                dates.append(d)
                break
            except ValueError:
                continue
    return max(dates).date().isoformat() if dates else None


def scrape_page(session: requests.Session, url: str):
    """Fetch one list page and return list of book dicts (title, author, rating, date_read, pages)."""
    r = session.get(url, timeout=30)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    rows = soup.select("tr.bookalike")
    books = []
    for tr in rows:
        title_el = tr.select_one(".title .value")
        if not title_el:
            continue
        # Title may include series in parentheses; we keep full title
        title = _text(tr, ".title .value").strip()
        if not title:
            continue
        author = _text(tr, ".author .value").strip().rstrip(" *")
        rating_el = tr.select_one(".rating .stars")
        rating = None
        if rating_el and rating_el.get("data-rating"):
            try:
                rating = float(rating_el["data-rating"])
            except (TypeError, ValueError):
                pass
        pages_raw = _text(tr, ".num_pages")
        pages = None
        if pages_raw and pages_raw != "—":
            try:
                pages = int(re.sub(r"[^\d]", "", pages_raw) or 0) or None
            except ValueError:
                pass
        date_read = _parse_date_read(tr)
        books.append({
            "title": title,
            "author": author,
            "rating": rating,
            "date_read": date_read,
            "pages": pages,
        })
    return books


def fetch_all_pages(session: requests.Session, base_url: str, max_pages: int = 50):
    """Paginate through shelf=read and collect all books."""
    all_books = []
    seen = set()
    sep = "&" if "?" in base_url else "?"
    page = 1
    while page <= max_pages:
        url = f"{base_url}{sep}page={page}&per_page=100"
        books = scrape_page(session, url)
        if not books:
            break
        for b in books:
            key = (b["title"].strip(), b["author"].strip())
            if key not in seen:
                seen.add(key)
                all_books.append(b)
        if len(books) < 100:
            break
        page += 1
    return all_books


def book_to_record(b: dict) -> dict:
    """Map scraped book to Supabase row (worldly_good_reads_books)."""
    record = {
        "title": (b.get("title") or "").strip(),
        "author": (b.get("author") or "").strip(),
        "rating": b.get("rating"),
        "date_read": b.get("date_read"),
        "pages": b.get("pages"),
    }
    return {k: v for k, v in record.items() if v is not None or k in ("rating", "pages")}


def main():
    parser = argparse.ArgumentParser(description="Scrape Goodreads read shelf and load into Supabase")
    parser.add_argument("--dry-run", action="store_true", help="Only scrape and print counts, do not insert")
    parser.add_argument("--max-pages", type=int, default=50, help="Max list pages to fetch (default 50)")
    args = parser.parse_args()

    if not GOODREADS_SESSION:
        print(
            "Set GOODREADS_SESSION in .env (paste document.cookie from Goodreads while logged in).",
            file=sys.stderr,
        )
        sys.exit(2)
    if not GOODREADS_LIST_URL:
        print(
            "Set GOODREADS_LIST_URL in .env to your read shelf URL, e.g.\n"
            "https://www.goodreads.com/review/list/USER_ID-username?shelf=read&per_page=100",
            file=sys.stderr,
        )
        sys.exit(2)

    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    })
    session.cookies.update(_parse_cookie_string(GOODREADS_SESSION))

    print("Scraping Goodreads read shelf...")
    books = fetch_all_pages(session, GOODREADS_LIST_URL, max_pages=args.max_pages)
    print(f"Scraped {len(books)} books.")

    if args.dry_run:
        if books:
            print("Sample:", books[0])
        return

    if not SUPABASE_URL or not SUPABASE_KEY:
        print("Set SUPABASE_URL and SUPABASE_ANON_KEY in .env to insert into Supabase.", file=sys.stderr)
        sys.exit(3)

    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    try:
        res = supabase.table(TABLE).select("title, author").execute()
        existing = {((r["title"] or "").strip(), (r["author"] or "").strip()) for r in (res.data or [])}
    except Exception as e:
        print(f"Failed to fetch existing books: {e}", file=sys.stderr)
        sys.exit(4)

    to_insert = []
    for b in books:
        title = (b.get("title") or "").strip()
        author = (b.get("author") or "").strip()
        if (title, author) in existing:
            continue
        existing.add((title, author))
        to_insert.append(book_to_record(b))

    print(f"New books to insert: {len(to_insert)}")
    inserted = 0
    batch_size = 100
    for i in range(0, len(to_insert), batch_size):
        batch = to_insert[i : i + batch_size]
        try:
            supabase.table(TABLE).insert(batch).execute()
            inserted += len(batch)
        except Exception as e:
            print(f"Insert error at batch {i // batch_size}: {e}", file=sys.stderr)
    print(f"Inserted {inserted} books.")


def _parse_cookie_string(s: str) -> dict:
    """Turn 'name1=value1; name2=value2' into dict."""
    out = {}
    for part in s.split(";"):
        part = part.strip()
        if "=" in part:
            k, v = part.split("=", 1)
            out[k.strip()] = v.strip()
    return out


if __name__ == "__main__":
    main()
