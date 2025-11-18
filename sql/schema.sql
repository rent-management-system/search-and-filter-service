CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS earthdistance CASCADE; -- Ensure earthdistance is created

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'propertystatus') THEN
        CREATE TYPE propertystatus AS ENUM ('PENDING', 'APPROVED', 'REJECTED');
    END IF;
END$$;

CREATE TABLE IF NOT EXISTS properties (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    location VARCHAR(255) NOT NULL,
    price NUMERIC(10, 2) NOT NULL,
    house_type VARCHAR(50), -- Added house_type
    amenities JSONB DEFAULT '[]'::jsonb,
    photos JSONB DEFAULT '[]'::jsonb,
    status propertystatus NOT NULL DEFAULT 'PENDING',
    lat FLOAT, -- Added lat
    lon FLOAT, -- Added lon
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    fts tsvector
);

-- Create a function to update the updated_at timestamp
CREATE OR REPLACE FUNCTION trigger_set_timestamp()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Drop the trigger if it exists to avoid errors on re-run
DROP TRIGGER IF EXISTS set_timestamp ON properties;

-- Create the trigger
CREATE TRIGGER set_timestamp
BEFORE UPDATE ON properties
FOR EACH ROW
EXECUTE PROCEDURE trigger_set_timestamp();

-- Indexes
CREATE INDEX IF NOT EXISTS idx_properties_user_id ON properties (user_id);
CREATE INDEX IF NOT EXISTS idx_properties_status ON properties (status);
CREATE INDEX IF NOT EXISTS idx_properties_location ON properties (location);
CREATE INDEX IF NOT EXISTS idx_properties_price ON properties (price);
-- Add index for geospatial queries, using lat/lon
CREATE INDEX IF NOT EXISTS idx_properties_lat_lon ON properties USING GIST(ll_to_earth(lat, lon));

-- Full-text search index
CREATE INDEX IF NOT EXISTS fts_idx ON properties USING gin(fts);

CREATE OR REPLACE FUNCTION update_fts_column() RETURNS trigger AS $$
BEGIN
  NEW.fts := to_tsvector('english', NEW.title || ' ' || NEW.description || ' ' || NEW.location || ' ' || COALESCE(NEW.house_type, ''));
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS update_fts ON properties;

CREATE TRIGGER update_fts
BEFORE INSERT OR UPDATE ON properties
FOR EACH ROW EXECUTE PROCEDURE update_fts_column();