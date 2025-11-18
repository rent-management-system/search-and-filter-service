# API Documentation

Base URL: `http://localhost:8005`

Authentication
- The majority of endpoints require a Bearer token via the `Authorization: Bearer <token>` header.
- Health and map preview endpoints do not require authentication.

Versioning
- All endpoints are prefixed with `/api/v1`.

---

## Search

GET `/api/v1/search`

Search APPROVED properties around Adama. Distance is calculated using PostgreSQL `earthdistance` from Adama center (8.5408, 39.2682).

Query parameters
- `min_price` (float, optional)
- `max_price` (float, optional)
- `house_type` (string, optional)
- `amenities` (array, optional; repeat param, e.g. `amenities=wifi&amenities=parking`)
- `max_distance_km` (float, optional; default 20) – distance radius around Adama
- `sort_by` (string, optional; `distance`|`price`; default `distance`)
- Note: `location` is ignored for scoping. This service is Adama-only.

Response (200)
```
[
  {
    "id": "<uuid>",
    "title": "<string>",
    "description": "<string>",
    "location": "Adama",
    "price": <float>,
    "house_type": "<string>",
    "amenities": ["<string>", ...],
    "lat": <float>,
    "lon": <float>,
    "distance_km": <float>,
    "map_url": "<string|nullable>",
    "preview_url": "http://localhost:8005/api/v1/map/preview?lat=...&lon=...&zoom=14"
  }
]
```

Error Responses
- 400 – invalid input (e.g., `min_price > max_price`)
- 401 – unauthenticated
- 403 – forbidden role (only Tenants may search)
- 500 – internal error

Examples
- Price filter within Adama, sort by price:
  - GET `/api/v1/search?min_price=5000&max_price=20000&sort_by=price`
- Distance filter of 12km from Adama center:
  - GET `/api/v1/search?max_distance_km=12&sort_by=distance`

---

## Get Single Property

GET `/api/v1/property/{id}`

Fetch one property by UUID.

Response (200)
```
{
  "id": "<uuid>",
  "title": "<string>",
  "description": "<string>",
  "location": "Adama",
  "price": <float>,
  "house_type": "<string>",
  "amenities": ["<string>", ...],
  "lat": <float>,
  "lon": <float>,
  "distance_km": <float>,
  "map_url": "<string|nullable>",
  "preview_url": "http://localhost:8005/api/v1/map/preview?lat=...&lon=...&zoom=14"
}
```

Error Responses
- 401 – unauthenticated
- 404 – not found
- 500 – internal error

---

## Save Search

POST `/api/v1/saved-searches`

Save a user’s search preferences.

Request body
```
{
  "location": "Adama",          // optional (kept for compatibility)
  "min_price": 5000,             // optional
  "max_price": 20000,            // optional
  "house_type": "apartment",    // optional
  "amenities": ["wifi"],         // optional
  "max_distance_km": 10          // optional
}
```

Response (200)
```
{
  "id": 123,
  "message": "Search saved"
}
```

Error Responses
- 401 – unauthenticated
- 403 – forbidden role (only Tenants may save searches)
- 500 – internal error

---

## Map Tile Proxy

GET `/api/v1/map/tile/{z}/{x}/{y}`

Proxies map tiles from Gebeta Maps and caches them in Redis. Returns `image/png` bytes.

Response codes
- 200 – tile bytes
- 500 – error fetching tile

---

## Map Preview (No Auth)

GET `/api/v1/map/preview?lat=8.54&lon=39.27&zoom=14`

Returns an interactive Leaflet map centered at the given coordinates using the tile proxy. No authentication required.

Response
- 200 – HTML document

---

## Geocode and External

- Geocoding is not used by property search. The service supports Gebeta ONM/Matrix under `/api/v1/onm/*` for routing use-cases if needed.
- Endpoints:
  - POST `/api/v1/onm/route`
  - POST `/api/v1/onm/nearest`

---

## Health (No Auth)

- GET `/api/v1/health` → `{ "status": "ok" }`
- GET `/api/v1/health/ready` → readiness including `redis` and `database` checks.
