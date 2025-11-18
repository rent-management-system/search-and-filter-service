from fastapi import APIRouter
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
