from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from pathlib import Path
from supa import supabase
import os
import subprocess
import sys
from dotenv import load_dotenv

# Load environment variables: project root and app directory
_app_dir = Path(__file__).resolve().parent
_root_dir = _app_dir.parent
for _env_path in (_root_dir / ".env", _app_dir / ".env"):
    if _env_path.exists():
        load_dotenv(_env_path)

app = FastAPI()

# Authentication: API Key from environment variable
API_KEY = os.getenv("API_KEY")
if not API_KEY:
    print("WARNING: API_KEY not set in environment. Write operations will be disabled.")
    print("Set API_KEY in your .env file to enable write operations.")

def verify_api_key(x_api_key: str = Header(None)):
    """Verify API key for write operations"""
    if not API_KEY:
        raise HTTPException(status_code=503, detail="API authentication not configured")
    if not x_api_key:
        raise HTTPException(status_code=401, detail="API key required. Provide X-API-Key header.")
    if x_api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API key")
    return True

# Mount static files directory
static_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Enable CORS if needed
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
@app.get("/globe")
def get_globe():
    """Serve the globe visualization HTML page (React version)"""
    globe_path = Path(__file__).parent / "templates" / "globe.html"
    return FileResponse(globe_path)

@app.get("/country")
def get_country():
    """Serve the country details HTML page"""
    country_path = Path(__file__).parent / "templates" / "country.html"
    return FileResponse(country_path)

@app.get("/globe-simple")
def get_globe_simple():
    """Serve the simple globe visualization HTML page (globe.gl version)"""
    globe_path = Path(__file__).parent / "templates" / "globe.html"
    return FileResponse(globe_path)

@app.get("/api/countries")
def get_countries():
    try:
        result = supabase.table("worldly_countries").select("*").execute()
        return result.data if result.data else []
    except Exception as e:
        return {"error": str(e), "message": "Failed to fetch countries"}

@app.get("/api/countries/with-data")
def get_countries_with_data():
    """Get countries that have associated data (books, albums, artists)"""
    try:
        # Get all countries
        countries_result = supabase.table("worldly_countries").select("*").execute()
        if not countries_result.data:
            return []
        
        # Get books with countries (using same filter as country_items_view: only books with valid ISO codes)
        books_result = supabase.table("worldly_good_reads_books").select("iso_code_3, country").filter("date_read", "not.is", "null").filter("iso_code_3", "not.is", "null").neq("iso_code_3", "").neq("iso_code_3", "N/A").execute()
        books_countries = set()
        if books_result.data:
            books_countries = set([b.get("iso_code_3") for b in books_result.data if b.get("iso_code_3")])
        
        # Get albums with countries
        albums_result = supabase.table("worldly_albums").select("iso_code_3, country").execute()
        albums_countries = set()
        if albums_result.data:
            albums_countries = set([a.get("iso_code_3") for a in albums_result.data if a.get("iso_code_3")])
        
        # Get artists with countries
        artists_result = supabase.table("worldly_artists").select("iso_code_3, country").execute()
        artists_countries = set()
        if artists_result.data:
            artists_countries = set([a.get("iso_code_3") for a in artists_result.data if a.get("iso_code_3")])
        
        # Combine all countries with data
        all_countries_with_data = books_countries | albums_countries | artists_countries
        
        # Mark countries that have data
        countries_with_data = []
        for country in countries_result.data:
            has_data = country.get("iso_code_3") in all_countries_with_data
            country_info = {
                **country,
                "has_data": has_data,
                "data_types": []
            }
            if country.get("iso_code_3") in books_countries:
                country_info["data_types"].append("books")
            if country.get("iso_code_3") in albums_countries:
                country_info["data_types"].append("albums")
            if country.get("iso_code_3") in artists_countries:
                country_info["data_types"].append("artists")
            
            countries_with_data.append(country_info)
        
        return countries_with_data
    except Exception as e:
        return {"error": str(e), "message": "Failed to fetch countries with data"}

