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

# Load environment variables
load_dotenv()

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
static_dir = Path(__file__).parent
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
    globe_path = Path(__file__).parent / "globe.html"
    return FileResponse(globe_path)

@app.get("/country")
def get_country():
    """Serve the country details HTML page"""
    country_path = Path(__file__).parent / "country.html"
    return FileResponse(country_path)

@app.get("/globe-simple")
def get_globe_simple():
    """Serve the simple globe visualization HTML page (globe.gl version)"""
    globe_path = Path(__file__).parent / "globe-simple.html"
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
        
        # Get books with countries
        books_result = supabase.table("worldly_good_reads_books").select("iso_code_3, country").filter("date_read", "not.is", "null").execute()
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
                return {"error": str(rpc_error), "rpc_error": str(rpc_error), "table_error": str(table_error), "message": f"Failed to fetch items for country {iso_code_3}"}
    except Exception as e:
        print(f"[DEBUG] Outer exception: {str(e)}")
        return {"error": str(e), "message": f"Failed to fetch items for country {iso_code_3}"}

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
    albums_path = Path(__file__).parent / "albums.html"
    return FileResponse(albums_path)

@app.get("/api/albums")
def get_albums():
    try:
        result = supabase.table("worldly_albums").select("*").execute()
        return result.data if result.data else []
    except Exception as e:
        return {"error": str(e), "message": "Failed to fetch albums"}

@app.get("/api/albums/listened")
def get_albums_listened():
    """Get albums from worldly_countrys_listened table"""
    try:
        result = supabase.table("worldly_countrys_listened").select("*").execute()
        return result.data if result.data else []
    except Exception as e:
        return {"error": str(e), "message": "Failed to fetch listened albums"}

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
    books_path = Path(__file__).parent / "books.html"
    return FileResponse(books_path)

@app.get("/listening")
def get_listening_page():
    """Serve the Last.fm listening page"""
    listening_path = Path(__file__).parent / "listening.html"
    return FileResponse(listening_path)

@app.get("/progress")
def get_progress_page():
    """Serve the progress tracking page"""
    progress_path = Path(__file__).parent / "progress.html"
    return FileResponse(progress_path)

@app.get("/api/listening")
def get_listening_tracks(limit: int = 100):
    """Get recent tracks from lastfm_listened_table"""
    try:
        result = supabase.table("lastfm_listened_table").select("*").order("date_uts", desc=True).limit(limit).execute()
        return result.data if result.data else []
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
        
        # Sort albums by listen_date (most recent first)
        def get_sort_date(album):
            listen_date = album.get('listen_date')
            parsed = parse_date(listen_date)
            return parsed if parsed else datetime.min
        
        filtered_albums.sort(key=get_sort_date, reverse=True)
        
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
            exercise_goal = 20 * 12  # 240 exercises per year
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
            exercise_goal = 20  # 20 exercises per month
        
        # Dummy data for other categories (can be updated later)
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
                "count": 3,
                "goal": books_goal,
                "percentage": int((3 / books_goal * 100)) if books_goal > 0 else 0,
                "trend": "same"
            },
            "meditations_done": {
                "count": 18,
                "goal": days_in_period,  # Goal equals number of days in the period
                "percentage": int((18 / days_in_period * 100)) if days_in_period > 0 else 0,
                "trend": "up"
            },
            "exercise_done": {
                "count": 12,
                "goal": exercise_goal,
                "percentage": int((12 / exercise_goal * 100)) if exercise_goal > 0 else 0,
                "trend": "down"
            },
            "albums": filtered_albums  # Include the albums list
        }
        
        return progress_data
    except Exception as e:
        return {"error": str(e), "message": "Failed to fetch progress data"}

@app.get("/quotes")
def get_quotes_page():
    """Serve the quotes HTML page"""
    quotes_path = Path(__file__).parent / "quotes.html"
    return FileResponse(quotes_path)

@app.get("/api/books")
def get_books():
    try:
        result = supabase.table("worldly_good_reads_books").select("*").filter("date_read", "not.is", "null").execute()
        return result.data if result.data else []
    except Exception as e:
        return {"error": str(e), "message": "Failed to fetch books"}

@app.get("/api/quotes")
def get_quotes():
    try:
        result = supabase.table("worldly_quotes").select("*").execute()
        quotes = result.data if result.data else []
        
        # Filter out quotes from CK, Conor, or Conor Kennedy (case-insensitive)
        excluded_authors = ['ck', 'conor', 'conor kennedy']
        filtered_quotes = [
            quote for quote in quotes
            if not quote.get('author') or quote.get('author', '').strip().lower() not in excluded_authors
        ]
        
        return filtered_quotes
    except Exception as e:
        return {"error": str(e), "message": "Failed to fetch quotes"}

@app.get("/api/quotes/random")
def get_random_quote():
    """Get a random quote (excluding quotes from CK, Conor, or Conor Kennedy)"""
    try:
        result = supabase.table("worldly_quotes").select("*").execute()
        quotes = result.data if result.data else []
        
        # Filter out quotes from CK, Conor, or Conor Kennedy (case-insensitive)
        excluded_authors = ['ck', 'conor', 'conor kennedy']
        filtered_quotes = [
            quote for quote in quotes
            if not quote.get('author') or quote.get('author', '').strip().lower() not in excluded_authors
        ]
        
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
    """Get books that need country assignment (empty country or iso_code_3)"""
    try:
        # Get all books with date_read, then filter in Python for empty country/iso_code_3
        result = supabase.table("worldly_good_reads_books").select("*").filter("date_read", "not.is", "null").execute()
        if result.data:
            # Filter for books with empty country or iso_code_3
            filtered = [
                book for book in result.data 
                if not book.get("country") or not book.get("iso_code_3")
            ]
            return filtered
        return []
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
        country_path = Path(__file__).parent / "country.html"
        return FileResponse(country_path)
    else:
        raise HTTPException(status_code=404, detail="Invalid country code format. Expected 3-letter ISO code (e.g., NGA, USA, FRA)")
