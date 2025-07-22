#!/usr/bin/env python3
"""
Debug script to isolate the exact method call causing the greenlet_spawn error
"""

import asyncio
import logging
import traceback
from uuid import uuid4

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def debug_orchestrator_greenlet():
    """Step-by-step debug of orchestrator initialization to find the greenlet error"""
    
    print("=" * 80)
    print("🔍 DEBUG: Orchestrator Greenlet Error - Method Level Analysis")
    print("=" * 80)
    
    try:
        from database.connection import db_manager
        from database.models import ThoughtTree
        from core.orchestrator.top_level import TopLevelOrchestrator
        
        # Step 1: Create thought tree
        print("\n📋 Step 1: Creating ThoughtTree...")
        thought_tree_id = str(uuid4())
        async with db_manager.get_async_session() as session:
            thought_tree = ThoughtTree(
                id=thought_tree_id,
                parent_id=None,
                root_id=thought_tree_id,
                goal="DEBUG: Greenlet test",
                status='in_progress',
                depth=1,
                metadata_={'test': 'greenlet'},
                importance_level='medium'
            )
            session.add(thought_tree)
            await session.commit()
        print(f"✅ ThoughtTree created: {thought_tree_id}")
        
        # Step 2: Create orchestrator instance
        print("\n📋 Step 2: Creating TopLevelOrchestrator instance...")
        orchestrator = TopLevelOrchestrator(
            max_concurrent_agents=6,
            max_execution_time_minutes=60,
            max_cost_usd=20.0,
            max_recursion_depth=5
        )
        orchestrator.thought_tree_id = thought_tree_id
        print(f"✅ Orchestrator instance created: {orchestrator.id}")
        
        # Step 3: Test individual orchestrator initialization methods
        print("\n📋 Step 3: Testing BaseOrchestrator.initialize() step by step...")
        
        # Test 3.1: Set execution start time
        print("\n  📋 Step 3.1: Setting execution_start_time...")
        from datetime import datetime
        orchestrator.execution_start_time = datetime.now()
        print("  ✅ execution_start_time set")
        
        # Test 3.2: Check thought_tree_id (should skip _create_thought_tree)
        print("\n  📋 Step 3.2: Checking thought_tree_id...")
        if orchestrator.thought_tree_id:
            print(f"  ✅ thought_tree_id is set: {orchestrator.thought_tree_id}")
        else:
            print("  ❌ thought_tree_id not set")
        
        # Test 3.3: Test _persist_orchestrator_state (LIKELY CULPRIT)
        print("\n  📋 Step 3.3: Testing _persist_orchestrator_state...")
        try:
            await orchestrator._persist_orchestrator_state()
            print("  ✅ _persist_orchestrator_state successful")
        except Exception as persist_error:
            print(f"  ❌ _persist_orchestrator_state FAILED: {persist_error}")
            print("  🔍 PERSIST ERROR TRACEBACK:")
            traceback.print_exc()
            print("  ^^ THIS IS LIKELY THE GREENLET ERROR SOURCE")
        
        # Test 3.4: Test _orchestrator_specific_initialization
        print("\n  📋 Step 3.4: Testing _orchestrator_specific_initialization...")
        try:
            result = await orchestrator._orchestrator_specific_initialization()
            print(f"  ✅ _orchestrator_specific_initialization successful: {result}")
        except Exception as specific_error:
            print(f"  ❌ _orchestrator_specific_initialization FAILED: {specific_error}")
            print("  🔍 SPECIFIC INIT ERROR TRACEBACK:")
            traceback.print_exc()
        
        # Test 3.5: Test state setting
        print("\n  📋 Step 3.5: Testing state setting...")
        from core.orchestrator.base import OrchestratorState
        orchestrator.state = OrchestratorState.ACTIVE
        print("  ✅ State set to ACTIVE")
        
        # Test 3.6: Test final _persist_orchestrator_state
        print("\n  📋 Step 3.6: Testing final _persist_orchestrator_state...")
        try:
            await orchestrator._persist_orchestrator_state()
            print("  ✅ Final _persist_orchestrator_state successful")
        except Exception as final_persist_error:
            print(f"  ❌ Final _persist_orchestrator_state FAILED: {final_persist_error}")
            print("  🔍 FINAL PERSIST ERROR TRACEBACK:")
            traceback.print_exc()
        
        print("\n📋 Step 4: Now test the SAME orchestrator initialization within integration context...")
        
        # Step 4: Simulate integration context
        from core.motivation.orchestrator_integration import MotivationalOrchestratorIntegration
        from core.motivation.engine import MotivationalModelEngine
        
        # Create minimal engine and integration
        engine = MotivationalModelEngine(evaluation_interval=30.0)
        integration = MotivationalOrchestratorIntegration(engine)
        
        # Create a new orchestrator in integration context
        print("Creating new orchestrator in integration context...")
        orchestrator2 = TopLevelOrchestrator(
            max_concurrent_agents=6,
            max_execution_time_minutes=60,
            max_cost_usd=20.0,
            max_recursion_depth=5
        )
        
        # Create another thought tree
        thought_tree_id2 = str(uuid4())
        async with db_manager.get_async_session() as session:
            thought_tree2 = ThoughtTree(
                id=thought_tree_id2,
                parent_id=None,
                root_id=thought_tree_id2,
                goal="DEBUG: Integration context test",
                status='in_progress',
                depth=1,
                metadata_={'test': 'integration'},
                importance_level='medium'
            )
            session.add(thought_tree2)
            await session.commit()
        
        orchestrator2.thought_tree_id = thought_tree_id2
        
        print("Testing orchestrator initialization in integration context...")
        try:
            await orchestrator2.initialize()
            print("✅ Orchestrator initialization in integration context: SUCCESS")
        except Exception as integration_error:
            print(f"❌ Integration context initialization FAILED: {integration_error}")
            print("🔍 INTEGRATION ERROR TRACEBACK:")
            traceback.print_exc()
            
            # Let's test if it's the background tasks causing issues
            print("\nTesting if background engine tasks are interfering...")
            await engine.stop()  # Stop any background tasks
            
            try:
                orchestrator3 = TopLevelOrchestrator(
                    max_concurrent_agents=6,
                    max_execution_time_minutes=60,
                    max_cost_usd=20.0,
                    max_recursion_depth=5
                )
                orchestrator3.thought_tree_id = thought_tree_id2  # Reuse existing tree
                await orchestrator3.initialize()
                print("✅ Orchestrator initialization AFTER stopping engine: SUCCESS")
            except Exception as post_stop_error:
                print(f"❌ Post-stop initialization still FAILED: {post_stop_error}")
                print("🔍 POST-STOP ERROR TRACEBACK:")
                traceback.print_exc()
        
        print("\n" + "=" * 80)
        print("🔍 DEBUG COMPLETE - Check above for the exact method causing greenlet error")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n💥 FATAL ERROR in debug script: {e}")
        traceback.print_exc()

async def main():
    """Main debug function"""
    try:
        await debug_orchestrator_greenlet()
    except KeyboardInterrupt:
        print("\n🛑 Debug interrupted by user")
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())