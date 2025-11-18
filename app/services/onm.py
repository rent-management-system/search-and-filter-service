import json
from typing import List, Tuple, Dict, Any, Optional

import httpx
from structlog import get_logger
from redis.asyncio import Redis

from app.config import settings
from app.utils.retry import retry

logger = get_logger()


# Utilities to load and cache the dataset in-memory
_ROUTES_DATA: Optional[List[Dict[str, Any]]] = None


def _normalize_coord(lat: float, lon: float) -> str:
    return f"{lat},{lon}"


def _coords_list_param(coords: List[Tuple[float, float]]) -> str:
    # Builds: [{lat,lon},{lat,lon},...]
    return ",".join([f"{{{c[0]},{c[1]}}}" for c in coords])


def load_routes_dataset() -> List[Dict[str, Any]]:
    global _ROUTES_DATA
    if _ROUTES_DATA is None:
        with open(settings.ROUTES_DATA_PATH, "r", encoding="utf-8") as f:
            _ROUTES_DATA = json.load(f)
    return _ROUTES_DATA


@retry(tries=3, delay=1, backoff=2)
async def onm_route(origin_lat: float, origin_lon: float, waypoints: List[Tuple[float, float]]) -> Dict[str, Any]:
    """
    Call Gebeta ONM API with origin and up to 10 waypoints (API limit).
    Returns JSON response from Gebeta.
    """
    if len(waypoints) == 0:
        raise ValueError("At least one waypoint is required")
    if len(waypoints) > 10:
        logger.warning("Waypoints exceed limit; trimming to 10", count=len(waypoints))
        waypoints = waypoints[:10]

    origin_param = _normalize_coord(origin_lat, origin_lon)
    coords_param = _coords_list_param(waypoints)
    url = (
        f"{settings.ONM_API_BASE}?json=[{coords_param}]&origin={origin_param}&apiKey={settings.GEBETA_API_KEY}"
    )

    redis = Redis.from_url(settings.REDIS_URL, encoding="utf-8", decode_responses=True)
    cache_key = f"onm:{origin_param}:[{coords_param}]"
    cached = await redis.get(cache_key)
    if cached:
        logger.info("ONM cache hit", cache_key=cache_key)
        return json.loads(cached)

    logger.info("ONM cache miss", url=url)
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(url)
        try:
            resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            logger.error("ONM error", status=e.response.status_code, text=e.response.text)
            raise
        data = resp.json()
        await redis.setex(cache_key, 600, json.dumps(data))
        return data


@retry(tries=3, delay=1, backoff=2)
async def matrix(coords: List[Tuple[float, float]]) -> Dict[str, Any]:
    """
    Call Gebeta Matrix API for a set of coordinates (<= 10 as per docs).
    Returns JSON response from Gebeta.
    """
    if len(coords) < 2:
        raise ValueError("Matrix requires at least two coordinates")
    if len(coords) > 10:
        logger.warning("Matrix coords exceed limit; trimming to 10", count=len(coords))
        coords = coords[:10]

    coords_param = _coords_list_param(coords)
    url = f"{settings.MATRIX_API_BASE}?json=[{coords_param}]&apiKey={settings.GEBETA_API_KEY}"

    redis = Redis.from_url(settings.REDIS_URL, encoding="utf-8", decode_responses=True)
    cache_key = f"matrix:[{coords_param}]"
    cached = await redis.get(cache_key)
    if cached:
        logger.info("Matrix cache hit", cache_key=cache_key)
        return json.loads(cached)

    logger.info("Matrix cache miss", url=url)
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(url)
        try:
            resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            logger.error("Matrix error", status=e.response.status_code, text=e.response.text)
            raise
        data = resp.json()
        await redis.setex(cache_key, 600, json.dumps(data))
        return data


def get_destinations_from_dataset() -> List[Dict[str, Any]]:
    return load_routes_dataset()


def resolve_destinations_by_name(names: List[str]) -> List[Tuple[float, float]]:
    data = load_routes_dataset()
    idx = {item["destination"].lower(): (item["dest_lat"], item["dest_lon"]) for item in data}
    coords: List[Tuple[float, float]] = []
    for n in names:
        c = idx.get(n.lower())
        if c:
            coords.append(c)
    return coords
