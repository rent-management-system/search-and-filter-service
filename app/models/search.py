from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from app.models import Base # Import Base from the common models file

class SavedSearch(Base):
    __tablename__ = "SavedSearches"
    id = Column(Integer, primary_key=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("Users.id", ondelete="CASCADE"), nullable=False) # Changed to UUID
    location = Column(String(255))
    min_price = Column(Float, nullable=True)
    max_price = Column(Float, nullable=True)
    # house_type removed as it's a property attribute, not a saved search attribute
    amenities = Column(JSONB, nullable=True) # Changed to JSONB
    bedrooms = Column(Integer, nullable=True)
    # max_distance_km removed as it's a search parameter, not a saved search attribute
    created_at = Column(DateTime(timezone=True), server_default=func.now())