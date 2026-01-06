from pydantic_settings import BaseSettings
from typing import List
import os


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql://justabill:justabill@localhost:5432/justabill"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # Congress API
    CONGRESS_API_KEY: str = ""
    
    # LLM Configuration
    LLM_PROVIDER: str = "openai"  # openai, anthropic, or local
    LLM_MODEL: str = "gpt-4"
    LLM_API_KEY: str = ""
    LLM_BASE_URL: str = ""  # For local models
    
    # Application
    SECRET_KEY: str = "your-secret-key-change-in-production"
    BACKEND_CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8000"]
    
    # Server
    BACKEND_HOST: str = "0.0.0.0"
    BACKEND_PORT: int = 8000
    
    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"
    
    # Rate Limiting
    RATE_LIMIT_REQUESTS_PER_MINUTE: int = 60
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"  # Ignore extra environment variables


settings = Settings()
