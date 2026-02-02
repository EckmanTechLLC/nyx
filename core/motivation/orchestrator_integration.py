"""
Orchestrator Integration for Motivational Model

Integrates the motivational model with NYX's existing orchestrator system
to enable self-initiated task execution.
"""

import asyncio
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from uuid import uuid4

from database.connection import db_manager
from database.models import MotivationalTask, ThoughtTree
from core.orchestrator.top_level import TopLevelOrchestrator, WorkflowInput, WorkflowInputType
from .engine import MotivationalModelEngine
from .spawner import SelfInitiatedTaskSpawner
from .feedback import MotivationalFeedbackLoop
from .dto import TaskSpawnContext, WorkflowExecutionContext

logger = logging.getLogger(__name__)


class MotivationalOrchestratorIntegration:
    """
    Integration layer between the motivational model and NYX orchestrators.
    Enables autonomous task spawning and execution tracking.
    """
    
    def __init__(
        self, 
        motivational_engine: MotivationalModelEngine
    ):
        self.db_manager = db_manager
        self.motivational_engine = motivational_engine
        self.spawner = SelfInitiatedTaskSpawner()
        self.feedback_loop = MotivationalFeedbackLoop()
        
        # Track active motivated workflows
        self.active_motivated_workflows: Dict[str, Dict[str, Any]] = {}
        
        # Task polling configuration
        self.polling_interval = 10.0  # seconds
        self.polling_task: Optional[asyncio.Task] = None
        self.polling_enabled = False

    async def start_integration(self):
        """Start the integration system"""
        try:
            if not self.polling_enabled:
                self.polling_enabled = True
                self.polling_task = asyncio.create_task(self._polling_loop())
                logger.info("Motivational orchestrator integration started")
            
        except Exception as e:
            logger.error(f"Failed to start integration: {e}")

    async def stop_integration(self):
        """Stop the integration system"""
        try:
            self.polling_enabled = False
            if self.polling_task:
                self.polling_task.cancel()
                try:
                    await self.polling_task
                except asyncio.CancelledError:
                    pass
                self.polling_task = None
            
            logger.info("Motivational orchestrator integration stopped")
            
        except Exception as e:
            logger.error(f"Error stopping integration: {e}")

    async def _polling_loop(self):
        """Main polling loop to check for pending motivated tasks"""
        try:
            while self.polling_enabled:
                try:
                    await self._process_pending_tasks()
                    await asyncio.sleep(self.polling_interval)
                except Exception as e:
                    logger.error(f"Error in polling loop: {e}")
                    await asyncio.sleep(self.polling_interval)
        except asyncio.CancelledError:
            logger.info("Motivational integration polling loop cancelled")
        except Exception as e:
            logger.error(f"Fatal error in polling loop: {e}")

    async def _process_pending_tasks(self):
        """Process any pending motivated tasks by spawning orchestrators"""
        try:
            async with self.db_manager.get_async_session() as session:
                # Get pending motivated tasks
                pending_tasks = await self.spawner.get_pending_tasks(session, limit=5)
                
                for task in pending_tasks:
                    if str(task.id) not in self.active_motivated_workflows:
                        # Extract task context data within session to avoid lazy loading issues
                        task_context = await self._extract_task_context(session, task)
                        await self._spawn_workflow_for_task_data(task_context)
                
        except Exception as e:
            logger.error(f"Error processing pending tasks: {e}")

    async def _extract_task_context(self, session, task) -> 'TaskSpawnContext':
        """
        Extract complete task context from MotivationalTask within active session.
        
        This method ensures all related data (especially motivational_state) is loaded
        while the session is active, preventing lazy loading issues later.
        
        Args:
            session: Active AsyncSession
            task: MotivationalTask object (session-bound)
            
        Returns:
            TaskSpawnContext with all needed data extracted
        """
        from .dto import extract_task_context_from_loaded_task
        return await extract_task_context_from_loaded_task(session, task)

    async def _spawn_workflow_for_task_data(self, task_context: 'TaskSpawnContext'):
        """
        Spawn a workflow orchestrator using task context data.
        
        This method replaces _spawn_workflow_for_task() and operates on data
        rather than SQLAlchemy objects, eliminating session boundary violations.
        
        Args:
            task_context: TaskSpawnContext with all necessary task data
        """
        thought_tree_id = None
        
        try:
            # Database operations - create new session for this workflow spawn
            async with self.db_manager.get_async_session() as session:
                logger.debug(f"Starting workflow spawn for task {task_context.task_id}")
                
                # Step 1: Update task status to spawned
                await self.spawner.update_task_status(
                    session,
                    task_context.task_id,
                    'spawned',
                    metadata={'spawned_at': datetime.now(timezone.utc).isoformat()}
                )
                
                # Step 2: Create thought tree for the motivated workflow
                thought_tree_id = await self._create_thought_tree_from_context(session, task_context)
                
                # Step 3: Update task with thought tree ID and set to active
                await self.spawner.update_task_status(
                    session,
                    task_context.task_id,
                    'active',
                    thought_tree_id=thought_tree_id,
                    metadata={'thought_tree_created': datetime.now(timezone.utc).isoformat()}
                )
                
                # Step 4: Commit all database changes
                await session.commit()
                logger.debug(f"Database operations completed for task {task_context.task_id}")
                
        except Exception as e:
            logger.error(f"Error in database operations for task {task_context.task_id}: {e}")
            try:
                async with self.db_manager.get_async_session() as error_session:
                    await self.spawner.update_task_status(
                        error_session,
                        task_context.task_id,
                        'failed',
                        metadata={'db_error': str(e), 'failed_at': datetime.now(timezone.utc).isoformat()}
                    )
                    await error_session.commit()
            except Exception as nested_e:
                logger.error(f"Failed to update task status after error: {nested_e}")
            return
        
        # NOW - orchestrator work with clean data (no SQLAlchemy objects)
        try:
            logger.debug(f"Starting orchestrator initialization for task {task_context.task_id}")
            
            # Create workflow input from context data (no lazy loading)
            workflow_input = self._create_workflow_input_from_context(task_context)
            
            # Create and configure orchestrator
            orchestrator = TopLevelOrchestrator(
                max_concurrent_agents=6,
                max_execution_time_minutes=60,
                max_cost_usd=20.0,
                max_recursion_depth=5
            )
            
            # Set thought tree ID and initialize
            orchestrator.thought_tree_id = thought_tree_id
            
            # Create clean async context for initialization
            async def init_orchestrator():
                return await orchestrator.initialize()
            
            await init_orchestrator()
            
            # Create execution context for workflow tracking
            execution_context = self._create_execution_context(
                task_context, thought_tree_id, orchestrator.id, workflow_input
            )
            
            # Track the workflow with orchestrator object for execution
            self.active_motivated_workflows[thought_tree_id] = {
                'orchestrator': orchestrator,
                'task_id': task_context.task_id,
                'thought_tree_id': thought_tree_id,
                'workflow_input': workflow_input
            }

            # Execute workflow in background using working execution method
            asyncio.create_task(self._execute_motivated_workflow(workflow_input, self.active_motivated_workflows[thought_tree_id]))
            
            logger.info(f"Successfully spawned motivated workflow for task {task_context.task_id}")
            
        except Exception as e:
            logger.error(f"Error initializing orchestrator for task {task_context.task_id}: {e}")
            
            # Update task status using fresh session
            try:
                async with self.db_manager.get_async_session() as error_session:
                    await self.spawner.update_task_status(
                        error_session,
                        task_context.task_id,
                        'failed',
                        metadata={'orchestrator_error': str(e)}
                    )
                    await error_session.commit()
                    logger.debug(f"Updated task {task_context.task_id} status to failed")
            except Exception as error_e:
                logger.error(f"Failed to update task status after orchestrator error: {error_e}")


    def _create_workflow_input_from_context(self, task_context: TaskSpawnContext) -> WorkflowInput:
        """
        Create WorkflowInput from TaskSpawnContext (replacing the task object version).
        
        This method operates on extracted data rather than SQLAlchemy objects,
        eliminating lazy loading issues.
        
        Args:
            task_context: TaskSpawnContext with all needed data
            
        Returns:
            WorkflowInput for orchestrator execution
        """
        # Create workflow input for autonomous execution using context data
        workflow_input = WorkflowInput(
            input_type=WorkflowInputType.USER_PROMPT,  # Treat as user prompt for compatibility
            content={
                'content': task_context.generated_prompt,
                'autonomous_origin': True,
                'motivation_type': task_context.motivation_type  # No lazy loading - data already extracted
            },
            execution_context={
                'motivated_task': True,
                'task_priority': task_context.task_priority,
                'arbitration_score': task_context.arbitration_score,
                'autonomous_execution': True,
                'task_id': task_context.task_id,
                'motivation_type': task_context.motivation_type,
                'quality_settings': {
                    'validation_level': 'standard',
                    'require_council_consensus': False
                },
                'execution_preferences': {
                    'optimization_focus': 'balanced'
                }
            },
            priority=self._priority_from_score(task_context.task_priority),
            urgency='normal'
        )
        
        return workflow_input

    def _create_execution_context(
        self, 
        task_context: TaskSpawnContext, 
        thought_tree_id: str, 
        orchestrator_id: str,
        workflow_input: WorkflowInput
    ) -> WorkflowExecutionContext:
        """
        Create WorkflowExecutionContext for tracking workflow execution.
        
        This replaces the previous approach of mixing objects and primitives
        in workflow tracking dictionaries.
        
        Args:
            task_context: TaskSpawnContext with task data
            thought_tree_id: ID of created thought tree
            orchestrator_id: ID of orchestrator instance
            workflow_input: WorkflowInput for execution
            
        Returns:
            WorkflowExecutionContext for tracking
        """
        return WorkflowExecutionContext(
            task_context=task_context,
            thought_tree_id=thought_tree_id,
            orchestrator_id=orchestrator_id,
            started_at=datetime.now(timezone.utc),
            workflow_input=workflow_input.content,  # Store serializable content
            execution_metadata={
                'spawning_method': 'data_context',
                'created_at': datetime.now(timezone.utc).isoformat()
            }
        )

    async def _create_thought_tree_from_context(self, session, task_context: TaskSpawnContext) -> str:
        """
        Create a thought tree from task context data (replacing the task object version).
        
        This method operates on TaskSpawnContext data rather than the MotivationalTask object,
        avoiding any potential lazy loading issues.
        
        Args:
            session: Active AsyncSession
            task_context: TaskSpawnContext with all needed task data
            
        Returns:
            thought_tree_id: UUID string of created thought tree
        """
        try:
            # Generate UUID as string (following codebase patterns)
            thought_tree_id = str(uuid4())
            
            # Create thought tree using context data (no model object relationships)
            thought_tree = ThoughtTree(
                id=thought_tree_id,
                parent_id=None,
                root_id=thought_tree_id,  # Set to self for top-level tasks
                goal=f"AUTONOMOUS: {task_context.motivation_type} - {task_context.generated_prompt[:200]}...",
                status='in_progress',  # Match orchestrator expectation
                depth=1,  # Match orchestrator expectation for root workflows
                metadata_={
                    'autonomous_task': True,
                    'motivation_type': task_context.motivation_type,
                    'motivated_task_id': task_context.task_id,
                    'priority': task_context.task_priority,
                    'arbitration_score': task_context.arbitration_score,
                    'orchestrator_type': 'top_level'  # Match orchestrator metadata
                },
                importance_level='medium' if task_context.task_priority >= 0.5 else 'low'
            )
            
            session.add(thought_tree)
            # DO NOT commit here - let the caller handle the commit
            
            return thought_tree_id
            
        except Exception as e:
            logger.error(f"Error creating thought tree from context: {e}")
            raise

    async def _execute_motivated_workflow_from_context(self, execution_context: WorkflowExecutionContext):
        """
        Execute motivated workflow using execution context (replacing the mixed-object version).
        
        This method operates on WorkflowExecutionContext rather than mixing
        SQLAlchemy objects with primitives.
        
        Args:
            execution_context: WorkflowExecutionContext with all workflow data
        """
        task_id = execution_context.task_context.task_id
        thought_tree_id = execution_context.thought_tree_id
        
        try:
            logger.info(f"Executing motivated workflow {thought_tree_id}")
            
            # Get orchestrator from active workflows (stored as data, not object)
            workflow_info = self.active_motivated_workflows.get(thought_tree_id)
            if not workflow_info:
                logger.error(f"Workflow info not found for {thought_tree_id}")
                return
            
            # Since we're using data context pattern, we would need to either:
            # 1. Re-instantiate the orchestrator from the orchestrator_id, or  
            # 2. Keep a separate tracking of orchestrator objects
            # For now, this is a placeholder that shows the pattern
            logger.info(f"Would execute workflow for task {task_id} with thought tree {thought_tree_id}")
            
            # Process feedback using task context data
            await self.motivational_engine.process_task_outcome(
                task_id,
                success=True,  # Placeholder
                outcome_score=0.8,  # Placeholder
                metadata={
                    'thought_tree_id': thought_tree_id,
                    'motivation_type': execution_context.task_context.motivation_type,
                    'task_priority': execution_context.task_context.task_priority
                }
            )
            
            logger.info(f"Completed motivated workflow {thought_tree_id}")
            
        except Exception as e:
            logger.error(f"Error executing motivated workflow {thought_tree_id}: {e}")
            
            # Handle failure using context data
            await self.motivational_engine.process_task_outcome(
                task_id,
                False,
                0.0,
                metadata={'error': str(e), 'thought_tree_id': thought_tree_id}
            )
            
        finally:
            # Clean up
            if thought_tree_id in self.active_motivated_workflows:
                del self.active_motivated_workflows[thought_tree_id]

    def _create_workflow_input_from_task(self, task: MotivationalTask) -> WorkflowInput:
        """Create WorkflowInput from a MotivationalTask"""
        
        # Get motivation type safely without lazy loading
        # This method should not access relationships - use the data-passing pattern instead
        motivation_type = 'unknown'
        
        # Create workflow input for autonomous execution
        workflow_input = WorkflowInput(
            input_type=WorkflowInputType.USER_PROMPT,  # Treat as user prompt for compatibility
            content={
                'content': task.generated_prompt,
                'autonomous_origin': True,
                'motivation_type': motivation_type
            },
            execution_context={
                'motivated_task': True,
                'task_priority': task.task_priority,
                'arbitration_score': task.arbitration_score,
                'autonomous_execution': True,
                'quality_settings': {
                    'validation_level': 'standard',
                    'require_council_consensus': False
                },
                'execution_preferences': {
                    'optimization_focus': 'balanced'
                }
            },
            priority=self._priority_from_score(task.task_priority),
            urgency='normal'
        )
        
        return workflow_input

    def _priority_from_score(self, score: float) -> str:
        """Convert numeric priority score to string priority"""
        if score >= 0.8:
            return 'high'
        elif score >= 0.6:
            return 'medium'
        elif score >= 0.3:
            return 'low'
        else:
            return 'minimal'

    async def _create_thought_tree_within_session(self, session, task: MotivationalTask) -> str:
        """Create a thought tree for the motivated task within the provided session"""
        try:
            # Get motivation type for context from the task's lazy-loaded relationship
            motivation_type = 'unknown'
            if task.motivational_state_id:
                from sqlalchemy import select
                from database.models import MotivationalState
                # Use the same session to maintain transaction consistency
                state_result = await session.execute(
                    select(MotivationalState)
                    .where(MotivationalState.id == task.motivational_state_id)
                )
                state = state_result.scalar_one_or_none()
                if state:
                    motivation_type = state.motivation_type
            
            # Generate UUID as string (following codebase patterns)
            thought_tree_id = str(uuid4())
            
            # Create thought tree in the SAME session for transaction consistency
            thought_tree = ThoughtTree(
                id=thought_tree_id,
                parent_id=None,
                root_id=thought_tree_id,  # Set to self for top-level tasks
                goal=f"AUTONOMOUS: {motivation_type} - {task.generated_prompt[:200]}...",
                status='in_progress',  # Match orchestrator expectation
                depth=1,  # Match orchestrator expectation for root workflows
                metadata_={
                    'autonomous_task': True,
                    'motivation_type': motivation_type,
                    'motivated_task_id': str(task.id),
                    'priority': task.task_priority,
                    'arbitration_score': task.arbitration_score,
                    'orchestrator_type': 'top_level'  # Match orchestrator metadata
                },
                importance_level='medium' if task.task_priority >= 0.5 else 'low'
            )
            
            session.add(thought_tree)
            # DO NOT commit here - let the caller handle the commit
            
            return thought_tree_id
            
        except Exception as e:
            logger.error(f"Error creating thought tree for motivated task: {e}")
            raise

    async def _create_thought_tree(self, session, task: MotivationalTask) -> str:
        """Create a thought tree for the motivated task"""
        try:
            # Get motivation type for context
            motivation_type = 'unknown'
            if task.motivational_state_id:
                # Fetch from database using fresh session to avoid async context issues
                async with self.db_manager.get_async_session() as fresh_session:
                    from sqlalchemy import select
                    from database.models import MotivationalState
                    state_result = await fresh_session.execute(
                        select(MotivationalState)
                        .where(MotivationalState.id == task.motivational_state_id)
                    )
                    state = state_result.scalar_one_or_none()
                    if state:
                        motivation_type = state.motivation_type
            
            # Generate UUID as string (following codebase patterns)
            thought_tree_id = str(uuid4())
            
            # Create thought tree in a completely fresh session to avoid async context issues
            async with self.db_manager.get_async_session() as tree_session:
                thought_tree = ThoughtTree(
                    id=thought_tree_id,
                    parent_id=None,
                    root_id=thought_tree_id,  # Set to self for top-level tasks
                    goal=f"AUTONOMOUS: {motivation_type} - {task.generated_prompt[:200]}...",
                    status='in_progress',  # Match orchestrator expectation
                    depth=1,  # Match orchestrator expectation for root workflows
                    metadata_={
                        'autonomous_task': True,
                        'motivation_type': motivation_type,
                        'motivated_task_id': str(task.id),
                        'priority': task.task_priority,
                        'arbitration_score': task.arbitration_score,
                        'orchestrator_type': 'top_level'  # Match orchestrator metadata
                    },
                    importance_level='medium' if task.task_priority >= 0.5 else 'low'
                )
                
                tree_session.add(thought_tree)
                await tree_session.commit()
            
            return thought_tree_id
            
        except Exception as e:
            logger.error(f"Error creating thought tree for motivated task: {e}")
            raise

    async def _execute_motivated_workflow(self, workflow_input: WorkflowInput, workflow_info: Dict[str, Any]):
        """Execute the motivated workflow and handle outcome"""
        orchestrator = workflow_info['orchestrator']
        task_id = workflow_info['task_id']
        thought_tree_id = workflow_info['thought_tree_id']
        
        try:
            logger.info(f"Executing motivated workflow {thought_tree_id}")
            
            # Execute the workflow
            result = await orchestrator.execute_workflow(workflow_input)
            
            # Calculate outcome metrics
            success = result.success
            outcome_score = self._calculate_outcome_score(result)
            
            # Process feedback
            await self.motivational_engine.process_task_outcome(
                task_id,
                success,
                outcome_score,
                metadata={
                    'thought_tree_id': thought_tree_id,
                    'execution_time_ms': result.execution_time_ms,
                    'total_cost': result.total_cost_usd,
                    'agents_used': result.agents_spawned,
                    'strategy_used': result.metadata.get('strategy_used') if result.metadata else None
                }
            )
            
            # Update thought tree status
            await self._update_thought_tree_completion(thought_tree_id, result)
            
            logger.info(f"Completed motivated workflow {thought_tree_id}: success={success}, score={outcome_score:.2f}")
            
        except Exception as e:
            logger.error(f"Error executing motivated workflow {thought_tree_id}: {e}")
            
            # Handle failure
            await self.motivational_engine.process_task_outcome(
                task_id,
                False,
                0.0,
                metadata={'error': str(e), 'thought_tree_id': thought_tree_id}
            )
            
        finally:
            # Clean up
            try:
                await orchestrator.terminate()
            except:
                pass
            
            # Remove from active workflows
            if thought_tree_id in self.active_motivated_workflows:
                del self.active_motivated_workflows[thought_tree_id]

    def _calculate_outcome_score(self, orchestrator_result) -> float:
        """Calculate outcome score from orchestrator result"""
        try:
            base_score = 0.8 if orchestrator_result.success else 0.2
            
            # Adjust based on execution metrics
            if orchestrator_result.success:
                # Bonus for efficiency
                if orchestrator_result.execution_time_ms < 300000:  # Under 5 minutes
                    base_score += 0.1
                
                if orchestrator_result.total_cost_usd < 10.0:  # Under budget
                    base_score += 0.1
                
                # Penalty for high agent failure rate
                if orchestrator_result.agents_failed > 0:
                    total_agents = orchestrator_result.agents_spawned
                    failure_rate = orchestrator_result.agents_failed / total_agents if total_agents > 0 else 0
                    base_score -= failure_rate * 0.3
            
            return max(0.0, min(1.0, base_score))
            
        except Exception as e:
            logger.error(f"Error calculating outcome score: {e}")
            return 0.5

    async def _update_thought_tree_completion(self, thought_tree_id: str, orchestrator_result):
        """Update thought tree with completion status"""
        try:
            async with self.db_manager.get_async_session() as session:
                from sqlalchemy import update
                from uuid import UUID
                
                update_data = {
                    'status': 'completed' if orchestrator_result.success else 'failed',
                    'completed_at': datetime.now(timezone.utc),
                    'updated_at': datetime.now(timezone.utc)
                }
                
                # Update metadata with execution details
                metadata_update = {
                    'execution_completed': True,
                    'final_success': orchestrator_result.success,
                    'execution_time_ms': orchestrator_result.execution_time_ms,
                    'total_cost_usd': orchestrator_result.total_cost_usd,
                    'agents_spawned': orchestrator_result.agents_spawned,
                    'agents_completed': orchestrator_result.agents_completed,
                    'agents_failed': orchestrator_result.agents_failed
                }
                
                if orchestrator_result.final_output:
                    metadata_update['final_output_preview'] = str(orchestrator_result.final_output)[:500]
                
                if orchestrator_result.error_message:
                    metadata_update['error_message'] = orchestrator_result.error_message

                update_data['metadata_'] = metadata_update

                # Execute update
                await session.execute(
                    update(ThoughtTree)
                    .where(ThoughtTree.id == UUID(thought_tree_id))
                    .values(**update_data)
                )
                
                await session.commit()
                
        except Exception as e:
            logger.error(f"Error updating thought tree completion: {e}")

    async def get_integration_status(self) -> Dict[str, Any]:
        """Get status of the integration system"""
        try:
            active_count = len(self.active_motivated_workflows)
            
            # Get breakdown by motivation type
            motivation_breakdown = {}
            for workflow_info in self.active_motivated_workflows.values():
                motivation_type = workflow_info.get('motivation_type', 'unknown')
                motivation_breakdown[motivation_type] = motivation_breakdown.get(motivation_type, 0) + 1
            
            # Calculate running time for active workflows
            now = datetime.now(timezone.utc)
            running_times = []
            for workflow_info in self.active_motivated_workflows.values():
                started = workflow_info.get('started_at')
                if started:
                    elapsed = (now - started).total_seconds() / 60  # minutes
                    running_times.append(elapsed)
            
            avg_running_time = sum(running_times) / len(running_times) if running_times else 0
            
            return {
                'integration_active': self.polling_enabled,
                'polling_interval': self.polling_interval,
                'active_motivated_workflows': active_count,
                'motivation_breakdown': motivation_breakdown,
                'average_running_time_minutes': round(avg_running_time, 1),
                'longest_running_minutes': round(max(running_times, default=0), 1),
                'status': 'operational' if self.polling_enabled else 'stopped'
            }
            
        except Exception as e:
            logger.error(f"Error getting integration status: {e}")
            return {
                'status': 'error',
                'error': str(e)
            }

    async def force_process_pending_tasks(self):
        """Manually trigger processing of pending tasks (for testing/debugging)"""
        try:
            await self._process_pending_tasks()
            logger.info("Manually processed pending motivated tasks")
        except Exception as e:
            logger.error(f"Error in manual task processing: {e}")


# Helper function to create a complete motivational system
async def create_integrated_motivational_system(
    start_engine: bool = True,
    start_integration: bool = True
) -> tuple[MotivationalModelEngine, MotivationalOrchestratorIntegration]:
    """
    Create a complete integrated motivational system
    
    Returns:
        Tuple of (engine, integration) for full autonomous capability
    """
    try:
        # Initialize the motivational model system
        from .initializer import quick_init_motivational_system
        
        engine = await quick_init_motivational_system(
            start_engine=start_engine
        )
        
        if not engine:
            raise RuntimeError("Failed to initialize motivational engine")
        
        # Create integration layer
        integration = MotivationalOrchestratorIntegration(engine)
        
        if start_integration:
            await integration.start_integration()
        
        logger.info("Integrated motivational system created successfully")
        return engine, integration
        
    except Exception as e:
        logger.error(f"Failed to create integrated motivational system: {e}")
        raise