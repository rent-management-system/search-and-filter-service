from fastapi import APIRouter, Query
from fastapi.responses import HTMLResponse

router = APIRouter(prefix="/api/v1", tags=["map"], include_in_schema=True)


def _html_page(lat: float, lon: float, zoom: int, tile_url: str) -> str:
    return f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" />
  <title>Map Preview</title>
  <link rel=\"stylesheet\" href=\"https://unpkg.com/leaflet@1.9.4/dist/leaflet.css\" crossorigin=\"\" />
  <style>html, body, #map {{ height: 100%; margin: 0; }}</style>
</head>
<body>
<div id=\"map\"></div>
<script src=\"https://unpkg.com/leaflet@1.9.4/dist/leaflet.js\" crossorigin=\"\"></script>
<script>
  const lat = {lat};
  const lon = {lon};
  const zoom = {zoom};
  const map = L.map('map').setView([lat, lon], zoom);
  L.tileLayer('{tile_url}', {{
    maxZoom: 19,
    tileSize: 256,
    zoomOffset: 0,
    attribution: '&copy; Gebeta Maps'
  }}).addTo(map);
  L.marker([lat, lon]).addTo(map);
</script>
</body>
</html>
"""


@router.get("/map/preview", response_class=HTMLResponse)
async def map_preview(
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
    zoom: int = Query(14, ge=3, le=19),
):
    """
    Simple unauthenticated HTML page to preview a map centered at lat/lon using the service's tile proxy.
    """
    # Use local proxy so no API key is exposed to clients
    tile_url = "/api/v1/map/tile/{z}/{x}/{y}"
    return HTMLResponse(content=_html_page(lat, lon, zoom, tile_url))
