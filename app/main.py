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

@app.get("/api/books")
def get_books():
    try:
        result = supabase.table("worldly_good_reads_books").select("*").filter("date_read", "not.is", "null").execute()
        return result.data if result.data else []
    except Exception as e:
        return {"error": str(e), "message": "Failed to fetch books"}

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
