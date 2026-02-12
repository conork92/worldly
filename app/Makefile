start:
	./venv/bin/uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Pull latest books from Goodreads (scraped from your read shelf; no CSV). Set GOODREADS_SESSION and GOODREADS_LIST_URL in .env
pull-books:
	cd $(dir $(MAKEFILE_LIST)) && ./venv/bin/python scripts/scrape_goodreads.py

# Pull from CSV instead: export from Goodreads, save to app/data/, then run this
pull-books-csv:
	cd $(dir $(MAKEFILE_LIST)) && ./venv/bin/python scripts/load_goodreads.py

# Load Letterboxd CSVs: truncate then full load first-level files from app/data/letterboxd/
load-letterboxd:
	cd $(dir $(MAKEFILE_LIST)) && ./venv/bin/python scripts/load_letterboxd.py

# Enrich Letterboxd watched + watchlist with TMDB (runtime, genre, director). Requires TMDB_API_KEY. Run letterboxd_tmdb_enrichment.sql first.
enrich-letterboxd-tmdb:
	cd $(dir $(MAKEFILE_LIST)) && ./venv/bin/python scripts/enrich_letterboxd_tmdb.py

# Pull Strava activities into worldly_strava. Requires STRAVA_CLIENT_ID, STRAVA_CLIENT_SECRET, STRAVA_REFRESH_TOKEN. Run sql/worldly_strava.sql first.
pull-strava:
	cd $(dir $(MAKEFILE_LIST)) && ./venv/bin/python scripts/pull_strava.py

# Print Strava OAuth URL (reads STRAVA_CLIENT_ID from .env). Open URL, authorize, copy the 'code' from redirect.
strava-auth-url:
	cd $(dir $(MAKEFILE_LIST)) && ./venv/bin/python scripts/strava_auth_helper.py

# Exchange Strava auth code for refresh token. Usage: make strava-exchange CODE=your_code_here
strava-exchange:
	cd $(dir $(MAKEFILE_LIST)) && ./venv/bin/python scripts/strava_auth_helper.py "$(CODE)"