"""
Configuration management for FastAPI application.

Provides access to NYX settings and FastAPI-specific configuration.
"""

from functools import lru_cache
from typing import List, Optional
from pydantic import BaseModel

# Import existing NYX settings
from config.settings import settings as nyx_settings

class FastAPISettings(BaseModel):
    """FastAPI-specific configuration settings"""
    
    # API Configuration
    api_title: str = "NYX Autonomous Agent API"
    api_version: str = "1.0.0"
    api_description: str = "REST API for NYX autonomous orchestration system"
    
    # Server Configuration
    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = False
    
    # CORS Configuration
    allowed_origins: List[str] = [
        "http://localhost:3000",
        "http://localhost:8080",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8080"
    ]
    
    # Security
    secret_key: str = "your-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expiration_minutes: int = 30
    
    # Rate Limiting
    rate_limit_requests: int = 100
    rate_limit_window_minutes: int = 1
    
    # Logging
    log_level: str = "INFO"
    
    class Config:
        env_prefix = "FASTAPI_"

@lru_cache()
def get_settings() -> nyx_settings.__class__:
    """Get NYX settings with caching"""
    return nyx_settings

@lru_cache()
def get_fastapi_settings() -> FastAPISettings:
    """Get FastAPI-specific settings with caching"""
    return FastAPISettings()

# Convenience access
settings = get_settings()
fastapi_settings = get_fastapi_settings()