@app.get("/api/country-items/{iso_code_3}")
def get_country_items(iso_code_3: str):
    """
    Get all items (books, albums) for a country using country_items_view by iso_code_3.
    This pulls from the Postgres function/view directly for combined items.
    """
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        # Normalize ISO code (uppercase)
        iso_code_3 = iso_code_3.upper().strip()
        print(f"[DEBUG] get_country_items called with iso_code_3: {iso_code_3}")
        
        # Try calling the PostgreSQL function first
        try:
            print(f"[DEBUG] Attempting RPC call to country_items_view with iso_code_3: {iso_code_3}")
            # RPC calls return all data, we need to filter in Python
            result = supabase.rpc("country_items_view", {"finished_only": False}).execute()
            print(f"[DEBUG] RPC result: {len(result.data) if result.data else 0} total items")
            
            # Debug: Count items by type and ISO code
            if result.data:
                books_by_iso = {}
                albums_by_iso = {}
                for item in result.data:
                    iso_val = item.get("iso_alpha_3") or item.get("iso_code_3") or "NULL"
                    item_type = item.get("type", "unknown")
                    if item_type == "book":
                        books_by_iso[iso_val] = books_by_iso.get(iso_val, 0) + 1
                    elif item_type == "album":
                        albums_by_iso[iso_val] = albums_by_iso.get(iso_val, 0) + 1
                
                print(f"[DEBUG] Books by ISO: {dict(list(books_by_iso.items())[:10])}")  # Show first 10
                print(f"[DEBUG] Albums by ISO: {dict(list(albums_by_iso.items())[:10])}")  # Show first 10
                if iso_code_3 in books_by_iso:
                    print(f"[DEBUG] Found {books_by_iso[iso_code_3]} books for {iso_code_3}")
                if iso_code_3 in albums_by_iso:
                    print(f"[DEBUG] Found {albums_by_iso[iso_code_3]} albums for {iso_code_3}")
            
            if result.data:
                # Filter by iso_alpha_3 in Python
                # Also check for iso_code_3 as a fallback (for books that might use different field name)
                filtered_items = []
                books_count = 0
                albums_count = 0
                null_iso_count = 0
                
                for item in result.data:
                    iso_value = item.get("iso_alpha_3") or item.get("iso_code_3")
                    if iso_value:
                        iso_normalized = str(iso_value).upper().strip()
                        if iso_normalized == iso_code_3:
                            filtered_items.append(item)
                            if item.get("type") == "book":
                                books_count += 1
                            elif item.get("type") == "album":
                                albums_count += 1
                    else:
                        # Count items with null ISO codes for debugging
                        if item.get("type") == "book":
                            null_iso_count += 1
                            print(f"[DEBUG] Book with null ISO: {item.get('title', 'Unknown')} - type: {item.get('type')}, iso_alpha_3: {item.get('iso_alpha_3')}, iso_code_3: {item.get('iso_code_3')}")
                
                print(f"[DEBUG] Filtered to {len(filtered_items)} items for {iso_code_3} (Books: {books_count}, Albums: {albums_count})")
                if null_iso_count > 0:
                    print(f"[DEBUG] Found {null_iso_count} books with null ISO codes that were excluded")
                print(f"[DEBUG] Sample items: {filtered_items[:2] if filtered_items else 'None'}")
                return filtered_items
            else:
                print(f"[DEBUG] No data returned from RPC")
                return []
        except Exception as rpc_error:
            print(f"[DEBUG] RPC failed: {str(rpc_error)}, trying table approach...")
            # If RPC fails, try alternative approach - query the view directly
            try:
                result = supabase.table("country_items_view").select("*").eq("iso_alpha_3", iso_code_3).execute()
                print(f"[DEBUG] Table query result: {len(result.data) if result.data else 0} items")
                return result.data if result.data else []
            except Exception as table_error:
                print(f"[DEBUG] Table query also failed: {str(table_error)}")
                # Return empty array instead of error object to prevent frontend issues
                logger.warning(f"Failed to fetch items for {iso_code_3}: RPC error: {str(rpc_error)}, Table error: {str(table_error)}")
                return []
    except Exception as e:
        print(f"[DEBUG] Outer exception: {str(e)}")
        # Return empty array instead of error object to prevent frontend issues
        logger.warning(f"Failed to fetch items for {iso_code_3}: {str(e)}")
        return []

@app.get("/api/world_hexed_polygons")
def get_world_hexed_polygons():
    """
    Endpoint to return Hexed Polygons Layer data suitable for react-globe.gl.
    This returns an array of {"lat": ..., "lng": ..., "value": ...} objects.
    """
    try:
        # Sample/dummy data for demonstration
        # You can modify this to pull actual data from your database
        hex_data = [
            {"lat": 51.5, "lng": -0.09, "value": 10},
            {"lat": 48.85, "lng": 2.35, "value": 8},
            {"lat": 40.71, "lng": -74.00, "value": 12},
            {"lat": 35.69, "lng": 139.69, "value": 7},
            {"lat": -33.87, "lng": 151.21, "value": 5},
            {"lat": 55.75, "lng": 37.62, "value": 9},
            {"lat": 39.90, "lng": 116.41, "value": 15},
            {"lat": 19.43, "lng": -99.13, "value": 6},
            {"lat": -22.91, "lng": -43.17, "value": 11},
            {"lat": 28.61, "lng": 77.21, "value": 13},
            {"lat": 6.5244, "lng": 3.3792, "value": 8},
        ]
        return hex_data
    except Exception as e:
        return {"error": str(e), "message": "Failed to fetch world hexed polygons data"}


@app.get("/albums")
def get_albums_page():
    """Serve the albums HTML page"""
    albums_path = Path(__file__).parent / "templates" / "albums.html"
    return FileResponse(albums_path)

@app.get("/api/albums")
def get_albums():
    try:
        result = supabase.table("worldly_albums").select("*").execute()
        return result.data if result.data else []
    except Exception as e:
        return {"error": str(e), "message": "Failed to fetch albums"}

@app.get("/api/albums/suggested")
def get_suggested_album():
    """Get a random suggested album from worldly_albums"""
    try:
        import random
        result = supabase.table("worldly_albums").select("*").execute()
        albums = result.data if result.data else []
        if albums:
            return random.choice(albums)
        return {}
    except Exception as e:
        return {"error": str(e), "message": "Failed to fetch suggested album"}

@app.get("/api/albums/suggested/{iso_code_3}")
def get_suggested_albums_for_country(iso_code_3: str, limit: int = 5):
    """Get suggested albums from worldly_albums for a specific country"""
    try:
        import random
        iso_code_3 = iso_code_3.upper().strip()
        result = supabase.table("worldly_albums").select("*").eq("iso_code_3", iso_code_3).execute()
        albums = result.data if result.data else []
        
        if albums:
            # Return up to 'limit' random albums
            if len(albums) <= limit:
                return albums
            else:
                return random.sample(albums, limit)
        return []
    except Exception as e:
        return {"error": str(e), "message": f"Failed to fetch suggested albums for country {iso_code_3}"}

@app.get("/api/albums/suggested-for-unlistened")
def get_suggested_album_for_unlistened(iso_code_3: str = None):
    """Get a random suggested album from worldly_albums, optionally filtered by country"""
    try:
        import random
        if iso_code_3:
            iso_code_3 = iso_code_3.upper().strip()
            result = supabase.table("worldly_albums").select("*").eq("iso_code_3", iso_code_3).execute()
            albums = result.data if result.data else []
            if albums:
                return random.choice(albums)
        
        # If no country or no albums for that country, get any random album
        result = supabase.table("worldly_albums").select("*").execute()
        albums = result.data if result.data else []
        if albums:
            return random.choice(albums)
        return {}
    except Exception as e:
        return {"error": str(e), "message": "Failed to fetch suggested album"}

class BatchRequest(BaseModel):
    iso_codes: list = []

