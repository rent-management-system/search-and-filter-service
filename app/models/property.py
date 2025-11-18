from sqlalchemy import Column, Integer, String, Float, DateTime, func, Enum, Text, Numeric
from sqlalchemy.dialects.postgresql import UUID, JSONB, TSVECTOR
# Import Base from the common models file
from app.models import Base

class Property(Base):
    __tablename__ = "properties" # Note: lowercase 'properties' to match the SQL schema
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.uuid_generate_v4())
    user_id = Column(UUID(as_uuid=True), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    location = Column(String(255), nullable=False)
    price = Column(Numeric(10, 2), nullable=False)
    house_type = Column(String(50)) # Added house_type
    bedrooms = Column(Integer) # Added bedrooms
    amenities = Column(JSONB, default=[]) # Corrected default
    photos = Column(JSONB, default=[]) # Corrected default
    status = Column(Enum('PENDING', 'APPROVED', 'REJECTED', name='propertystatus'), nullable=False, server_default='PENDING')
    lat = Column(Float) # Added lat
    lon = Column(Float) # Added lon
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    fts = Column(TSVECTOR) # Full-text search vector, managed by triggers in SQL

    # Note: fts column is managed by triggers in the SQL schema, so we don't need to define its update logic here.
    # The 'onupdate' for updated_at is also handled by a trigger.
