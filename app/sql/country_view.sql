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
  listen_date::date AS finished_date
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
  date_read::date AS finished_date
FROM "public"."worldly_good_reads_books"
WHERE date_read IS NOT NULL