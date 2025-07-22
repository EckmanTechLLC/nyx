#!/usr/bin/env python3
"""
Debug script to trace what happens during engine evaluation cycles
"""

import asyncio
import sys
import logging
sys.path.append('/app')

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

async def debug_engine_evaluation():
    """Run a single engine evaluation cycle with detailed debugging"""
    from database.connection import db_manager
    from core.motivation.engine import MotivationalModelEngine
    from core.motivation.arbitration import GoalArbitrationEngine
    from core.motivation.states import MotivationalStateManager
    
    print("=== DEBUGGING SINGLE ENGINE EVALUATION CYCLE ===")
    
    # Initialize components
    state_manager = MotivationalStateManager()
    arbitration_engine = GoalArbitrationEngine()
    
    engine = MotivationalModelEngine(
        evaluation_interval=5.0,
        max_concurrent_motivated_tasks=3,
        min_arbitration_threshold=0.1  # Same as pressure test
    )
    
    # Manually run one evaluation cycle
    async with db_manager.get_async_session() as session:
        print("\n1. Checking current motivational states...")
        states = await state_manager.get_active_states(session)
        for state in states:
            score = await state_manager.calculate_arbitration_score(state)
            print(f"   {state.motivation_type:25} | Urgency: {state.urgency:.3f} | Score: {score:.3f}")
        
        print(f"\n2. Checking if can spawn new tasks...")
        can_spawn = await engine._can_spawn_new_tasks(session)
        print(f"   Can spawn new tasks: {can_spawn}")
        
        if not can_spawn:
            from database.models import MotivationalTask
            from sqlalchemy import select, func
            active_result = await session.execute(
                select(func.count(MotivationalTask.id))
                .where(MotivationalTask.status.in_(['queued', 'spawned', 'active']))
            )
            active_count = active_result.scalar() or 0
            print(f"   Active task count: {active_count} (max: {engine.max_concurrent_motivated_tasks})")
            return
        
        print(f"\n3. Running goal arbitration...")
        selected_motivations = await arbitration_engine.arbitrate_goals(
            session,
            max_tasks=engine.max_concurrent_motivated_tasks,
            min_threshold=engine.min_arbitration_threshold
        )
        
        print(f"   Selected motivations: {len(selected_motivations)}")
        for i, motivation in enumerate(selected_motivations, 1):
            score = await state_manager.calculate_arbitration_score(motivation)
            print(f"   {i}. {motivation.motivation_type} (score: {score:.3f})")
        
        if not selected_motivations:
            print("   No motivations met the arbitration criteria")
            print(f"   Threshold: {engine.min_arbitration_threshold}")
            
            # Check why no motivations were selected
            print(f"\n4. Analyzing arbitration failure...")
            all_states = await state_manager.get_active_states(session)
            for state in all_states:
                score = await state_manager.calculate_arbitration_score(state)
                meets_threshold = score >= engine.min_arbitration_threshold
                print(f"   {state.motivation_type:25} | Score: {score:.3f} | Above threshold: {meets_threshold}")
        
        else:
            print(f"\n4. Would spawn {len(selected_motivations)} tasks")
            
        print(f"\n=== EVALUATION CYCLE COMPLETE ===")

if __name__ == "__main__":
    asyncio.run(debug_engine_evaluation())