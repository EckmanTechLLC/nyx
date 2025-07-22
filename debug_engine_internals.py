#!/usr/bin/env python3
"""
Debug script to trace engine internal evaluation cycles to identify why no tasks are spawned
"""

import asyncio
import sys
import logging
sys.path.append('/app')

# Set up detailed logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def debug_engine_internals():
    """Directly trace what happens inside engine evaluation cycles"""
    print("=== DEBUGGING ENGINE INTERNAL EVALUATION CYCLES ===")
    
    from database.connection import db_manager
    from core.motivation.engine import MotivationalModelEngine
    from core.motivation.arbitration import GoalArbitrationEngine
    from core.motivation.states import MotivationalStateManager
    from database.models import MotivationalTask
    from sqlalchemy import select, func
    
    # Create engine with debug logging
    engine = MotivationalModelEngine(
        evaluation_interval=5.0,
        max_concurrent_motivated_tasks=3,
        min_arbitration_threshold=0.1,
        test_mode=True  # Enable test mode for shorter cooldowns
    )
    
    # Don't start daemon - do manual evaluation
    print("Engine created, running manual evaluation cycle...")
    
    async with db_manager.get_async_session() as session:
        print("\n1. PRE-EVALUATION STATE CHECK")
        print("=" * 50)
        
        # Check task capacity
        task_count_result = await session.execute(
            select(func.count(MotivationalTask.id))
            .where(MotivationalTask.status.in_(['queued', 'spawned', 'active']))
        )
        active_count = task_count_result.scalar() or 0
        print(f"Active task count: {active_count}/{engine.max_concurrent_motivated_tasks}")
        
        can_spawn = await engine._can_spawn_new_tasks(session)
        print(f"Engine can spawn new tasks: {can_spawn}")
        
        print("\n2. MANUAL EVALUATION CYCLE")
        print("=" * 50)
        
        # Call the engine's actual evaluation method directly
        print("Calling engine._evaluate_and_act()...")
        
        try:
            # This is the method that should be creating tasks
            await engine._evaluate_and_act()
            print("✅ Evaluation cycle completed successfully")
            
        except Exception as e:
            print(f"❌ Error in evaluation cycle: {e}")
            import traceback
            traceback.print_exc()
            
        print("\n3. POST-EVALUATION STATE CHECK")
        print("=" * 50)
        
        # Check if tasks were created
        final_count_result = await session.execute(select(func.count(MotivationalTask.id)))
        final_count = final_count_result.scalar() or 0
        print(f"Total tasks after evaluation: {final_count}")
        
        if final_count > 0:
            # Show the tasks
            recent_tasks_result = await session.execute(
                select(MotivationalTask.status, MotivationalTask.generated_prompt)
                .order_by(MotivationalTask.spawned_at.desc())
                .limit(3)
            )
            recent_tasks = recent_tasks_result.fetchall()
            print("Recent tasks:")
            for status, prompt in recent_tasks:
                print(f"   {status}: {prompt[:50]}...")
        else:
            print("❌ No tasks were created by the evaluation cycle")
            
        print("\n4. ENGINE METHOD INSPECTION")
        print("=" * 50)
        
        # Let's also manually check what the arbitration engine returns
        arbitration_engine = GoalArbitrationEngine(test_mode=True)
        state_manager = MotivationalStateManager()
        
        print("Getting active states...")
        states = await state_manager.get_active_states(session)
        print(f"Found {len(states)} active states")
        
        for state in states:
            score = await state_manager.calculate_arbitration_score(state)
            print(f"   {state.motivation_type}: score={score:.3f}")
            
        print("\nRunning goal arbitration...")
        selected = await arbitration_engine.arbitrate_goals(
            session,
            max_tasks=engine.max_concurrent_motivated_tasks,
            min_threshold=engine.min_arbitration_threshold
        )
        print(f"Arbitration selected: {len(selected)} motivations")
        
        if selected:
            print("Selected motivations:")
            for motivation in selected:
                score = await state_manager.calculate_arbitration_score(motivation)
                print(f"   {motivation.motivation_type}: score={score:.3f}")
                
            # Now try to spawn tasks manually
            print("\nManual task spawning...")
            for motivation in selected:
                try:
                    print(f"   Spawning task for {motivation.motivation_type}...")
                    task = await engine.task_spawner.spawn_task(session, motivation)
                    if task:
                        print(f"   ✅ Created task {task.id}")
                    else:
                        print(f"   ❌ spawn_task returned None")
                except Exception as spawn_e:
                    print(f"   ❌ Error spawning: {spawn_e}")
                    
            await session.commit()
            
            # Final check
            newest_count_result = await session.execute(select(func.count(MotivationalTask.id)))
            newest_count = newest_count_result.scalar() or 0
            print(f"\nTasks after manual spawning: {newest_count}")
            
        else:
            print("❌ No motivations selected by arbitration")

if __name__ == "__main__":
    asyncio.run(debug_engine_internals())