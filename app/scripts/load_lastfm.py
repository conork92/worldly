import csv
import os
from supabase import create_client, Client
import logging
from dotenv import load_dotenv
import sys

# --- Setup Logging ---
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Load environment variables from project root .env (single source of truth)
_app_dir = os.path.dirname(os.path.dirname(__file__))
_root_dir = os.path.dirname(_app_dir)
dotenv_path = os.path.join(_root_dir, '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_ANON_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    logger.error("Missing required Supabase environment variables. Please check your .env file at app/.env.")
    sys.exit(1)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def upload_lastfm_csv_to_supabase_table(csv_path, table_name):
    if not os.path.exists(csv_path):
        logger.error(f"CSV not found: {csv_path}")
        raise FileNotFoundError(f"CSV not found: {csv_path}")

    with open(csv_path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)

        if not rows:
            logger.error("No data found in CSV.")
            return

        # Batch insert, up to 500 records at a time
        batch_size = 500
        for i in range(0, len(rows), batch_size):
            batch = rows[i:i + batch_size]
            try:
                res = supabase.table(table_name).insert(batch).execute()
            except Exception as ex:
                logger.error(f"Batch insert threw an exception: {ex}")
                continue
            error_msg = getattr(res, "error", None) or (getattr(res, "data", None) and getattr(res.data, "error", None))
            if error_msg:
                logger.error(f"Error uploading batch {i // batch_size}: {error_msg}")

if __name__ == "__main__":
    try:
        upload_lastfm_csv_to_supabase_table(
            csv_path='data/lastfm_listen_history_extended.csv',
            table_name='lastfm_listened_table'
        )
    except FileNotFoundError as e:
        logger.error(str(e))
        sys.exit(2)
    except Exception as e:
        logger.exception("Unexpected error during table upload.")
        sys.exit(1)
