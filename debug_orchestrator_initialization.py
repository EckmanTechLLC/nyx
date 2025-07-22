#!/usr/bin/env python3
"""
Debug script to isolate the orchestrator initialization async context issue
"""

import asyncio
import sys
import logging
from uuid import uuid4
sys.path.append('/app')

# Enable detailed logging
logging.basicConfig(level=logging.DEBUG)

async def debug_orchestrator_initialization():
    """Debug exactly what happens during orchestrator initialization"""
    print("=== DEBUGGING ORCHESTRATOR INITIALIZATION ASYNC CONTEXT ===")
    
    from database.connection import db_manager
    from core.orchestrator.top_level import TopLevelOrchestrator, WorkflowInput, WorkflowInputType
    from database.models import MotivationalTask
    
    print("\n1. TEST: Direct TopLevelOrchestrator creation and initialization")
    print("=" * 70)
    
    try:
        # Test basic orchestrator creation
        orchestrator = TopLevelOrchestrator(
            max_concurrent_agents=6,
            max_execution_time_minutes=60,
            max_cost_usd=20.0,
            max_recursion_depth=5
        )
        print("✅ Created TopLevelOrchestrator")
        
        # Set thought tree ID
        thought_tree_id = str(uuid4())
        orchestrator.thought_tree_id = thought_tree_id
        print("✅ Set thought tree ID")
        
        # Try to initialize (this is where it fails)
        print("--- About to call orchestrator.initialize() ---")
        await orchestrator.initialize()
        print("✅ Orchestrator initialization succeeded")
        
        # Clean up
        await orchestrator.terminate()
        print("✅ Orchestrator terminated cleanly")
        
    except Exception as e:
        print(f"❌ Direct orchestrator initialization failed: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n2. TEST: Orchestrator initialization in fresh async context")
    print("=" * 70)
    
    try:
        # Create orchestrator in a completely separate async task
        async def create_and_init_orchestrator():
            orchestrator = TopLevelOrchestrator(
                max_concurrent_agents=6,
                max_execution_time_minutes=60,
                max_cost_usd=20.0,
                max_recursion_depth=5
            )
            
            thought_tree_id = str(uuid4())
            orchestrator.thought_tree_id = thought_tree_id
            
            await orchestrator.initialize()
            
            # Clean up
            await orchestrator.terminate()
            return "success"
        
        # Run in fresh async context
        print("--- Running orchestrator in fresh async task ---")
        result = await asyncio.create_task(create_and_init_orchestrator())
        print(f"✅ Fresh async task orchestrator initialization: {result}")
        
    except Exception as e:
        print(f"❌ Fresh async task initialization failed: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n3. TEST: Simulate integration workflow creation pattern")
    print("=" * 70)
    
    try:
        # This mimics the exact pattern from _spawn_workflow_for_task
        print("--- Simulating _spawn_workflow_for_task pattern ---")
        
        # Create mock task data
        mock_task = {
            'id': str(uuid4()),
            'generated_prompt': 'Test autonomous task for orchestrator debug',
            'task_priority': 0.5,
            'arbitration_score': 0.3
        }
        
        # Create workflow input (from _create_workflow_input_from_task)
        workflow_input = WorkflowInput(
            input_type=WorkflowInputType.USER_PROMPT,
            content={
                'content': mock_task['generated_prompt'],
                'autonomous_origin': True,
                'motivation_type': 'debug_test'
            },
            execution_context={
                'motivated_task': True,
                'task_priority': mock_task['task_priority'],
                'arbitration_score': mock_task['arbitration_score'],
                'autonomous_execution': True
            },
            priority='medium',
            urgency='normal'
        )
        print("✅ Created WorkflowInput")
        
        # Create and configure orchestrator (same pattern)
        orchestrator = TopLevelOrchestrator(
            max_concurrent_agents=6,
            max_execution_time_minutes=60,
            max_cost_usd=20.0,
            max_recursion_depth=5
        )
        print("✅ Created orchestrator")
        
        # Set thought tree ID and initialize
        thought_tree_id = str(uuid4())
        orchestrator.thought_tree_id = thought_tree_id
        print("✅ Set thought tree ID")
        
        print("--- About to initialize orchestrator (exact integration pattern) ---")
        await orchestrator.initialize()
        print("✅ Integration pattern initialization succeeded")
        
        # Test workflow execution setup (but don't actually execute)
        print("--- Testing workflow execution setup ---")
        # Don't actually execute: result = await orchestrator.execute_workflow(workflow_input)
        print("✅ Workflow execution setup ready")
        
        # Clean up
        await orchestrator.terminate()
        print("✅ Integration pattern orchestrator terminated")
        
    except Exception as e:
        print(f"❌ Integration pattern test failed: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n4. TEST: Check what happens inside orchestrator.initialize()")
    print("=" * 70)
    
    try:
        # Let's look at what initialize() actually does that might cause async issues
        from core.orchestrator.top_level import TopLevelOrchestrator
        import inspect
        
        orchestrator = TopLevelOrchestrator(
            max_concurrent_agents=6,
            max_execution_time_minutes=60,
            max_cost_usd=20.0,
            max_recursion_depth=5
        )
        
        # Check if initialize is async and what it does
        init_method = getattr(orchestrator, 'initialize', None)
        if init_method:
            if asyncio.iscoroutinefunction(init_method):
                print("✅ initialize() is an async coroutine")
            else:
                print("⚠️  initialize() is not async")
                
            # Try to get source code or docstring
            try:
                source = inspect.getsource(init_method)
                print("initialize() source code:")
                print(source[:500] + "..." if len(source) > 500 else source)
            except:
                try:
                    doc = init_method.__doc__
                    if doc:
                        print(f"initialize() docstring: {doc}")
                    else:
                        print("No docstring available")
                except:
                    print("Could not inspect initialize() method")
        else:
            print("❌ No initialize() method found")
            
    except Exception as e:
        print(f"❌ Method inspection failed: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n5. SUMMARY")
    print("=" * 70)
    print("This will help identify:")
    print("- Whether TopLevelOrchestrator.initialize() works in isolation")
    print("- Whether it's an async context boundary issue")
    print("- What specific operation inside initialize() is causing the greenlet error")
    print("- Whether the issue is in the integration's async task scheduling")

if __name__ == "__main__":
    asyncio.run(debug_orchestrator_initialization())