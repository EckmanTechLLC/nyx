"""
NYX FastAPI Main Application

Entry point for the NYX REST API providing access to autonomous agent capabilities.
"""

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
import logging
from datetime import datetime
from typing import Dict, Any

from .core.exceptions import NYXAPIException, nyx_exception_handler

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import routers
from .api.v1 import system, orchestrator, motivational
# Additional routers will be imported as they are created:
# from .api.v1 import tools, llm

app = FastAPI(
    title="NYX Autonomous Agent API",
    description="""
    REST API for NYX autonomous orchestration system.
    
    NYX is a fully autonomous AI agent system capable of self-directed operation,
    goal formation, and continuous task execution without human intervention.
    
    ## Features
    
    * **Workflow Orchestration**: Execute complex multi-agent workflows
    * **Autonomous Operation**: Start/stop autonomous motivational engine
    * **System Monitoring**: Real-time status and performance metrics
    * **Tool Execution**: Secure execution of system tools
    * **LLM Integration**: Claude API with native prompt caching
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    contact={
        "name": "NYX Development Team",
        "url": "https://github.com/your-org/nyx",
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT",
    }
)

# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8080"],  # Configure for production
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Exception handlers
app.add_exception_handler(NYXAPIException, nyx_exception_handler)

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle request validation errors with detailed responses"""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "Validation Error",
            "detail": str(exc),
            "errors": exc.errors(),
            "timestamp": datetime.utcnow().isoformat()
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions with structured error responses"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal Server Error", 
            "detail": "An unexpected error occurred",
            "timestamp": datetime.utcnow().isoformat()
        }
    )

# Health check endpoint
@app.get("/health", tags=["system"])
async def health_check() -> Dict[str, Any]:
    """
    Health check endpoint for load balancers and monitoring systems.
    
    Returns basic system health status and version information.
    """
    return {
        "status": "healthy",
        "version": "1.0.0",
        "service": "nyx-api",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/", tags=["system"])
async def root():
    """
    Root endpoint providing basic API information.
    """
    return {
        "message": "NYX Autonomous Agent API",
        "version": "1.0.0", 
        "docs": "/docs",
        "health": "/health"
    }

# Include routers
app.include_router(system.router, prefix="/api/v1/system", tags=["system"])
app.include_router(orchestrator.router, prefix="/api/v1/orchestrator", tags=["orchestrator"])
app.include_router(motivational.router, prefix="/api/v1/motivational", tags=["motivational"])

# Additional routers will be included as they are created:
# app.include_router(tools.router, prefix="/api/v1/tools", tags=["tools"])
# app.include_router(llm.router, prefix="/api/v1/llm", tags=["llm"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )