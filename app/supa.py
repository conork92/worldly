import os
from supabase import create_client, Client
from pathlib import Path
from dotenv import load_dotenv

# Load .env if present (local/dev). In Cloud Run, env vars are set by the platform.
_load_env = Path(__file__).resolve().parent.parent / ".env"
if _load_env.exists():
    load_dotenv(_load_env)

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_ANON_KEY")

if not url or not key:
    raise ValueError("SUPABASE_URL and SUPABASE_ANON_KEY must be set in environment variables")

supabase: Client = create_client(url, key)

