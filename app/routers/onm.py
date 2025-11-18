from typing import List, Tuple

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi_limiter.depends import RateLimiter
from structlog import get_logger

from app.schemas.onm import ONMRouteRequest, NearestRequest, NearestResponse, DestinationOut
from app.services.onm import (
    resolve_destinations_by_name,
    onm_route,
    matrix,
    get_destinations_from_dataset,
)

logger = get_logger()
router = APIRouter(prefix="/api/v1/onm", tags=["onm"])


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    from math import radians, sin, cos, asin, sqrt
    R = 6371.0
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    return R * c


@router.post("/route", dependencies=[Depends(RateLimiter(times=10, seconds=60))])
async def compute_route(req: ONMRouteRequest):
    # Resolve destinations: use provided lat/lon or lookup by name in dataset
    waypoints: List[Tuple[float, float]] = []
    for d in req.destinations:
        if d.lat is not None and d.lon is not None:
            waypoints.append((float(d.lat), float(d.lon)))
        elif d.name:
            resolved = resolve_destinations_by_name([d.name])
            if not resolved:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Destination '{d.name}' not found")
            waypoints.extend(resolved)
        else:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Each destination must include a name or lat/lon")

    try:
        data = await onm_route(req.origin_lat, req.origin_lon, waypoints)
        logger.info("ONM route computed", origin=(req.origin_lat, req.origin_lon), waypoint_count=len(waypoints))
        return data
    except Exception as e:
        logger.error("ONM route failed", error=str(e))
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Failed to compute route via Gebeta ONM")


@router.post("/nearest", response_model=NearestResponse, dependencies=[Depends(RateLimiter(times=10, seconds=60))])
async def nearest(req: NearestRequest):
    dataset = get_destinations_from_dataset()

    # Try Matrix API first (best for travel distance/time). On error, fallback to haversine.
    coords: List[Tuple[float, float]] = [(req.origin_lat, req.origin_lon)] + [
        (float(x["dest_lat"]), float(x["dest_lon"])) for x in dataset
    ]

    ranking: List[Tuple[int, float]] = []  # (index in dataset, distance_km)
    used_matrix = False
    try:
        resp = await matrix(coords[: min(len(coords), 10)])  # respect <=10 limit
        # Matrix schema can vary; attempt to read distances matrix (first row is origin to others)
        # Expect something like {"distances": [[0, d1, d2, ...]]} in kilometers or meters.
        distances = None
        if isinstance(resp, dict):
            distances = resp.get("distances") or resp.get("distance") or resp.get("matrix")
        if distances and isinstance(distances, list) and distances:
            row = distances[0]
            # pair dataset index with distance value starting from 1 (since 0 is origin)
            for i, d in enumerate(row[1:], start=0):
                try:
                    dk = float(d) / 1000.0 if float(d) > 1000 else float(d)  # guess meters->km
                except Exception:
                    dk = float(d)
                ranking.append((i, dk))
            used_matrix = True
    except Exception:
        used_matrix = False

    if not used_matrix:
        # Haversine fallback for all
        for i, item in enumerate(dataset):
            dk = _haversine_km(req.origin_lat, req.origin_lon, float(item["dest_lat"]), float(item["dest_lon"]))
            ranking.append((i, dk))

    ranking.sort(key=lambda x: x[1])
    top = ranking[: req.limit]

    results: List[DestinationOut] = []
    for idx, dk in top:
        item = dataset[idx]
        results.append(
            DestinationOut(
                source=item["source"],
                destination=item["destination"],
                kilometer=float(item["kilometer"]),
                price=float(item["price"]),
                dest_lat=float(item["dest_lat"]),
                dest_lon=float(item["dest_lon"]),
                straight_distance_km=dk,
            )
        )

    return NearestResponse(origin=(req.origin_lat, req.origin_lon), results=results)
