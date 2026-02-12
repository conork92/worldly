#!/usr/bin/env python3
"""
Pull Strava activities into worldly_strava table.

Requires: STRAVA_CLIENT_ID, STRAVA_CLIENT_SECRET, STRAVA_REFRESH_TOKEN and Supabase in .env.
Run: python scripts/pull_strava.py   (from app dir)
     or: make pull-strava

Create the table first: app/sql/worldly_strava.sql
Get a refresh token: https://developers.strava.com/docs/authentication/
"""

import json
import os
import sys
import time
from pathlib import Path

import requests
from dotenv import load_dotenv
from supabase import create_client

app_dir = Path(__file__).resolve().parent.parent
root_dir = app_dir.parent
load_dotenv(root_dir / ".env")
load_dotenv(app_dir / ".env")

def _env(key: str, default: str = "") -> str:
    return (os.getenv(key) or default).strip().strip('"').strip("'")

STRAVA_CLIENT_ID = _env("STRAVA_CLIENT_ID")
STRAVA_CLIENT_SECRET = _env("STRAVA_CLIENT_SECRET")
STRAVA_REFRESH_TOKEN = _env("STRAVA_REFRESH_TOKEN")
SUPABASE_URL = _env("SUPABASE_URL")
SUPABASE_KEY = _env("SUPABASE_ANON_KEY")

if not all([STRAVA_CLIENT_ID, STRAVA_CLIENT_SECRET, STRAVA_REFRESH_TOKEN]):
    print("Set STRAVA_CLIENT_ID, STRAVA_CLIENT_SECRET, STRAVA_REFRESH_TOKEN in .env", file=sys.stderr)
    sys.exit(1)
if not SUPABASE_URL or not SUPABASE_KEY:
    print("Set SUPABASE_URL and SUPABASE_ANON_KEY in .env", file=sys.stderr)
    sys.exit(1)

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
TOKEN_URL = "https://www.strava.com/oauth/token"
API_BASE = "https://www.strava.com/api/v3"
PER_PAGE = 200


def get_access_token():
    """Exchange refresh token for access token. Strava may return a new refresh token."""
    r = requests.post(
        TOKEN_URL,
        data={
            "client_id": STRAVA_CLIENT_ID,
            "client_secret": STRAVA_CLIENT_SECRET,
            "refresh_token": STRAVA_REFRESH_TOKEN,
            "grant_type": "refresh_token",
        },
        timeout=10,
    )
    if r.status_code != 200:
        print(f"Token refresh failed: {r.status_code} {r.text}", file=sys.stderr)
        print("Get a new refresh token: re-run the OAuth flow (authorize URL, then exchange code for tokens).", file=sys.stderr)
        # Help debug: refresh tokens are usually 80+ chars; 40 chars often means access_token was used by mistake
        n = len(STRAVA_REFRESH_TOKEN or "")
        if n > 0 and n < 60:
            print(f"Note: STRAVA_REFRESH_TOKEN length is {n}. Strava refresh tokens are usually 80+ characters. If you have a 40-char value, you may have set the access_token by mistake.", file=sys.stderr)
        sys.exit(1)
    data = r.json()
    access_token = data.get("access_token")
    if not access_token:
        print("Token response missing access_token.", file=sys.stderr)
        sys.exit(1)
    # Verify token works (and catch wrong/expired refresh token that still returns 200)
    check = requests.get(f"{API_BASE}/athlete", headers={"Authorization": f"Bearer {access_token}"}, timeout=10)
    if check.status_code == 401:
        print("Unauthorized; refresh token may have expired or was revoked.", file=sys.stderr)
        print("Get a new refresh token:", file=sys.stderr)
        print("  1. Open: https://www.strava.com/oauth/authorize?client_id=YOUR_ID&response_type=code&redirect_uri=http://localhost&approval_prompt=force&scope=activity:read_all", file=sys.stderr)
        print("  2. Authorize, then copy the 'code' from the redirect URL.", file=sys.stderr)
        print("  3. Exchange: curl -X POST https://www.strava.com/oauth/token -d client_id=... -d client_secret=... -d code=... -d grant_type=authorization_code", file=sys.stderr)
        print("  4. Put the new refresh_token in .env as STRAVA_REFRESH_TOKEN.", file=sys.stderr)
        sys.exit(1)
    if check.status_code != 200:
        print(f"Unexpected response from Strava: {check.status_code}", file=sys.stderr)
        sys.exit(1)
    return access_token, data.get("refresh_token")


