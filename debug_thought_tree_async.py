#!/usr/bin/env python3
"""
Debug script to isolate the SQLAlchemy async context issue in ThoughtTree creation
"""

import asyncio
import sys
import logging
from uuid import uuid4
sys.path.append('/app')

# Enable detailed logging
logging.basicConfig(level=logging.DEBUG)

async def test_thought_tree_creation():
    """Test ThoughtTree creation in different async contexts to isolate the issue"""
    print("=== DEBUGGING THOUGHT TREE ASYNC CONTEXT ISSUE ===")
    
    from database.connection import db_manager
    from database.models import ThoughtTree, MotivationalTask
    from sqlalchemy import select
    
    print("\n1. TEST: Direct ThoughtTree creation (should work)")
    print("=" * 60)
    
    try:
        async with db_manager.get_async_session() as session:
            thought_tree_id = str(uuid4())
            thought_tree = ThoughtTree(
                id=thought_tree_id,
                parent_id=None,
                root_id=thought_tree_id,
                goal="DEBUG: Direct creation test",
                status='in_progress',
                depth=1,
                metadata_={'debug_test': True}
            )
            
            session.add(thought_tree)
            await session.commit()
            print("✅ Direct ThoughtTree creation succeeded")
            
    except Exception as e:
        print(f"❌ Direct ThoughtTree creation failed: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n2. TEST: Simulate orchestrator integration pattern")
    print("=" * 60)
    
    try:
        # This mimics the exact pattern from orchestrator integration
        async with db_manager.get_async_session() as outer_session:
            print("✅ Created outer session")
            
            # Get a mock task (similar to pending task retrieval)
            mock_task_data = {
                'id': str(uuid4()),
                'motivational_state_id': None,
                'task_priority': 0.5,
                'arbitration_score': 0.3,
                'generated_prompt': "Mock task for async debug"
            }
            
            print("✅ Created mock task data")
            
            # Now test the thought tree creation pattern from _create_thought_tree
            motivation_type = 'debug_test'
            thought_tree_id = str(uuid4())
            
            print("--- Testing fresh session pattern ---")
            # This is the pattern currently used in _create_thought_tree
            async with db_manager.get_async_session() as tree_session:
                thought_tree = ThoughtTree(
                    id=thought_tree_id,
                    parent_id=None,
                    root_id=thought_tree_id,
                    goal=f"AUTONOMOUS: {motivation_type} - {mock_task_data['generated_prompt'][:200]}...",
                    status='in_progress',
                    depth=1,
                    metadata_={
                        'autonomous_task': True,
                        'motivation_type': motivation_type,
                        'motivated_task_id': mock_task_data['id'],
                        'priority': mock_task_data['task_priority'],
                        'arbitration_score': mock_task_data['arbitration_score']
                    }
                )
                
                print("✅ Created ThoughtTree object")
                tree_session.add(thought_tree)
                print("✅ Added ThoughtTree to fresh session")
                await tree_session.commit()
                print("✅ Committed fresh session")
            
            print("✅ Fresh session ThoughtTree creation succeeded")
            
    except Exception as e:
        print(f"❌ Fresh session ThoughtTree creation failed: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n3. TEST: Simulate exact integration polling context")
    print("=" * 60)
    
    try:
        # This simulates the exact async context from integration polling
        from core.motivation.orchestrator_integration import MotivationalOrchestratorIntegration
        from core.motivation.engine import MotivationalModelEngine
        from core.motivation.spawner import SelfInitiatedTaskSpawner
        
        engine = MotivationalModelEngine(test_mode=True)
        integration = MotivationalOrchestratorIntegration(engine)
        spawner = SelfInitiatedTaskSpawner()
        
        print("✅ Created integration components")
        
        # Check if there are actual pending tasks first
        async with db_manager.get_async_session() as session:
            pending_tasks = await spawner.get_pending_tasks(session, limit=1)
            
            if pending_tasks:
                task = pending_tasks[0]
                print(f"✅ Found pending task: {task.id}")
                
                # Now test the exact _create_thought_tree call that's failing
                print("--- Testing _create_thought_tree with real task ---")
                thought_tree_id = await integration._create_thought_tree(session, task)
                print(f"✅ _create_thought_tree succeeded: {thought_tree_id}")
                
            else:
                print("ℹ️  No pending tasks found, creating mock task...")
                
                # Create a minimal mock task for testing
                from database.models import MotivationalState
                from sqlalchemy import select
                
                # Get a motivational state
                state_result = await session.execute(select(MotivationalState).limit(1))
                state = state_result.scalar_one_or_none()
                
                if state:
                    # Create a mock task
                    mock_task = MotivationalTask(
                        id=str(uuid4()),
                        motivational_state_id=state.id,
                        task_priority=0.5,
                        arbitration_score=0.3,
                        generated_prompt="Mock task for async debugging",
                        status='queued'
                    )
                    
                    session.add(mock_task)
                    await session.commit()
                    print(f"✅ Created mock task: {mock_task.id}")
                    
                    # Now test _create_thought_tree
                    print("--- Testing _create_thought_tree with mock task ---")
                    thought_tree_id = await integration._create_thought_tree(session, mock_task)
                    print(f"✅ _create_thought_tree succeeded: {thought_tree_id}")
                else:
                    print("❌ No motivational states found")
                    
    except Exception as e:
        print(f"❌ Integration context test failed: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n4. SUMMARY")
    print("=" * 60)
    print("If test 1 and 2 work but test 3 fails, the issue is in the integration async context.")
    print("If all tests fail at the same point, the issue is in the ThoughtTree model or session handling.")
    print("If tests work in isolation but fail in integration, it's an async task boundary issue.")

if __name__ == "__main__":
    asyncio.run(test_thought_tree_creation())