# Letterboxd + TMDB enrichment

Movies from **letterboxd_watched** and **letterboxd_watchlist** can be enhanced with data from [The Movie Database (TMDB)](https://www.themoviedb.org/) so the Movies page shows runtime, genre, director, and more.

## What we store from TMDB

| Field | Description |
|-------|-------------|
| **runtime_minutes** | Film length |
| **genres** | e.g. Comedy, Drama, Horror |
| **director** | Director name (from credits) |
| **overview** | Short synopsis |
| **poster_path** | Poster image (we build full URL) |
| **backdrop_path** | Backdrop image |
| **release_date** | Theatrical release (YYYY-MM-DD) |
| **tagline** | Tagline |
| **vote_average** | TMDB user rating |
| **vote_count** | Number of TMDB votes |
| **production_countries** | Countries of production |
| **spoken_languages** | Languages (e.g. English, Spanish) |

## Other TMDB fields you could add

- **Cast** (top N) – from `/movie/{id}/credits` → `cast`
- **Keywords** – from `/movie/{id}/keywords`
- **Videos** – trailer key for YouTube embed
- **Budget / revenue** – for “box office” style stats
- **Belongs to collection** – series name
- **IMDb id** – link to IMDb
- **Original title** – for non-English films

To add any of these, extend `letterboxd_tmdb_enrichment` and `enrich_letterboxd_tmdb.py` (and the API/template if you want them on the UI).

## Setup

1. **TMDB API key**  
   Get a key at [TMDB API](https://developer.themoviedb.org/docs). Add to `.env`:
   ```bash
   TMDB_API_KEY=your_key
   ```

2. **Create the enrichment table**  
   In Supabase SQL Editor, run:
   ```sql
   -- contents of app/sql/letterboxd_tmdb_enrichment.sql
   ```

3. **Backfill**  
   From the `app` directory:
   ```bash
   make enrich-letterboxd-tmdb
   ```
   Or: `python scripts/enrich_letterboxd_tmdb.py`  
   This finds each distinct (name, year) in watched + watchlist, looks it up on TMDB, and upserts into `letterboxd_tmdb_enrichment`. Rate-limited to avoid hitting TMDB limits.

4. **Movies page**  
   `/api/movies` joins enrichment and returns `runtime_minutes`, `genres`, `director`, etc. The Movies template shows runtime, genres, and director under the title when present.

## Re-enriching

Re-run `make enrich-letterboxd-tmdb` after adding new Letterboxd exports (or new films) to backfill any missing rows. Existing rows are upserted so you can refresh data by re-running.