def latlng_to_str(arr):
    if not arr or not isinstance(arr, list) or len(arr) < 2:
        return None
    return f"{arr[0]},{arr[1]}"


def activity_to_row(a):
    """Map Strava activity dict to worldly_strava row (and raw_json)."""
    raw = dict(a)
    row = {
        "strava_id": a.get("id"),
        "name": a.get("name"),
        "type": a.get("type"),
        "sport_type": a.get("sport_type"),
        "start_date": a.get("start_date"),
        "start_date_local": a.get("start_date_local"),
        "timezone": a.get("timezone"),
        "utc_offset": a.get("utc_offset"),
        "distance": a.get("distance"),
        "moving_time": a.get("moving_time"),
        "elapsed_time": a.get("elapsed_time"),
        "total_elevation_gain": a.get("total_elevation_gain"),
        "elev_high": a.get("elev_high"),
        "elev_low": a.get("elev_low"),
        "average_speed": a.get("average_speed"),
        "max_speed": a.get("max_speed"),
        "average_cadence": a.get("average_cadence"),
        "average_watts": a.get("average_watts"),
        "weighted_average_watts": a.get("weighted_average_watts"),
        "average_temp": a.get("average_temp"),
        "kudos_count": a.get("kudos_count"),
        "comment_count": a.get("comment_count"),
        "achievement_count": a.get("achievement_count"),
        "pr_count": a.get("pr_count"),
        "athlete_count": a.get("athlete_count"),
        "photo_count": a.get("photo_count"),
        "total_photo_count": a.get("total_photo_count"),
        "trainer": a.get("trainer"),
        "commute": a.get("commute"),
        "manual": a.get("manual"),
        "private": a.get("private"),
        "flagged": a.get("flagged"),
        "gear_id": a.get("gear_id"),
        "workout_type": a.get("workout_type"),
        "external_id": a.get("external_id"),
        "upload_id": a.get("upload_id"),
        "from_accepted_tag": a.get("from_accepted_tag"),
        "has_heartrate": a.get("has_heartrate"),
        "max_heartrate": a.get("max_heartrate"),
        "has_kudoed": a.get("has_kudoed"),
        "suffer_score": a.get("suffer_score"),
        "calories": a.get("calories"),
        "description": a.get("description"),
        "device_name": a.get("device_name"),
        "start_latlng": latlng_to_str(a.get("start_latlng")),
        "end_latlng": latlng_to_str(a.get("end_latlng")),
        "athlete_id": (a.get("athlete") or {}).get("id") if isinstance(a.get("athlete"), dict) else None,
        "raw_json": raw,
    }
    return row


def main():
    access_token, new_refresh = get_access_token()
    headers = {"Authorization": f"Bearer {access_token}"}
    total = 0
    page = 1
    while True:
        r = requests.get(
            f"{API_BASE}/athlete/activities",
            params={"page": page, "per_page": PER_PAGE},
            headers=headers,
            timeout=15,
        )
        if r.status_code == 401:
            print("Unauthorized on activities; token may have insufficient scope.", file=sys.stderr)
            print("Re-authorize with scope activity:read_all (see message above for steps).", file=sys.stderr)
            sys.exit(1)
        if r.status_code != 200:
            print(f"Activities fetch failed: {r.status_code} {r.text}", file=sys.stderr)
            break
        activities = r.json()
        if not activities:
            break
        for a in activities:
            try:
                row = activity_to_row(a)
                supabase.table("worldly_strava").upsert(
                    row,
                    on_conflict="strava_id",
                    ignore_duplicates=False,
                ).execute()
                total += 1
                print(f"  [{total}] {row.get('name') or 'Unnamed'} — {row.get('sport_type') or row.get('type')} ({row.get('start_date_local', '')[:10]})")
            except Exception as e:
                print(f"  Skip {a.get('id')}: {e}", file=sys.stderr)
        page += 1
        time.sleep(0.5)
    print(f"Done. Synced {total} activities.")
    if new_refresh and new_refresh != STRAVA_REFRESH_TOKEN:
        print("Note: Strava issued a new refresh token. Update STRAVA_REFRESH_TOKEN in .env for next run.", file=sys.stderr)


if __name__ == "__main__":
    main()
