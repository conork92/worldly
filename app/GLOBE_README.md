# Globe Visualization Setup

This project includes a hexed polygons globe visualization using react-globe.gl and globe.gl libraries.

## Files

- `main-globe.py` - FastAPI backend with endpoints for globe data
- `globe.html` - React-based globe visualization (requires react-globe.gl)
- `globe-simple.html` - Simple globe visualization using globe.gl (recommended for quick setup)

## Quick Start

### 1. Start the FastAPI server

```bash
cd app
uvicorn main-globe:app --reload
```

The server will run on `http://localhost:8000`

### 2. View the Globe

**Option A: Simple Version (Recommended)**
- Open `http://localhost:8000/globe-simple` in your browser
- Uses the base `globe.gl` library which works directly with CDN

**Option B: React Version**
- Open `http://localhost:8000/globe` in your browser
- Uses `react-globe.gl` (may require proper build setup)

**Option C: Direct File**
- Open `globe-simple.html` directly in your browser
- Make sure the FastAPI server is running on `http://localhost:8000`

## API Endpoints

- `GET /api/world_hexed_polygons` - Returns hexed polygon data in format:
  ```json
  [
    {"lat": 51.5, "lng": -0.09, "value": 10},
    {"lat": 48.85, "lng": 2.35, "value": 8},
    ...
  ]
  ```

## Customization

The hexed polygons visualization can be customized by modifying the globe properties:

- `hexBinResolution` - Controls the hexagon size (default: 4)
- `hexTopColor` / `hexSideColor` - Colors based on data values
- `hexBinPointWeight` - Which field to use for weighting
- `atmosphereColor` - Color of the atmosphere glow

## Data Format

The API endpoint expects data in the format:
```json
{
  "lat": <latitude>,
  "lng": <longitude>,
  "value": <numeric_value>
}
```

You can modify the `/api/world_hexed_polygons` endpoint in `main-globe.py` to pull real data from your database.

## References

- [react-globe.gl GitHub](https://github.com/vasturiano/react-globe.gl)
- [globe.gl Documentation](https://globe.gl/)
- [Hexed Polygons Example](https://github.com/vasturiano/react-globe.gl#hexed-country-polygons)

