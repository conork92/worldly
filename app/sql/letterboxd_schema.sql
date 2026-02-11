-- Letterboxd export tables (first-level CSVs only).
-- Run once in Supabase SQL Editor. load_letterboxd.py truncates via _source then full-loads.

-- comments.csv: Date, Content, Comment
CREATE TABLE IF NOT EXISTS public.letterboxd_comments (
    id BIGSERIAL PRIMARY KEY,
    date TEXT,
    content TEXT,
    comment TEXT,
    _source TEXT NOT NULL DEFAULT 'letterboxd'
);

-- diary.csv: Date, Name, Year, Letterboxd URI, Rating, Rewatch, Tags, Watched Date
CREATE TABLE IF NOT EXISTS public.letterboxd_diary (
    id BIGSERIAL PRIMARY KEY,
    date TEXT,
    name TEXT,
    year TEXT,
    letterboxd_uri TEXT,
    rating TEXT,
    rewatch TEXT,
    tags TEXT,
    watched_date TEXT,
    _source TEXT NOT NULL DEFAULT 'letterboxd'
);

-- profile.csv: Date Joined, Username, Given Name, Family Name, Email Address, Location, Website, Bio, Pronoun, Favorite Films
CREATE TABLE IF NOT EXISTS public.letterboxd_profile (
    id BIGSERIAL PRIMARY KEY,
    date_joined TEXT,
    username TEXT,
    given_name TEXT,
    family_name TEXT,
    email_address TEXT,
    location TEXT,
    website TEXT,
    bio TEXT,
    pronoun TEXT,
    favorite_films TEXT,
    _source TEXT NOT NULL DEFAULT 'letterboxd'
);

-- ratings.csv: Date, Name, Year, Letterboxd URI, Rating
CREATE TABLE IF NOT EXISTS public.letterboxd_ratings (
    id BIGSERIAL PRIMARY KEY,
    date TEXT,
    name TEXT,
    year TEXT,
    letterboxd_uri TEXT,
    rating TEXT,
    _source TEXT NOT NULL DEFAULT 'letterboxd'
);

-- reviews.csv: Date, Name, Year, Letterboxd URI, Rating, Rewatch, Review, Tags, Watched Date
CREATE TABLE IF NOT EXISTS public.letterboxd_reviews (
    id BIGSERIAL PRIMARY KEY,
    date TEXT,
    name TEXT,
    year TEXT,
    letterboxd_uri TEXT,
    rating TEXT,
    rewatch TEXT,
    review TEXT,
    tags TEXT,
    watched_date TEXT,
    _source TEXT NOT NULL DEFAULT 'letterboxd'
);

-- watched.csv: Date, Name, Year, Letterboxd URI
CREATE TABLE IF NOT EXISTS public.letterboxd_watched (
    id BIGSERIAL PRIMARY KEY,
    date TEXT,
    name TEXT,
    year TEXT,
    letterboxd_uri TEXT,
    _source TEXT NOT NULL DEFAULT 'letterboxd'
);

-- watchlist.csv: Date, Name, Year, Letterboxd URI
CREATE TABLE IF NOT EXISTS public.letterboxd_watchlist (
    id BIGSERIAL PRIMARY KEY,
    date TEXT,
    name TEXT,
    year TEXT,
    letterboxd_uri TEXT,
    _source TEXT NOT NULL DEFAULT 'letterboxd'
);
