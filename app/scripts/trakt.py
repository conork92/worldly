import os
import sys
import requests
import logging
from datetime import datetime

# Set up basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration: replace with your values, or set as environment variables
TRAKT_CLIENT_ID = os.getenv("TRAKT_CLIENT_ID")
TRAKT_CLIENT_SECRET = os.getenv("TRAKT_CLIENT_SECRET")
TRAKT_ACCESS_TOKEN = os.getenv("TRAKT_ACCESS_TOKEN")
TRAKT_API_URL = "https://api.trakt.tv"

if not TRAKT_CLIENT_ID or not TRAKT_ACCESS_TOKEN:
    logger.error("Please set TRAKT_CLIENT_ID and TRAKT_ACCESS_TOKEN in your environment.")
    sys.exit(1)

HEADERS = {
    "Content-Type": "application/json",
    "trakt-api-version": "2",
    "trakt-api-key": TRAKT_CLIENT_ID,
    "Authorization": f"Bearer {TRAKT_ACCESS_TOKEN}",
}


def get_history(username="me", history_type="all", limit=50, page=1):
    """
    Pull the user's Trakt history (all watched movies/episodes).
    Args:
        username: trakt username, or "me" for current user
        history_type: 'movies', 'episodes', or 'all'
        limit: items per page (max 10000 for all, 100 for movies/episodes)
        page: which page to retrieve
    Returns: List of history records
    """
    if history_type not in ['all', 'movies', 'episodes']:
        raise ValueError("history_type must be 'all', 'movies', or 'episodes'")

    url = f"{TRAKT_API_URL}/users/{username}/history"
    if history_type != 'all':
        url += f"/{history_type}"

    params = {
        "limit": limit,
        "page": page
    }

    resp = requests.get(url, headers=HEADERS, params=params)
    if resp.status_code != 200:
        logger.error(f"Failed to fetch Trakt history: {resp.status_code} {resp.text}")
        return []

    return resp.json()


def dump_history_to_file(records, fname="trakt_history.json"):
    import json
    with open(fname, "w", encoding="utf8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)
    logger.info(f"Wrote {len(records)} history records to {fname}")


def get_all_history(username="me", history_type="all"):
    """
    Fetch ALL history from Trakt for a user/type, paginating as needed.
    """
    all_records = []
    page = 1
    while True:
        logger.info(f"Fetching page {page} of {history_type} history")
        records = get_history(username, history_type=history_type, limit=100, page=page)
        if not records:
            break
        all_records.extend(records)
        if len(records) < 100:
            break
        page += 1
    return all_records


if __name__ == "__main__":
    # Basic usage: fetch and save full Trakt history (movies+episodes) for yourself
    history_type = "all"  # change to "movies" or "episodes" if only want those
    username = "me"  # or your username string
    all_history = get_all_history(username=username, history_type=history_type)
    dump_history_to_file(all_history)
