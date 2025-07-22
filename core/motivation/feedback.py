"""
MotivationalFeedbackLoop - Updates satisfaction based on outcomes, stores reinforcement data
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from database.connection import db_manager
from database.models import MotivationalTask, MotivationalState, ThoughtTree
from .states import MotivationalStateManager

logger = logging.getLogger(__name__)


class MotivationalFeedbackLoop:
    """
    Processes task outcomes and updates motivational states based on success/failure,
    creating a feedback loop that reinforces successful motivations and dampens
    unsuccessful ones.
    """
    
    def __init__(self):
        self.db_manager = db_manager
        self.state_manager = MotivationalStateManager()
        
        # Satisfaction adjustment parameters for different outcomes
        self.satisfaction_adjustments = {
            'resolve_unfinished_tasks': {
                'success': 0.3,     # Large positive gain for resolving failures
                'failure': -0.1,    # Moderate negative for failing to resolve
                'partial': 0.1      # Small positive for partial progress
            },
            'refine_low_confidence': {
                'success': 0.25,    # Good gain for improving confidence
                'failure': -0.05,   # Small negative for failing to improve
                'partial': 0.15     # Moderate positive for some improvement
            },
            'explore_recent_failure': {
                'success': 0.4,     # High reward for fixing systemic issues
                'failure': -0.15,   # Moderate penalty for not addressing failures
                'partial': 0.2      # Good reward for partial diagnosis
            },
            'maximize_coverage': {
                'success': 0.2,     # Moderate reward for expanding coverage
                'failure': -0.05,   # Small penalty for failed exploration
                'partial': 0.1      # Small reward for attempting new areas
            },
            'revisit_old_thoughts': {
                'success': 0.35,    # High reward for completing old work
                'failure': -0.1,    # Moderate penalty for still not completing
                'partial': 0.15     # Moderate reward for making progress
            },
            'idle_exploration': {
                'success': 0.15,    # Moderate reward for useful idle discoveries
                'failure': -0.02,   # Very small penalty for failed exploration
                'partial': 0.08     # Small reward for any idle insights
            }
        }

    async def process_outcome(
        self, 
        session: AsyncSession, 
        task_id: str, 
        success: bool, 
        outcome_score: float,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Process the outcome of a motivational task and update the associated
        motivational state's satisfaction and metrics.
        
        Args:
            session: Database session
            task_id: ID of the completed motivational task
            success: Whether the task was successful
            outcome_score: Quality/effectiveness score (0.0 to 1.0)
            metadata: Additional context about the outcome
        """
        try:
            # Get the motivational task
            task_result = await session.execute(
                select(MotivationalTask)
                .where(MotivationalTask.id == task_id)
            )
            task = task_result.scalar_one_or_none()
            
            if not task:
                logger.error(f"Motivational task {task_id} not found")
                return
            
            # Get the associated motivational state
            state_result = await session.execute(
                select(MotivationalState)
                .where(MotivationalState.id == task.motivational_state_id)
            )
            state = state_result.scalar_one_or_none()
            
            if not state:
                logger.error(f"Motivational state for task {task_id} not found")
                return
            
            # Update task outcome
            await self._update_task_outcome(session, task, success, outcome_score, metadata)
            
            # Calculate satisfaction adjustment
            satisfaction_change = await self._calculate_satisfaction_change(
                state, task, success, outcome_score, metadata
            )
            
            # Update motivational state
            await self.state_manager.update_satisfaction(
                session, 
                state.motivation_type, 
                satisfaction_change, 
                success
            )
            
            # Apply reinforcement learning adjustments
            await self._apply_reinforcement_adjustments(session, state, task, success, outcome_score)
            
            logger.info(
                f"Processed outcome for {state.motivation_type}: "
                f"success={success}, score={outcome_score:.2f}, "
                f"satisfaction_change={satisfaction_change:+.3f}"
            )
            
        except Exception as e:
            logger.error(f"Error processing outcome for task {task_id}: {e}")

    async def _update_task_outcome(
        self, 
        session: AsyncSession, 
        task: MotivationalTask,
        success: bool, 
        outcome_score: float, 
        metadata: Optional[Dict[str, Any]]
    ):
        """Update the task record with outcome information"""
        try:
            # Calculate satisfaction gain based on outcome
            # Get motivation type safely without triggering lazy loading
            motivation_type = 'unknown'
            if hasattr(task, 'motivational_state') and task.motivational_state is not None:
                try:
                    motivation_type = task.motivational_state.motivation_type
                except:
                    # If relationship access fails, query separately
                    if task.motivational_state_id:
                        from sqlalchemy import select
                        from database.models import MotivationalState
                        state_result = await session.execute(
                            select(MotivationalState)
                            .where(MotivationalState.id == task.motivational_state_id)
                        )
                        state = state_result.scalar_one_or_none()
                        if state:
                            motivation_type = state.motivation_type
            
            # Determine outcome category
            if success and outcome_score >= 0.7:
                outcome_category = 'success'
            elif success and outcome_score >= 0.3:
                outcome_category = 'partial'
            else:
                outcome_category = 'failure'
            
            # Get base satisfaction adjustment
            adjustments = self.satisfaction_adjustments.get(motivation_type, {})
            base_satisfaction_gain = adjustments.get(outcome_category, 0.0)
            
            # Scale by outcome score
            satisfaction_gain = base_satisfaction_gain * outcome_score if success else base_satisfaction_gain
            
            # Update task context with outcome metadata
            updated_context = task.context or {}
            if metadata:
                updated_context.update(metadata)
            updated_context.update({
                'outcome_processed_at': datetime.now(timezone.utc).isoformat(),
                'outcome_category': outcome_category
            })
            
            # Update the task
            await session.execute(
                update(MotivationalTask)
                .where(MotivationalTask.id == task.id)
                .values(
                    success=success,
                    outcome_score=outcome_score,
                    satisfaction_gain=satisfaction_gain,
                    status='completed' if success else 'failed',
                    completed_at=datetime.now(timezone.utc),
                    context=updated_context
                )
            )
            
        except Exception as e:
            logger.error(f"Error updating task outcome: {e}")

    async def _calculate_satisfaction_change(
        self, 
        state: MotivationalState, 
        task: MotivationalTask,
        success: bool, 
        outcome_score: float, 
        metadata: Optional[Dict[str, Any]]
    ) -> float:
        """Calculate how much satisfaction should change based on the outcome"""
        try:
            # Get base adjustments for this motivation type
            adjustments = self.satisfaction_adjustments.get(state.motivation_type, {
                'success': 0.2, 'failure': -0.1, 'partial': 0.1
            })
            
            # Determine outcome category
            if success and outcome_score >= 0.7:
                base_change = adjustments['success']
            elif success and outcome_score >= 0.3:
                base_change = adjustments.get('partial', adjustments['success'] * 0.5)
            else:
                base_change = adjustments['failure']
            
            # Scale by outcome score and task priority
            score_modifier = outcome_score if success else (1.0 - outcome_score)
            priority_modifier = task.task_priority  # Higher priority tasks have more impact
            
            final_change = base_change * score_modifier * priority_modifier
            
            # Apply diminishing returns if satisfaction is already high
            if state.satisfaction > 0.8 and final_change > 0:
                final_change *= 0.5  # Reduce positive gains when already highly satisfied
            
            # Apply urgency factor - more urgent tasks have bigger impact
            urgency_factor = 0.5 + (state.urgency * 0.5)  # Scale from 0.5 to 1.0
            final_change *= urgency_factor
            
            return final_change
            
        except Exception as e:
            logger.error(f"Error calculating satisfaction change: {e}")
            return 0.0

    async def _apply_reinforcement_adjustments(
        self, 
        session: AsyncSession, 
        state: MotivationalState, 
        task: MotivationalTask,
        success: bool, 
        outcome_score: float
    ):
        """Apply reinforcement learning adjustments to the motivational state"""
        try:
            # Adjust boost factor based on recent performance
            new_boost_factor = state.boost_factor
            
            if success and outcome_score >= 0.7:
                # Successful tasks increase boost factor slightly (up to max of 2.0)
                new_boost_factor = min(2.0, state.boost_factor + 0.05)
            elif not success or outcome_score < 0.3:
                # Failed tasks decrease boost factor (down to min of 0.5)
                new_boost_factor = max(0.5, state.boost_factor - 0.1)
            
            # Adjust decay rate based on effectiveness
            new_decay_rate = state.decay_rate
            
            # If motivation is consistently successful, reduce decay (preserve it longer)
            if state.success_rate > 0.7 and success:
                new_decay_rate = max(0.005, state.decay_rate - 0.005)
            elif state.success_rate < 0.3:
                # If consistently unsuccessful, increase decay (let it fade faster)
                new_decay_rate = min(0.2, state.decay_rate + 0.01)
            
            # Update the state with reinforcement adjustments
            await session.execute(
                update(MotivationalState)
                .where(MotivationalState.id == state.id)
                .values(
                    boost_factor=new_boost_factor,
                    decay_rate=new_decay_rate,
                    updated_at=datetime.now(timezone.utc)
                )
            )
            
            logger.debug(
                f"Applied reinforcement adjustments to {state.motivation_type}: "
                f"boost_factor: {state.boost_factor:.2f} -> {new_boost_factor:.2f}, "
                f"decay_rate: {state.decay_rate:.3f} -> {new_decay_rate:.3f}"
            )
            
        except Exception as e:
            logger.error(f"Error applying reinforcement adjustments: {e}")

    async def process_thought_tree_completion(
        self, 
        session: AsyncSession, 
        thought_tree_id: str,
        success: bool,
        quality_metrics: Optional[Dict[str, float]] = None
    ):
        """
        Process completion of a thought tree that may have originated from a motivation
        """
        try:
            # Find if this thought tree was spawned by a motivational task
            task_result = await session.execute(
                select(MotivationalTask)
                .where(MotivationalTask.thought_tree_id == thought_tree_id)
            )
            task = task_result.scalar_one_or_none()
            
            if task is None:
                # Not a motivated task, nothing to process
                return
            
            # Get thought tree for additional context
            tree_result = await session.execute(
                select(ThoughtTree)
                .where(ThoughtTree.id == thought_tree_id)
            )
            tree = tree_result.scalar_one_or_none()
            
            if tree is None:
                logger.error(f"Thought tree {thought_tree_id} not found")
                return
            
            # Calculate outcome score based on thought tree metrics and quality
            outcome_score = self._calculate_outcome_score_from_tree(tree, quality_metrics)
            
            # Create metadata from thought tree context
            metadata = {
                'thought_tree_goal': tree.goal,
                'tree_depth': tree.depth,
                'tree_status': tree.status,
                'completion_time': tree.completed_at.isoformat() if tree.completed_at else None
            }
            
            if quality_metrics:
                metadata['quality_metrics'] = quality_metrics
            
            # Process the outcome
            await self.process_outcome(
                session, 
                str(task.id), 
                success, 
                outcome_score, 
                metadata
            )
            
        except Exception as e:
            logger.error(f"Error processing thought tree completion {thought_tree_id}: {e}")

    def _calculate_outcome_score_from_tree(
        self, 
        tree: ThoughtTree, 
        quality_metrics: Optional[Dict[str, float]]
    ) -> float:
        """Calculate outcome score based on thought tree completion"""
        try:
            base_score = 0.5  # Default middle score
            
            # Adjust based on tree completion status
            if tree.status == 'completed':
                base_score = 0.8
            elif tree.status == 'failed':
                base_score = 0.2
            elif tree.status == 'cancelled':
                base_score = 0.1
            
            # Adjust based on NYX's internal scoring if available
            if hasattr(tree, 'overall_weight') and tree.overall_weight is not None:
                weight_score = float(tree.overall_weight)
                base_score = (base_score + weight_score) / 2
            
            # Factor in quality metrics if provided
            if quality_metrics:
                avg_quality = sum(quality_metrics.values()) / len(quality_metrics)
                base_score = (base_score + avg_quality) / 2
            
            # Factor in task complexity (deeper trees that complete are more valuable)
            if tree.depth > 0:
                depth_bonus = min(0.1, tree.depth * 0.02)  # Small bonus for depth
                base_score += depth_bonus
            
            return max(0.0, min(1.0, base_score))
            
        except Exception as e:
            logger.error(f"Error calculating outcome score from tree: {e}")
            return 0.5

    async def get_feedback_summary(
        self, 
        session: AsyncSession, 
        motivation_type: Optional[str] = None,
        days: int = 7
    ) -> Dict[str, Any]:
        """Get summary of feedback and outcomes for analysis"""
        try:
            from sqlalchemy import and_, desc, func
            from datetime import timedelta
            
            since = datetime.now(timezone.utc) - timedelta(days=days)
            
            # Build query conditions
            conditions = [MotivationalTask.completed_at >= since]
            if motivation_type:
                # Join with motivational_states to filter by type
                from sqlalchemy.orm import aliased
                ms_alias = aliased(MotivationalState)
                conditions.append(ms_alias.motivation_type == motivation_type)
            
            # Get completed tasks with outcomes
            query = select(
                MotivationalTask,
                MotivationalState.motivation_type
            ).join(
                MotivationalState,
                MotivationalTask.motivational_state_id == MotivationalState.id
            ).where(and_(*conditions)).order_by(desc(MotivationalTask.completed_at))
            
            result = await session.execute(query)
            tasks_with_types = result.all()
            
            # Aggregate statistics
            total_tasks = len(tasks_with_types)
            successful_tasks = sum(1 for task, _ in tasks_with_types if task.success)
            
            outcome_scores = [task.outcome_score for task, _ in tasks_with_types if task.outcome_score is not None]
            avg_outcome_score = sum(outcome_scores) / len(outcome_scores) if outcome_scores else 0.0
            
            satisfaction_gains = [task.satisfaction_gain for task, _ in tasks_with_types if task.satisfaction_gain is not None]
            avg_satisfaction_gain = sum(satisfaction_gains) / len(satisfaction_gains) if satisfaction_gains else 0.0
            
            # Group by motivation type
            by_motivation = {}
            for task, mot_type in tasks_with_types:
                if mot_type not in by_motivation:
                    by_motivation[mot_type] = {
                        'count': 0,
                        'successes': 0,
                        'avg_outcome_score': 0.0,
                        'avg_satisfaction_gain': 0.0
                    }
                
                stats = by_motivation[mot_type]
                stats['count'] += 1
                if task.success:
                    stats['successes'] += 1
                if task.outcome_score is not None:
                    # Running average
                    old_avg = stats['avg_outcome_score']
                    stats['avg_outcome_score'] = (old_avg * (stats['count'] - 1) + task.outcome_score) / stats['count']
                if task.satisfaction_gain is not None:
                    old_avg = stats['avg_satisfaction_gain']
                    stats['avg_satisfaction_gain'] = (old_avg * (stats['count'] - 1) + task.satisfaction_gain) / stats['count']
            
            # Calculate success rates
            for stats in by_motivation.values():
                stats['success_rate'] = stats['successes'] / stats['count'] if stats['count'] > 0 else 0.0
            
            return {
                'period_days': days,
                'total_tasks': total_tasks,
                'successful_tasks': successful_tasks,
                'success_rate': successful_tasks / total_tasks if total_tasks > 0 else 0.0,
                'avg_outcome_score': avg_outcome_score,
                'avg_satisfaction_gain': avg_satisfaction_gain,
                'by_motivation_type': by_motivation,
                'motivation_filter': motivation_type
            }
            
        except Exception as e:
            logger.error(f"Error generating feedback summary: {e}")
            return {'error': str(e)}