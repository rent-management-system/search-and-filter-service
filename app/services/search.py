from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.sql import text
from app.config import settings
from structlog import get_logger
from redis.asyncio import Redis
import json
from typing import List, Optional
from app.schemas.search import SavedSearchRequest # Added this import
from app.models.search import SavedSearch
from app.services.user import get_user_contact_info

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
        try:
            listings = json.loads(cached)
            # Ensure preview_url and map_url exist for each item (backward-compat for older cache)
            changed = False
            for listing in listings:
                lat = listing.get("lat")
                lon = listing.get("lon")
                if lat is not None and lon is not None:
                    expected_map = (
                        f"https://mapapi.gebeta.app/staticmap?center={lat},{lon}&zoom=14&size=600x300&apiKey={settings.GEBETA_API_KEY}"
                    )
                    if listing.get("map_url") != expected_map:
                        listing["map_url"] = expected_map
                        changed = True
                    if not listing.get("preview_url"):
                        listing["preview_url"] = f"/api/v1/map/preview?lat={lat}&lon={lon}&zoom=14"
                        changed = True
                else:
                    if listing.get("map_url") is not None:
                        listing["map_url"] = None
                        changed = True
                    if listing.get("preview_url") is not None:
                        listing["preview_url"] = None
                        changed = True
            if changed:
                await redis.setex(cache_key, 3600, json.dumps(listings, default=str))
            return listings
        except Exception:
            # If cache is corrupted, ignore and rebuild
            logger.warning("Cache parse/enrich failed; rebuilding", cache_key=cache_key)
    
    logger.info("Search cache miss", cache_key=cache_key)

    async_engine = create_async_engine(settings.DATABASE_URL)
    async with AsyncSession(async_engine) as db:
        params = {}
        conditions = []
        
        # Only apply distance filtering if use_distance is True and location/coordinates are provided
        if use_distance and location and max_distance_km is not None:
            # Use Adama center as default if no specific location coordinates provided
            # In a full implementation, you would geocode the location parameter here
            user_lat, user_lon = 8.5408, 39.2682
            params["user_lon"] = user_lon
            params["user_lat"] = user_lat
            
            query_str = """
                SELECT id::text as id, user_id::text as user_id, title, description, location, price, house_type, amenities, photos, lat, lon,
                (earth_distance(ll_to_earth(lat, lon), ll_to_earth(:user_lat, :user_lon)) / 1000.0) AS distance_km
                FROM properties
                WHERE status = 'APPROVED'
            """
            conditions.append("earth_distance(ll_to_earth(lat, lon), ll_to_earth(:user_lat, :user_lon)) <= :max_distance_meters")
            params["max_distance_meters"] = float(max_distance_km) * 1000.0
        else:
            # No distance filtering - search all approved properties
            query_str = """
                SELECT id::text as id, user_id::text as user_id, title, description, location, price, house_type, amenities, photos, lat, lon,
                0.0 AS distance_km
                FROM properties
                WHERE status = 'APPROVED'
            """


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
        if sort_by == "distance" and use_distance and location and max_distance_km is not None:
            query_str += " ORDER BY distance_km"
        elif sort_by == "price":
            query_str += " ORDER BY price"
        else:
            # Default ordering by ID for consistent results
            query_str += " ORDER BY id"

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
            
            # Fetch owner contact information
            user_id = listing.get("user_id")
            if user_id:
                owner_contact = await get_user_contact_info(user_id)
                listing["owner_contact"] = owner_contact
            else:
                listing["owner_contact"] = None

        await redis.setex(cache_key, 3600, json.dumps(listings, default=str))
        return listings

async def get_property_by_id(prop_id: str) -> Optional[dict]:
    async_engine = create_async_engine(settings.DATABASE_URL)
    async with AsyncSession(async_engine) as db:
        # Compute distance from Adama center as context
        query_str = """
            SELECT id::text as id, user_id::text as user_id, title, description, location, price, house_type, amenities, photos, lat, lon,
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
        
        # Fetch owner contact information
        user_id = item.get("user_id")
        if user_id:
            owner_contact = await get_user_contact_info(user_id)
            item["owner_contact"] = owner_contact
        else:
            item["owner_contact"] = None
        
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

async def get_all_approved_properties() -> List[dict]:
    """
    Retrieve all approved properties from the database without any filters.
    Returns all properties with status = 'APPROVED'.
    """
    cache_key = "all_approved_properties"
    redis = Redis.from_url(settings.REDIS_URL, encoding="utf-8", decode_responses=True)
    
    # Check cache first
    cached = await redis.get(cache_key)
    if cached:
        logger.info("All approved properties cache hit")
        try:
            listings = json.loads(cached)
            # Ensure preview_url and map_url exist for each item
            changed = False
            for listing in listings:
                lat = listing.get("lat")
                lon = listing.get("lon")
                if lat is not None and lon is not None:
                    expected_map = (
                        f"https://mapapi.gebeta.app/staticmap?center={lat},{lon}&zoom=14&size=600x300&apiKey={settings.GEBETA_API_KEY}"
                    )
                    if listing.get("map_url") != expected_map:
                        listing["map_url"] = expected_map
                        changed = True
                    if not listing.get("preview_url"):
                        listing["preview_url"] = f"/api/v1/map/preview?lat={lat}&lon={lon}&zoom=14"
                        changed = True
                else:
                    if listing.get("map_url") is not None:
                        listing["map_url"] = None
                        changed = True
                    if listing.get("preview_url") is not None:
                        listing["preview_url"] = None
                        changed = True
            if changed:
                await redis.setex(cache_key, 3600, json.dumps(listings, default=str))
            return listings
        except Exception:
            logger.warning("Cache parse/enrich failed; rebuilding", cache_key=cache_key)
    
    logger.info("All approved properties cache miss")
    
    async_engine = create_async_engine(settings.DATABASE_URL)
    async with AsyncSession(async_engine) as db:
        query_str = """
            SELECT id::text as id, user_id::text as user_id, title, description, location, price, house_type, amenities, photos, lat, lon,
            0.0 AS distance_km
            FROM properties
            WHERE status = 'APPROVED'
            ORDER BY id
        """
        result = await db.execute(text(query_str))
        listings = [dict(row) for row in result.mappings()]
        
        # Add map URLs and preview URLs
        for listing in listings:
            if listing.get("lat") is not None and listing.get("lon") is not None:
                listing["map_url"] = (
                    f"https://mapapi.gebeta.app/staticmap?center={listing['lat']},{listing['lon']}&zoom=14&size=600x300&apiKey={settings.GEBETA_API_KEY}"
                )
                listing["preview_url"] = f"/api/v1/map/preview?lat={listing['lat']}&lon={listing['lon']}&zoom=14"
            else:
                listing["map_url"] = None
                listing["preview_url"] = None
            
            # Fetch owner contact information
            user_id = listing.get("user_id")
            if user_id:
                owner_contact = await get_user_contact_info(user_id)
                listing["owner_contact"] = owner_contact
            else:
                listing["owner_contact"] = None
        
        # Cache for 1 hour
        await redis.setex(cache_key, 3600, json.dumps(listings, default=str))
        return listings