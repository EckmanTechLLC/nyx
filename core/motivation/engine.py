"""
MotivationalModelEngine - Core timer-based daemon for evaluating internal state and memory
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional, Any
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from database.connection import db_manager
from database.models import MotivationalState, MotivationalTask, ThoughtTree, Agent, ToolExecution, LLMInteraction
from .states import MotivationalStateManager
from .arbitration import GoalArbitrationEngine
from .spawner import SelfInitiatedTaskSpawner
from .feedback import MotivationalFeedbackLoop

logger = logging.getLogger(__name__)


class MotivationalModelEngine:
    """
    Timer-based daemon that evaluates internal state and memory to generate
    autonomous tasks based on motivations.
    """
    
    def __init__(
        self,
        evaluation_interval: float = 30.0,  # seconds
        max_concurrent_motivated_tasks: int = 3,
        min_arbitration_threshold: float = 0.3,
        safety_enabled: bool = True,
        test_mode: bool = False
    ):
        self.db_manager = db_manager
        self.evaluation_interval = evaluation_interval
        self.max_concurrent_motivated_tasks = max_concurrent_motivated_tasks
        self.min_arbitration_threshold = min_arbitration_threshold
        self.safety_enabled = safety_enabled
        self.test_mode = test_mode
        
        # Components
        self.state_manager = MotivationalStateManager()
        self.arbitration_engine = GoalArbitrationEngine(test_mode=test_mode)
        self.task_spawner = SelfInitiatedTaskSpawner()
        self.feedback_loop = MotivationalFeedbackLoop()
        
        # Control flags
        self._running = False
        self._task = None
        self._startup_time = None
        
        logger.info(f"MotivationalModelEngine initialized with {evaluation_interval}s interval")

    async def start(self):
        """Start the motivational engine daemon"""
        if self._running:
            logger.warning("MotivationalModelEngine already running")
            return
            
        self._running = True
        self._startup_time = datetime.now(timezone.utc)
        self._task = asyncio.create_task(self._run_evaluation_loop())
        logger.info("MotivationalModelEngine daemon started")

    async def stop(self):
        """Stop the motivational engine daemon"""
        if not self._running:
            return
            
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("MotivationalModelEngine daemon stopped")

    async def _run_evaluation_loop(self):
        """Main evaluation loop that runs continuously"""
        try:
            while self._running:
                try:
                    await self._evaluate_and_act()
                    await asyncio.sleep(self.evaluation_interval)
                except Exception as e:
                    logger.error(f"Error in motivation evaluation cycle: {e}", exc_info=True)
                    # Continue running despite errors, but with exponential backoff
                    await asyncio.sleep(min(self.evaluation_interval * 2, 300))
        except asyncio.CancelledError:
            logger.info("Motivational evaluation loop cancelled")
        except Exception as e:
            logger.error(f"Fatal error in motivational evaluation loop: {e}", exc_info=True)

    async def _evaluate_and_act(self):
        """Single evaluation cycle: update states, arbitrate goals, spawn tasks"""
        start_time = time.time()
        
        async with self.db_manager.get_async_session() as session:
            try:
                # 1. Update motivational states based on system state
                await self._update_motivational_states(session)
                
                # 2. Check if we can spawn new motivated tasks
                if not await self._can_spawn_new_tasks(session):
                    logger.debug("Cannot spawn new tasks - at max capacity")
                    return
                
                # 3. Arbitrate goals to select top motivations
                system_context = {
                    'startup_time': self._startup_time,
                    'testing_mode': self.test_mode,
                    'manual_trigger': False  # This would be True for manual task creation
                }
                
                selected_motivations = await self.arbitration_engine.arbitrate_goals(
                    session, 
                    max_tasks=self.max_concurrent_motivated_tasks,
                    min_threshold=self.min_arbitration_threshold,
                    system_context=system_context
                )
                
                if not selected_motivations:
                    logger.debug("No motivations selected for task spawning")
                    return
                
                # 4. Spawn tasks for selected motivations
                spawned_tasks = []
                for motivation in selected_motivations:
                    try:
                        task = await self.task_spawner.spawn_task(session, motivation)
                        if task:
                            spawned_tasks.append(task)
                            logger.info(f"Spawned motivated task: {motivation.motivation_type}")
                    except Exception as e:
                        logger.error(f"Failed to spawn task for motivation {motivation.motivation_type}: {e}")
                
                await session.commit()
                
                # 5. Log evaluation cycle metrics
                cycle_time = time.time() - start_time
                logger.debug(f"Motivation evaluation cycle completed in {cycle_time:.2f}s, spawned {len(spawned_tasks)} tasks")
                
            except Exception as e:
                await session.rollback()
                logger.error(f"Error in motivation evaluation cycle: {e}", exc_info=True)

    async def _update_motivational_states(self, session: AsyncSession):
        """Update all motivational states based on current system conditions"""
        try:
            # Apply decay to all active motivations
            await self.state_manager.apply_decay_to_all(session)
            
            # Check conditions for each motivation type and update urgency
            await self._check_resolve_unfinished_tasks(session)
            await self._check_refine_low_confidence(session)
            await self._check_explore_recent_failure(session)
            await self._check_maximize_coverage(session)
            await self._check_revisit_old_thoughts(session)
            await self._check_idle_exploration(session)
            
        except Exception as e:
            logger.error(f"Error updating motivational states: {e}")

    async def _check_resolve_unfinished_tasks(self, session: AsyncSession):
        """Check for unfinished tasks and boost resolve_unfinished_tasks motivation"""
        try:
            # Count failed/cancelled tasks in last 24 hours
            since = datetime.now(timezone.utc) - timedelta(hours=24)
            failed_tasks = await session.execute(
                select(func.count(ThoughtTree.id))
                .where(and_(
                    ThoughtTree.status.in_(['failed', 'cancelled']),
                    ThoughtTree.updated_at >= since
                ))
            )
            failed_count = failed_tasks.scalar() or 0
            
            if failed_count > 0:
                urgency_boost = min(0.1 * failed_count, 0.5)  # Cap at 0.5
                await self.state_manager.boost_motivation(
                    session, 
                    'resolve_unfinished_tasks',
                    urgency_boost,
                    {'failed_tasks_24h': failed_count}
                )
                
        except Exception as e:
            logger.error(f"Error checking unfinished tasks: {e}")

    async def _check_refine_low_confidence(self, session: AsyncSession):
        """Check for low confidence outputs and boost refine_low_confidence motivation"""
        try:
            # Look for recent LLM interactions with low confidence indicators
            since = datetime.now(timezone.utc) - timedelta(hours=6)
            low_confidence = await session.execute(
                select(func.count(LLMInteraction.id))
                .where(and_(
                    LLMInteraction.request_timestamp >= since,
                    LLMInteraction.response_text.like('%low confidence%') |
                    LLMInteraction.response_text.like('%uncertain%') |
                    LLMInteraction.response_text.like('%not sure%')
                ))
            )
            low_conf_count = low_confidence.scalar() or 0
            
            if low_conf_count > 0:
                urgency_boost = min(0.05 * low_conf_count, 0.3)
                await self.state_manager.boost_motivation(
                    session,
                    'refine_low_confidence', 
                    urgency_boost,
                    {'low_confidence_outputs_6h': low_conf_count}
                )
                
        except Exception as e:
            logger.error(f"Error checking low confidence outputs: {e}")

    async def _check_explore_recent_failure(self, session: AsyncSession):
        """Check for recent tool failures and boost explore_recent_failure motivation"""
        try:
            # Count failed tool executions in last hour
            since = datetime.now(timezone.utc) - timedelta(hours=1)
            failed_tools = await session.execute(
                select(ToolExecution.tool_name, func.count(ToolExecution.id).label('failure_count'))
                .where(and_(
                    ToolExecution.success == False,
                    ToolExecution.started_at >= since
                ))
                .group_by(ToolExecution.tool_name)
                .having(func.count(ToolExecution.id) >= 3)  # 3+ failures
            )
            failed_tools_data = failed_tools.fetchall()
            
            if failed_tools_data:
                total_failures = sum(row.failure_count for row in failed_tools_data)
                urgency_boost = min(0.1 * len(failed_tools_data), 0.4)
                await self.state_manager.boost_motivation(
                    session,
                    'explore_recent_failure',
                    urgency_boost,
                    {'failed_tools': {row.tool_name: row.failure_count for row in failed_tools_data}}
                )
                
        except Exception as e:
            logger.error(f"Error checking recent tool failures: {e}")

    async def _check_maximize_coverage(self, session: AsyncSession):
        """Check for underexplored task domains and boost maximize_coverage motivation"""
        try:
            # This is a simplified check - could be made more sophisticated
            # Check if we have very few recent successful tasks
            since = datetime.now(timezone.utc) - timedelta(hours=12)
            successful_tasks = await session.execute(
                select(func.count(ThoughtTree.id))
                .where(and_(
                    ThoughtTree.status == 'completed',
                    ThoughtTree.completed_at >= since
                ))
            )
            success_count = successful_tasks.scalar() or 0
            
            # If very few successful tasks recently, boost coverage motivation
            if success_count < 3:
                urgency_boost = 0.2
                await self.state_manager.boost_motivation(
                    session,
                    'maximize_coverage',
                    urgency_boost,
                    {'successful_tasks_12h': success_count}
                )
                
        except Exception as e:
            logger.error(f"Error checking task coverage: {e}")

    async def _check_revisit_old_thoughts(self, session: AsyncSession):
        """Check for old unvisited thoughts and boost revisit_old_thoughts motivation"""
        try:
            # Look for thought trees that haven't been updated in 48+ hours
            old_threshold = datetime.now(timezone.utc) - timedelta(hours=48)
            old_thoughts = await session.execute(
                select(func.count(ThoughtTree.id))
                .where(and_(
                    ThoughtTree.updated_at <= old_threshold,
                    ThoughtTree.status.in_(['pending', 'in_progress'])
                ))
            )
            old_count = old_thoughts.scalar() or 0
            
            if old_count > 0:
                urgency_boost = min(0.05 * old_count, 0.25)
                await self.state_manager.boost_motivation(
                    session,
                    'revisit_old_thoughts',
                    urgency_boost,
                    {'old_thoughts_count': old_count}
                )
                
        except Exception as e:
            logger.error(f"Error checking old thoughts: {e}")

    async def _check_idle_exploration(self, session: AsyncSession):
        """Check for idle state and boost idle_exploration motivation"""
        try:
            # Check if there are very few active agents and recent activity
            since = datetime.now(timezone.utc) - timedelta(minutes=30)
            
            active_agents = await session.execute(
                select(func.count(Agent.id))
                .where(Agent.status.in_(['active', 'waiting']))
            )
            active_count = active_agents.scalar() or 0
            
            recent_activity = await session.execute(
                select(func.count(ThoughtTree.id))
                .where(ThoughtTree.updated_at >= since)
            )
            recent_count = recent_activity.scalar() or 0
            
            # If low activity, boost idle exploration
            if active_count <= 1 and recent_count <= 2:
                urgency_boost = 0.3
                await self.state_manager.boost_motivation(
                    session,
                    'idle_exploration',
                    urgency_boost,
                    {
                        'active_agents': active_count,
                        'recent_activity_30min': recent_count
                    }
                )
                
        except Exception as e:
            logger.error(f"Error checking idle state: {e}")

    async def _can_spawn_new_tasks(self, session: AsyncSession) -> bool:
        """Check if we can spawn new motivated tasks based on current load"""
        try:
            # Count currently active motivated tasks
            active_tasks = await session.execute(
                select(func.count(MotivationalTask.id))
                .where(MotivationalTask.status.in_(['queued', 'spawned', 'active']))
            )
            active_count = active_tasks.scalar() or 0
            
            return active_count < self.max_concurrent_motivated_tasks
            
        except Exception as e:
            logger.error(f"Error checking task capacity: {e}")
            return False

    async def process_task_outcome(self, task_id: str, success: bool, outcome_score: float, metadata: Optional[Dict[str, Any]] = None):
        """Process the outcome of a motivated task and update satisfaction"""
        async with self.db_manager.get_async_session() as session:
            try:
                await self.feedback_loop.process_outcome(session, task_id, success, outcome_score, metadata)
                await session.commit()
                logger.info(f"Processed outcome for motivated task {task_id}: success={success}, score={outcome_score}")
            except Exception as e:
                await session.rollback()
                logger.error(f"Error processing task outcome for {task_id}: {e}")

    @asynccontextmanager
    async def managed_lifecycle(self):
        """Context manager for managing the engine lifecycle"""
        try:
            await self.start()
            yield self
        finally:
            await self.stop()

    def get_status(self) -> Dict[str, Any]:
        """Get current status of the motivational engine"""
        return {
            'running': self._running,
            'evaluation_interval': self.evaluation_interval,
            'max_concurrent_tasks': self.max_concurrent_motivated_tasks,
            'min_arbitration_threshold': self.min_arbitration_threshold,
            'safety_enabled': self.safety_enabled
        }