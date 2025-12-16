from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from pathlib import Path
from supa import supabase

app = FastAPI()

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
def read_root():
    return {"message": "Welcome to Worldly API"}

@app.get("/globe")
def get_globe():
    """Serve the globe visualization HTML page (React version)"""
    globe_path = Path(__file__).parent / "globe.html"
    return FileResponse(globe_path)

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


@app.get("/api/albums")
def get_albums():
    try:
        result = supabase.table("worldly_albums").select("*").execute()
        return result.data if result.data else []
    except Exception as e:
        return {"error": str(e), "message": "Failed to fetch albums"}

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

@app.post("/api/quotes")
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

@app.patch("/api/books/{book_id}")
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
