from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum

class SortByEnum(str, Enum):
    distance = "distance"
    price = "price"

class SearchQuery(BaseModel):
    location: Optional[str] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    house_type: Optional[str] = None
    amenities: Optional[List[str]] = None
    bedrooms: Optional[int] = None
    max_distance_km: Optional[float] = Field(None, description="Maximum distance in kilometers from the geocoded location.")
    use_distance: Optional[bool] = Field(True, description="If false, disables distance scoping (use for price-only or other filters)")
    sort_by: Optional[SortByEnum] = Field(SortByEnum.distance, description="Field to sort results by.")

    class Config:
        json_schema_extra = {
            "example": {
                "location": "ቦሌ",
                "min_price": 1000.0,
                "max_price": 2000.0,
                "house_type": "apartment",
                "amenities": ["wifi", "parking"],
                "bedrooms": 2,
                "max_distance_km": 5.0,
                "use_distance": True,
                "sort_by": "distance"
            }
        }

class SearchResponse(BaseModel):
    id: str
    title: str
    description: str # Added description back as it was in the original schema
    location: str
    price: float
    house_type: str
    amenities: List[str]
    lat: float
    lon: float
    distance_km: float # Added distance_km
    map_url: str
    preview_url: str

class SavedSearchRequest(BaseModel):
    location: Optional[str] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    house_type: Optional[str] = None
    amenities: Optional[List[str]] = None
    max_distance_km: Optional[float] = None
