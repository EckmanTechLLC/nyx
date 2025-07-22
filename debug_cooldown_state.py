#!/usr/bin/env python3
"""
Debug script to check the actual cooldown state in the database
"""

import asyncio
import sys
sys.path.append('/app')

async def check_cooldown_state():
    """Check the actual last_triggered_at values in the database"""
    from database.connection import db_manager
    from database.models import MotivationalState
    from sqlalchemy import select
    from datetime import datetime, timezone
    
    async with db_manager.get_async_session() as session:
        print("=== MOTIVATIONAL STATE COOLDOWN CHECK ===")
        
        states = await session.execute(select(MotivationalState))
        all_states = states.scalars().all()
        
        now = datetime.now(timezone.utc)
        
        for state in all_states:
            last_triggered = state.last_triggered_at
            if last_triggered:
                time_diff = now - last_triggered
                hours_ago = time_diff.total_seconds() / 3600
                print(f"{state.motivation_type:25} | Last triggered: {hours_ago:.2f} hours ago ({last_triggered})")
            else:
                print(f"{state.motivation_type:25} | Last triggered: Never (NULL)")

if __name__ == "__main__":
    asyncio.run(check_cooldown_state())