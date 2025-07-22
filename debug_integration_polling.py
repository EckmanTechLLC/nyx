#!/usr/bin/env python3
"""
Debug script to test orchestrator integration polling directly
"""

import asyncio
import sys
import logging
sys.path.append('/app')

# Enable detailed logging
logging.basicConfig(level=logging.DEBUG)

async def test_integration_polling():
    """Test if integration polling can pick up the queued task"""
    print("=== TESTING ORCHESTRATOR INTEGRATION POLLING ===")
    
    from database.connection import db_manager
    from core.motivation.engine import MotivationalModelEngine
    from core.motivation.orchestrator_integration import MotivationalOrchestratorIntegration
    from core.motivation.spawner import SelfInitiatedTaskSpawner
    from database.models import MotivationalTask
    from sqlalchemy import select, func
    
    # Create engine and integration
    engine = MotivationalModelEngine(test_mode=True)
    integration = MotivationalOrchestratorIntegration(engine)
    spawner = SelfInitiatedTaskSpawner()
    
    async with db_manager.get_async_session() as session:
        print("\n1. CHECK PENDING TASKS")
        print("=" * 40)
        
        # Check if spawner can find pending tasks
        pending_tasks = await spawner.get_pending_tasks(session, limit=10)
        print(f"Spawner found {len(pending_tasks)} pending tasks:")
        
        for task in pending_tasks:
            print(f"   Task {task.id}: {task.status} - {task.generated_prompt[:50]}...")
            
        print("\n2. TEST INTEGRATION PROCESSING")
        print("=" * 40)
        
        if pending_tasks:
            print("Testing integration._process_pending_tasks()...")
            try:
                # Call the integration method directly
                await integration._process_pending_tasks()
                print("✅ Integration._process_pending_tasks() completed")
                
            except Exception as e:
                print(f"❌ Error in integration._process_pending_tasks(): {e}")
                import traceback
                traceback.print_exc()
                
        else:
            print("❌ No pending tasks found for integration to process")
            
        print("\n3. CHECK TASK STATUS AFTER PROCESSING")
        print("=" * 40)
        
        # Check if task status changed
        task_count_result = await session.execute(
            select(func.count(MotivationalTask.id), MotivationalTask.status)
            .group_by(MotivationalTask.status)
        )
        
        counts = task_count_result.fetchall()
        print("Task counts by status after processing:")
        for count, status in counts:
            print(f"   {status}: {count}")
            
        print("\n4. CHECK INTEGRATION STATUS")
        print("=" * 40)
        
        # Check integration status
        try:
            status = await integration.get_integration_status()
            print(f"Integration status: {status}")
        except Exception as status_e:
            print(f"Error getting integration status: {status_e}")

if __name__ == "__main__":
    asyncio.run(test_integration_polling())