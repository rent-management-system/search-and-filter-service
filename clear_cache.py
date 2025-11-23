#!/usr/bin/env python3
"""
Script to clear Redis cache for the search service.
Run this after making changes to the search queries.
"""
import asyncio
from redis.asyncio import Redis
from app.config import settings

async def clear_cache():
    redis = Redis.from_url(settings.REDIS_URL, encoding="utf-8", decode_responses=True)
    
    # Clear all search-related cache keys
    keys = await redis.keys("search:*")
    keys.extend(await redis.keys("all_approved_properties"))
    
    if keys:
        deleted = await redis.delete(*keys)
        print(f"✓ Cleared {deleted} cache keys")
    else:
        print("✓ No cache keys found")
    
    await redis.close()
    print("✓ Cache cleared successfully!")

if __name__ == "__main__":
    asyncio.run(clear_cache())
