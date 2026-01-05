import requests
import time
import sys
import os
import logging
from dotenv import load_dotenv
from supabase import create_client, Client

# --- Setup Logging ---
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# --- Load environment variables ---
dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)

LASTFM_API_KEY = os.getenv('LASTFM_API_KEY')
LASTFM_USERNAME = os.getenv('LASTFM_USERNAME')

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY")
LASTFM_SUPABASE_TABLE = 'lastfm_listened_table'

if not SUPABASE_URL or not SUPABASE_KEY:
    logger.error("Missing required Supabase environment variables. Please check your .env file at app/.env.")
    sys.exit(1)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

class LastFMClient:
    API_URL = 'http://ws.audioscrobbler.com/2.0/'

    def __init__(self, api_key, username):
        self.api_key = api_key
        self.username = username

    def get_recent_tracks_page(self, limit=200, page=1):
        params = {
            'method': 'user.getrecenttracks',
            'user': self.username,
            'api_key': self.api_key,
            'format': 'json',
            'limit': limit,
            'page': page,
            'extended': 1
        }
        logger.debug(f"Requesting recent tracks page={page}, limit={limit}")
        response = requests.get(self.API_URL, params=params)
        response.raise_for_status()
        return response.json().get('recenttracks', {})

    def get_new_tracks_since(self, since_uts, sleep_sec=0.25):
        """
        Only fetch new tracks that have a 'date_uts' greater than since_uts.
        Returns a list of dicts. Stops once no further new record is found in a page.
        """
        logger.info(f"Fetching new tracks since unix timestamp: {since_uts}")
        all_new_tracks = []
        page = 1
        while True:
            try:
                data = self.get_recent_tracks_page(limit=200, page=page)
            except Exception as ex:
                logger.error(f"Failed to fetch page {page}: {ex}")
                break
            tracks = data.get('track', [])
            new_in_page = []
            for t in tracks:
                # Tracks that are currently playing don't have a "date"
                if 'date' not in t or not t['date'].get('uts'):
                    continue
                try:
                    track_uts = int(t['date']['uts'])
                except Exception:
                    continue
                if track_uts > since_uts:
                    artist_images = {img['size']: img['#text'] for img in t.get('artist', {}).get('image', [])}
                    track_images = {img['size']: img['#text'] for img in t.get('image', [])}
                    row = {
                        'artist_name': t.get('artist', {}).get('name') or t.get('artist', {}).get('#text', ''),
                        'artist_url': t.get('artist', {}).get('url', ''),
                        'artist_mbid': t.get('artist', {}).get('mbid', ''),
                        'artist_image_small': artist_images.get('small', ''),
                        'artist_image_medium': artist_images.get('medium', ''),
                        'artist_image_large': artist_images.get('large', ''),
                        'artist_image_extralarge': artist_images.get('extralarge', ''),
                        'track_name': t.get('name', ''),
                        'track_url': t.get('url', ''),
                        'track_mbid': t.get('mbid', ''),
                        'track_loved': t.get('loved', ''),
                        'track_streamable': t.get('streamable', ''),
                        'track_image_small': track_images.get('small', ''),
                        'track_image_medium': track_images.get('medium', ''),
                        'track_image_large': track_images.get('large', ''),
                        'track_image_extralarge': track_images.get('extralarge', ''),
                        'album_name': t.get('album', {}).get('#text', ''),
                        'album_mbid': t.get('album', {}).get('mbid', ''),
                        'date_uts': t.get('date', {}).get('uts', '') if 'date' in t else '',
                        'date_text': t.get('date', {}).get('#text', '') if 'date' in t else ''
                    }
                    new_in_page.append(row)
                else:
                    # Because 'user.getrecenttracks' returns them in reverse-chronological order,
                    # we can stop here: all subsequent tracks are older.
                    break
            if not new_in_page:
                break
            all_new_tracks.extend(new_in_page)
            logger.info(f"Fetched {len(new_in_page)} new tracks on page {page}.")
            time.sleep(sleep_sec)
            page += 1
        logger.info(f"Total new tracks to add: {len(all_new_tracks)}")
        return all_new_tracks

def get_latest_date_uts_from_supabase(table_name):
    """
    Query Supabase for the most recent date_uts value.
    Returns int unix timestamp, or 0 if table is empty or any issues.
    """
    try:
        res = supabase.table(table_name).select('date_uts').order('date_uts', desc=True).limit(1).execute()
        rows = getattr(res, 'data', None) or []
        if rows and rows[0].get('date_uts'):
            # If date_uts is string, ensure it's int
            try:
                return int(rows[0]['date_uts'])
            except Exception:
                return 0
    except Exception as ex:
        logger.warning(f"Could not read latest date_uts from Supabase: {ex}")
    return 0

def insert_new_tracks_to_supabase(table_name, records):
    """
    Insert records (list of dicts) to supabase table, batched.
    """
    if not records:
        logger.info("No new records to insert.")
        return

    batch_size = 500
    for i in range(0, len(records), batch_size):
        batch = records[i:i + batch_size]
        try:
            res = supabase.table(table_name).insert(batch).execute()
        except Exception as ex:
            logger.error(f"Batch insert threw an exception: {ex}")
            continue
        error_msg = getattr(res, "error", None) or (getattr(res, "data", None) and getattr(res.data, "error", None))
        if error_msg:
            logger.error(f"Error uploading batch {i // batch_size}: {error_msg}")
    logger.info(f"Inserted {len(records)} new records into {table_name}")


if __name__ == '__main__':
    # Load from environment; no input required
    api_key = LASTFM_API_KEY
    username = LASTFM_USERNAME

    if not api_key or not username:
        logger.error("Error: Please set LASTFM_API_KEY and LASTFM_USERNAME in your .env file at app/.env")
        sys.exit(1)

    client = LastFMClient(api_key, username)

    # 1. Get latest (max) date_uts from the database to only fetch new
    latest_uts = get_latest_date_uts_from_supabase(LASTFM_SUPABASE_TABLE)
    logger.info(f"Most recent date_uts in supabase: {latest_uts}")

    try:
        # 2. Fetch only new tracks from the API
        new_tracks = client.get_new_tracks_since(latest_uts)
        # 3. Insert any new tracks to the table
        insert_new_tracks_to_supabase(LASTFM_SUPABASE_TABLE, new_tracks)
    except Exception as e:
        logger.exception("Error occurred during LastFM incremental loading")
        sys.exit(1)
