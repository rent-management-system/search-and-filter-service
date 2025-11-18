import httpx
from app.config import settings
from app.utils.retry import retry
from structlog import get_logger
from redis.asyncio import Redis
import json
import asyncio

logger = get_logger()

@retry(tries=3, delay=1, backoff=2)
async def geocode(query: str) -> dict:
    redis = Redis.from_url(settings.REDIS_URL, encoding="utf-8", decode_responses=True)
    cache_key = f"geocode:{query}"
    cached = await redis.get(cache_key)
    if cached:
        logger.info("Geocode cache hit", query=query)
        return json.loads(cached)
    
    logger.info("Geocode cache miss", query=query)
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.gebeta.app/geocode",
                params={"query": query},
                headers={"X-Gebeta-API-Key": settings.GEBETA_API_KEY}
            )
            response.raise_for_status() # Raises HTTPStatusError for bad responses (4xx or 5xx)
            data = response.json()
            if not data:
                raise ValueError("Geocoding returned no results")
            result = data[0]
            await redis.setex(cache_key, 3600, json.dumps(result))  # Cache for 1 hour
            return result
    except Exception as e:
        logger.warning("Geocoding failed, using fallback", query=query, error=str(e))
        # Fallback to Addis Ababa center
        return {"lat": 9.03, "lon": 38.75}

@retry(tries=3, delay=1, backoff=2)
async def get_map_tile(z: int, x: int, y: int) -> bytes:
    # Use binary-safe Redis connection for tiles
    redis = Redis.from_url(settings.REDIS_URL, decode_responses=False)
    cache_key = f"tile:{z}:{x}:{y}"
    cached = await redis.get(cache_key)
    if cached is not None:
        logger.info("Map tile cache hit", cache_key=cache_key)
        return cached  # bytes
    
    logger.info("Map tile cache miss", cache_key=cache_key)
    async with httpx.AsyncClient() as client:
        try:
            # Use mapapi host with explicit PNG extension and apiKey query
            response = await client.get(
                f"https://mapapi.gebeta.app/tiles/{z}/{x}/{y}.png?apiKey={settings.GEBETA_API_KEY}"
            )
            response.raise_for_status()
            tile = response.content  # bytes
            await redis.setex(cache_key, 3600, tile)  # Cache for 1 hour
            return tile
        except httpx.HTTPStatusError as e:
            logger.error("Map tile failed", z=z, x=x, y=y, status_code=e.response.status_code, response=e.response.text)
            raise ValueError(f"Map tile failed: {e.response.status_code}")
        except httpx.RequestError as e:
            logger.error("Map tile failed", z=z, x=x, y=y, error=str(e))
            raise ValueError(f"Map tile failed: {str(e)}")
