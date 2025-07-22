#!/usr/bin/env python3
"""
Debug script to pinpoint the SQLAlchemy async context issue in orchestrator initialization
"""

import asyncio
import logging
import traceback
from datetime import datetime, timezone
from uuid import uuid4

# Configure logging for detailed debugging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def debug_orchestrator_async_context():
    """Debug the async context issue step by step"""
    
    print("=" * 70)
    print("🔍 DEBUG: Orchestrator Async Context Issue")
    print("=" * 70)
    
    try:
        # Step 1: Test basic database connection
        print("\n📋 Step 1: Testing basic database connection...")
        from database.connection import db_manager
        
        async with db_manager.get_async_session() as session:
            from sqlalchemy import text
            result = await session.execute(text("SELECT 1"))
            print("✅ Basic database connection working")
        
        # Step 2: Test ThoughtTree creation (our fix)
        print("\n📋 Step 2: Testing ThoughtTree creation...")
        from database.models import ThoughtTree
        
        thought_tree_id = str(uuid4())
        async with db_manager.get_async_session() as session:
            thought_tree = ThoughtTree(
                id=thought_tree_id,
                parent_id=None,
                root_id=thought_tree_id,
                goal="DEBUG: Test thought tree creation",
                status='in_progress',
                depth=1,
                metadata_={'debug_test': True},
                importance_level='medium'
            )
            session.add(thought_tree)
            await session.commit()
            print(f"✅ ThoughtTree created successfully: {thought_tree_id}")
        
        # Step 3: Test orchestrator creation WITHOUT initialization
        print("\n📋 Step 3: Testing orchestrator instantiation...")
        from core.orchestrator.top_level import TopLevelOrchestrator
        
        orchestrator = TopLevelOrchestrator(
            max_concurrent_agents=6,
            max_execution_time_minutes=60,
            max_cost_usd=20.0,
            max_recursion_depth=5
        )
        orchestrator.thought_tree_id = thought_tree_id
        print(f"✅ Orchestrator instantiated: {orchestrator.id}")
        
        # Step 4: Test orchestrator initialization - WHERE THE ERROR OCCURS
        print("\n📋 Step 4: Testing orchestrator initialization (ERROR EXPECTED HERE)...")
        try:
            await orchestrator.initialize()
            print("✅ Orchestrator initialization successful")
        except Exception as init_error:
            print(f"❌ Orchestrator initialization failed: {init_error}")
            print("\n🔍 DETAILED ERROR TRACEBACK:")
            traceback.print_exc()
            
            # Let's dig deeper into what method is causing this
            print("\n📋 Step 4.1: Testing BaseOrchestrator.initialize() components individually...")
            
            # Test _create_thought_tree (should be skipped since we set thought_tree_id)
            print("Testing thought tree creation skip...")
            if orchestrator.thought_tree_id:
                print("✅ Thought tree creation will be skipped (ID already set)")
            
            # Test _persist_orchestrator_state
            print("\n📋 Step 4.2: Testing _persist_orchestrator_state directly...")
            try:
                await orchestrator._persist_orchestrator_state()
                print("✅ _persist_orchestrator_state successful")
            except Exception as persist_error:
                print(f"❌ _persist_orchestrator_state failed: {persist_error}")
                print("🔍 PERSIST ERROR TRACEBACK:")
                traceback.print_exc()
            
            # Test _orchestrator_specific_initialization
            print("\n📋 Step 4.3: Testing _orchestrator_specific_initialization...")
            try:
                result = await orchestrator._orchestrator_specific_initialization()
                print(f"✅ _orchestrator_specific_initialization successful: {result}")
            except Exception as specific_error:
                print(f"❌ _orchestrator_specific_initialization failed: {specific_error}")
                print("🔍 SPECIFIC INIT ERROR TRACEBACK:")
                traceback.print_exc()
        
        # Step 5: Test database connection context during orchestrator operations
        print("\n📋 Step 5: Testing database context during orchestrator operations...")
        try:
            # Simulate what happens during orchestrator persistence
            from database.models import Orchestrator
            from sqlalchemy import select
            
            async with db_manager.get_async_session() as test_session:
                # Check if thought tree exists
                result = await test_session.execute(
                    select(ThoughtTree).where(ThoughtTree.id == thought_tree_id)
                )
                existing_tree = result.scalar_one_or_none()
                if existing_tree:
                    print("✅ ThoughtTree found in database")
                    
                    # Try to create orchestrator record
                    new_orchestrator = Orchestrator(
                        id=str(orchestrator.id),
                        parent_orchestrator_id=None,
                        thought_tree_id=thought_tree_id,
                        orchestrator_type="top_level",
                        status="active",
                        max_concurrent_agents=6,
                        current_active_agents=0,
                        global_context={}
                    )
                    test_session.add(new_orchestrator)
                    await test_session.commit()
                    print("✅ Orchestrator database record created successfully")
                else:
                    print("❌ ThoughtTree not found in database")
                    
        except Exception as db_error:
            print(f"❌ Database context test failed: {db_error}")
            print("🔍 DATABASE ERROR TRACEBACK:")
            traceback.print_exc()
        
        print("\n" + "=" * 70)
        print("🔍 DEBUG COMPLETE")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n💥 FATAL ERROR in debug script: {e}")
        traceback.print_exc()

async def main():
    """Main debug function"""
    try:
        await debug_orchestrator_async_context()
    except KeyboardInterrupt:
        print("\n🛑 Debug interrupted by user")
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())