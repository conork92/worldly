import json
from pathlib import Path
from supa import supabase

def load_quotes(json_path="app/data/quotes_keep.json"):
    """
    Loads quotes from a JSON file and inserts them into the worldly_quotes table in Supabase.
    Skips duplicates (by quote text and author).
    """
    # Load existing quotes from Supabase (to check for duplicates)
    existing_quotes = set()
    try:
        data = supabase.table("worldly_quotes").select("quote,author").execute()
        if data.data:
            for item in data.data:
                key = (
                    item.get("quote", "").strip(),
                    (item.get("author") or "").strip()
                )
                existing_quotes.add(key)
    except Exception as e:
        print("Warning: Could not fetch existing quotes from Supabase.", e)

    # Load local quotes
    json_file = Path(json_path)
    with open(json_file, "r", encoding="utf-8") as f:
        data = json.load(f)
        # top-level may be dict with 'quotes' or just a list
        if isinstance(data, list):
            quotes = data
        elif isinstance(data, dict) and "quotes" in data:
            quotes = data["quotes"]
        else:
            print("JSON structure not recognized.")
            return

    inserted_count = 0
    for q in quotes:
        quote_text = q.get("quote", "").strip()
        author = (q.get("author") or "").strip()
        key = (quote_text, author)
        if key in existing_quotes:  # Skip duplicates
            continue

        payload = {
            "quote": quote_text,
            "author": author if author else None,
            "source": q.get("book") or q.get("source"),
            "type": q.get("type"),
            "page": q.get("page"),
            "country": q.get("country"),
            "iso_code_3": q.get("iso_code_3"),
            "year": q.get("year"),
            "category": q.get("category"),
            "tags": q["tags"] if "tags" in q else (q["theme"].split(",") if "theme" in q else None),
        }
        # Remove empty fields to avoid inserting null/None where not needed
        payload = {k: v for k, v in payload.items() if v}

        try:
            resp = supabase.table("worldly_quotes").insert(payload).execute()
            if hasattr(resp, "data") and resp.data:
                inserted_count += 1
        except Exception as e:
            print(f"Error inserting quote: {quote_text[:70]}...", e)

    print(f"Done! Inserted {inserted_count} new quotes.")

if __name__ == "__main__":
    load_quotes()
