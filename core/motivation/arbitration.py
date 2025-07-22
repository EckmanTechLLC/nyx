"""
GoalArbitrationEngine - Converts motivations to executable tasks using reinforcement history
"""

import logging
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, desc
from database.connection import db_manager
from database.models import MotivationalState, MotivationalTask, ThoughtTree, Agent
from .states import MotivationalStateManager

logger = logging.getLogger(__name__)


class GoalArbitrationEngine:
    """
    Arbitrates between competing motivations to select which should be converted
    into executable tasks, based on urgency, satisfaction, and reinforcement history.
    """
    
    def __init__(self, test_mode: bool = False):
        self.db_manager = db_manager
        self.state_manager = MotivationalStateManager()
        self.test_mode = test_mode

    async def arbitrate_goals(
        self, 
        session: AsyncSession, 
        max_tasks: int = 3,
        min_threshold: float = 0.3,
        system_context: Optional[Dict[str, Any]] = None
    ) -> List[MotivationalState]:
        """
        Arbitrate between motivations and select top candidates for task spawning
        
        Args:
            session: Database session
            max_tasks: Maximum number of tasks to select
            min_threshold: Minimum arbitration score to consider
            
        Returns:
            List of selected motivational states to convert to tasks
        """
        try:
            # Get all active motivational states
            active_states = await self.state_manager.get_active_states(session)
            
            if not active_states:
                logger.debug("No active motivational states found")
                return []
            
            # Calculate arbitration scores and filter by threshold
            scored_motivations = []
            for state in active_states:
                score = await self.state_manager.calculate_arbitration_score(state)
                
                if score >= min_threshold:
                    # Additional checks before considering for arbitration
                    if await self._is_eligible_for_spawning(session, state, system_context):
                        scored_motivations.append((state, score))
            
            if not scored_motivations:
                logger.debug(f"No motivations meet threshold {min_threshold}")
                return []
            
            # Sort by arbitration score (descending)
            scored_motivations.sort(key=lambda x: x[1], reverse=True)
            
            # Apply additional arbitration logic
            selected_motivations = await self._apply_arbitration_logic(
                session, 
                scored_motivations, 
                max_tasks
            )
            
            logger.info(
                f"Arbitrated {len(selected_motivations)} motivations from {len(scored_motivations)} candidates"
            )
            
            return selected_motivations
            
        except Exception as e:
            logger.error(f"Error in goal arbitration: {e}")
            return []

    async def _is_eligible_for_spawning(self, session: AsyncSession, state: MotivationalState, system_context: Optional[Dict[str, Any]] = None) -> bool:
        """Check if a motivational state is eligible for task spawning"""
        try:
            # Check if there's already an active task for this motivation
            existing_task = await session.execute(
                select(MotivationalTask)
                .where(and_(
                    MotivationalTask.motivational_state_id == state.id,
                    MotivationalTask.status.in_(['queued', 'spawned', 'active'])
                ))
            )
            
            if existing_task.scalar_one_or_none() is not None:
                logger.debug(f"Motivation {state.motivation_type} already has active task")
                return False
            
            # Check cooldown period - don't spawn tasks too frequently for same motivation
            if not self._should_apply_cooldown(state, system_context):
                logger.debug(f"Cooldown bypassed for {state.motivation_type} due to system context")
            elif state.last_triggered_at:
                cooldown_period = self._get_effective_cooldown_period(state.motivation_type, system_context)
                if datetime.now(timezone.utc) - state.last_triggered_at < cooldown_period:
                    logger.debug(f"Motivation {state.motivation_type} in cooldown period")
                    return False
            
            # Check if motivation has reasonable success rate (after some attempts)
            if state.total_attempts >= 5 and state.success_rate < 0.1:
                logger.debug(f"Motivation {state.motivation_type} has very low success rate ({state.success_rate:.2f})")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking eligibility for {state.motivation_type}: {e}")
            return False

    def _get_cooldown_period(self, motivation_type: str) -> timedelta:
        """Get cooldown period for different motivation types"""
        if self.test_mode:
            # Shorter cooldowns for testing - all under 1 minute
            test_cooldowns = {
                'resolve_unfinished_tasks': timedelta(seconds=10),
                'refine_low_confidence': timedelta(seconds=5),
                'explore_recent_failure': timedelta(seconds=3),
                'maximize_coverage': timedelta(seconds=15),  # Still longest but reasonable for tests
                'revisit_old_thoughts': timedelta(seconds=20),
                'idle_exploration': timedelta(seconds=8)
            }
            return test_cooldowns.get(motivation_type, timedelta(seconds=10))
        else:
            # Production cooldowns
            cooldowns = {
                'resolve_unfinished_tasks': timedelta(minutes=15),
                'refine_low_confidence': timedelta(minutes=10),
                'explore_recent_failure': timedelta(minutes=5),
                'maximize_coverage': timedelta(hours=1),
                'revisit_old_thoughts': timedelta(hours=2),
                'idle_exploration': timedelta(minutes=30)
            }
            return cooldowns.get(motivation_type, timedelta(minutes=15))

    def _should_apply_cooldown(self, state: MotivationalState, system_context: Optional[Dict[str, Any]] = None) -> bool:
        """Determine if cooldown should be applied based on system context"""
        if not system_context:
            return True
            
        # System context based bypasses
        if system_context.get('testing_mode'):
            return False
            
        if system_context.get('manual_trigger'):
            return False
            
        # Check if in startup grace period
        startup_time = system_context.get('startup_time')
        if startup_time and self._is_in_startup_grace_period(startup_time):
            return False
            
        return True

    def _is_in_startup_grace_period(self, startup_time: datetime, grace_minutes: int = 30) -> bool:
        """Check if we're still in the startup grace period"""
        return (datetime.now(timezone.utc) - startup_time).total_seconds() < (grace_minutes * 60)

    def _get_effective_cooldown_period(self, motivation_type: str, system_context: Optional[Dict[str, Any]] = None) -> timedelta:
        """Get effective cooldown period considering system context"""
        base_cooldown = self._get_cooldown_period(motivation_type)
        
        if not system_context:
            return base_cooldown
            
        # Reduce cooldown during startup grace period
        startup_time = system_context.get('startup_time')
        if startup_time and self._is_in_startup_grace_period(startup_time):
            # Use 25% of normal cooldown during startup
            return base_cooldown / 4
            
        return base_cooldown

    async def _apply_arbitration_logic(
        self, 
        session: AsyncSession,
        scored_motivations: List[tuple[MotivationalState, float]], 
        max_tasks: int
    ) -> List[MotivationalState]:
        """Apply additional arbitration logic beyond basic scoring"""
        try:
            selected = []
            
            # Priority 1: High urgency motivations (urgency > 0.7)
            high_urgency = [
                state for state, score in scored_motivations 
                if state.urgency > 0.7 and len(selected) < max_tasks
            ]
            selected.extend(high_urgency[:max_tasks - len(selected)])
            
            if len(selected) >= max_tasks:
                return selected
            
            # Priority 2: Diversify motivation types - don't pick similar motivations
            remaining = [
                (state, score) for state, score in scored_motivations 
                if state not in selected
            ]
            
            # Group motivations by category for diversity
            motivation_categories = {
                'resolve_unfinished_tasks': 'remedial',
                'refine_low_confidence': 'quality',
                'explore_recent_failure': 'remedial',
                'maximize_coverage': 'exploratory',
                'revisit_old_thoughts': 'maintenance',
                'idle_exploration': 'exploratory'
            }
            
            category_selected = set()
            for state, score in remaining:
                if len(selected) >= max_tasks:
                    break
                
                category = motivation_categories.get(state.motivation_type, 'unknown')
                
                # Prefer diversity in categories, but allow same category if score is very high
                if category not in category_selected or score > 0.8:
                    selected.append(state)
                    category_selected.add(category)
            
            # Priority 3: Fill remaining slots with highest scoring motivations
            if len(selected) < max_tasks:
                remaining_states = [
                    state for state, _ in remaining 
                    if state not in selected
                ]
                selected.extend(remaining_states[:max_tasks - len(selected)])
            
            return selected
            
        except Exception as e:
            logger.error(f"Error applying arbitration logic: {e}")
            # Fallback: just return top scoring motivations
            return [state for state, _ in scored_motivations[:max_tasks]]

    async def evaluate_motivation_context(
        self, 
        session: AsyncSession, 
        state: MotivationalState
    ) -> Dict[str, Any]:
        """Evaluate additional context for a motivation to inform task generation"""
        try:
            context = {
                'motivation_type': state.motivation_type,
                'current_urgency': state.urgency,
                'current_satisfaction': state.satisfaction,
                'success_history': {
                    'success_rate': state.success_rate,
                    'total_attempts': state.total_attempts,
                    'recent_success': state.success_count > 0
                },
                'trigger_condition': state.trigger_condition,
                'last_triggered': state.last_triggered_at.isoformat() if state.last_triggered_at else None,
                'system_context': {}
            }
            
            # Add specific context based on motivation type
            if state.motivation_type == 'resolve_unfinished_tasks':
                context['system_context'] = await self._get_unfinished_task_context(session)
            elif state.motivation_type == 'refine_low_confidence':
                context['system_context'] = await self._get_low_confidence_context(session)
            elif state.motivation_type == 'explore_recent_failure':
                context['system_context'] = await self._get_failure_context(session)
            elif state.motivation_type == 'maximize_coverage':
                context['system_context'] = await self._get_coverage_context(session)
            elif state.motivation_type == 'revisit_old_thoughts':
                context['system_context'] = await self._get_old_thoughts_context(session)
            elif state.motivation_type == 'idle_exploration':
                context['system_context'] = await self._get_idle_context(session)
            
            return context
            
        except Exception as e:
            logger.error(f"Error evaluating motivation context for {state.motivation_type}: {e}")
            return {
                'motivation_type': state.motivation_type,
                'error': str(e)
            }

    async def _get_unfinished_task_context(self, session: AsyncSession) -> Dict[str, Any]:
        """Get context for unfinished tasks motivation"""
        try:
            # Get recent failed/cancelled tasks
            since = datetime.now(timezone.utc) - timedelta(hours=24)
            failed_tasks = await session.execute(
                select(ThoughtTree)
                .where(and_(
                    ThoughtTree.status.in_(['failed', 'cancelled']),
                    ThoughtTree.updated_at >= since
                ))
                .order_by(desc(ThoughtTree.updated_at))
                .limit(5)
            )
            
            failed_list = []
            for task in failed_tasks.scalars():
                failed_list.append({
                    'goal': task.goal[:200],  # Truncate for context
                    'status': task.status,
                    'depth': task.depth,
                    'updated_at': task.updated_at.isoformat() if task.updated_at else None
                })
            
            return {
                'failed_tasks_24h': failed_list,
                'task_count': len(failed_list)
            }
            
        except Exception as e:
            logger.error(f"Error getting unfinished task context: {e}")
            return {}

    async def _get_low_confidence_context(self, session: AsyncSession) -> Dict[str, Any]:
        """Get context for low confidence outputs motivation"""
        # This would analyze recent LLM interactions for confidence indicators
        # Implementation would depend on how confidence is tracked
        return {
            'context_type': 'low_confidence_analysis',
            'note': 'Context analysis would be implemented based on confidence tracking system'
        }

    async def _get_failure_context(self, session: AsyncSession) -> Dict[str, Any]:
        """Get context for recent failures motivation"""
        # This would analyze recent tool execution failures
        return {
            'context_type': 'failure_analysis',
            'note': 'Context analysis would include recent tool execution patterns'
        }

    async def _get_coverage_context(self, session: AsyncSession) -> Dict[str, Any]:
        """Get context for coverage maximization motivation"""
        try:
            # Analyze recent task domains/types
            since = datetime.now(timezone.utc) - timedelta(hours=12)
            recent_goals = await session.execute(
                select(ThoughtTree.goal)
                .where(and_(
                    ThoughtTree.status == 'completed',
                    ThoughtTree.completed_at >= since
                ))
                .limit(10)
            )
            
            goals = [goal[0] for goal in recent_goals]
            
            return {
                'recent_completed_goals': goals,
                'goal_count': len(goals)
            }
            
        except Exception as e:
            logger.error(f"Error getting coverage context: {e}")
            return {}

    async def _get_old_thoughts_context(self, session: AsyncSession) -> Dict[str, Any]:
        """Get context for old thoughts motivation"""
        try:
            # Find oldest pending/in-progress thoughts
            old_threshold = datetime.now(timezone.utc) - timedelta(hours=48)
            old_thoughts = await session.execute(
                select(ThoughtTree)
                .where(and_(
                    ThoughtTree.updated_at <= old_threshold,
                    ThoughtTree.status.in_(['pending', 'in_progress'])
                ))
                .order_by(ThoughtTree.updated_at)
                .limit(3)
            )
            
            old_list = []
            for thought in old_thoughts.scalars():
                old_list.append({
                    'goal': thought.goal[:200],
                    'status': thought.status,
                    'age_hours': (datetime.now(timezone.utc) - thought.updated_at).total_seconds() / 3600,
                    'depth': thought.depth
                })
            
            return {
                'old_thoughts': old_list,
                'count': len(old_list)
            }
            
        except Exception as e:
            logger.error(f"Error getting old thoughts context: {e}")
            return {}

    async def _get_idle_context(self, session: AsyncSession) -> Dict[str, Any]:
        """Get context for idle exploration motivation"""
        try:
            # Check current system activity level
            active_agents = await session.execute(
                select(func.count(Agent.id))
                .where(Agent.status.in_(['active', 'waiting']))
            )
            active_count = active_agents.scalar() or 0
            
            # Check recent activity
            since = datetime.now(timezone.utc) - timedelta(minutes=30)
            recent_activity = await session.execute(
                select(func.count(ThoughtTree.id))
                .where(ThoughtTree.updated_at >= since)
            )
            recent_count = recent_activity.scalar() or 0
            
            return {
                'active_agents': active_count,
                'recent_activity_30min': recent_count,
                'system_state': 'idle' if active_count <= 1 and recent_count <= 2 else 'active'
            }
            
        except Exception as e:
            logger.error(f"Error getting idle context: {e}")
            return {}