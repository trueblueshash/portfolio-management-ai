from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    APP_NAME: str = "Portfolio Intelligence Tracker"
    PROJECT_NAME: str = "Portfolio Intelligence API"
    API_V1_PREFIX: str = "/api"
    DATABASE_URL: str
    MIGRATION_DATABASE_URL: str
    REDIS_URL: str = "redis://localhost:6379/0"
    OPENROUTER_API_KEY: str
    GOOGLE_SERVICE_ACCOUNT_JSON: str
    SECRET_KEY: str = "not-used-yet"
    APP_API_KEY: str = "lightspeed2026"
    DEBUG: bool = True
    CORS_ORIGINS: list = ["http://localhost:3000", "http://localhost:5173", "http://localhost:8000"]
    
    class Config:
        env_file = ".env"
        extra = "ignore"

@lru_cache()
def get_settings():
    return Settings()

settings = Settings()