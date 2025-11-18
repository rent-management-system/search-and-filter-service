from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://user:password@db:5432/rental_db"
    REDIS_URL: str = "redis://localhost:6379/0"
    JWT_SECRET: str = "your_jwt_secret"
    GEBETA_API_KEY: str = "your_gebeta_key"
    USER_MANAGEMENT_URL: str = "http://user-management:8000"
    NOTIFICATION_URL: str = "http://notification:8000"
    # Gebeta routing APIs
    ONM_API_BASE: str = "https://mapapi.gebeta.app/api/route/onm/"
    MATRIX_API_BASE: str = "https://mapapi.gebeta.app/api/route/matrix/"
    # Dataset path for predefined routes (source/destination coordinates)
    ROUTES_DATA_PATH: str = "data/routes.json"
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
