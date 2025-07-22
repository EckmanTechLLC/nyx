#!/usr/bin/env python3
"""
Clear test artifacts from database to allow clean autonomous testing
"""

import asyncio
import sys
sys.path.append('/app')

async def clear_test_data():
    """Clear motivational tasks and related test data"""
    from database.connection import db_manager
    from database.models import MotivationalTask, MotivationalState
    from sqlalchemy import delete
    
    async with db_manager.get_async_session() as session:
        print("=== CLEARING TEST DATA ===")
        
        # Delete all motivational tasks
        task_result = await session.execute(delete(MotivationalTask))
        print(f"Deleted {task_result.rowcount} motivational tasks")
        
        # Reset motivational state metrics AND timing fields (keep the states but reset counters)
        from sqlalchemy import update
        state_result = await session.execute(
            update(MotivationalState)
            .values(
                success_count=0,
                failure_count=0,
                total_attempts=0,
                last_triggered_at=None,  # This will clear cooldown periods!
                last_satisfied_at=None
            )
        )
        print(f"Reset {state_result.rowcount} motivational state counters")
        
        await session.commit()
        print("✅ Database cleared successfully")
        
        # Verify cleanup
        from sqlalchemy import select, func
        
        task_count = await session.execute(select(func.count(MotivationalTask.id)))
        remaining_tasks = task_count.scalar() or 0
        print(f"Remaining tasks: {remaining_tasks}")
        
        state_count = await session.execute(select(func.count(MotivationalState.id)))
        total_states = state_count.scalar() or 0
        print(f"Total motivational states: {total_states}")

if __name__ == "__main__":
    asyncio.run(clear_test_data())