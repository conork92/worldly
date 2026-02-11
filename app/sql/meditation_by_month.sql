-- Count records per month from public.ck_meditation for "meditation bit in progress".
-- Uses [Started At] for the month; adjust the WHERE column if your bit name is in a different column (e.g. "Name", "Bit", "Task").
-- Run in Supabase SQL Editor. If your column names use spaces, they may be stored as "Started At" / "Name" (quoted).

WITH months AS (
  SELECT date_trunc('month', ("Started At")::timestamptz) AS month_start
  FROM public.ck_meditation
  WHERE "Started At" IS NOT NULL
)
SELECT
  month_start,
  to_char(month_start, 'YYYY-MM') AS year_month,
  count(*) AS record_count
FROM months
GROUP BY month_start
ORDER BY month_start;
