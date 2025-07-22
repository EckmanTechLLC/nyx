#!/usr/bin/env python3
"""
Debug script to isolate and fix the feedback loop priority issue
"""

import asyncio
import sys
import os
sys.path.append('/app')

async def debug_feedback_loop():
    """Debug the feedback loop priority issue step by step"""
    
    print("=== DEBUGGING FEEDBACK LOOP PRIORITY ISSUE ===")
    
    from database.connection import db_manager
    from core.motivation.states import MotivationalStateManager
    from core.motivation.spawner import SelfInitiatedTaskSpawner
    from core.motivation.feedback import MotivationalFeedbackLoop
    
    async with db_manager.get_async_session() as session:
        state_manager = MotivationalStateManager()
        spawner = SelfInitiatedTaskSpawner()
        feedback_loop = MotivationalFeedbackLoop()
        
        print("\n1. Getting idle_exploration state...")
        state = await state_manager.get_state_by_type(session, 'idle_exploration')
        print(f"   Original state urgency: {state.urgency}, satisfaction: {state.satisfaction}")
        print(f"   boost_factor: {state.boost_factor}, max_urgency: {state.max_urgency}")
        
        print("\n2. Reducing satisfaction first (since it's at max 1.0)...")
        # Manually reduce satisfaction so we can get a meaningful arbitration score
        from database.models import MotivationalState
        from sqlalchemy import update
        await session.execute(
            update(MotivationalState)
            .where(MotivationalState.id == state.id)
            .values(satisfaction=0.3)  # Reduce to 0.3 so inverse = 0.7
        )
        await session.flush()
        
        print("\n3. Boosting motivation urgency...")
        await state_manager.boost_motivation(session, 'idle_exploration', 0.5)
        await session.flush()
        
        print("\n4. Getting updated state...")
        updated_state = await state_manager.get_state_by_type(session, 'idle_exploration')
        print(f"   Updated state urgency: {updated_state.urgency}, satisfaction: {updated_state.satisfaction}")
        
        print("\n5. Calculating arbitration score manually...")
        arbitration_score = await state_manager.calculate_arbitration_score(updated_state)
        print(f"   Arbitration score: {arbitration_score}")
        
        print("\n6. Spawning task with updated state...")
        task = await spawner.spawn_task(session, updated_state)
        print(f"   Task priority: {task.task_priority}, arbitration_score: {task.arbitration_score}")
        
        await session.flush()
        original_satisfaction = updated_state.satisfaction
        
        print("\n7. Processing successful outcome...")
        await feedback_loop.process_outcome(
            session,
            str(task.id),
            success=True,
            outcome_score=0.8,
            metadata={'test': 'debug_feedback_test'}
        )
        
        print("\n8. Checking final satisfaction...")
        final_state = await state_manager.get_state_by_type(session, 'idle_exploration')
        print(f"   Original satisfaction: {original_satisfaction}")
        print(f"   Final satisfaction: {final_state.satisfaction}")
        print(f"   Satisfaction change: {final_state.satisfaction - original_satisfaction}")
        
        if final_state.satisfaction != original_satisfaction:
            print("\n✅ SUCCESS: Satisfaction was updated!")
        else:
            print("\n❌ FAILED: Satisfaction was not updated")
            
        await session.commit()
        print("\n=== DEBUG COMPLETE ===")

if __name__ == "__main__":
    asyncio.run(debug_feedback_loop())