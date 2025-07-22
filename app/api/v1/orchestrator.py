"""
Orchestrator API endpoints for workflow execution and management.

Provides REST API access to NYX's TopLevelOrchestrator capabilities.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, Optional, List
from uuid import UUID, uuid4
from datetime import datetime
from pydantic import BaseModel, Field

from ...core.database import get_db
from ...core.exceptions import WorkflowExecutionError

# Import verified NYX orchestrator components
from core.orchestrator.top_level import TopLevelOrchestrator, WorkflowInput, WorkflowInputType
from database.schemas import ThoughtTree as ThoughtTreeSchema

logger = __import__('logging').getLogger(__name__)

router = APIRouter()

# Request/Response models based on verified WorkflowInput structure
class WorkflowRequest(BaseModel):
    """Request model for workflow execution based on verified WorkflowInput dataclass"""
    input_type: str = Field(
        ..., 
        description="Type of workflow input",
        example="user_prompt"
    )
    content: Dict[str, Any] = Field(
        ..., 
        description="Workflow content and parameters",
        example={"prompt": "Generate a comprehensive system analysis"}
    )
    execution_context: Dict[str, Any] = Field(
        default_factory=dict,
        description="Execution context and constraints"
    )
    domain_context: Dict[str, Any] = Field(
        default_factory=dict,
        description="Domain-specific context"
    )
    user_context: Dict[str, Any] = Field(
        default_factory=dict,
        description="User-specific context and preferences"
    )
    historical_context: Dict[str, Any] = Field(
        default_factory=dict,
        description="Historical context from previous workflows"
    )
    priority: str = Field(
        default="medium",
        description="Workflow priority level",
        example="high"
    )
    urgency: str = Field(
        default="normal",
        description="Workflow urgency level",
        example="urgent"
    )

class WorkflowResponse(BaseModel):
    """Response model for workflow execution"""
    success: bool = Field(..., description="Whether workflow execution succeeded")
    content: str = Field(..., description="Workflow output content")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Execution metadata")
    execution_time_ms: int = Field(..., description="Execution time in milliseconds")
    cost_usd: float = Field(default=0.0, description="Execution cost in USD")
    workflow_id: Optional[str] = Field(None, description="Unique workflow identifier")
    timestamp: str = Field(..., description="Execution timestamp")

class WorkflowStatusResponse(BaseModel):
    """Response model for workflow status"""
    workflow_id: str
    status: str
    created_at: str
    updated_at: str
    metadata: Dict[str, Any] = Field(default_factory=dict)

@router.post("/workflows/execute", response_model=WorkflowResponse)
async def execute_workflow(
    request: WorkflowRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Execute a workflow using NYX TopLevelOrchestrator.
    
    This endpoint provides access to NYX's sophisticated orchestration capabilities,
    supporting multiple workflow types with comprehensive context management.
    
    Args:
        request: Workflow execution request
        db: Database session
        
    Returns:
        WorkflowResponse: Execution results and metadata
        
    Raises:
        HTTPException: If workflow execution fails
    """
    try:
        logger.info(f"Executing workflow: {request.input_type}")
        
        # Validate input_type against verified enum values
        try:
            workflow_input_type = WorkflowInputType(request.input_type)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid input_type '{request.input_type}'. Valid types: {[e.value for e in WorkflowInputType]}"
            )
        
        # Create TopLevelOrchestrator instance with database session
        orchestrator = TopLevelOrchestrator(db)
        
        # Create WorkflowInput using verified dataclass structure
        workflow_input = WorkflowInput(
            input_type=workflow_input_type,
            content=request.content,
            execution_context=request.execution_context,
            domain_context=request.domain_context,
            user_context=request.user_context,
            historical_context=request.historical_context,
            priority=request.priority,
            urgency=request.urgency
        )
        
        # Execute workflow using verified execute_workflow method
        start_time = datetime.utcnow()
        result = await orchestrator.execute_workflow(workflow_input)
        execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        # Create response using verified OrchestratorResult attributes
        response = WorkflowResponse(
            success=result.success,
            content=result.content,
            metadata=result.metadata,
            execution_time_ms=int(execution_time),
            cost_usd=float(result.cost_usd) if result.cost_usd else 0.0,
            workflow_id=result.metadata.get('workflow_id') if result.metadata else None,
            timestamp=datetime.utcnow().isoformat()
        )
        
        logger.info(f"Workflow execution completed: success={result.success}")
        return response
        
    except ValueError as e:
        # Handle validation errors
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid workflow parameters: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Workflow execution failed: {e}", exc_info=True)
        raise WorkflowExecutionError(
            detail=f"Workflow execution failed: {str(e)}",
            metadata={
                "input_type": request.input_type,
                "error_type": type(e).__name__,
                "timestamp": datetime.utcnow().isoformat()
            }
        )