@app.post("/api/albums/suggested-batch")
def get_suggested_albums_batch(request: BatchRequest):
    """Get suggested albums for multiple ISO codes in one request - optimized for performance"""
    try:
        import random
        iso_codes = request.iso_codes if request.iso_codes else []
        
        # Fetch all albums once
        albums_result = supabase.table("worldly_albums").select("*").execute()
        all_albums = albums_result.data if albums_result.data else []
        
        if not all_albums:
            return {}
        
        # Fetch artists to get correct country associations
        artists_result = supabase.table("worldly_artists").select("name, iso_code_3").execute()
        artists_by_name = {}
        if artists_result.data:
            for artist in artists_result.data:
                artist_name = artist.get('name', '').lower().strip()
                if artist_name:
                    artists_by_name[artist_name] = artist.get('iso_code_3', '').upper().strip()
        
        # Known artist-country associations for validation (fallback if not in artists table)
        known_artists = {
            'bjork': 'ISL',  # Iceland
            'björk': 'ISL',
            'bob dylan': 'USA',
            'bob dulan': 'USA',  # Common misspelling
        }
        
        # Group albums by ISO code, using artist's country when available
        albums_by_country = {}
        for album in all_albums:
            artist_name = album.get('artist_name', '').lower().strip()
            album_iso = album.get('iso_code_3', '').upper().strip() if album.get('iso_code_3') else None
            
            # Try to get correct ISO from artists table first
            correct_iso = None
            if artist_name in artists_by_name:
                correct_iso = artists_by_name[artist_name]
            elif artist_name in known_artists:
                correct_iso = known_artists[artist_name]
            
            # Use correct ISO if found, otherwise use album's ISO (but log warning)
            iso_to_use = correct_iso if correct_iso else album_iso
            
            if iso_to_use:
                # If we corrected the ISO, log it
                if correct_iso and album_iso and correct_iso != album_iso:
                    print(f"[INFO] Corrected {album.get('artist_name')} from {album_iso} to {correct_iso}")
                
                if iso_to_use not in albums_by_country:
                    albums_by_country[iso_to_use] = []
                albums_by_country[iso_to_use].append(album)
        
        # Get suggested album for each ISO code
        suggestions = {}
        for iso_code in iso_codes:
            iso_code = iso_code.upper().strip() if iso_code else None
            if iso_code and iso_code in albums_by_country and len(albums_by_country[iso_code]) > 0:
                # Pick a random album from that country
                suggestions[iso_code] = random.choice(albums_by_country[iso_code])
        
        # Also add a general "any" suggestion for albums without country
        if all_albums:
            suggestions['any'] = random.choice(all_albums)
        
        return suggestions
    except Exception as e:
        return {"error": str(e), "message": "Failed to fetch suggested albums"}

@app.get("/api/albums/listened")
def get_albums_listened():
    """Get albums from worldly_countrys_listened table"""
    try:
        result = supabase.table("worldly_countrys_listened").select("*").execute()
        return result.data if result.data else []
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch listened albums: {str(e)}"
        )

class AlbumUpdate(BaseModel):
    album: str = None
    artist: str = None
    rating: float = None
    listen_date: str = None
    country_name: str = None
    iso_alpha_2: str = None
    iso_alpha_3: str = None
    year: int = None
    spotify_link: str = None
    comments: str = None
    fav_tracks: list[str] = None

@app.patch("/api/albums/listened/{album_id}")
def update_album_listened(album_id: int, update: AlbumUpdate):
    """Update an album in worldly_countrys_listened table"""
    try:
        # Remove None values
        update_data = update.dict(exclude_none=True)
        
        result = supabase.table("worldly_countrys_listened").update(update_data).eq("id", album_id).execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Album not found")
        
        return {"success": True, "data": result.data[0]}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update album: {str(e)}")

@app.get("/api/artists")
def get_artists():
    try:
        result = supabase.table("worldly_artists").select("*").execute()
        return result.data if result.data else []
    except Exception as e:
        return {"error": str(e), "message": "Failed to fetch artists"}

@app.get("/api/artists/country/{iso_code_3}")
def get_artists_by_country(iso_code_3: str):
    """Get artists for a specific country by ISO code"""
    try:
        iso_code_3 = iso_code_3.upper().strip()
        result = supabase.table("worldly_artists").select("*").eq("iso_code_3", iso_code_3).execute()
        return result.data if result.data else []
    except Exception as e:
        return {"error": str(e), "message": "Failed to fetch artists for country"}

class ArtistCreate(BaseModel):
    name: str
    iso_code_2: str
    iso_code_3: str
    country: str = None
    country_id: int = None
    genre: str = None
    formation_year: int = None
    biography: str = None
    bea_artist_link: str = None

@app.post("/api/artists", dependencies=[Depends(verify_api_key)])
def create_artist(artist: ArtistCreate):
    """Create a new artist"""
    try:
        # Normalize ISO codes
        artist_data = artist.dict(exclude_none=True)
        artist_data["iso_code_2"] = artist_data["iso_code_2"].upper().strip()
        artist_data["iso_code_3"] = artist_data["iso_code_3"].upper().strip()
        
        result = supabase.table("worldly_artists").insert(artist_data).execute()
        
        if not result.data:
            raise HTTPException(status_code=500, detail="Failed to create artist")
        
        return result.data[0]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create artist: {str(e)}")

@app.get("/books")
def get_books_page():
    """Serve the books HTML page"""
    books_path = Path(__file__).parent / "templates" / "books.html"
    return FileResponse(books_path)

@app.get("/movies")
def get_movies_page():
    """Serve the Letterboxd movies page (watched + watchlist)"""
    movies_path = Path(__file__).parent / "templates" / "movies.html"
    return FileResponse(movies_path)

