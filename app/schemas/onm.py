from typing import List, Optional
from pydantic import BaseModel, Field, confloat


class DestRef(BaseModel):
    name: Optional[str] = Field(None, description="Destination name to lookup from dataset")
    lat: Optional[confloat(ge=-90, le=90)] = None
    lon: Optional[confloat(ge=-180, le=180)] = None


class ONMRouteRequest(BaseModel):
    origin_lat: confloat(ge=-90, le=90)
    origin_lon: confloat(ge=-180, le=180)
    destinations: List[DestRef] = Field(..., description="Up to 10 waypoints by name or lat/lon")


class NearestRequest(BaseModel):
    origin_lat: confloat(ge=-90, le=90)
    origin_lon: confloat(ge=-180, le=180)
    limit: int = Field(5, ge=1, le=10, description="Max results (<=10)")


class DestinationOut(BaseModel):
    source: str
    destination: str
    kilometer: float
    price: float
    dest_lat: float
    dest_lon: float
    straight_distance_km: float


class NearestResponse(BaseModel):
    origin: tuple
    results: List[DestinationOut]
