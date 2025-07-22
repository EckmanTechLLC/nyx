#!/usr/bin/env python3
"""
Debug script to check task counts that might be blocking new task generation
"""

import asyncio
import sys
sys.path.append('/app')

async def check_task_counts():
    """Check motivational task counts by status"""
    from database.connection import db_manager
    from database.models import MotivationalTask
    from sqlalchemy import select, func
    
    async with db_manager.get_async_session() as session:
        print("=== MOTIVATIONAL TASK COUNTS BY STATUS ===")
        
        # Get counts by status
        result = await session.execute(
            select(MotivationalTask.status, func.count(MotivationalTask.id))
            .group_by(MotivationalTask.status)
        )
        
        status_counts = result.fetchall()
        total = 0
        
        for status, count in status_counts:
            print(f"{status:15} | {count:3d} tasks")
            total += count
            
        print(f"{'TOTAL':15} | {total:3d} tasks")
        
        # Check specifically what _can_spawn_new_tasks checks
        active_result = await session.execute(
            select(func.count(MotivationalTask.id))
            .where(MotivationalTask.status.in_(['queued', 'spawned', 'active']))
        )
        active_count = active_result.scalar() or 0
        
        print(f"\n=== CAPACITY CHECK ===")
        print(f"Active tasks (queued/spawned/active): {active_count}")
        print(f"Max concurrent tasks allowed: 3")
        print(f"Can spawn new tasks: {active_count < 3}")
        
        # Check recent tasks
        from sqlalchemy import desc
        recent_result = await session.execute(
            select(MotivationalTask.status, MotivationalTask.spawned_at)
            .order_by(desc(MotivationalTask.spawned_at))
            .limit(5)
        )
        
        print(f"\n=== RECENT TASKS ===")
        recent_tasks = recent_result.fetchall()
        for status, spawned_at in recent_tasks:
            spawned_str = spawned_at.strftime("%H:%M:%S") if spawned_at else "Unknown"
            print(f"{status:15} | {spawned_str}")

if __name__ == "__main__":
    asyncio.run(check_task_counts())