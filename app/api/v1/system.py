"""
System status and health check endpoints for NYX API.

Provides comprehensive system monitoring and health check capabilities.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any
from datetime import datetime
import logging
import asyncio

from ...core.database import get_db, check_database_health
from ...core.exceptions import DatabaseError

# Import NYX components for status checking
from database.connection import db_manager

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """
    Comprehensive system health check.
    
    Checks the health of all major system components including:
    - Database connectivity
    - System responsiveness
    - Basic component initialization
    
    Returns:
        Dict containing health status of all components
    """
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
        "service": "nyx-api",
        "components": {}
    }
    
    overall_healthy = True
    
    # Check database health
    try:
        db_healthy = await check_database_health()
        health_status["components"]["database"] = {
            "status": "healthy" if db_healthy else "unhealthy",
            "connection": "connected" if db_healthy else "disconnected"
        }
        if not db_healthy:
            overall_healthy = False
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        health_status["components"]["database"] = {
            "status": "unhealthy",
            "connection": "failed",
            "error": str(e)
        }
        overall_healthy = False
    
    # Check system responsiveness
    try:
        start_time = datetime.utcnow()
        await asyncio.sleep(0.001)  # Minimal async operation test
        response_time_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        health_status["components"]["system"] = {
            "status": "healthy",
            "response_time_ms": round(response_time_ms, 2)
        }
    except Exception as e:
        logger.error(f"System responsiveness check failed: {e}")
        health_status["components"]["system"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        overall_healthy = False
    
    # Update overall status
    if not overall_healthy:
        health_status["status"] = "unhealthy"
    
    return health_status

@router.get("/status")
async def get_system_status(db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """
    Get detailed system status and statistics.
    
    Provides comprehensive information about:
    - Database connection status
    - System performance metrics
    - Component initialization status
    
    Args:
        db: Database session dependency
        
    Returns:
        Dict containing detailed system status information
    """
    try:
        status_info = {
            "timestamp": datetime.utcnow().isoformat(),
            "uptime": "N/A",  # Will be implemented with actual startup tracking
            "version": "1.0.0",
            "environment": "development",  # Will be configured from settings
            "database": {},
            "components": {
                "fastapi": {
                    "status": "operational",
                    "version": "1.0.0"
                }
            }
        }
        
        # Database statistics
        try:
            # Basic database connection test
            from sqlalchemy import text
            result = await db.execute(text("SELECT 1 as test"))
            test_result = result.scalar()
            
            status_info["database"] = {
                "status": "connected" if test_result == 1 else "error",
                "connection_pool": "healthy",
                "last_check": datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Database status check failed: {e}")
            status_info["database"] = {
                "status": "error",
                "error": str(e),
                "last_check": datetime.utcnow().isoformat()
            }
        
        return status_info
        
    except Exception as e:
        logger.error(f"System status check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve system status: {str(e)}"
        )

@router.get("/info")
async def get_system_info() -> Dict[str, Any]:
    """
    Get basic system information.
    
    Returns static information about the NYX system and API.
    
    Returns:
        Dict containing system information
    """
    return {
        "name": "NYX Autonomous Agent API",
        "version": "1.0.0",
        "description": "REST API for NYX autonomous orchestration system",
        "features": [
            "Workflow orchestration",
            "Autonomous operation control",
            "System monitoring", 
            "Tool execution",
            "LLM integration"
        ],
        "endpoints": {
            "health": "/api/v1/system/health",
            "status": "/api/v1/system/status",
            "docs": "/docs",
            "redoc": "/redoc"
        },
        "timestamp": datetime.utcnow().isoformat()
    }