@router.get("/workflows/{workflow_id}/status", response_model=WorkflowStatusResponse)
async def get_workflow_status(
    workflow_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Get status of a specific workflow by querying the thought tree.
    
    Args:
        workflow_id: UUID of the workflow to check
        db: Database session
        
    Returns:
        WorkflowStatusResponse: Current workflow status
        
    Raises:
        HTTPException: If workflow not found or status check fails
    """
    try:
        # Query the thought tree for workflow status using verified database models
        from sqlalchemy import select
        from database.models import ThoughtTree
        
        result = await db.execute(
            select(ThoughtTree)
            .where(ThoughtTree.id == workflow_id)
        )
        
        workflow = result.scalar_one_or_none()
        
        if not workflow:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Workflow {workflow_id} not found"
            )
        
        return WorkflowStatusResponse(
            workflow_id=str(workflow.id),
            status=workflow.status,
            created_at=workflow.created_at.isoformat(),
            updated_at=workflow.updated_at.isoformat(),
            metadata=workflow.metadata or {}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get workflow status: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve workflow status: {str(e)}"
        )

@router.get("/workflows/active")
async def list_active_workflows(
    limit: int = 10,
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
):
    """
    List currently active workflows.
    
    Args:
        limit: Maximum number of workflows to return
        offset: Number of workflows to skip
        db: Database session
        
    Returns:
        Dict containing list of active workflows
    """
    try:
        from sqlalchemy import select, desc
        from database.models import ThoughtTree
        
        # Query for active workflows (pending or in_progress status)
        result = await db.execute(
            select(ThoughtTree)
            .where(ThoughtTree.status.in_(['pending', 'in_progress']))
            .order_by(desc(ThoughtTree.created_at))
            .limit(limit)
            .offset(offset)
        )
        
        workflows = result.scalars().all()
        
        active_workflows = [
            {
                "workflow_id": str(workflow.id),
                "status": workflow.status,
                "goal": workflow.goal,
                "created_at": workflow.created_at.isoformat(),
                "updated_at": workflow.updated_at.isoformat(),
                "depth": workflow.depth,
                "importance_level": workflow.importance_level
            }
            for workflow in workflows
        ]
        
        return {
            "active_workflows": active_workflows,
            "count": len(active_workflows),
            "limit": limit,
            "offset": offset,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to list active workflows: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve active workflows: {str(e)}"
        )

@router.get("/strategies")
async def list_workflow_strategies():
    """
    List available workflow execution strategies.
    
    Returns information about the different execution strategies
    supported by the TopLevelOrchestrator.
    
    Returns:
        Dict containing available strategies and their descriptions
    """
    from core.orchestrator.top_level import WorkflowStrategy
    
    strategies = {
        strategy.value: {
            "name": strategy.value,
            "description": _get_strategy_description(strategy.value)
        }
        for strategy in WorkflowStrategy
    }
    
    return {
        "strategies": strategies,
        "count": len(strategies),
        "timestamp": datetime.utcnow().isoformat()
    }

def _get_strategy_description(strategy: str) -> str:
    """Get description for workflow strategy"""
    descriptions = {
        "direct_execution": "Execute workflow directly without decomposition",
        "sequential_decomposition": "Break down workflow into sequential subtasks",
        "parallel_execution": "Execute workflow components in parallel",
        "recursive_decomposition": "Recursively decompose complex workflows",
        "council_driven": "Use council of agents for decision-making",
        "iterative_refinement": "Iteratively refine workflow outputs"
    }
    return descriptions.get(strategy, "Strategy description not available")

@router.get("/input-types")
async def list_input_types():
    """
    List supported workflow input types.
    
    Returns:
        Dict containing supported input types and descriptions
    """
    input_types = {
        input_type.value: {
            "name": input_type.value,
            "description": _get_input_type_description(input_type.value)
        }
        for input_type in WorkflowInputType
    }
    
    return {
        "input_types": input_types,
        "count": len(input_types),
        "timestamp": datetime.utcnow().isoformat()
    }

def _get_input_type_description(input_type: str) -> str:
    """Get description for input type"""
    descriptions = {
        "user_prompt": "Natural language prompt from user",
        "structured_task": "Structured task with defined parameters",
        "goal_workflow": "Goal-oriented workflow specification", 
        "scheduled_workflow": "Time-scheduled recurring workflow",
        "reactive_workflow": "Event-triggered reactive workflow",
        "continuation_workflow": "Continuation of existing workflow"
    }
    return descriptions.get(input_type, "Input type description not available")