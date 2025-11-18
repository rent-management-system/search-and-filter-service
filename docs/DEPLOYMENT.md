# Deployment Guide (Production)

This guide outlines what you need to run the service in production, with a checklist and recommended settings.

## 1) Environment Variables

Create a `.env` file (or environment variables in your platform) with at least:

- `DATABASE_URL` = `postgresql+asyncpg://<user>:<password>@<host>:5432/<db>`
- `REDIS_URL` = `redis://<host>:6379/0`
- `GEBETA_API_KEY` = `<your-gebeta-api-key>`
- `BASE_URL` = `https://your-domain` (used to build absolute preview links)

Keep secrets out of your repo. Use your hosting provider's secret manager when possible.

## 2) Database

Enable required extensions and run schema/migrations.

- Extensions (once per database):
  ```sql
  CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
  CREATE EXTENSION IF NOT EXISTS cube;
  CREATE EXTENSION IF NOT EXISTS earthdistance;
  ```
- Apply schema and triggers (optional if using Alembic only):
  ```bash
  ./migrate.sh
  ```
- Recommended indexes (performance):
  ```sql
  -- distance searches around Adama
  CREATE INDEX IF NOT EXISTS idx_properties_latlon ON properties USING GIST (ll_to_earth(lat, lon));
  CREATE INDEX IF NOT EXISTS idx_properties_status ON properties (status);
  CREATE INDEX IF NOT EXISTS idx_properties_price ON properties (price);
  ```

## 3) Running the App

### a) Direct (Uvicorn)
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2
```

### b) Production (Gunicorn + Uvicorn workers)
```bash
gunicorn app.main:app \
  -k uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --workers 2 \
  --timeout 60
```

Tune workers by CPU core count and traffic pattern.

## 4) Docker (Optional)

- Build:
  ```bash
  docker build -t property-search:latest .
  ```
- Run:
  ```bash
  docker run --env-file .env -p 8000:8000 property-search:latest
  ```

If needed, replace the container `CMD` with Gunicorn in your Dockerfile for production.

## 5) CORS & Rate Limiting

- CORS is already enabled in `app/main.py`. Set `allow_origins` to your front-end domains.
- Rate limiting uses Redis via `fastapi-limiter`; keep Redis highly available for consistent limits.

## 6) Health & Readiness

- `GET /api/v1/health` – liveness
- `GET /api/v1/health/ready` – checks Redis and DB

Use these in your load balancer / orchestrator (Kubernetes probes, etc.).

## 7) Logging & Monitoring

- Structured logging via `structlog` is configured on startup.
- Aggregate logs (CloudWatch, ELK, Stackdriver) and set alerts on error rates.

## 8) Security

- All non-health endpoints require Bearer auth; the token is verified by the user management service.
- Ensure HTTPS end-to-end. Terminate TLS at the ingress/load balancer and forward to the app.
- Rotate `GEBETA_API_KEY` periodically.

## 9) Frontend Map Integration

- Prefer `preview_url` returned by the API, which renders an interactive Leaflet map using the service's tile proxy. This avoids exposing your map API key to the browser.
- Static map links may not be available on your current plan; the preview endpoint is designed to work regardless.

## 10) Testing

- Run unit tests locally:
  ```bash
  pytest -q
  ```
- Add smoke tests on `/api/v1/health`, `/api/v1/health/ready`, and `/api/v1/search` in your CI/CD.

## 11) Pagination (Recommended)

- For large datasets, add pagination to `/api/v1/search` (e.g., `limit` & `offset` query params and `ORDER BY`). This keeps responses fast and small.

## 12) Observability (Optional)

- Add request IDs and include them in logs.
- Integrate tracing (OpenTelemetry) if required by your platform.

## 13) Known Limits (Mitigations Applied)

- Static map endpoint is not guaranteed -> The service serves an internal **preview map** instead, powered by tile proxy.
- External dependencies (Redis, user-management) -> health/readiness checks in place.
- Rate limiting -> backed by Redis; ensure stable Redis.
