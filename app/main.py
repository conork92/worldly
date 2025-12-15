from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
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
        ]
        return hex_data
    except Exception as e:
        return {"error": str(e), "message": "Failed to fetch world hexed polygons data"}
