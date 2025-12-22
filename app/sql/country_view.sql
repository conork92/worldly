-- country_view.sql: A view and helper function for querying items (books, albums, etc) associated with countries.
-- 
-- This SQL file defines a helper function `country_items_view` which returns a unified table of "items" (such as books or albums) along with their associated country information.
--
-- The returned table provides, for each item:
--   - type: 'album' or 'book'
--   - country_name: country name as string
--   - iso_alpha_2: ISO two-letter country code
--   - iso_alpha_3: ISO three-letter country code
--   - artist: artist (for albums) or author (for books)
--   - title: album or book title
--   - rating: user rating (if present)
--   - pages: book pages (NULL for albums)
--   - comments: textual comments or notes
--   - year: publication/release year
--   - finished_date: the date finished/listened/read (if present)
--   - is_finished: boolean if finished/listened/read

-- If you pass finished_only=true, only finished/listened/read items will be shown.

-- EXAMPLE USAGE:
-- 1. Select all country items (both finished and unfinished):
--     SELECT * FROM country_items_view();

-- 2. Select only finished items from the view:
--     SELECT * FROM country_items_view(TRUE);

CREATE OR REPLACE FUNCTION country_items_view(finished_only BOOLEAN DEFAULT FALSE)
RETURNS TABLE(
  type text,
  country_name text,
  iso_alpha_2 text,
  iso_alpha_3 text,
  artist text,
  title text,
  rating double precision,
  pages integer,
  comments text,
  year integer,
  finished_date date,
  is_finished boolean
) AS $$
  SELECT * FROM (
    SELECT 
      'album' AS type,
      country_name,
      iso_alpha_2,
      iso_alpha_3,
      artist,
      album AS title,
      rating,
      NULL::integer AS pages,
      comments,
      year,
      CASE 
          WHEN listen_date IS NOT NULL AND listen_date != '' THEN
            COALESCE(
              -- Try DD/MM/YYYY format first
              TO_DATE(listen_date, 'DD/MM/YYYY'),
              -- Fall back to ISO format
              listen_date::date
            )
          ELSE NULL
        END AS finished_date,
      CASE 
          WHEN listen_date IS NOT NULL AND listen_date != '' THEN TRUE
          ELSE FALSE
        END AS is_finished
    FROM "public"."worldly_countrys_listened"

    UNION ALL

    SELECT 
      'book' AS type,
      country AS country_name,
      NULL::text AS iso_alpha_2,
      iso_code_3 AS iso_alpha_3,
      author AS artist,
      title AS title,
      rating,
      pages,
      NULL::text AS comments,
      NULL::integer AS year,
      date_read::date AS finished_date,
      CASE 
          WHEN date_read IS NOT NULL THEN TRUE
          ELSE FALSE
        END AS is_finished
    FROM "public"."worldly_good_reads_books"
  ) t_final
  WHERE (finished_only IS FALSE OR is_finished IS TRUE)
$$ LANGUAGE SQL
STABLE;
