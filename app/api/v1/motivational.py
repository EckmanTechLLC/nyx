"""
Motivational system API endpoints for autonomous operation control.

Provides REST API access to NYX's autonomous motivational model capabilities.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, Optional, List
from datetime import datetime
from pydantic import BaseModel, Field

from ...core.database import get_db
from ...core.exceptions import MotivationalEngineError

# Import verified NYX motivational components
from core.motivation.engine import MotivationalModelEngine
from core.motivation.states import MotivationalStateManager
from core.motivation.orchestrator_integration import (
    MotivationalOrchestratorIntegration, 
    create_integrated_motivational_system
)

logger = __import__('logging').getLogger(__name__)

router = APIRouter()

# Global instances for engine management (in production, use dependency injection)
_engine_instance = None
_integration_instance = None

# Request/Response models
class EngineConfig(BaseModel):
    """Configuration for starting the motivational engine"""
    evaluation_interval: float = Field(
        default=30.0,
        description="Evaluation interval in seconds",
        ge=1.0,
        le=300.0
    )
    max_concurrent_tasks: int = Field(
        default=3,
        description="Maximum concurrent motivated tasks",
        ge=1,
        le=10
    )
    min_arbitration_threshold: float = Field(
        default=0.3,
        description="Minimum arbitration threshold for task generation",
        ge=0.0,
        le=1.0
    )
    safety_enabled: bool = Field(
        default=True,
        description="Enable safety constraints"
    )
    test_mode: bool = Field(
        default=False,
        description="Enable test mode with shorter cooldowns"
    )

class EngineStatusResponse(BaseModel):
    """Response model for engine status"""
    running: bool = Field(..., description="Whether engine is currently running")
    evaluation_interval: float = Field(..., description="Current evaluation interval in seconds")
    max_concurrent_tasks: int = Field(..., description="Maximum concurrent tasks")
    min_arbitration_threshold: float = Field(..., description="Minimum arbitration threshold")
    safety_enabled: bool = Field(..., description="Safety constraints enabled")
    timestamp: str = Field(..., description="Status check timestamp")

class MotivationBoostRequest(BaseModel):
    """Request model for boosting motivation"""
    boost_amount: float = Field(
        ...,
        description="Amount to boost motivation",
        ge=0.0,
        le=1.0
    )
    reason: Optional[str] = Field(
        default=None,
        description="Reason for motivation boost"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata"
    )

@router.post("/engine/start")
async def start_engine(config: Optional[EngineConfig] = None):
    """
    Start the autonomous motivational engine.
    
    Initializes and starts the motivational model daemon that enables
    autonomous task generation based on internal motivational states.
    
    Args:
        config: Optional engine configuration parameters
        
    Returns:
        Dict containing startup status and engine information
        
    Raises:
        HTTPException: If engine fails to start
    """
    global _engine_instance, _integration_instance
    
    try:
        if _engine_instance and _engine_instance.get_status()['running']:
            return {
                "message": "Motivational engine already running",
                "status": "running",
                "timestamp": datetime.utcnow().isoformat()
            }
        
        if config:
            # Create new engine with custom configuration
            logger.info(f"Starting motivational engine with custom config: interval={config.evaluation_interval}s")
            
            _engine_instance = MotivationalModelEngine(
                evaluation_interval=config.evaluation_interval,
                max_concurrent_motivated_tasks=config.max_concurrent_tasks,
                min_arbitration_threshold=config.min_arbitration_threshold,
                safety_enabled=config.safety_enabled,
                test_mode=config.test_mode
            )
            
            await _engine_instance.start()
            
            # Create integration manually
            _integration_instance = MotivationalOrchestratorIntegration(_engine_instance)
            await _integration_instance.start_integration()
            
        else:
            # Use default configuration with verified create_integrated_motivational_system
            logger.info("Starting motivational engine with default configuration")
            
            _engine_instance, _integration_instance = await create_integrated_motivational_system(
                start_engine=True,
                start_integration=True
            )
        
        # Verify engine is running using verified get_status method
        engine_status = _engine_instance.get_status()
        
        return {
            "message": "Motivational engine started successfully",
            "status": "running",
            "config": {
                "evaluation_interval": engine_status['evaluation_interval'],
                "max_concurrent_tasks": engine_status['max_concurrent_tasks'],
                "min_arbitration_threshold": engine_status['min_arbitration_threshold'],
                "safety_enabled": engine_status['safety_enabled']
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to start motivational engine: {e}", exc_info=True)
        raise MotivationalEngineError(
            detail=f"Failed to start engine: {str(e)}",
            metadata={
                "error_type": type(e).__name__,
                "timestamp": datetime.utcnow().isoformat()
            }
        )

@router.post("/engine/stop")
async def stop_engine():
    """
    Stop the autonomous motivational engine.
    
    Gracefully shuts down the motivational model daemon and integration.
    
    Returns:
        Dict containing shutdown status
        
    Raises:
        HTTPException: If engine is not running or fails to stop
    """
    global _engine_instance, _integration_instance
    
    if not _engine_instance:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Motivational engine not initialized"
        )
    
    try:
        # Stop integration first, then engine using verified methods
        if _integration_instance:
            await _integration_instance.stop_integration()
            
        await _engine_instance.stop()
        
        return {
            "message": "Motivational engine stopped successfully",
            "status": "stopped",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to stop motivational engine: {e}", exc_info=True)
        raise MotivationalEngineError(
            detail=f"Failed to stop engine: {str(e)}",
            metadata={
                "error_type": type(e).__name__,
                "timestamp": datetime.utcnow().isoformat()
            }
        )

@router.put("/engine/config")
async def update_engine_config(config: EngineConfig):
    """
    Update the running engine's configuration.
    
    Updates the configuration of the currently running motivational engine.
    If the engine is not running, returns an error.
    
    Args:
        config: New engine configuration parameters
        
    Returns:
        Dict containing updated configuration status
        
    Raises:
        HTTPException: If engine is not running or update fails
    """
    global _engine_instance
    
    if not _engine_instance:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Engine not initialized. Start the engine first."
        )
    
    if not _engine_instance.get_status()['running']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Engine not running. Start the engine first."
        )
    
    try:
        # Update the engine configuration
        _engine_instance.update_config({
            'evaluation_interval': config.evaluation_interval,
            'max_concurrent_tasks': config.max_concurrent_tasks,
            'min_arbitration_threshold': config.min_arbitration_threshold,
            'safety_enabled': config.safety_enabled,
            'test_mode': config.test_mode
        })
        
        # Get updated status to confirm changes
        updated_status = _engine_instance.get_status()
        
        return {
            "message": "Engine configuration updated successfully",
            "config": {
                "evaluation_interval": updated_status['evaluation_interval'],
                "max_concurrent_tasks": updated_status['max_concurrent_tasks'],
                "min_arbitration_threshold": updated_status['min_arbitration_threshold'],
                "safety_enabled": updated_status['safety_enabled']
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to update engine configuration: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update engine configuration: {str(e)}"
        )

@router.get("/engine/status", response_model=EngineStatusResponse)
async def get_engine_status():
    """
    Get current status of the motivational engine.
    
    Returns detailed information about the engine's operational state
    using the verified get_status method.
    
    Returns:
        EngineStatusResponse: Current engine status and configuration
    """
    global _engine_instance
    
    if not _engine_instance:
        return EngineStatusResponse(
            running=False,
            evaluation_interval=30.0,
            max_concurrent_tasks=3,
            min_arbitration_threshold=0.3,
            safety_enabled=True,
            timestamp=datetime.utcnow().isoformat()
        )
    
    # Use verified get_status method from engine.py line 377
    status = _engine_instance.get_status()
    
    return EngineStatusResponse(
        running=status['running'],
        evaluation_interval=status['evaluation_interval'],
        max_concurrent_tasks=status['max_concurrent_tasks'],
        min_arbitration_threshold=status['min_arbitration_threshold'],
        safety_enabled=status['safety_enabled'],
        timestamp=datetime.utcnow().isoformat()
    )

@router.get("/states")
async def get_motivational_states(db: AsyncSession = Depends(get_db)):
    """
    Get all current motivational states.
    
    Returns comprehensive information about all active motivational states
    including urgency, satisfaction, and arbitration scores.
    
    Args:
        db: Database session
        
    Returns:
        Dict containing motivational states summary
    """
    try:
        state_manager = MotivationalStateManager()
        
        # Use verified get_motivation_summary method
        summary = await state_manager.get_motivation_summary(db)
        
        # Add timestamp and additional metadata
        result = {
            **summary,
            "timestamp": datetime.utcnow().isoformat(),
            "engine_running": _engine_instance.get_status()['running'] if _engine_instance else False
        }
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to get motivational states: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve motivational states: {str(e)}"
        )

@router.post("/states/{motivation_type}/boost")
async def boost_motivation(
    motivation_type: str,
    request: MotivationBoostRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Boost a specific motivation type.
    
    Increases the urgency level of the specified motivation type,
    which may trigger autonomous task generation.
    
    Args:
        motivation_type: Type of motivation to boost
        request: Boost parameters
        db: Database session
        
    Returns:
        Dict containing boost confirmation
        
    Raises:
        HTTPException: If boost operation fails
    """
    try:
        state_manager = MotivationalStateManager()
        
        # Prepare metadata for boost operation
        boost_metadata = {
            "manual_boost": True,
            "api_triggered": True,
            "timestamp": datetime.utcnow().isoformat(),
            "reason": request.reason,
            **request.metadata
        }
        
        # Use verified boost_motivation method from states.py
        await state_manager.boost_motivation(
            db,
            motivation_type,
            request.boost_amount,
            boost_metadata
        )
        
        logger.info(f"Boosted motivation {motivation_type} by {request.boost_amount}")
        
        return {
            "message": f"Successfully boosted {motivation_type}",
            "motivation_type": motivation_type,
            "boost_amount": request.boost_amount,
            "reason": request.reason,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to boost motivation {motivation_type}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to boost motivation: {str(e)}"
        )