def _movies_enrichment_rows():
    """Fetch all rows from letterboxd_tmdb_enrichment with poster/backdrop as full URLs."""
    r = supabase.table("letterboxd_tmdb_enrichment").select(
        "name,year,runtime_minutes,genres,director,overview,poster_path,backdrop_path,tagline,"
        "vote_average,vote_count,release_date,production_countries,spoken_languages"
    ).execute()
    rows = []
    for row in (r.data or []):
        p = (row.get("poster_path") or "").strip()
        b = (row.get("backdrop_path") or "").strip()
        row = dict(row)
        row["poster_url"] = p if (p and p.startswith("http")) else ("https://image.tmdb.org/t/p/w500" + p if p else None)
        row["backdrop_url"] = b if (b and b.startswith("http")) else ("https://image.tmdb.org/t/p/w780" + b if b else None)
        rows.append(row)
    return rows


@app.get("/api/movies/filters")
def get_movies_filters():
    """Return distinct genres, years, production_countries, spoken_languages and runtime range for filter UI."""
    try:
        rows = _movies_enrichment_rows()
        genres = set()
        years = set()
        countries = set()
        languages = set()
        runtimes = []
        for row in rows:
            for g in row.get("genres") or []:
                if g:
                    genres.add(g)
            rd = row.get("release_date") or ""
            if len(rd) >= 4:
                years.add(rd[:4])
            for c in row.get("production_countries") or []:
                if c:
                    countries.add(c)
            sl = (row.get("spoken_languages") or "").strip()
            if sl:
                for part in sl.replace(",", " ").split():
                    part = part.strip()
                    if part:
                        languages.add(part)
            rt = row.get("runtime_minutes")
            if rt is not None:
                runtimes.append(rt)
        return {
            "genres": sorted(genres),
            "years": sorted(years, reverse=True),
            "production_countries": sorted(countries),
            "spoken_languages": sorted(languages),
            "runtime_min": min(runtimes) if runtimes else None,
            "runtime_max": max(runtimes) if runtimes else None,
        }
    except Exception:
        return {"genres": [], "years": [], "production_countries": [], "spoken_languages": [], "runtime_min": None, "runtime_max": None}


@app.get("/api/movies")
def get_movies(
    filter: str = "all",
    posters: bool = True,
    genre: str = None,
    length_min: int = None,
    length_max: int = None,
    year: str = None,
    production_country: str = None,
    spoken_languages: str = None,
    order_by: str = None,
    order_dir: str = "desc",
):
    """Get movies from letterboxd_tmdb_enrichment, with optional join to watched/watchlist for source/date/uri. Supports filters and ordering."""
    try:
        # Letterboxd lookup: (name, year) -> date, letterboxd_uri, source
        watched_key_to_meta = {}
        watchlist_key_to_meta = {}
        if filter in ("all", "watched"):
            r = supabase.table("letterboxd_watched").select("date,name,year,letterboxd_uri").order("date", desc=True).execute()
            for x in (r.data or []):
                key = ((x.get("name") or "").strip(), (x.get("year") or "").strip())
                watched_key_to_meta[key] = {"date": x.get("date"), "letterboxd_uri": x.get("letterboxd_uri"), "source": "watched"}
        if filter in ("all", "watchlist"):
            r = supabase.table("letterboxd_watchlist").select("date,name,year,letterboxd_uri").order("date", desc=True).execute()
            for x in (r.data or []):
                key = ((x.get("name") or "").strip(), (x.get("year") or "").strip())
                watchlist_key_to_meta[key] = {"date": x.get("date"), "letterboxd_uri": x.get("letterboxd_uri"), "source": "watchlist"}

        rows = _movies_enrichment_rows()
        # Restrict by list filter: only include (name,year) that exist in watched and/or watchlist when filter is watched/watchlist
        if filter == "watched":
            rows = [m for m in rows if (m.get("name") or "").strip() and ((m.get("name") or "").strip(), (m.get("year") or "").strip()) in watched_key_to_meta]
        elif filter == "watchlist":
            rows = [m for m in rows if (m.get("name") or "").strip() and ((m.get("name") or "").strip(), (m.get("year") or "").strip()) in watchlist_key_to_meta]

        for m in rows:
            key = ((m.get("name") or "").strip(), (m.get("year") or "").strip())
            meta = watched_key_to_meta.get(key) or watchlist_key_to_meta.get(key)
            if meta:
                m["date"] = meta.get("date")
                m["letterboxd_uri"] = meta.get("letterboxd_uri")
                m["source"] = meta.get("source")
            else:
                m["date"] = None
                m["letterboxd_uri"] = None
                m["source"] = "enrichment"

        # Filters
        if genre:
            genre_lower = genre.strip().lower()
            rows = [m for m in rows if (m.get("genres") or []) and any((g or "").strip().lower() == genre_lower for g in m.get("genres"))]
        if length_min is not None:
            rows = [m for m in rows if m.get("runtime_minutes") is not None and m["runtime_minutes"] >= length_min]
        if length_max is not None:
            rows = [m for m in rows if m.get("runtime_minutes") is not None and m["runtime_minutes"] <= length_max]
        if year:
            year_s = str(year).strip()
            rows = [m for m in rows if (m.get("release_date") or "")[:4] == year_s]
        if production_country:
            pc = production_country.strip()
            rows = [m for m in rows if (m.get("production_countries") or []) and any((c or "").strip() == pc for c in m.get("production_countries"))]
        if spoken_languages:
            sl_param = spoken_languages.strip().lower()
            rows = [m for m in rows if sl_param in ((m.get("spoken_languages") or "").lower())]

        # Order
        order_by = (order_by or "release_date").strip().lower()
        order_dir = (order_dir or "desc").strip().lower()
        reverse = order_dir == "desc"

        def sort_key(m):
            if order_by == "vote_average":
                v = m.get("vote_average")
                return (v is None, v if v is not None else 0)
            if order_by == "vote_count":
                v = m.get("vote_count")
                return (v is None, v if v is not None else 0)
            if order_by == "release_date":
                return (m.get("release_date") or "")
            if order_by == "name":
                return (m.get("name") or "").lower()
            return (m.get("release_date") or "")

        rows.sort(key=sort_key, reverse=reverse)

        if not posters:
            for m in rows:
                m["poster_url"] = None
                m["backdrop_url"] = None

        return rows
    except Exception:
        return []

