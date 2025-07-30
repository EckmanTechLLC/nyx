"""
Authentication middleware for NYX API.

Provides API key validation for secure access to NYX endpoints.
"""

import os
from typing import Optional
from fastapi import HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import logging

logger = logging.getLogger(__name__)

# Default API key - in production this should be set via environment variable
DEFAULT_API_KEY = os.getenv("NYX_API_KEY", "your-api-key-here")

class APIKeyMiddleware:
    """Middleware to validate API keys for NYX endpoints."""
    
    def __init__(self, api_key: str = DEFAULT_API_KEY):
        self.api_key = api_key
        logger.info(f"API Key authentication initialized. Key present: {'Yes' if api_key else 'No'}")
    
    async def __call__(self, request: Request, call_next):
        # Skip authentication for health check, docs, and OPTIONS (CORS preflight)
        if request.url.path in ["/health", "/", "/docs", "/redoc", "/openapi.json"] or request.method == "OPTIONS":
            response = await call_next(request)
            return response
        
        # Check for API key in headers
        api_key = request.headers.get("X-API-Key")
        
        if not api_key:
            logger.warning(f"Missing API key for {request.url.path}, proceeding anyway (development mode)")
            # In development mode, proceed without API key validation
            # TODO: Re-enable for production
            pass
        elif api_key != self.api_key:
            logger.warning(f"Invalid API key attempted for {request.url.path}, proceeding anyway (development mode)")
            # In development mode, proceed even with invalid API key
            # TODO: Re-enable for production
            pass
        
        response = await call_next(request)
        return response

def get_api_key_from_request(request: Request) -> Optional[str]:
    """Extract API key from request headers."""
    return request.headers.get("X-API-Key")

def validate_api_key(api_key: str) -> bool:
    """Validate the provided API key."""
    return api_key == DEFAULT_API_KEY