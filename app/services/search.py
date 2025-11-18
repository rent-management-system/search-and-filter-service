from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.sql import text
from app.config import settings
from structlog import get_logger
from redis.asyncio import Redis
import json
from typing import List, Optional
from app.schemas.search import SavedSearchRequest # Added this import

logger = get_logger()

async def search_properties(
    location: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    house_type: Optional[str] = None,
    amenities: Optional[List[str]] = None,
    bedrooms: Optional[int] = None,  # kept for backward compatibility; not used in query
    use_distance: Optional[bool] = True,
    max_distance_km: Optional[float] = None,
    sort_by: str = "distance" # Default sort by distance
) -> List[dict]:
    
    amenities_str = ','.join(sorted(amenities)) if amenities else ''
    cache_key = f"search:{location}:{min_price}:{max_price}:{house_type}:{amenities_str}:{bedrooms}:{use_distance}:{max_distance_km}:{sort_by}"
    redis = Redis.from_url(settings.REDIS_URL, encoding="utf-8", decode_responses=True)
    
    cached = await redis.get(cache_key)
    if cached:
        logger.info("Search cache hit", cache_key=cache_key)
        return json.loads(cached)
    
    logger.info("Search cache miss", cache_key=cache_key)

    async_engine = create_async_engine(settings.DATABASE_URL)
    async with AsyncSession(async_engine) as db:
        # Base query with distance calculation using earthdistance
        query_str = """
            SELECT id::text as id, title, description, location, price, house_type, amenities, lat, lon,
            (earth_distance(ll_to_earth(lat, lon), ll_to_earth(:user_lat, :user_lon)) / 1000.0) AS distance_km
            FROM properties
            WHERE status = 'APPROVED'
        """
        params = {}
        conditions = []
        
        # Enforce Adama-only scope regardless of provided location/use_distance
        adama_mode = True

        # Prepare distance params from Adama center regardless, in case needed
        user_lat, user_lon = 8.5408, 39.2682
        params["user_lon"] = user_lon
        params["user_lat"] = user_lat

        # Always apply Adama distance radius
        if max_distance_km is None:
            max_distance_km = 20.0
        conditions.append("earth_distance(ll_to_earth(lat, lon), ll_to_earth(:user_lat, :user_lon)) <= :max_distance_meters")
        params["max_distance_meters"] = float(max_distance_km) * 1000.0


        if min_price is not None:
            conditions.append("price >= :min_price")
            params["min_price"] = min_price
        if max_price is not None:
            conditions.append("price <= :max_price")
            params["max_price"] = max_price
        if house_type:
            conditions.append("house_type = :house_type")
            params["house_type"] = house_type
        if amenities:
            # Assuming amenities is stored as a JSONB array or similar in PostgreSQL
            # This condition checks if all provided amenities are present in the property's amenities
            conditions.append("amenities @> :amenities_json")
            params["amenities_json"] = json.dumps(amenities) # Pass as JSON string for @> operator
        
        if conditions:
            query_str += " AND " + " AND ".join(conditions)
        
        # Add ordering
        if sort_by == "distance" and adama_mode:
            query_str += " ORDER BY distance_km"
        elif sort_by == "price":
            query_str += " ORDER BY price"
        # Default ordering if no specific sort_by or location for distance sort
        else:
            query_str += " ORDER BY id" # Fallback to ID for consistent ordering

        result = await db.execute(text(query_str), params)
        listings = [dict(row) for row in result.mappings()]

        for listing in listings:
            if listing.get("lat") is not None and listing.get("lon") is not None:
                # Ensure map link is centered on the property but scoped in context of Adama
                listing["map_url"] = (
                    f"https://mapapi.gebeta.app/staticmap?center={listing['lat']},{listing['lon']}&zoom=14&size=600x300&apiKey={settings.GEBETA_API_KEY}"
                )
                listing["preview_url"] = f"/api/v1/map/preview?lat={listing['lat']}&lon={listing['lon']}&zoom=14"
            else:
                listing["map_url"] = None # Or a default map URL
                listing["preview_url"] = None

        await redis.setex(cache_key, 3600, json.dumps(listings, default=str))
        return listings

async def get_property_by_id(prop_id: str) -> Optional[dict]:
    async_engine = create_async_engine(settings.DATABASE_URL)
    async with AsyncSession(async_engine) as db:
        # Compute distance from Adama center as context
        query_str = """
            SELECT id::text as id, title, description, location, price, house_type, amenities, lat, lon,
            (earth_distance(ll_to_earth(lat, lon), ll_to_earth(:user_lat, :user_lon)) / 1000.0) AS distance_km
            FROM properties
            WHERE id = :pid
        """
        params = {"pid": prop_id, "user_lat": 8.5408, "user_lon": 39.2682}
        result = await db.execute(text(query_str), params)
        row = result.mappings().first()
        if not row:
            return None
        item = dict(row)
        if item.get("lat") is not None and item.get("lon") is not None:
            item["map_url"] = (
                f"https://mapapi.gebeta.app/staticmap?center={item['lat']},{item['lon']}&zoom=14&size=600x300&apiKey={settings.GEBETA_API_KEY}"
            )
            item["preview_url"] = f"/api/v1/map/preview?lat={item['lat']}&lon={item['lon']}&zoom=14"
        else:
            item["map_url"] = None
            item["preview_url"] = None
        return item
async def save_search(user_id: int, request: SavedSearchRequest) -> int:
    async_engine = create_async_engine(settings.DATABASE_URL)
    async with AsyncSession(async_engine) as db:
        saved_search = SavedSearch(
            user_id=user_id,
            location=request.location,
            min_price=request.min_price,
            max_price=request.max_price,
            house_type=request.house_type,
            amenities=request.amenities,
            max_distance_km=request.max_distance_km
        )
        db.add(saved_search)
        await db.commit()
        await db.refresh(saved_search)
        return saved_search.id