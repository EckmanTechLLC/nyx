#!/usr/bin/env python3
"""
Test script for the Motivational Model system
"""

import sys
import os
import asyncio
import logging
from datetime import datetime, timedelta
from uuid import uuid4

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from database.connection import db_manager
from database.models import MotivationalState, MotivationalTask, ThoughtTree
from core.motivation import (
    MotivationalModelEngine,
    MotivationalStateManager,
    GoalArbitrationEngine,
    SelfInitiatedTaskSpawner,
    MotivationalFeedbackLoop
)
from core.motivation.initializer import MotivationalModelInitializer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MotivationalModelTester:
    """Comprehensive test suite for the motivational model"""
    
    def __init__(self):
        self.db_manager = db_manager
        self.initializer = MotivationalModelInitializer()
        self.test_results = {}

    async def run_all_tests(self):
        """Run all motivational model tests"""
        logger.info("Starting Motivational Model test suite...")
        
        tests = [
            ("Database Setup", self.test_database_setup),
            ("State Management", self.test_state_management),
            ("Goal Arbitration", self.test_goal_arbitration),
            ("Task Spawning", self.test_task_spawning),
            ("Feedback Loop", self.test_feedback_loop),
            ("Engine Integration", self.test_engine_integration),
            ("Performance", self.test_performance),
        ]
        
        passed = 0
        failed = 0
        
        for test_name, test_func in tests:
            try:
                logger.info(f"\n{'='*50}")
                logger.info(f"Running test: {test_name}")
                logger.info('='*50)
                
                await test_func()
                logger.info(f"✓ {test_name} PASSED")
                self.test_results[test_name] = "PASSED"
                passed += 1
                
            except Exception as e:
                logger.error(f"✗ {test_name} FAILED: {e}")
                self.test_results[test_name] = f"FAILED: {e}"
                failed += 1
        
        # Print summary
        logger.info(f"\n{'='*50}")
        logger.info(f"TEST SUMMARY")
        logger.info('='*50)
        logger.info(f"Total tests: {len(tests)}")
        logger.info(f"Passed: {passed}")
        logger.info(f"Failed: {failed}")
        
        if failed == 0:
            logger.info("🎉 ALL TESTS PASSED!")
        else:
            logger.error(f"❌ {failed} tests failed")
        
        return failed == 0

    async def test_database_setup(self):
        """Test database schema and initial setup"""
        async with self.db_manager.get_async_session() as session:
            # Test database connection
            from sqlalchemy import text
            await session.execute(text("SELECT 1"))
            
            # Initialize default states
            state_manager = MotivationalStateManager()
            await state_manager.initialize_default_states(session)
            
            # Verify states were created
            states = await state_manager.get_active_states(session)
            assert len(states) >= 6, f"Expected at least 6 default states, got {len(states)}"
            
            # Verify specific motivation types exist
            expected_types = [
                'resolve_unfinished_tasks', 
                'refine_low_confidence',
                'explore_recent_failure',
                'maximize_coverage',
                'revisit_old_thoughts',
                'idle_exploration'
            ]
            
            state_types = {state.motivation_type for state in states}
            for expected_type in expected_types:
                assert expected_type in state_types, f"Missing motivation type: {expected_type}"
            
            logger.info(f"✓ Created {len(states)} default motivational states")

    async def test_state_management(self):
        """Test motivational state management operations"""
        async with self.db_manager.get_async_session() as session:
            state_manager = MotivationalStateManager()
            
            # Test getting a specific state
            state = await state_manager.get_state_by_type(session, 'idle_exploration')
            assert state is not None, "Could not retrieve idle_exploration state"
            assert state.motivation_type == 'idle_exploration'
            
            original_urgency = state.urgency
            original_satisfaction = state.satisfaction
            
            # Test boosting motivation
            await state_manager.boost_motivation(
                session, 
                'idle_exploration', 
                0.3,
                {'test': 'boost_test'}
            )
            await session.commit()
            
            # Verify boost was applied - refresh the session to get updated values
            await session.refresh(state)
            assert state.urgency > original_urgency, "Urgency was not boosted"
            
            # Test updating satisfaction
            await state_manager.update_satisfaction(
                session,
                'idle_exploration',
                0.2,
                success=True
            )
            
            # Verify satisfaction was updated
            updated_state2 = await state_manager.get_state_by_type(session, 'idle_exploration')
            assert updated_state2.satisfaction > original_satisfaction, "Satisfaction was not updated"
            assert updated_state2.success_count > 0, "Success count not incremented"
            
            # Test decay
            await state_manager.apply_decay_to_all(session)
            
            # Test arbitration score calculation
            score = await state_manager.calculate_arbitration_score(updated_state2)
            assert 0.0 <= score <= 1.0, f"Arbitration score out of bounds: {score}"
            
            await session.commit()
            logger.info("✓ State management operations working correctly")

    async def test_goal_arbitration(self):
        """Test goal arbitration logic"""
        async with self.db_manager.get_async_session() as session:
            arbitration_engine = GoalArbitrationEngine()
            state_manager = MotivationalStateManager()
            
            # Boost multiple motivations to different levels
            await state_manager.boost_motivation(session, 'idle_exploration', 0.6)
            await state_manager.boost_motivation(session, 'maximize_coverage', 0.4)
            await state_manager.boost_motivation(session, 'resolve_unfinished_tasks', 0.8)
            
            # Test arbitration with different parameters
            selected = await arbitration_engine.arbitrate_goals(
                session,
                max_tasks=2,
                min_threshold=0.3
            )
            
            assert len(selected) <= 2, f"Too many tasks selected: {len(selected)}"
            
            if selected:
                # Verify highest urgency was selected first
                urgencies = [state.urgency for state in selected]
                assert urgencies == sorted(urgencies, reverse=True), "Selection not ordered by urgency"
            
            # Test context evaluation
            if selected:
                context = await arbitration_engine.evaluate_motivation_context(
                    session, 
                    selected[0]
                )
                assert 'motivation_type' in context, "Context missing motivation_type"
                assert 'current_urgency' in context, "Context missing current_urgency"
            
            await session.commit()
            logger.info(f"✓ Goal arbitration selected {len(selected)} tasks correctly")

    async def test_task_spawning(self):
        """Test task spawning functionality"""
        async with self.db_manager.get_async_session() as session:
            spawner = SelfInitiatedTaskSpawner()
            state_manager = MotivationalStateManager()
            
            # Get a motivation to spawn task for
            state = await state_manager.get_state_by_type(session, 'idle_exploration')
            assert state is not None
            
            # Spawn a task
            task = await spawner.spawn_task(session, state)
            assert task is not None, "Failed to spawn task"
            assert task.generated_prompt is not None, "Task has no generated prompt"
            assert len(task.generated_prompt) > 10, "Generated prompt too short"
            assert task.status in ['generated', 'queued'], f"Invalid initial status: {task.status}"
            
            # Test task status update
            await spawner.update_task_status(
                session,
                str(task.id),
                'active',
                metadata={'test': 'status_update'}
            )
            
            # Get pending tasks
            pending = await spawner.get_pending_tasks(session)
            # Note: task might not be pending if status was changed to 'active'
            
            await session.commit()
            logger.info("✓ Task spawning working correctly")

    async def test_feedback_loop(self):
        """Test motivational feedback loop"""
        async with self.db_manager.get_async_session() as session:
            feedback_loop = MotivationalFeedbackLoop()
            spawner = SelfInitiatedTaskSpawner()
            state_manager = MotivationalStateManager()
            
            # Create a test task
            state = await state_manager.get_state_by_type(session, 'maximize_coverage')
            original_satisfaction = state.satisfaction
            
            task = await spawner.spawn_task(session, state)
            await session.flush()
            
            # Process successful outcome
            await feedback_loop.process_outcome(
                session,
                str(task.id),
                success=True,
                outcome_score=0.8,
                metadata={'test': 'feedback_test'}
            )
            
            # Verify feedback was processed
            updated_state = await state_manager.get_state_by_type(session, 'maximize_coverage')
            assert updated_state.satisfaction != original_satisfaction, "Satisfaction not updated by feedback"
            assert updated_state.total_attempts > 0, "Attempt count not updated"
            
            # Test feedback summary
            summary = await feedback_loop.get_feedback_summary(session, days=1)
            assert 'total_tasks' in summary, "Summary missing total_tasks"
            
            await session.commit()
            logger.info("✓ Feedback loop processing correctly")

    async def test_engine_integration(self):
        """Test full engine integration"""
        engine = MotivationalModelEngine(
            evaluation_interval=1.0,  # Fast interval for testing
            max_concurrent_motivated_tasks=2,
            min_arbitration_threshold=0.1  # Low threshold for testing
        )
        
        try:
            # Test engine lifecycle
            await engine.start()
            assert engine._running, "Engine not marked as running"
            
            # Let it run for a few cycles
            await asyncio.sleep(3)
            
            # Test status
            status = engine.get_status()
            assert status['running'] is True, "Status not showing running"
            
            # Test manual outcome processing
            async with self.db_manager.get_async_session() as session:
                # Create a test task for outcome processing
                spawner = SelfInitiatedTaskSpawner()
                state_manager = MotivationalStateManager()
                
                state = await state_manager.get_state_by_type(session, 'idle_exploration')
                task = await spawner.spawn_task(session, state)
                await session.commit()
            
            # Process outcome through engine
            await engine.process_task_outcome(
                str(task.id),
                success=True,
                outcome_score=0.7,
                metadata={'test': 'engine_outcome'}
            )
            
            await engine.stop()
            assert not engine._running, "Engine still marked as running after stop"
            
            logger.info("✓ Engine integration working correctly")
            
        except Exception as e:
            # Ensure engine is stopped even if test fails
            try:
                await engine.stop()
            except:
                pass
            raise e

    async def test_performance(self):
        """Test performance with multiple operations"""
        import time
        
        start_time = time.time()
        
        async with self.db_manager.get_async_session() as session:
            state_manager = MotivationalStateManager()
            arbitration_engine = GoalArbitrationEngine()
            
            # Perform multiple operations
            for i in range(10):
                await state_manager.boost_motivation(
                    session,
                    'idle_exploration',
                    0.1,
                    {'performance_test': i}
                )
                
                await arbitration_engine.arbitrate_goals(session, max_tasks=1)
            
            await session.commit()
        
        elapsed = time.time() - start_time
        operations_per_second = 20 / elapsed  # 10 boosts + 10 arbitrations
        
        assert operations_per_second > 5, f"Performance too slow: {operations_per_second:.2f} ops/sec"
        
        logger.info(f"✓ Performance test: {operations_per_second:.2f} operations/second")

    async def cleanup(self):
        """Clean up test data"""
        try:
            # Note: In a production system, you might want to preserve some test data
            # or use a separate test database. For now, we'll leave cleanup minimal.
            logger.info("Test cleanup completed")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")


async def main():
    """Main test runner"""
    tester = MotivationalModelTester()
    
    try:
        success = await tester.run_all_tests()
        
        if success:
            logger.info("\n🎉 All motivational model tests passed!")
            return 0
        else:
            logger.error("\n❌ Some tests failed")
            return 1
            
    except Exception as e:
        logger.error(f"Test suite failed with error: {e}")
        return 1
    finally:
        await tester.cleanup()


if __name__ == "__main__":
    exit_code = asyncio.run(main())