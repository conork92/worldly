#!/usr/bin/env python3
"""
Enhance Letterboxd watched + watchlist with TMDB data (runtime, genre, director, etc.).

Requires: TMDB_API_KEY and Supabase env in project root .env.
Run: python scripts/enrich_letterboxd_tmdb.py   (from app dir)
     or: make enrich-letterboxd-tmdb

Uses letterboxd_tmdb_enrichment table; create it first with app/sql/letterboxd_tmdb_enrichment.sql.
"""

import os
import sys
import time
from pathlib import Path
from typing import Optional

import requests
from dotenv import load_dotenv
from supabase import create_client

# Load .env from project root and app/ (so TMDB keys in either place work)
app_dir = Path(__file__).resolve().parent.parent
root_dir = app_dir.parent
load_dotenv(root_dir / ".env")
load_dotenv(app_dir / ".env")

TMDB_API_KEY = os.getenv("TMDB_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY")
if not TMDB_API_KEY:
    print("Set TMDB_API_KEY in .env", file=sys.stderr)
    sys.exit(1)
if not SUPABASE_URL or not SUPABASE_KEY:
    print("Set SUPABASE_URL and SUPABASE_ANON_KEY in .env", file=sys.stderr)
    sys.exit(1)

BASE = "https://api.themoviedb.org/3"
IMAGE_BASE = "https://image.tmdb.org/t/p"
HEADERS = {"Accept": "application/json"}
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


def search_movie(name: str, year: Optional[str]) -> Optional[int]:
    """Return TMDB movie id or None."""
    params = {"api_key": TMDB_API_KEY, "query": name, "language": "en-US"}
    if year:
        params["year"] = str(year).strip()
    r = requests.get(f"{BASE}/search/movie", params=params, headers=HEADERS, timeout=10)
    if r.status_code != 200:
        return None
    data = r.json()
    results = data.get("results") or []
    if not results:
        return None
    return results[0].get("id")


def movie_details(tmdb_id: int) -> Optional[dict]:
    """Get movie details + credits (director). Returns dict with runtime_minutes, genres, director, etc."""
    params = {"api_key": TMDB_API_KEY, "language": "en-US", "append_to_response": "credits"}
    r = requests.get(f"{BASE}/movie/{tmdb_id}", params=params, headers=HEADERS, timeout=10)
    if r.status_code != 200:
        return None
    data = r.json()
    # Director from credits.crew
    director = None
    for p in (data.get("credits") or {}).get("crew") or []:
        if (p.get("job") or "").strip().lower() == "director":
            director = (p.get("name") or "").strip()
            break
    genres = [g.get("name") for g in (data.get("genres") or []) if g.get("name")]
    countries = [c.get("name") for c in (data.get("production_countries") or []) if c.get("name")]
    lang = (data.get("spoken_languages") or [])
    spoken = ", ".join(l.get("english_name") or l.get("name") or "" for l in lang[:3]) if lang else None
    raw_poster = (data.get("poster_path") or "").strip()
    raw_backdrop = (data.get("backdrop_path") or "").strip()
    poster_path = (IMAGE_BASE + "/w500" + raw_poster) if raw_poster else None
    backdrop_path = (IMAGE_BASE + "/w780" + raw_backdrop) if raw_backdrop else None
    return {
        "tmdb_id": tmdb_id,
        "runtime_minutes": data.get("runtime") or None,
        "genres": genres or None,
        "director": director or None,
        "overview": (data.get("overview") or "").strip() or None,
        "poster_path": poster_path,
        "backdrop_path": backdrop_path,
        "release_date": (data.get("release_date") or "").strip() or None,
        "tagline": (data.get("tagline") or "").strip() or None,
        "vote_average": data.get("vote_average"),
        "vote_count": data.get("vote_count"),
        "production_countries": countries or None,
        "spoken_languages": spoken,
    }


def main():
    # Distinct (name, year) from watched + watchlist
    seen = set()
    all_rows = []
    for table in ("letterboxd_watched", "letterboxd_watchlist"):
        r = supabase.table(table).select("name, year").execute()
        for x in (r.data or []):
            name = (x.get("name") or "").strip()
            year = (x.get("year") or "").strip()
            if not name:
                continue
            key = (name, year)
            if key in seen:
                continue
            seen.add(key)
            all_rows.append({"name": name, "year": year})

    # Skip films already in enrichment so we can resume after a stop
    existing_keys = set()
    try:
        er = supabase.table("letterboxd_tmdb_enrichment").select("name, year").execute()
        for x in (er.data or []):
            existing_keys.add(((x.get("name") or "").strip(), (x.get("year") or "").strip()))
    except Exception as e:
        print(f"Could not load existing enrichment (will process all): {e}", file=sys.stderr)

    rows = [r for r in all_rows if (r["name"], r["year"]) not in existing_keys]
    skipped = len(all_rows) - len(rows)
    if skipped:
        print(f"Skipping {skipped} already-enriched films (resuming from last run).")
    print(f"Found {len(rows)} films left to enrich (of {len(all_rows)} total).")
    updated = 0
    for i, row in enumerate(rows):
        name, year = row["name"], row["year"]
        tmdb_id = search_movie(name, year)
        time.sleep(0.3)  # rate limit
        if not tmdb_id:
            print(f"  [{i+1}/{len(rows)}] No TMDB match: {name} ({year})")
            continue
        details = movie_details(tmdb_id)
        time.sleep(0.3)
        if not details:
            print(f"  [{i+1}/{len(rows)}] No details for TMDB id {tmdb_id}: {name}")
            continue
        payload = {
            "name": name,
            "year": year,
            "tmdb_id": details["tmdb_id"],
            "runtime_minutes": details["runtime_minutes"],
            "genres": details["genres"],
            "director": details["director"],
            "overview": details["overview"],
            "poster_path": details["poster_path"],
            "backdrop_path": details["backdrop_path"],
            "release_date": details["release_date"],
            "tagline": details["tagline"],
            "vote_average": details["vote_average"],
            "vote_count": details["vote_count"],
            "production_countries": details["production_countries"],
            "spoken_languages": details["spoken_languages"],
        }
        try:
            supabase.table("letterboxd_tmdb_enrichment").upsert(
                payload,
                on_conflict="name,year",
                ignore_duplicates=False,
            ).execute()
            updated += 1
            print(f"  [{i+1}/{len(rows)}] OK: {name} ({year}) — {details.get('runtime_minutes')}m, {details.get('director') or '?'}")
        except Exception as e:
            print(f"  [{i+1}/{len(rows)}] Error {name}: {e}", file=sys.stderr)
    print(f"Done. Enriched {updated} films.")


if __name__ == "__main__":
    main()
