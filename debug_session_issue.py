#!/usr/bin/env python3
"""
Debug script to isolate the SQLAlchemy async context issue in orchestrator integration
"""

import asyncio
import sys
import logging
from uuid import uuid4

# Setup logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

sys.path.append('/app')

async def test_basic_session():
    """Test 1: Basic database session functionality"""
    print("=== TEST 1: Basic Database Session ===")
    try:
        from database.connection import db_manager
        from database.models import ThoughtTree
        
        async with db_manager.get_async_session() as session:
            print("✅ Created async session")
            
            # Test a simple query
            from sqlalchemy import select
            result = await session.execute(select(ThoughtTree).limit(1))
            print("✅ Simple query executed successfully")
            
    except Exception as e:
        print(f"❌ Basic session test failed: {e}")
        return False
    return True

async def test_thought_tree_creation():
    """Test 2: Direct ThoughtTree creation (same pattern as integration)"""
    print("\n=== TEST 2: ThoughtTree Creation ===")
    try:
        from database.connection import db_manager
        from database.models import ThoughtTree
        
        async with db_manager.get_async_session() as session:
            print("✅ Created async session")
            
            # Create thought tree exactly as in orchestrator_integration.py
            thought_tree_id = str(uuid4())
            thought_tree = ThoughtTree(
                id=thought_tree_id,
                parent_id=None,
                root_id=thought_tree_id,
                goal="DEBUG: Test thought tree creation",
                status='in_progress',
                depth=1,
                metadata_={
                    'debug_test': True,
                    'test_type': 'thought_tree_creation'
                },
                importance_level='low'
            )
            
            print("✅ Created ThoughtTree object")
            
            session.add(thought_tree)
            print("✅ Added to session")
            
            await session.commit()
            print("✅ Committed successfully")
            
            return thought_tree_id
            
    except Exception as e:
        print(f"❌ ThoughtTree creation failed: {e}")
        import traceback
        traceback.print_exc()
        return None

async def test_motivational_task_operations():
    """Test 3: Motivational task database operations"""
    print("\n=== TEST 3: Motivational Task Operations ===")
    try:
        from database.connection import db_manager
        from database.models import MotivationalTask, MotivationalState
        from core.motivation.spawner import SelfInitiatedTaskSpawner
        
        spawner = SelfInitiatedTaskSpawner()
        
        async with db_manager.get_async_session() as session:
            print("✅ Created async session")
            
            # Get pending tasks (this is what fails in the integration)
            pending_tasks = await spawner.get_pending_tasks(session, limit=1)
            print(f"✅ Retrieved {len(pending_tasks)} pending tasks")
            
            if pending_tasks:
                task = pending_tasks[0]
                print(f"✅ Got task: {task.id}")
                
                # Try to update task status (this works in the logs)
                await spawner.update_task_status(
                    session,
                    str(task.id),
                    'debug_test',
                    metadata={'debug_test': 'session_check'}
                )
                print("✅ Updated task status")
                
                await session.commit()
                print("✅ Committed task update")
                
                return task
            else:
                print("ℹ️  No pending tasks found")
                return None
                
    except Exception as e:
        print(f"❌ Motivational task operations failed: {e}")
        import traceback
        traceback.print_exc()
        return None

async def test_nested_session_issue():
    """Test 4: Try to reproduce the exact nested session pattern"""
    print("\n=== TEST 4: Nested Session Pattern ===")
    try:
        from database.connection import db_manager
        from database.models import ThoughtTree, MotivationalTask
        from core.motivation.spawner import SelfInitiatedTaskSpawner
        
        spawner = SelfInitiatedTaskSpawner()
        
        # This mimics the exact pattern from _process_pending_tasks -> _spawn_workflow_for_task
        async with db_manager.get_async_session() as outer_session:
            print("✅ Created outer session")
            
            # Get a task (like in _process_pending_tasks)
            pending_tasks = await spawner.get_pending_tasks(outer_session, limit=1)
            
            if pending_tasks:
                task = pending_tasks[0]
                print(f"✅ Got task from outer session: {task.id}")
                
                # Now try the operations that fail in _spawn_workflow_for_task
                print("--- Starting _spawn_workflow_for_task simulation ---")
                
                # Step 1: Update task status (this works)
                await spawner.update_task_status(
                    outer_session,
                    str(task.id),
                    'spawned',
                    metadata={'debug_test': 'spawn_simulation'}
                )
                print("✅ Task status updated to spawned")
                
                # Step 2: Create thought tree (THIS IS WHERE IT FAILS)
                print("--- About to create thought tree (failure point) ---")
                thought_tree_id = str(uuid4())
                
                thought_tree = ThoughtTree(
                    id=thought_tree_id,
                    parent_id=None,
                    root_id=thought_tree_id,
                    goal="DEBUG: Nested session test",
                    status='in_progress',
                    depth=1,
                    metadata_={'debug_nested_test': True}
                )
                
                print("✅ Created ThoughtTree object")
                outer_session.add(thought_tree)
                print("✅ Added ThoughtTree to outer session")
                
                # This might be the problem - trying to flush within existing session
                print("--- About to commit (potential failure point) ---")
                await outer_session.commit()
                print("✅ Committed outer session successfully")
                
                return True
            else:
                print("ℹ️  No pending tasks for nested test")
                return True
                
    except Exception as e:
        print(f"❌ Nested session pattern failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Run all debug tests"""
    print("🔍 NYX SQLAlchemy Async Context Debug Suite")
    print("=" * 50)
    
    tests = [
        ("Basic Session", test_basic_session),
        ("ThoughtTree Creation", test_thought_tree_creation), 
        ("Motivational Task Operations", test_motivational_task_operations),
        ("Nested Session Pattern", test_nested_session_issue)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results[test_name] = result is not False
        except Exception as e:
            print(f"❌ {test_name} crashed: {e}")
            results[test_name] = False
    
    print("\n" + "=" * 50)
    print("🔍 DEBUG RESULTS SUMMARY")
    print("=" * 50)
    
    for test_name, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_name:25} | {status}")
    
    print("\n🎯 DIAGNOSIS:")
    if all(results.values()):
        print("All tests passed - the issue may be in async task scheduling or threading")
    else:
        failed_tests = [name for name, passed in results.items() if not passed]
        print(f"Failed tests: {', '.join(failed_tests)}")
        print("Root cause identified in the failed test above.")

if __name__ == "__main__":
    asyncio.run(main())