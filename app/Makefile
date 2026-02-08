start:
	./venv/bin/uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Pull latest books from Goodreads (scraped from your read shelf; no CSV). Set GOODREADS_SESSION and GOODREADS_LIST_URL in .env
pull-books:
	cd $(dir $(MAKEFILE_LIST)) && ./venv/bin/python scripts/scrape_goodreads.py

# Pull from CSV instead: export from Goodreads, save to app/data/, then run this
pull-books-csv:
	cd $(dir $(MAKEFILE_LIST)) && ./venv/bin/python scripts/load_goodreads.py