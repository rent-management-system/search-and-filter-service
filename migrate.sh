#!/bin/bash
set -e

# Load environment variables safely
if [ -f .env ]; then
    set -a
    source .env
    set +a
fi

# Check if DATABASE_URL is set
if [ -z "$DATABASE_URL" ]; then
    echo "Error: DATABASE_URL is not set in .env file."
    exit 1
fi

# Extract DB connection details for psql from DATABASE_URL
# Assuming DATABASE_URL is in the format: postgresql+asyncpg://user:password@host:port/dbname
DB_USER=$(echo $DATABASE_URL | sed -r "s/postgresql\+asyncpg:\/\/(.*):.*@.*/\1/")
DB_PASSWORD=$(echo $DATABASE_URL | sed -r "s/postgresql\+asyncpg:\/\/.*:(.*)@.*/\1/")
DB_HOST=$(echo $DATABASE_URL | sed -r "s/postgresql\+asyncpg:\/\/.*@(.*):.*/\1/")
DB_PORT=$(echo $DATABASE_URL | sed -r "s/postgresql\+asyncpg:\/\/.*:.*@.*:(.*)\/.*/\1/")
DB_NAME=$(echo $DATABASE_URL | sed -r "s/postgresql\+asyncpg:\/\/.*@.*\/([^?]*).*/\1/")

export PGPASSWORD=$DB_PASSWORD

if [ -f sql/schema.sql ]; then
    echo "Applying schema.sql..."
    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -f sql/schema.sql
else
    echo "sql/schema.sql not found, skipping."
fi

echo "Running Alembic migrations..."
# Explicitly call alembic from the virtual environment's bin directory
"/home/dagi/Desktop/flash files one documentes and desktop /prop- search/search_filters/.venv/bin/alembic" upgrade heads

# Apply seed data only if seed.sql exists and after migrations
if [ -f sql/seed.sql ]; then
    echo "Applying seed.sql..."
    # Extract DB connection details for psql from DATABASE_URL
    # Assuming DATABASE_URL is in the format: postgresql+asyncpg://user:password@host:port/dbname
    DB_USER=$(echo $DATABASE_URL | sed -r "s/postgresql\+asyncpg:\/\/(.*):.*@.*/\1/")
    DB_PASSWORD=$(echo $DATABASE_URL | sed -r "s/postgresql\+asyncpg:\/\/.*:(.*)@.*/\1/")
    DB_HOST=$(echo $DATABASE_URL | sed -r "s/postgresql\+asyncpg:\/\/.*@(.*):.*/\1/")
    DB_PORT=$(echo $DATABASE_URL | sed -r "s/postgresql\+asyncpg:\/\/.*:.*@.*:(.*)\/.*/\1/")
    DB_NAME=$(echo $DATABASE_URL | sed -r "s/postgresql\+asyncpg:\/\/.*@.*\/([^?]*).*/\1/")

    export PGPASSWORD=$DB_PASSWORD

    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -f sql/seed.sql
else
    echo "sql/seed.sql not found, skipping."
fi

echo "Database migration and seeding complete."