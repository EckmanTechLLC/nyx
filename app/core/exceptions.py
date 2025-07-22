"""
Custom exceptions and exception handlers for NYX FastAPI application.
"""

from fastapi import HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.requests import Request
from typing import Dict, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class NYXAPIException(HTTPException):
    """Base exception for NYX API errors"""
    
    def __init__(
        self,
        status_code: int,
        detail: str,
        error_code: str = None,
        metadata: Dict[str, Any] = None
    ):
        super().__init__(status_code=status_code, detail=detail)
        self.error_code = error_code or "GENERIC_ERROR"
        self.metadata = metadata or {}

class WorkflowExecutionError(NYXAPIException):
    """Exception for workflow execution failures"""
    
    def __init__(self, detail: str, metadata: Dict[str, Any] = None):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail,
            error_code="WORKFLOW_EXECUTION_ERROR",
            metadata=metadata
        )

class MotivationalEngineError(NYXAPIException):
    """Exception for motivational engine operations"""
    
    def __init__(self, detail: str, metadata: Dict[str, Any] = None):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail,
            error_code="MOTIVATIONAL_ENGINE_ERROR",
            metadata=metadata
        )

class ToolExecutionError(NYXAPIException):
    """Exception for tool execution failures"""
    
    def __init__(self, detail: str, metadata: Dict[str, Any] = None):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
            error_code="TOOL_EXECUTION_ERROR",
            metadata=metadata
        )

class LLMIntegrationError(NYXAPIException):
    """Exception for LLM integration failures"""
    
    def __init__(self, detail: str, metadata: Dict[str, Any] = None):
        super().__init__(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=detail,
            error_code="LLM_INTEGRATION_ERROR",
            metadata=metadata
        )

class DatabaseError(NYXAPIException):
    """Exception for database operation failures"""
    
    def __init__(self, detail: str = "Database operation failed"):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail,
            error_code="DATABASE_ERROR"
        )

async def nyx_exception_handler(request: Request, exc: NYXAPIException) -> JSONResponse:
    """
    Handle NYX-specific exceptions with structured error responses.
    
    Args:
        request: FastAPI request object
        exc: NYX exception instance
        
    Returns:
        JSONResponse: Structured error response
    """
    logger.error(
        f"NYX API Exception: {exc.error_code} - {exc.detail}",
        extra={
            "error_code": exc.error_code,
            "status_code": exc.status_code,
            "metadata": exc.metadata,
            "url": str(request.url),
            "method": request.method
        }
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": True,
            "error_code": exc.error_code,
            "detail": exc.detail,
            "metadata": exc.metadata,
            "timestamp": datetime.utcnow().isoformat(),
            "path": str(request.url.path)
        }
    )

def create_exception_handler(exc_class: Exception):
    """
    Create a generic exception handler for any exception type.
    
    Args:
        exc_class: Exception class to handle
        
    Returns:
        Exception handler function
    """
    async def handler(request: Request, exc: Exception):
        logger.error(
            f"Unhandled {exc_class.__name__}: {str(exc)}",
            exc_info=True,
            extra={
                "url": str(request.url),
                "method": request.method
            }
        )
        
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": True,
                "error_code": "INTERNAL_SERVER_ERROR",
                "detail": "An unexpected error occurred",
                "timestamp": datetime.utcnow().isoformat(),
                "path": str(request.url.path)
            }
        )
    
    return handler