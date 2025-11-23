from fastapi import APIRouter, Depends, HTTPException, Response, status
from app.schemas.search import SearchQuery, SearchResponse, SavedSearchRequest
from app.services.search import search_properties, save_search, get_property_by_id, get_all_approved_properties
from app.services.gebeta import geocode, get_map_tile
from app.dependencies.auth import get_current_user
from app.config import settings
from structlog import get_logger
from fastapi_limiter.depends import RateLimiter
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy import insert
from typing import List

logger = get_logger()
router = APIRouter(prefix="/api/v1", tags=["search"])

@router.get("/search", response_model=List[SearchResponse], dependencies=[Depends(RateLimiter(times=5, seconds=60))])
async def search(query: SearchQuery = Depends(), user: dict = Depends(get_current_user)):
    if user.get("role").lower() != "tenant":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only Tenants can search")

    logger.info(
        "Received search request",
        user_id=user.get("id"),
        query_params=query.dict()
    )
    
    if query.min_price is not None and query.max_price is not None and query.min_price > query.max_price:
        logger.warning("Invalid price range", min_price=query.min_price, max_price=query.max_price)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="min_price cannot be greater than max_price")

    try:
        results = await search_properties(
            location=query.location,
            min_price=query.min_price,
            max_price=query.max_price,
            house_type=query.house_type,
            amenities=query.amenities,
            bedrooms=query.bedrooms,
            use_distance=query.use_distance,
            max_distance_km=query.max_distance_km,
            sort_by=query.sort_by
        )
        logger.info("Search completed", user_id=user.get("id"), query=query.dict(), result_count=len(results))
        return results
    except Exception as e:
        logger.error("Search failed", query=query.dict(), error=str(e), exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Search failed")

@router.get("/property/{id}", response_model=SearchResponse, dependencies=[Depends(RateLimiter(times=10, seconds=60))])
async def get_property(id: str, user: dict = Depends(get_current_user)):
    try:
        item = await get_property_by_id(id)
        if not item:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Property not found")
        return item
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Get property failed", id=id, error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to fetch property")

@router.post("/saved-searches", response_model=dict, dependencies=[Depends(RateLimiter(times=5, seconds=60))])
async def save_search_endpoint(request: SavedSearchRequest, user: dict = Depends(get_current_user)):
    if user.get("role").lower() != "tenant":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only Tenants can save searches")
    try:
        search_id = await save_search(user["id"], request)
        logger.info("Saved search", user_id=user["id"], search_id=search_id)
        return {"id": search_id, "message": "Search saved"}
    except Exception as e:
        logger.error("Save search failed", error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to save search")

@router.get("/map/tile/{z}/{x}/{y}", response_class=Response)
async def get_tile_endpoint(z: int, x: int, y: int):
    try:
        tile_content = await get_map_tile(z, x, y)
        return Response(content=tile_content, media_type="image/png")
    except Exception as e:
        logger.error("Map tile fetch failed", z=z, x=x, y=y, error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to fetch map tile")

@router.get("/geocode/{query}", response_model=dict, dependencies=[Depends(RateLimiter(times=5, seconds=60))])
async def geocode_location_endpoint(query: str):
    try:
        result = await geocode(query)
        logger.info("Geocode successful", query=query, result=result)
        return result
    except ValueError as e:
        logger.warning("Geocode failed for query", query=query, error=str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Geocoding failed: {str(e)}")
    except Exception as e:
        logger.error("Geocode failed unexpectedly", query=query, error=str(e), exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Geocoding failed unexpectedly")

@router.get("/properties/approved", response_model=List[SearchResponse], dependencies=[Depends(RateLimiter(times=10, seconds=60))])
async def list_all_approved_properties(user: dict = Depends(get_current_user)):
    """
    Get all approved properties from the database without any filters.
    Returns all properties with status = 'APPROVED'.
    """
    try:
        results = await get_all_approved_properties()
        logger.info("Retrieved all approved properties", user_id=user.get("id"), result_count=len(results))
        return results
    except Exception as e:
        logger.error("Failed to retrieve all approved properties", error=str(e), exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve approved properties")
