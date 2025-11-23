from fastapi import APIRouter, HTTPException
from structlog import get_logger
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.sql import text

from app.config import settings

logger = get_logger()
router = APIRouter(prefix="/api/v1", tags=["health"]) 

@router.get("/health")
async def health():
    return {"status": "ok"}

@router.get("/health/ready")
async def readiness():
    details = {"status": "ok", "checks": {}}

    # Redis check
    try:
        redis = Redis.from_url(settings.REDIS_URL, encoding="utf-8", decode_responses=True)
        pong = await redis.ping()
        details["checks"]["redis"] = "ok" if pong else "fail"
    except Exception as e:
        logger.warning("health redis fail", error=str(e))
        details["checks"]["redis"] = f"fail: {str(e)}"
        details["status"] = "degraded"

    # Database check
    try:
        engine = create_async_engine(settings.DATABASE_URL)
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        details["checks"]["database"] = "ok"
    except Exception as e:
        logger.warning("health db fail", error=str(e))
        details["checks"]["database"] = f"fail: {str(e)}"
        details["status"] = "degraded"

    return details

@router.post("/cache/clear")
async def clear_cache():
    """
    Clear all Redis cache for search results.
    Use this after deploying changes to search queries.
    """
    try:
        redis = Redis.from_url(settings.REDIS_URL, encoding="utf-8", decode_responses=True)
        
        # Clear all search-related cache keys
        keys = await redis.keys("search:*")
        all_approved_key = await redis.keys("all_approved_properties")
        
        all_keys = keys + all_approved_key
        
        if all_keys:
            deleted = await redis.delete(*all_keys)
            logger.info("Cache cleared", deleted_keys=deleted)
            return {"status": "ok", "cleared_keys": deleted}
        else:
            logger.info("No cache keys to clear")
            return {"status": "ok", "cleared_keys": 0}
    except Exception as e:
        logger.error("Failed to clear cache", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to clear cache: {str(e)}")
