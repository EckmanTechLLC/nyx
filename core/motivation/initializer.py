"""
Motivational Model Initializer - Sets up initial motivational states and integrates with orchestrator
"""

import asyncio
import logging
from typing import Optional

from database.connection import db_manager
from database.models import MotivationalState
from .states import MotivationalStateManager
from .engine import MotivationalModelEngine

logger = logging.getLogger(__name__)


class MotivationalModelInitializer:
    """
    Initializes the motivational model system and integrates it with the existing
    NYX architecture.
    """
    
    def __init__(self):
        self.db_manager = db_manager
        self.state_manager = MotivationalStateManager()

    async def initialize_system(
        self, 
        create_default_states: bool = True,
        start_engine: bool = False
    ) -> Optional[MotivationalModelEngine]:
        """
        Initialize the complete motivational model system
        
        Args:
            create_default_states: Whether to create default motivational states
            start_engine: Whether to start the motivational engine daemon
            
        Returns:
            MotivationalModelEngine instance if start_engine=True, else None
        """
        try:
            logger.info("Initializing Motivational Model system...")
            
            # Step 1: Initialize database tables (migration should be run first)
            if create_default_states:
                await self._create_default_states()
            
            # Step 2: Validate system prerequisites
            await self._validate_prerequisites()
            
            # Step 3: Initialize engine if requested
            engine = None
            if start_engine:
                engine = await self._initialize_engine()
            
            logger.info("Motivational Model system initialization complete")
            return engine
            
        except Exception as e:
            logger.error(f"Error initializing Motivational Model system: {e}")
            raise

    async def _create_default_states(self):
        """Create default motivational states in the database"""
        try:
            async with self.db_manager.get_async_session() as session:
                await self.state_manager.initialize_default_states(session)
                logger.info("Default motivational states created successfully")
        except Exception as e:
            logger.error(f"Error creating default motivational states: {e}")
            raise

    async def _validate_prerequisites(self):
        """Validate that all system prerequisites are met"""
        try:
            # Check database connectivity
            async with self.db_manager.get_async_session() as session:
                # Verify motivational tables exist and have data
                from sqlalchemy import select, func
                
                state_count = await session.execute(
                    select(func.count(MotivationalState.id))
                    .where(MotivationalState.is_active == True)
                )
                active_states = state_count.scalar() or 0
                
                if active_states == 0:
                    raise RuntimeError("No active motivational states found. Run initialization with create_default_states=True")
                
                logger.info(f"Found {active_states} active motivational states")
                
                # TODO: Add checks for orchestrator integration points
                # - Verify orchestrator classes are available
                # - Check that necessary agent types are registered
                # - Validate tool system is operational
                
        except Exception as e:
            logger.error(f"Prerequisites validation failed: {e}")
            raise

    async def _initialize_engine(self) -> MotivationalModelEngine:
        """Initialize and start the motivational engine"""
        try:
            # Create engine with default configuration
            # These parameters could be loaded from system configuration
            engine = MotivationalModelEngine(
                evaluation_interval=30.0,  # 30 seconds between evaluations
                max_concurrent_motivated_tasks=3,
                min_arbitration_threshold=0.3,
                safety_enabled=True
            )
            
            # Start the engine daemon
            await engine.start()
            
            logger.info("Motivational engine started successfully")
            return engine
            
        except Exception as e:
            logger.error(f"Error initializing motivational engine: {e}")
            raise

    async def create_test_scenarios(self):
        """Create test scenarios to validate the motivational system"""
        try:
            async with self.db_manager.get_async_session() as session:
                # Boost some motivations to trigger immediate activity
                await self.state_manager.boost_motivation(
                    session,
                    'idle_exploration',
                    0.5,
                    {'test_scenario': 'initialization_test'}
                )
                
                await self.state_manager.boost_motivation(
                    session,
                    'maximize_coverage', 
                    0.4,
                    {'test_scenario': 'coverage_test'}
                )
                
                await session.commit()
                logger.info("Created test scenarios for motivational validation")
                
        except Exception as e:
            logger.error(f"Error creating test scenarios: {e}")

    async def get_system_status(self) -> dict:
        """Get current status of the motivational system"""
        try:
            async with self.db_manager.get_async_session() as session:
                # Get motivation summary
                motivation_summary = await self.state_manager.get_motivation_summary(session)
                
                # Get task statistics
                from sqlalchemy import select, func, desc
                from database.models import MotivationalTask
                from datetime import datetime, timedelta
                
                # Recent task counts
                since_24h = datetime.now(timezone.utc) - timedelta(hours=24)
                recent_tasks = await session.execute(
                    select(
                        MotivationalTask.status,
                        func.count(MotivationalTask.id).label('count')
                    )
                    .where(MotivationalTask.spawned_at >= since_24h)
                    .group_by(MotivationalTask.status)
                )
                
                task_counts = {row.status: row.count for row in recent_tasks}
                
                return {
                    'status': 'operational',
                    'motivation_summary': motivation_summary,
                    'task_counts_24h': task_counts,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
                
        except Exception as e:
            logger.error(f"Error getting system status: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }


# Convenience functions for common operations
async def quick_init_motivational_system(
    start_engine: bool = True
) -> Optional[MotivationalModelEngine]:
    """Quick initialization of the motivational system with defaults"""
    initializer = MotivationalModelInitializer()
    return await initializer.initialize_system(
        create_default_states=True,
        start_engine=start_engine
    )


async def create_motivational_test_environment():
    """Create a test environment with boosted motivations for validation"""
    initializer = MotivationalModelInitializer()
    await initializer.initialize_system(create_default_states=True, start_engine=False)
    await initializer.create_test_scenarios()
    return initializer