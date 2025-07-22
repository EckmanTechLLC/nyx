#!/usr/bin/env python3
"""
Debug script to trace the complete flow from engine evaluation to task spawning
to identify where the disconnect occurs
"""

import asyncio
import sys
import logging
sys.path.append('/app')

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

async def debug_full_autonomous_flow():
    """Trace the complete autonomous task flow end-to-end"""
    print("=== DEBUGGING COMPLETE AUTONOMOUS TASK FLOW ===")
    
    from database.connection import db_manager
    from core.motivation.engine import MotivationalModelEngine
    from core.motivation.arbitration import GoalArbitrationEngine
    from core.motivation.states import MotivationalStateManager
    from database.models import MotivationalTask
    from sqlalchemy import select, func
    
    # Initialize components exactly as pressure test does
    state_manager = MotivationalStateManager()
    arbitration_engine = GoalArbitrationEngine()
    
    engine = MotivationalModelEngine(
        evaluation_interval=5.0,
        max_concurrent_motivated_tasks=3,
        min_arbitration_threshold=0.1
    )
    
    async with db_manager.get_async_session() as session:
        print("\n1. INITIAL STATE CHECK")
        print("=" * 40)
        
        # Check initial task count
        task_count_result = await session.execute(select(func.count(MotivationalTask.id)))
        initial_task_count = task_count_result.scalar() or 0
        print(f"Initial task count: {initial_task_count}")
        
        # Check active task count (what blocks new spawning)
        active_result = await session.execute(
            select(func.count(MotivationalTask.id))
            .where(MotivationalTask.status.in_(['queued', 'spawned', 'active']))
        )
        active_count = active_result.scalar() or 0
        print(f"Active tasks: {active_count}/{engine.max_concurrent_motivated_tasks}")
        
        print("\n2. ENGINE EVALUATION CYCLE")
        print("=" * 40)
        
        # Check if engine can spawn new tasks
        can_spawn = await engine._can_spawn_new_tasks(session)
        print(f"Can spawn new tasks: {can_spawn}")
        
        if not can_spawn:
            print("❌ Engine blocked from spawning - stopping here")
            return
        
        # Get states and calculate scores
        states = await state_manager.get_active_states(session)
        print(f"Active motivational states: {len(states)}")
        
        for state in states:
            score = await state_manager.calculate_arbitration_score(state)
            print(f"   {state.motivation_type:25} | Score: {score:.3f}")
        
        # Run goal arbitration
        selected_motivations = await arbitration_engine.arbitrate_goals(
            session,
            max_tasks=engine.max_concurrent_motivated_tasks,
            min_threshold=engine.min_arbitration_threshold
        )
        
        print(f"\nGoal arbitration selected: {len(selected_motivations)} motivations")
        for motivation in selected_motivations:
            score = await state_manager.calculate_arbitration_score(motivation)
            print(f"   Selected: {motivation.motivation_type} (score: {score:.3f})")
        
        if not selected_motivations:
            print("❌ No motivations selected - stopping here")
            return
            
        print("\n3. TASK SPAWNING PROCESS")
        print("=" * 40)
        
        # Now the critical part - does the engine actually spawn tasks?
        # Let's call the method that should create the tasks
        from core.motivation.spawner import SelfInitiatedTaskSpawner
        spawner = SelfInitiatedTaskSpawner()
        
        print("About to spawn tasks for selected motivations...")
        spawn_count = 0
        
        for motivation in selected_motivations:
            try:
                print(f"   Spawning task for: {motivation.motivation_type}")
                
                # This is the critical call - does it actually work?
                task = await spawner.spawn_task(session, motivation)
                
                if task:
                    print(f"   ✅ Created task {task.id}")
                    spawn_count += 1
                else:
                    print(f"   ❌ Failed to create task")
                    
            except Exception as e:
                print(f"   ❌ Error spawning task for {motivation.motivation_type}: {e}")
                import traceback
                traceback.print_exc()
        
        print(f"\nSpawned {spawn_count} tasks")
        
        # Commit the spawned tasks
        try:
            await session.commit()
            print("✅ Committed spawned tasks")
        except Exception as e:
            print(f"❌ Failed to commit spawned tasks: {e}")
            await session.rollback()
            return
        
        print("\n4. VERIFICATION")
        print("=" * 40)
        
        # Check final task count
        final_task_count_result = await session.execute(select(func.count(MotivationalTask.id)))
        final_task_count = final_task_count_result.scalar() or 0
        
        print(f"Final task count: {final_task_count}")
        print(f"Tasks created: {final_task_count - initial_task_count}")
        
        # Check pending tasks
        pending_tasks = await spawner.get_pending_tasks(session, limit=10)
        print(f"Pending tasks ready for workflow: {len(pending_tasks)}")
        
        for task in pending_tasks:
            print(f"   Task {task.id}: {task.status} - {task.generated_prompt[:50]}...")
        
        print("\n5. ENGINE METHOD CHECK")
        print("=" * 40)
        
        # Let's also test engine task spawning directly using the same pattern
        print("Testing direct spawning using engine's task_spawner...")
        try:
            # Use the same spawner as the engine
            engine_spawned = 0
            for motivation in selected_motivations:
                try:
                    task = await engine.task_spawner.spawn_task(session, motivation)
                    if task:
                        engine_spawned += 1
                        print(f"   Engine spawner created task {task.id}")
                except Exception as task_e:
                    print(f"   Engine spawner failed for {motivation.motivation_type}: {task_e}")
            
            print(f"Engine task_spawner spawned: {engine_spawned} tasks")
            
            await session.commit()
            
            # Final verification
            newest_count_result = await session.execute(select(func.count(MotivationalTask.id)))
            newest_count = newest_count_result.scalar() or 0
            print(f"Task count after engine task_spawner: {newest_count}")
            
        except Exception as e:
            print(f"❌ Error in engine task_spawner test: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_full_autonomous_flow())