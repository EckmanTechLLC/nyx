"""
SelfInitiatedTaskSpawner - Routes motivation-driven prompts into recursive architecture
"""

import logging
from typing import Optional, Dict, Any
from uuid import uuid4
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from database.connection import db_manager
from database.models import MotivationalState, MotivationalTask, ThoughtTree
from .arbitration import GoalArbitrationEngine

logger = logging.getLogger(__name__)


class SelfInitiatedTaskSpawner:
    """
    Converts selected motivations into executable tasks by generating appropriate
    prompts and routing them into NYX's recursive architecture.
    """
    
    def __init__(self):
        self.db_manager = db_manager
        self.arbitration_engine = GoalArbitrationEngine()
        
        # Prompt templates for different motivation types
        self.prompt_templates = {
            'resolve_unfinished_tasks': self._generate_resolve_unfinished_prompt,
            'refine_low_confidence': self._generate_refine_confidence_prompt,
            'explore_recent_failure': self._generate_explore_failure_prompt,
            'maximize_coverage': self._generate_coverage_prompt,
            'revisit_old_thoughts': self._generate_revisit_thoughts_prompt,
            'idle_exploration': self._generate_idle_exploration_prompt
        }

    async def spawn_task(
        self, 
        session: AsyncSession, 
        motivation_state: MotivationalState
    ) -> Optional[MotivationalTask]:
        """
        Spawn a task based on a motivational state
        
        Args:
            session: Database session
            motivation_state: The motivational state to convert to a task
            
        Returns:
            Created MotivationalTask or None if spawning failed
        """
        try:
            # Get context for the motivation
            context = await self.arbitration_engine.evaluate_motivation_context(
                session, motivation_state
            )
            
            # Generate appropriate prompt based on motivation type
            prompt_generator = self.prompt_templates.get(motivation_state.motivation_type)
            if not prompt_generator:
                logger.error(f"No prompt generator for motivation type: {motivation_state.motivation_type}")
                return None
            
            generated_prompt = await prompt_generator(context)
            if not generated_prompt:
                logger.error(f"Failed to generate prompt for motivation: {motivation_state.motivation_type}")
                return None
            
            # Calculate task priority based on arbitration score
            from .states import MotivationalStateManager
            state_manager = MotivationalStateManager()
            arbitration_score = await state_manager.calculate_arbitration_score(motivation_state)
            
            # Create motivational task record
            task = MotivationalTask(
                id=uuid4(),
                motivational_state_id=motivation_state.id,
                generated_prompt=generated_prompt,
                task_priority=min(arbitration_score, 1.0),  # Ensure it's within [0,1]
                arbitration_score=arbitration_score,
                status='generated',
                context=context
            )
            
            session.add(task)
            await session.flush()  # Get the ID
            
            # TODO: Integrate with NYX orchestrator to actually spawn the task
            # For now, we'll mark it as queued and would need orchestrator integration
            task.status = 'queued'
            
            logger.info(
                f"Spawned motivated task for {motivation_state.motivation_type} "
                f"with priority {task.task_priority:.3f}"
            )
            
            return task
            
        except Exception as e:
            logger.error(f"Error spawning task for motivation {motivation_state.motivation_type}: {e}")
            return None

    async def _generate_resolve_unfinished_prompt(self, context: Dict[str, Any]) -> str:
        """Generate prompt for resolving unfinished tasks"""
        try:
            system_context = context.get('system_context', {})
            failed_tasks = system_context.get('failed_tasks_24h', [])
            
            if not failed_tasks:
                return "Review recent system activity and identify any incomplete or failed tasks that should be revisited and completed."
            
            # Focus on most recent failed task
            latest_failure = failed_tasks[0]
            
            prompt = f"""AUTONOMOUS TASK: Resolve Unfinished Work

I notice there are {len(failed_tasks)} failed or cancelled tasks in the last 24 hours. 
The most recent failure was:

Goal: {latest_failure['goal']}
Status: {latest_failure['status']}
Depth: {latest_failure['depth']}
Failed at: {latest_failure['updated_at']}

Please analyze this failure and either:
1. Retry the task with improved approach
2. Break it down into smaller, more manageable subtasks
3. Identify why it failed and address the root cause
4. Determine if the goal is still relevant and should be pursued

Focus on learning from the failure and improving success probability."""

            return prompt
            
        except Exception as e:
            logger.error(f"Error generating resolve unfinished prompt: {e}")
            return "Review and retry any recently failed or incomplete tasks, learning from previous failures."

    async def _generate_refine_confidence_prompt(self, context: Dict[str, Any]) -> str:
        """Generate prompt for refining low confidence outputs"""
        
        prompt = """AUTONOMOUS TASK: Improve Output Confidence

I've detected outputs or decisions that were marked with low confidence or uncertainty. 

Please:
1. Review recent interactions for uncertainty indicators
2. Identify specific areas where confidence was low
3. Research or analyze these areas more thoroughly
4. Provide more definitive conclusions or recommendations
5. If uncertainty persists, clearly document what additional information is needed

Focus on converting uncertain or tentative responses into confident, well-supported conclusions."""

        return prompt

    async def _generate_explore_failure_prompt(self, context: Dict[str, Any]) -> str:
        """Generate prompt for exploring recent failures"""
        
        prompt = """AUTONOMOUS TASK: Investigate System Failures

I've detected repeated tool failures or execution problems recently.

Please:
1. Analyze recent tool execution logs for failure patterns
2. Identify which tools are failing most frequently
3. Determine root causes of failures (permissions, resources, configuration, etc.)
4. Test alternative approaches or tools for the same objectives
5. Document findings and recommend improvements to prevent future failures

Focus on improving system reliability and finding more robust execution strategies."""

        return prompt

    async def _generate_coverage_prompt(self, context: Dict[str, Any]) -> str:
        """Generate prompt for maximizing task coverage"""
        try:
            system_context = context.get('system_context', {})
            recent_goals = system_context.get('recent_completed_goals', [])
            
            prompt = f"""AUTONOMOUS TASK: Expand Task Coverage

Recent activity analysis shows {len(recent_goals)} completed tasks in the last 12 hours.

Recent completed goals:
{chr(10).join(f"- {goal[:150]}..." if len(goal) > 150 else f"- {goal}" for goal in recent_goals[:5])}

Please:
1. Identify underexplored domains or task types
2. Generate diverse tasks in areas we haven't recently addressed
3. Explore new capabilities or tools that haven't been fully utilized
4. Create experimental or research tasks to expand knowledge
5. Focus on areas that could provide new insights or capabilities

Aim for diversity and exploration rather than repeating similar tasks."""

            return prompt
            
        except Exception as e:
            logger.error(f"Error generating coverage prompt: {e}")
            return "Explore new task domains and capabilities that haven't been recently utilized to maximize system coverage."

    async def _generate_revisit_thoughts_prompt(self, context: Dict[str, Any]) -> str:
        """Generate prompt for revisiting old thoughts"""
        try:
            system_context = context.get('system_context', {})
            old_thoughts = system_context.get('old_thoughts', [])
            
            if not old_thoughts:
                return "Review long-pending tasks and thought processes to identify opportunities for completion or insights."
            
            # Focus on oldest thought
            oldest = old_thoughts[0]
            
            prompt = f"""AUTONOMOUS TASK: Revisit Stale Thoughts

I found {len(old_thoughts)} thoughts that haven't been updated in over 48 hours.

Oldest pending thought:
Goal: {oldest['goal']}
Status: {oldest['status']}
Age: {oldest['age_hours']:.1f} hours
Depth: {oldest['depth']}

Please:
1. Review this long-pending thought and assess its current relevance
2. Determine if it can be completed with current capabilities
3. Look for new insights or approaches that weren't available before
4. Either complete it, break it down further, or decide if it should be abandoned
5. Apply any new learning or context that has developed since it was created

Focus on extracting value from work that has been sitting idle."""

            return prompt
            
        except Exception as e:
            logger.error(f"Error generating revisit thoughts prompt: {e}")
            return "Review and progress long-pending thoughts and tasks that may have been overlooked."

    async def _generate_idle_exploration_prompt(self, context: Dict[str, Any]) -> str:
        """Generate prompt for idle exploration"""
        try:
            system_context = context.get('system_context', {})
            active_agents = system_context.get('active_agents', 0)
            recent_activity = system_context.get('recent_activity_30min', 0)
            
            prompt = f"""AUTONOMOUS TASK: Idle Exploration & Self-Discovery

Current system state: {active_agents} active agents, {recent_activity} recent activities.

Since the system is relatively idle, please engage in exploratory activities:

1. **Self-Assessment**: Analyze your own capabilities, limitations, and performance patterns
2. **Environment Discovery**: Explore available tools, data sources, or system capabilities
3. **Knowledge Synthesis**: Connect insights from previous tasks in new ways
4. **Experimental Tasks**: Try novel approaches or combinations of existing capabilities
5. **Meta-Learning**: Reflect on learning patterns and identify areas for improvement

Possible specific activities:
- Test edge cases of available tools
- Analyze your own memory and learning patterns
- Explore system configuration or environment details
- Generate creative problem-solving scenarios
- Research topics that came up in recent tasks but weren't fully explored

Focus on discovery, learning, and creative exploration rather than routine tasks."""

            return prompt
            
        except Exception as e:
            logger.error(f"Error generating idle exploration prompt: {e}")
            return "Engage in self-directed exploration and learning activities to discover new insights and capabilities."

    async def update_task_status(
        self, 
        session: AsyncSession, 
        task_id: str, 
        new_status: str,
        thought_tree_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Update the status of a motivational task"""
        try:
            # Get the task
            from sqlalchemy import select, update
            result = await session.execute(
                select(MotivationalTask)
                .where(MotivationalTask.id == task_id)
            )
            task = result.scalar_one_or_none()
            
            if not task:
                logger.error(f"Task {task_id} not found")
                return
            
            # Prepare update data
            update_data = {
                'status': new_status,
            }
            
            if new_status == 'spawned' and not task.started_at:
                update_data['started_at'] = datetime.now(timezone.utc)
            elif new_status in ['completed', 'failed', 'cancelled'] and not task.completed_at:
                update_data['completed_at'] = datetime.now(timezone.utc)
            
            if thought_tree_id:
                update_data['thought_tree_id'] = thought_tree_id
            
            if metadata:
                current_context = task.context or {}
                current_context.update(metadata)
                update_data['context'] = current_context
            
            # Update the task
            await session.execute(
                update(MotivationalTask)
                .where(MotivationalTask.id == task_id)
                .values(**update_data)
            )
            
            logger.info(f"Updated task {task_id} status to {new_status}")
            
        except Exception as e:
            logger.error(f"Error updating task status for {task_id}: {e}")

    async def get_pending_tasks(self, session: AsyncSession, limit: int = 10) -> list[MotivationalTask]:
        """Get pending motivational tasks ready for execution"""
        try:
            from sqlalchemy import select, desc
            from sqlalchemy.orm import selectinload
            result = await session.execute(
                select(MotivationalTask)
                .options(selectinload(MotivationalTask.motivational_state))  # EAGER LOAD relationships
                .where(MotivationalTask.status == 'queued')
                .order_by(desc(MotivationalTask.task_priority))
                .limit(limit)
            )
            
            return result.scalars().all()
            
        except Exception as e:
            logger.error(f"Error getting pending tasks: {e}")
            return []