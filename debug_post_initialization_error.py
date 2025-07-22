#!/usr/bin/env python3
"""
Debug script to find the exact line causing the greenlet error AFTER successful orchestrator initialization
"""

import asyncio
import logging
import traceback
from datetime import datetime, timezone
from uuid import uuid4

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def debug_post_initialization_error():
    """Debug the exact line causing greenlet error after orchestrator initialization"""
    
    print("=" * 80)
    print("🔍 DEBUG: Post-Initialization Greenlet Error - Line by Line")  
    print("=" * 80)
    
    try:
        from database.connection import db_manager
        from database.models import ThoughtTree, MotivationalTask, MotivationalState
        from core.orchestrator.top_level import TopLevelOrchestrator
        from core.motivation.orchestrator_integration import MotivationalOrchestratorIntegration
        from core.motivation.engine import MotivationalModelEngine
        from uuid import uuid4
        from sqlalchemy import select
        
        # Step 1: Recreate the EXACT integration scenario
        print("\n📋 Step 1: Recreating exact integration scenario...")
        
        # Create motivational state and task like the integration test does
        async with db_manager.get_async_session() as session:
            # Get or create motivational state
            state_result = await session.execute(
                select(MotivationalState).where(MotivationalState.motivation_type == 'maximize_coverage')
            )
            state = state_result.scalar_one_or_none()
            
            if not state:
                print("No maximize_coverage state found, creating minimal test environment")
                return
            
            # Create motivated task
            task = MotivationalTask(
                id=str(uuid4()),
                motivational_state_id=state.id,
                generated_prompt="Debug: Test workflow tracking error",
                task_priority=0.5,
                arbitration_score=0.6,
                status='queued'
            )
            session.add(task)
            await session.commit()
            
            print(f"✅ Created motivated task: {task.id}")
            
        # Step 2: Create integration components
        print("\n📋 Step 2: Creating integration components...")
        engine = MotivationalModelEngine(evaluation_interval=30.0)
        integration = MotivationalOrchestratorIntegration(engine)
        print("✅ Integration components created")
        
        # Step 3: Execute the EXACT workflow spawn process line by line
        print("\n📋 Step 3: Executing workflow spawn process line by line...")
        
        async with db_manager.get_async_session() as session:
            # Reload the task in this session
            task_result = await session.execute(select(MotivationalTask).where(MotivationalTask.id == task.id))
            task = task_result.scalar_one()
            
            print(f"Task reloaded: {task.id}")
            
            # Execute the spawn workflow method step by step
            thought_tree_id = None
            
            print("\n  📋 Step 3.1: Database operations (known working)...")
            
            # Update task status
            await integration.spawner.update_task_status(
                session, str(task.id), 'spawned',
                metadata={'spawned_at': datetime.now(timezone.utc).isoformat()}
            )
            print("  ✅ Task status updated to spawned")
            
            # Create thought tree  
            thought_tree_id = await integration._create_thought_tree_within_session(session, task)
            print(f"  ✅ ThoughtTree created: {thought_tree_id}")
            
            # Update task to active
            await integration.spawner.update_task_status(
                session, str(task.id), 'active',
                thought_tree_id=thought_tree_id,
                metadata={'thought_tree_created': datetime.now(timezone.utc).isoformat()}
            )
            print("  ✅ Task status updated to active")
            
            # Commit all changes
            await session.commit()
            print("  ✅ Database operations committed")
        
        print("\n  📋 Step 3.2: Post-commit workflow operations...")
        
        # NOW - outside session context - test each operation
        
        # Test 3.2.1: Workflow input creation
        print("\n    📋 Step 3.2.1: Testing workflow input creation...")
        try:
            workflow_input = integration._create_workflow_input_from_task(task)
            print("    ✅ Workflow input created successfully")
            print(f"    Content: {workflow_input.content.get('motivation_type', 'unknown')}")
        except Exception as workflow_error:
            print(f"    ❌ Workflow input creation FAILED: {workflow_error}")
            print("    🔍 WORKFLOW INPUT ERROR TRACEBACK:")
            traceback.print_exc()
            
        # Test 3.2.2: Orchestrator creation
        print("\n    📋 Step 3.2.2: Testing orchestrator creation...")
        try:
            orchestrator = TopLevelOrchestrator(
                max_concurrent_agents=6,
                max_execution_time_minutes=60,
                max_cost_usd=20.0,
                max_recursion_depth=5
            )
            orchestrator.thought_tree_id = thought_tree_id
            print("    ✅ Orchestrator created successfully")
        except Exception as orch_create_error:
            print(f"    ❌ Orchestrator creation FAILED: {orch_create_error}")
            traceback.print_exc()
            
        # Test 3.2.3: Orchestrator initialization
        print("\n    📋 Step 3.2.3: Testing orchestrator initialization...")
        try:
            await orchestrator.initialize()
            print("    ✅ Orchestrator initialization successful")
        except Exception as init_error:
            print(f"    ❌ Orchestrator initialization FAILED: {init_error}")
            traceback.print_exc()
            
        # Test 3.2.4: Workflow info creation (SUSPECTED CULPRIT)
        print("\n    📋 Step 3.2.4: Testing workflow info creation...")
        try:
            print("    Testing individual workflow_info fields...")
            
            task_id_str = str(task.id)
            print(f"    ✅ task_id: {task_id_str}")
            
            print(f"    ✅ thought_tree_id: {thought_tree_id}")
            
            print(f"    ✅ orchestrator: {orchestrator}")
            
            started_at = datetime.now(timezone.utc)
            print(f"    ✅ started_at: {started_at}")
            
            # THIS IS THE SUSPECTED CULPRIT
            print("    Testing motivation_type access...")
            try:
                if hasattr(task, 'motivational_state'):
                    motivation_type = task.motivational_state.motivation_type
                    print(f"    ✅ motivation_type via relationship: {motivation_type}")
                else:
                    motivation_type = 'unknown'
                    print("    ✅ motivation_type: unknown (no relationship)")
            except Exception as motivation_error:
                print(f"    ❌ motivation_type access FAILED: {motivation_error}")
                print("    🔍 MOTIVATION TYPE ERROR TRACEBACK:")
                traceback.print_exc()
                motivation_type = 'unknown'
            
            # Now create the full workflow_info dict
            workflow_info = {
                'task_id': task_id_str,
                'thought_tree_id': thought_tree_id,
                'orchestrator': orchestrator,
                'started_at': started_at,
                'motivation_type': motivation_type
            }
            print("    ✅ workflow_info dict created successfully")
            
        except Exception as workflow_info_error:
            print(f"    ❌ Workflow info creation FAILED: {workflow_info_error}")
            print("    🔍 WORKFLOW INFO ERROR TRACEBACK:")
            traceback.print_exc()
            
        # Test 3.2.5: Active workflows tracking
        print("\n    📋 Step 3.2.5: Testing active workflows tracking...")
        try:
            integration.active_motivated_workflows[thought_tree_id] = workflow_info
            print("    ✅ Active workflows tracking successful")
        except Exception as tracking_error:
            print(f"    ❌ Active workflows tracking FAILED: {tracking_error}")
            traceback.print_exc()
            
        # Test 3.2.6: Background task creation
        print("\n    📋 Step 3.2.6: Testing background task creation...")
        try:
            # Just test the creation, not execution
            background_task = asyncio.create_task(
                integration._execute_motivated_workflow(workflow_input, workflow_info)
            )
            print("    ✅ Background task created successfully")
            
            # Cancel it immediately to avoid actual execution
            background_task.cancel()
            try:
                await background_task
            except asyncio.CancelledError:
                pass
            print("    ✅ Background task cancelled cleanly")
            
        except Exception as background_error:
            print(f"    ❌ Background task creation FAILED: {background_error}")
            print("    🔍 BACKGROUND TASK ERROR TRACEBACK:")
            traceback.print_exc()
            
        print("\n" + "=" * 80)
        print("🔍 DEBUG COMPLETE - Check above for the exact error source")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n💥 FATAL ERROR in debug script: {e}")
        traceback.print_exc()

async def main():
    """Main debug function"""
    try:
        await debug_post_initialization_error()
    except KeyboardInterrupt:
        print("\n🛑 Debug interrupted by user")
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())