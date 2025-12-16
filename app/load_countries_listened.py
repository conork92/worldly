import csv
from pathlib import Path

from supa import supabase

# Configure path to CSV
CSV_PATH = Path(__file__).parent / "data" / "bea_music.csv"

def load_bea_music_to_db():
    # Open CSV file
    with open(CSV_PATH, 'r', newline='', encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        rows = list(reader)
        for row in rows:
            # Remove leading/trailing whitespace and handle missing fields as None
            record = {k: (v.strip() if isinstance(v, str) and v.strip() != "" else None) for k, v in row.items()}

            # Parse and convert fields if necessary, handle as null if empty or invalid
            rating = record.get('rating')
            try:
                rating = float(rating) if rating is not None else None
            except Exception:
                rating = None

            year = record.get('year')
            try:
                year = int(year) if year is not None else None
            except Exception:
                year = None

            # Ensure iso_alpha_2 is uppercased and max 2 chars
            iso_alpha_2 = record.get('iso_alpha_2')
            if iso_alpha_2 is not None:
                iso_alpha_2 = iso_alpha_2.upper()
                if len(iso_alpha_2) > 2:
                    iso_alpha_2 = None  # Handle overflow as None

            # Ensure iso_alpha_3 is uppercased and max 3 chars
            iso_alpha_3 = record.get('iso_alpha_3')
            if iso_alpha_3 is not None:
                iso_alpha_3 = iso_alpha_3.upper()
                if len(iso_alpha_3) > 3:
                    iso_alpha_3 = None

            insert_record = {
                'country_name': record.get('country_name'),
                'iso_alpha_2': iso_alpha_2,
                'iso_alpha_3': iso_alpha_3,
                'artist': record.get('artist'),
                'album': record.get('album'),
                'rating': rating,
                'listen_date': record.get('listen_date'),
                'comments': record.get('comments'),
                'state_or_country': record.get('state_or_country'),
                'year': year,
                'spotify_link': record.get('spotify_link')
                # 'created_at' and 'updated_at' handled by DB default
            }

            # Insert into worldly_countrys_listened
            supabase.table("worldly_countrys_listened").insert(insert_record).execute()

if __name__ == "__main__":
    load_bea_music_to_db()
    print("Loaded app/data/bea_music.csv into worldly_countrys_listened.")

