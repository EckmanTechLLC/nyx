from pydantic_settings import BaseSettings
from pydantic import Field, validator
from typing import Optional
import os

class Settings(BaseSettings):
    # Database Configuration
    database_url: str = Field(..., env="DATABASE_URL")
    
    # LLM API Configuration
    anthropic_api_key: str = Field(..., env="ANTHROPIC_API_KEY")
    
    # FastAPI Configuration
    debug: bool = Field(default=False, env="DEBUG")
    api_host: str = Field(default="0.0.0.0", env="API_HOST")
    api_port: int = Field(default=8000, env="API_PORT")
    
    # Logging Configuration
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_format: str = Field(default="json", env="LOG_FORMAT")
    
    # System Limits (defaults - can be overridden by database config)
    default_max_recursion_depth: int = Field(default=10, env="DEFAULT_MAX_RECURSION_DEPTH")
    default_max_concurrent_agents: int = Field(default=50, env="DEFAULT_MAX_CONCURRENT_AGENTS")
    default_retry_attempts: int = Field(default=3, env="DEFAULT_RETRY_ATTEMPTS")
    
    # Timeouts
    llm_timeout_seconds: int = Field(default=60, env="LLM_TIMEOUT_SECONDS")
    tool_timeout_seconds: int = Field(default=30, env="TOOL_TIMEOUT_SECONDS")
    
    class Config:
        env_file = ".env"
        case_sensitive = False
    
    @validator("database_url")
    def validate_database_url(cls, v):
        if not v.startswith("postgresql://"):
            raise ValueError("DATABASE_URL must be a PostgreSQL URL")
        return v
    
    @validator("log_level")
    def validate_log_level(cls, v):
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"LOG_LEVEL must be one of: {', '.join(valid_levels)}")
        return v.upper()
    
    @validator("anthropic_api_key")
    def validate_anthropic_api_key(cls, v):
        if v == "your_anthropic_api_key_here":
            raise ValueError("Please set a valid ANTHROPIC_API_KEY")
        return v
    
    @property
    def async_database_url(self) -> str:
        """Convert sync database URL to async version for SQLAlchemy"""
        return self.database_url.replace("postgresql://", "postgresql+asyncpg://")
    
    @property
    def is_production(self) -> bool:
        """Check if running in production mode"""
        return not self.debug

# Global settings instance
settings = Settings()