@router.get("/states/{motivation_type}")
async def get_motivation_state(
    motivation_type: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get details of a specific motivational state.
    
    Args:
        motivation_type: Type of motivation to query
        db: Database session
        
    Returns:
        Dict containing detailed motivation state information
    """
    try:
        state_manager = MotivationalStateManager()
        
        # Use verified get_state_by_type method
        state = await state_manager.get_state_by_type(db, motivation_type)
        
        if not state:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Motivation type '{motivation_type}' not found"
            )
        
        # Calculate arbitration score using verified method
        arbitration_score = await state_manager.calculate_arbitration_score(state)
        
        return {
            "motivation_type": state.motivation_type,
            "urgency": round(state.urgency, 3),
            "satisfaction": round(state.satisfaction, 3),
            "arbitration_score": round(arbitration_score, 3),
            "success_rate": round(state.success_rate, 3),
            "total_attempts": state.total_attempts,
            "success_count": state.success_count,
            "failure_count": state.failure_count,
            "is_active": state.is_active,
            "last_triggered": state.last_triggered_at.isoformat() if state.last_triggered_at else None,
            "last_satisfied": state.last_satisfied_at.isoformat() if state.last_satisfied_at else None,
            "decay_rate": state.decay_rate,
            "boost_factor": state.boost_factor,
            "max_urgency": state.max_urgency,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get motivation state {motivation_type}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve motivation state: {str(e)}"
        )

@router.get("/tasks/recent")
async def get_recent_motivational_tasks(
    limit: int = 10,
    db: AsyncSession = Depends(get_db)
):
    """
    Get recent autonomous tasks generated by the motivational system.
    
    Args:
        limit: Maximum number of tasks to return
        db: Database session
        
    Returns:
        Dict containing recent motivational tasks
    """
    try:
        from sqlalchemy import select, desc
        from database.models import MotivationalTask
        
        # Query recent motivational tasks with motivational_state relationship
        from sqlalchemy.orm import selectinload
        result = await db.execute(
            select(MotivationalTask)
            .options(selectinload(MotivationalTask.motivational_state))
            .order_by(desc(MotivationalTask.spawned_at))
            .limit(limit)
        )
        
        tasks = result.scalars().all()
        
        task_list = [
            {
                "task_id": str(task.id),
                "motivation_type": task.motivational_state.motivation_type if task.motivational_state else "unknown",
                "generated_prompt": task.generated_prompt[:200] + "..." if len(task.generated_prompt) > 200 else task.generated_prompt,
                "status": task.status,
                "task_priority": task.task_priority,
                "arbitration_score": task.arbitration_score,
                "spawned_at": task.spawned_at.isoformat(),
                "started_at": task.started_at.isoformat() if task.started_at else None,
                "completed_at": task.completed_at.isoformat() if task.completed_at else None,
                "success": task.success,
                "outcome_score": task.outcome_score
            }
            for task in tasks
        ]
        
        return {
            "recent_tasks": task_list,
            "count": len(task_list),
            "limit": limit,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get recent motivational tasks: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve recent tasks: {str(e)}"
        )

@router.get("/integration/status")
async def get_integration_status():
    """
    Get status of orchestrator integration.
    
    Returns information about the integration between the motivational
    system and the orchestrator.
    
    Returns:
        Dict containing integration status
    """
    global _integration_instance
    
    if not _integration_instance:
        return {
            "integration_active": False,
            "message": "Integration not initialized",
            "timestamp": datetime.utcnow().isoformat()
        }
    
    try:
        # Use verified get_integration_status method
        status = await _integration_instance.get_integration_status()
        
        return {
            "integration_active": True,
            "status": status,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get integration status: {e}", exc_info=True)
        return {
            "integration_active": False,
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }