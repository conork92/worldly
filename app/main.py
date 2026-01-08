from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from pathlib import Path
from supa import supabase
import os
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

@app.get("/books")
def get_books_page():
    """Serve the books HTML page"""
    books_path = Path(__file__).parent / "books.html"
    return FileResponse(books_path)

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
        return result.data if result.data else []
    except Exception as e:
        return {"error": str(e), "message": "Failed to fetch quotes"}

@app.get("/api/quotes/random")
def get_random_quote():
    """Get a random quote"""
    try:
        result = supabase.table("worldly_quotes").select("*").execute()
        if result.data and len(result.data) > 0:
            import random
            return random.choice(result.data)
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
