-- Strava activities synced from Strava API (scripts/pull_strava.py).
-- Run once in Supabase SQL Editor. Pull data via: make pull-strava or POST /api/exercise/refresh

CREATE TABLE IF NOT EXISTS public.worldly_strava (
    id BIGSERIAL PRIMARY KEY,
    strava_id BIGINT NOT NULL UNIQUE,
    name TEXT,
    type TEXT,
    sport_type TEXT,
    start_date TIMESTAMPTZ,
    start_date_local TIMESTAMPTZ,
    timezone TEXT,
    utc_offset NUMERIC(6,1),
    distance NUMERIC(12,2),
    moving_time INTEGER,
    elapsed_time INTEGER,
    total_elevation_gain NUMERIC(10,2),
    elev_high NUMERIC(10,2),
    elev_low NUMERIC(10,2),
    average_speed NUMERIC(10,4),
    max_speed NUMERIC(10,4),
    average_cadence NUMERIC(8,2),
    average_watts NUMERIC(8,2),
    weighted_average_watts INTEGER,
    average_temp NUMERIC(5,2),
    kudos_count INTEGER,
    comment_count INTEGER,
    achievement_count INTEGER,
    pr_count INTEGER,
    athlete_count INTEGER,
    photo_count INTEGER,
    total_photo_count INTEGER,
    trainer BOOLEAN,
    commute BOOLEAN,
    manual BOOLEAN,
    private BOOLEAN,
    flagged BOOLEAN,
    gear_id TEXT,
    workout_type INTEGER,
    external_id TEXT,
    upload_id BIGINT,
    from_accepted_tag BOOLEAN,
    has_heartrate BOOLEAN,
    max_heartrate NUMERIC(6,2),
    has_kudoed BOOLEAN,
    suffer_score NUMERIC(8,2),
    calories NUMERIC(10,2),
    description TEXT,
    device_name TEXT,
    start_latlng TEXT,
    end_latlng TEXT,
    athlete_id BIGINT,
    raw_json JSONB,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_worldly_strava_start_date
    ON public.worldly_strava (start_date_local);
CREATE INDEX IF NOT EXISTS idx_worldly_strava_sport_type
    ON public.worldly_strava (sport_type);
CREATE INDEX IF NOT EXISTS idx_worldly_strava_type
    ON public.worldly_strava (type);

COMMENT ON TABLE public.worldly_strava IS 'Strava activities synced via pull_strava.py. Used by Exercise tab and Progress.';
