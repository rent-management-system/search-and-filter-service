from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import search
from app.routers import onm
from app.core.logging import setup_logging
from fastapi_limiter import FastAPILimiter
from redis.asyncio import Redis
from app.config import settings

app = FastAPI(title="Search & Filters Microservice")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://*.onrender.com", "https://*.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(search.router)
app.include_router(onm.router)

@app.on_event("startup")
async def startup_event():
    setup_logging()
    redis = await Redis.from_url(settings.REDIS_URL, encoding="utf-8", decode_responses=True)
    await FastAPILimiter.init(redis)
