#!/usr/bin/env python3
"""
Debug script to investigate the "Multiple rows found" error in the arbitration system
"""

import asyncio
import logging
from datetime import datetime, timezone

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def debug_arbitration_multiple_rows():
    """Debug the multiple rows error in arbitration system"""
    
    print("=" * 80)
    print("🔍 DEBUG: Arbitration Multiple Rows Error Analysis")
    print("=" * 80)
    
    try:
        from database.connection import db_manager
        from database.models import MotivationalState, MotivationalTask
        from sqlalchemy import select, and_, func
        
        async with db_manager.get_async_session() as session:
            # Step 1: Check motivational states count and duplicates
            print("\n📋 Step 1: Analyzing motivational states...")
            
            # Count total motivational states
            total_count = await session.execute(select(func.count(MotivationalState.id)))
            total = total_count.scalar()
            print(f"Total motivational states: {total}")
            
            # Check for duplicate motivation_types (which should be unique)
            duplicate_check = await session.execute(
                select(MotivationalState.motivation_type, func.count(MotivationalState.id))
                .group_by(MotivationalState.motivation_type)
                .having(func.count(MotivationalState.id) > 1)
            )
            duplicates = duplicate_check.all()
            
            if duplicates:
                print("❌ FOUND DUPLICATE MOTIVATIONAL STATES:")
                for motivation_type, count in duplicates:
                    print(f"   - {motivation_type}: {count} records")
            else:
                print("✅ No duplicate motivation_types found")
            
            # Step 2: Check specific maximize_coverage states
            print("\n📋 Step 2: Analyzing maximize_coverage states specifically...")
            
            maximize_states = await session.execute(
                select(MotivationalState)
                .where(MotivationalState.motivation_type == 'maximize_coverage')
            )
            max_states = maximize_states.all()
            
            print(f"Found {len(max_states)} 'maximize_coverage' states:")
            for i, (state,) in enumerate(max_states):
                print(f"   State {i+1}:")
                print(f"      ID: {state.id}")
                print(f"      Created: {state.created_at}")
                print(f"      Updated: {state.updated_at}")
                print(f"      Active: {state.is_active}")
                print(f"      Urgency: {state.urgency}")
                print(f"      Last triggered: {state.last_triggered_at}")
            
            # Step 3: Check active tasks for maximize_coverage
            print("\n📋 Step 3: Checking active tasks for maximize_coverage...")
            
            for i, (state,) in enumerate(max_states):
                print(f"\n   Checking tasks for State {i+1} (ID: {state.id}):")
                
                # This is the query that might be causing issues
                existing_task_query = select(MotivationalTask).where(and_(
                    MotivationalTask.motivational_state_id == state.id,
                    MotivationalTask.status.in_(['queued', 'spawned', 'active'])
                ))
                
                existing_tasks_result = await session.execute(existing_task_query)
                existing_tasks = existing_tasks_result.all()
                
                print(f"      Found {len(existing_tasks)} active tasks")
                for j, (task,) in enumerate(existing_tasks):
                    print(f"         Task {j+1}: {task.id} - Status: {task.status}")
                
                # Test the problematic scalar_one_or_none() call
                try:
                    single_task_result = await session.execute(existing_task_query)
                    single_task = single_task_result.scalar_one_or_none()
                    if single_task:
                        print(f"      ✅ scalar_one_or_none() returned task: {single_task.id}")
                    else:
                        print(f"      ✅ scalar_one_or_none() returned None (no active tasks)")
                except Exception as scalar_error:
                    print(f"      ❌ scalar_one_or_none() FAILED: {scalar_error}")
                    print(f"         This is likely the source of the 'Multiple rows found' error")
            
            # Step 4: Check database constraints and indexes
            print("\n📋 Step 4: Analyzing database schema expectations...")
            
            # Check if there should be a unique constraint on motivation_type
            print("Expected schema per documentation:")
            print("   - motivation_type should be unique per active state")
            print("   - Only one active task per motivation_state_id should exist")
            
            # Step 5: Simulate the arbitration process
            print("\n📋 Step 5: Simulating arbitration eligibility check...")
            
            if max_states:
                state = max_states[0][0]  # Use first maximize_coverage state
                print(f"Testing eligibility for state: {state.id}")
                
                try:
                    # This is the exact query from _is_eligible_for_spawning
                    existing_task = await session.execute(
                        select(MotivationalTask)
                        .where(and_(
                            MotivationalTask.motivational_state_id == state.id,
                            MotivationalTask.status.in_(['queued', 'spawned', 'active'])
                        ))
                    )
                    
                    # This is where the error occurs
                    result = existing_task.scalar_one_or_none()
                    
                    if result is None:
                        print("✅ Eligibility check passed - no active tasks found")
                    else:
                        print(f"✅ Eligibility check found active task: {result.id}")
                        
                except Exception as eligibility_error:
                    print(f"❌ Eligibility check FAILED: {eligibility_error}")
                    print("   This confirms the source of the arbitration error")
            
            print("\n" + "=" * 80)
            print("🔍 ANALYSIS COMPLETE")
            print("=" * 80)
            
    except Exception as e:
        print(f"\n💥 Debug script failed: {e}")
        import traceback
        traceback.print_exc()

async def main():
    """Main debug function"""
    try:
        await debug_arbitration_multiple_rows()
    except KeyboardInterrupt:
        print("\n🛑 Debug interrupted by user")
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())