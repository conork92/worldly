import os
from supabase import create_client, Client
from pathlib import Path
from dotenv import load_dotenv

# Load .env if present (local/dev). In Cloud Run, env vars are set by the platform.
_app_dir = Path(__file__).resolve().parent
_root_dir = _app_dir.parent
for _env_path in (_root_dir / ".env", _app_dir / ".env"):
    if _env_path.exists():
        load_dotenv(_env_path)

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_ANON_KEY")

if not url or not key:
    raise ValueError("SUPABASE_URL and SUPABASE_ANON_KEY must be set in environment variables")

supabase: Client = create_client(url, key)

