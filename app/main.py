"""
NYX FastAPI Main Application

Entry point for the NYX REST API providing access to autonomous agent capabilities.
"""

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
import logging
from datetime import datetime, timezone
from typing import Dict, Any
from contextlib import asynccontextmanager

from .core.exceptions import NYXAPIException, nyx_exception_handler
from .middleware.auth import APIKeyMiddleware
from database.connection import db_manager
from database.models import MotivationalTask, ThoughtTree, Agent
from sqlalchemy import update

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import routers
from .api.v1 import system, orchestrator, motivational, social
# Additional routers will be imported as they are created:
# from .api.v1 import tools, llm


async def cleanup_orphaned_resources():
    """
    Clean up orphaned resources from previous runs on startup.

    Marks all in-progress tasks, thought trees, and agents as cancelled/terminated
    since they cannot be resumed after a restart.
    """
    try:
        logger.info("Starting orphaned resource cleanup...")

        async with db_manager.get_async_session() as session:
            cleanup_timestamp = datetime.now(timezone.utc)

            # 1. Clean up MotivationalTasks
            result = await session.execute(
                update(MotivationalTask)
                .where(MotivationalTask.status.in_(['queued', 'spawned', 'active']))
                .values(
                    status='cancelled',
                    completed_at=cleanup_timestamp,
                    context=MotivationalTask.context.op('||')({
                        'cancelled_reason': 'startup_cleanup',
                        'cancelled_at': cleanup_timestamp.isoformat()
                    })
                )
            )
            tasks_cleaned = result.rowcount

            # 2. Clean up ThoughtTrees
            result = await session.execute(
                update(ThoughtTree)
                .where(ThoughtTree.status.in_(['pending', 'in_progress']))
                .values(
                    status='cancelled',
                    completed_at=cleanup_timestamp,
                    metadata_=ThoughtTree.metadata_.op('||')({
                        'cancelled_reason': 'startup_cleanup',
                        'cancelled_at': cleanup_timestamp.isoformat()
                    })
                )
            )
            trees_cleaned = result.rowcount

            # 3. Clean up Agents
            result = await session.execute(
                update(Agent)
                .where(Agent.status.in_(['spawned', 'active', 'waiting']))
                .values(
                    status='terminated',
                    completed_at=cleanup_timestamp,
                    state=Agent.state.op('||')({
                        'terminated_reason': 'startup_cleanup',
                        'terminated_at': cleanup_timestamp.isoformat()
                    })
                )
            )
            agents_cleaned = result.rowcount

            await session.commit()

            logger.info(
                f"Startup cleanup complete: "
                f"{tasks_cleaned} tasks, "
                f"{trees_cleaned} thought trees, "
                f"{agents_cleaned} agents marked as cancelled/terminated"
            )

    except Exception as e:
        logger.error(f"Error during startup cleanup: {e}", exc_info=True)
        # Don't fail startup if cleanup fails


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifespan handler for startup and shutdown events.

    Startup: Clean up orphaned resources from previous runs
    Shutdown: Currently no cleanup needed (engine stops via API)
    """
    # Startup
    await cleanup_orphaned_resources()

    yield

    # Shutdown
    logger.info("NYX API shutting down...")


app = FastAPI(
    lifespan=lifespan,
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
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:8080",
        "http://127.0.0.1:3000",
        "http://192.168.50.13:3000",
        "http://192.168.50.13:8000"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Add API Key authentication middleware
api_auth_middleware = APIKeyMiddleware()
app.middleware("http")(api_auth_middleware)

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
app.include_router(social.router, prefix="/api/v1/social", tags=["social"])

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