@app.get("/listening")
def get_listening_page():
    """Serve the Last.fm listening page"""
    listening_path = Path(__file__).parent / "templates" / "listening.html"
    return FileResponse(listening_path)

@app.get("/progress")
def get_progress_page():
    """Serve the progress tracking page"""
    progress_path = Path(__file__).parent / "templates" / "progress.html"
    return FileResponse(progress_path)

@app.get("/exercise")
def get_exercise_page():
    """Serve the Exercise (Strava) page"""
    exercise_path = Path(__file__).parent / "templates" / "exercise.html"
    return FileResponse(exercise_path)

@app.get("/api/listening")
def get_listening_tracks(limit: int = 100, month: int = None, year: int = None):
    """Get tracks from lastfm_listened_table, optionally filtered by month and year"""
    try:
        result = supabase.table("lastfm_listened_table").select("*").order("date_uts", desc=True).execute()
        tracks = result.data if result.data else []
        
        # Filter by month and year if provided
        if month is not None and year is not None:
            from datetime import datetime
            filtered_tracks = []
            for track in tracks:
                if track.get('date_uts'):
                    try:
                        # date_uts is Unix timestamp
                        track_date = datetime.fromtimestamp(int(track['date_uts']))
                        if track_date.month == month and track_date.year == year:
                            filtered_tracks.append(track)
                    except (ValueError, TypeError):
                        continue
            tracks = filtered_tracks
        
        # Apply limit after filtering
        if limit and limit > 0:
            tracks = tracks[:limit]
        
        return tracks
    except Exception as e:
        return {"error": str(e), "message": "Failed to fetch listening tracks"}

