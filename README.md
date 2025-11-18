# Search & Filters Microservice

This microservice handles searching and filtering of rental properties.

## Setup

1.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
2.  **Set up environment variables:**
    Create a `.env` file from `.env.example` and fill in the values.
3.  **Run migrations:**
    ```bash
    ./migrate.sh
    ```
4.  **Run the service:**
    ```bash
    uvicorn app.main:app --host 0.0.0.0 --port 8000
    ```

## Endpoints

- `GET /api/v1/search`: Search for properties.
- `POST /api/v1/saved-searches`: Save a search.
- `GET /api/v1/map/tile/{z}/{x}/{y}`: Proxy for Gebeta Maps tiles.
- `GET /api/v1/geocode/{query}`: Proxy for Gebeta Maps geocoding.
