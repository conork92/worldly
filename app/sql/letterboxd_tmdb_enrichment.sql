-- TMDB enrichment for Letterboxd movies (watched + watchlist).
-- Keyed by (name, year) so one row per film; join when serving /api/movies.
-- Run once in Supabase SQL Editor. Backfill via: python scripts/enrich_letterboxd_tmdb.py

CREATE TABLE IF NOT EXISTS public.letterboxd_tmdb_enrichment (
    id BIGSERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    year TEXT NOT NULL,
    tmdb_id INTEGER,
    runtime_minutes INTEGER,
    genres TEXT[],                    -- e.g. {'Comedy', 'Drama'}
    director TEXT,
    overview TEXT,
    poster_path TEXT,                 -- full poster URL (e.g. https://image.tmdb.org/t/p/w500/...)
    backdrop_path TEXT,               -- full backdrop URL (e.g. https://image.tmdb.org/t/p/w780/...)
    release_date TEXT,                -- YYYY-MM-DD
    tagline TEXT,
    vote_average NUMERIC(3,1),
    vote_count INTEGER,
    production_countries TEXT[],      -- country names or ISO codes
    spoken_languages TEXT,            -- comma-separated or first language
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(name, year)
);

CREATE INDEX IF NOT EXISTS idx_letterboxd_tmdb_enrichment_name_year
    ON public.letterboxd_tmdb_enrichment (name, year);

COMMENT ON TABLE public.letterboxd_tmdb_enrichment IS 'TMDB data for Letterboxd films (runtime, genre, director, etc.). Backfilled by enrich_letterboxd_tmdb.py.';
