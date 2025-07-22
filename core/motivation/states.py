"""
MotivationalStateManager - Manages motivational states and their lifecycle
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional, Any
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_, or_, func
from database.connection import db_manager
from database.models import MotivationalState

logger = logging.getLogger(__name__)


class MotivationalStateManager:
    """
    Manages the lifecycle and state of motivational states including creation,
    updating, decay, and satisfaction tracking.
    """
    
    def __init__(self):
        self.db_manager = db_manager
        
        # Default motivational state configurations
        self.default_states = {
            'resolve_unfinished_tasks': {
                'urgency': 0.0,
                'satisfaction': 0.5,
                'decay_rate': 0.02,
                'boost_factor': 1.2,
                'max_urgency': 0.9,
                'trigger_condition': {
                    'type': 'failed_tasks',
                    'threshold': 1,
                    'time_window_hours': 24
                }
            },
            'refine_low_confidence': {
                'urgency': 0.0,
                'satisfaction': 0.7,
                'decay_rate': 0.05,
                'boost_factor': 1.1,
                'max_urgency': 1.0,
                'trigger_condition': {
                    'type': 'low_confidence_output',
                    'keywords': ['low confidence', 'uncertain', 'not sure'],
                    'time_window_hours': 6
                }
            },
            'explore_recent_failure': {
                'urgency': 0.0,
                'satisfaction': 0.4,
                'decay_rate': 0.1,
                'boost_factor': 1.3,
                'max_urgency': 0.85,
                'trigger_condition': {
                    'type': 'tool_failures',
                    'threshold': 3,
                    'time_window_hours': 1
                }
            },
            'maximize_coverage': {
                'urgency': 0.1,
                'satisfaction': 0.6,
                'decay_rate': 0.01,
                'boost_factor': 1.0,
                'max_urgency': 1.0,
                'trigger_condition': {
                    'type': 'low_activity',
                    'successful_tasks_threshold': 3,
                    'time_window_hours': 12
                }
            },
            'revisit_old_thoughts': {
                'urgency': 0.05,
                'satisfaction': 0.8,
                'decay_rate': 0.03,
                'boost_factor': 1.1,
                'max_urgency': 1.0,
                'trigger_condition': {
                    'type': 'old_thoughts',
                    'age_threshold_hours': 48,
                    'status_filter': ['pending', 'in_progress']
                }
            },
            'idle_exploration': {
                'urgency': 0.0,
                'satisfaction': 0.9,
                'decay_rate': 0.02,
                'boost_factor': 1.5,
                'max_urgency': 1.0,
                'trigger_condition': {
                    'type': 'low_system_activity',
                    'max_active_agents': 1,
                    'max_recent_activity': 2,
                    'time_window_minutes': 30
                }
            }
        }

    async def initialize_default_states(self, session: AsyncSession):
        """Initialize default motivational states if they don't exist"""
        try:
            for motivation_type, config in self.default_states.items():
                # Check if state already exists
                existing = await session.execute(
                    select(MotivationalState)
                    .where(MotivationalState.motivation_type == motivation_type)
                )
                state = existing.scalar_one_or_none()
                
                if state is None:
                    # Create new motivational state
                    new_state = MotivationalState(
                        id=uuid4(),
                        motivation_type=motivation_type,
                        urgency=config['urgency'],
                        satisfaction=config['satisfaction'],
                        decay_rate=config['decay_rate'],
                        boost_factor=config['boost_factor'],
                        max_urgency=config['max_urgency'],
                        trigger_condition=config['trigger_condition'],
                        is_active=True,
                        success_count=0,
                        failure_count=0,
                        total_attempts=0,
                        success_rate=0.0
                    )
                    session.add(new_state)
                    logger.info(f"Created default motivational state: {motivation_type}")
                
            await session.commit()
            
        except Exception as e:
            await session.rollback()
            logger.error(f"Error initializing default motivational states: {e}")
            raise

    async def get_active_states(self, session: AsyncSession) -> List[MotivationalState]:
        """Get all active motivational states"""
        try:
            result = await session.execute(
                select(MotivationalState)
                .where(MotivationalState.is_active == True)
                .order_by(MotivationalState.urgency.desc())
            )
            return result.scalars().all()
            
        except Exception as e:
            logger.error(f"Error retrieving active motivational states: {e}")
            return []

    async def get_state_by_type(self, session: AsyncSession, motivation_type: str) -> Optional[MotivationalState]:
        """Get a specific motivational state by type"""
        try:
            result = await session.execute(
                select(MotivationalState)
                .where(and_(
                    MotivationalState.motivation_type == motivation_type,
                    MotivationalState.is_active == True
                ))
            )
            return result.scalar_one_or_none()
            
        except Exception as e:
            logger.error(f"Error retrieving motivational state {motivation_type}: {e}")
            return None

    async def boost_motivation(
        self, 
        session: AsyncSession, 
        motivation_type: str, 
        urgency_increase: float,
        trigger_metadata: Optional[Dict[str, Any]] = None
    ):
        """Boost the urgency of a specific motivation and update trigger metadata"""
        try:
            state = await self.get_state_by_type(session, motivation_type)
            if state is None:
                logger.warning(f"Cannot boost non-existent motivation: {motivation_type}")
                return
            
            # Calculate new urgency with boost factor applied
            boost_amount = urgency_increase * state.boost_factor
            new_urgency = min(state.urgency + boost_amount, state.max_urgency)
            
            # Update the state
            update_data = {
                'urgency': new_urgency,
                'last_triggered_at': datetime.now(timezone.utc),
                'updated_at': datetime.now(timezone.utc)
            }
            
            # Update metadata if provided
            if trigger_metadata:
                current_metadata = state.metadata_ or {}
                current_metadata.update({
                    'last_trigger': trigger_metadata,
                    'last_boost_amount': boost_amount
                })
                update_data['metadata_'] = current_metadata
            
            await session.execute(
                update(MotivationalState)
                .where(MotivationalState.id == state.id)
                .values(**update_data)
            )
            
            logger.debug(f"Boosted {motivation_type} urgency from {state.urgency:.3f} to {new_urgency:.3f}")
            
        except Exception as e:
            logger.error(f"Error boosting motivation {motivation_type}: {e}")

    async def update_satisfaction(
        self, 
        session: AsyncSession, 
        motivation_type: str, 
        satisfaction_change: float,
        success: bool = True
    ):
        """Update satisfaction level and success metrics for a motivation"""
        try:
            state = await self.get_state_by_type(session, motivation_type)
            if state is None:
                logger.warning(f"Cannot update satisfaction for non-existent motivation: {motivation_type}")
                return
            
            # Update satisfaction (clamped between 0.0 and 1.0)
            new_satisfaction = max(0.0, min(1.0, state.satisfaction + satisfaction_change))
            
            # Update success metrics
            new_total_attempts = state.total_attempts + 1
            new_success_count = state.success_count + (1 if success else 0)
            new_failure_count = state.failure_count + (0 if success else 1)
            new_success_rate = new_success_count / new_total_attempts if new_total_attempts > 0 else 0.0
            
            await session.execute(
                update(MotivationalState)
                .where(MotivationalState.id == state.id)
                .values(
                    satisfaction=new_satisfaction,
                    last_satisfied_at=datetime.now(timezone.utc) if satisfaction_change > 0 else state.last_satisfied_at,
                    success_count=new_success_count,
                    failure_count=new_failure_count,
                    total_attempts=new_total_attempts,
                    success_rate=new_success_rate,
                    updated_at=datetime.now(timezone.utc)
                )
            )
            
            logger.debug(
                f"Updated {motivation_type} satisfaction: {state.satisfaction:.3f} -> {new_satisfaction:.3f}, "
                f"success_rate: {state.success_rate:.3f} -> {new_success_rate:.3f}"
            )
            
        except Exception as e:
            logger.error(f"Error updating satisfaction for {motivation_type}: {e}")

    async def apply_decay_to_all(self, session: AsyncSession):
        """Apply decay to urgency of all active motivational states"""
        try:
            # Get all active states
            active_states = await self.get_active_states(session)
            
            for state in active_states:
                if state.urgency > 0.0:
                    # Apply decay
                    new_urgency = max(0.0, state.urgency - state.decay_rate)
                    
                    await session.execute(
                        update(MotivationalState)
                        .where(MotivationalState.id == state.id)
                        .values(
                            urgency=new_urgency,
                            updated_at=datetime.now(timezone.utc)
                        )
                    )
            
            logger.debug(f"Applied decay to {len([s for s in active_states if s.urgency > 0.0])} motivational states")
            
        except Exception as e:
            logger.error(f"Error applying decay to motivational states: {e}")

    async def calculate_arbitration_score(self, state: MotivationalState) -> float:
        """Calculate arbitration score for a motivational state"""
        try:
            # Base formula: urgency × (1 - satisfaction) × success_rate_factor
            inverse_satisfaction = 1.0 - state.satisfaction
            
            # Success rate factor - penalize states with very low success rates
            success_rate_factor = max(0.5, state.success_rate) if state.total_attempts >= 3 else 1.0
            
            # Time factor - boost states that haven't been triggered recently
            time_factor = 1.0
            if state.last_triggered_at:
                hours_since_trigger = (datetime.now(timezone.utc) - state.last_triggered_at).total_seconds() / 3600
                # Boost score for states not triggered in a while (gradual increase over 24h)
                time_factor = min(1.5, 1.0 + (hours_since_trigger / 24.0) * 0.5)
            
            score = state.urgency * inverse_satisfaction * success_rate_factor * time_factor
            
            return max(0.0, min(1.0, score))  # Clamp to [0, 1]
            
        except Exception as e:
            logger.error(f"Error calculating arbitration score for {state.motivation_type}: {e}")
            return 0.0

    async def deactivate_state(self, session: AsyncSession, motivation_type: str):
        """Deactivate a motivational state"""
        try:
            await session.execute(
                update(MotivationalState)
                .where(MotivationalState.motivation_type == motivation_type)
                .values(
                    is_active=False,
                    updated_at=datetime.now(timezone.utc)
                )
            )
            logger.info(f"Deactivated motivational state: {motivation_type}")
            
        except Exception as e:
            logger.error(f"Error deactivating motivational state {motivation_type}: {e}")

    async def reactivate_state(self, session: AsyncSession, motivation_type: str):
        """Reactivate a motivational state"""
        try:
            await session.execute(
                update(MotivationalState)
                .where(MotivationalState.motivation_type == motivation_type)
                .values(
                    is_active=True,
                    updated_at=datetime.now(timezone.utc)
                )
            )
            logger.info(f"Reactivated motivational state: {motivation_type}")
            
        except Exception as e:
            logger.error(f"Error reactivating motivational state {motivation_type}: {e}")

    async def get_motivation_summary(self, session: AsyncSession) -> Dict[str, Any]:
        """Get a summary of all motivational states for debugging/monitoring"""
        try:
            states = await self.get_active_states(session)
            
            summary = {
                'total_active_states': len(states),
                'states': []
            }
            
            for state in states:
                arbitration_score = await self.calculate_arbitration_score(state)
                
                state_info = {
                    'motivation_type': state.motivation_type,
                    'urgency': round(state.urgency, 3),
                    'satisfaction': round(state.satisfaction, 3),
                    'arbitration_score': round(arbitration_score, 3),
                    'success_rate': round(state.success_rate, 3),
                    'total_attempts': state.total_attempts,
                    'last_triggered': state.last_triggered_at.isoformat() if state.last_triggered_at else None,
                    'last_satisfied': state.last_satisfied_at.isoformat() if state.last_satisfied_at else None
                }
                summary['states'].append(state_info)
            
            return summary
            
        except Exception as e:
            logger.error(f"Error generating motivation summary: {e}")
            return {'error': str(e)}