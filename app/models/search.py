from sqlalchemy import Column, Integer, String, Float, DateTime, ARRAY
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.models import Base # Import Base from the common models file

class SavedSearch(Base):
    __tablename__ = "SavedSearches"
    id = Column(Integer, primary_key=True)
    location = Column(String(255), nullable=True)
    min_price = Column(Float, nullable=True)
    max_price = Column(Float, nullable=True)
    house_type = Column(String(50), nullable=True)
    amenities = Column(ARRAY(String), nullable=True)
    bedrooms = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=False), server_default=func.current_timestamp())
    max_distance_km = Column(Float, nullable=True)
    user_id = Column(UUID(as_uuid=True), nullable=True)  # No FK constraint - users table is in another service