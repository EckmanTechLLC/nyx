#!/usr/bin/env python3
"""
Force clear all cooldown periods and set motivation levels for immediate testing
"""

import asyncio
import sys
from datetime import datetime, timezone
sys.path.append('/app')

async def force_clear_cooldowns():
    """Aggressively clear all cooldown periods and boost motivations for testing"""
    from database.connection import db_manager
    from database.models import MotivationalTask, MotivationalState
    from sqlalchemy import delete, update
    
    async with db_manager.get_async_session() as session:
        print("=== FORCE CLEARING ALL COOLDOWNS AND BOOSTING MOTIVATIONS ===")
        
        # Delete ALL tasks
        task_result = await session.execute(delete(MotivationalTask))
        print(f"Deleted {task_result.rowcount} tasks")
        
        # Force reset ALL timing fields and boost urgency
        state_result = await session.execute(
            update(MotivationalState)
            .values(
                success_count=0,
                failure_count=0,
                total_attempts=0,
                last_triggered_at=None,        # Clear cooldown
                last_satisfied_at=None,        # Clear satisfaction cooldown
                urgency=1.0,                   # MAX urgency for testing
                satisfaction_level=0.5         # Medium satisfaction for motivation
            )
        )
        print(f"Force reset {state_result.rowcount} motivational states with max urgency")
        
        await session.commit()
        print("✅ Force clear completed")
        
        # Verify the clear worked
        from sqlalchemy import select
        states_result = await session.execute(select(MotivationalState))
        states = states_result.scalars().all()
        
        print("\nVerification - all states should have:")
        print("- urgency=1.0, satisfaction=0.5, last_triggered_at=None")
        for state in states:
            triggered_str = "None" if not state.last_triggered_at else state.last_triggered_at.isoformat()
            print(f"   {state.motivation_type:25} | urgency={state.urgency:.1f} | satisfaction={state.satisfaction_level:.1f} | triggered={triggered_str}")

if __name__ == "__main__":
    asyncio.run(force_clear_cooldowns())