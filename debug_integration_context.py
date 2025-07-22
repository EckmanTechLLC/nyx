#!/usr/bin/env python3
"""
Debug script to examine the context differences between working orchestrator init
and the integration test that fails
"""

import asyncio
import logging
import traceback
import threading
from datetime import datetime, timezone

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def debug_integration_context():
    """Debug the context of integration test vs direct orchestrator init"""
    
    print("=" * 80)
    print("🔍 DEBUG: Integration Context vs Direct Context")
    print("=" * 80)
    
    # Test 1: Direct orchestrator initialization (we know this works)
    print("\n📋 Test 1: Direct Orchestrator Initialization (KNOWN WORKING)")
    print("-" * 60)
    
    try:
        from database.connection import db_manager
        from database.models import ThoughtTree
        from core.orchestrator.top_level import TopLevelOrchestrator
        from uuid import uuid4
        
        # Create thought tree
        thought_tree_id = str(uuid4())
        async with db_manager.get_async_session() as session:
            thought_tree = ThoughtTree(
                id=thought_tree_id,
                parent_id=None,
                root_id=thought_tree_id,
                goal="DEBUG: Direct test",
                status='in_progress',
                depth=1,
                metadata_={'test': 'direct'},
                importance_level='medium'
            )
            session.add(thought_tree)
            await session.commit()
        
        # Create and initialize orchestrator
        orchestrator = TopLevelOrchestrator(
            max_concurrent_agents=6,
            max_execution_time_minutes=60,
            max_cost_usd=20.0,
            max_recursion_depth=5
        )
        orchestrator.thought_tree_id = thought_tree_id
        
        print(f"Context info - Current thread: {threading.current_thread().name}")
        print(f"Context info - Event loop: {asyncio.current_task()}")
        
        await orchestrator.initialize()
        print("✅ Direct orchestrator initialization: SUCCESS")
        
    except Exception as e:
        print(f"❌ Direct orchestrator initialization: FAILED - {e}")
        traceback.print_exc()
    
    # Test 2: Motivational Integration Context
    print("\n📋 Test 2: Motivational Integration Context (POTENTIALLY FAILING)")
    print("-" * 60)
    
    try:
        from core.motivation import create_integrated_motivational_system
        from core.motivation.initializer import create_motivational_test_environment
        
        print("Creating integrated motivational system...")
        print(f"Context info - Current thread: {threading.current_thread().name}")
        print(f"Context info - Event loop: {asyncio.current_task()}")
        
        # Create the integrated system (this starts the engine and integration)
        engine, integration = await create_integrated_motivational_system(
            start_engine=True,
            start_integration=True
        )
        
        print("✅ Integrated system created successfully")
        
        # Create test environment with motivated tasks
        print("Creating motivational test environment...")
        await create_motivational_test_environment()
        print("✅ Test environment created")
        
        # Force processing of tasks (this is where orchestrator init might fail)
        print("Processing pending motivated tasks...")
        print(f"Context info before processing - Current thread: {threading.current_thread().name}")
        print(f"Context info before processing - Event loop: {asyncio.current_task()}")
        
        await integration.force_process_pending_tasks()
        print("✅ Pending tasks processed successfully")
        
        # Check integration status
        status = await integration.get_integration_status()
        print(f"Integration status: {status}")
        
        # Cleanup
        await engine.stop_engine()
        await integration.stop_integration()
        print("✅ Integration context test: SUCCESS")
        
    except Exception as e:
        print(f"❌ Integration context test: FAILED - {e}")
        print("\n🔍 DETAILED ERROR TRACEBACK:")
        traceback.print_exc()
        
        # Try to clean up if we got partway through
        try:
            if 'engine' in locals() and engine:
                await engine.stop_engine()
            if 'integration' in locals() and integration:
                await integration.stop_integration()
        except:
            pass
    
    # Test 3: Examine the specific call path that's failing
    print("\n📋 Test 3: Isolated Orchestrator Integration Call Path")
    print("-" * 60)
    
    try:
        from core.motivation.orchestrator_integration import MotivationalOrchestratorIntegration
        from core.motivation.engine import MotivationalModelEngine
        from database.models import MotivationalTask
        
        # Create a minimal engine
        engine = MotivationalModelEngine(evaluation_interval=30.0)
        
        # Create integration
        integration = MotivationalOrchestratorIntegration(engine)
        
        # Create a fake motivated task to test with
        async with db_manager.get_async_session() as session:
            from sqlalchemy import select
            
            # Find an existing motivated task or create one
            result = await session.execute(select(MotivationalTask).limit(1))
            task = result.scalar_one_or_none()
            
            if not task:
                print("No existing motivated task found - creating one")
                from database.models import MotivationalState
                from uuid import uuid4
                
                # Get a motivational state
                state_result = await session.execute(select(MotivationalState).limit(1))
                state = state_result.scalar_one_or_none()
                
                if state:
                    task = MotivationalTask(
                        id=str(uuid4()),
                        motivational_state_id=state.id,
                        generated_prompt="Debug test prompt",
                        task_priority=0.5,
                        arbitration_score=0.5,
                        status='queued'
                    )
                    session.add(task)
                    await session.commit()
            
            if task:
                print(f"Testing with motivated task: {task.id}")
                print(f"Context info - Current thread: {threading.current_thread().name}")
                print(f"Context info - Event loop: {asyncio.current_task()}")
                
                # This is the exact call that's failing
                await integration._spawn_workflow_for_task(session, task)
                print("✅ _spawn_workflow_for_task: SUCCESS")
            else:
                print("⚠️  No motivated task available for testing")
        
    except Exception as e:
        print(f"❌ Isolated integration call: FAILED - {e}")
        print("\n🔍 DETAILED ERROR TRACEBACK:")
        traceback.print_exc()
    
    print("\n" + "=" * 80)
    print("🔍 DEBUG COMPLETE")
    print("=" * 80)

async def main():
    """Main debug function"""
    try:
        await debug_integration_context()
    except KeyboardInterrupt:
        print("\n🛑 Debug interrupted by user")
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())