@app.post("/api/listening/refresh", dependencies=[Depends(verify_api_key)])
def refresh_listening_data():
    """Trigger the Last.fm script to update the listening data"""
    try:
        # Get the path to the lastfm script
        script_path = Path(__file__).parent / "scripts" / "lastfm.py"
        
        if not script_path.exists():
            raise HTTPException(status_code=404, detail="Last.fm script not found")
        
        # Run the script in the background
        # Use the same Python interpreter
        python_path = sys.executable
        process = subprocess.Popen(
            [python_path, str(script_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=str(Path(__file__).parent)
        )
        
        # Don't wait for completion - return immediately
        # The script will run in the background
        return {
            "success": True,
            "message": "Last.fm data refresh started",
            "pid": process.pid
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start refresh: {str(e)}")

@app.get("/api/exercise")
def get_exercise_data(month: int = None, year: int = None, limit: int = 500):
    """Get Strava activities from worldly_strava, optionally filtered by month/year"""
    try:
        q = supabase.table("worldly_strava").select("*").order("start_date_local", desc=True)
        if limit and limit > 0:
            q = q.limit(limit)
        r = q.execute()
        rows = list(r.data or [])
        if month is not None and year is not None:
            from datetime import datetime
            filtered = []
            for row in rows:
                sd = row.get("start_date_local") or row.get("start_date")
                if not sd:
                    continue
                if isinstance(sd, str):
                    try:
                        dt = datetime.fromisoformat(sd.replace("Z", "+00:00"))
                    except Exception:
                        continue
                else:
                    dt = sd
                if dt.month == month and dt.year == year:
                    filtered.append(row)
            rows = filtered
        return rows
    except Exception as e:
        return {"error": str(e), "message": "Failed to fetch exercise data"}

@app.post("/api/exercise/refresh", dependencies=[Depends(verify_api_key)])
def refresh_exercise_data():
    """Trigger Strava pull script to sync activities into worldly_strava"""
    try:
        script_path = Path(__file__).parent / "scripts" / "pull_strava.py"
        if not script_path.exists():
            raise HTTPException(status_code=404, detail="Strava pull script not found")
        python_path = sys.executable
        process = subprocess.Popen(
            [python_path, str(script_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=str(Path(__file__).parent),
        )
        return {
            "success": True,
            "message": "Strava data refresh started",
            "pid": process.pid,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start refresh: {str(e)}")

@app.get("/api/auth/status")
def get_auth_status():
    """Check if API key authentication is configured (without revealing the key)"""
    return {
        "api_key_configured": API_KEY is not None and len(API_KEY) > 0,
        "message": "API key is configured" if API_KEY else "API key is not configured. Set API_KEY in your .env file."
    }

@app.get("/api/progress")
def get_progress_data(month: int = None, year: int = None, all_months: bool = False):
    """Get progress data for a specific month and year, or all months in a year"""
    try:
        # Use current month/year if not specified
        from datetime import datetime
        import calendar
        
        # Parse all_months from query string (FastAPI converts it)
        if year is None:
            year = datetime.now().year
        if not all_months:
            if month is None:
                month = datetime.now().month
        else:
            # When all_months is True, month is not needed
            month = None
        
        # Get albums listened in the specified month/year
        albums_result = supabase.table("worldly_countrys_listened").select("*").execute()
        albums = albums_result.data if albums_result.data else []
        
        # Get books read from worldly_good_reads_books
        books_result = supabase.table("worldly_good_reads_books").select("*").filter("date_read", "not.is", "null").execute()
        books = books_result.data if books_result.data else []
        
        # Helper function to parse dates
        def parse_date(date_str):
            """Parse various date formats"""
            if not date_str:
                return None
            
            if isinstance(date_str, datetime):
                return date_str
            
            if not isinstance(date_str, str):
                return None
            
            date_str = date_str.strip()
            if not date_str:
                return None
            
            # Try multiple date formats
            formats = [
                '%Y-%m-%d',                    # 2024-01-15
                '%d %b %Y',                    # 15 Jan 2024
                '%d %B %Y',                    # 15 January 2024
                '%Y-%m-%d %H:%M:%S',          # 2024-01-15 12:30:45
                '%Y-%m-%dT%H:%M:%S',          # 2024-01-15T12:30:45
                '%Y-%m-%dT%H:%M:%SZ',         # 2024-01-15T12:30:45Z
                '%d/%m/%Y',                    # 15/01/2024
                '%m/%d/%Y',                    # 01/15/2024
                '%d-%m-%Y',                    # 15-01-2024
            ]
            
            for fmt in formats:
                try:
                    return datetime.strptime(date_str.split(',')[0].strip(), fmt)
                except:
                    continue
            
            # Try ISO format
            try:
                return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            except:
                pass
            
            return None
        
        # Filter albums by month and year based on listen_date
        filtered_albums = []
        for album in albums:
            if album.get('listen_date'):
                try:
                    listen_date = album['listen_date']
                    date_obj = parse_date(listen_date)
                    
                    if date_obj:
                        if all_months:
                            # Include all albums from the year
                            if date_obj.year == year:
                                filtered_albums.append(album)
                        else:
                            # Include albums from specific month
                            if date_obj.month == month and date_obj.year == year:
                                filtered_albums.append(album)
                except Exception as e:
                    # Skip albums with unparseable dates
                    continue
        
        # Filter books by month and year based on date_read
        filtered_books = []
        for book in books:
            if book.get('date_read'):
                try:
                    date_read = book['date_read']
                    # date_read might be a datetime object or string
                    if isinstance(date_read, str):
                        date_obj = parse_date(date_read)
                    elif isinstance(date_read, datetime):
                        date_obj = date_read
                    else:
                        continue
                    
                    if date_obj:
                        if all_months:
                            # Include all books from the year
                            if date_obj.year == year:
                                filtered_books.append(book)
                        else:
                            # Include books from specific month
                            if date_obj.month == month and date_obj.year == year:
                                filtered_books.append(book)
                except Exception as e:
                    # Skip books with unparseable dates
                    continue
        
        # Get meditation count from ck_meditation using [Started At] for the period
        meditations_count = 0
        meditations_prev_count = 0
        meditations_trend = "same"
        try:
            med_result = supabase.table("ck_meditation").select("*").execute()
            med_rows = med_result.data if med_result.data else []
            started_key = next(
                (k for k in ("Started At", "[Started At]", "started_at") if any(r.get(k) for r in med_rows)),
                "started_at"
            )
            for r in med_rows:
                started = r.get(started_key)
                date_obj = parse_date(started) if isinstance(started, str) else (started if isinstance(started, datetime) else None)
                if not date_obj:
                    continue
                if all_months:
                    if date_obj.year == year:
                        meditations_count += 1
                    if date_obj.year == year - 1:
                        meditations_prev_count += 1
                else:
                    if date_obj.month == month and date_obj.year == year:
                        meditations_count += 1
                    prev_m = month - 1 if month > 1 else 12
                    prev_y = year if month > 1 else year - 1
                    if date_obj.month == prev_m and date_obj.year == prev_y:
                        meditations_prev_count += 1
            if meditations_prev_count < meditations_count:
                meditations_trend = "up"
            elif meditations_prev_count > meditations_count:
                meditations_trend = "down"
            else:
                meditations_trend = "same"
        except Exception:
            meditations_trend = "same"
        
        # Sort albums by listen_date (most recent first)
        def get_sort_date(album):
            listen_date = album.get('listen_date')
            parsed = parse_date(listen_date)
            return parsed if parsed else datetime.min
        
        filtered_albums.sort(key=get_sort_date, reverse=True)
        
        # Sort books by date_read (most recent first)
        def get_book_sort_date(book):
            date_read = book.get('date_read')
            if isinstance(date_read, str):
                parsed = parse_date(date_read)
            elif isinstance(date_read, datetime):
                parsed = date_read
            else:
                parsed = None
            return parsed if parsed else datetime.min
        
        filtered_books.sort(key=get_book_sort_date, reverse=True)
        
        # Calculate global albums listened stats
        albums_count = len(filtered_albums)
        
        if all_months:
            # For all months view: goal is 6 albums per month * 12 months = 72
            albums_goal = 6 * 12  # 72 albums per year
            albums_percentage = int((albums_count / albums_goal * 100)) if albums_goal > 0 else 0
            
            # Compare with previous year for trend
            prev_year_albums = []
            for album in albums:
                if album.get('listen_date'):
                    try:
                        listen_date = album['listen_date']
                        date_obj = parse_date(listen_date)
                        if date_obj and date_obj.year == year - 1:
                            prev_year_albums.append(album)
                    except:
                        continue
            
            prev_count = len(prev_year_albums)
            if albums_count > prev_count:
                albums_trend = "up"
            elif albums_count < prev_count:
                albums_trend = "down"
            else:
                albums_trend = "same"
            
            # For all months: meditation goal is total days in the year
            days_in_period = 366 if calendar.isleap(year) else 365
            books_goal = 6 * 12  # 72 books per year
            
            # Calculate books read in the year
            books_count = len(filtered_books)
            
            # Compare with previous year for books trend
            prev_year_books = []
            for book in books:
                if book.get('date_read'):
                    try:
                        date_read = book['date_read']
                        if isinstance(date_read, str):
                            date_obj = parse_date(date_read)
                        elif isinstance(date_read, datetime):
                            date_obj = date_read
                        else:
                            continue
                        if date_obj and date_obj.year == year - 1:
                            prev_year_books.append(book)
                    except:
                        continue
            
            prev_books_count = len(prev_year_books)
            if books_count > prev_books_count:
                books_trend = "up"
            elif books_count < prev_books_count:
                books_trend = "down"
            else:
                books_trend = "same"
            
            books_percentage = int((books_count / books_goal * 100)) if books_goal > 0 else 0
            exercise_goal = 10 * 12  # 120 exercises per year
        else:
            # For single month view
            albums_goal = 6  # 6 albums per month
            albums_percentage = int((albums_count / albums_goal * 100)) if albums_goal > 0 else 0
            
            # Calculate trend (compare with previous month)
            prev_month = month - 1 if month > 1 else 12
            prev_year = year if month > 1 else year - 1
            
            prev_month_albums = []
            for album in albums:
                if album.get('listen_date'):
                    try:
                        listen_date = album['listen_date']
                        date_obj = parse_date(listen_date)
                        
                        if date_obj and date_obj.month == prev_month and date_obj.year == prev_year:
                            prev_month_albums.append(album)
                    except:
                        continue
            
            prev_count = len(prev_month_albums)
            if albums_count > prev_count:
                albums_trend = "up"
            elif albums_count < prev_count:
                albums_trend = "down"
            else:
                albums_trend = "same"
            
            # Calculate number of days in the month for meditation goal
            days_in_period = calendar.monthrange(year, month)[1]
            books_goal = 6  # 6 books per month
            
            # Calculate books read in the month
            books_count = len(filtered_books)
            
            # Calculate trend (compare with previous month)
            prev_month = month - 1 if month > 1 else 12
            prev_year = year if month > 1 else year - 1
            
            prev_month_books = []
            for book in books:
                if book.get('date_read'):
                    try:
                        date_read = book['date_read']
                        if isinstance(date_read, str):
                            date_obj = parse_date(date_read)
                        elif isinstance(date_read, datetime):
                            date_obj = date_read
                        else:
                            continue
                        if date_obj and date_obj.month == prev_month and date_obj.year == prev_year:
                            prev_month_books.append(book)
                    except:
                        continue
            
            prev_books_count = len(prev_month_books)
            if books_count > prev_books_count:
                books_trend = "up"
            elif books_count < prev_books_count:
                books_trend = "down"
            else:
                books_trend = "same"
            
            books_percentage = int((books_count / books_goal * 100)) if books_goal > 0 else 0
            exercise_goal = 10  # 10 exercises per month
        
        # Exercise count from worldly_strava (Strava activities)
        exercise_count = 0
        exercise_prev_count = 0
        exercise_trend = "same"
        try:
            strava_result = supabase.table("worldly_strava").select("start_date_local,start_date").execute()
            strava_rows = strava_result.data if strava_result.data else []
            for row in strava_rows:
                sd = row.get("start_date_local") or row.get("start_date")
                date_obj = parse_date(sd) if sd and isinstance(sd, str) else (sd if isinstance(sd, datetime) else None)
                if not date_obj:
                    continue
                if all_months:
                    if date_obj.year == year:
                        exercise_count += 1
                    if date_obj.year == year - 1:
                        exercise_prev_count += 1
                else:
                    if date_obj.month == month and date_obj.year == year:
                        exercise_count += 1
                    prev_m = month - 1 if month > 1 else 12
                    prev_y = year if month > 1 else year - 1
                    if date_obj.month == prev_m and date_obj.year == prev_y:
                        exercise_prev_count += 1
            if exercise_prev_count < exercise_count:
                exercise_trend = "up"
            elif exercise_prev_count > exercise_count:
                exercise_trend = "down"
        except Exception:
            pass
        
        # Meditation goal is "one per day". For current month/year, "on track" = count >= days elapsed so far.
        def _meditations_progress(count, goal_days, trend, month_val, year_val, all_months_val):
            now = datetime.now()
            if all_months_val:
                days_elapsed = (now - datetime(year_val, 1, 1)).days + 1 if year_val == now.year else goal_days
            else:
                days_elapsed = now.day if (year_val == now.year and month_val == now.month) else goal_days
            days_elapsed = min(days_elapsed, goal_days)
            return {
                "count": count,
                "goal": goal_days,
                "goal_so_far": days_elapsed,
                "percentage": int((count / goal_days * 100)) if goal_days > 0 else 0,
                "trend": trend
            }
        
        progress_data = {
            "month": month if not all_months else None,
            "year": year,
            "all_months": all_months,
            "global_albums_listened": {
                "count": albums_count,
                "goal": albums_goal,
                "percentage": albums_percentage,
                "trend": albums_trend
            },
            "books_read": {
                "count": books_count,
                "goal": books_goal,
                "percentage": books_percentage,
                "trend": books_trend
            },
            "meditations_done": _meditations_progress(meditations_count, days_in_period, meditations_trend, month, year, all_months),
            "exercise_done": {
                "count": exercise_count,
                "goal": exercise_goal,
                "percentage": int((exercise_count / exercise_goal * 100)) if exercise_goal > 0 else 0,
                "trend": exercise_trend
            },
            "albums": filtered_albums  # Include the albums list
        }
        
        return progress_data
    except Exception as e:
        return {"error": str(e), "message": "Failed to fetch progress data"}

@app.get("/quotes")
def get_quotes_page():
    """Serve the quotes HTML page"""
    quotes_path = Path(__file__).parent / "templates" / "quotes.html"
    return FileResponse(quotes_path)

@app.get("/api/books")
def get_books():
    """Return all read books (with date_read set). Books without country show as 'No Country' and can be assigned via Assign Country."""
    try:
        result = supabase.table("worldly_good_reads_books").select("*").filter("date_read", "not.is", "null").order("date_read", desc=True).execute()
        return result.data if result.data else []
    except Exception as e:
        return {"error": str(e), "message": "Failed to fetch books"}

@app.get("/api/books/suggested")
def get_suggested_book():
    """Get a random suggested book from worldly_books"""
    try:
        import random
        result = supabase.table("worldly_books").select("*").execute()
        books = result.data if result.data else []
        if books:
            return random.choice(books)
        return {}
    except Exception as e:
        return {"error": str(e), "message": "Failed to fetch suggested book"}

@app.get("/api/quotes")
def get_quotes():
    try:
        result = supabase.table("worldly_quotes").select("*").execute()
        quotes = result.data if result.data else []
        
        # Filter out quotes from CK, Conor, or Conor Kennedy (case-insensitive)
        excluded_authors = ['ck', 'conor', 'conor kennedy']
        
        # Keywords to identify alcohol-related quotes
        alcohol_keywords = ['alcohol', 'drink', 'drunk', 'beer', 'wine', 'whiskey', 'whisky', 'vodka', 
                           'rum', 'gin', 'cocktail', 'bar', 'pub', 'drinking', 'intoxicated', 'sober',
                           'hangover', 'booze', 'liquor', 'champagne', 'tequila', 'brandy']
        
        filtered_quotes = []
        for quote in quotes:
            # Skip quotes from excluded authors
            author = quote.get('author', '').strip().lower() if quote.get('author') else ''
            if author in excluded_authors:
                continue
            
            # Skip alcohol-related quotes
            quote_text = (quote.get('quote') or '').lower()
            quote_category = (quote.get('category') or '').lower()
            quote_tags = quote.get('tags') or []
            quote_tags_lower = [str(tag).lower() for tag in quote_tags] if isinstance(quote_tags, list) else []
            
            # Check if quote contains alcohol keywords
            contains_alcohol = any(keyword in quote_text for keyword in alcohol_keywords) or \
                            any(keyword in quote_category for keyword in alcohol_keywords) or \
                            any(any(keyword in str(tag).lower() for keyword in alcohol_keywords) for tag in quote_tags_lower)
            
            if contains_alcohol:
                continue
            
            filtered_quotes.append(quote)
        
        return filtered_quotes
    except Exception as e:
        return {"error": str(e), "message": "Failed to fetch quotes"}

@app.get("/api/quotes/random")
def get_random_quote():
    """Get a random quote (excluding quotes from CK, Conor, or Conor Kennedy, and alcohol-related quotes)"""
    try:
        result = supabase.table("worldly_quotes").select("*").execute()
        quotes = result.data if result.data else []
        
        # Filter out quotes from CK, Conor, or Conor Kennedy (case-insensitive)
        excluded_authors = ['ck', 'conor', 'conor kennedy']
        
        # Keywords to identify alcohol-related quotes
        alcohol_keywords = ['alcohol', 'drink', 'drunk', 'beer', 'wine', 'whiskey', 'whisky', 'vodka', 
                           'rum', 'gin', 'cocktail', 'bar', 'pub', 'drinking', 'intoxicated', 'sober',
                           'hangover', 'booze', 'liquor', 'champagne', 'tequila', 'brandy']
        
        filtered_quotes = []
        for quote in quotes:
            # Skip quotes from excluded authors
            author = quote.get('author', '').strip().lower() if quote.get('author') else ''
            if author in excluded_authors:
                continue
            
            # Skip alcohol-related quotes
            quote_text = (quote.get('quote') or '').lower()
            quote_category = (quote.get('category') or '').lower()
            quote_tags = quote.get('tags') or []
            quote_tags_lower = [str(tag).lower() for tag in quote_tags] if isinstance(quote_tags, list) else []
            
            # Check if quote contains alcohol keywords
            contains_alcohol = any(keyword in quote_text for keyword in alcohol_keywords) or \
                            any(keyword in quote_category for keyword in alcohol_keywords) or \
                            any(any(keyword in str(tag).lower() for keyword in alcohol_keywords) for tag in quote_tags_lower)
            
            if contains_alcohol:
                continue
            
            filtered_quotes.append(quote)
        
        if filtered_quotes and len(filtered_quotes) > 0:
            import random
            return random.choice(filtered_quotes)
        return {}
    except Exception as e:
        return {"error": str(e), "message": "Failed to fetch random quote"}

class QuoteCreate(BaseModel):
    quote: str
    author: str = None
    source: str = None
    type: str = None
    page: str = None
    country: str = None
    iso_code_3: str = None
    year: int = None
    category: str = None
    tags: list = None

@app.post("/api/quotes", dependencies=[Depends(verify_api_key)])
def create_quote(quote: QuoteCreate):
    """Create a new quote"""
    try:
        payload = quote.dict(exclude_none=True)
        result = supabase.table("worldly_quotes").insert(payload).execute()
        
        if not result.data:
            raise HTTPException(status_code=400, detail="Failed to create quote")
        
        return {"success": True, "data": result.data[0]}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create quote: {str(e)}")

@app.get("/api/books/needs-country")
def get_books_needs_country():
    """Get books that need country assignment (no country or no valid iso_code_3)."""
    try:
        result = supabase.table("worldly_good_reads_books").select("*").filter("date_read", "not.is", "null").order("date_read", desc=True).execute()
        if not result.data:
            return []
        # Include books where country or iso_code_3 is missing/empty/N/A
        filtered = [
            book for book in result.data
            if not (book.get("country") or "").strip() or not (book.get("iso_code_3") or "").strip() or (book.get("iso_code_3") or "").strip().upper() == "N/A"
        ]
        return filtered
    except Exception as e:
        return {"error": str(e), "message": "Failed to fetch books needing country"}

class BookUpdate(BaseModel):
    country: str
    iso_code_3: str

@app.patch("/api/books/{book_id}", dependencies=[Depends(verify_api_key)])
def update_book_country(book_id: int, update: BookUpdate):
    """Update a book's country and ISO code"""
    try:
        result = supabase.table("worldly_good_reads_books").update({
            "country": update.country,
            "iso_code_3": update.iso_code_3
        }).eq("id", book_id).execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Book not found")
        
        return {"success": True, "data": result.data[0]}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update book: {str(e)}")

@app.get("/{iso_code}")
def get_country_by_iso(iso_code: str):
    """Serve the country details HTML page for a specific ISO code (3-letter code)
    
    This route must be placed after all other specific routes to avoid conflicts.
    Examples: /NGA, /USA, /FRA
    """
    # Validate ISO code format (should be 3 uppercase letters)
    iso_code_upper = iso_code.upper()
    if len(iso_code_upper) == 3 and iso_code_upper.isalpha():
        country_path = Path(__file__).parent / "templates" / "country.html"
        return FileResponse(country_path)
    else:
        raise HTTPException(status_code=404, detail="Invalid country code format. Expected 3-letter ISO code (e.g., NGA, USA, FRA)")
