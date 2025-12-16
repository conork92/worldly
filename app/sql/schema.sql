-- Create the worldly schema


-- COUNTRIES table
CREATE TABLE public.worldly_countries (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    iso_code_2 CHAR(2) NOT NULL UNIQUE,
    iso_code_3 CHAR(3) NOT NULL UNIQUE,
    continent VARCHAR(100),
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);


-- USERS table
CREATE TABLE public.worldly_users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP WITH TIME ZONE
);


-- ARTISTS table
CREATE TABLE public.worldly_artists (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,                    -- artist (CSV: artist)
    bea_artist_link VARCHAR(255),                  -- from CSV: e.g., /thechart.php?a=123251
    country VARCHAR(100),                          -- country name from CSV: mirrors CSV, denormalized for import
    country_id INTEGER ,
    iso_code_2 CHAR(2) NOT NULL,
    iso_code_3 VARCHAR(3) NOT NULL,
    genre VARCHAR(100),
    formation_year INTEGER,
    biography TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ALBUMS table
-- Worldly Albums Table - optimized for source CSV import and future data use

CREATE TABLE public.worldly_albums (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    bea_album_rank VARCHAR(24),                -- from CSV: e.g., "112,508th"
    bea_album_link VARCHAR(255),               -- from CSV: e.g., "/thechart.php?a=52269"
    artist_id INTEGER,                -- foreign key to artists.id
    artist_name VARCHAR(255) NOT NULL,         -- for direct access (mirrors artist in CSV and helps with import)
    country VARCHAR(100),                      -- country name from CSV (redundant but useful for denorm/source-trace)
    iso_code_2 CHAR(2),                             -- ISO2 from CSV
    iso_code_3 CHAR(3),                             -- ISO3 from CSV
    bea_country_link VARCHAR(100),            -- from CSV: e.g., "/bandstats.php?l=af"
    release_year INTEGER,
    genre VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);



-- AUTHORS table
CREATE TABLE public.worldly_authors (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    country_id INTEGER NOT NULL,
    iso_code_3 VARCHAR(3) NOT NULL,
    birth_year INTEGER,
    death_year INTEGER,
    biography TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (country_id) REFERENCES public.worldly_countries(id) ON DELETE RESTRICT,
    CONSTRAINT chk_birth_year CHECK (birth_year >= 1000 AND birth_year <= 2100),
    CONSTRAINT chk_death_year CHECK (death_year >= 1000 AND death_year <= 2100),
    CONSTRAINT chk_birth_before_death CHECK (death_year IS NULL OR death_year >= birth_year)
);

-- BOOKS table
CREATE TABLE public.worldly_books (
    id SERIAL PRIMARY KEY,
    title VARCHAR(500) NOT NULL,
    author_id INTEGER NOT NULL,
    publication_year INTEGER,
    genre VARCHAR(100),
    isbn VARCHAR(13),
    avg_rating DECIMAL(2, 1) DEFAULT 0.0,
    rating_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (author_id) REFERENCES public.worldly_authors(id) ON DELETE CASCADE,
    CONSTRAINT chk_book_rating CHECK (avg_rating >= 0 AND avg_rating <= 10),
    CONSTRAINT chk_book_rating_count CHECK (rating_count >= 0),
    CONSTRAINT chk_publication_year CHECK (publication_year >= 1000 AND publication_year <= 2100)
);


-- DIRECTORS table
CREATE TABLE public.worldly_directors (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    country_id INTEGER NOT NULL,
    iso_code_3 VARCHAR(3) NOT NULL,
    birth_year INTEGER,
    death_year INTEGER,
    biography TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (country_id) REFERENCES public.worldly_countries(id) ON DELETE RESTRICT,
    CONSTRAINT chk_director_birth_year CHECK (birth_year >= 1000 AND birth_year <= 2100),
    CONSTRAINT chk_director_death_year CHECK (death_year >= 1000 AND death_year <= 2100),
    CONSTRAINT chk_director_birth_before_death CHECK (death_year IS NULL OR death_year >= birth_year)
);

-- FILMS table
CREATE TABLE public.worldly_films (
    id SERIAL PRIMARY KEY,
    title VARCHAR(500) NOT NULL,
    director_id INTEGER NOT NULL,
    country_id INTEGER NOT NULL,
    iso_code_3 VARCHAR(3) NOT NULL,
    release_year INTEGER,
    genre VARCHAR(100),
    runtime_minutes INTEGER,
    avg_rating DECIMAL(2, 1) DEFAULT 0.0,
    rating_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (director_id) REFERENCES public.worldly_directors(id) ON DELETE CASCADE,
    FOREIGN KEY (country_id) REFERENCES public.worldly_countries(id) ON DELETE RESTRICT,
    CONSTRAINT chk_film_rating CHECK (avg_rating >= 0 AND avg_rating <= 10),
    CONSTRAINT chk_film_rating_count CHECK (rating_count >= 0),
    CONSTRAINT chk_film_release_year CHECK (release_year >= 1000 AND release_year <= 2100),
    CONSTRAINT chk_runtime CHECK (runtime_minutes > 0)
);

-- ALBUM_RATINGS table
CREATE TABLE public.worldly_album_ratings (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    album_id INTEGER NOT NULL,
    rating DECIMAL(2, 1) NOT NULL,
    review TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES public.worldly_users(id) ON DELETE CASCADE,
    FOREIGN KEY (album_id) REFERENCES public.worldly_albums(id) ON DELETE CASCADE,
    CONSTRAINT chk_album_user_rating CHECK (rating >= 0 AND rating <= 10),
    CONSTRAINT unique_user_album UNIQUE (user_id, album_id)
);

-- BOOK_RATINGS table
CREATE TABLE public.worldly_book_ratings (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    book_id INTEGER NOT NULL,
    rating DECIMAL(2, 1) NOT NULL,
    review TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES public.worldly_users(id) ON DELETE CASCADE,
    FOREIGN KEY (book_id) REFERENCES public.worldly_books(id) ON DELETE CASCADE,
    CONSTRAINT chk_book_user_rating CHECK (rating >= 0 AND rating <= 10),
    CONSTRAINT unique_user_book UNIQUE (user_id, book_id)
);


-- Table to store best ever albums by country, as per best_ever_albums_country.csv
-- Make schema more flexible: allow more nullable fields, allow for additional/unknown columns, and relax some NOT NULL constraints.
-- Use JSONB for flexible or unmapped columns if import source changes.
CREATE TABLE public.worldly_best_ever_albums_country (
    id SERIAL PRIMARY KEY,
    country VARCHAR(150),
    artist VARCHAR(350),
    album_name_and_rank VARCHAR(500),
    country_link TEXT,
    artist_link TEXT,
    album_link TEXT,
    iso_code_2 VARCHAR(10),
    iso_code_3 VARCHAR(10),
    pop_est BIGINT,
    continent VARCHAR(100),
    gdp_md_est BIGINT,
    combined TEXT,
    extra_data JSONB, -- stores any additional columns or non-standard data for future imports
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);






-- FILM_RATINGS table
CREATE TABLE public.worldly_film_ratings (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    film_id INTEGER NOT NULL,
    rating DECIMAL(2, 1) NOT NULL,
    review TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES public.worldly_users(id) ON DELETE CASCADE,
    FOREIGN KEY (film_id) REFERENCES public.worldly_films(id) ON DELETE CASCADE,
    CONSTRAINT chk_film_user_rating CHECK (rating >= 0 AND rating <= 10),
    CONSTRAINT unique_user_film UNIQUE (user_id, film_id)
);

-- Table: worldly_quotes
CREATE TABLE public.worldly_quotes (
    id SERIAL PRIMARY KEY,
    quote_text TEXT NOT NULL,
    author VARCHAR(255),
    source VARCHAR(255),
    language VARCHAR(50),
    country VARCHAR(100),
    iso_code_2 VARCHAR(10),
    iso_code_3 VARCHAR(10),
    context TEXT,
    year INTEGER,
    category VARCHAR(100),
    theme VARCHAR(100),
    extra_data JSONB, -- Allows for additional/unmapped fields from the JSON file
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);



-- Create function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create triggers for updated_at on all relevant tables
CREATE TRIGGER update_countries_updated_at
    BEFORE UPDATE ON public.worldly_countries
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_artists_updated_at
    BEFORE UPDATE ON public.worldly_artists
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_albums_updated_at
    BEFORE UPDATE ON public.worldly_albums
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_authors_updated_at
    BEFORE UPDATE ON public.worldly_authors
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_books_updated_at
    BEFORE UPDATE ON public.worldly_books
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_directors_updated_at
    BEFORE UPDATE ON public.worldly_directors
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_films_updated_at
    BEFORE UPDATE ON public.worldly_films
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_album_ratings_updated_at
    BEFORE UPDATE ON public.worldly_album_ratings
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_book_ratings_updated_at
    BEFORE UPDATE ON public.worldly_book_ratings
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_film_ratings_updated_at
    BEFORE UPDATE ON public.worldly_film_ratings
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Add comments to tables for documentation
COMMENT ON SCHEMA public.worldly IS 'Schema for the Worldly countries and art application';
COMMENT ON TABLE public.worldly_countries IS 'Central table containing all countries in the world';
COMMENT ON TABLE public.worldly_users IS 'Application users who can rate and review content';
COMMENT ON TABLE public.worldly_artists IS 'Musical artists from various countries';
COMMENT ON TABLE public.worldly_albums IS 'Albums created by artists';
COMMENT ON TABLE public.worldly_authors IS 'Book authors from various countries';
COMMENT ON TABLE public.worldly_books IS 'Books written by authors';
COMMENT ON TABLE public.worldly_directors IS 'Film directors from various countries';
COMMENT ON TABLE public.worldly_films IS 'Films directed by directors';
COMMENT ON TABLE public.worldly_album_ratings IS 'User ratings and reviews for albums';
COMMENT ON TABLE public.worldly_book_ratings IS 'User ratings and reviews for books';
COMMENT ON TABLE public.worldly_film_ratings IS 'User ratings and reviews for films';