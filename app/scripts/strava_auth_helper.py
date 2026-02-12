#!/usr/bin/env python3
"""
Generate Strava OAuth URL and exchange code for tokens using .env.

Usage (from app dir or repo root):
  python app/scripts/strava_auth_helper.py              # print authorize URL
  python app/scripts/strava_auth_helper.py <code>       # exchange code, print refresh_token for .env
"""
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
import requests

app_dir = Path(__file__).resolve().parent.parent
root_dir = app_dir.parent
load_dotenv(root_dir / ".env")
load_dotenv(app_dir / ".env")

CLIENT_ID = os.getenv("STRAVA_CLIENT_ID")
CLIENT_SECRET = os.getenv("STRAVA_CLIENT_SECRET")
REDIRECT_URI = os.getenv("STRAVA_REDIRECT_URI", "http://localhost")
SCOPE = "activity:read_all"

if not CLIENT_ID:
    print("Set STRAVA_CLIENT_ID in .env", file=sys.stderr)
    sys.exit(1)

if len(sys.argv) < 2:
    url = (
        "https://www.strava.com/oauth/authorize"
        f"?client_id={CLIENT_ID}"
        "&response_type=code"
        f"&redirect_uri={REDIRECT_URI}"
        "&approval_prompt=force"
        f"&scope={SCOPE}"
    )
    print("Open this URL in your browser, then authorize and copy the 'code' from the redirect URL:\n")
    print(url)
    print("\nThen run:  make strava-exchange CODE=your_code_here")
    sys.exit(0)

code = sys.argv[1].strip()
if not CLIENT_SECRET:
    print("Set STRAVA_CLIENT_SECRET in .env to exchange the code", file=sys.stderr)
    sys.exit(1)

r = requests.post(
    "https://www.strava.com/oauth/token",
    data={
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "code": code,
        "grant_type": "authorization_code",
    },
    timeout=10,
)
if r.status_code != 200:
    print(f"Exchange failed: {r.status_code} {r.text}", file=sys.stderr)
    sys.exit(1)

data = r.json()
refresh = (data.get("refresh_token") or "").strip()
access = (data.get("access_token") or "").strip()
if not refresh:
    print("Response missing refresh_token", file=sys.stderr)
    sys.exit(1)

print("Add this to your .env (or replace existing STRAVA_REFRESH_TOKEN):\n")
print(f"STRAVA_REFRESH_TOKEN={refresh}")
print(f"\n(Refresh token length: {len(refresh)} chars. Copy the full line above into .env — no extra spaces or quotes. Do NOT use STRAVA_ACCESS_TOKEN; only the refresh_token goes in .env.)")
if access:
    print("(access_token expires in ~6 hours; only refresh_token is needed in .env)")
