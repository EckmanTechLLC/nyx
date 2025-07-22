"""
Data Transfer Objects for Motivational System

This module contains data transfer objects (DTOs) that replace SQLAlchemy model objects
when passing data across session boundaries in the motivational system.

Following the principle: "Pass data, not objects" to eliminate session boundary violations.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from datetime import datetime
from uuid import UUID


@dataclass
class TaskSpawnContext:
    """
    Data context for spawning motivated workflows.
    Replaces passing MotivationalTask objects across session boundaries.
    
    This contains all data needed to spawn and track a motivated workflow
    without requiring access to the original SQLAlchemy objects.
    """
    # Required fields (no defaults) - must come first
    task_id: str
    motivational_state_id: str
    generated_prompt: str
    task_priority: float
    arbitration_score: float
    motivation_type: str
    
    # Optional fields (with defaults) - must come after required fields
    thought_tree_id: Optional[str] = None
    status: str = "generated"
    spawned_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    success: Optional[bool] = None
    outcome_score: Optional[float] = None
    satisfaction_gain: Optional[float] = None
    context: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        result = {}
        for key, value in self.__dict__.items():
            if isinstance(value, datetime):
                result[key] = value.isoformat()
            elif isinstance(value, UUID):
                result[key] = str(value)
            else:
                result[key] = value
        return result
    
    @classmethod
    def from_task_model(
        cls, 
        task,  # MotivationalTask model instance
        motivation_type: str
    ) -> "TaskSpawnContext":
        """
        Factory method to create TaskSpawnContext from MotivationalTask model.
        
        IMPORTANT: This method should ONLY be called within an active SQLAlchemy session
        where the task object is properly loaded.
        
        Args:
            task: MotivationalTask model instance (must be session-bound)
            motivation_type: The motivation_type from the related MotivationalState
                           (should be passed explicitly to avoid lazy loading)
        """
        return cls(
            task_id=str(task.id),
            motivational_state_id=str(task.motivational_state_id),
            thought_tree_id=str(task.thought_tree_id) if task.thought_tree_id else None,
            generated_prompt=task.generated_prompt,
            task_priority=task.task_priority,
            arbitration_score=task.arbitration_score,
            motivation_type=motivation_type,
            status=task.status,
            spawned_at=task.spawned_at,
            started_at=task.started_at,
            completed_at=task.completed_at,
            success=task.success,
            outcome_score=task.outcome_score,
            satisfaction_gain=task.satisfaction_gain,
            context=task.context or {}
        )


@dataclass
class MotivationalStateContext:
    """
    Data context for motivational state information.
    Replaces passing MotivationalState objects across session boundaries.
    """
    # Core identifiers  
    state_id: str
    motivation_type: str
    
    # State values
    urgency: float
    satisfaction: float
    decay_rate: float
    boost_factor: float
    
    # Control parameters
    is_active: bool = True
    max_urgency: float = 1.0
    min_satisfaction: float = 0.0
    
    # Statistics
    success_count: int = 0
    failure_count: int = 0
    total_attempts: int = 0
    success_rate: float = 0.0
    
    # Timing information
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    last_triggered_at: Optional[datetime] = None
    last_satisfied_at: Optional[datetime] = None
    
    # Configuration data
    trigger_condition: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def from_state_model(cls, state) -> "MotivationalStateContext":
        """
        Factory method to create MotivationalStateContext from MotivationalState model.
        
        IMPORTANT: This method should ONLY be called within an active SQLAlchemy session.
        """
        return cls(
            state_id=str(state.id),
            motivation_type=state.motivation_type,
            urgency=state.urgency,
            satisfaction=state.satisfaction,
            decay_rate=state.decay_rate,
            boost_factor=state.boost_factor,
            is_active=state.is_active,
            max_urgency=state.max_urgency,
            min_satisfaction=state.min_satisfaction,
            success_count=state.success_count,
            failure_count=state.failure_count,
            total_attempts=state.total_attempts,
            success_rate=state.success_rate,
            created_at=state.created_at,
            updated_at=state.updated_at,
            last_triggered_at=state.last_triggered_at,
            last_satisfied_at=state.last_satisfied_at,
            trigger_condition=state.trigger_condition or {},
            metadata=state.metadata_ or {}
        )


@dataclass  
class WorkflowExecutionContext:
    """
    Complete context for executing motivated workflows.
    Contains all information needed to track and execute a workflow
    without referencing SQLAlchemy objects.
    """
    # Task context
    task_context: TaskSpawnContext
    
    # Execution identifiers
    thought_tree_id: str
    orchestrator_id: str
    
    # Timing
    started_at: datetime
    
    # Workflow configuration
    workflow_input: Dict[str, Any]
    
    # Execution metadata
    execution_metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_workflow_info_dict(self) -> Dict[str, Any]:
        """
        Convert to the workflow_info dictionary format used by
        active_motivated_workflows tracking.
        
        This replaces the previous approach that mixed objects and primitives.
        """
        return {
            'task_id': self.task_context.task_id,
            'thought_tree_id': self.thought_tree_id,
            'orchestrator_id': self.orchestrator_id,
            'started_at': self.started_at,
            'motivation_type': self.task_context.motivation_type,
            'task_priority': self.task_context.task_priority,
            'arbitration_score': self.task_context.arbitration_score,
            'status': self.task_context.status,
            'metadata': self.execution_metadata
        }


# Utility functions for common data extraction patterns

async def extract_task_context_from_db(
    session,  # AsyncSession
    task_id: str
) -> TaskSpawnContext:
    """
    Extract complete task context from database within session.
    
    This function performs eager loading of the motivational_state relationship
    to avoid lazy loading issues when the task data is used outside the session.
    
    Args:
        session: Active AsyncSession
        task_id: UUID string of the task
        
    Returns:
        TaskSpawnContext with all needed data
    """
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
    from database.models import MotivationalTask
    
    # Eager load the motivational_state relationship to avoid lazy loading
    result = await session.execute(
        select(MotivationalTask)
        .options(selectinload(MotivationalTask.motivational_state))
        .where(MotivationalTask.id == task_id)
    )
    
    task = result.scalar_one()
    
    # Extract motivation_type safely - ensure relationship is loaded
    motivation_type = 'unknown'
    if hasattr(task, 'motivational_state') and task.motivational_state is not None:
        motivation_type = task.motivational_state.motivation_type
    
    return TaskSpawnContext.from_task_model(task, motivation_type)


async def extract_task_context_from_loaded_task(
    session,  # AsyncSession 
    task   # MotivationalTask (already loaded)
) -> TaskSpawnContext:
    """
    Extract task context from already-loaded task object.
    
    This is used when we already have a task object (e.g., from a query loop)
    and need to extract the context data including the motivational_state relationship.
    
    Args:
        session: Active AsyncSession (for lazy loading if needed)
        task: Already loaded MotivationalTask object
        
    Returns:
        TaskSpawnContext with all needed data
    """
    # Ensure motivational_state is loaded to avoid lazy loading outside session
    if not hasattr(task, '_sa_instance_state') or task._sa_instance_state.expired:
        # Task might be detached, reload it
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload
        from database.models import MotivationalTask
        
        result = await session.execute(
            select(MotivationalTask)
            .options(selectinload(MotivationalTask.motivational_state))
            .where(MotivationalTask.id == task.id)
        )
        task = result.scalar_one()
    
    # Access the relationship safely
    motivation_type = 'unknown'
    if hasattr(task, 'motivational_state') and task.motivational_state is not None:
        motivation_type = task.motivational_state.motivation_type
    
    return TaskSpawnContext.from_task_model(task, motivation_type)